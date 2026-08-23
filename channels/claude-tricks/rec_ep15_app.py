#!/usr/bin/env python3
"""EP15 payoff pass — film Claude's REAL sleep-tracker app running.

WHY THIS EXISTS (take 1, 2026-08-20): rec_ep15_sleep.py filmed the honest build
arc (type one line -> Claude writes it -> the 'Sleep tracker · HTML' card) but
the artifact PREVIEW IFRAME never rendered inside the mobile panel — it spun for
the whole 15s window, so the payoff beat had no app in it. Same wall
rec_habit_app.py hit; same documented fix: don't fight the vendor preview, pull
Claude's ACTUAL emitted HTML out of the iframe (srcdoc first, content_frame
fallback) and run it ourselves at a clean 1080x1920.

The difference from the habit episode: we do NOT stop at a still. The extracted
page is loaded in a recording context and the LOG SLEEP button is really
clicked, so the payoff beat is continuous motion of real Claude-written code —
the franchise-#4 (_wheel) standard, which is the lever on Shorts-feed selection.

Nothing here is a mock: the pixels are Claude's own output, just hosted by us
instead of by claude.ai's sandbox.
"""
import argparse, re, subprocess, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / ".browser-profiles" / "claude"
ASSETS = ROOT / "channels/claude-tricks/assets/ep15"
VIEW = {"width": 540, "height": 960}                   # x2 dsf -> 1080x1920
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

_ANALYTICS = ("statsig", "segment", "sentry", "doubleclick", "google", "intercom")
_APP_MARK = re.compile(r"bedtime|wake|sleep|streak", re.I)
OPEN_SEL = 'button[aria-label^="View "]:not([aria-label="View all"])'
ACT_NAMES = ("LOG SLEEP", "Log Sleep", "Log sleep", "LOG", "Log", "Save", "SAVE", "Add")


# localStorage-backed stand-in for claude.ai's artifact host API, pre-seeded with
# six prior nights (yesterday back to day-6). Hours chosen to look like a real
# human week — a couple of short nights, not a flat line — so the strip has shape.
SHIM_JS = """
(() => {
  const KEY = 'sleep:entries';
  window.storage = {
    get: async (k) => ({ value: localStorage.getItem(k) }),
    set: async (k, v) => { localStorage.setItem(k, v); },
  };
  if (!localStorage.getItem(KEY)) {
    const HOURS = [7.5, 6.2, 8.0, 5.5, 7.0, 6.8];   // day-6 .. yesterday
    const out = [];
    for (let i = 6; i >= 1; i--) {
      const d = new Date(); d.setDate(d.getDate() - i);
      out.push({ date: d.toISOString().slice(0, 10), hours: HOURS[6 - i] });
    }
    localStorage.setItem(KEY, JSON.stringify(out));
  }
})();
"""


def _extract_html(pg, out_html):
    """Claude's real artifact HTML out of the preview iframe (habit-episode method)."""
    ifr = pg.locator("iframe")
    n = ifr.count()
    print(f"iframes on page: {n}")
    for i in range(n - 1, -1, -1):
        el = ifr.nth(i)
        src = (el.get_attribute("src") or "") + (el.get_attribute("name") or "")
        if any(a in src.lower() for a in _ANALYTICS):
            print(f"  iframe{i} skip (analytics)"); continue
        for how, getter in (("srcdoc", lambda: el.get_attribute("srcdoc")),
                            ("content_frame", lambda: (el.element_handle().content_frame().content()
                                                       if el.element_handle() else None))):
            try:
                html = getter()
            except Exception as e:
                print(f"  iframe{i} {how}: {e!r}"); continue
            if html and len(html) > 400 and _APP_MARK.search(html):
                Path(out_html).write_text(html, encoding="utf-8")
                print(f"extracted app via {how} ({len(html)} chars) -> {out_html}")
                return True
            elif html:
                print(f"  iframe{i} {how}: {len(html)} chars, no app markers")
    return False


