#!/usr/bin/env python3
"""build_ep01_v3.py — CINEMATIC cut for "Already Happening" Ep01.

v3 over v2: Seedance 2.5 motion (clean, no distortion), the new tap-phone/pod-
arrives beat, punchy AI-Unpacked-style VO (Brian), bespoke Suno score ("Neon
Horizon"), running word captions w/ teal keyword pops, upscale to 1080x1920,
cinematic grade + light grain, branded end card. Master -14 LUFS.
"""
import json, os, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
MOT = os.path.join(HERE, "assets", "ep02", "motion")
VO = os.path.join(HERE, "renders", "ep02", "vo")
OUT = os.path.join(HERE, "renders", "ep02")
TMP = tempfile.mkdtemp(prefix="ah_ep02_")
W, H, FPS = 1080, 1920, 30
TEAL = (34, 211, 238)
WHITE = (245, 248, 250)
# Reuse an existing generated instrumental bed (calmest/most cinematic of the
# claude-tricks library; bed_active is busier + is AI Unpacked's active bed).
MUSIC = os.path.join(HERE, "..", "claude-tricks", "assets", "music", "bed_3.mp3")
MUSIC_SS = 20   # start 20s in, past any intro

TAIL = 0.5
GAP = 0.5

BEATS = [
    ("beat1.mp4", "beat1"),   # HOOK  — AI interface scanning a document
    ("beat2.mp4", "beat2"),   # today — contract review
    ("beat3.mp4", "beat3"),   # more  — night office running itself
    ("beat4.mp4", "beat4"),   # +5yr  — one human amid AI workflows
    ("beat5.mp4", "beat5"),   # gut   — quiet near-empty office
    ("beat6.mp4", "beat6"),   # button— finger over APPROVE
]
HOT = {"AI","JOB","ALREADY","TOLD","SECONDS","CONTRACT","RISKS","LAWYERS","CODE","TICKETS",
       "SLEEP","FIVE","YEARS","APPROVE","QUIET","TEN","MACHINES","REPLACED","SIGNS","OFF","ONE","NOBODY","WHOLE"}

def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def probe(p):
    return float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nk=1:nw=1",p]).strip())

def font(sz):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf","/System/Library/Fonts/HelveticaNeue.ttc"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
    return ImageFont.load_default()

FBIG = font(58); TRACK = 3
def _m(word,f):
    d=ImageDraw.Draw(Image.new("RGBA",(4,4))); return sum(d.textlength(c,font=f)+TRACK for c in word)-TRACK
def color_for(w): return TEAL if w.upper() in HOT else WHITE
def draw_word(d,x,y,word,col,f):
    for c in word:
        d.text((x+2,y+3),c,font=f,fill=(0,0,0,180)); d.text((x,y),c,font=f,fill=col+(255,))
        x+=d.textlength(c,font=f)+TRACK
    return x
def caption_png(words,path):
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    maxw=W*0.82; lines=[]; cur=[]; cw=0
    for wd in words:
        ww=_m(wd,FBIG)+_m(" ",FBIG)
        if cw+ww>maxw and cur: lines.append(cur); cur=[]; cw=0
        cur.append(wd); cw+=ww
    if cur: lines.append(cur)
    lines=lines[-2:]; lh=78; y0=int(H*0.70)
    widths=[sum(_m(w,FBIG)+_m(" ",FBIG) for w in ln)-_m(" ",FBIG) for ln in lines]
    pill_w=int(max(widths)+80); pill_h=lh*len(lines)+46; px0=(W-pill_w)//2; py0=y0-24
    d.rounded_rectangle([px0,py0,px0+pill_w,py0+pill_h],radius=26,fill=(8,10,14,170))
    for i,ln in enumerate(lines):
        x=(W-widths[i])//2; y=y0+i*lh
        for wd in ln: x=draw_word(d,x,y,wd,color_for(wd),FBIG); x+=_m(" ",FBIG)
    im.save(path)

def fit_clip(src,target,out):
    clip=probe(src)
    base=f"scale={W}:{H}:flags=lanczos,unsharp=5:5:0.6"
    if target<=clip:
        vf=f"{base},trim=0:{target},setpts=PTS-STARTPTS"
    else:
        vf=f"{base},setpts={target/clip:.4f}*PTS"
    run(["ffmpeg","-y","-i",src,"-vf",vf,"-an","-t",str(target),"-r",str(FPS),
         "-c:v","libx264","-crf","16","-preset","medium","-pix_fmt","yuv420p",out])

