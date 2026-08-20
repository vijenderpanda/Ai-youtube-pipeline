#!/usr/bin/env python3
"""Capture the reaction-time GAME demo — franchise entry #4.

Why this game (2026-08-20 analytics read): the channel's builds win distribution
but lose retention (habit tracker 39.8% AVP vs a 50.9% tip median). A game has
intrinsic pull, and a REACTION TEST specifically fixes our two measured problems:
  · the payoff is a NUMBER that arrives (Plate 09 — "the single highest-value
    block for a data-driven short"), not a static screen;
  · it gives a real reason to comment ("what's your reaction time?"), unlike the
    generic "what should I build next?" which returned 0 comments on 218 views.

Capture-wise it is also the safest playable thing to film: ONE full-screen tap
target, so there are no per-generation coordinates to guess (the failure that
cost four takes on the wheel).

The hard part is that the green cue fires after a RANDOM delay, so we cannot
pre-schedule the tap. We poll a small centre crop and tap when the frame turns
green — the poll latency (~150-350ms) lands a realistic, human-looking score.

One take, mobile 540x960@2 = 1080x1920:
  type one line -> Claude builds -> artifact card -> OPEN fullscreen ->
  start -> wait for green -> TAP -> the reaction time appears -> play again.
"""
import argparse, subprocess, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / ".browser-profiles" / "claude"
ASSETS = ROOT / "channels/claude-tricks/assets/ep_game"
VIEW = {"width": 540, "height": 960}
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

# "big full screen" alone was not enough — take 2 rendered a bordered box inside
# the chat, with claude's bullet list and the composer still in frame. Naming the
# edge-to-edge fill explicitly is what gets a full-bleed artifact worth filming.
PROMPT = ("Build me a reaction time game that fills the whole screen edge to edge - "
          "no borders, no header, just colour. Red means wait, green means tap, "
          "and show my reaction time in milliseconds in huge numbers.")

# `View all` is the left-nav link; `View request/response` is the tool-call
# inspector that appears when a build step fails. Neither is the artifact, and
# clicking either loses the take.
ART_SEL = ('button[aria-label^="View "]'
           ':not([aria-label="View all"])'
           ':not([aria-label*="request"])'
           ':not([aria-label*="response"])')


def _dismiss(pg):
    for label in ("Got it", "Accept", "Dismiss", "No thanks", "Maybe later", "Close"):
        try:
            b = pg.get_by_role("button", name=label).first
            if b.is_visible(timeout=300):
                b.click(); time.sleep(0.3)
        except Exception:
            pass


def _composer(pg):
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
    time.sleep(1.2)
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
    if still and prompt[:12] in still:
        if clicked:
            pg.keyboard.press("Enter")
        else:
            try: sb.click()
            except Exception: pass