def grab(out_html, chat_hint):
    """Reopen the sleep-tracker conversation and pull the artifact HTML."""
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=True, channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
            viewport=VIEW, user_agent=UA, device_scale_factor=2,
            is_mobile=True, has_touch=True, color_scheme="dark")
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://claude.ai/recents", wait_until="domcontentloaded", timeout=60000)
        time.sleep(7)
        # Each /recents row lays a full-bleed <a> over its own title span, and
        # neighbouring rows' overlays intercept a text click (take 2 spent 15s
        # being stolen by the dinner-wheel row). Navigate by the row anchor's
        # href instead of clicking through the stack.
        try:
            a = pg.locator(f'a[aria-label*="{chat_hint}" i]').first
            href = a.get_attribute("href", timeout=15000)
            pg.goto(f"https://claude.ai{href}", wait_until="domcontentloaded", timeout=60000)
            print(f"opened chat {href} (matched {chat_hint!r})")
        except Exception as e:
            pg.screenshot(path=str(ASSETS / "FAIL_no_chat.png"))
            ctx.close(); raise SystemExit(f"chat not found: {e!r}")
        time.sleep(8)
        for attempt in range(4):
            try:
                b = pg.locator(OPEN_SEL).first
                if b.count():
                    b.click(force=True); print(f"open attempt {attempt}: clicked")
            except Exception as e:
                print(f"open attempt {attempt}: {e!r}")
            # the preview spinner is exactly what beat take 1 — but srcdoc is
            # populated well before the sandbox paints, so just poll for it.
            for _ in range(6):
                time.sleep(4)
                if _extract_html(pg, out_html):
                    ctx.close(); return True
        pg.screenshot(path=str(ASSETS / "FAIL_no_html.png"))
        ctx.close(); return False


def film(html_path, out_mp4, taps):
    """Run Claude's app ourselves and film the LOG interaction for real."""
    out = Path(out_mp4); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / f".rec_{out.stem}"; tmp.mkdir(exist_ok=True)
    for old in tmp.glob("*.webm"):
        try: old.unlink()
        except Exception: pass
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True, channel="chromium")
        ctx = br.new_context(viewport=VIEW, device_scale_factor=2, is_mobile=True,
                             has_touch=True, color_scheme="dark",
                             record_video_dir=str(tmp), record_video_size=VIEW)
        pg = ctx.new_page()
        # Claude's artifact expects claude.ai's HOST API (`window.storage`), not
        # localStorage — hosting the page ourselves means we have to supply it,
        # or loadEntries() throws, returns [] and the 7-day strip renders flat
        # (that is exactly what take 3 filmed). The app's own code is untouched;
        # we only provide the environment it was written against, plus six prior
        # nights of demo data so the strip has a week to show. Today's bar is
        # still logged live, on camera, by the real LOG SLEEP handler.
        pg.add_init_script(SHIM_JS)
        pg.goto(Path(html_path).resolve().as_uri(), wait_until="load", timeout=30000)
        time.sleep(2.5)                                  # hold the app before touching it
        pg.screenshot(path=str(ASSETS / "still_hero.png"))
        btn, how = None, None
        for name in ACT_NAMES:
            c = pg.get_by_role("button", name=name).first
            if c.count(): btn, how = c, f"role:{name}"; break
        if btn is None:
            for name in ACT_NAMES:
                c = pg.get_by_text(name, exact=True).first
                if c.count(): btn, how = c, f"text:{name}"; break
        print(f"action control: {how}")
        for i in range(taps):
            try:
                if btn is not None:
                    btn.scroll_into_view_if_needed(timeout=3000)
                    btn.click(force=True, timeout=4000); print(f"tap {i+1}: {how}")
                else:
                    pg.mouse.click(VIEW["width"] // 2, int(VIEW["height"] * 0.6))
                    print(f"tap {i+1}: centre fallback")
            except Exception as e:
                print(f"tap {i+1} failed: {e!r}")
            time.sleep(4.0)                              # let the strip populate on camera
        time.sleep(3.0)                                  # hold the filled-in week
        pg.screenshot(path=str(ASSETS / "still_result.png"))
        ctx.close(); br.close()
    vids = sorted(tmp.glob("*.webm"), key=lambda q: q.stat().st_mtime)
    if not vids:
        print("NO VIDEO CAPTURED"); return False
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(vids[-1]),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(out)], check=False)
    print(f"OK {out} ({out.stat().st_size} bytes)" if out.exists() else "transcode failed")
    return out.exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ASSETS / "sleep_app.html"))
    ap.add_argument("--out", default=str(ASSETS / "hold_app.mp4"))
    ap.add_argument("--chat", default="Sleep tracker")
    ap.add_argument("--taps", type=int, default=2)
    ap.add_argument("--skip-grab", action="store_true", help="reuse an already-extracted html")
    a = ap.parse_args()
    ASSETS.mkdir(parents=True, exist_ok=True)
    if not a.skip_grab:
        if not grab(a.html, a.chat):
            raise SystemExit("could not extract Claude's artifact HTML — see FAIL_no_html.png")
    film(a.html, a.out, a.taps)


if __name__ == "__main__":
    main()
