#!/usr/bin/env python3
"""AFTER tape for ep `_payperword` — same question + the fix line, NEW chat.

Wraps scripts/record_demo.py (same hygiene: login probe, PII redaction, popup
dismissal, draft clear) and adds what this tape's spec needs on top of the
single-ask recorder:

  * fix_typing_start / fix_typing_end stamped from the REAL keystroke that
    starts the fix clause (not estimated) — the fix clause is also typed a
    touch slower than the question, because reading it land is the teach beat
  * the FULL final answer text captured out of the DOM (read_answer sees the
    whole message; the stock sidecar keeps only a 400-char head) → exact
    N_AFTER, never transcribed from pixels
  * a multi-punch sidecar for style_punch.py: tight composer punch only while
    the fix clause types (zoom capped by the MEASURED typed-ink extent, §10c),
    then a near-full-frame hold on the bullets through the end of the take

Acceptance (hard, from the plan): answer ≤ ~80 words with >= 3 bullet lines,
else exit 2 so the caller re-records with a tighter cap.
"""
import json, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import record_demo as rd

QUESTION = "How do I ask my boss for a raise?"
FIX = " Answer in 3 bullets, max 60 words."
PROMPT = QUESTION + FIX
OUT = Path(__file__).resolve().parents[0] / "assets/ep_payperword/raw_after.mp4"
MAX_WORDS = 80

state = {"boxes": []}

# --- patch 1: keystroke-true fix-clause marks + slower fix typing ------------
def human_type_marked(el, text, cps=14):
    import random
    n_q = len(QUESTION)
    for i, ch in enumerate(text):
        if i == 0:
            state["m_first_char"] = time.monotonic()
        if i == n_q:
            time.sleep(0.35)                      # tiny beat before the fix
            state["m_fix_char"] = time.monotonic()
        rate = 10 if i >= n_q else cps            # fix clause reads as it types
        el.type(ch, delay=0)
        time.sleep(random.uniform(0.5, 1.5) / rate)
    state["m_last_char"] = time.monotonic()
rd.human_type = human_type_marked

# --- patch 2: keep the FULL answer text --------------------------------------
_orig_read = rd.read_answer
def read_full(page):
    sel, txt = _orig_read(page)
    if txt:
        state["answer_full"] = txt
    return sel, txt
rd.read_answer = read_full

# --- patch 3: log measured element boxes -------------------------------------
_orig_box = rd.box_norm
def box_logged(page, selector, last=False):
    b = _orig_box(page, selector, last)
    state["boxes"].append({"selector": selector, "last": last, "box": b})
    return b
rd.box_norm = box_logged


def wait_profile_free(timeout=600):
    """Parallel jobs share .browser-profiles/claude — wait, never kill."""
    end = time.time() + timeout
    while time.time() < end:
        r = subprocess.run(["pgrep", "-f", r"user-data-dir=.*browser-profiles/claude"],
                           capture_output=True)
        if r.returncode != 0:
            return
        print("claude profile busy (another tape recording) — waiting 5s")
        time.sleep(5)
    sys.exit("ABORT: claude profile still locked after 10 min")


def ink_extent(video, t0, t1):
    """Measured extent of the pixels that changed in [t0,t1] (the typed ink)."""
    import numpy as np
    dw, dh, dfps = 135, 240, 6.0
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video),
         "-vf", f"fps={dfps},scale={dw}:{dh}", "-pix_fmt", "gray",
         "-f", "rawvideo", "-"], capture_output=True, check=True)
    raw = np.frombuffer(proc.stdout, dtype=np.uint8)
    n = len(raw) // (dw * dh)
    fr = raw[: n * dw * dh].reshape(n, dh, dw).astype(np.float32)
    i0, i1 = max(0, int(t0 * dfps)), min(n - 1, int(t1 * dfps))
    if i1 <= i0 + 1:
        return None
    acc = np.abs(np.diff(fr[i0:i1 + 1], axis=0)).sum(axis=0)
    thr = acc.max() * 0.2 if acc.max() > 0 else 1.0
    ys, xs = np.nonzero(acc >= thr)
    if not len(xs):
        return None
    pad = 0.03
    return [max(0.0, xs.min() / dw - pad), max(0.0, ys.min() / dh - pad),
            min(1.0, (xs.max() + 1) / dw + pad), min(1.0, (ys.max() + 1) / dh + pad)]


