#!/usr/bin/env python3
"""
In-house PIL proof-pane generator for claude-tricks Ep 10 ("stop copy-pasting
between AIs"). Renders a 1080x1920 @30fps screen-recording STAND-IN — no
Leonardo, no real capture (see COST DISCIPLINE in the produce_preview brief).

Four time regions, sliced by the episode spec via `rec:ep10/demo_parallel.mp4@t`:

    0.0 - 14.0   PAIN   three chat tabs, one prompt, copy -> paste -> paste
   14.0 - 26.0   FIX    the aggregator UI: ONE input box, model pickers
   26.0 - 46.0   DEMO   one prompt, two answers streaming side by side
   46.0 - 62.0   PAYOFF the better answer picked out of the two

These are STYLISED panes in the channel's own visual language (dark ink +
magenta + yellow chips), deliberately NOT dressed up as screenshots of any
real product — nothing here should read as a captured UI of a named vendor.

Usage: python3 scripts/make_parallel_ai_mock.py --out <path.mp4>
"""
import argparse, math, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
INK = (14, 14, 20)
PANEL = (24, 25, 34)
PANEL2 = (32, 33, 44)
LINE = (58, 60, 76)
TXT = (228, 230, 238)
DIM = (138, 142, 158)
MAGENTA = (224, 33, 138)
YELLOW = (255, 212, 0)
GREEN = (60, 200, 130)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANTON = os.path.join(REPO, "remotion-studio", "public", "fonts", "Anton.ttf")
UI_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
]
MONO_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
]


def _pick(cands):
    for c in cands:
        if os.path.exists(c):
            return c
    return None


_UI, _MONO = _pick(UI_CANDIDATES), _pick(MONO_CANDIDATES)
_cache = {}


def font(kind, size):
    key = (kind, size)
    if key not in _cache:
        path = {"anton": ANTON, "ui": _UI, "mono": _MONO}[kind]
        _cache[key] = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    return _cache[key]


