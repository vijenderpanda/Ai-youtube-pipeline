#!/usr/bin/env python3
"""
Build the FREE proof-of-concept assets + spec for the AI Unpacked format.
No paid tools: Leonardo Sol still (already made) + Pillow mock screens + macOS `say` VO.

Produces:
  assets/poc/hook.png, screen_before.png, screen_plan.png, screen_planout.png, payoff.png
  assets/poc/sol_badge.png            (circular Sol + magenta ring)
  renders/poc/vo.wav                  (macOS `say` voiceover, concatenated per line)
  episodes/01.short.json              (timeline spec for assemble_short.py)

Then render:
  python3 scripts/assemble_short.py --spec channels/claude-tricks/episodes/01.short.json \
      --out channels/claude-tricks/renders/ep01_poc.mp4
"""
import os, json, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CH = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(CH))
POC = os.path.join(CH, "assets", "poc")
REND = os.path.join(CH, "renders", "poc")
os.makedirs(POC, exist_ok=True); os.makedirs(REND, exist_ok=True)

W, H = 1080, 1920
INK = (14, 14, 20); PANEL = (22, 22, 30); MAG = (224, 33, 138)
WHITE = (238, 240, 245); DIM = (140, 146, 160); GREEN = (80, 220, 140)

def ffont(cands, size):
    for p in cands:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

DISPLAY = ["/System/Library/Fonts/Supplemental/Impact.ttf",
           "/System/Library/Fonts/Supplemental/Arial Black.ttf",
           "/System/Library/Fonts/HelveticaNeue.ttc"]
MONO = ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf",
        "/System/Library/Fonts/Courier.ttc"]
SANS = ["/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf"]

def bg():
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    for i in range(0, H, 4):  # faint scanline texture
        d.line([(0, i), (W, i)], fill=(18, 18, 26), width=1)
    return im

def window(d, x, y, w, h, title="claude-code — ~/project"):
    d.rounded_rectangle([x, y, x + w, y + h], radius=28, fill=PANEL, outline=(44, 46, 60), width=2)
    d.rounded_rectangle([x, y, x + w, y + 74], radius=28, fill=(30, 30, 42))
    d.rectangle([x, y + 46, x + w, y + 74], fill=(30, 30, 42))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([x + 30 + i * 34, y + 30, x + 30 + i * 34 + 18, y + 48], fill=c)
    d.text((x + 150, y + 26), title, font=ffont(MONO, 26), fill=DIM)

def mono_lines(d, x, y, lines, size=34, lh=52):
    f = ffont(MONO, size)
    for i, (txt, col) in enumerate(lines):
        d.text((x, y + i * lh), txt, font=f, fill=col)

def save(im, name):
    p = os.path.join(POC, name); im.save(p); print("  wrote", os.path.relpath(p, REPO)); return p

# ---- hook card ----
def make_hook():
    im = bg(); d = ImageDraw.Draw(im)
    f1 = ffont(DISPLAY, 165)
    d.text((70, 300), ">_ claude code is editing 14 files...", font=ffont(MONO, 34), fill=GREEN)
    d.text((70, 460), "STOP", font=ffont(DISPLAY, 230), fill=MAG)
    d.text((70, 700), "LETTING AI", font=f1, fill=WHITE)
    d.text((70, 860), "WRECK YOUR", font=f1, fill=WHITE)
    d.text((70, 1020), "FILES", font=ffont(DISPLAY, 210), fill=(255, 214, 10))
    d.rounded_rectangle([70, 1260, 70 + 620, 1272], radius=6, fill=MAG)
    save(im, "hook.png")

# ---- screen: before (chaotic, no plan) ----
def make_before():
    im = bg(); d = ImageDraw.Draw(im)
    d.text((70, 210), "THE PROBLEM", font=ffont(DISPLAY, 74), fill=DIM)
    window(d, 60, 340, 960, 1180)
    mono_lines(d, 100, 470, [
        ("> refactor the auth module", WHITE),
        ("", WHITE),
        ("editing 14 files...", DIM),
        ("  ~/auth/login.ts", (255, 120, 120)),
        ("  ~/auth/session.ts", (255, 120, 120)),
        ("  ~/api/routes.ts", (255, 120, 120)),
        ("  + 11 more", (255, 120, 120)),
        ("", WHITE),
        ("wait — what did it just", WHITE),
        ("change?!", MAG),
    ])
    save(im, "screen_before.png")

# ---- screen: plan mode entering ----
def make_plan():
    im = bg(); d = ImageDraw.Draw(im)
    d.text((70, 210), "THE FIX", font=ffont(DISPLAY, 74), fill=WHITE)
    d.rounded_rectangle([300, 250, 300 + 470, 250 + 84], radius=18, fill=MAG)
    d.text((330, 262), "SHIFT + TAB", font=ffont(DISPLAY, 60), fill=WHITE)
    window(d, 60, 400, 960, 1120)
    mono_lines(d, 100, 520, [
        ("⏸  plan mode  on", GREEN),
        ("", WHITE),
        ("> refactor the auth module", WHITE),
        ("", WHITE),
        ("thinking through the change", DIM),
        ("before touching your code...", DIM),
    ])
    save(im, "screen_plan.png")

