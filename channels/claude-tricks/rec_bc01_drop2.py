#!/usr/bin/env python3
"""BC01 tape A2: Netlify Drop deploy, take 2.

The synthetic DragEvent in take 1 didn't fire Netlify's React dropzone.
This take tries, in order:
  1. CDP Input.dispatchDragEvent with a real file payload (browser-level drag —
     the page can't tell it from a human drop)
  2. any <input type=file> on the page (same deploy pipeline, hidden picker)
Films the whole reaction: dropzone -> upload -> live .netlify.app URL.
On success rewrites tapes.marks.json (live_url + drop take-2 marks) so
rec_bc01_build.py --skip-a can shoot tape B against the real site.

  python3 channels/claude-tricks/rec_bc01_drop2.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
CH = ROOT / "channels" / "claude-tricks"
OUT_DIR = CH / "assets" / "bc01"
SITE = OUT_DIR / "site" / "index.html"
VIEW = {"width": 1080, "height": 1350}


def find_live_url(pg):
    for el in pg.query_selector_all("a[href*='netlify.app']"):
        href = el.get_attribute("href") or ""
        if ".netlify.app" in href and "app.netlify.com" not in href:
            return href
    return None


def main():
    marks = json.loads((OUT_DIR / "tapes.marks.json").read_text())
    vdir = OUT_DIR / ".rec_tmp"
    vdir.mkdir(exist_ok=True)
    live_url = None

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(ROOT / ".browser-profiles" / "claude"), headless=False,
            viewport=VIEW,
            args=["--disable-blink-features=AutomationControlled"],
            record_video_dir=str(vdir), record_video_size=VIEW)
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://app.netlify.com/drop", wait_until="domcontentloaded",
                timeout=90000)
        pg.wait_for_timeout(7000)
        t0 = time.time()
        mk = lambda k: marks.__setitem__(k, round(time.time() - t0, 2))
        marks["drop2_url"] = pg.url

        # diagnose what's actually on the page
        n_inputs = len(pg.query_selector_all("input[type=file]"))
        body_head = pg.inner_text("body")[:300].replace("\n", " | ")
        print(f">> inputs[type=file]: {n_inputs}\n>> body: {body_head}")
        marks["drop2_inputs"] = n_inputs

        # --- attempt 1: single-file input (page text: "or choose a file") ----
        mk("drop2_input_start")
        inputs = pg.query_selector_all("input[type=file]")
        file_inp = None
        for inp in inputs:
            wd = inp.get_attribute("webkitdirectory")
            print(f">> input: webkitdirectory={wd is not None} "
                  f"accept={inp.get_attribute('accept')}")
            if wd is None and file_inp is None:
                file_inp = inp
        if file_inp is None and inputs:
            file_inp = inputs[0]
        if file_inp is not None:
            file_inp.set_input_files(str(SITE))
            print(">> set_input_files(index.html)")
            for _ in range(90):
                pg.wait_for_timeout(1000)
                live_url = find_live_url(pg)
                if live_url:
                    break

        # --- attempt 2: CDP real drag ----------------------------------------
        if not live_url:
            mk("drop2_drag_start")
            try:
                cdp = ctx.new_cdp_session(pg)
                cx, cy = VIEW["width"] / 2, VIEW["height"] / 2
                data = {"items": [], "files": [str(SITE)],
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

        mk("drop2_url_live")
        marks["live_url"] = live_url
        print(f">> live URL: {live_url}")
        pg.wait_for_timeout(6000)
        vid = pg.video.path()
        ctx.close()

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid),
                    "-vf", "scale=1080:1350", "-r", "30", "-c:v", "libx264",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-an",
                    str(OUT_DIR / "tape_a_drop.mp4")], check=True)
    (OUT_DIR / "tapes.marks.json").write_text(json.dumps(marks, indent=1))
    print(json.dumps({k: v for k, v in marks.items()
                      if k.startswith("drop2") or k == "live_url"}, indent=1))
    sys.exit(0 if live_url else 1)


if __name__ == "__main__":
    main()
