#!/usr/bin/env python3
"""leo_chrome.py — drive Leonardo AI's WEB UI (app.leonardo.ai) instead of the
blocked REST API (v16, 2026-08-11).

WHY: the Leonardo API generation pool is exhausted (~5 tokens; scripts/leo_*.sh
and leo_ref_gen.py 402 on POST /generations). The WEB subscription pool is
separate and still has ~24k tokens (docs/PRODUCTION-PLAYBOOK.md:38 — "API
credits != web-subscription tokens"). This tool moves *generation* to the
browser (persistent logged-in Chromium profile) while REUSING the free GET
download path (GET calls cost no generation tokens, leo_fetch_recent.py:6-7).

RELIABLE (works today):
  --setup            one-time headed login into a persistent Leonardo profile
  --fetch <dir> [n]  download the account's recent generations (free GET) into
                     <dir> — use this AFTER generating (in the UI or via --generate)
  --recipe <shot>    print the exact web-UI settings + prompt/negative to paste
                     for a shot type (portrait|pip|wide|hero), from the locked
                     Sol recipe. Copy-paste generation is the fallback if the
                     DOM driver drifts.

BEST-EFFORT (needs one live-validation pass once the profile is logged in —
Leonardo is a heavy SPA and Google-SSO inside automation Chromium can trip
"browser may not be secure"; if --setup fails at the Google step, fall back to
the suno_gen.py real-Chrome CDP pattern):
  --generate         drive the UI end-to-end: set Kino XL + Photography +
                     Alchemy + Char-Ref@Mid + seed + dims, paste prompt, click
                     Generate, wait, then --fetch the result.

The locked Sol recipe (channels/claude-tricks/.../OUTFIT.md + host-shoot memory):
  Kino XL · Photography · Alchemy V2 on · Private · Char-Ref @ Mid against
  ref_founder.jpeg · 896x1344 (2:3) · fixed seed 9422710109 · warm-Duchenne
  prompt · anti-plastic/stern/teal negatives · magenta studio.
"""
import argparse
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
PROFILE = os.path.join(REPO, ".browser-profiles", "leonardo")
APP_URL = "https://app.leonardo.ai/image-generation"
REF_FOUNDER = os.path.join(
    REPO, "channels", "claude-tricks", "assets", "character", "ref_founder.jpeg")

# ---- locked recipe constants (from OUTFIT.md + host-shoot-leonardo-recipe) ----
SEED_PRIMARY = "9422710109"
NEG = ("intense stare, furrowed brow, knitted eyebrows, cold eyes, dead eyes, "
       "serious blank stare, stern, airbrushed, plastic skin, waxy skin, doll "
       "skin, glossy, oversaturated, HDR, 3d render, CGI, teal, green, cyan, "
       "earring, extra fingers, cluttered background, text, watermark")
WARM_EYES = ("facing the camera and smiling warmly with a genuine happy Duchenne "
             "smile, bright kind eyes that crinkle at the corners, relaxed raised "
             "brows")
WARDROBE_10 = ("a South Asian man in his early thirties with short dark textured "
               "hair swept up and a neat well-groomed dark beard, wearing a "
               "heather-grey marl crew-neck sweatshirt over a grey tee")
STUDIO = ("dark editorial studio with soft magenta rim light and gentle magenta "
          "bokeh behind him, clean uncluttered background. Photography, natural "
          "realistic skin texture with visible pores, soft flattering key light, "
          "shallow depth of field, sharp eyes, 85mm portrait look")

