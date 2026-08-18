#!/usr/bin/env python3
"""Generalized Aashiqana long-form assembler (TEST 1, reproduces the Aaja Ve LF recipe).

Montage-cycles per-song motion clips + Ken Burns keyframes to the track with xfade
dissolves, opening on a premium thumbnail-grade frame held ~1.3s (sub-4s hook cold-open),
then muxes the track with a 4s fade-out. Captions are a SEPARATE later pass
(scripts/lyric_karaoke.py) so timing can iterate without re-render.

Usage:
  python3 scripts/assemble_lf.py --dir channels/aashiqana/songs/07-tu-meri \
      --track .../track/tu_meri_final.wav --out .../renders/base.mp4 \
      --exclude 07,13,15 --open kf_01 [--res 1920x1080] [--fps 30] [--xfade 0.7]
"""
import argparse, glob, os, subprocess, sys

def probe_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=nw=1:nk=1",path],capture_output=True,text=True)
    return float(r.stdout.strip())

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-1800:]); raise SystemExit(f"ffmpeg failed: {' '.join(cmd[:6])}...")

def norm_motion(src, dst, dur, W, H, FPS):
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"fps={FPS},setsar=1,format=yuv420p")
    run(["ffmpeg","-y","-i",src,"-t",f"{dur:.3f}","-vf",vf,"-an",
         "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",dst])

def ken_burns(src, dst, dur, direction, W, H, FPS):
    frames=int(dur*FPS)
    z = "min(zoom+0.0007,1.14)" if direction=="in" else "if(lte(zoom,1.0),1.14,max(zoom-0.0007,1.0))"
    vf=(f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
        f"zoompan=z='{z}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
        f"setsar=1,format=yuv420p")
    run(["ffmpeg","-y","-loop","1","-i",src,"-t",f"{dur:.3f}","-vf",vf,"-an",
         "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",dst])

def still_hold(src, dst, dur, W, H, FPS):
    vf=(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,format=yuv420p")
    run(["ffmpeg","-y","-loop","1","-i",src,"-t",f"{dur:.3f}","-vf",vf,"-an",
         "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",dst])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--track", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--exclude", default="", help="comma kf numbers with motion versions, e.g. 07,13,15")
    ap.add_argument("--open", default="kf_01", help="opener/thumbnail keyframe stem")
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--xfade", type=float, default=0.7)
    ap.add_argument("--kb", type=float, default=4.6)
    a=ap.parse_args()
    W,H=map(int,a.res.split("x")); FPS=a.fps; T=a.xfade
    THUMB_HOLD=1.3
    work=f"{a.dir}/renders/work"; os.makedirs(work,exist_ok=True)
    song_dur=probe_dur(a.track)

    excl={f"kf_{int(x):02d}" for x in a.exclude.split(",") if x.strip()}
    kf_all=sorted(glob.glob(f"{a.dir}/scenes/keyframes/kf_*.jpg"))
    opener=f"{a.dir}/scenes/keyframes/{a.open}.jpg"
    stills=[p for p in kf_all if os.path.splitext(os.path.basename(p))[0] not in excl
            and os.path.basename(p)!=os.path.basename(opener)]
    motion=sorted(glob.glob(f"{a.dir}/renders/clips/*.mp4"))
    print(f"opener={a.open}  stills={len(stills)}  motion={len(motion)}  song={song_dur:.1f}s")

    pool={}
    # opener: premium frame held (frame 0 = thumbnail source), then a slow KB continuation folded via its own KB later
    o_dst=f"{work}/_open.mp4"; still_hold(opener,o_dst,THUMB_HOLD+1.6,W,H,FPS); pool["_open"]=o_dst
    for i,src in enumerate(motion):
        d=max(2.0,probe_dur(src)-0.1); dst=f"{work}/m{i}.mp4"; norm_motion(src,dst,d,W,H,FPS); pool[f"m{i}"]=dst
        print("norm motion", os.path.basename(src), f"{d:.1f}s")
    for i,src in enumerate(stills):
        direction="in" if i%2==0 else "out"; dst=f"{work}/s{i}.mp4"; ken_burns(src,dst,a.kb,direction,W,H,FPS); pool[f"s{i}"]=dst

    # interleave: motion every ~3rd slot, stills fill; cycle to song length
    m_ids=[f"m{i}" for i in range(len(motion))]; s_ids=[f"s{i}" for i in range(len(stills))]
    order=["_open"]; si=0; mi=0; slot=0
    while si<len(s_ids) or mi<len(m_ids) or True:
        if slot%3==2 and m_ids:
            order.append(m_ids[mi%len(m_ids)]); mi+=1
        else:
            order.append(s_ids[si%len(s_ids)]); si+=1
        slot+=1
        # stop once we have plenty; fill loop below trims to song_dur
        if len(order)>200: break

    # build sequence to fill song_dur (accounting xfade overlap)
    seq=[]; acc=0.0
    for k,pid in enumerate(order):
        d=probe_dur(pool[pid]); contrib=d if k==0 else d-T
        seq.append(pid); acc+=contrib
        if acc>=song_dur+1.0: break
    print(f"segments={len(seq)} approx_total={acc:.1f}s target={song_dur:.1f}s")

    inputs=[]
    for pid in seq: inputs+=["-i",pool[pid]]
    fc=[]; prev="0:v"; accd=probe_dur(pool[seq[0]])
    for k in range(1,len(seq)):
        d=probe_dur(pool[seq[k]]); off=accd-T; lbl=f"v{k}"
        fc.append(f"[{prev}][{k}:v]xfade=transition=fade:duration={T}:offset={off:.3f}[{lbl}]")
        prev=lbl; accd=accd+d-T
    vlabel=f"[{prev}]" if len(seq)>1 else "[0:v]"
    aidx=len(seq); fade_st=max(0,song_dur-4)
    cmd=["ffmpeg","-y"]+inputs+["-i",a.track]
    cmd+=(["-filter_complex",";".join(fc),"-map",vlabel] if fc else ["-map","0:v"])
    cmd+=["-map",f"{aidx}:a","-af",f"afade=t=out:st={fade_st:.2f}:d=4","-t",f"{song_dur:.3f}",
          "-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
          "-c:a","aac","-b:a","192k","-ar","48000","-movflags","+faststart",a.out]
    print("rendering base cut...")
    run(cmd)
    print(">> DONE", a.out, f"{probe_dur(a.out):.1f}s")

if __name__=="__main__":
    main()
