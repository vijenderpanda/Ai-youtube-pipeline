#!/usr/bin/env python3
"""Aaja Ve "OUT NOW" glimpse Short — 9:16 derivative cut of an already-released song.

Grammar (deliberately NOT the live Short's full-bleed centre crop, playbook §15):
  * every shot is a 1080x1200 "lyric band" at y=250 over a blurred/darkened cover-scale
    of the same frame -> ~46% of the source width survives instead of ~32%, and the
    470px below the band is a permanent caption zone, so karaoke never sits on the couple
  * per-join transition is per-shot (`xf`): the glimpse montage hard-cuts (xf 0), the
    cards dissolve. A flash montage crossfaded reads as a slideshow, not a glimpse.
  * frame-zero card == end-frame card, so the cut loops back into its own cold open.

Audio: the mix for the vocal beats, then a linear crossfade to the LOW-PASSED demucs
`no_vocals` stem of the SAME timeline window for the end cards -- so the "duck" is the
identical bar with the vocal lifted out, not a different piece of music. Two-pass
loudnorm to -14 LUFS / -1.5 TP on the lossless wav before muxing (a cut taken from a
late chorus arrives hotter than one taken from the top of the song).

Video slowdown uses `minterpolate` (mci/aobmc) BEFORE setpts: the hero clips are 24fps
and 5.875s, so a plain setpts stretch to 8.3s would present ~17 unique fps at 30 and
judder. Interpolating to 60 first leaves every output frame unique.

Usage:
  python3 scripts/assemble_short_aaja_ve_outnow.py --config <cut.json> --out base.mp4
"""
import argparse, json, os, subprocess, sys

W, H, FPS = 1080, 1920, 30
BAND_W, BAND_H, BAND_Y = 1080, 1200, 250
PAN = 1.10                     # pre-upscale -> pan headroom inside the band
GOLD_HAIRLINE = "0xF0C45C@0.30"


def run(cmd, what):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(f"\n--- {what} failed ---\n" + p.stderr[-2500:] + "\n")
        raise SystemExit(1)
    return p


def probe(path, entry="format=duration"):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entry,
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    return r.stdout.strip().splitlines()


def dims(path):
    o = probe(path, "stream=width,height")
    return int(o[0]), int(o[1])


def band_geometry(sw, sh):
    s = max(BAND_W / sw, BAND_H / sh) * PAN
    return int(round(sw * s)) // 2 * 2, int(round(sh * s)) // 2 * 2


def drift_expr(scaled, band, center, delta, dur):
    """Linear crop-window translation, clamped to the scaled frame."""
    span = scaled - band
    if span <= 0:
        return "0"
    c = center * scaled - band / 2
    a = max(0.0, min(span, c - delta / 2.0))
    b = max(0.0, min(span, c + delta / 2.0))
    return f"{a:.2f}+({b - a:.2f})*min(1,t/{dur:.3f})"


