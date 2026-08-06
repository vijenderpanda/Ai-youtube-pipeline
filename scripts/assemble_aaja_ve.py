#!/usr/bin/env python3
"""Aashiqana song #02 'Aaja Ve' — story-driven assembler.

Unlike the song #01 montage cycler, shots are pinned to song sections derived from
the forced-aligned karaoke timing, so the narrative (apart → memory → reunion)
lands on the right lyric. Frame zero holds the S09 thumbnail-quality frame (custom
thumbnail push is blocked on phone-verify, so the auto-thumb source must be premium).

Usage:
  python3 scripts/assemble_aaja_ve.py [--res 1920x1080] [--xfade 0.7]
"""
import argparse, json, os, subprocess

BASE = "channels/aashiqana/songs/02-aaja-ve"
FIN = f"{BASE}/scenes/stills_final"
CLIPS = f"{BASE}/renders/clips"
SONG = f"{BASE}/track/aaja_ve_final.mp3"

# display-line index ranges per section (27 aligned display lines)
SECTIONS = [
    ("chorus1", 0, 4),
    ("verse1", 5, 8),
    ("chorus2", 9, 13),
    ("verse2", 14, 17),
    ("bridge", 18, 19),
    ("chorus3", 20, 24),
    ("outro", 25, 26),
]
# shots per section: (id, kind, source, kb_direction)
# long chorus sections carry QC-passed alternates as extra coverage (anti-templating: fresh frames)
V2 = f"{BASE}/scenes/stills_v2"
V1 = f"{BASE}/scenes/stills"
FIX = f"{BASE}/scenes/stills_fix"
PLAN = {
    "chorus1": [("S01", "motion", f"{CLIPS}/s01_motion.mp4", None),
                ("S02", "kb", f"{FIN}/S02.jpg", "in"),
                ("S01b", "kb", f"{V2}/s01_1.jpg", "out")],
    "verse1":  [("S03", "kb", f"{FIN}/S03.jpg", "out"),
                ("S04", "kb", f"{FIN}/S04.jpg", "in")],
    "chorus2": [("S05", "kb", f"{FIN}/S05.jpg", "in"),
                ("S06", "kb", f"{FIN}/S06.jpg", "out"),
                ("S06b", "kb", f"{V1}/s06_1.jpg", "in"),
                ("S05b", "kb", f"{V2}/s05_0.jpg", "out")],
    "verse2":  [("S07", "motion", f"{CLIPS}/s07_motion.mp4", None),
                ("S08", "kb", f"{FIN}/S08.jpg", "in"),
                ("S09", "kb", f"{FIN}/S09_THUMB.jpg", "in")],
    "bridge":  [("S10a", "kb", f"{V2}/s10_1.jpg", "in"),
                ("S10", "motion", f"{CLIPS}/s10_motion.mp4", None)],
    "chorus3": [("S11", "motion", f"{CLIPS}/s11_motion.mp4", None),
                ("S11b", "kb", f"{FIN}/S11.jpg", "in"),
                ("S11c", "kb", f"{FIX}/cinematic-medium-two-shot-beside-a-r_368d3822_1.jpg", "out"),
                ("S11d", "kb", f"{V2}/s11_1.jpg", "in")],
    "outro":   [("S12", "motion", f"{CLIPS}/s12_motion.mp4", None)],
}
THUMB_HOLD = 1.3   # S09 premium frame at t=0
MOTION_CAP = 9.0   # max seconds a 5.9s Hailuo clip can stretch (1.55x slow) before freezing


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(r.stdout.strip())


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(p.stderr[-1500:])


def norm_motion(src, dst, dur, W, H, FPS):
    """Scale/pad to WxH; if dur exceeds clip length, slow down up to 1.6x then hold last frame."""
    nat = probe(src) - 0.05
    speed = min(1.6, max(1.0, dur / nat))
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"setpts={speed:.4f}*PTS,fps={FPS},tpad=stop_mode=clone:stop_duration=3")
    run(["ffmpeg", "-y", "-i", src, "-vf", vf, "-t", f"{dur:.3f}", "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", dst])