def _wait_settled(pg, timeout_s):
    """Artifact exists AND the build has stopped churning. `View all` is the
    left-nav link, not the artifact — matching it opens a nav item mid-build."""
    sel = ART_SEL
    stable = 0
    for i in range(timeout_s // 2):
        time.sleep(2)
        try:
            n = pg.locator(sel).count()
        except Exception:
            n = 0
        if n:
            try:
                busy = pg.locator("button[aria-label*='Stop'], button[aria-label*='stop']").count()
            except Exception:
                busy = 0
            stable = stable + 2 if not busy else 0
            if stable >= 10:
                try:
                    label = pg.locator(sel).first.get_attribute("aria-label") or ""
                except Exception:
                    label = ""
                print(f"artifact settled ({label!r})")
                return True
        else:
            stable = 0
    print("artifact never settled (proceeding)")
    return False


def _artifact_frame(pg):
    """The artifact renders in a child frame. Grab it by elimination (the main
    frame plus claude's analytics frames are not it)."""
    best = None
    for f in pg.frames:
        if f == pg.main_frame:
            continue
        u = (f.url or "").lower()
        if any(k in u for k in ("googletagmanager", "segment", "doubleclick", "analytics")):
            continue
        best = f
    return best


# Read the live state straight out of the artifact frame. Screenshot polling was
# too slow and silently returned nothing on take 1 — the loop never saw green,
# tapped on the fallback, and the game recorded 12186 ms. Reading computed style
# costs ~5ms, so the tap lands at a believable human latency instead.
_PROBE_JS = r"""() => {
    const vw = innerWidth * innerHeight;
    let green = null, big = null;
    for (const el of document.querySelectorAll('*')) {
      const r = el.getBoundingClientRect();
      if (r.width * r.height < vw * 0.25) continue;      // full-bleed surfaces only
      const c = getComputedStyle(el).backgroundColor || '';
      const m = c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?/);
      if (!m) continue;
      const [r_, g_, b_] = [+m[1], +m[2], +m[3]];
      if (m[4] !== undefined && parseFloat(m[4]) < 0.5) continue;   // transparent
      big = [r_, g_, b_];
      if (g_ > 90 && g_ > r_ + 40 && g_ > b_ + 40) { green = [r_, g_, b_]; break; }
    }
    return { green, big, text: (document.body.innerText || '').slice(0, 60).replace(/\s+/g, ' ') };
}"""


def _probe(fr):
    if fr is None:
        return None
    try:
        return fr.evaluate(_PROBE_JS)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(ASSETS / "raw_capture.mp4"))
    ap.add_argument("--build-timeout", type=int, default=300)
    ap.add_argument("--rounds", type=int, default=2, help="how many times to play on camera")
    # HONESTY + CREDIBILITY. Polling computed style detects green in ~36ms, which
    # is FASTER THAN ANY HUMAN CAN BE (physiological floor ~100ms; the widely
    # known benchmark is ~250ms). A 36ms readout makes a correctly-working app
    # look broken, and reporting it as a personal score would be a false claim.
    # So the tap waits a beat: the number lands in the normal human band, and the
    # VO describes what the app MEASURES rather than bragging a reflex.
    ap.add_argument("--tap-delay", type=float, default=0.2,
                    help="seconds to wait after green before tapping")
    a = ap.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / f".rec_{out.stem}"; tmp.mkdir(exist_ok=True)
    for old in tmp.glob("*.webm"):
        try: old.unlink()
        except Exception: pass

    CX, CY = VIEW["width"] // 2, int(VIEW["height"] * 0.45)

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
            pg.screenshot(path=str(out.parent / "FAIL_no_composer.png"))
            ctx.close(); raise SystemExit("composer never hydrated")

        _send(pg, box, PROMPT)                       # BEAT: type one line
        _wait_settled(pg, a.build_timeout)           # BEAT: it builds
        time.sleep(2.5)

        # BEAT: open the artifact fullscreen (overlay button is the real target)
        for attempt in range(4):
            try:
                b = pg.locator(ART_SEL).locator("visible=true").first
                if b.count():
                    lbl = b.get_attribute("aria-label") or ""
                    b.click(force=True); print(f"open attempt {attempt}: clicked {lbl!r}")
                else:
                    print(f"open attempt {attempt}: no visible artifact button")
            except Exception as e:
                print(f"open attempt {attempt}: {e!r}")
            time.sleep(5.0)
            _dismiss(pg)
            # full-bleed check: the artifact frame must own most of the viewport,
            # otherwise we are still filming the inline card inside chat chrome
            cov = 0.0
            try:
                fr = pg.locator("iframe").locator("visible=true").first
                if fr.count():
                    bb = fr.bounding_box() or {}
                    cov = (bb.get("width", 0) * bb.get("height", 0)) / (VIEW["width"] * VIEW["height"])
            except Exception:
                pass
            print(f"open attempt {attempt}: artifact covers {cov:.0%} of frame")
            if cov >= 0.6:
                break
        pg.screenshot(path=str(out.parent / "still_open.png"))
        time.sleep(1.5)

        # BEAT: PLAY IT. The green cue fires on a random delay, so poll a centre
        # crop and tap the moment it goes green. Poll latency reads as a human
        # reaction time, which is exactly what should appear on screen.
        for rnd in range(a.rounds):
            pg.mouse.click(CX, CY)                   # start / arm the round
            print(f"round {rnd+1}: armed")
            time.sleep(0.6)
            fr = _artifact_frame(pg)
            tapped = False
            seen = set()
            for i in range(400):                     # ~12s at 30ms polling
                st = _probe(fr)
                if st and st.get("green"):
                    time.sleep(a.tap_delay)
                    pg.mouse.click(CX, CY)
                    print(f"round {rnd+1}: GREEN {st['green']} -> tapped")
                    tapped = True
                    break
                if st:                               # log each new state once
                    k = (tuple(st.get("big") or ()), st.get("text", "")[:24])
                    if k not in seen:
                        seen.add(k)
                        print(f"  [{i*0.03:5.1f}s] bg={st.get('big')} {st.get('text','')[:44]!r}")
                elif i == 0:
                    print(f"  probe FAILED (frames: {[f.url[:48] for f in pg.frames]})")
                time.sleep(0.03)
            if not tapped:
                pg.mouse.click(CX, CY)
                print(f"round {rnd+1}: no green detected, tapped anyway")
            time.sleep(3.2)                          # hold on the score
        time.sleep(2.0)

        pg.screenshot(path=str(out.parent / "still_result.png"))
        ctx.close()

    vids = sorted(tmp.glob("*.webm"), key=lambda q: q.stat().st_mtime)
    if not vids:
        print("NO VIDEO CAPTURED"); return
    src = vids[-1]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(out)], check=False)
    print(f"OK {out} ({out.stat().st_size} bytes)" if out.exists() else f"transcode failed; webm at {src}")


if __name__ == "__main__":
    main()
