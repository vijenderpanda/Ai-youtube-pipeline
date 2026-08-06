#!/usr/bin/env python3
"""
Build a 9:16 Short for a music release. Two modes:

CLIP MODE (original) -- center-cropped vertical montage of the motion clips, xfaded,
with a contiguous slice of the song as audio:
  python3 scripts/assemble_short_music.py --song song.mp3 --start 66.9 --dur 32 --out base.mp4

CONFIG MODE -- an explicit beat list (cards + stills) over a pre-built audio bed. Needed
for cut formats that are not a montage: a frame-zero card, per-beat stills with their own
pan/push, HARD cuts on a vocal onset, and closing cards. Boundaries are per-beat, so one
cut can mix dissolves and hard cuts:
  python3 scripts/assemble_short_music.py --config duel.json --out base.mp4

Config schema:
  {"audio": "bed.wav",
   "segments": [
     {"kind":"card",  "src":"versus.png", "dur":2.35, "xfade_in":0.0},
     {"kind":"still", "src":"a.jpg", "dur":5.95, "xfade_in":0.35,
      "cx":[0.52,0.66], "cy":0.5, "zoom":[1.0,1.05],
      "chip":{"src":"chip1.png","x":72,"y":210}},
     ...]}
  xfade_in 0 = HARD CUT (concat, no dissolve at all -- not a 1-frame xfade).

Run lyric_karaoke.py afterwards for the sung lines; keeping the lyric pass separate means
a re-sync never re-renders the base (playbook S4).
"""
import argparse, json, os, subprocess, sys

BASE = "channels/aashiqana/songs/01-baarish-aur-tum"
CLIPS = f"{BASE}/renders/clips"
W, H, FPS = 1080, 1920, 30
T = 0.6
SS = 1.6          # supersample factor: pan crop happens above output res, then zoompan
                  # downsamples -- keeps a 1344x768 source clean through a push-in

CLIP_ORDER = ["c07_rooftop_embrace","c01_rain_intimate","c05_cafe_couple",
              "c10_hills_walk","c03_meera_rain_a","c02_rain_wide","c07_rooftop_embrace"]

def probe(p):
    r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                      "-of","default=nw=1:nk=1",p],capture_output=True,text=True)
    return float(r.stdout.strip())
def dims(p):
    r=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
                      "stream=width,height","-of","csv=p=0:s=x",p],capture_output=True,text=True)
    w,h=r.stdout.strip().split("x"); return int(w),int(h)
def run(cmd,what="ffmpeg"):
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode!=0:
        sys.stderr.write(f"\n--- {what} failed ---\n"+p.stderr[-2500:]+"\n"); raise SystemExit(1)


# ------------------------------------------------------------------ config mode

def pan_expr(scaled, crop, c0, c1, dur):
    """Linear crop-window translation between two centre fractions, clamped in python
    so the ffmpeg expression can never drive the window off the frame."""
    span = max(0, scaled - crop)
    a = max(0.0, min(span, c0 * scaled - crop / 2.0))
    b = max(0.0, min(span, c1 * scaled - crop / 2.0))
    if abs(b - a) < 0.5:
        return f"{a:.2f}"
    return f"{a:.2f}+({b - a:.2f})*min(1,t/{dur:.3f})"