def build_segment(idx,clip,vo,dur):
    base=os.path.join(TMP,f"fit_{idx}.mp4"); fit_clip(os.path.join(MOT,clip),dur,base)
    words=json.load(open(os.path.join(VO,vo+".words.json")))
    lines=[]; cur=[]
    for w in words:
        cur.append(w)
        if len(cur)>=5: lines.append(cur); cur=[]
    if cur: lines.append(cur)
    pngs=[]; wins=[]
    for li,ln in enumerate(lines):
        line_end=ln[-1]["end"]+0.35
        if li<len(lines)-1: line_end=min(line_end,lines[li+1][0]["start"])
        for wi in range(len(ln)):
            p=os.path.join(TMP,f"cap_{idx}_{li}_{wi}.png"); caption_png([w["w"] for w in ln[:wi+1]],p)
            s=ln[wi]["start"]; e=ln[wi+1]["start"] if wi+1<len(ln) else line_end
            pngs.append(p); wins.append((s,e))
    inputs=["-i",base]
    for p in pngs: inputs+=["-i",p]
    fc=[]; prev="[0:v]"
    for i,(s,e) in enumerate(wins):
        lbl="[v]" if i==len(wins)-1 else f"[o{i}]"
        fc.append(f"{prev}[{i+1}:v]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'{lbl}"); prev=lbl
    seg=os.path.join(TMP,f"seg_{idx}.mp4")
    if wins:
        run(["ffmpeg","-y",*inputs,"-filter_complex",";".join(fc),"-map","[v]","-t",str(dur),
             "-c:v","libx264","-crf","16","-preset","medium","-pix_fmt","yuv420p",seg])
    else: os.replace(base,seg)
    return seg

def _pill(d, cx, cy, label, f, filled):
    tw=sum(d.textlength(c,font=f)+2 for c in label)-2
    pad=44; ph=84; pw=int(tw+pad*2)
    x0=int(cx-pw/2); y0=int(cy-ph/2); r=ph//2
    if filled:
        d.rounded_rectangle([x0,y0,x0+pw,y0+ph],radius=r,fill=TEAL+(255,))
        tcol=(8,14,18,255)
    else:
        d.rounded_rectangle([x0,y0,x0+pw,y0+ph],radius=r,outline=TEAL+(255,),width=3)
        tcol=TEAL+(255,)
    x=cx-tw/2
    for c in label:
        d.text((x,cy-f.size*0.62),c,font=f,fill=tcol); x+=d.textlength(c,font=f)+2
    return pw

