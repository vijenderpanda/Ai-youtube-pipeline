#!/usr/bin/env python3
"""BC02 tapes: Chapter 2 — the Ch.1 site gets SMART, recorded end-to-end.

Tape A (1080x1350, logged-in claude.ai session):
  1. paste the Ch.2 pinned prompt (assets/bc02/SHARE-PROMPT.txt) + the REAL
     current anitas-tiffin index.html (assets/bc01/site/index.html) in one turn
  2. Claude answers "what's missing" + writes the question-box feature
  3. if it pauses for confirmation, send the ep19 move ON CAMERA:
     "What am I missing?" — then extract the COMPLETE updated index.html
Deploy (off camera, reliable path): netlify-cli to the anitas-tiffin site.
Tape B (1080x1920 native phone): the LIVE smart site — open the question box,
  type "aaj ka menu kya hai?", the site answers itself. Money shot.

  python3 channels/claude-tricks/rec_bc02_build.py [--skip-a] [--site SITE_ID]
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

CH = Path(__file__).resolve().parent
ROOT = CH.parent.parent
PROFILE = ROOT / ".browser-profiles" / "claude"
PROMPT_FILE = CH / "assets" / "bc02" / "SHARE-PROMPT.txt"
CH1_SITE = CH / "assets" / "bc01" / "site" / "index.html"

VIEW_A = {"width": 1080, "height": 1350}
VIEW_B = {"width": 540, "height": 960}   # x2 dsf -> 1080x1920 native

HIDE_CSS = "nav, [data-testid='menu-sidebar'], aside { display:none !important; }"
LIVE_SITE = "https://anitas-tiffin.netlify.app"


def human_type(pg, el, text, cps=24):
    el.click()
    for ch in text:
        el.type(ch, delay=1000.0 / cps)


def generating(pg):
    """claude.ai shows a stop control while streaming."""
    for sel in ("button[aria-label*='Stop']", "button[aria-label*='stop']"):
        el = pg.query_selector(sel)
        if el and el.is_visible():
            return True
    return False


def settle(pg, min_quiet=4.0, timeout=300):
    """Wait for generation to START (stop button appears, up to 60s), then END
    (stop button gone + page text stable min_quiet)."""
    t0 = time.time()
    while time.time() - t0 < 60:
        if generating(pg):
            break
        time.sleep(0.5)
    prev, quiet_since = "", time.time()
    while time.time() - t0 < timeout:
        if not generating(pg):
            cur = pg.inner_text("body")
            if cur != prev:
                prev, quiet_since = cur, time.time()
            elif time.time() - quiet_since >= min_quiet:
                return cur
        else:
            quiet_since = time.time()
        time.sleep(0.5)
    return prev


def looks_like_code_done(txt, pg):
    if "</html>" in txt:
        return True
    for pre in pg.query_selector_all("pre"):
        if "</html>" in pre.inner_text().lower():
            return True
    return False


def extract_html(pg, ctx):
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
    ap.add_argument("--out-dir", default="assets/bc02")
    ap.add_argument("--skip-a", action="store_true")
    ap.add_argument("--skip-deploy", action="store_true")
    a = ap.parse_args()
    out_dir = CH / a.out_dir if not Path(a.out_dir).is_absolute() else Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    site_dir = out_dir / "site"
    site_dir.mkdir(exist_ok=True)
    vdir = out_dir / ".rec_tmp"
    vdir.mkdir(exist_ok=True)

    prompt_body = PROMPT_FILE.read_text().split("\n", 2)[2].strip()
    full_prompt = prompt_body + "\n" + CH1_SITE.read_text()
    marks = {}

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

            # 1. paste prompt + current site (insert_text: too long to type)
            box = pg.wait_for_selector("div[contenteditable=true]", timeout=30000)
            box.click()
            mk("prompt_paste")
            pg.keyboard.insert_text(full_prompt)
            pg.wait_for_timeout(1800)
            pg.keyboard.press("Enter")
            mk("prompt_sent")

            # 2. wait; if no complete file yet, the ep19 move ON CAMERA
            txt = settle(pg)
            if not looks_like_code_done(txt, pg):
                pg.add_style_tag(content=HIDE_CSS)
                box = pg.wait_for_selector("div[contenteditable=true]", timeout=30000)
                mk("wami_start")
                human_type(pg, box, "What am I missing?")
                pg.wait_for_timeout(500)
                pg.keyboard.press("Enter")
                mk("wami_sent")
                txt = settle(pg, min_quiet=4, timeout=300)
            mk("code_done")

            pg.wait_for_timeout(1500)
            html, how = extract_html(pg, ctx)
            marks["extract_how"] = how
            marks["extract_chars"] = len(html)
            (site_dir / "index.html").write_text(html)
            print(f">> extracted index.html: {len(html)} chars via {how}")
            pg.wait_for_timeout(2500)
            vid = pg.video.path()
            ctx.close()
        encode(vid, out_dir / "tape_a_claude.mp4", 1080, 1350)

    # 3. deploy the updated file to the SAME live site (CLI = reliable path)
    if not a.skip_deploy:
        r = subprocess.run(["npx", "netlify-cli", "deploy", "--prod",
                            "--dir", str(site_dir), "--site", "665d5de5-419c-4a71-9105-03f16b5862bf"],
                           capture_output=True, text=True, cwd=str(ROOT))
        print(r.stdout[-600:] or r.stderr[-600:])
        marks["deployed"] = r.returncode == 0
        if r.returncode != 0:
            print("!! deploy failed — tape B will show the un-updated site",
                  file=sys.stderr)

    # 4. Tape B: live smart site answers a question, phone viewport
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(PROFILE) + "-phone", headless=False,
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=1.0,
            args=["--disable-blink-features=AutomationControlled"],
            record_video_dir=str(vdir),
            record_video_size={"width": 1080, "height": 1920})
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto(LIVE_SITE, wait_until="load", timeout=90000)
        pg.wait_for_timeout(5000)
        t0 = time.time()
        marks["b_open"] = 0.0
        for _ in range(16):
            pg.mouse.wheel(0, 90)
            pg.wait_for_timeout(200)
        marks["b_scrolled"] = round(time.time() - t0, 2)
        # find the question box the feature added: any visible text input
        inp = None
        for sel in ("input[type=text]", "input:not([type])", "textarea",
                    "[contenteditable=true]"):
            els = [e for e in pg.query_selector_all(sel) if e.is_visible()]
            if els:
                inp = els[0]
                break
        if not inp:
            # maybe behind a launcher button
            for sel in ("button:has-text('Ask')", "[class*='chat']",
                        "[class*='ask']", "[id*='ask']"):
                el = pg.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    pg.wait_for_timeout(1200)
                    break
            for sel in ("input[type=text]", "input:not([type])", "textarea"):
                els = [e for e in pg.query_selector_all(sel) if e.is_visible()]
                if els:
                    inp = els[0]
                    break
        if inp:
            inp.scroll_into_view_if_needed()
            pg.wait_for_timeout(800)
            marks["b_ask_start"] = round(time.time() - t0, 2)
            human_type(pg, inp, "aaj ka menu kya hai?", cps=14)
            pg.wait_for_timeout(400)
            pg.keyboard.press("Enter")
            marks["b_asked"] = round(time.time() - t0, 2)
            pg.wait_for_timeout(3500)
            marks["b_answered"] = round(time.time() - t0, 2)
            # second question: price
            human_type(pg, inp, "thali kitne ka hai?", cps=14)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(3500)
        else:
            print("!! no question box found on the live site", file=sys.stderr)
            marks["b_ask_start"] = None
        pg.wait_for_timeout(2000)
        vidb = pg.video.path()
        ctx.close()
    encode(vidb, out_dir / "tape_b_phone.mp4", 1080, 1920)

    (out_dir / "tapes.marks.json").write_text(json.dumps(marks, indent=1))
    print(json.dumps(marks, indent=1))


if __name__ == "__main__":
    main()