def main():
    wait_profile_free()
    cfg = rd.SITES["claude"]
    out, timeline = rd.record(
        cfg["url"], cfg["input"], PROMPT, OUT,
        wait_after=16, profile=rd.PROFILES / "claude", submit_sel=cfg["submit"],
        require_login=True, redact=True, site="claude")

    # ---- fix-clause marks from real keystroke times -------------------------
    tlp = OUT.with_suffix(".timeline.json")
    tl = json.loads(tlp.read_text())
    off = tl["typing_start"] - state["m_first_char"]   # monotonic -> video time
    tl["fix_typing_start"] = round(state["m_fix_char"] + off, 3)
    tl["fix_typing_end"] = tl["typing_end"]

    # ---- exact word count + acceptance --------------------------------------
    answer = state.get("answer_full", "").strip()
    if not answer:
        sys.exit("ABORT: no answer text captured from the DOM")
    (OUT.parent / "answer_after.txt").write_text(answer + "\n")
    n_after = len(answer.split())
    bullets = [l for l in answer.splitlines()
               if re.match(r"^\s*([-•*·]|\d+[.)])\s+\S", l)]
    print(f"N_AFTER={n_after} words, {len(bullets)} bullet lines")
    if n_after > MAX_WORDS or len(bullets) < 3:
        sys.exit(2)  # caller re-records with a tighter cap

    counts_p = OUT.parent / "counts.json"
    counts = json.loads(counts_p.read_text()) if counts_p.exists() else {}
    counts["n_after"] = n_after
    counts["after"] = {
        "n_after": n_after, "bullet_lines": len(bullets),
        "method": "full answer text copied out of the DOM in-session "
                  "(read_answer full text), words = len(text.split())",
        "prompt": PROMPT, "source": "raw_after.mp4",
        "marks": {k: tl.get(k) for k in
                  ("fix_typing_start", "fix_typing_end", "submit",
                   "answer_start", "first_token", "answer_end")},
    }
    counts_p.write_text(json.dumps(counts, indent=2))

    # ---- punch windows for style_punch.py -----------------------------------
    dur = tl["duration"]
    composer_ink = ink_extent(OUT, tl["fix_typing_start"], tl["fix_typing_end"])
    composer_box = next((b["box"] for b in state["boxes"]
                         if not b["last"] and b["box"]), None)
    fix_box = composer_ink or composer_box
    c1, z1 = rd.punch_from_box(fix_box, 1.30, floor=1.15)
    answer_box = next((b["box"] for b in reversed(state["boxes"])
                       if b["last"] and b["box"]), None)
    c2, z2 = rd.punch_from_box(answer_box, 1.05, floor=1.02)
    p1_t1 = min(tl["fix_typing_end"] + 0.3, tl["submit"] - 0.05)
    p2_t0 = max((tl.get("first_token") or tl["submit"] + 1.5) - 0.2,
                p1_t1 + rd.MIN_PUNCH_GAP)
    tl["punches"] = [
        {"t0": round(max(0.0, tl["fix_typing_start"] - 0.1), 3),
         "t1": round(p1_t1, 3), "center": c1, "zoom": z1, "label": "fixline"},
        {"t0": round(p2_t0, 3), "t1": round(dur, 3),
         "center": c2, "zoom": z2, "label": "bullets_hold"},
    ]
    tl["observed"]["answer_words"] = n_after
    tlp.write_text(json.dumps(tl, indent=2))
    print(f"punches: fixline z={z1}@{c1}  bullets z={z2}@{c2}")
    print(f"OK {OUT} n_after={n_after}")


if __name__ == "__main__":
    main()
