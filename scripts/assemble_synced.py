#!/usr/bin/env python3
"""Lyric-synced motion assembly (network standard).

Input json: {"T": 0.6, "audio": "...", "out": "...",
  "shots":[{"clip":"...","at":0.0}, ...],          # `at` = absolute second the shot must be on screen
  "overlays":[{"png":"...","st":21.2,"en":25.9}, ...],
  "end": 94.68}
Cut boundaries come from Whisper word timestamps of the actual song —
never from fixed per-shot durations (audio races ahead otherwise).
"""
import argparse, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from assemble_motion import make_scene, assemble, add_audio, run

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    a = ap.parse_args()
    p = json.load(open(a.plan))
    T = p.get("T", 0.6)
    shots = p["shots"]; end = p["end"]
    bounds = [s["at"] for s in shots] + [end]
    # dur_i so that xfade offsets land exactly on the requested boundaries
    durs = []
    for i in range(len(shots)):
        gap = bounds[i+1] - bounds[i]
        durs.append(gap + (T if i < len(shots)-1 else 0))
    tmp = tempfile.mkdtemp(prefix="sync_")
    scene_files = []
    for i, (s, d) in enumerate(zip(shots, durs)):
        sf = os.path.join(tmp, f"scene_{i:02d}.mp4")
        print(f"scene {i} {s['clip']} at={s['at']} dur={d:.2f}")
        make_scene(s["clip"], d, sf)
        scene_files.append(sf)
    silent = os.path.join(tmp, "video_silent.mp4")
    assemble(scene_files, durs, silent, T=T)
    with_audio = os.path.join(tmp, "video_audio.mp4")
    add_audio(silent, p["audio"], with_audio)
    # overlays (finite inputs, absolute windows)
    ovls = p.get("overlays", [])
    if not ovls:
        run(["ffmpeg", "-y", "-i", with_audio, "-c", "copy", p["out"]]); print("DONE", p["out"]); return
    cmd = ["ffmpeg", "-y", "-i", with_audio]
    for o in ovls:
        cmd += ["-loop", "1", "-t", f"{o['en']-o['st']:.2f}", "-i", o["png"]]
    parts = []
    for i, o in enumerate(ovls, start=1):
        dur = o["en"] - o["st"]
        fade = min(0.4, dur/4)
        parts.append(f"[{i}:v]fps=30,format=rgba,fade=t=in:st=0:d={fade:.2f}:alpha=1,"
                     f"fade=t=out:st={dur-fade:.2f}:d={fade:.2f}:alpha=1,setpts=PTS+{o['st']:.2f}/TB[c{i}]")
    prev = "0:v"
    for i in range(1, len(ovls)+1):
        lbl = "vout" if i == len(ovls) else f"b{i}"
        parts.append(f"[{prev}][c{i}]overlay=0:0:eof_action=pass:repeatlast=0[{lbl}]")
        prev = lbl
    cmd += ["-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "0:a",
            "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "copy", p["out"]]
    run(cmd)
    print("DONE", p["out"])

if __name__ == "__main__":
    main()
