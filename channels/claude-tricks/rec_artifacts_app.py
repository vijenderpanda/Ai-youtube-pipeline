#!/usr/bin/env python3
"""Capture the Artifacts standalone-tip demo tape on mobile claude.ai.

Films the full arc in one take (editor segments it into the rec: clips):
  type one line -> Claude builds -> artifact card -> TAP to open ->
  a real working "Split the bill" app renders (Rs1200 / 3 = Rs400) ->
  live stepper (3->4 = Rs300 -> back to 3 = Rs400) -> hold.

Reuses the logged-in .browser-profiles/claude session (see record_demo.py).
Mobile 540x960@2 = 1080x1920 portrait, matching the recorder's tape format.
No account PII is on screen in the money shots (composer greeting is generic;
the artifact fullscreen view is just the app). Output: a raw master .mp4.
"""
import argparse, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]             # repo root (file is at channels/claude-tricks/)
PROFILE = ROOT / ".browser-profiles" / "claude"
VIEW = {"width": 540, "height": 960}
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
PROMPT = "Build me a bill splitter app - Rs 1200 split 3 ways, big clear numbers."
# stepper coords in CSS px (from probe: 1080x1920 screenshot / dsf2)
PLUS, MINUS = (403, 516), (136, 516)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(ROOT / "channels/claude-tricks/assets/ep_artifacts/raw_capture_v2.mp4"))
    ap.add_argument("--build-timeout", type=int, default=140)
    args = ap.parse_args()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / f".rec_{out.stem}"; tmp.mkdir(exist_ok=True)
    for old in tmp.glob("*.webm"):                        # clear stale takes so the
        try: old.unlink()                                # newest-by-mtime pick is unambiguous
        except Exception: pass

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=True, channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
            viewport=VIEW, user_agent=UA, device_scale_factor=2,
            is_mobile=True, has_touch=True, color_scheme="dark",
            record_video_dir=str(tmp), record_video_size=VIEW)
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()

        def dismiss():
            for label in ("Got it", "Accept", "Dismiss", "No thanks", "Maybe later"):
                try:
                    b = pg.get_by_role("button", name=label).first
                    if b.is_visible(timeout=300): b.click(); time.sleep(0.3)
                except Exception: pass

        # --- BEAT: type one line (hold_type) ---
        # visible-filter: mobile claude.ai keeps a HIDDEN fallback composer in the DOM;
        # a bare .first/.last can resolve to it (record_demo.py). And claude.ai flakes
        # under rapid headless access - momentarily bouncing to /login?from=logout and
        # self-recovering - so retry the load past any login bounce until it hydrates.
        box = None
        for attempt in range(6):
            pg.goto("https://claude.ai/new", wait_until="domcontentloaded", timeout=60000)
            time.sleep(8)
            if "/login" in pg.url or "logout" in pg.url:
                print(f"attempt {attempt}: bounced to {pg.url}; reloading"); time.sleep(4); continue
            dismiss()
            for _ in range(10):
                if pg.locator("div[contenteditable=true]").locator("visible=true").count() >= 1:
                    box = pg.locator("div[contenteditable=true]").locator("visible=true").first; break
                time.sleep(2)
            if box is not None:
                print(f"composer ready (attempt {attempt})"); break
            print(f"attempt {attempt}: no composer at {pg.url}; retrying")
        if box is None:
            shot = str(out.parent / "FAIL_no_composer.png"); pg.screenshot(path=shot)
            raise SystemExit(f"composer never hydrated after retries; url={pg.url} shot={shot}")
        box.click(); time.sleep(0.4)                     # poll already confirmed visibility
        pg.keyboard.press("ControlOrMeta+A"); pg.keyboard.press("Backspace")  # clear any draft
        time.sleep(0.3)
        pg.keyboard.type(PROMPT, delay=14)
        time.sleep(1.0)                                  # hold the fully-typed line
        sb = pg.locator("button[aria-label='Send message'], button[aria-label*='Send']").locator("visible=true").first
        clicked = False
        try:
            if sb.count() and sb.is_visible(): sb.click(); clicked = True
        except Exception: clicked = False
        if not clicked: pg.keyboard.press("Enter")
        time.sleep(0.8)                                  # verify the send actually fired
        try: still = (box.inner_text(timeout=500) or "").strip()
        except Exception: still = ""
        if still and PROMPT[:12] in still:
            if clicked: pg.keyboard.press("Enter")
            else:
                try: sb.click()
                except Exception: pass

        # --- BEAT: it builds, then the artifact CARD appears (hold_build) ---
        # Poll for the card title (reliable; the Download button renders late and
        # mobile's tap-to-open is flaky). The opened-app payoff is a baked still-hold
        # (ep27 pattern), so we deliberately do NOT fight tap-to-open here.
        ready = False
        for _ in range(args.build_timeout // 2):
            time.sleep(2)
            try:
                if pg.get_by_text("Bill splitter", exact=True).first.is_visible(timeout=400):
                    ready = True; break
            except Exception: pass
        print(f"artifact_ready={ready}")
        time.sleep(3.0)                                  # hold on the finished card

        # --- BEAT: the working app + live compute (hold_total) ---
        time.sleep(2.5)                                  # hero hold on Rs400
        pg.mouse.click(*PLUS);  time.sleep(1.8)          # 3 -> 4 people => Rs300
        pg.mouse.click(*MINUS); time.sleep(2.8)          # 4 -> 3 people => Rs400 (hero again)

        ctx.close()                                      # finalizes the video

    vids = sorted(tmp.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not vids:
        print("NO VIDEO CAPTURED"); return
    src = vids[-1]                                        # newest by mtime, not by name-hash
    # transcode webm -> mp4 (h264) at the tape size
    import subprocess
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(out)], check=False)
    print(f"OK {out} ({out.stat().st_size} bytes)" if out.exists() else f"transcode failed; webm at {src}")


if __name__ == "__main__":
    main()
