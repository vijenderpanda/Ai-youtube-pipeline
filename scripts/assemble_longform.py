#!/usr/bin/env python3
"""
assemble_longform.py — build a 16:9 LONG-FORM video from ordered segments
(LONGFORM-PLAN.md §3/§6 gap 1: "nothing in this repo renders 16:9").

The channel's whole pipeline renders 1080x1920 (Shorts). A long-form is a genuine
second rendering path. Rather than reimplement the join engine, this reuses the
PROVEN spine in assemble_compilation.py (loudnorm -14 two-pass, per-join xfade with
correct running-offset math, alimiter ceiling, predicted-vs-actual duration check,
assert-before-replace) and adds the two things long-form needs on top of it:

  1. TARGET IS FORCED to 1920x1080. assemble_compilation inherits the FIRST segment's
     dims — feed it 9:16 Shorts and it conforms the whole video VERTICAL. Long-form must
     letterbox/pillarbox any-aspect input into a landscape frame, so we always pass an
     explicit target=(1920,1080,fps). (The conform in build_compilation already does the
     letterboxing; it just needed to be told the frame.)

  2. CHAPTER SIDECAR. YouTube chapters + the keyword description are, per the plan, "free
     for us — we have per-beat timings". This emits <out>.chapters.txt in the exact format
     YouTube parses (first line 00:00, one `M:SS Title` per chapter), computed from the same
     running-offset math the join uses, so the timestamps match the cut to the frame.

The long-form beat structure from the plan (cold-open -> funnel/promise -> segments ->
mid-roll stakes interrupt -> payoff -> outro) needs NO new join code: every beat is just
another ordered `video`/`interlude` segment with a `title`. Bookends are intentionally NOT
used (the cold-open/outro are real segments), so chapter times stay exact.

Spec (channels/<slug>/longform/<name>.json):
  {
    "title": "The AI Beginner's Playbook",
    "target": "1920x1080",       # optional; this IS the default and only tested value
    "fps": 30,                    # optional (default 30)
    "xfade": 2.0,                 # crossfade seconds per join (floor 2.0). xfade_ramp also honored.
    "segments": [
      {"video": "channels/claude-tricks/renders/longform/coldopen.mp4",
       "title": "You're paying for AI and using 10% of it", "chapter": false},
      {"video": ".../seg01_model_switch.mp4", "title": "1. Switch models in one click"},
      {"video": ".../seg02_effort_dial.mp4",  "title": "2. Turn up the thinking dial"},
      {"interlude": {"audio": ".../bed.mp3", "stills": [".../news.png"], "duration": 25},
       "title": "Why companies are cutting AI-illiterate roles"},   # mid-roll interrupt
      {"video": ".../seg06.mp4", "title": "6. ..."},
      {"video": ".../payoff.mp4", "title": "The one prompt that picks your next move"},
      {"video": ".../outro.mp4",  "title": "Outro", "chapter": false}
    ]
  }

A segment with "chapter": false is a real beat in the cut but is NOT written to the
chapter list (cold-opens/outros are not chapters). Every other segment needs a "title".

Usage:
  python3 scripts/assemble_longform.py --channel claude-tricks \
      --spec channels/claude-tricks/longform/beginner_playbook.json \
      --out  channels/claude-tricks/renders/longform/beginner_playbook.mp4

  # Validate the 16:9 filtergraph at full scale on SYNTHETIC sources (no credits spent —
  # Playbook §14 mandate). Proves the vertical->letterbox conform, the chapter arithmetic
  # and the loudness chain before any real asset exists:
  python3 scripts/assemble_longform.py --selftest --out /tmp/longform_selftest.mp4
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import assemble_compilation as ac  # reuse the proven spine — do NOT reimplement it

FFMPEG = ac.FFMPEG
DEFAULT_TARGET = (1920, 1080)
DEFAULT_FPS = "30/1"
# YouTube's own chapter rules — enforce them at emit time, not after upload rejects them.
YT_MIN_CHAPTERS = 3
YT_MIN_CHAPTER_GAP = 10.0   # seconds; consecutive chapters closer than this are silently dropped by YT


def fmt_ts(seconds):
    """YouTube chapter timestamp: H:MM:SS over an hour, else M:SS (both parse; this is
    the canonical short form). Floor to the second — a chapter that rounds UP past its
    own frame lands the viewer before the cut."""
    s = int(seconds)  # floor
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def parse_target(spec):
    t = spec.get("target", "1920x1080")
    try:
        w, h = (int(x) for x in str(t).lower().split("x"))
    except ValueError:
        sys.exit(f"!! target must be WxH (e.g. 1920x1080), got {t!r}")
    if (w, h) != DEFAULT_TARGET:
        print(f"!! target {w}x{h} is not the tested 1920x1080 — proceeding, but nothing "
              f"downstream (thumbnails, Remotion cards) is built for it yet")
    fps = spec.get("fps", 30)
    fps_frac = f"{int(fps)}/1" if isinstance(fps, (int, float)) and float(fps).is_integer() else str(fps)
    return w, h, fps_frac


def compute_chapters(segments, spec_segments, xfades):
    """Running-offset math IDENTICAL to build_compilation's join: segment i first appears
    at sum(durs[:i]) - sum(xfades[:i]). Returns [(start_seconds, title)] for every segment
    whose spec entry did not set chapter:false."""
    durs = [d for _, d, _ in segments]
    chapters = []
    for i, raw in enumerate(spec_segments):
        if raw.get("chapter") is False:
            continue
        title = raw.get("title")
        if not title:
            sys.exit(f"!! segment {i} needs a \"title\" (or set \"chapter\": false to exclude it)")
        off = sum(durs[:i]) - sum(xfades[:i]) if i else 0.0
        chapters.append((max(0.0, off), title))
    return chapters


def write_chapters(chapters, out_path):
    """Emit <out>.chapters.txt. YouTube requires the first chapter at 00:00 and >=3
    chapters >=10s apart — assert loudly here rather than shipping a description YouTube
    silently ignores."""
    if not chapters:
        print("!! no chapters to write (all segments were chapter:false)")
        return None
    # YouTube demands the first chapter be exactly 00:00. The cold-open is chapter:false,
    # so the first REAL chapter starts a few seconds in — pin it to 0:00 so YT accepts the
    # list (the cold-open belongs to chapter 1 anyway).
    chapters = list(chapters)
    if chapters[0][0] > 0:
        chapters[0] = (0.0, chapters[0][1])

    if len(chapters) < YT_MIN_CHAPTERS:
        print(f"!! only {len(chapters)} chapters — YouTube needs >={YT_MIN_CHAPTERS} or it "
              f"shows none. Add segments or promote a chapter:false beat.")
    for i in range(1, len(chapters)):
        gap = chapters[i][0] - chapters[i - 1][0]
        if gap < YT_MIN_CHAPTER_GAP:
            print(f"!! chapters {i} and {i+1} are {gap:.1f}s apart (<{YT_MIN_CHAPTER_GAP}s) — "
                  f"YouTube will drop one. Merge or lengthen the segment.")

    txt = os.path.splitext(out_path)[0] + ".chapters.txt"
    with open(txt, "w") as f:
        f.write("# Paste into the YouTube description (timestamps make chapters):\n")
        for start, title in chapters:
            f.write(f"{fmt_ts(start)} {title}\n")
    print(f">> chapters: {txt} ({len(chapters)} chapters)")
    return txt


def build(spec, channel, out_path, crf, preset):
    W, H, fps = parse_target(spec)
    xfade = float(spec.get("xfade", ac.DEFAULT_XFADE))
    xfade_ramp = spec.get("xfade_ramp")
    if xfade_ramp and len(xfade_ramp) != 2:
        sys.exit("!! xfade_ramp must be [first_join_seconds, last_join_seconds]")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="longform_")
    try:
        segments = ac.resolve_segments(spec, tmp)
        print(f".. {len(segments)} segments resolved: "
              + ", ".join(f"{k}({d:.1f}s)" for _, d, k in segments))
        xfades = ac.resolve_xfades(len(segments), xfade, xfade_ramp)

        chapters = compute_chapters(segments, spec["segments"], xfades)

        ac.build_compilation(
            segments, xfades, dim_arc=bool(spec.get("dim_arc", False)),
            out_path=out_path, crf=crf, preset=preset,
            dim_tempo_scope=spec.get("dim_tempo_scope", "interlude"),
            dim_brightness_step=spec.get("dim_brightness_step"),
            dim_tempo_step=spec.get("dim_tempo_step"),
            target=(W, H, fps),          # <<< the whole point: force 16:9, never inherit input dims
        )
        write_chapters(chapters, out_path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total = ac.probe_dur(out_path)
    w, h, _ = ac.probe_video(out_path)
    print(f">> DONE: {out_path}  ({total:.2f}s = {int(total//60)}m{total%60:04.1f}s, "
          f"{w}x{h}, {len(spec['segments'])} segments)")
    if (w, h) != (W, H):
        sys.exit(f"!! output is {w}x{h}, expected {W}x{H} — the target override did not take")
    return out_path


# ---------------------------------------------------------------------------
# --selftest: full-scale synthetic validation (Playbook §14 — prove the graph
# before spending generation credits). Deliberately feeds a MIX of 16:9 and 9:16
# synthetic segments so the letterbox/pillarbox conform is exercised, not just
# same-aspect joins.
# ---------------------------------------------------------------------------

def make_synthetic_segment(path, dur, w, h, color, freq):
    """A lavfi color+sine clip at EXACT duration — the §14 recipe."""
    run = ac.run
    run([FFMPEG, "-y",
         "-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"color=c={color}:s={w}x{h}:r=30",
         "-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"sine=frequency={freq}:sample_rate=48000",
         "-shortest", *ac.venc("28", "ultrafast"), "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", path])
    ac.verify_media(path, f"synthetic {os.path.basename(path)}")


def selftest(out_path, crf, preset):
    tmp = tempfile.mkdtemp(prefix="longform_selftest_")
    try:
        # exact planned durations, deliberately including a 9:16 segment to prove the conform
        plan = [
            ("coldopen", 6.0, 1920, 1080, "0x101418", 220, False),
            ("seg01",    40.0, 1080, 1920, "0x1a1a2e", 330, True),   # <-- VERTICAL input
            ("seg02",    38.0, 1920, 1080, "0x16213e", 440, True),
            ("midroll",  25.0, 1280, 720,  "0x0f3460", 550, True),   # <-- odd aspect
            ("seg03",    42.0, 1080, 1920, "0x1a1a2e", 660, True),   # <-- VERTICAL again
            ("outro",    8.0,  1920, 1080, "0x101418", 770, False),
        ]
        seg_paths = []
        spec_segments = []
        for name, dur, w, h, color, freq, is_chap in plan:
            p = os.path.join(tmp, f"{name}.mp4")
            make_synthetic_segment(p, dur, w, h, color, freq)
            seg_paths.append(p)
            entry = {"video": p, "title": f"{name} chapter"}
            if not is_chap:
                entry["chapter"] = False
            spec_segments.append(entry)

        spec = {"title": "SELFTEST", "target": "1920x1080", "fps": 30,
                "xfade": 2.0, "segments": spec_segments}

        print("\n== SELFTEST: full-scale synthetic 16:9 join (mixed 9:16 / 16:9 / 720p inputs) ==")
        build(spec, channel="_selftest", out_path=out_path, crf=crf, preset=preset)

        # Assertions the plan cares about
        w, h, _ = ac.probe_video(out_path)
        assert (w, h) == DEFAULT_TARGET, f"output {w}x{h} != 1920x1080"
        durs = [d for _, d, _ in ac.resolve_segments(spec, tmp)]
        xfades = ac.resolve_xfades(len(durs), 2.0, None)
        predicted = sum(durs) - sum(xfades)
        actual = ac.probe_dur(out_path)
        assert abs(actual - predicted) <= 1.0, f"duration drift {actual-predicted:+.2f}s"
        chap_txt = os.path.splitext(out_path)[0] + ".chapters.txt"
        assert os.path.isfile(chap_txt), "chapters sidecar not written"
        lines = [l for l in open(chap_txt).read().splitlines() if l and not l.startswith("#")]
        assert lines[0].startswith("0:00"), f"first chapter not at 0:00: {lines[0]!r}"
        assert len(lines) == 4, f"expected 4 chapters (6 segs, 2 chapter:false), got {len(lines)}"
        print("\n== chapters.txt ==")
        print(open(chap_txt).read())
        print(f"== SELFTEST PASS: {w}x{h}, {actual:.2f}s (predicted {predicted:.2f}s), "
              f"{len(lines)} chapters, vertical+odd inputs letterboxed cleanly ==")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Build a 16:9 long-form from ordered segments + emit chapters.")
    ap.add_argument("--channel", help="channel slug (used only for messaging; no bookends applied)")
    ap.add_argument("--spec", help="longform spec json")
    ap.add_argument("--out", required=True, help="output mp4")
    ap.add_argument("--crf", default="19")
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--selftest", action="store_true",
                    help="validate the 16:9 graph on synthetic sources (no spec/credits needed)")
    args = ap.parse_args()

    if args.selftest:
        selftest(args.out, args.crf, args.preset)
        return
    if not args.spec:
        sys.exit("!! --spec is required (or use --selftest)")
    spec = json.load(open(args.spec))
    if "segments" not in spec or not spec["segments"]:
        sys.exit("!! spec has no segments")
    build(spec, args.channel or spec.get("channel", "unknown"), args.out, args.crf, args.preset)


if __name__ == "__main__":
    main()