# ---- screen: plan output waiting ----
def make_planout():
    im = bg(); d = ImageDraw.Draw(im)
    d.text((70, 210), "THE PLAN", font=ffont(DISPLAY, 74), fill=WHITE)
    window(d, 60, 340, 960, 1180)
    mono_lines(d, 100, 460, [
        ("Here's my plan:", WHITE),
        ("", WHITE),
        ("1. extract session helper", (150, 200, 255)),
        ("2. add token refresh", (150, 200, 255)),
        ("3. update 3 call sites", (150, 200, 255)),
        ("4. add tests", (150, 200, 255)),
        ("", WHITE),
        ("Approve this plan? (y/n)", GREEN),
        ("", WHITE),
        ("▏ waiting for your ok", MAG),
    ])
    save(im, "screen_planout.png")

# ---- payoff card ----
def make_payoff():
    im = bg(); d = ImageDraw.Draw(im)
    d.text((70, 430), "NO MORE", font=ffont(DISPLAY, 130), fill=WHITE)
    d.text((70, 560), "SURPRISE", font=ffont(DISPLAY, 130), fill=WHITE)
    d.text((70, 690), "REWRITES", font=ffont(DISPLAY, 175), fill=MAG)
    d.rounded_rectangle([70, 930, 70 + 900, 930 + 150], radius=24, outline=MAG, width=5)
    d.text((100, 962), "Follow for a new AI trick", font=ffont(SANS, 46), fill=WHITE)
    d.text((100, 1017), "every day  ·  link in profile", font=ffont(SANS, 40), fill=DIM)
    save(im, "payoff.png")

# ---- Sol circular badge with magenta ring ----
def make_badge():
    src = Image.open(os.path.join(CH, "assets", "character", "sol_canonical.jpg")).convert("RGB")
    s = min(src.size); src = src.crop(((src.width - s) // 2, (src.height - s) // 2,
                                       (src.width + s) // 2, (src.height + s) // 2)).resize((512, 512))
    d = 512; badge = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    mask = Image.new("L", (d, d), 0); ImageDraw.Draw(mask).ellipse([16, 16, d - 16, d - 16], fill=255)
    badge.paste(src, (0, 0), mask)
    ring = ImageDraw.Draw(badge)
    ring.ellipse([8, 8, d - 8, d - 8], outline=MAG, width=14)
    p = os.path.join(POC, "sol_badge.png"); badge.save(p)
    print("  wrote", os.path.relpath(p, REPO)); return p

# ---- voiceover via macOS `say` + caption timings ----
HOT = {"STOP", "WRECKING", "SHIFT", "TAB", "PLAN", "MODE", "THINKS", "FIRST",
       "FULL", "YES", "CONTROL", "ZERO", "REWRITES", "FOLLOW", "EVERY", "DAY"}
def clean(w): return "".join(c for c in w.upper() if c.isalnum() or c in "+-'")

# Vaibhav-cadence: command hook -> stakes -> fast steps -> payoff -> CTA. Short punchy lines.
LINES = [
    "Stop letting Claude Code wreck your files.",
    "One shortcut fixes it.",
    "Press Shift Tab. That's Plan Mode.",
    "Now Claude thinks first. Full plan. Waits for your yes.",
    "You stay in control. Zero surprise rewrites.",
    "Follow. New A.I. trick every day.",
]
TEMPO = 1.12  # speed up VO ~12% (Kokoro fallback only; Hrithik is naturally fast)

# Sol's LOCKED signature voice: "Hrithik - Charismatic Gen Z Male" (ElevenLabs)
ELEVEN_VOICE = "ZZ5OIPIzxVJswEhc0UXt"

def build_vo_eleven():
    """One ElevenLabs call -> continuous VO + real word timings; derive per-line durs."""
    import sys as _sys
    _sys.path.insert(0, os.path.join(REPO, "scripts"))
    from eleven_vo import load_key, synth
    vo = os.path.join(REND, "vo.wav")
    script = " ".join(LINES).replace("A.I.", "A I")
    synth(load_key(), ELEVEN_VOICE, script, vo, speed=1.0, style=0.5)
    words = json.load(open(vo.rsplit(".", 1)[0] + ".words.json"))
    caps = [{**w, "hot": w["w"].strip(".,!?").upper() in HOT} for w in words]
    for c in caps:
        c["w"] = clean(c["w"])
    # per-line durations from word counts (line boundary = midpoint of gap)
    counts = [len(l.replace("A.I.", "AI").split()) for l in LINES]
    seg_durs, idx, prev_end = [], 0, 0.0
    for n in counts:
        last = caps[idx + n - 1]
        nxt = caps[idx + n]["start"] if idx + n < len(caps) else last["end"]
        bound = round((last["end"] + nxt) / 2, 3)
        seg_durs.append(round(bound - prev_end, 3)); prev_end = bound
        idx += n
    total = caps[-1]["end"]
    seg_durs[-1] = round(seg_durs[-1] + (total - sum(seg_durs)), 3)
    print(f"  ElevenLabs VO: {round(total,1)}s, lines={seg_durs}")
    return vo, seg_durs, caps, total

_KOKORO = None
def synth_line(line, wav):
    """Kokoro-82M (free, commercial-safe) with macOS `say` fallback."""
    global _KOKORO
    try:
        if _KOKORO is None:
            from kokoro import KPipeline
            _KOKORO = KPipeline(lang_code="a")   # American English
        import numpy as np, soundfile as sf
        chunks = [audio for _, _, audio in _KOKORO(line, voice="am_michael")]
        sf.write(wav, np.concatenate(chunks), 24000)
        return "kokoro"
    except Exception as e:
        print(f"   (kokoro unavailable: {e}; falling back to say)")
        aiff = wav.replace(".wav", ".aiff")
        subprocess.run(["say", "-v", "Alex", "-o", aiff, line], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aiff,
                        "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", wav], check=True)
        return "say"

def build_vo():
    seg_durs = []; caps = []; wavs = []; t = 0.0
    for i, line in enumerate(LINES):
        wav = os.path.join(REND, f"l{i}.wav")
        eng = synth_line(line, wav)
        if i == 0: print(f"   voice engine: {eng}")
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
              "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", wav]).strip())
        wavs.append(wav); seg_durs.append(round(dur, 3))
        words = line.replace(".", "").replace(",", "").split()
        weights = [max(2, len(w)) for w in words]; tot = sum(weights); wt = t
        for w, ww in zip(words, weights):
            dw = dur * ww / tot
            disp = clean(w)
            caps.append({"w": disp, "start": round(wt, 2), "end": round(wt + dw * 0.9, 2),
                         "hot": disp in HOT})
            wt += dw
        t += dur
    # concat line wavs -> vo.wav (sped up by TEMPO; caption/segment times scaled to match)
    lst = os.path.join(REND, "vo_list.txt")
    open(lst, "w").write("\n".join(f"file '{os.path.abspath(w)}'" for w in wavs) + "\n")
    vo = os.path.join(REND, "vo.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-filter:a", f"atempo={TEMPO}", "-c:a", "pcm_s16le", vo], check=True)
    seg_durs = [round(d / TEMPO, 3) for d in seg_durs]
    for c in caps:
        c["start"] = round(c["start"] / TEMPO, 2); c["end"] = round(c["end"] / TEMPO, 2)
    t = t / TEMPO
    print("  wrote", os.path.relpath(vo, REPO), f"({round(t,1)}s @ x{TEMPO})")
    return vo, seg_durs, caps, t

