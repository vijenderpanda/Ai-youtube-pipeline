#!/usr/bin/env python3
"""Capture the Sleep Tracker demo — franchise entry #5 (EP15).

WHY THIS ANGLE (2026-08-20): Habit Tracker pulled 213 views day one vs Working
App's 19 — same franchise, back-to-back. The delta is not the format, it is that
the thing built is PERSONALLY USEFUL. So: a sleep tracker. Everybody sleeps.

Same proven mechanics as rec_wheel_app.py (franchise #4): the artifact is filmed
OPENED AND RUNNING, never a baked still — continuous motion is the lever on the
Shorts-feed-selection ceiling. Here the on-camera interaction is the LOG button:
tap it and last night's total + the 7-day strip populate for real.

One take, mobile 540x960@2 = 1080x1920:
  type one line -> Claude builds -> artifact card -> OPEN fullscreen ->
  tap LOG -> last night + the 7-day strip fill in -> hold.

Reuses the logged-in .browser-profiles/claude session. Mobile config is required:
a desktop UA trips claude.ai's Cloudflare bot wall (see rec_habit_app.py).
"""
import argparse, subprocess, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]             # repo root (file is at channels/claude-tricks/)
PROFILE = ROOT / ".browser-profiles" / "claude"
ASSETS = ROOT / "channels/claude-tricks/assets/ep15"
VIEW = {"width": 540, "height": 960}
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

# ONE short line so "type one line" is literal on camera. Asking for one big
# centered LOG button gives a single, predictable tap target to film (the wheel
# episode's SPIN lesson: name the control in the prompt so it exists to click).
PROMPT = ("Build me a sleep tracker - set last night's bedtime and wake time, one big "
          "LOG SLEEP button, and a 7 day bar strip of hours slept.")
TITLE_CANDS = ["Sleep tracker", "Sleep Tracker", "Sleep log", "Sleep Log",
               "Sleep tracking app", "Weekly sleep tracker"]
# Control labels to hunt inside the artifact iframe, best-first.
ACT_NAMES = ("LOG SLEEP", "Log Sleep", "Log sleep", "LOG", "Log", "Save", "SAVE",
             "Add", "ADD", "Log night", "Track")


def _dismiss(pg):
    for label in ("Got it", "Accept", "Dismiss", "No thanks", "Maybe later", "Close"):
        try:
            b = pg.get_by_role("button", name=label).first
            if b.is_visible(timeout=300):
                b.click(); time.sleep(0.3)
        except Exception:
            pass


def _composer(pg):
    """Hydrate past claude.ai's login-bounce flake + the hidden fallback composer."""
    for attempt in range(6):
        pg.goto("https://claude.ai/new", wait_until="domcontentloaded", timeout=60000)
        time.sleep(8)
        if "/login" in pg.url or "logout" in pg.url:
            print(f"attempt {attempt}: bounced to {pg.url}; reloading"); time.sleep(4); continue
        _dismiss(pg)
        for _ in range(10):
            if pg.locator("div[contenteditable=true]").locator("visible=true").count() >= 1:
                print(f"composer ready (attempt {attempt})")
                return pg.locator("div[contenteditable=true]").locator("visible=true").first
            time.sleep(2)
        print(f"attempt {attempt}: no composer at {pg.url}; retrying")
    return None


def _send(pg, box, prompt):
    box.click(); time.sleep(0.4)
    pg.keyboard.press("ControlOrMeta+A"); pg.keyboard.press("Backspace"); time.sleep(0.3)
    pg.keyboard.type(prompt, delay=14)
    time.sleep(1.2)                                    # hold the fully-typed line on camera
    sb = pg.locator("button[aria-label='Send message'], button[aria-label*='Send']").locator("visible=true").first
    clicked = False
    try:
        if sb.count() and sb.is_visible():
            sb.click(); clicked = True
    except Exception:
        clicked = False
    if not clicked:
        pg.keyboard.press("Enter")
    time.sleep(0.8)
    try:
        still = (box.inner_text(timeout=500) or "").strip()
    except Exception:
        still = ""
    if still and prompt[:12] in still:                 # send didn't take — try the other path
        if clicked:
            pg.keyboard.press("Enter")
        else:
            try: sb.click()
            except Exception: pass