# shot recipes: (dims, positive-prompt-body, charref?, note)
RECIPES = {
    "portrait": (
        "896 x 1344 (2:3)",
        f"{WARM_EYES}, looking directly into the lens. Chest-up talking-head "
        f"portrait, head in the upper third. {WARDROBE_10}. {STUDIO}.",
        True,
        "Full-frame host talking-head — the standard center.jpg framing.",
    ),
    "pip": (
        "896 x 1344 (2:3)",
        f"{WARM_EYES}, looking directly into the lens. Tight head-and-shoulders "
        f"portrait, close crop, face fills the frame, only a sliver of headroom "
        f"above the hair, shoulders squared to camera, cropped at the upper "
        f"chest. {WARDROBE_10}. {STUDIO}.",
        True,
        "PIP-optimized tight crop. NOTE: the pipCallout PIP is a HeyGen VIDEO "
        "cropped in Remotion (seg.pipZoom) — you usually do NOT need this. Only "
        "generate a pip still if you're building a NEW HeyGen photo-avatar.",
    ),
    "wide": (
        "2376 x 1344 (16:9)",
        f"{WARM_EYES}. Host seated at the left third of a wide editorial frame, "
        f"generous negative space on the right for a monitor/overlay. {WARDROBE_10}. "
        f"{STUDIO}.",
        True,
        "Wide environmental plate (left_corner / right_corner). Mirror with "
        "`sips -f horizontal` for the opposite corner (Kino re-centers faces).",
    ),
    "hero": (
        "832 x 1472 (9:16) or 1024 x 1024",
        "REPLACE THIS with your cinematic-scene prompt. Hero illustrations are "
        "conceptual (e.g. a giant robot hand over a keyboard) — NO Char-Ref, use "
        "a Phoenix/Lucid model for scene fidelity, NOT Kino XL (Char-Ref is for "
        "the host only). Style: cinematic, dramatic lighting, magenta/dark palette "
        "to match the channel; keep it on-brand (no real person's face unless "
        "it's the synthetic Sol).",
        False,
        "Cinematic hero for cover/intro. Char-Ref OFF. Not a portrait recipe.",
    ),
}


def cmd_recipe(shot):
    if shot not in RECIPES:
        sys.exit(f"unknown shot {shot!r}; choose: {', '.join(RECIPES)}")
    dims, body, charref, note = RECIPES[shot]
    print(f"=== Leonardo web-UI recipe: {shot} ===\n")
    print("SETTINGS (left rail, Legacy Mode):")
    print("  Model:        Leonardo Kino XL" if charref else "  Model:        Phoenix / Lucid Origin (scene model)")
    print("  Preset Style: Photography" if charref else "  Preset Style: Cinematic / Dynamic")
    print("  Alchemy:      On (V2)")
    print("  Private:      On (Public Images off)")
    print(f"  Dimensions:   {dims}")
    print("  Num Images:   4")
    print(f"  Fixed Seed:   On -> {SEED_PRIMARY}" if charref else "  Fixed Seed:   Off (let it vary)")
    if charref:
        print(f"  Char-Ref:     Image Guidance -> upload {os.path.relpath(REF_FOUNDER, REPO)} -> type=Character Reference -> Strength=Mid")
    else:
        print("  Char-Ref:     OFF (scene, not host)")
    print(f"\nPOSITIVE PROMPT (paste):\n{body}\n")
    if charref:
        print(f"NEGATIVE PROMPT (paste):\n{NEG}\n")
    print(f"NOTE: {note}")


def cmd_fetch(outdir, limit):
    """Reuse leo_fetch_recent.py verbatim — free GET download of the account's
    recent generations (whether made in the UI or via --generate)."""
    script = os.path.join(HERE, "leo_fetch_recent.py")
    print(f">> downloading recent Leonardo generations into {outdir} (free GET)")
    r = subprocess.run(["python3", script, outdir, str(limit)])
    sys.exit(r.returncode)