def end_card(dur,out):
    im=Image.new("RGB",(W,H),(9,11,15)); di=ImageDraw.Draw(im); d=di
    f1=font(94); f2=font(42); fc=font(40)
    def cx(t,f): return (W-_m(t,f))//2
    y=int(H*0.30)
    for t in ("ALREADY","HAPPENING"):
        x=cx(t,f1)
        for c in t:
            d.text((x,y),c,font=f1,fill=TEAL+(255,) if t=="HAPPENING" else WHITE+(255,)); x+=d.textlength(c,font=f1)+TRACK
        y+=116
    d.rectangle([W//2-56,y+16,W//2+56,y+22],fill=TEAL)
    tag="The future isn't coming. It's already here."
    d.text(((W-d.textlength(tag,font=f2))//2,y+44),tag,font=f2,fill=(150,160,170))
    # CTA pills
    cta_y=int(H*0.58)
    lbl="SUBSCRIBE FOR MORE"
    w1=_pill(d, W*0.5, cta_y, lbl, fc, True)
    _pill(d, W*0.5, cta_y+112, "SHARE THIS", fc, False)
    hint="new drops from the near future, weekly"
    d.text(((W-d.textlength(hint,font=font(32)))//2,cta_y+180),hint,font=font(32),fill=(120,130,140))
    p=os.path.join(TMP,"endcard.png"); im.save(p)
    run(["ffmpeg","-y","-loop","1","-i",p,"-t",str(dur),"-r",str(FPS),
         "-vf",f"scale={W}:{H},fade=t=in:st=0:d=0.4,fade=t=out:st={dur-0.5}:d=0.5",
         "-c:v","libx264","-crf","18","-preset","medium","-pix_fmt","yuv420p",out])

HTRACK = 10   # letter-spacing for the hook title
def _fit_hook_size(title, track, maxw):
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    for sz in range(70, 32, -2):
        f = font(sz)
        w = sum(probe.textlength(c, font=f)+track for c in title) - track
        if w <= maxw:
            return sz
    return 34
HFONT = _fit_hook_size("THE FUTURE ISN'T COMING", HTRACK, int(W*0.86))

def _black_base_png(path):
    """Cinematic black with a faint teal glow-pool behind where the title sits."""
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W*0.5)/W)**2 + ((yy - H*0.43)/H)**2)
    glow = np.clip(1 - d/0.42, 0, 1)**2
    base = np.zeros((H, W, 3), float) + np.array([4, 6, 9])
    for i, t in enumerate((10, 34, 40)):        # subtle teal pool
        base[..., i] += glow * t
    Image.fromarray(np.clip(base, 0, 255).astype('uint8')).save(path)

def _hook_png(text, cursor, underline_frac, path):
    """Transparent overlay: glowing teal-white title on black + optional cursor + drawing underline."""
    f = font(HFONT)
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    def tw(s): return (sum(probe.textlength(c, font=f)+HTRACK for c in s) - HTRACK) if s else 0
    text_w = tw(text)
    x0 = (W - text_w)//2 if text else W//2
    y = int(H*0.42)
    # glow layer (teal halo)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    x = x0
    for c in text:
        gd.text((x, y), c, font=f, fill=(34, 211, 238, 170)); x += probe.textlength(c, font=f)+HTRACK
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    im = glow
    d = ImageDraw.Draw(im)
    # crisp text
    x = x0
    for c in text:
        d.text((x+2, y+3), c, font=f, fill=(0, 0, 0, 150))
        d.text((x, y), c, font=f, fill=(240, 245, 248, 255))
        x += probe.textlength(c, font=f)+HTRACK
    # cursor (teal block) right after the text
    if cursor:
        cx = x + 8 if text else W//2 - 10
        d.rectangle([cx, y+int(HFONT*0.10), cx+max(16, HFONT//3), y+int(HFONT*0.95)], fill=TEAL+(255,))
    # drawing underline
    if underline_frac > 0 and text:
        uw = int(text_w * underline_frac)
        ux = (W - text_w)//2
        uy = y + int(HFONT*1.45)
        d.rectangle([ux, uy, ux+uw, uy+5], fill=TEAL+(235,))
    im.save(path)

def cold_open(dur, out):
    """Game-opener: pure cinematic black, a lone teal cursor pulses, the title types out with a
    glow, a teal underline draws in, then it holds on a blinking cursor (unfinished = the hook)."""
    bpng = os.path.join(TMP, "cold_black.png"); _black_base_png(bpng)
    base = os.path.join(TMP, "cold_base.mp4")
    run(["ffmpeg", "-y", "-loop", "1", "-i", bpng, "-t", str(dur), "-r", str(FPS),
         "-vf", f"fade=t=in:st=0:d=0.4,noise=alls=9:allf=t,vignette=PI/4.5",
         "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", base])
    title = "THE FUTURE ISN'T COMING"
    frames = []  # (png, start, end)
    # 1) lone blinking cursor — anticipation
    curp = os.path.join(TMP, "hk_cur0.png"); _hook_png("", True, 0, curp)
    frames.append((curp, 0.30, 0.52)); frames.append((curp, 0.66, 0.80))
    # 2) type the line (glow + cursor)
    tstart, dt = 0.86, 0.052
    for i in range(1, len(title)+1):
        p = os.path.join(TMP, f"hk_t{i}.png"); _hook_png(title[:i], True, 0, p)
        frames.append((p, tstart+(i-1)*dt, tstart+i*dt))
    full = tstart + len(title)*dt
    # 3) teal underline draws in under the finished line
    ud = 0.55
    for k in range(1, 8):
        p = os.path.join(TMP, f"hk_u{k}.png"); _hook_png(title, True, k/7.0, p)
        frames.append((p, full+(k-1)*(ud/7), full+k*(ud/7)))
    hold = full + ud
    # 4) hold on a blinking cursor (the unfinished thought) until the cut
    pc = os.path.join(TMP, "hk_full_cur.png"); _hook_png(title, True, 1.0, pc)
    pn = os.path.join(TMP, "hk_full_off.png"); _hook_png(title, False, 1.0, pn)
    t, blink, k = hold, 0.40, 0
    while t < dur-0.06:
        frames.append((pc if k % 2 == 0 else pn, t, min(t+blink, dur-0.06))); t += blink; k += 1
    inputs = ["-i", base]
    for p, _, _ in frames: inputs += ["-loop", "1", "-i", p]
    fc = []; prev = "[0:v]"
    for j, (p, s, e) in enumerate(frames):
        lbl = "[v]" if j == len(frames)-1 else f"[o{j}]"
        fc.append(f"{prev}[{j+1}:v]overlay=0:0:enable='between(t,{s:.3f},{e:.3f})'{lbl}"); prev = lbl
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", str(dur),
         "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", out])

def brand_bug(path):
    """Small persistent wordmark for the top-left corner: teal dot + ALREADY HAPPENING."""
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    f=font(30); x,y=46,58
    d.ellipse([x,y+8,x+16,y+24],fill=TEAL+(255,))
    xx=x+28
    for c in "ALREADY HAPPENING":
        d.text((xx+1,y+1),c,font=f,fill=(0,0,0,150))
        d.text((xx,y),c,font=f,fill=(236,240,245,205)); xx+=d.textlength(c,font=f)+2
    im.save(path)

def main():
    os.makedirs(OUT,exist_ok=True)
    segs=[]; vo_parts=[]; durs=[]
    COLD=3.2
    copen=os.path.join(TMP,"seg_cold.mp4"); cold_open(COLD,copen); segs.append(copen)
    for i,(clip,vo) in enumerate(BEATS):
        d=json.load(open(os.path.join(VO,vo+".words.json")))
        dur=(d[-1]["end"] if d else 2.0)+TAIL; durs.append(dur)
        segs.append(build_segment(i,clip,vo,dur)); vo_parts.append(os.path.join(VO,vo+".wav"))
    ecard=os.path.join(TMP,"seg_end.mp4"); end_card(2.6,ecard)
    listf=os.path.join(TMP,"segs.txt"); open(listf,"w").write("".join(f"file '{s}'\n" for s in segs+[ecard]))
    concat=os.path.join(TMP,"concat.mp4")
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",listf,"-c:v","libx264","-crf","16","-preset","medium","-pix_fmt","yuv420p",concat])
    graded0=os.path.join(TMP,"graded0.mp4")
    run(["ffmpeg","-y","-i",concat,"-vf","eq=contrast=1.05:saturation=1.08,noise=alls=3:allf=t,vignette=PI/6",
         "-c:v","libx264","-crf","17","-preset","medium","-pix_fmt","yuv420p",graded0])
    total=COLD+sum(durs)+2.6
    bug=os.path.join(TMP,"bug.png"); brand_bug(bug)
    graded=os.path.join(TMP,"graded.mp4")
    run(["ffmpeg","-y","-i",graded0,"-loop","1","-i",bug,"-filter_complex",
         f"[1:v]format=rgba[b];[0:v][b]overlay=0:0:enable='between(t,{COLD:.2f},{total-2.6:.2f})'[v]",
         "-map","[v]","-t",str(total),"-c:v","libx264","-crf","17","-preset","medium","-pix_fmt","yuv420p",graded])
    # VO track w/ gaps (end card has no VO -> trailing silence)
    sil=os.path.join(TMP,"sil.wav"); run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=44100:cl=mono","-t",str(GAP),"-c:a","pcm_s16le",sil])
    endsil=os.path.join(TMP,"endsil.wav"); run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=44100:cl=mono","-t","2.6","-c:a","pcm_s16le",endsil])
    coldsil=os.path.join(TMP,"coldsil.wav"); run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=44100:cl=mono","-t","3.2","-c:a","pcm_s16le",coldsil])
    ap=[coldsil]
    for p in vo_parts: ap+=[p,sil]
    ap.append(endsil)
    al=os.path.join(TMP,"vo.txt"); open(al,"w").write("".join(f"file '{p}'\n" for p in ap))
    vofull=os.path.join(TMP,"vo_full.wav"); run(["ffmpeg","-y","-f","concat","-safe","0","-i",al,"-c:a","pcm_s16le",vofull])
    out=os.path.join(OUT,"ep02.mp4")
    total=COLD+sum(durs)+2.6
    # bed: high-pass to clear sub for VO, gentle scoop in VO presence band,
    # slow fade in/out, sat under the narration; loudnorm masters the mix.
    fc=("[1:a]volume=6dB[v0];"
        f"[2:a]highpass=f=90,equalizer=f=2200:width_type=q:w=1.4:g=-3,"
        f"afade=t=in:st=0:d=1.8,afade=t=out:st={total-2.0:.2f}:d=2.0,volume=-13dB[m];"
        "[v0][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    run(["ffmpeg","-y","-i",graded,"-i",vofull,"-stream_loop","-1","-ss",str(MUSIC_SS),"-i",MUSIC,
         "-filter_complex",fc,"-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k",
         "-ar","48000","-movflags","+faststart","-shortest",out])
    print(f"OK -> {out}  (~{total:.1f}s, ep02 bed=bed_3.mp3)")

if __name__=="__main__":
    main()