def main():
    print(">> mock screens"); make_hook(); make_before(); make_plan(); make_planout(); make_payoff()
    print(">> Sol badge"); make_badge()
    print(">> voiceover")
    try:
        vo, durs, caps, total = build_vo_eleven()
    except Exception as e:
        print(f"   (ElevenLabs unavailable: {e}; falling back to Kokoro)")
        vo, durs, caps, total = build_vo()
    # 6 VO lines -> 5 visual beats: hook card, chaos term, planmode term, planout term, payoff card
    def P(n): return os.path.join(POC, n)
    segments = [
        {"img": P("hook.png"), "dur": durs[0], "motion": "zoom_in"},
        {"vid": P("term_plan.mp4"), "dur": durs[1], "punch": True},
        {"vid": P("term_planmode.mp4"), "dur": durs[2], "punch": True},
        {"vid": P("term_planout.mp4"), "dur": durs[3], "punch": True},
        {"img": P("payoff.png"), "dur": round(durs[4] + durs[5], 3), "motion": "zoom_out"},
    ]
    hook_end = durs[0]; payoff_start = round(total - durs[-1], 2)
    spec = {
        "w": W, "h": H, "fps": 30, "accent": "E0218A",
        "vo": vo, "music": "", "music_gain": 0.12,
        "caption_size": 165,
        "segments": segments,
        "avatar": (
            {"video": idle, "corner": "br", "size": 430, "margin": 54,
             "windows": [[0.0, round(hook_end, 2)], [payoff_start, round(total, 2)]]}
            if os.path.exists(idle := os.path.join(CH, "assets", "character", "sol_idle.mp4"))
            else {"img": os.path.join(POC, "sol_badge.png"), "corner": "br",
                  "size": 430, "margin": 54,
                  "windows": [[0.0, round(hook_end, 2)], [payoff_start, round(total, 2)]],
                  "chroma": False}),
        "captions": caps,
    }
    sp = os.path.join(CH, "episodes", "01.short.json")
    json.dump(spec, open(sp, "w"), indent=2)
    print(">> wrote spec", os.path.relpath(sp, REPO), f"| total ~{round(total,1)}s")

if __name__ == "__main__":
    main()
