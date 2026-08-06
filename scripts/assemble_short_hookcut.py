#!/usr/bin/env python3
"""
Hook-first 9:16 Shorts cut from an existing music-video release (zero new generation).

Re-frames already-approved 16:9 charref-locked shots into a vertical "lyric band"
composition instead of a hard centre crop:

    1080x1920 canvas
      backdrop : same frame, cover-scaled, heavy blur, darkened + desaturated
      band     : 1080x1200 at y=290 — a 0.9-aspect crop of the source, so ~51% of the
                 original frame width survives (a full-bleed 9:16 cover crop keeps only
                 ~32% and decapitates two-shots)
      dead zone: the 430px below the band is where the karaoke line lives — captions
                 never sit on the taught/tender content

Ken Burns is re-composed for vertical: the source is pre-upscaled 1.10x so the band crop
has pan headroom, then the crop window translates linearly (smooth — no zoompan jitter).
Stills get a real push-in via zoompan on a 2x supersample.

Usage:
  python3 scripts/assemble_short_hookcut.py --config <shots.json> --audio hook.wav \
      --out short_base.mp4 [--work DIR]
"""
import argparse, json, os, subprocess, sys

W, H, FPS = 1080, 1920, 30
BAND_W, BAND_H, BAND_Y = 1080, 1200, 250   # 470px of dead space below = the caption zone
PAN = 1.10          # pre-upscale factor -> pan headroom inside the band
XF = 0.55           # crossfade between shots


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
    """Scale the source so a BAND_W x BAND_H crop covers it, then add PAN headroom."""
    s = max(BAND_W / sw, BAND_H / sh) * PAN
    return int(round(sw * s)) // 2 * 2, int(round(sh * s)) // 2 * 2


def drift_expr(scaled, band, center, delta, dur):
    """Linear crop-window translation from (center-delta/2) to (center+delta/2), clamped."""
    span = scaled - band
    if span <= 0:
        return "0"
    c = center * scaled - band / 2
    a = max(0.0, min(span, c - delta / 2.0))
    b = max(0.0, min(span, c + delta / 2.0))
    return f"{a:.2f}+({b - a:.2f})*min(1,t/{dur:.3f})"


