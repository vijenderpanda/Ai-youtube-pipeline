#!/usr/bin/env python3
"""BC01 demo tapes: the REAL Build Club Chapter 1 run, recorded end-to-end.

Tape A (1080x1350, one continuous logged-in claude.ai session):
  1. paste the exact SHARE-PROMPT (assets/bc01/SHARE-PROMPT.txt) into a new chat
  2. Claude interviews us — answer its questions like a text, one at a time
  3. Claude writes index.html — extract the REAL file from the page
  4. new tab -> app.netlify.com/drop -> drop the real file -> live URL appears
Tape B (1080x1920 native, phone viewport): the LIVE deployed site, slow scroll,
  hover the WhatsApp button. This is the premium-bar proof + hook footage.

Marks sidecar carries every beat boundary + the live URL + extraction stats.
The prompt shown on camera IS the pinned prompt (BUILD-CLUB.md rule).

  python3 channels/claude-tricks/rec_bc01_build.py --out-dir assets/bc01
"""
import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
CH = ROOT / "channels" / "claude-tricks"
PROFILE = ROOT / ".browser-profiles" / "claude"
PROMPT_FILE = CH / "assets" / "bc01" / "SHARE-PROMPT.txt"

VIEW_A = {"width": 1080, "height": 1350}
VIEW_B = {"width": 540, "height": 960}   # x2 dsf -> 1080x1920 native

HIDE_CSS = "nav, [data-testid='menu-sidebar'], aside { display:none !important; }"

# Interview answers, in the order the prompt's SECTION 1 asks its questions.
# 99999 99999 is a deliberate dummy (wa.me rejects it politely if clicked).
ANSWERS = [
    "Anita's Tiffin",
    "Home-style tiffin meals. Rajma Chawal Rs 120, Paneer Thali Rs 150, Dal + 4 Roti Rs 90",
    "Working folks and students in Indiranagar, Bengaluru - lunch and dinner",
    "99999 99999",
    "warm & homely",
    "Fresh ghar-ka-khana cooked the same morning. Free delivery within 3 km. Order by 10 AM for lunch.",
]


def human_type(pg, el, text, cps=24):
    el.click()
    for ch in text:
        el.type(ch, delay=1000.0 / cps)


def last_response_text(pg):
    els = pg.query_selector_all(".font-claude-response")
    return els[-1].inner_text() if els else ""


def settle(pg, min_quiet=3.0, timeout=150):
    """Wait until the newest response stops growing for min_quiet seconds."""
    t0, prev, quiet_since = time.time(), "", time.time()
    while time.time() - t0 < timeout:
        cur = last_response_text(pg)
        if cur != prev:
            prev, quiet_since = cur, time.time()
        elif cur and time.time() - quiet_since >= min_quiet:
            return cur
        time.sleep(0.5)
    return prev


def looks_like_code_done(txt, pg):
    if "</html>" in txt or "</body>" in txt:
        return True
    # artifact panel: code lives outside .font-claude-response
    for pre in pg.query_selector_all("pre"):
        t = pre.inner_text()
        if "<!doctype" in t.lower() or "</html>" in t.lower():
            return True
    return False


def extract_html(pg, ctx):
    """Longest DOM code block containing an html doc; clipboard fallback."""
    best = ""
    for pre in pg.query_selector_all("pre"):
        t = pre.inner_text()
        if ("<!doctype" in t.lower() or "<html" in t.lower()) and len(t) > len(best):
            best = t
    if len(best) > 400:
        return best, "dom"
    try:
        ctx.grant_permissions(["clipboard-read", "clipboard-write"],
                              origin="https://claude.ai")
        for sel in ("button[aria-label*='Copy']", "button:has-text('Copy')"):
            btns = pg.query_selector_all(sel)
            if btns:
                btns[-1].click()
                pg.wait_for_timeout(800)
                txt = pg.evaluate("() => navigator.clipboard.readText()")
                if txt and "<html" in txt.lower():
                    return txt, "clipboard"
    except Exception as e:
        print(f">> clipboard fallback failed: {e}")
    return best, "dom-short"


