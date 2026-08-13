#!/usr/bin/env python3
"""BC01 v3 mobile tapes — the WHOLE journey on a phone (VJ 2026-08-13):
"you can straight away do it live with me, just with your mobile phone…
a novice can pause and do the steps."

Tape M (540x960 mobile emulation -> 1080x1920 upscale, one continuous take):
  1. claude.ai (mobile web): PASTE the pinned prompt -> wait -> it asks
  2. FAST answers, texting pace (VJ: "fast paced answering to match the VO")
  3. the site comes back -> tap DOWNLOAD -> index.html lands on the phone
     (the captured download IS the artifact we redeploy — full continuity)
  4. same browser: app.netlify.com/drop -> "choose a file" -> uploading -> live
Tape M2 (after the fresh file is redeployed to anitas-tiffin.netlify.app):
  the live site, scrolled slowly on the phone, WhatsApp CTA hover.

  python3 channels/claude-tricks/rec_bc01_mobile.py [--skip-m]
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
CH = ROOT / "channels" / "claude-tricks"
OUT_DIR = CH / "assets" / "bc01"
SITE_DIR = OUT_DIR / "site"
PROMPT_FILE = OUT_DIR / "SHARE-PROMPT.txt"
PROFILE = ROOT / ".browser-profiles" / "claude"

VIEW = {"width": 540, "height": 960}
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 "
      "Safari/604.1")
HIDE_CSS = "nav, [data-testid='menu-sidebar'], aside { display:none !important; }"

ANSWERS = [
    "Anita's Tiffin",
    "Home-style tiffin meals. Rajma Chawal Rs 120, Paneer Thali Rs 150, Dal + 4 Roti Rs 90",
    "Working folks and students in Indiranagar, Bengaluru - lunch and dinner",
    "99999 99999",
    "warm & homely",
    "Fresh ghar-ka-khana cooked the same morning. Free delivery within 3 km. Order by 10 AM for lunch.",
]


def human_type(el, text, cps=34):
    el.click()
    for ch in text:
        el.type(ch, delay=1000.0 / cps)


def hide_greeting(pg):
    """The mobile empty-chat greeting shows the ACCOUNT HOLDER'S REAL NAME
    (take 2 leaked it on camera). Hide any small element carrying it."""
    pg.evaluate("""() => {
      document.querySelectorAll('h1,h2,h3,div,span').forEach(e => {
        const t = (e.textContent || '').trim();
        // leaf-only: short text, and NEVER an ancestor of the composer
        // (take 3 hid a wrapper div and the chat input vanished with it)
        if (t.length && t.length < 60 &&
            /back at it|vijender/i.test(t) &&
            !e.querySelector('[contenteditable], [data-testid="chat-input"]'))
          e.style.visibility = 'hidden';
      });
    }""")


def send_message(pg):
    """Mobile claude.ai: Enter = NEWLINE (take 2 stacked everything in the
    composer, nothing ever sent). Tap the send button; Enter is fallback."""
    for sel in ("button[aria-label*='Send' i]",
                "button[type='submit']",
                "fieldset button:last-of-type"):
        el = pg.query_selector(sel)
        if el and el.is_visible():
            el.click()
            return sel
    pg.keyboard.press("Enter")
    return "enter-fallback"


def last_response(pg):
    els = pg.query_selector_all(".font-claude-response")
    return els[-1].inner_text() if els else ""


def settle(pg, quiet=2.5, timeout=75, min_wait=6.0):
    """Wait until the PAGE BODY stops changing. The desktop-only
    .font-claude-response class does not exist on mobile-width claude.ai —
    take 1 burned the full timeout on every turn because of it (2026-08-13).
    min_wait guards against settling before the reply even starts."""
    t0, prev, since = time.time(), "", time.time()
    while time.time() - t0 < timeout:
        try:
            cur = pg.inner_text("body")
        except Exception:
            cur = prev
        if cur != prev:
            prev, since = cur, time.time()
        elif (time.time() - since >= quiet
              and time.time() - t0 >= min_wait):
            return cur
        time.sleep(0.4)
    return prev


def code_done(txt, pg):
    if "</html>" in txt or "</body>" in txt:
        return True
    for pre in pg.query_selector_all("pre"):
        t = pre.inner_text()
        if "<!doctype" in t.lower() or "</html>" in t.lower():
            return True
    # artifact chip present + response settled with a handover line
    return bool(pg.query_selector("[data-testid*='artifact'],"
                                  " [aria-label*='artifact']"))


def encode(src, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-vf", "scale=1080:1920:flags=lanczos", "-r", "30",
                    "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-an", str(out)], check=True)


def try_download(pg, ctx, marks, mk):
    """Find + tap a Download affordance; capture the file. Returns path|None."""
    # the file/artifact CARD sits above the handover text — scroll up to it
    # and tap it first (take 4: "Download the index.html file above")
    card = None
    for el in pg.query_selector_all(
            "[data-testid*='artifact'], div[role='button'], button, a"):
        t = (el.inner_text() or "")[:90].lower()
        if "index.html" in t and "netlify" not in t and len(t) < 60:
            card = el
            break
    if card:
        card.scroll_into_view_if_needed()
        pg.wait_for_timeout(1200)
        mk("file_card_seen")
        try:
            with pg.expect_download(timeout=12000) as dl:
                card.click()
            path = SITE_DIR / "index.html"
            dl.value.save_as(str(path))
            mk("download_tapped")
            marks["download_via"] = "file-card"
            print(f">> downloaded via file card -> {path}")
            return path
        except Exception as e:
            print(f">> file-card tap did not download directly: {e}")
            pg.wait_for_timeout(1500)
    cands = [
        "button[aria-label*='Download']",
        "a[download]",
        "button:has-text('Download')",
    ]
    # the artifact bubble often needs a tap first to open its panel
    art = pg.query_selector("[data-testid*='artifact'], "
                            "[aria-label*='artifact']")
    if art:
        art.click()
        pg.wait_for_timeout(2500)
        mk("artifact_open")
        # panels tuck Download behind a kebab/menu
        for menu_sel in ("button[aria-label*='More']",
                         "button[aria-label*='menu']"):
            m = pg.query_selector(menu_sel)
            if m:
                m.click()
                pg.wait_for_timeout(1200)
                break
    for sel in cands:
        el = pg.query_selector(sel)
        if el and el.is_visible():
            try:
                with pg.expect_download(timeout=15000) as dl:
                    el.click()
                path = SITE_DIR / "index.html"
                dl.value.save_as(str(path))
                mk("download_tapped")
                marks["download_via"] = sel
                print(f">> downloaded via {sel} -> {path}")
                return path
            except Exception as e:
                print(f">> download via {sel} failed: {e}")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-m", action="store_true",
                    help="only re-shoot tape M2 (live site)")
    a = ap.parse_args()
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    vdir = OUT_DIR / ".rec_tmp"
    vdir.mkdir(exist_ok=True)
    marks_path = OUT_DIR / "tape_m.marks.json"
    marks = (json.loads(marks_path.read_text())
             if marks_path.exists() else {})

    prompt_body = PROMPT_FILE.read_text().split("\n", 2)[2].strip()

    if not a.skip_m:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                str(PROFILE), headless=False, viewport=VIEW,
                user_agent=UA, is_mobile=True, has_touch=True,
                device_scale_factor=2.0, accept_downloads=True,
                args=["--disable-blink-features=AutomationControlled"],
                record_video_dir=str(vdir), record_video_size=VIEW)
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.goto("https://claude.ai/new", wait_until="domcontentloaded",
                    timeout=90000)
            pg.wait_for_timeout(8000)
            if "login" in pg.url:
                print("!! not logged in", file=sys.stderr)
                sys.exit(2)
            pg.add_style_tag(content=HIDE_CSS)
            hide_greeting(pg)
            t0 = time.time()
            mk = lambda k: marks.__setitem__(k, round(time.time() - t0, 2))

            box = pg.wait_for_selector("div[contenteditable=true]",
                                       timeout=30000)
            box.click()
            mk("m_paste")
            pg.keyboard.insert_text(prompt_body)
            pg.wait_for_timeout(1400)
            marks["m_send_via"] = send_message(pg)
            mk("m_sent")

            ai = 0
            for _ in range(10):
                txt = settle(pg, min_wait=6.0 if ai < len(ANSWERS) else 12.0,
                             timeout=75 if ai < len(ANSWERS) else 200)
                if code_done(txt, pg) and ai >= len(ANSWERS):
                    mk("m_code_done")
                    break
                if ai >= len(ANSWERS):
                    settle(pg, quiet=3, timeout=200, min_wait=15)
                    mk("m_code_done")
                    break
                pg.add_style_tag(content=HIDE_CSS)
                box = pg.wait_for_selector("div[contenteditable=true]",
                                           timeout=30000)
                mk(f"m_a{ai + 1}_start")
                human_type(box, ANSWERS[ai])
                pg.wait_for_timeout(350)
                send_message(pg)
                pg.wait_for_timeout(700)
                # verify it actually left the composer
                if len((box.inner_text() or "").strip()) > 2:
                    send_message(pg)
                mk(f"m_a{ai + 1}_sent")
                ai += 1
            marks["m_answers_used"] = ai

            pg.wait_for_timeout(1500)
            got = try_download(pg, ctx, marks, mk)
            if not got:
                # extraction fallback keeps the pipeline alive; the download
                # beat then reuses the copy affordance visual
                best = ""
                for pre in pg.query_selector_all("pre"):
                    t = pre.inner_text()
                    if ("<!doctype" in t.lower() or "<html" in t.lower()) \
                            and len(t) > len(best):
                        best = t
                if len(best) > 400:
                    (SITE_DIR / "index.html").write_text(best)
                    marks["download_via"] = "dom-fallback"
                    print(f">> DOM fallback extraction: {len(best)} chars")
            pg.wait_for_timeout(2000)

            # --- netlify drop, same phone browser ---------------------------
            pg.goto("https://app.netlify.com/drop",
                    wait_until="domcontentloaded", timeout=90000)
            pg.wait_for_timeout(6000)
            mk("m_drop_page")
            # the teaching tap: "choose a file"
            choose = pg.query_selector("text=/choose a\\s+file/i")
            if choose:
                choose.hover()
                pg.wait_for_timeout(900)
            inputs = pg.query_selector_all("input[type=file]")
            file_inp = None
            for inp in inputs:
                if inp.get_attribute("webkitdirectory") is None:
                    file_inp = inp
                    break
            if file_inp:
                file_inp.set_input_files(str(SITE_DIR / "index.html"))
                mk("m_file_chosen")
                live = None
                for _ in range(75):
                    pg.wait_for_timeout(1000)
                    m2 = re.search(r"https?://[a-z0-9-]+\.netlify\.app",
                                   pg.inner_text("body"))
                    if m2 and "app.netlify" not in m2.group(0):
                        live = m2.group(0)
                        break
                mk("m_drop_live")
                marks["m_drop_url"] = live
                print(f">> drop live: {live}")
            pg.wait_for_timeout(5000)
            vid = pg.video.path()
            ctx.close()
        encode(vid, OUT_DIR / "tape_m.mp4")

    # --- redeploy the FRESH file, then tape M2 on the live site -------------
    tok = ""
    for ln in (ROOT / "secrets" / "factory.env").read_text().splitlines():
        if ln.startswith("NETLIFY_AUTH_TOKEN="):
            tok = ln.split("=", 1)[1].strip()
    if tok and (SITE_DIR / "index.html").exists():
        r = subprocess.run(
            ["npx", "-y", "netlify-cli", "deploy", "--dir", str(SITE_DIR),
             "--prod", "--site", "665d5de5-419c-4a71-9105-03f16b5862bf"],
            env={**__import__("os").environ, "NETLIFY_AUTH_TOKEN": tok},
            capture_output=True, text=True, timeout=300)
        print(">> redeploy:", "ok" if r.returncode == 0 else r.stderr[-200:])

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(PROFILE) + "-phone", headless=False, viewport=VIEW,
            user_agent=UA, is_mobile=True, has_touch=True,
            device_scale_factor=2.0,
            args=["--disable-blink-features=AutomationControlled"],
            record_video_dir=str(vdir), record_video_size=VIEW)
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://anitas-tiffin.netlify.app", wait_until="load",
                timeout=90000)
        pg.wait_for_timeout(4500)
        for _ in range(26):
            pg.mouse.wheel(0, 80)
            pg.wait_for_timeout(200)
        pg.wait_for_timeout(1000)
        cta = pg.query_selector("a[href*='wa.me']")
        if cta:
            cta.scroll_into_view_if_needed()
            pg.wait_for_timeout(800)
            cta.hover()
        pg.wait_for_timeout(2400)
        vid2 = pg.video.path()
        ctx.close()
    encode(vid2, OUT_DIR / "tape_m2.mp4")

    marks_path.write_text(json.dumps(marks, indent=1))
    print(json.dumps(marks, indent=1))


if __name__ == "__main__":
    main()