def build_segment(shot, work, idx):
    """One 1080x1920 band-on-blur segment."""
    src, dur = shot["src"], shot["dur"]
    kind = shot.get("kind", "still")
    sw, sh = dims(src)
    gw, gh = band_geometry(sw, sh)
    out = os.path.join(work, f"seg{idx:02d}.mp4")

    bg = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"boxblur=40:2,eq=brightness=-0.20:saturation=0.72:contrast=1.02,"
          f"format=yuv420p,setsar=1")

    # Every chain ends in tpad+`-t dur`. zoompan and minterpolate both land a frame or
    # three SHORT of the requested length, and a segment shorter than the offset the
    # xfade chain was built from silently truncates the whole cut at that join -- the
    # first build lost every shot after the cold open and still reported 20.00s, because
    # the container took its duration from the audio.
    pad = f"tpad=stop_mode=clone:stop_duration=1.0,"
    # JPEG-backed shots decode as FULL range and x264 tags them yuvj420p, while the
    # video-backed shot is yuv420p. Concat them and the pixel format CHANGES mid-stream;
    # `xfade` is configured once for the first format and silently emits nothing from the
    # switch onward -- the cut died at 8.7s of 20.1s and still reported the right duration.
    # Pin every segment to limited range so the whole cut is one format.
    rng = "scale=in_range=auto:out_range=tv,"
    ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-color_range", "tv"]

    if kind == "card":
        # cards are pre-composed full-canvas plates -- no band, no grade
        fc = (f"[0:v]scale={W}:{H},setsar=1,fps={FPS},{pad}{rng}format=yuv420p[v]")
        ins = ["-loop", "1", "-t", f"{dur + 1.0:.3f}", "-i", src]
        run(["ffmpeg", "-y", "-v", "error"] + ins +
            ["-filter_complex", fc, "-map", "[v]", "-an", "-t", f"{dur:.3f}",
             *ENC, out], f"card {idx}")
        return out

    if kind == "still":
        z0, z1 = shot.get("zoom", [1.0, 1.07])
        frames = max(2, int(round(dur * FPS)))
        ss_w, ss_h = gw * 2, gh * 2
        cx, cy = shot.get("cx", 0.5), shot.get("cy", 0.5)
        band = (f"scale={ss_w}:{ss_h}:flags=lanczos,"
                f"zoompan=z='{z0}+({z1 - z0})*on/{frames - 1}':d={frames}:s={gw}x{gh}:fps={FPS}"
                f":x='iw/2-(iw/zoom/2)+({cx - 0.5:.4f})*iw/zoom'"
                f":y='ih/2-(ih/zoom/2)+({cy - 0.5:.4f})*ih/zoom',"
                f"crop={BAND_W}:{BAND_H}:{(gw - BAND_W) // 2}:{(gh - BAND_H) // 2},setsar=1")
        src_in = ["-loop", "1", "-t", f"{dur + 1.0:.3f}", "-i", src]
        bg_in = ["-loop", "1", "-t", f"{dur + 1.0:.3f}", "-i", src]
    else:                                            # motion clip
        sdur = float(probe(src)[0])
        take = min(sdur, shot.get("take", sdur))
        pre = ""
        if dur > take + 0.02:
            # true slow-motion: synthesise frames first, THEN stretch time
            pre = (f"minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
                   f"setpts={dur / take:.5f}*PTS,")
        dx, dy = shot.get("drift", [0, 60])
        xe = drift_expr(gw, BAND_W, shot.get("cx", 0.5), dx, dur)
        ye = drift_expr(gh, BAND_H, shot.get("cy", 0.5), dy, dur)
        band = (f"{pre}scale={gw}:{gh}:flags=lanczos,fps={FPS},"
                f"crop={BAND_W}:{BAND_H}:'{xe}':'{ye}',setsar=1")
        src_in = ["-t", f"{take:.3f}", "-i", src]
        bg_in = ["-t", f"{take:.3f}", "-i", src]
        if pre:
            bg = pre + bg

    edge = (f"drawbox=x=0:y={BAND_Y}:w={W}:h=2:color={GOLD_HAIRLINE}:t=fill,"
            f"drawbox=x=0:y={BAND_Y + BAND_H - 2}:w={W}:h=2:color={GOLD_HAIRLINE}:t=fill")
    fc = (f"[0:v]{bg}[bg];[1:v]{band}[bd];"
          f"[bg][bd]overlay=0:{BAND_Y}:eof_action=endall,{edge},"
          f"fps={FPS},{pad}{rng}format=yuv420p[v]")
    run(["ffmpeg", "-y", "-v", "error"] + bg_in + src_in +
        ["-filter_complex", fc, "-map", "[v]", "-an", "-t", f"{dur:.3f}",
         *ENC, out], f"segment {idx}")
    return out


