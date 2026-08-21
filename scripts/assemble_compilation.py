#!/usr/bin/env python3
"""
assemble_compilation.py — bind a channel's published episodes into one
long-form compilation (Playbook §11/§13: "long-form compilation that binds
shorts/episodes = where real ad RPM lives"). No existing generator does this —
assemble_video.py / assemble_synced.py only build single episodes.

  ep01.mp4 ─┐
  interlude ├─►  [conform each to a uniform target + loudness-match]  ─►
  ep02.mp4 ─┘        [>=2s video xfade + audio acrossfade, never a hard cut]
                  ─►  add_bookends.py (intro/outro)  ─►  OUT.mp4

Usage:
  python3 scripts/assemble_compilation.py --channel pip-moonlit-garden \
      --spec channels/pip-moonlit-garden/comp/30min_calm.json \
      --out  channels/pip-moonlit-garden/renders/30min_calm.mp4

comp.json:
  {
    "segments": [
      {"video": "channels/<slug>/renders/song01.mp4"},
      {"interlude": {"audio": "path/to/bed.mp3",
                     "stills": ["path/a.jpg", "path/b.jpg"],
                     "duration": 20, "pace": 0.015}},
      {"video": "channels/<slug>/renders/song02.mp4"}
    ],
    "xfade": 2.5,          # crossfade seconds between segments (floor 2.0 — never a hard cut)
    "xfade_ramp": [2.5, 5.0],   # OPTIONAL: ramp the crossfade from first join to last, so a
                                # sleep compilation's back half dissolves more slowly than its
                                # front half. Overrides "xfade". Both ends obey the 2.0s floor.
    "dim_arc": false,      # progressive brightness/tempo ramp across segments (calm channels only)
    "dim_tempo_scope": "interlude",   # who gets the atempo ramp: interlude (default) | all | none
    "end_on_last_frame": true   # never truncate with -shortest; the last segment plays out fully
  }

🔴 dim_arc's TEMPO ramp TRUNCATES the end of whatever it touches — which is why it
defaults to interludes only. `atempo=0.93` stretches a segment's audio to ~1.077x its
length, and the graph then trims back to the segment's VIDEO duration, so the last ~7%
of the musical content is silently never heard. Measured on a synthetic tail-beep:
at the 14th segment (atempo 0.916) a 160s song loses its final ~15s — the entire closing
cadence. On a bed that is a looped ambient reprise nobody can tell; on a published song
it is a modification, and a compilation whose premise is "each published song appears
once, unmodified" must not do it. `dim_tempo_scope: "all"` restores the old behaviour
for callers who really want it; the brightness ramp is unaffected either way.

Conventions carried over from add_bookends.py / §3 of the playbook:
  - loudnorm two-pass (measure -> linear correct) to -14 LUFS per segment before joining
  - amix is NOT used here (acrossfade replaces it), but the alimiter=0.89 ceiling from the
    mastering formula still applies at the very end to tame the joined peaks
  - assert-before-replace: every input (existing master OR freshly rendered interlude) is
    ffprobed for a real moov atom + nonzero duration before being fed to the big filtergraph;
    a 0-byte/broken producer output fails loudly, never silently continues
  - supersample 2x before zoompan (kills jitter); pass -framerate explicitly on looped stills
    (a bare -loop 1 -t defaults to 25fps and undercounts frames — §10c)
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
from ffmpeg_util import venc  # GPU (NVENC) encode when available, else libx264

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

PIX_FMT = "yuv420p"
A_RATE = 48000
A_CH = 2
A_BITRATE = "192k"
LUFS_I = -14.0
LUFS_TP = -1.5
LUFS_LRA = 11.0
ALIMITER = 0.89          # §3 mastering formula — tame peaks to ~broadcast
MIN_XFADE = 2.0           # "never a hard cut" floor
DEFAULT_XFADE = 2.5
DEFAULT_PACE = 0.015      # ultra-slow Ken Burns push for interlude stills (fraction zoom growth)
DEFAULT_DIM_BRIGHTNESS_STEP = 0.02
DEFAULT_DIM_TEMPO_STEP = 0.006
# The dim arc's end points. A FIXED per-segment step plus a clamp is a trap on a long
# compilation: 0.02/segment hits the -0.20 floor at segment 11, so a 15-segment hour
# spends its last 28 minutes — the part that is supposed to be sinking into the dark —
# at exactly ONE brightness. So the steps auto-spread across however many segments
# there actually are, landing on the floor at the final segment. A spec that sets
# dim_brightness_step / dim_tempo_step explicitly opts back into fixed steps.
DIM_BRIGHTNESS_FLOOR = -0.20
DIM_TEMPO_FLOOR = 0.94          # ≤6% slow-down: also bounds the atempo end-trim loss


def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def probe_video(path):
    out = subprocess.check_output([
        FFPROBE, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "json", path])
    st = json.loads(out)["streams"][0]
    return int(st["width"]), int(st["height"]), st.get("r_frame_rate", "30/1")


def probe_dur(path):
    out = subprocess.check_output([
        FFPROBE, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path])
    return float(out.strip())


def has_audio(path):
    out = subprocess.check_output([
        FFPROBE, "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=index", "-of", "csv=p=0", path])
    return bool(out.strip())


def fps_float(frac):
    try:
        n, d = frac.split("/")
        return float(n) / float(d)
    except (ValueError, ZeroDivisionError):
        return float(frac)


def verify_media(path, label):
    """Assert-before-replace: a producer output with no moov atom / 0 duration
    must fail LOUDLY here, not get fed silently into the big join graph."""
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        sys.exit(f"!! {label}: missing or 0-byte — {path}")
    try:
        dur = probe_dur(path)
    except subprocess.CalledProcessError:
        sys.exit(f"!! {label}: ffprobe failed (no moov atom / broken container) — {path}")
    if dur <= 0:
        sys.exit(f"!! {label}: zero-length media — {path}")
    return dur


def measure_loudness(path):
    """Two-pass loudnorm measure (mirrors add_bookends.py). None -> caller falls
    back to single-pass dynamic loudnorm."""
    cmd = [FFMPEG, "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0",
           "-af", f"loudnorm=I={LUFS_I}:TP={LUFS_TP}:LRA={LUFS_LRA}:print_format=json",
           "-f", "null", "-"]
    print("+", " ".join(str(c) for c in cmd))
    p = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
    if p.returncode != 0:
        print(f"!! loudness measurement failed ({path}) — falling back to dynamic loudnorm")
        return None
    err = p.stderr
    try:
        blob = err[err.rindex("{"):err.rindex("}") + 1]
        j = json.loads(blob)
        return {
            "measured_I": j["input_i"], "measured_TP": j["input_tp"],
            "measured_LRA": j["input_lra"], "measured_thresh": j["input_thresh"],
            "offset": j["target_offset"],
        }
    except (ValueError, KeyError) as e:
        print(f"!! could not parse loudnorm JSON ({path}: {e}) — falling back to dynamic loudnorm")
        return None


def loudnorm_filter(path):
    m = measure_loudness(path)
    ln = f"loudnorm=I={LUFS_I}:TP={LUFS_TP}:LRA={LUFS_LRA}"
    if m:
        ln += (f":measured_I={m['measured_I']}:measured_TP={m['measured_TP']}"
               f":measured_LRA={m['measured_LRA']}:measured_thresh={m['measured_thresh']}"
               f":offset={m['offset']}:linear=true")
    return ln


# ---------------------------------------------------------------------------
# Interlude rendering: stills -> ultra-slow Ken Burns clip, muxed with audio.
# ---------------------------------------------------------------------------

def ken_burns_still(img, dur, out, fps, pace, direction="in"):
    """Supersample 2x then zoompan — a true push so slow it's felt, not seen
    (mirrors make_still_hold.py). `direction` alternates in/out across stills
    in one interlude for a little variety without ever being fast."""
    n = max(int(round(dur * fps)), 1)
    if direction == "out":
        z = f"max({1+pace}-{pace}*on/{max(n-1,1)},1.0)"
    else:
        z = f"min(1.0+{pace}*on/{max(n-1,1)},{1+pace})"
    vf = (f"scale=iw*2:ih*2:flags=lanczos,"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"d=1:s=1920x1080:fps={fps},setsar=1,format={PIX_FMT}")
    run([FFMPEG, "-y", "-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", img,
         "-vf", vf, "-r", str(fps), "-frames:v", str(n),
         *venc("18", "slow"), "-pix_fmt", PIX_FMT, out])
    verify_media(out, f"interlude still clip ({os.path.basename(img)})")


def concat_stills(clips, out, internal_xfade):
    """Small internal crossfade between stills WITHIN one interlude (the
    segment-level >=2s floor is a comp-join rule, not required in here, but a
    hard cut between stills looks amateur too — so we still soften it)."""
    n = len(clips)
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    if n == 1:
        run([FFMPEG, "-y", "-i", clips[0], "-c", "copy", out]); return
    durs = [probe_dur(c) for c in clips]
    fc, prev = [], "[0:v]"
    for i in range(1, n):
        off = sum(durs[:i]) - i * internal_xfade
        lbl = "[vout]" if i == n - 1 else f"[x{i}]"
        fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={internal_xfade}:offset={max(off,0):.3f}{lbl}")
        prev = lbl
    run([FFMPEG, "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[vout]",
         *venc("18", "medium"), "-pix_fmt", PIX_FMT, out])


def build_interlude(entry, idx, tmpdir, fps=30):
    """entry = {"audio": path, "stills": [path,...], "duration": s, "pace": float}
    Returns (path_to_muxed_clip, duration)."""
    audio = entry["audio"]
    stills = entry["stills"]
    duration = float(entry["duration"])
    pace = float(entry.get("pace", DEFAULT_PACE))
    if not stills:
        sys.exit(f"!! interlude {idx}: no stills given")
    verify_media(audio, f"interlude {idx} audio")
    for s in stills:
        if not os.path.isfile(s):
            sys.exit(f"!! interlude {idx}: still not found — {s}")

    per = duration / len(stills)
    clips = []
    for i, still in enumerate(stills):
        clip = os.path.join(tmpdir, f"interlude{idx}_still{i:02d}.mp4")
        ken_burns_still(still, per, clip, fps, pace, direction="in" if i % 2 == 0 else "out")
        clips.append(clip)

    silent = os.path.join(tmpdir, f"interlude{idx}_silent.mp4")
    internal_xfade = min(1.0, per / 3) if len(clips) > 1 else 0.0
    concat_stills(clips, silent, internal_xfade)
    verify_media(silent, f"interlude {idx} silent video")
    actual_dur = probe_dur(silent)

    muxed = os.path.join(tmpdir, f"interlude{idx}.mp4")
    fo = max(0.1, actual_dur - 2.0)
    run([FFMPEG, "-y", "-i", silent, "-stream_loop", "-1", "-i", audio,
         "-filter_complex",
         f"[1:a]atrim=0:{actual_dur:.3f},afade=t=in:st=0:d=1.5,"
         f"afade=t=out:st={fo:.2f}:d=2,{loudnorm_filter(audio)}[a]",
         "-map", "0:v", "-map", "[a]", "-t", f"{actual_dur:.3f}",
         "-c:v", "copy", "-c:a", "aac", "-b:a", A_BITRATE, muxed])
    verify_media(muxed, f"interlude {idx} muxed clip")
    return muxed, actual_dur


# ---------------------------------------------------------------------------
# Main join: conform every segment to one spec, loudness-match, crossfade.
# ---------------------------------------------------------------------------

def resolve_segments(spec, tmpdir):
    """Return [(path, duration, kind)] in order, verifying every one."""
    out = []
    for i, seg in enumerate(spec["segments"]):
        if "video" in seg:
            path = seg["video"]
            if not os.path.isabs(path):
                path = os.path.join(REPO, path) if not os.path.isfile(path) else path
            dur = verify_media(path, f"segment {i} (video)")
            out.append((path, dur, "video"))
        elif "interlude" in seg:
            path, dur = build_interlude(seg["interlude"], i, tmpdir)
            out.append((path, dur, "interlude"))
        else:
            sys.exit(f"!! segment {i}: must have 'video' or 'interlude' key")
    return out


def resolve_xfades(n, xfade, xfade_ramp):
    """One crossfade value per JOIN (n-1 of them).

    A flat `xfade` is the common case. `xfade_ramp=[a, b]` linearly interpolates
    from the first join to the last, which is how a sleep compilation gets a back
    half that dissolves more slowly than its front half — the same "progressive"
    idea as dim_arc, applied to the joins. Every value is clamped to the 2.0s
    never-a-hard-cut floor.
    """
    if n < 2:
        return []
    if xfade_ramp:
        a, b = float(xfade_ramp[0]), float(xfade_ramp[1])
        if n == 2:
            vals = [b]
        else:
            vals = [a + (b - a) * i / (n - 2) for i in range(n - 1)]
    else:
        vals = [float(xfade)] * (n - 1)
    out = []
    for i, v in enumerate(vals):
        if v < MIN_XFADE:
            print(f"!! join {i}: xfade={v:.2f}s is below the {MIN_XFADE}s "
                  f"never-a-hard-cut floor — clamping")
            v = MIN_XFADE
        out.append(v)
    return out


def build_compilation(segments, xfades, dim_arc, out_path, crf="19", preset="medium",
                       dim_brightness_step=None,
                       dim_tempo_step=None,
                       dim_tempo_scope="interlude",
                       target=None):
    n = len(segments)
    paths = [s[0] for s in segments]
    durs = [s[1] for s in segments]

    # auto-spread so the LAST segment sits exactly on the floor (see the constants)
    spread = max(n - 1, 1)
    if dim_brightness_step is None:
        dim_brightness_step = abs(DIM_BRIGHTNESS_FLOOR) / spread
    if dim_tempo_step is None:
        dim_tempo_step = (1.0 - DIM_TEMPO_FLOOR) / spread

    # Target spec resolution, in priority order:
    #   1. explicit `target=(W, H, fps)` — REQUIRED for long-form, where the inputs may be
    #      9:16 Shorts and inheriting the first segment's dims would conform the whole video
    #      VERTICAL. assemble_longform.py always passes (1920, 1080, ...). The conform below
    #      already letterboxes/pillarboxes any-aspect input into this frame.
    #   2. first VIDEO segment (existing masters define the house look — the Lulla path);
    #   3. all-interlude fallback = the 1920x1080/30 every generator renders interludes at.
    video_segs = [s for s in segments if s[2] == "video"]
    if target is not None:
        W, H, fps = target
    elif video_segs:
        W, H, fps = probe_video(video_segs[0][0])
    else:
        W, H, fps = 1920, 1080, "30/1"
    fps_n = fps_float(fps)
    xf_desc = (f"{xfades[0]:.2f}→{xfades[-1]:.2f}s ramp" if xfades and xfades[0] != xfades[-1]
               else f"{xfades[0]:.2f}s flat" if xfades else "n/a")
    print(f".. target spec: {W}x{H} @ {fps_n:.3f} fps, {PIX_FMT}, aac {A_RATE}Hz x{A_CH}, "
          f"loudnorm I={LUFS_I} LUFS, xfade={xf_desc}, dim_arc={dim_arc}"
          f"{f' (tempo scope: {dim_tempo_scope})' if dim_arc else ''}")

    needs_silence = [not has_audio(p) for p in paths]
    inputs = []
    for p in paths:
        inputs += ["-i", p]
    silent_order = [i for i, s in enumerate(needs_silence) if s]
    for i in silent_order:
        inputs += ["-f", "lavfi", "-t", f"{durs[i]:.3f}", "-i", f"anullsrc=r={A_RATE}:cl=stereo"]

    filt = []
    for i, (path, dur, kind) in enumerate(segments):
        vf = (f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
              f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps}")
        if dim_arc:
            b = max(DIM_BRIGHTNESS_FLOOR, -dim_brightness_step * i)
            vf += f",eq=brightness={b:.4f}"
        vf += f",format={PIX_FMT}[v{i}]"
        filt.append(vf)

        if needs_silence[i]:
            a_input = n + silent_order.index(i)
            af = f"[{a_input}:a]aformat=sample_fmts=fltp:sample_rates={A_RATE}:channel_layouts=stereo"
        else:
            af = f"[{i}:a]{loudnorm_filter(path)},aresample={A_RATE}"
        # 🔴 atempo stretches the audio and the atrim below then cuts it back to the
        # segment's video duration — so whatever this touches loses its LAST ~(1/t - 1)
        # of musical content. Harmless on a looped ambient bed, a silent edit on a
        # published song. Scope defaults to interludes for exactly that reason.
        tempo_ok = (dim_tempo_scope == "all"
                    or (dim_tempo_scope == "interlude" and kind == "interlude"))
        if dim_arc and tempo_ok:
            t = max(DIM_TEMPO_FLOOR, 1.0 - dim_tempo_step * i)
            af += f",atempo={t:.4f}"
        # Conform every segment's audio to exactly its own video's duration so
        # the crossfade offset math (computed off `durs`, the VIDEO truth) never drifts.
        af += (f",atrim=0:{dur:.3f},apad,atrim=0:{dur:.3f},"
               f"aformat=sample_fmts=fltp:sample_rates={A_RATE}:channel_layouts=stereo[a{i}]")
        filt.append(af)

    if n == 1:
        filt.append(f"[v0]copy[vout]")
        filt.append(f"[a0]copy[aout]")
    else:
        prev_v, prev_a = "[v0]", "[a0]"
        for i in range(1, n):
            # With per-join crossfades the offset is the running timeline length so far,
            # i.e. everything played minus every overlap CONSUMED SO FAR — not i*xfade.
            xf = xfades[i - 1]
            off = sum(durs[:i]) - sum(xfades[:i])
            if off < 0:
                sys.exit(f"!! segment {i}: xfade={xf}s is longer than the preceding "
                         f"segment(s) allow (offset would go negative) — shorten xfade or segments")
            vlbl = "[vout]" if i == n - 1 else f"[vx{i}]"
            albl = "[aout]" if i == n - 1 else f"[ax{i}]"
            filt.append(f"{prev_v}[v{i}]xfade=transition=fade:duration={xf}:offset={off:.3f}{vlbl}")
            filt.append(f"{prev_a}[a{i}]acrossfade=d={xf}:curve1=tri:curve2=tri{albl}")
            prev_v, prev_a = vlbl, albl

    # §3 mastering formula's ceiling — tame the joined peaks. amix's normalize=0
    # gotcha doesn't apply here (no amix, acrossfade already sums correctly).
    filt.append(f"[aout]alimiter=limit={ALIMITER}[aout_lim]")

    cmd = [FFMPEG, "-y"] + inputs + [
        "-filter_complex", ";".join(filt),
        "-map", "[vout]", "-map", "[aout_lim]",
        *venc(str(crf), preset),
        "-pix_fmt", PIX_FMT, "-r", fps,
        "-c:a", "aac", "-b:a", A_BITRATE, "-ar", str(A_RATE), "-ac", str(A_CH),
        "-movflags", "+faststart", out_path]
    try:
        run(cmd)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    verify_media(out_path, "raw compilation")

    total = sum(durs) - sum(xfades) if n > 1 else durs[0]
    actual = probe_dur(out_path)
    print(f".. raw compilation: {total:.2f}s predicted / {actual:.2f}s actual "
          f"({n} segments, {len(xfades)} joins, xfade {xf_desc})")
    if abs(actual - total) > 1.0:
        print(f"!! predicted and actual differ by {actual - total:+.2f}s — the offset "
              f"math and ffmpeg disagree; check before shipping")
    return out_path


def add_bookends(channel, raw_path, out_path):
    """Compose intro/outro via add_bookends.py rather than reimplementing it."""
    script = os.path.join(HERE, "add_bookends.py")
    cmd = [sys.executable, script, "--channel", channel, "--episode", raw_path, "--out", out_path]
    try:
        run(cmd)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    verify_media(out_path, "final bookended compilation")


def main():
    ap = argparse.ArgumentParser(description="Bind a channel's episodes into one long-form compilation.")
    ap.add_argument("--channel", required=True, help="channel slug, e.g. pip-moonlit-garden")
    ap.add_argument("--spec", required=True, help="comp.json (segments + xfade + dim_arc + end_on_last_frame)")
    ap.add_argument("--out", required=True, help="output mp4")
    ap.add_argument("--skip-bookends", action="store_true",
                     help="write the raw joined compilation straight to --out (no intro/outro); "
                          "useful for a dry run before bookends exist")
    ap.add_argument("--crf", default="19")
    ap.add_argument("--preset", default="medium")
    args = ap.parse_args()

    spec = json.load(open(args.spec))
    if "segments" not in spec or not spec["segments"]:
        sys.exit("!! spec has no segments")

    xfade = float(spec.get("xfade", DEFAULT_XFADE))
    xfade_ramp = spec.get("xfade_ramp")
    if xfade_ramp and len(xfade_ramp) != 2:
        sys.exit("!! xfade_ramp must be [first_join_seconds, last_join_seconds]")
    dim_arc = bool(spec.get("dim_arc", False))
    dim_tempo_scope = spec.get("dim_tempo_scope", "interlude")
    if dim_tempo_scope not in ("interlude", "all", "none"):
        sys.exit(f"!! dim_tempo_scope must be interlude|all|none, got {dim_tempo_scope!r}")
    end_on_last_frame = bool(spec.get("end_on_last_frame", True))
    if not end_on_last_frame:
        print("!! end_on_last_frame=false requested, but this generator never truncates with "
              "-shortest anyway — the final segment always plays out fully")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="compilation_")
    try:
        segments = resolve_segments(spec, tmp)
        print(f".. {len(segments)} segments resolved: "
              + ", ".join(f"{k}({d:.1f}s)" for _, d, k in segments))
        xfades = resolve_xfades(len(segments), xfade, xfade_ramp)

        dim_kw = {
            "dim_tempo_scope": dim_tempo_scope,
            "dim_brightness_step": spec.get("dim_brightness_step"),
            "dim_tempo_step": spec.get("dim_tempo_step"),
        }
        if args.skip_bookends:
            build_compilation(segments, xfades, dim_arc, args.out, args.crf, args.preset,
                              **dim_kw)
        else:
            raw = os.path.join(tmp, "raw_compilation.mp4")
            build_compilation(segments, xfades, dim_arc, raw, args.crf, args.preset, **dim_kw)
            add_bookends(args.channel, raw, args.out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total = probe_dur(args.out)
    print(f">> DONE: {args.out}  ({total:.2f}s = {int(total//60)}m{total%60:04.1f}s, "
          f"{len(spec['segments'])} segments, "
          f"xfade={'%.2f→%.2f' % (xfades[0], xfades[-1]) if xfades else 'n/a'}s, "
          f"dim_arc={dim_arc}, bookends={'skipped' if args.skip_bookends else 'applied'})")


if __name__ == "__main__":
    main()
