#!/usr/bin/env python3
"""BC01 v5 tape: browse the "Vij Codes" demo prop site, then deploy it live via
Netlify Drop on camera (real drag/upload against the real app.netlify.com/drop
service — no mock). Films the whole reaction: local demo site -> Netlify Drop
upload -> live .netlify.app URL.

Requires: `python3 -m http.server 8934` running in
channels/claude-tricks/tapes/bc01_v5_demo_site/ (this script starts it itself
if not already running).

  python3 channels/claude-tricks/rec_bc01_v5_demo.py
"""
import json
import subprocess
import sys
import time
import http.server
import threading
import functools
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
CH = ROOT / "channels" / "claude-tricks"
SITE_DIR = CH / "tapes" / "bc01_v5_demo_site"
SITE_FILE = SITE_DIR / "index.html"
OUT_DIR = CH / "assets" / "epbc01"
VIEW = {"width": 1080, "height": 1350}
PORT = 8934


def start_local_server():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                 directory=str(SITE_DIR))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def find_live_url(pg):
    for el in pg.query_selector_all("a[href*='netlify.app']"):
        href = el.get_attribute("href") or ""
        if ".netlify.app" in href and "app.netlify.com" not in href:
            return href
    return None


def main():
    if not SITE_FILE.exists():
        print(f">> ERROR: demo site not found at {SITE_FILE}")
        sys.exit(2)

    httpd = start_local_server()
    marks = {}
    vdir = OUT_DIR / ".rec_tmp_v5"
    vdir.mkdir(parents=True, exist_ok=True)
    live_url = None

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                str(ROOT / ".browser-profiles" / "claude"), headless=False,
                viewport=VIEW,
                args=["--disable-blink-features=AutomationControlled"],
                record_video_dir=str(vdir), record_video_size=VIEW)
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            t0 = time.time()
            mk = lambda k: marks.__setitem__(k, round(time.time() - t0, 2))

            # --- browse the demo site locally -------------------------------
            pg.goto(f"http://127.0.0.1:{PORT}/index.html",
                    wait_until="domcontentloaded", timeout=30000)
            mk("site_loaded")
            pg.wait_for_timeout(2500)
            # scroll through it a bit so it's obviously a real live-looking page
            pg.mouse.wheel(0, 400)
            pg.wait_for_timeout(1200)
            pg.mouse.wheel(0, 400)
            pg.wait_for_timeout(1500)
            pg.mouse.wheel(0, -800)
            pg.wait_for_timeout(1500)
            mk("site_browse_done")

            # --- go to Netlify Drop and deploy for real ---------------------
            pg.goto("https://app.netlify.com/drop", wait_until="domcontentloaded",
                    timeout=90000)
            mk("drop_page_loaded")
            pg.wait_for_timeout(6000)

            n_inputs = len(pg.query_selector_all("input[type=file]"))
            marks["drop_inputs"] = n_inputs
            print(f">> inputs[type=file]: {n_inputs}")

            inputs = pg.query_selector_all("input[type=file]")
            file_inp = None
            for inp in inputs:
                wd = inp.get_attribute("webkitdirectory")
                if wd is None and file_inp is None:
                    file_inp = inp
            if file_inp is None and inputs:
                file_inp = inputs[0]

            if file_inp is not None:
                mk("upload_start")
                file_inp.set_input_files(str(SITE_FILE))
                print(">> set_input_files(index.html)")
                for _ in range(90):
                    pg.wait_for_timeout(1000)
                    live_url = find_live_url(pg)
                    if live_url:
                        break

            if not live_url:
                mk("drag_start")
                try:
                    cdp = ctx.new_cdp_session(pg)
                    cx, cy = VIEW["width"] / 2, VIEW["height"] / 2
                    data = {"items": [], "files": [str(SITE_FILE)],
                            "dragOperationsMask": 1}
                    for typ in ("dragEnter", "dragOver", "drop"):
                        cdp.send("Input.dispatchDragEvent",
                                 {"type": typ, "x": cx, "y": cy, "data": data})
                        pg.wait_for_timeout(350)
                    print(">> CDP drag dispatched")
                except Exception as e:
                    print(f">> CDP drag failed: {e}")
                for _ in range(30):
                    pg.wait_for_timeout(1000)
                    live_url = find_live_url(pg)
                    if live_url:
                        break

            mk("live_url_found")
            marks["live_url"] = live_url
            print(f">> live URL: {live_url}")

            if live_url:
                pg.wait_for_timeout(2000)
                new_pg = ctx.new_page()
                new_pg.goto(live_url, wait_until="domcontentloaded", timeout=30000)
                mk("visited_live_url")
                new_pg.wait_for_timeout(4000)

            pg.wait_for_timeout(3000)
            vid = pg.video.path()
            ctx.close()
    finally:
        httpd.shutdown()

    if not live_url:
        print(">> FAILED: no live Netlify URL captured")
        (OUT_DIR / "v5_demo_marks.json").write_text(json.dumps(marks, indent=1))
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_mp4 = OUT_DIR / "bc01_v5_netlify_drop.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid),
                    "-vf", "scale=1080:1350", "-r", "30", "-c:v", "libx264",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-an",
                    str(out_mp4)], check=True)
    (OUT_DIR / "v5_demo_marks.json").write_text(json.dumps(marks, indent=1))
    print(json.dumps(marks, indent=1))
    print(f">> saved {out_mp4}")
    sys.exit(0)


if __name__ == "__main__":
    main()