def build_segment(shot, dur, work, idx):
    """Render one 1080x1920 band-on-blur segment."""
    src = shot["src"]
    sw, sh = dims(src)
    gw, gh = band_geometry(sw, sh)
    out = os.path.join(work, f"seg{idx:02d}.mp4")
    is_still = shot.get("kind", "video") == "still"

    # --- backdrop: cover the whole canvas, blur it down to ambience ---
    bg = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"boxblur=40:2,eq=brightness=-0.20:saturation=0.72:contrast=1.02,"
          f"format=yuv420p,setsar=1")

    if is_still:
        # real Ken Burns: supersample, then zoompan push/pull inside the band
        z0, z1 = shot.get("zoom", [1.0, 1.07])
        frames = max(2, int(round(dur * FPS)))
        ss_w, ss_h = gw * 2, gh * 2
        zexpr = f"{z0}+({z1 - z0})*on/{frames - 1}"
        cx, cy = shot.get("cx", 0.5), shot.get("cy", 0.5)
        band = (f"scale={ss_w}:{ss_h}:flags=lanczos,"
                f"zoompan=z='{zexpr}':d={frames}:s={gw}x{gh}:fps={FPS}"
                f":x='iw/2-(iw/zoom/2)+({cx - 0.5:.4f})*iw/zoom'"
                f":y='ih/2-(ih/zoom/2)+({cy - 0.5:.4f})*ih/zoom',"
                f"crop={BAND_W}:{BAND_H}:{(gw - BAND_W) // 2}:{(gh - BAND_H) // 2},"
                f"setsar=1")
        src_in = ["-loop", "1", "-t", f"{dur:.3f}", "-i", src]
        bg_in = ["-loop", "1", "-t", f"{dur:.3f}", "-i", src]
    else:
        dx, dy = shot.get("drift", [0, 60])
        xe = drift_expr(gw, BAND_W, shot.get("cx", 0.5), dx, dur)
        ye = drift_expr(gh, BAND_H, shot.get("cy", 0.5), dy, dur)
        band = (f"scale={gw}:{gh}:flags=lanczos,fps={FPS},"
                f"crop={BAND_W}:{BAND_H}:'{xe}':'{ye}',setsar=1")
        src_in = ["-t", f"{dur:.3f}", "-i", src]
        bg_in = ["-t", f"{dur:.3f}", "-i", src]

    # gold hairline top+bottom of the band, at low alpha — frames the band as intentional
    edge = (f"drawbox=x=0:y={BAND_Y}:w={W}:h=2:color=0xF0C45C@0.30:t=fill,"
            f"drawbox=x=0:y={BAND_Y + BAND_H - 2}:w={W}:h=2:color=0xF0C45C@0.30:t=fill")

    fc = (f"[0:v]{bg}[bg];[1:v]{band}[bd];"
          f"[bg][bd]overlay=0:{BAND_Y}:eof_action=endall,{edge},"
          f"fps={FPS},format=yuv420p[v]")
    run(["ffmpeg", "-y", "-v", "error"] + bg_in + src_in +
        ["-filter_complex", fc, "-map", "[v]", "-an", "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", out], f"segment {idx}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=None)
    a = ap.parse_args()

    cfg = json.load(open(a.config))
    work = a.work or os.path.join(os.path.dirname(a.out), "_hookcut")
    os.makedirs(work, exist_ok=True)
    adur = float(probe(a.audio)[0])
    shots = cfg["shots"]
    card_d = float(cfg.get("card_dur", 1.2))
    card = cfg.get("card")

    # body must run to the end of the audio; the card xfades in over its last XF seconds
    body = adur - (card_d - XF) if card else adur
    fixed = sum(s["dur"] for s in shots if s.get("dur"))
    flex = [s for s in shots if not s.get("dur")]
    need = body + XF * (len(shots) - 1)
    if flex:
        share = (need - fixed) / len(flex)
        for s in flex:
            s["dur"] = share
    print(f"audio {adur:.2f}s · body {body:.2f}s · {len(shots)} shots "
          f"({', '.join(f'{s['dur']:.2f}' for s in shots)})")

    segs = [build_segment(s, s["dur"], work, i) for i, s in enumerate(shots)]

    inputs, fc, prev, acc = [], [], "0:v", shots[0]["dur"]
    for s in segs:
        inputs += ["-i", s]
    for k in range(1, len(segs)):
        off = acc - XF
        fc.append(f"[{prev}][{k}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}]")
        prev = f"x{k}"
        acc = acc + shots[k]["dur"] - XF
    if card:
        ci = len(segs)
        inputs += ["-loop", "1", "-t", f"{card_d:.3f}", "-i", card]
        # settb: looped stills arrive on 1/FPS, the rendered segments on 1/15360 — xfade
        # refuses to mix timebases
        fc.append(f"[{ci}:v]fps={FPS},scale={W}:{H},setsar=1,settb=1/15360,format=yuv420p[cd]")
        fc.append(f"[{prev}][cd]xfade=transition=fade:duration={XF}:offset={acc - XF:.3f}[vv]")
        prev = "vv"

    ai = len(segs) + (1 if card else 0)
    fade_st = max(0.0, adur - 2.6)
    cmd = (["ffmpeg", "-y", "-v", "error"] + inputs + ["-i", a.audio] +
           ["-filter_complex", ";".join(fc), "-map", f"[{prev}]", "-map", f"{ai}:a",
            "-af", f"afade=t=in:st=0:d=0.03,afade=t=out:st={fade_st:.2f}:d=2.6",
            "-t", f"{adur:.3f}", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", a.out])
    run(cmd, "assemble")
    print(">> DONE", a.out, f"{float(probe(a.out)[0]):.2f}s")


if __name__ == "__main__":
    main()
