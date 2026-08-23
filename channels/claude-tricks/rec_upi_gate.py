#!/usr/bin/env python3
"""GATE TEST for episode _upi — does Claude return a GROUPED per-merchant
breakdown, or prose?

This is the one question the whole film rests on. Beat 5 (12-17s) frames the
real reply scrolling; if the answer comes back as paragraphs there is no proof
beat and the episode does not exist. Established 2026-08-20.

Deliberately run on SYNTHETIC screenshots — invented merchants in the same
SHAPE as the owner's real data (Blinkit-heavy, three shots with ~250px overlap).
That answers the capability question with zero real-PII exposure. The real tape
is a separate, consented shoot.

It also tests the dedup instruction, because the shots genuinely overlap.

Reuses .browser-profiles/claude (mobile 540x960@2 = 1080x1920), the same rig as
rec_wheel_app.py / rec_habit_app.py.
"""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / ".browser-profiles" / "claude"
SP = Path("/private/tmp/claude-501/-Users-vijenderpanda-Ai-youtube-pipeline/"
          "b2fdbc7d-44b8-4f9f-9e97-025e976bb199/scratchpad")
SHOTS = [SP / f"gate_shot{i}.png" for i in (1, 2, 3)]

# the exact line from the beat sheet — char-for-char what the video will show
PROMPT = (
    "My UPI history - the shots overlap so count each payment once, group by category, "
    "keep people as one line with no names, and tell me which app took the most."
)


def _dismiss(pg):
    for label in ("Got it", "Accept", "Dismiss", "No thanks", "Maybe later", "Close"):
        try:
            b = pg.get_by_role("button", name=label).first
            if b.is_visible(timeout=300):
                b.click(); time.sleep(0.3)
        except Exception:
            pass


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=False,
            viewport={"width": 540, "height": 960}, device_scale_factor=2,
            is_mobile=True, has_touch=True,
            user_agent=("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/126 Mobile Safari/537.36"),
        )
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        box = None
        for attempt in range(5):
            pg.goto("https://claude.ai/new", wait_until="domcontentloaded", timeout=60000)
            time.sleep(8)
            if "/login" in pg.url:
                print(f"attempt {attempt}: bounced to login"); time.sleep(4); continue
            _dismiss(pg)
            for _ in range(10):
                loc = pg.locator("div[contenteditable=true]").locator("visible=true")
                if loc.count():
                    box = loc.first; break
                time.sleep(2)
            if box: break
        if not box:
            print("ABORT: no composer"); ctx.close(); sys.exit(3)
        print(">> composer ready")

        # attach the three shots
        fi = pg.locator("input[type=file]").first
        fi.set_input_files([str(s) for s in SHOTS])
        print(">> attached 3 screenshots")
        time.sleep(9)  # thumbnails must finish uploading before send

        box.click(); time.sleep(0.4)
        pg.keyboard.type(PROMPT, delay=8)
        time.sleep(1.0)
        pg.keyboard.press("Enter")
        print(">> sent; waiting for the reply to settle")

        last, stable = "", 0
        for _ in range(90):
            time.sleep(2)
            try:
                txt = pg.locator("main").inner_text(timeout=5000)
            except Exception:
                continue
            if txt == last:
                stable += 1
                if stable >= 4:
                    break
            else:
                stable = 0; last = txt
        (SP / "gate_reply.txt").write_text(last)
        pg.screenshot(path=str(SP / "gate_reply.png"), full_page=True)
        print(f">> reply captured: {len(last)} chars -> gate_reply.txt / gate_reply.png")
        ctx.close()


if __name__ == "__main__":
    main()