def rrect(d, box, r, fill, outline=None, width=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def wrap(d, text, f, maxw):
    out, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            if cur:
                out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


def typed(text, t, t0, cps=26.0):
    """Text revealed at `cps` chars/sec starting at t0, with a block cursor."""
    if t < t0:
        return ""
    n = int((t - t0) * cps)
    s = text[:n]
    if n < len(text) and int(t * 2) % 2 == 0:
        s += "|"
    return s


def base(d):
    d.rectangle([0, 0, W, H], fill=INK)


def chrome_tabs(d, y, tabs, active, hot=None):
    """Browser-ish tab strip. `hot` = index to pulse in magenta."""
    x = 40
    for i, name in enumerate(tabs):
        w = 300
        on = i == active
        fill = PANEL2 if on else (20, 21, 28)
        oc = MAGENTA if i == hot else (LINE if on else (20, 21, 28))
        rrect(d, [x, y, x + w, y + 76], 14, fill, oc, 3 if i == hot else 2)
        f = font("ui", 30)
        d.text((x + 26, y + 22), name, font=f, fill=TXT if on else DIM)
        x += w + 14


def panel_header(d, box, label, color=DIM):
    d.line([box[0], box[1] + 74, box[2], box[1] + 74], fill=LINE, width=2)
    d.ellipse([box[0] + 26, box[1] + 28, box[0] + 50, box[1] + 52], fill=color)
    d.text((box[0] + 68, box[1] + 24), label, font=font("ui", 32), fill=TXT)


def bubble(d, x, y, w, lines, f, fill=PANEL2, txt=TXT, pad=24):
    h = pad * 2 + len(lines) * (f.size + 12)
    rrect(d, [x, y, x + w, y + h], 18, fill)
    for i, ln in enumerate(lines):
        d.text((x + pad, y + pad + i * (f.size + 12)), ln, font=f, fill=txt)
    return y + h


def stream_lines(d, x, y, w, text, f, frac, fill=PANEL2, txt=TXT):
    """Answer bubble whose text is revealed progressively (frac 0..1)."""
    full = wrap(d, text, f, w - 48)
    n_chars = max(1, int(len(text) * max(0.0, min(1.0, frac))))
    shown, used = [], 0
    for ln in full:
        if used >= n_chars:
            break
        take = min(len(ln), n_chars - used)
        shown.append(ln[:take])
        used += len(ln) + 1
    if not shown:
        shown = [""]
    # reserve full height so the pane doesn't jump as text streams in
    h = 48 + len(full) * (f.size + 12)
    rrect(d, [x, y, x + w, y + h], 18, fill)
    for i, ln in enumerate(shown):
        d.text((x + 24, y + 24 + i * (f.size + 12)), ln, font=f, fill=txt)
    return y + h


PROMPT = "explain quantum entanglement in 2 sentences"
ANS_A = ("Two particles can share one linked state, so measuring one instantly "
         "fixes what you'll measure on the other. That link holds no matter how "
         "far apart they are.")
ANS_B = ("Entangled particles behave like one system described by a single wave "
         "function. Measure one and the other's outcome is settled at once — but "
         "no usable signal travels between them.")


# ---------------------------------------------------------------- region 1
def draw_pain(d, t):
    """0-14s: one prompt, three tabs, manual copy/paste round trip."""
    base(d)
    d.text((44, 60), "THE OLD WAY", font=font("anton", 58), fill=YELLOW)

    # which tab is active + what the friction beat is right now
    beats = [(0.0, 0, "type"), (3.4, 0, "copy"), (5.2, 1, "paste"),
             (8.0, 1, "copy"), (9.6, 2, "paste"), (12.0, 2, "read")]
    active, mode = 0, "type"
    for bt, a, m in beats:
        if t >= bt:
            active, mode = a, m
    hot = active if mode in ("copy", "paste") else None
    chrome_tabs(d, 168, ["AI CHAT 1", "AI CHAT 2", "AI CHAT 3"], active, hot)

    box = [40, 280, W - 40, H - 300]
    rrect(d, box, 22, PANEL, LINE)
    panel_header(d, box, f"AI CHAT {active + 1}", [MAGENTA, YELLOW, GREEN][active])

    f = font("ui", 34)
    y = box[1] + 116
    shown = PROMPT if t > 3.0 else typed(PROMPT, t, 0.6)
    if shown:
        y = bubble(d, box[0] + 28, y, box[2] - box[0] - 56,
                   wrap(d, shown, f, box[2] - box[0] - 104), f) + 22

    if mode in ("paste", "read") or (mode == "copy" and active > 0):
        frac = min(1.0, (t - [0, 5.2, 9.6][active]) / 2.4)
        ans = [ANS_A, ANS_B, ANS_A][active]
        stream_lines(d, box[0] + 28, y, box[2] - box[0] - 56, ans, f, frac,
                     fill=(30, 31, 42))

    # the friction label — this is the whole point of the beat
    if mode in ("copy", "paste"):
        lab = "COPY" if mode == "copy" else "PASTE"
        fa = font("anton", 66)
        tw = d.textlength(lab, font=fa)
        bx = (W - tw) / 2
        by = H - 260
        rrect(d, [bx - 34, by - 16, bx + tw + 34, by + 88], 16, MAGENTA)
        d.text((bx, by), lab, font=fa, fill=(255, 255, 255))

    # tally of manual steps so far
    steps = sum(1 for bt, _, m in beats if t >= bt and m in ("copy", "paste"))
    if steps:
        d.text((44, H - 130), f"MANUAL STEPS: {steps}", font=font("anton", 52),
               fill=YELLOW)


# ---------------------------------------------------------------- region 2
def draw_fix(d, t):
    """14-26s: the aggregator — ONE box, pick your models."""
    u = t - 14.0
    base(d)
    d.text((44, 60), "ONE BOX INSTEAD", font=font("anton", 58), fill=YELLOW)

    box = [40, 190, W - 40, 700]
    rrect(d, box, 22, PANEL, LINE)
    panel_header(d, box, "PARALLEL CHAT", MAGENTA)

    d.text((box[0] + 32, box[1] + 116), "ASK ONCE", font=font("ui", 30), fill=DIM)
    ib = [box[0] + 32, box[1] + 168, box[2] - 32, box[1] + 300]
    rrect(d, ib, 16, (18, 19, 26), MAGENTA if u > 1.0 else LINE)
    f = font("ui", 34)
    d.text((ib[0] + 24, ib[1] + 34), typed(PROMPT, u, 1.2)[:46] or " ",
           font=f, fill=TXT)

    # model pickers switch on one at a time
    d.text((box[0] + 32, box[1] + 336), "SEND TO", font=font("ui", 30), fill=DIM)
    picks = [("MODEL A", 4.4), ("MODEL B", 5.6)]
    x = box[0] + 32
    for name, on_at in picks:
        on = u >= on_at
        w = 290
        rrect(d, [x, box[1] + 386, x + w, box[1] + 470], 14,
              (46, 20, 38) if on else (20, 21, 28), MAGENTA if on else LINE)
        if on:
            d.ellipse([x + 22, box[1] + 414, x + 50, box[1] + 442], fill=MAGENTA)
        else:
            d.ellipse([x + 22, box[1] + 414, x + 50, box[1] + 442], outline=LINE, width=3)
        d.text((x + 68, box[1] + 410), name, font=font("ui", 32),
               fill=TXT if on else DIM)
        x += w + 20

    if u > 7.0:
        fa = font("anton", 54)
        rrect(d, [40, 760, W - 40, 880], 18, (46, 20, 38), MAGENTA)
        d.text((80, 786), "NO API KEYS · NO PASTING", font=fa, fill=(255, 255, 255))

    # two empty answer panes waiting
    if u > 8.4:
        for i, lab in enumerate(["ANSWER A", "ANSWER B"]):
            top = 930 + i * 460
            pb = [40, top, W - 40, top + 420]
            rrect(d, pb, 20, PANEL, LINE)
            panel_header(d, pb, lab, [MAGENTA, YELLOW][i])
            dots = int((u * 3) % 4)
            d.text((pb[0] + 32, pb[1] + 130), "." * dots or " ",
                   font=font("anton", 72), fill=DIM)


# ---------------------------------------------------------------- region 3
def draw_demo(d, t):
    """26-46s: one prompt in, two answers streaming at once."""
    u = t - 26.0
    base(d)
    d.text((44, 52), "ONE PROMPT · TWO ANSWERS", font=font("anton", 52), fill=YELLOW)

    ib = [40, 150, W - 40, 268]
    rrect(d, ib, 16, (18, 19, 26), MAGENTA)
    d.text((ib[0] + 24, ib[1] + 34), PROMPT[:46], font=font("ui", 34), fill=TXT)
    rrect(d, [W - 210, 168, W - 60, 250], 14, MAGENTA)
    d.text((W - 178, 186), "SEND", font=font("anton", 44), fill=(255, 255, 255))

    f = font("ui", 33)
    for i, (lab, ans, col) in enumerate([("ANSWER A", ANS_A, MAGENTA),
                                         ("ANSWER B", ANS_B, YELLOW)]):
        top = 320 + i * 700
        pb = [40, top, W - 40, top + 660]
        rrect(d, pb, 20, PANEL, LINE)
        panel_header(d, pb, lab, col)
        # BOTH panes stream on the same clock — that's the whole payoff
        frac = (u - 1.6) / 9.0
        stream_lines(d, pb[0] + 28, pb[1] + 110, pb[2] - pb[0] - 56, ans, f,
                     frac, fill=(30, 31, 42))
        if frac >= 1.0:
            d.text((pb[0] + 28, pb[3] - 76), "done", font=font("ui", 28), fill=GREEN)

    if u > 13.0:
        fa = font("anton", 58)
        lab = "AT THE SAME TIME"
        tw = d.textlength(lab, font=fa)
        rrect(d, [(W - tw) / 2 - 34, H - 172, (W + tw) / 2 + 34, H - 66], 16, MAGENTA)
        d.text(((W - tw) / 2, H - 152), lab, font=fa, fill=(255, 255, 255))


# ---------------------------------------------------------------- region 4
def draw_payoff(d, t):
    """46-62s: compare, keep the better one."""
    u = t - 46.0
    base(d)
    d.text((44, 52), "PICK THE BETTER ONE", font=font("anton", 52), fill=YELLOW)

    f = font("ui", 33)
    winner = 1 if u > 3.0 else None
    for i, (lab, ans, col) in enumerate([("ANSWER A", ANS_A, MAGENTA),
                                         ("ANSWER B", ANS_B, YELLOW)]):
        top = 220 + i * 720
        pb = [40, top, W - 40, top + 680]
        won = winner == i
        rrect(d, pb, 20, (26, 34, 30) if won else PANEL,
              GREEN if won else LINE, 5 if won else 2)
        panel_header(d, pb, lab, GREEN if won else col)
        stream_lines(d, pb[0] + 28, pb[1] + 110, pb[2] - pb[0] - 56, ans, f, 1.0,
                     fill=(30, 40, 34) if won else (30, 31, 42))
        if won:
            rrect(d, [pb[2] - 250, pb[1] + 18, pb[2] - 28, pb[1] + 92], 14, GREEN)
            d.text((pb[2] - 226, pb[1] + 30), "KEEP", font=font("anton", 46),
                   fill=(10, 30, 20))
        elif winner is not None:
            # dim the loser
            ov = Image.new("RGBA", (pb[2] - pb[0], pb[3] - pb[1]), (14, 14, 20, 150))
            d._image.paste(ov, (pb[0], pb[1]), ov)

    if u > 7.0:
        fa = font("anton", 62)
        for j, (line, col) in enumerate([("ZERO COPY-PASTE", YELLOW),
                                         ("ONE PROMPT", MAGENTA)]):
            tw = d.textlength(line, font=fa)
            y = H - 250 + j * 96
            d.text(((W - tw) / 2, y), line, font=fa, fill=col)


REGIONS = [(0.0, 14.0, draw_pain), (14.0, 26.0, draw_fix),
           (26.0, 46.0, draw_demo), (46.0, 62.0, draw_payoff)]
TOTAL = 62.0


def render(out):
    tmp = tempfile.mkdtemp(prefix="ep10mock_")
    n = int(TOTAL * FPS)
    for i in range(n):
        t = i / FPS
        img = Image.new("RGB", (W, H), INK)
        d = ImageDraw.Draw(img)
        d._image = img
        for a, b, fn in REGIONS:
            if a <= t < b:
                fn(d, t)
                break
        else:
            REGIONS[-1][2](d, TOTAL - 0.01)
        img.save(os.path.join(tmp, f"f{i:05d}.png"))
        if i % 300 == 0:
            print(f"   frame {i}/{n}", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", os.path.join(tmp, "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", out],
                   check=True)
    print(f">> {out}  ({TOTAL:.0f}s, {W}x{H}@{FPS})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    render(a.out)