def ken_burns(src, dst, dur, direction, W, H, FPS):
    frames = int(dur * FPS)
    if direction == "in":
        z = f"min(zoom+0.0006,1.18)"
    else:
        z = f"if(lte(zoom,1.0),1.18,max(zoom-0.0006,1.0))"
    vf = (f"scale=3200:-2,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s={W}x{H}:fps={FPS}")
    run(["ffmpeg", "-y", "-loop", "1", "-i", src, "-vf", vf, "-t", f"{dur:.3f}", "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", dst])


def still_hold(src, dst, dur, W, H, FPS):
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}"
    run(["ffmpeg", "-y", "-loop", "1", "-i", src, "-vf", vf, "-t", f"{dur:.3f}", "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", dst])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--xfade", type=float, default=0.7)
    ap.add_argument("--out", default=f"{BASE}/renders/aaja_ve_base.mp4")
    a = ap.parse_args()
    W, H = map(int, a.res.split("x")); FPS = a.fps; T = a.xfade

    lines = json.load(open(f"{BASE}/lyrics/timing_karaoke.json"))["lines"]
    song_dur = probe(SONG)
    work = f"{BASE}/renders/work"; os.makedirs(work, exist_ok=True)

    # section windows from aligned lines; each window ends where the next begins
    bounds = []
    for i, (name, s_idx, e_idx) in enumerate(SECTIONS):
        start = lines[s_idx]["s"]
        end = lines[SECTIONS[i + 1][1]]["s"] if i + 1 < len(SECTIONS) else song_dur
        bounds.append((name, start, end))
    print("sections:", [(n, round(s, 1), round(e, 1)) for n, s, e in bounds])

    # timeline: opening thumbnail hold from 0 -> chorus1 shots start at their window
    segs = []  # (label, path, alloc)
    first_start = max(THUMB_HOLD + 0.4, bounds[0][1])
    segs.append(("S09_open", f"{FIN}/S09_THUMB.jpg", "hold", first_start))
    for i, (name, start, end) in enumerate(bounds):
        shots = PLAN[name]
        seg_start = first_start if i == 0 else start
        dur = end - seg_start
        # motion segments cap at MOTION_CAP; Ken Burns shots absorb the remainder equally
        n_motion = sum(1 for s in shots if s[1] == "motion")
        n_kb = len(shots) - n_motion
        equal = dur / len(shots)
        m_alloc = min(MOTION_CAP, equal) if n_motion else 0
        kb_alloc = (dur - m_alloc * n_motion) / n_kb if n_kb else dur / max(1, n_motion)
        if not n_kb:
            m_alloc = dur / n_motion
        for sid, kind, src, kb in shots:
            alloc = m_alloc if kind == "motion" else kb_alloc
            segs.append((sid, src, kind if kind != "kb" else kb, alloc))

    # render normalized segments (xfade eats T at each junction -> pad every non-final seg)
    pool = []
    for j, (sid, src, mode, alloc) in enumerate(segs):
        d = alloc + (T if j < len(segs) - 1 else 0)
        dst = f"{work}/{j:02d}_{sid}.mp4"
        if mode == "hold":
            still_hold(src, dst, d, W, H, FPS)
        elif mode == "motion":
            norm_motion(src, dst, d, W, H, FPS)
        else:
            ken_burns(src, dst, d, mode, W, H, FPS)
        pool.append(dst)
        print(f"seg {j:02d} {sid:9s} {d:5.2f}s {mode}")

    inputs = []
    for p in pool:
        inputs += ["-i", p]
    fc = []; prev = "0:v"; acc = probe(pool[0])
    for k in range(1, len(pool)):
        off = acc - T
        fc.append(f"[{prev}][{k}:v]xfade=transition=fade:duration={T}:offset={off:.3f}[v{k}]")
        prev = f"v{k}"; acc = acc + probe(pool[k]) - T
    fade_st = max(0, song_dur - 4)
    cmd = (["ffmpeg", "-y"] + inputs + ["-i", SONG,
           "-filter_complex", ";".join(fc), "-map", f"[{prev}]", "-map", f"{len(pool)}:a",
           "-af", f"afade=t=out:st={fade_st:.2f}:d=4",
           "-t", f"{song_dur:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out])
    print("rendering base cut...")
    run(cmd)
    print(">> DONE", a.out, f"{probe(a.out):.1f}s")


if __name__ == "__main__":
    main()
