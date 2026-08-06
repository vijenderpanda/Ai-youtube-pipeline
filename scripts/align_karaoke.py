#!/usr/bin/env python3
"""Forced-align sung Hindi lyrics to a demucs vocal stem and emit karaoke line windows.

The locked pipeline (playbook §4, validated on Aashiqana song #01):
  1. stable-ts `align()` on the vocal stem with Devanagari text (whisper tokenizes
     Hindi script far better than Latin), then chunk the aligned WORDS back into the
     split display phrases by word count -> each phrase gets its own honest [s,e].
  2. ONSET-SNAP each start to the nearest VAD vocal onset within --onset-snap-window,
     guarded so a snap can never cross the previous line's end. This kills the ~2s
     interpolation error the aligner introduces right after instrumental gaps.
  3. SWEEP-CAP each end: e = min(aligned_e, next_s - --gap, s + --sweep-cap), so a
     line the aligner stretched across a break doesn't crawl and gaps show NOTHING.
  4. Optional --final-cap hand-caps the last displayed line so its gold fill completes
     before an end card crossfades in (a sweep running over a title card reads as a bug).

Usage:
  python3 scripts/align_karaoke.py --vocals vocals.wav --lyrics lyrics.md \
      --out timing_karaoke.json --model small [--final-cap 27.9 --card-start 28.4]
`lyrics.md` must contain "## Lyrics (romanized" and "## Lyrics (Devanagari" sections
whose non-tag lines correspond 1:1. Lines in (parentheses) are aligned but not displayed
-- they act as a sink for sustained tails so the aligner doesn't stretch the last real
line to the end of the cut.
"""
import argparse, json, os, re

MIN_LINE = 0.5      # a sweep shorter than this reads as a flicker


def section_lines(md, header_prefix):
    """Lyric lines from a '## Lyrics (<kind>...)' section. If the section wraps its
    lyrics in a fenced block, take ONLY the fence — sheets carry prose notes after it."""
    m = re.search(rf"## Lyrics \({header_prefix}.*?\n(.*?)(?=\n## |\Z)", md, re.S)
    body = m.group(1)
    fence = re.search(r"```[^\n]*\n(.*?)```", body, re.S)
    if fence:
        body = fence.group(1)
    lines = []
    for ln in body.strip().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("[") or ln.startswith("`"):
            continue
        lines.append(ln)
    return lines


VAD_THRESHOLDS = (0.5, 0.35)  # union: 0.5 alone misses attacks buried in reverb tails


def vad_onsets(wav_path):
    """Silero-VAD speech onsets (seconds).

    speech_pad_ms=0 so an onset is the TRUE attack, not a padded one; short
    min_silence so breath gaps between sung phrases still produce their own onset.
    Sung vocals with heavy reverb sit far below speech confidence at threshold 0.5 --
    on the Aashiqana hook that alone lost two attacks later confirmed by RMS steps --
    so onsets are the UNION over several thresholds, deduped at 0.05s."""
    from faster_whisper.audio import decode_audio
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    audio = decode_audio(wav_path, sampling_rate=16000)
    found = []
    for th in VAD_THRESHOLDS:
        opts = VadOptions(threshold=th, min_speech_duration_ms=120,
                          min_silence_duration_ms=120, speech_pad_ms=0)
        found += [t["start"] / 16000.0 for t in get_speech_timestamps(
            audio, opts, sampling_rate=16000)]
    out = []
    for o in sorted(found):
        if not out or o - out[-1] > 0.05:
            out.append(round(o, 2))
    return out