def build_audio(cfg, total, work):
    """Mix window -> linear crossfade -> low-passed no_vocals of the SAME window."""
    a = cfg["audio"]
    st, duck, xf = a["start"], a["duck_at"], a.get("duck_xf", 0.5)
    mix, stem = os.path.join(work, "a_mix.wav"), os.path.join(work, "a_stem.wav")
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{st}", "-t", f"{total:.3f}",
         "-i", a["mix"], "-ac", "2", "-ar", "48000", mix], "audio mix slice")
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{st}", "-t", f"{total:.3f}",
         "-i", a["stem"], "-af", f"lowpass=f={a.get('lowpass', 820)}:poles=2,volume=-1.5dB",
         "-ac", "2", "-ar", "48000", stem], "audio stem slice")

    joined = os.path.join(work, "a_joined.wav")
    tail = a.get("tail_fade", 0.55)
    fc = (f"[0:a]afade=t=out:st={duck:.3f}:d={xf:.3f}[m];"
          f"[1:a]afade=t=in:st={duck:.3f}:d={xf:.3f}[s];"
          f"[m][s]amix=inputs=2:normalize=0,"
          f"afade=t=in:st=0:d=0.04,afade=t=out:st={total - tail:.3f}:d={tail:.3f}[a]")
    run(["ffmpeg", "-y", "-v", "error", "-i", mix, "-i", stem,
         "-filter_complex", fc, "-map", "[a]", joined], "audio join")

    # two-pass loudnorm on the lossless wav (never re-encode video to fix audio)
    m = run(["ffmpeg", "-y", "-v", "info", "-i", joined,
             "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
             "-f", "null", "-"], "loudnorm measure").stderr
    js = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    print(f"   loudnorm pass1: I={js['input_i']} TP={js['input_tp']} LRA={js['input_lra']}")
    final = os.path.join(work, "a_final.wav")
    run(["ffmpeg", "-y", "-v", "error", "-i", joined, "-af",
         f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:"
         f"measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
         f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true",
         "-ar", "48000", final], "loudnorm apply")
    return final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=None)
    a = ap.parse_args()

    cfg = json.load(open(a.config))
    shots = cfg["shots"]
    work = a.work or os.path.join(os.path.dirname(a.out), "_work")
    os.makedirs(work, exist_ok=True)

    # A hard cut is NOT a very short xfade. Forcing one through xfade puts
    # offset+duration exactly on the end of the incoming chain, and xfade then has no
    # frames left to blend -- it emits nothing and every later shot vanishes, while the
    # container still reports the audio's full length. So: consecutive shots joined by
    # `xf: 0` are CONCATENATED into one group, and xfade is used only for real dissolves.
    groups, cur = [], [0]
    for k in range(1, len(shots)):
        if shots[k].get("xf", 0.0) > 0:
            groups.append(cur); cur = [k]
        else:
            cur.append(k)
    groups.append(cur)

    total = sum(s["dur"] for s in shots) - sum(shots[g[0]]["xf"] for g in groups[1:])
    print(f"timeline {total:.2f}s over {len(shots)} shots in {len(groups)} groups")

    segs = [build_segment(s, work, i) for i, s in enumerate(shots)]
    for s, seg in zip(shots, segs):
        got = float(probe(seg)[0])
        if abs(got - s["dur"]) > 1.5 / FPS:
            raise SystemExit(f"{seg}: {got:.3f}s but the timeline wants {s['dur']:.3f}s "
                             f"-- a short segment truncates the chain at its join")
    audio = build_audio(cfg, total, work)

    gfiles, gdurs = [], []
    for gi, g in enumerate(groups):
        gd = sum(shots[i]["dur"] for i in g)
        gdurs.append(gd)
        if len(g) == 1:
            gfiles.append(segs[g[0]]); continue
        # concat FILTER, not the concat demuxer. The demuxer + `-c copy` produces a file
        # that plays and probes correctly (right frame count, right duration) but whose
        # timestamps make a downstream `xfade` stop emitting at the first segment
        # boundary -- measured 262 frames out of 603, with no warning from ffmpeg.
        gf = os.path.join(work, f"group{gi}.mp4")
        ins, labs = [], ""
        for n, i in enumerate(g):
            ins += ["-i", segs[i]]
            labs += f"[{n}:v]"
        run(["ffmpeg", "-y", "-v", "error"] + ins +
            ["-filter_complex", f"{labs}concat=n={len(g)}:v=1:a=0[c]", "-map", "[c]", "-an",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-color_range", "tv",
             gf], f"concat group {gi}")
        got = float(probe(gf)[0])
        if abs(got - gd) > 1.5 / FPS:
            raise SystemExit(f"{gf}: {got:.3f}s but the group should be {gd:.3f}s")
        gfiles.append(gf)

    inputs, fc, prev, acc = [], [], "0:v", gdurs[0]
    for f in gfiles:
        inputs += ["-i", f]
    for k in range(1, len(gfiles)):
        xf = shots[groups[k][0]]["xf"]
        off = acc - xf
        fc.append(f"[{prev}][{k}:v]xfade=transition=fade:duration={xf:.4f}:"
                  f"offset={off:.4f}[x{k}]")
        print(f"   dissolve into group {k} at {off:.2f}s (xf {xf:.2f}s)")
        prev = f"x{k}"
        acc = off + gdurs[k]
    at = 0.0
    for gi, g in enumerate(groups):                      # real timeline position per shot
        if gi:
            at -= shots[g[0]]["xf"]
        for i in g:
            print(f"   shot {i} ({'diss' if i == g[0] and gi else 'cut' if i != g[0] else 'open'})"
                  f" at {at:.2f}s  {shots[i].get('_beat', '')[:46]}")
            at += shots[i]["dur"]

    ai = len(gfiles)
    run(["ffmpeg", "-y", "-v", "error"] + inputs + ["-i", audio,
         "-filter_complex", ";".join(fc), "-map", f"[{prev}]", "-map", f"{ai}:a",
         "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-color_range", "tv", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", a.out], "assemble")

    # the container takes its duration from the LONGEST stream, so a truncated video
    # chain still reports the audio's length -- count video frames, not duration
    n = int(probe(a.out, "stream=nb_read_frames")[0].replace("N/A", "0") or 0) or int(
        subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_read_frames", "-of",
                        "default=nw=1:nk=1", a.out], capture_output=True,
                       text=True).stdout.strip())
    want = int(round(total * FPS))
    print(f">> DONE {a.out}  {float(probe(a.out)[0]):.2f}s  "
          f"video {n} frames (predicted {want})")
    if abs(n - want) > 2:
        raise SystemExit(f"video chain is {want - n} frames short of the timeline")


if __name__ == "__main__":
    main()
