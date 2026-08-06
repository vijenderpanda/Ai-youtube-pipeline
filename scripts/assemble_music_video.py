#!/usr/bin/env python3
"""
Aashiqana music-video assembler (Pipeline A, cinematic).
Sequences motion clips + Ken Burns stills to a song with xfade dissolves, muxes audio.
Lyric overlays are a SEPARATE later pass so timing can be iterated without re-render.

Usage:
  python3 scripts/assemble_music_video.py --song <mp3> --out <mp4> [--res 1920x1080]
          [--fps 30] [--xfade 0.7] [--preview]
"""
import argparse, os, subprocess, sys, json

BASE = "channels/aashiqana/songs/01-baarish-aur-tum"
CLIPS = f"{BASE}/renders/clips"
CHARS = f"{BASE}/characters"
SCENES = f"{BASE}/scenes"

def probe_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=nw=1:nk=1",path],capture_output=True,text=True)
    return float(r.stdout.strip())

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-1500:]); raise SystemExit(f"ffmpeg failed: {' '.join(cmd[:6])}...")

def norm_motion(src, dst, dur, W, H, FPS):
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},fps={FPS},setsar=1,format=yuv420p")
    run(["ffmpeg","-y","-i",src,"-t",f"{dur:.3f}","-vf",vf,"-an",
         "-c:v","libx264","-preset","veryfast","-crf","20",dst])

def ken_burns(src, dst, dur, direction, W, H, FPS):
    frames = int(dur*FPS)
    # scale up first to reduce zoompan jitter
    if direction == "in":
        z = "min(zoom+0.0007,1.14)"
    else:
        z = "if(lte(zoom,1.0),1.14,max(zoom-0.0007,1.0))"
    x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
    vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
          f"zoompan=z='{z}':d={frames}:x='{x}':y='{y}':s={W}x{H}:fps={FPS},"
          f"setsar=1,format=yuv420p")
    run(["ffmpeg","-y","-loop","1","-i",src,"-t",f"{dur:.3f}","-vf",vf,"-an",
         "-c:v","libx264","-preset","veryfast","-crf","20",dst])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--xfade", type=float, default=0.7)
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    W,H = map(int,a.res.split("x")); FPS=a.fps; T=a.xfade
    work = f"{BASE}/renders/work"; os.makedirs(work, exist_ok=True)

    song_dur = probe_dur(a.song)
    target = min(60.0, song_dur) if a.preview else song_dur

    # unique pool -> normalized intermediate
    motion = [
        ("m_rain_intimate", f"{CLIPS}/c01_rain_intimate.mp4"),
        ("m_rain_wide",     f"{CLIPS}/c02_rain_wide.mp4"),
        ("m_meera",         f"{CLIPS}/c03_meera_rain_a.mp4"),
        ("m_cafe",          f"{CLIPS}/c05_cafe_couple.mp4"),
        ("m_rooftop",       f"{CLIPS}/c07_rooftop_embrace.mp4"),
        ("m_hills",         f"{CLIPS}/c10_hills_walk.mp4"),
    ]
    stills = [
        ("s_twoshot1", f"{CHARS}/couple_twoshot_1.jpg", "in"),
        ("s_meera0",   f"{CHARS}/couple_master_0.jpg",  "out"),
        ("s_rooftop0", f"{SCENES}/scene_rooftop_0.jpg", "in"),
        ("s_hills0",   f"{SCENES}/scene_hills_0.jpg",   "out"),
        ("s_cafe1",    f"{SCENES}/scene_cafe_1.jpg",    "in"),
    ]
    pool = {}
    for pid, src in motion:
        dst = f"{work}/{pid}.mp4"
        d = max(2.0, probe_dur(src)-0.2)
        norm_motion(src, dst, d, W, H, FPS); pool[pid]=(dst,d)
        print("norm motion", pid, f"{d:.1f}s")
    KB = 8.0
    for pid, src, direction in stills:
        dst = f"{work}/{pid}.mp4"
        ken_burns(src, dst, KB, direction, W, H, FPS); pool[pid]=(dst,KB)
        print("ken burns", pid)

    # musical order (verse=rain/solo, chorus=hero rooftop/cafe, antara=hills) — cycles to fill
    order = ["s_twoshot1","m_rain_intimate","m_meera","s_meera0",      # intro/mukhda
             "m_rooftop","s_rooftop0","m_cafe","s_cafe1",              # chorus warmth
             "m_rain_wide","s_hills0","m_hills","m_rain_intimate",     # antara
             "m_rooftop","s_rooftop0","m_cafe","m_hills"]              # chorus/outro
    seq=[]; acc=0.0; i=0
    while True:
        pid = order[i % len(order)]; dst,d = pool[pid]
        # last-segment fit
        if acc==0.0: contrib=d
        else: contrib=d-T
        if acc+contrib >= target+ (0 if a.preview else 2):
            seq.append(pid); acc+=contrib; break
        seq.append(pid); acc+=contrib; i+=1
        if len(seq)>120: break
    print(f"segments={len(seq)} approx_total={acc:.1f}s target={target:.1f}s")

    # build xfade filtergraph
    inputs=[];
    for pid in seq: inputs += ["-i", pool[pid][0]]
    fc=[]; prev="0:v"; accd=probe_dur(pool[seq[0]][0])
    for k in range(1,len(seq)):
        d=probe_dur(pool[seq[k]][0])
        off=accd - T
        lbl=f"v{k}"
        fc.append(f"[{prev}][{k}:v]xfade=transition=fade:duration={T}:offset={off:.3f}[{lbl}]")
        prev=lbl; accd=accd + d - T
    vlabel=f"[{prev}]" if len(seq)>1 else "[0:v]"
    # audio: song + fade
    fade_st=max(0, (target if not a.preview else target)-4)
    filter_complex=";".join(fc) if fc else None
    cmd=["ffmpeg","-y"]+inputs+["-i",a.song]
    aidx=len(seq)
    if filter_complex:
        cmd+=["-filter_complex",filter_complex,"-map",vlabel]
    else:
        cmd+=["-map","0:v"]
    cmd+=["-map",f"{aidx}:a",
          "-af",f"afade=t=out:st={fade_st:.2f}:d=4",
          "-t",f"{target:.3f}",
          "-c:v","libx264","-preset","veryfast" if a.preview else "medium",
          "-crf","23" if a.preview else "20","-pix_fmt","yuv420p",
          "-c:a","aac","-b:a","192k","-movflags","+faststart",a.out]
    print("rendering final...")
    run(cmd)
    print(">> DONE", a.out, f"{probe_dur(a.out):.1f}s")

if __name__=="__main__":
    main()