def realign_isolated(model, wav_path, text, t0, t1):
    """Re-align one line's text ALONE over [t0, t1] and return its start.

    Used only where VAD offers no onset at all: inside a continuous sung wash (a held
    vowel + reverb never falls below the speech floor, so there is no attack to snap
    to) the whole-cut alignment has nothing to anchor against and interpolates the
    line late. Realigning the fragment in isolation removes the pull of the
    neighbouring segments. Returns None if it fails."""
    import soundfile as sf, tempfile, os as _os
    from faster_whisper.audio import decode_audio
    audio = decode_audio(wav_path, sampling_rate=16000)
    clip = audio[int(t0 * 16000):int(t1 * 16000)]
    tmp = _os.path.join(tempfile.gettempdir(), "_realign_isolated.wav")
    sf.write(tmp, clip, 16000)
    try:
        r = model.align(tmp, text, language="hi", original_split=True)
        ws = r.all_words()
        if not ws:
            return None
        return float(ws[0].start) + t0
    except Exception as ex:
        print(f"!! isolated re-align failed: {ex}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocals", required=True)
    ap.add_argument("--lyrics", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="small")  # NOT medium: >10min timeout on CPU
    ap.add_argument("--onset-snap-window", type=float, default=2.5)
    ap.add_argument("--sweep-cap", type=float, default=6.5)
    ap.add_argument("--gap", type=float, default=0.2, help="clearance before next line's start")
    ap.add_argument("--final-cap", type=float, default=None,
                    help="hard cap on the last displayed line's end (end-card guard)")
    ap.add_argument("--card-start", type=float, default=None, help="documentation only")
    ap.add_argument("--note-prefix", default="")
    a = ap.parse_args()

    md = open(a.lyrics, encoding="utf-8").read()
    roman = section_lines(md, "roman")
    deva = section_lines(md, "Devanagari")
    assert len(roman) == len(deva), f"line mismatch: {len(roman)} roman vs {len(deva)} deva"

    def sung_text(ln):
        ln = re.sub(r"\(female echo:\s*", "", ln)
        return ln.replace("(", "").replace(")", "").strip()

    deva_sung = [sung_text(l) for l in deva]
    flat = "\n".join(deva_sung)

    import stable_whisper
    model = stable_whisper.load_faster_whisper(a.model)  # weights cached from song #01
    result = model.align(a.vocals, flat, language="hi", original_split=True)
    segs = result.segments
    words = result.all_words()
    counts = [len(l.split()) for l in deva_sung]
    print(f"aligned {len(segs)} segments / {len(words)} words for {len(deva_sung)} lines "
          f"(expected {sum(counts)} words)")

    # --- chunk aligned words back into the split display phrases by word count ---
    raw = []
    if len(words) == sum(counts):
        k = 0
        for n in counts:
            grp = words[k:k + n]
            k += n
            raw.append((float(grp[0].start), float(grp[-1].end)))
    else:
        print("!! word-count mismatch -> falling back to segment boundaries")
        assert len(segs) == len(deva_sung), f"{len(segs)} segments vs {len(deva_sung)} lines"
        raw = [(float(s.start), float(s.end)) for s in segs]

    # --- (2) onset-snap starts to the nearest VAD onset, guarded ---
    onsets = vad_onsets(a.vocals)
    print(f"VAD onsets: {onsets}")
    dur = raw[-1][1]
    snapped, prev_end, how = [], -1e9, []
    for i, (s, e) in enumerate(raw):
        # guard: a snap can never cross the previous line's end, nor its own end
        cands = [o for o in onsets
                 if abs(o - s) <= a.onset_snap_window and o > prev_end and o < e]
        if cands:
            ns, tag = min(cands, key=lambda o: abs(o - s)), "vad"
        else:
            ns, tag = s, "kept"
            rs = realign_isolated(model, a.vocals, deva_sung[i], max(0.0, prev_end), dur)
            if rs is not None and prev_end < rs < e and abs(rs - s) <= a.onset_snap_window:
                ns, tag = rs, "realign"
        snapped.append((ns, e, s))
        how.append(tag)
        prev_end = e

    # --- (3) sweep-cap ends; (4) drop non-display lines ---
    lines_out, deltas = [], []
    for i, (s, e, aligned_s) in enumerate(snapped):
        nxt = snapped[i + 1][0] if i + 1 < len(snapped) else None
        capped = min(e, s + a.sweep_cap)
        if nxt is not None:
            capped = min(capped, nxt - a.gap)
        if capped - s < MIN_LINE:
            capped = s + MIN_LINE
        if roman[i].startswith("("):
            continue  # echo/ad-lib: aligned as a sink for the sustained tail, not displayed
        lines_out.append({"s": round(s, 2), "e": round(capped, 2), "text": roman[i]})
        deltas.append([aligned_s, s, e, capped, how[i], roman[i]])

    # --- (4) hand-cap the final displayed line before the end card ---
    if a.final_cap is not None and lines_out:
        last = lines_out[-1]
        if last["e"] > a.final_cap:
            last["e"] = round(a.final_cap, 2)
            deltas[-1][3] = a.final_cap

    src = os.path.splitext(os.path.basename(a.lyrics))[0]
    note = (f"{a.note_prefix}{src} — stable-ts load_faster_whisper('{a.model}').align() on the demucs "
            f"vocal stem, Devanagari align text -> romanized display (1:1 by word count); "
            f"onset-snap to nearest silero-VAD onset (threshold union {VAD_THRESHOLDS}, "
            f"speech_pad 0) within {a.onset_snap_window:.1f}s "
            f"(guarded: a snap can never cross the previous line's end; a line with no "
            f"VAD onset at all is re-aligned in isolation over the remaining audio); "
            f"sweep-cap e = min(aligned_e, next_s-{a.gap:.1f}, s+{a.sweep_cap:.1f}); "
            f"MIN_LINE {MIN_LINE:.1f}s")
    if a.final_cap is not None:
        note += f"; final displayed line hand-capped to {a.final_cap:.2f}"
    if a.card_start is not None:
        note += f" so its gold fill completes before the end card crossfades in at {a.card_start:.2f}"
    note += ". Lines in (parens) are aligned as a tail sink and NOT displayed. Times are relative to the cut start."

    json.dump({"_note": note, "lines": lines_out},
              open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f">> wrote {a.out} with {len(lines_out)} display lines")
    print(f"{'aligned_s':>10} {'snapped_s':>10} {'delta':>7} {'via':>8} {'aligned_e':>10} {'final_e':>8}  text")
    for al_s, sn_s, al_e, fin_e, tag, txt in deltas:
        print(f"{al_s:10.2f} {sn_s:10.2f} {sn_s - al_s:+7.2f} {tag:>8} {al_e:10.2f} {fin_e:8.2f}  {txt}")


if __name__ == "__main__":
    main()
