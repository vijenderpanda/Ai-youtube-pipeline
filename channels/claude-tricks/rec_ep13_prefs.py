#!/usr/bin/env python3
"""EP13 demo tape: set claude.ai "Instructions for Claude" ONCE, then prove it
fires in a brand-new chat.

One continuous real session (persistent logged-in profile), no cuts:
  1. Settings -> Profile -> "Instructions for Claude" is empty
  2. human-type the style rule, Save
  3. close settings, open a BRAND-NEW chat, ask something unrelated
  4. the answer arrives short + bulleted with no re-prompting

Privacy: the left rail carries real chat titles, so it is CSS-hidden for the
whole take (not blurred - hidden beats blurred on a 1080-wide tape).
The preferences field is restored to its pre-run value on exit.

  python3 channels/claude-tricks/rec_ep13_prefs.py -o assets/ep13/prefs_demo.mp4
"""
import argparse, json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
PROFILE = ROOT / ".browser-profiles" / "claude"

VIEW = {"width": 1080, "height": 1350}

RULE = "Always answer in short bullet points. No preamble, no fluff."
ASK = "What should I look for when buying a used car?"

# the rail leaks real chat titles; kill it + the top-right avatar for the take
HIDE_CSS = """
nav, [data-testid='menu-sidebar'], aside { display:none !important; }
"""


def human_type(el, text, cps=22):
    el.click()
    for ch in text:
        el.type(ch, delay=1000.0 / cps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--wait-answer", type=float, default=16.0)
    a = ap.parse_args()
    out = Path(a.out)
    if not out.is_absolute():
        out = ROOT / "channels" / "claude-tricks" / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    vdir = out.parent / ".rec_tmp"
    vdir.mkdir(exist_ok=True)

    marks = {}
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(PROFILE), headless=False, viewport=VIEW,
            args=["--disable-blink-features=AutomationControlled"],
            record_video_dir=str(vdir), record_video_size=VIEW)
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://claude.ai/settings/profile",
                wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(9000)
        if "login" in pg.url or "Log in" in pg.inner_text("body")[:400]:
            print("!! not logged in", file=sys.stderr); sys.exit(2)
        pg.add_style_tag(content=HIDE_CSS)
        pg.wait_for_timeout(800)

        ta = pg.query_selector("textarea")
        if not ta:
            print("!! no preferences textarea found", file=sys.stderr); sys.exit(3)
        prior = ta.input_value() or ""
        print(f">> prior instructions ({len(prior)} chars): {prior[:80]!r}")
        ta.scroll_into_view_if_needed()
        pg.wait_for_timeout(1500)
        t0 = time.time()

        # --- 1. set it once -------------------------------------------------
        marks["type_start"] = round(time.time() - t0, 2)
        if prior:
            ta.click(); pg.keyboard.press("Meta+A"); pg.keyboard.press("Backspace")
        human_type(ta, RULE)
        marks["type_end"] = round(time.time() - t0, 2)
        pg.wait_for_timeout(900)

        save = None
        for b in pg.query_selector_all("button"):
            t = (b.inner_text() or "").strip().lower()
            if t in ("save", "save changes") and b.is_visible():
                save = b; break
        if save:
            save.click(); print(">> clicked Save")
        else:
            pg.keyboard.press("Tab"); print(">> no Save button — field autosaves on blur")
        marks["saved"] = round(time.time() - t0, 2)
        pg.wait_for_timeout(2200)

        # --- 2. brand-new chat, unrelated question --------------------------
        pg.goto("https://claude.ai/new", wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(5000)
        pg.add_style_tag(content=HIDE_CSS)
        marks["new_chat"] = round(time.time() - t0, 2)
        pg.wait_for_timeout(1200)
        box = pg.wait_for_selector("div[contenteditable=true]", timeout=30000)
        human_type(box, ASK)
        pg.wait_for_timeout(600)
        pg.keyboard.press("Enter")
        marks["asked"] = round(time.time() - t0, 2)

        pg.wait_for_timeout(int(a.wait_answer * 1000))
        marks["answer_settled"] = round(time.time() - t0, 2)
        try:
            ans = pg.query_selector_all(".font-claude-response")[-1].inner_text()
        except Exception:
            ans = ""
        marks["answer_head"] = ans[:400]
        bulleted = sum(1 for ln in ans.splitlines() if ln.strip()[:2] in ("- ", "• ", "* "))
        marks["bullet_lines"] = bulleted
        marks["answer_chars"] = len(ans)
        print(f">> answer {len(ans)} chars, {bulleted} bullet lines")
        pg.wait_for_timeout(2500)

        # --- restore ---------------------------------------------------------
        pg.goto("https://claude.ai/settings/profile",
                wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(6000)
        ta2 = pg.query_selector("textarea")
        if ta2:
            ta2.click(); pg.keyboard.press("Meta+A"); pg.keyboard.press("Backspace")
            if prior:
                ta2.type(prior)
            for b in pg.query_selector_all("button"):
                if (b.inner_text() or "").strip().lower() in ("save", "save changes") and b.is_visible():
                    b.click(); break
            pg.wait_for_timeout(2000)
            print(">> restored prior instructions")

        vid = pg.video.path()
        ctx.close()

    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid,
                    "-vf", f"scale={VIEW['width']}:{VIEW['height']}",
                    "-r", "30", "-c:v", "libx264", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-an", str(out)], check=True)
    side = out.with_suffix(".marks.json")
    side.write_text(json.dumps(marks, indent=1))
    print(f">> wrote {out}\n>> marks {side}\n{json.dumps(marks, indent=1)}")


if __name__ == "__main__":
    main()