def build_beat(seg, idx, work):
    """Render one 1080x1920 beat: full-bleed still with pan+push, or a card."""
    src, dur = seg["src"], float(seg["dur"])
    out = os.path.join(work, f"beat{idx:02d}.mp4")
    sw, sh = dims(src)
    s = max(W / sw, H / sh) * SS
    gw, gh = int(round(sw * s)) // 2 * 2, int(round(sh * s)) // 2 * 2
    cw, ch = int(W * SS) // 2 * 2, int(H * SS) // 2 * 2
    cw, ch = min(cw, gw), min(ch, gh)

    cx = seg.get("cx", 0.5)
    cx0, cx1 = (cx, cx) if isinstance(cx, (int, float)) else (cx[0], cx[1])
    cy = seg.get("cy", 0.5)
    cy0, cy1 = (cy, cy) if isinstance(cy, (int, float)) else (cy[0], cy[1])
    z0, z1 = seg.get("zoom", [1.0, 1.0])
    frames = max(2, int(round(dur * FPS)))

    chain = [f"scale={gw}:{gh}:flags=lanczos",
             f"crop={cw}:{ch}:'{pan_expr(gw, cw, cx0, cx1, dur)}'"
             f":'{pan_expr(gh, ch, cy0, cy1, dur)}'"]
    if z1 != z0 or SS != 1:
        # input to zoompan is already 9:16, so its crop region keeps the aspect -> no squeeze
        zexpr = f"{z0}+({z1 - z0})*on/{frames - 1}"
        chain.append(f"zoompan=z='{zexpr}':d={frames}:s={W}x{H}:fps={FPS}"
                     f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'")
    chain += [f"fps={FPS}", "setsar=1", "format=yuv420p"]

    inputs = ["-loop", "1", "-t", f"{dur:.3f}", "-i", src]
    fc = "[0:v]" + ",".join(chain) + "[v]"
    chip = seg.get("chip")
    if chip:
        inputs += ["-loop", "1", "-t", f"{dur:.3f}", "-i", chip["src"]]
        # chip fades in over 0.25s so it lands as a beat mark, not a pop
        fc += (f";[1:v]format=rgba,fade=t=in:st=0:d=0.25:alpha=1[ch];"
               f"[v][ch]overlay={chip['x']}:{chip['y']}:format=auto,format=yuv420p[v]")
    run(["ffmpeg", "-y", "-v", "error"] + inputs +
        ["-filter_complex", fc, "-map", "[v]", "-an", "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "17", out], f"beat {idx}")
    return out


def config_mode(a):
    cfg = json.load(open(a.config))
    segs = cfg["segments"]
    work = a.work or os.path.join(os.path.dirname(a.out), "_duel")
    os.makedirs(work, exist_ok=True)
    files = [build_beat(s, i, work) for i, s in enumerate(segs)]

    inputs, fc, prev, acc = [], [], "v0", float(segs[0]["dur"])
    for f in files:
        inputs += ["-i", f]
    # every beat normalised to one timebase first: looped stills and rendered mp4s
    # arrive on different tb and xfade refuses to mix them
    for k in range(len(files)):
        fc.append(f"[{k}:v]fps={FPS},settb=1/15360,setsar=1,format=yuv420p[v{k}]")
    for k in range(1, len(files)):
        d = float(segs[k].get("xfade_in", 0.35))
        if d <= 0:                                   # HARD CUT
            # concat re-stamps its output at 1/1000000; a following xfade refuses the
            # mismatch, so pin the timebase back on the way out
            fc.append(f"[{prev}][v{k}]concat=n=2:v=1:a=0,settb=1/15360[x{k}]")
            acc += float(segs[k]["dur"])
        else:
            fc.append(f"[{prev}][v{k}]xfade=transition=fade:duration={d}"
                      f":offset={acc - d:.3f}[x{k}]")
            acc += float(segs[k]["dur"]) - d
        prev = f"x{k}"

    adur = probe(cfg["audio"])
    total = min(acc, adur)
    print(f"beats={len(files)} video={acc:.2f}s audio={adur:.2f}s -> {total:.2f}s")
    run(["ffmpeg", "-y", "-v", "error"] + inputs + ["-i", cfg["audio"],
         "-filter_complex", ";".join(fc), "-map", f"[{prev}]", "-map", f"{len(files)}:a",
         "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", a.out], "assemble")
    print(">> DONE", a.out, f"{probe(a.out):.2f}s")


# ------------------------------------------------------------------ clip mode

def clip_mode(a):
    work=f"{BASE}/renders/work_short"; os.makedirs(work,exist_ok=True)
    segs=[]
    for i,name in enumerate(CLIP_ORDER):
        src=f"{CLIPS}/{name}.mp4"; d=max(2.0,probe(src)-0.2)
        dst=f"{work}/s{i}_{name}.mp4"
        vf=(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"fps={FPS},setsar=1,format=yuv420p")
        run(["ffmpeg","-y","-i",src,"-t",f"{d:.3f}","-vf",vf,"-an",
             "-c:v","libx264","-preset","veryfast","-crf","20",dst])
        segs.append((dst,probe(dst)))
    inputs=[]; use=[]; acc=0.0
    for dst,d in segs:
        contrib = d if not use else d-T
        use.append((dst,d)); acc+=contrib
        if acc>=a.dur: break
    for dst,_ in use: inputs+=["-i",dst]
    fc=[]; prev="0:v"; accd=use[0][1]
    for k in range(1,len(use)):
        off=accd-T; fc.append(f"[{prev}][{k}:v]xfade=transition=fade:duration={T}:offset={off:.3f}[v{k}]")
        prev=f"v{k}"; accd=accd+use[k][1]-T
    vlab=f"[{prev}]" if len(use)>1 else "[0:v]"
    cmd=["ffmpeg","-y"]+inputs+["-ss",f"{a.start}","-t",f"{a.dur}","-i",a.song]
    aidx=len(use)
    if fc: cmd+=["-filter_complex",";".join(fc),"-map",vlab]
    else: cmd+=["-map","0:v"]
    cmd+=["-map",f"{aidx}:a","-af",f"afade=t=in:st=0:d=0.6,afade=t=out:st={a.dur-1.2:.2f}:d=1.2",
          "-t",f"{a.dur:.3f}","-c:v","libx264","-preset","medium","-crf","20",
          "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",a.out]
    run(cmd); print(">> DONE",a.out,f"{probe(a.out):.1f}s")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config"); ap.add_argument("--work")
    ap.add_argument("--song"); ap.add_argument("--start",type=float)
    ap.add_argument("--dur",type=float,default=32.0); ap.add_argument("--out",required=True)
    a=ap.parse_args()
    if a.config:
        config_mode(a)
    else:
        if not (a.song and a.start is not None):
            raise SystemExit("clip mode needs --song and --start")
        clip_mode(a)

if __name__=="__main__": main()