def _wait_card(pg, timeout_s):
    """Wait for the artifact to exist AND the build to stop churning.

    Title matching is unreliable — Claude names the artifact freely ("Dinner
    decision spinner wheel" missed every candidate on the first take, so we
    burned the whole timeout and opened while it was still editing, and the
    panel closed under us). The OPEN BUTTON is the title-independent signal:
    `button[aria-label^="View "]`. Then require it to be stable (Claude often
    does extra edit passes — "Remove unused placeholder function" — each of
    which re-renders and can close the panel), so only open once it settles.
    """
    # ":not([aria-label='View all'])" matters — the left-nav "View all" link is a
    # button[aria-label^="View "] too, and matching it made take 2 "settle" at ~10s
    # and click a nav item while Claude was still building for another ~140s.
    open_sel = 'button[aria-label^="View "]:not([aria-label="View all"])'
    seen_at = None
    stable_for = 0
    for i in range(timeout_s // 2):
        time.sleep(2)
        try:
            n = pg.locator(open_sel).count()
        except Exception:
            n = 0
        if n:
            if seen_at is None:
                seen_at = i; print(f"artifact button present at ~{i*2}s")
            # streaming stopped? the composer's stop button disappears when idle
            try:
                busy = pg.locator("button[aria-label*='Stop'], button[aria-label*='stop']").count()
            except Exception:
                busy = 0
            stable_for = stable_for + 2 if not busy else 0
            if stable_for >= 10:                       # 10s quiet => the build settled
                try:
                    label = pg.locator(open_sel).first.get_attribute("aria-label") or ""
                except Exception:
                    label = ""
                print(f"artifact settled ({label!r})"); return label.replace("View ", "").strip() or True
        else:
            stable_for = 0
    print("artifact: never settled (proceeding anyway)")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(ASSETS / "raw_capture.mp4"))
    ap.add_argument("--build-timeout", type=int, default=300)
    ap.add_argument("--taps", type=int, default=2, help="how many times to tap LOG on camera")
    a = ap.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / f".rec_{out.stem}"; tmp.mkdir(exist_ok=True)
    for old in tmp.glob("*.webm"):
        try: old.unlink()
        except Exception: pass

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=True, channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
            viewport=VIEW, user_agent=UA, device_scale_factor=2,
            is_mobile=True, has_touch=True, color_scheme="dark",
            record_video_dir=str(tmp), record_video_size=VIEW)
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()

        box = _composer(pg)
        if box is None:
            shot = str(out.parent / "FAIL_no_composer.png"); pg.screenshot(path=shot)
            ctx.close(); raise SystemExit(f"composer never hydrated; url={pg.url} shot={shot}")

        _send(pg, box, PROMPT)                          # BEAT: type one line
        title = _wait_card(pg, a.build_timeout)         # BEAT: it builds -> card
        time.sleep(2.5)

        # BEAT: OPEN the artifact fullscreen, then VERIFY the app is really on
        # screen. An edit pass can close the panel right after it opens, which is
        # how take 1 ended up filming 200s of chat — so confirm the SPIN control
        # is visible and re-open (up to 3 tries) before filming anything.
        def find_act():
            # The app renders INSIDE the artifact iframe. pg.get_by_role() does NOT
            # pierce iframes — take 3 "found" a page-level SPIN and clicking it did
            # nothing (wheel never rotated, no result). So resolve the control in the
            # FRAME, and keep a centre-coordinate click as the always-works fallback
            # (the prompt asks for the SPIN button dead-centre).
            try:
                if pg.locator("iframe").count() == 0:
                    return None, None
            except Exception:
                return None, None
            try:
                fr = pg.frame_locator("iframe").last
                for name in ACT_NAMES:
                    c = fr.get_by_role("button", name=name).first
                    if c.count():
                        return c, f"iframe-role:{name}"
                for name in ACT_NAMES:
                    c = fr.get_by_text(name, exact=True).first
                    if c.count():
                        return c, f"iframe-text:{name}"
            except Exception as e:
                print(f"iframe control lookup: {e!r}")
            return None, "centre-fallback"

        spin, how = None, None
        for attempt in range(3):
            try:
                b = pg.locator('button[aria-label^="View "]:not([aria-label=\"View all\"])').first
                if b.count():
                    b.click(force=True); print(f"open attempt {attempt}: clicked")
            except Exception as e:
                print(f"open attempt {attempt} failed: {e!r}")
            time.sleep(5.0)
            _dismiss(pg)
            spin, how = find_act()
            if spin is not None:
                print(f"APP IS OPEN — action control via {how}"); break
            print(f"open attempt {attempt}: app not visible yet")
        if spin is None:
            pg.screenshot(path=str(out.parent / "FAIL_app_not_open.png"))
            print("!! app never rendered on screen — see FAIL_app_not_open.png")
        pg.screenshot(path=str(out.parent / "still_open.png"))   # hero still (hook/thumb source)
        time.sleep(2.0)                                          # hold the app before touching it

        CX, CY = VIEW["width"] // 2, int(VIEW["height"] * 0.56)    # LOG button band (form sits mid-page)
        for i in range(a.taps):
            before = None
            try:
                before = pg.screenshot()
            except Exception:
                pass
            clicked = False
            try:
                if spin is not None:
                    spin.click(force=True, timeout=4000); clicked = True
                    print(f"spin {i+1}: iframe control clicked")
            except Exception as e:
                print(f"spin {i+1}: iframe click failed ({e!r})")
            if not clicked:
                pg.mouse.click(CX, CY); print(f"spin {i+1}: centre click ({CX},{CY})")
            time.sleep(1.2)
            try:                                        # did anything actually move?
                after = pg.screenshot()
                if before is not None and after == before:
                    pg.mouse.click(CX, CY)
                    print(f"spin {i+1}: no motion detected -> centre click ({CX},{CY})")
            except Exception:
                pass
            time.sleep(5.0)                             # let the strip populate + settle, on camera
        time.sleep(3.0)                                 # hold the filled-in week

        pg.screenshot(path=str(out.parent / "still_result.png"))
        ctx.close()

    vids = sorted(tmp.glob("*.webm"), key=lambda q: q.stat().st_mtime)
    if not vids:
        print("NO VIDEO CAPTURED"); return
    src = vids[-1]                                       # newest by mtime, not name-hash
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(out)], check=False)
    print(f"OK {out} ({out.stat().st_size} bytes)" if out.exists() else f"transcode failed; webm at {src}")


if __name__ == "__main__":
    main()
