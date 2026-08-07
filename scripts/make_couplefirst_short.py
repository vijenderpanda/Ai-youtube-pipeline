#!/usr/bin/env python3
"""The STANDARD Aashiqana couple-first Short assembler (BRAND-BIBLE §3, LOCKED 2026-08-07).

Given a couple (folder or --mood auto-pick) + song audio + lyric timing, it:
  1. casts the couple (scripts/pick_couple.py when --mood),
  2. auto-builds the couple-first beat sequence from the couple's shots —
     heroine hook 0-2s -> COUPLE payoff ~2s -> alternate heroine<->couple, a new shot
     every ~2s (never static past 2s), Ken Burns push on each, last beat loops to the open,
  3. renders the montage via scripts/assemble_short_music.py (config mode, hard cuts),
  4. overlays bilingual lyric cards (Devanagari + romanized) per line, high-contrast,
     in the caption-safe band.

Usage:
  python scripts/make_couplefirst_short.py --mood "golden hour yearning" \
      --audio song.wav --lyrics timing.json --out short.mp4
  python scripts/make_couplefirst_short.py --couple couple_02_goldenhour \
      --audio song.wav --lyrics timing.json --out short.mp4

lyric timing json: {"lines":[{"s":0.48,"e":5.64,"text":"Aaja ve...","hi":"आजा वे..."}, ...]}
('hi' is optional — without it the card is romanized only.)
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)
W, H = 1080, 1920


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p], capture_output=True, text=True)
    return float(r.stdout.strip())


def resolve_couple(args):
    import pick_couple
    if args.couple:
        d = args.couple if os.path.isdir(args.couple) else os.path.join(pick_couple.LIBRARY, args.couple)
        if not os.path.isdir(d):
            sys.exit(f"couple folder not found: {d}")
        return d
    scored = pick_couple.rank(pick_couple.load_couples(), args.mood)
    if not scored:
        sys.exit("no couples in library")
    print(f"cast by mood '{args.mood}' -> {scored[0][1]['codename']}")
    return scored[0][1]["dir"]


def categorize_shots(shots_dir):
    """-> {'G':[...heroine], 'C':[...couple], 'H':[...hero]} sorted absolute paths."""
    cats = {"G": [], "C": [], "H": []}
    for f in sorted(os.listdir(shots_dir)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        m = re.search(r"_(G|C|H)_", f)
        if m:
            cats[m.group(1)].append(os.path.join(shots_dir, f))
    return cats


def build_beats(cats, dur, cut=2.0):
    """Couple-first order: G(hook) -> C(payoff) -> alternate, loop to opening frame."""
    G, C, Hh = cats["G"], cats["C"], cats["H"]
    if not G or not C:
        sys.exit("need at least one heroine (G) and one couple (C) shot")
    n = max(6, int(round(dur / cut)))
    seq = []
    gi = ci = hi = 0
    for i in range(n):
        if i == 0:
            src = G[0]                                  # heroine hook = scroll-stopper
        elif i == 1:
            src = C[ci % len(C)]; ci += 1               # COUPLE payoff, early (kills the cliff)
        elif i == n - 1:
            src = G[0]                                  # loop back to the opening frame
        elif i % 2 == 0:
            if Hh and i % 6 == 0:
                src = Hh[hi % len(Hh)]; hi += 1         # occasional hero cutaway
            else:
                gi += 1; src = G[gi % len(G)]
        else:
            ci += 1; src = C[ci % len(C)]
        seq.append(src)
    base = round(dur / n, 3)
    durs = [base] * n
    durs[-1] = round(dur - base * (n - 1), 3)
    segs = []
    for i, src in enumerate(seq):
        z = [1.0, 1.08] if i % 2 == 0 else [1.07, 1.0]  # alternate push-in / ease-out
        seg = {"kind": "still", "src": src, "dur": durs[i], "cx": [0.5, 0.5], "cy": 0.46, "zoom": z}
        if i > 0:
            seg["xfade_in"] = 0.0                        # hard cut on the beat
        segs.append(seg)
    return segs


def make_card(line, idx, work, font_hi, font_ro):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    hi = (line.get("hi") or "").strip()
    ro = (line.get("text") or "").strip()

    def centered(text, font, y, fill):
        if not text or not font:
            return y
        bb = d.textbbox((0, 0), text, font=font, stroke_width=5)
        w = bb[2] - bb[0]
        d.text(((W - w) // 2 - bb[0], y), text, font=font, fill=fill,
               stroke_width=5, stroke_fill=(0, 0, 0, 230))
        return y + (bb[3] - bb[1]) + 16

    y = 1330
    if hi:
        y = centered(hi, font_hi, y, (255, 255, 255, 255))      # Devanagari, white
    centered(ro, font_ro, y, (255, 214, 120, 255))              # romanized, warm amber
    p = os.path.join(work, f"card_{idx:02d}.png")
    img.save(p)
    return p


def find_font(cands, size):
    from PIL import ImageFont
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return None


def main():
    ap = argparse.ArgumentParser(description="standard Aashiqana couple-first Short")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--couple", help="couple folder name or path")
    g.add_argument("--mood", help="song mood + keywords (auto-casts via pick_couple)")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--lyrics", help="timing json {lines:[{s,e,text,hi?}]}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cut", type=float, default=2.0, help="seconds per beat (default 2.0)")
    a = ap.parse_args()

    cdir = resolve_couple(a)
    cats = categorize_shots(os.path.join(cdir, "shots"))
    dur = probe(a.audio)
    print(f"couple {os.path.basename(cdir)} | shots G{len(cats['G'])}/C{len(cats['C'])}/H{len(cats['H'])} | audio {dur:.1f}s")

    work = tempfile.mkdtemp(prefix="cfshort_")
    cfg = {"audio": os.path.abspath(a.audio), "segments": build_beats(cats, dur, a.cut)}
    cfg_p = os.path.join(work, "beats.json")
    json.dump(cfg, open(cfg_p, "w"), indent=1)
    montage = os.path.join(work, "montage.mp4")
    subprocess.run([sys.executable, "scripts/assemble_short_music.py",
                    "--config", cfg_p, "--out", montage, "--work", os.path.join(work, "beats")], check=True)

    if not a.lyrics:
        shutil.copy(montage, a.out)
        print(">> DONE (no lyrics)", a.out, f"{probe(a.out):.1f}s")
        return

    lines = json.load(open(a.lyrics)).get("lines", [])
    font_hi = find_font(["/System/Library/Fonts/Supplemental/Kohinoor.ttc",
                         "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
                         "/System/Library/Fonts/Kohinoor.ttc",
                         "/Library/Fonts/Kohinoor.ttc"], 60)
    font_ro = find_font(["/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
                         "/System/Library/Fonts/Supplemental/Georgia.ttf",
                         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"], 52)
    if font_hi is None:
        print("!! no Devanagari font found — cards will be romanized only", file=sys.stderr)
    cards = [(ln, make_card(ln, i, work, font_hi, font_ro)) for i, ln in enumerate(lines)]

    inputs, fc, prev = ["-i", montage], [], "0:v"
    for i, (ln, p) in enumerate(cards):
        inputs += ["-i", p]
        fc.append(f"[{prev}][{i+1}:v]overlay=0:0:enable='between(t,{ln['s']:.2f},{ln['e']:.2f})'[v{i}]")
        prev = f"v{i}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs +
                   ["-filter_complex", ";".join(fc), "-map", f"[{prev}]", "-map", "0:a",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", a.out], check=True)
    print(">> DONE", a.out, f"{probe(a.out):.1f}s ({len(cards)} lyric cards)")


if __name__ == "__main__":
    main()