def cmd_setup():
    """One-time headed login into the persistent Leonardo profile. Mirrors
    record_demo.py --setup-profile: launch headed, user logs in with Google,
    closes the window to flush the session. If Google blocks the automation
    Chromium ('browser may not be secure'), fall back to the suno_gen.py
    real-Chrome CDP pattern (scripts/suno_gen.py) with a ~/.chrome-leonardo-cdp
    profile on port 9222."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("!! playwright not importable — `python3 -m pip install playwright` "
                 "&& `python3 -m playwright install chromium`")
    os.makedirs(PROFILE, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, channel="chromium",
            viewport={"width": 1200, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://app.leonardo.ai/", wait_until="domcontentloaded")
        print("[leonardo] Log in (Google SSO), reach the app, then CLOSE the "
              "window to save the session.")
        print("[leonardo] If Google shows 'this browser may not be secure', "
              "close and use the CDP fallback (see --help).")
        try:
            pg.wait_for_event("close", timeout=15 * 60 * 1000)
        except Exception:
            pass
        try:
            ctx.close()
        except Exception:
            pass
    print(f">> session saved to {PROFILE}")


def cmd_generate(args):
    """BEST-EFFORT full-auto generation. Leonardo is a heavy SPA whose DOM
    drifts; this encodes the documented click-path but MUST be validated live
    once the profile is logged in. If a selector misses, fall back to
    `--recipe <shot>` + manual generation in the UI, then `--fetch`."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("!! playwright not importable")
    if not os.path.isdir(PROFILE):
        sys.exit(f"!! no Leonardo profile at {PROFILE} — run: python3 scripts/leo_chrome.py --setup")
    shot = args.shot
    dims, body, charref, _ = RECIPES[shot]
    prompt = args.prompt or body

    print(f">> [best-effort] generating shot={shot} in the Leonardo web UI")
    print(">> if any step below stalls, use `--recipe` + manual UI generation, then `--fetch`")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=args.headless, channel="chromium",
            viewport={"width": 1400, "height": 1000},
            args=["--disable-blink-features=AutomationControlled"],
        )
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(6)
        if "login" in pg.url or "auth" in pg.url:
            ctx.close()
            sys.exit("!! not logged in — run --setup first (session may have expired)")

        # The generation-prompt textarea is the most stable anchor across the SPA.
        # We type the prompt + submit; all the knob-setting (model/charref/seed)
        # is intentionally left to a one-time UI pre-config that persists per
        # session, because those controls are modals that drift most. Document
        # this: set Kino XL + Photography + Alchemy + Char-Ref@Mid + seed ONCE
        # in the logged-in window, then this driver reuses them.
        typed = False
        for sel in ('textarea[placeholder*="Type a prompt"]',
                    'textarea[placeholder*="prompt"]',
                    'textarea'):
            try:
                box = pg.wait_for_selector(sel, timeout=8000)
                box.click()
                box.fill(prompt)
                typed = True
                break
            except Exception:
                continue
        if not typed:
            ctx.close()
            sys.exit("!! could not find the prompt box — DOM drifted; use --recipe + manual UI")

        # click Generate
        clicked = False
        for sel in ('button:has-text("Generate")', 'button:has-text("Create")',
                    '[data-testid*="generate"]'):
            try:
                pg.click(sel, timeout=6000)
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            ctx.close()
            sys.exit("!! could not find the Generate button — use --recipe + manual UI")

        print(">> Generate clicked; waiting ~40s for the batch to render")
        time.sleep(args.wait)
        try:
            ctx.close()
        except Exception:
            pass

    # download via the free GET path
    print(">> generation submitted — pulling results via free GET")
    cmd_fetch(args.out, args.limit)


def main():
    ap = argparse.ArgumentParser(
        description="Drive Leonardo's web UI (blocked-API workaround). See module docstring.")
    ap.add_argument("--setup", action="store_true",
                    help="one-time headed login into the persistent Leonardo profile")
    ap.add_argument("--fetch", metavar="OUTDIR",
                    help="download the account's recent generations into OUTDIR (free GET)")
    ap.add_argument("--limit", type=int, default=8, help="how many recent generations to fetch")
    ap.add_argument("--recipe", metavar="SHOT",
                    help="print the web-UI settings + prompt for a shot: " + ", ".join(RECIPES))
    ap.add_argument("--generate", action="store_true",
                    help="[best-effort] drive the UI to generate (needs a logged-in profile)")
    ap.add_argument("--shot", default="portrait", choices=list(RECIPES),
                    help="shot recipe for --generate (default portrait)")
    ap.add_argument("--prompt", help="override the recipe's positive prompt for --generate")
    ap.add_argument("--out", default=os.path.join(REPO, "renders_out", "leo"),
                    help="output dir for --generate's download step")
    ap.add_argument("--wait", type=int, default=40, help="seconds to wait for the batch")
    ap.add_argument("--headless", action="store_true", help="run --generate headless")
    a = ap.parse_args()

    if a.setup:
        cmd_setup()
    elif a.fetch:
        cmd_fetch(a.fetch, a.limit)
    elif a.recipe:
        cmd_recipe(a.recipe)
    elif a.generate:
        cmd_generate(a)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