def encode(src, out, w, h):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-vf", f"scale={w}:{h}", "-r", "30", "-c:v", "libx264",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-an", str(out)],
                   check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="assets/bc01")
    ap.add_argument("--skip-a", action="store_true",
                    help="reuse an existing site/index.html + url, re-shoot only tape B")
    a = ap.parse_args()
    out_dir = CH / a.out_dir if not Path(a.out_dir).is_absolute() else Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    site_dir = out_dir / "site"
    site_dir.mkdir(exist_ok=True)
    vdir = out_dir / ".rec_tmp"
    vdir.mkdir(exist_ok=True)

    prompt = PROMPT_FILE.read_text()
    # on-camera we paste from "copy everything below" — strip the header lines
    prompt_body = prompt.split("\n", 2)[2].strip()

    marks = {"answers": ANSWERS}
    live_url = None

    if not a.skip_a:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                str(PROFILE), headless=False, viewport=VIEW_A,
                args=["--disable-blink-features=AutomationControlled"],
                record_video_dir=str(vdir), record_video_size=VIEW_A)
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.goto("https://claude.ai/new", wait_until="domcontentloaded",
                    timeout=90000)
            pg.wait_for_timeout(8000)
            if "login" in pg.url:
                print("!! not logged in", file=sys.stderr)
                sys.exit(2)
            pg.add_style_tag(content=HIDE_CSS)
            t0 = time.time()
            mk = lambda k: marks.__setitem__(k, round(time.time() - t0, 2))

            # --- 1. paste the pinned prompt --------------------------------
            box = pg.wait_for_selector("div[contenteditable=true]", timeout=30000)
            box.click()
            mk("prompt_paste")
            pg.keyboard.insert_text(prompt_body)
            pg.wait_for_timeout(1600)
            pg.keyboard.press("Enter")
            mk("prompt_sent")

            # --- 2. the interview ------------------------------------------
            ai = 0
            for turn in range(10):
                txt = settle(pg)
                if looks_like_code_done(txt, pg):
                    mk("code_done")
                    break
                if ai >= len(ANSWERS):
                    print(">> answers exhausted but no code yet; waiting more")
                    txt = settle(pg, min_quiet=4, timeout=180)
                    mk("code_done")
                    break
                pg.add_style_tag(content=HIDE_CSS)
                box = pg.wait_for_selector("div[contenteditable=true]",
                                           timeout=30000)
                mk(f"answer{ai + 1}_start")
                human_type(pg, box, ANSWERS[ai])
                pg.wait_for_timeout(500)
                pg.keyboard.press("Enter")
                mk(f"answer{ai + 1}_sent")
                ai += 1
            marks["answers_used"] = ai

            # --- 3. extract the REAL file ----------------------------------
            pg.wait_for_timeout(1500)
            html, how = extract_html(pg, ctx)
            marks["extract_how"] = how
            marks["extract_chars"] = len(html)
            (site_dir / "index.html").write_text(html)
            print(f">> extracted index.html: {len(html)} chars via {how}")
            pg.wait_for_timeout(2000)

            # --- 4. Netlify Drop -------------------------------------------
            drop = ctx.new_page()
            drop.goto("https://app.netlify.com/drop",
                      wait_until="domcontentloaded", timeout=90000)
            drop.wait_for_timeout(7000)
            mk("drop_page")
            marks["drop_url_after"] = drop.url
            b64 = base64.b64encode((site_dir / "index.html")
                                   .read_bytes()).decode()
            did = drop.evaluate("""async (b64) => {
                const res = await fetch('data:text/html;base64,' + b64);
                const blob = await res.blob();
                const file = new File([blob], 'index.html',
                                      {type: 'text/html'});
                const dt = new DataTransfer();
                dt.items.add(file);
                const cands = [
                  document.querySelector("[class*='drop']"),
                  document.querySelector('main'),
                  document.body];
                for (const el of cands) {
                  if (!el) continue;
                  for (const t of ['dragenter', 'dragover', 'drop']) {
                    el.dispatchEvent(new DragEvent(t, {bubbles: true,
                      cancelable: true, dataTransfer: dt}));
                  }
                }
                return true;
            }""", b64)
            print(f">> drop dispatched: {did}")
            mk("drop_dispatched")
            # wait for the live link
            for _ in range(90):
                drop.wait_for_timeout(1000)
                for el in drop.query_selector_all("a[href*='netlify.app']"):
                    href = el.get_attribute("href") or ""
                    if ".netlify.app" in href and "app.netlify.com" not in href:
                        live_url = href
                        break
                if live_url:
                    break
            mk("url_live")
            marks["live_url"] = live_url
            print(f">> live URL: {live_url}")
            drop.wait_for_timeout(6000)

            vid = pg.video.path()
            vid_drop = drop.video.path()
            ctx.close()
        encode(vid, out_dir / "tape_a_claude.mp4", 1080, 1350)
        encode(vid_drop, out_dir / "tape_a_drop.mp4", 1080, 1350)
    else:
        prior = json.loads((out_dir / "tapes.marks.json").read_text())
        live_url = prior.get("live_url")
        marks = prior

    # --- Tape B: the live site on a phone, 1080x1920 native ----------------
    if live_url:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                str(PROFILE) + "-phone", headless=False, viewport=VIEW_B,
                device_scale_factor=2.0,
                args=["--disable-blink-features=AutomationControlled"],
                record_video_dir=str(vdir),
                record_video_size={"width": 1080, "height": 1920})
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.goto(live_url, wait_until="load", timeout=90000)
            pg.wait_for_timeout(5000)
            t0 = time.time()
            marks["b_open"] = 0.0
            # slow scroll down, then back to the CTA
            for _ in range(24):
                pg.mouse.wheel(0, 90)
                pg.wait_for_timeout(220)
            marks["b_scrolled"] = round(time.time() - t0, 2)
            pg.wait_for_timeout(1200)
            cta = pg.query_selector("a[href*='wa.me']")
            if cta:
                cta.scroll_into_view_if_needed()
                pg.wait_for_timeout(900)
                cta.hover()
                marks["b_cta_hover"] = round(time.time() - t0, 2)
            pg.wait_for_timeout(2600)
            vidb = pg.video.path()
            ctx.close()
        encode(vidb, out_dir / "tape_b_phone.mp4", 1080, 1920)
    else:
        print("!! no live URL — tape B skipped", file=sys.stderr)

    (out_dir / "tapes.marks.json").write_text(json.dumps(marks, indent=1))
    print(json.dumps(marks, indent=1))
    print(f">> tapes in {out_dir}")


if __name__ == "__main__":
    main()
