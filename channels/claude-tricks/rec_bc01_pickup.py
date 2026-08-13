#!/usr/bin/env python3
"""BC01 pickup shot: the TAP-DOWNLOAD moment.

Take 5's automation searched for the file card while Claude was still
"Creating file" — the card was born seconds later. The chat persists in the
profile, so this pickup reopens it, scrolls to the card, DUMPS the candidate
elements (diagnostic), taps the best one, and records the download visual.

  python3 channels/claude-tricks/rec_bc01_pickup.py
"""
import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
CH = ROOT / "channels" / "claude-tricks"
OUT_DIR = CH / "assets" / "bc01"
VIEW = {"width": 540, "height": 960}
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 "
      "Safari/604.1")
HIDE_CSS = "nav, [data-testid='menu-sidebar'], aside { display:none !important; }"


def main():
    vdir = OUT_DIR / ".rec_tmp"
    vdir.mkdir(exist_ok=True)
    marks = {}
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(ROOT / ".browser-profiles" / "claude"), headless=False,
            viewport=VIEW, user_agent=UA, is_mobile=True, has_touch=True,
            device_scale_factor=2.0, accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"],
            record_video_dir=str(vdir), record_video_size=VIEW)
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://claude.ai/recents", wait_until="domcontentloaded",
                timeout=90000)
        pg.wait_for_timeout(6000)
        t0 = time.time()
        mk = lambda k: marks.__setitem__(k, round(time.time() - t0, 2))

        # recents rows are stacked overlay anchors that intercept clicks —
        # read the href off the right row and NAVIGATE instead of clicking
        href = pg.evaluate("""() => {
          for (const a of document.querySelectorAll('a[href^="/chat/"]')) {
            const label = (a.getAttribute('aria-label') || a.innerText || '');
            if (/premium one[- ]page|one[- ]page website/i.test(label))
              return a.getAttribute('href');
          }
          return null;
        }""")
        if not href:
            print("!! chat href not found in recents")
            ctx.close()
            return
        pg.goto("https://claude.ai" + href, wait_until="domcontentloaded",
                timeout=90000)
        pg.wait_for_timeout(6000)
        pg.add_style_tag(content=HIDE_CSS)
        mk("chat_open")

        # scroll to the bottom, then back UP two screens — the file card sits
        # above Claude's closing bullets ("Creating file" zone, take-5 probe)
        for _ in range(14):
            pg.mouse.wheel(0, 900)
            pg.wait_for_timeout(250)
        pg.wait_for_timeout(1000)
        for _ in range(4):
            pg.mouse.wheel(0, -700)
            pg.wait_for_timeout(300)
        pg.wait_for_timeout(1200)
        mk("at_card_zone")

        # diagnostic dump of candidates
        dump = pg.evaluate("""() => {
          const out = [];
          document.querySelectorAll('button,a,[role=button],div').forEach(e => {
            const t = (e.innerText || '').trim();
            if (t && t.length < 90 && /index\\.html|\\.html/i.test(t)) {
              const r = e.getBoundingClientRect();
              if (r.width > 40 && r.height > 20)
                out.push({tag: e.tagName, t: t.slice(0, 70),
                          y: Math.round(r.y), h: Math.round(r.height),
                          test: e.getAttribute('data-testid') || ''});
            }
          });
          return out.slice(0, 12);
        }""")
        print(json.dumps(dump, indent=1))

        # tap the most card-like candidate (small height, contains index.html)
        card = None
        for sel in ("[data-testid*='artifact']",
                    "button:has-text('index.html')",
                    "a:has-text('index.html')",
                    "div[role='button']:has-text('index.html')"):
            el = pg.query_selector(sel)
            if el and el.is_visible():
                card = el
                break
        if card is None:
            for e in pg.query_selector_all("div,button,a"):
                t = (e.inner_text() or "").strip()
                if 0 < len(t) < 60 and "index.html" in t.lower():
                    card = e
                    break
        if card is None:
            # fall back to the FILES DRAWER: the doc-glyph button in the chat
            # header (left of Share) opens a drawer listing the created file
            print(">> no inline card — trying the header files drawer")
            hdr = pg.evaluate("""() => {
              const out = [];
              document.querySelectorAll('button').forEach(e => {
                const r = e.getBoundingClientRect();
                if (r.y < 90 && r.width > 20)
                  out.push({label: e.getAttribute('aria-label') || '',
                            x: Math.round(r.x + r.width / 2),
                            y: Math.round(r.y + r.height / 2)});
              });
              return out;
            }""")
            print(json.dumps(hdr, indent=1))
            target = None
            for b in hdr:
                if any(k in (b["label"] or "").lower()
                       for k in ("file", "artifact", "content", "created")):
                    target = b
                    break
            if target is None and hdr:
                # the drawer glyph sits just left of Share (rightmost is Share)
                xs = sorted(hdr, key=lambda b: -b["x"])
                target = xs[1] if len(xs) > 1 else xs[0]
            if target:
                pg.mouse.click(target["x"], target["y"])
                pg.wait_for_timeout(2500)
                mk("drawer_open")
                (Path(str(vdir)) / "..").resolve()
                pg.screenshot(path=str(OUT_DIR / "pickup_drawer.png"))
                for e in pg.query_selector_all("div,button,a"):
                    t = (e.inner_text() or "").strip()
                    if 0 < len(t) < 70 and ("index.html" in t.lower()
                                            or ".html" in t.lower()):
                        card = e
                        break
        if card is None:
            print("!! no card candidate anywhere — see dumps")
            pg.wait_for_timeout(2500)
            vid = pg.video.path()
            ctx.close()
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i",
                            str(vid), "-vf", "scale=1080:1920:flags=lanczos",
                            "-r", "30", "-c:v", "libx264", "-crf", "19",
                            "-pix_fmt", "yuv420p", "-an",
                            str(OUT_DIR / "tape_pickup.mp4")], check=True)
            return
        card.scroll_into_view_if_needed()
        pg.wait_for_timeout(1400)
        mk("card_seen")
        try:
            with pg.expect_download(timeout=15000) as dl:
                card.click()
            (OUT_DIR / "site").mkdir(exist_ok=True)
            dl.value.save_as(str(OUT_DIR / "site" / "index.html"))
            mk("download_tapped")
            print(">> download captured")
        except Exception as e:
            print(f">> direct tap no download ({e}); trying panel buttons")
            pg.wait_for_timeout(2000)
            mk("panel_open")
            for sel in ("button[aria-label*='Download' i]", "a[download]",
                        "button:has-text('Download')"):
                el = pg.query_selector(sel)
                if el and el.is_visible():
                    try:
                        with pg.expect_download(timeout=12000) as dl:
                            el.click()
                        dl.value.save_as(str(OUT_DIR / "site" / "index.html"))
                        mk("download_tapped")
                        print(f">> download via {sel}")
                        break
                    except Exception as e2:
                        print(f">> {sel}: {e2}")
        pg.wait_for_timeout(3500)
        vid = pg.video.path()
        ctx.close()

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid),
                    "-vf", "scale=1080:1920:flags=lanczos", "-r", "30",
                    "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-an", str(OUT_DIR / "tape_pickup.mp4")], check=True)
    (OUT_DIR / "tape_pickup.marks.json").write_text(json.dumps(marks, indent=1))
    print(json.dumps(marks, indent=1))


if __name__ == "__main__":
    main()
