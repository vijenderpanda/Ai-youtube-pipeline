#!/usr/bin/env python3
"""Overlay EP02 brand-text PNGs onto the motion episode (finite inputs, veryfast)."""
import subprocess
V="channels/language-abc/renders/ep02_motion_full.mp4"
OUT="channels/language-abc/renders/ep02_final.mp4"
O="channels/language-abc/assets/scenes/ep02_ovl/"
durs=[13,13,13,13,13,13,13,12]; T=1.0
ovls=["ovl_0.png","ovl_1.png","ovl_2.png","ovl_3.png","ovl_4.png","ovl_5.png","ovl_6.png","ovl_7.png"]
wins=[]
for i,d in enumerate(durs):
    st=sum(durs[:i])-i*T
    en=st+d-(T if i<len(durs)-1 else 0)
    wins.append((ovls[i], st+ (0.6 if i else 1.0), en-0.4))
cmd=["ffmpeg","-y","-i",V]
for png,st,en in wins:
    cmd+=["-loop","1","-t",f"{en-st:.2f}","-i",O+png]
parts=[]
for i,(png,st,en) in enumerate(wins,start=1):
    dur=en-st
    parts.append(f"[{i}:v]fps=30,format=rgba,fade=t=in:st=0:d=0.5:alpha=1,"
                 f"fade=t=out:st={dur-0.5:.2f}:d=0.5:alpha=1,setpts=PTS+{st:.2f}/TB[c{i}]")
prev="0:v"
for i in range(1,len(wins)+1):
    o="vout" if i==len(wins) else f"b{i}"
    parts.append(f"[{prev}][c{i}]overlay=0:0:eof_action=pass:repeatlast=0[{o}]")
    prev=o
cmd+=["-filter_complex",";".join(parts),"-map","[vout]","-map","0:a",
      "-c:v","libx264","-crf","20","-preset","veryfast","-pix_fmt","yuv420p","-c:a","copy",OUT]
subprocess.run(cmd,check=True)
print("DONE",OUT)
