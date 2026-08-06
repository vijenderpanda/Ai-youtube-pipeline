#!/usr/bin/env python3
"""Record the memory / custom-instructions beat for AI Unpacked build #24.

record_demo.py only drives prompt -> answer. This sibling drives the SETTINGS
flow: open the personalization screen, flip the memory switch ON, seed one
"about me" line, save. Same launch/context settings as record_demo.py (mobile
540x960, chromium channel, persistent profile) so demo_cold_ask and this clip
cut together as one continuous session.

  python3 scripts/record_memory_demo.py -o renders_out/.../raw_memory.mp4

Hard rules baked in, all of them fail LOUDLY rather than filming the wrong thing:
  * DOM-presence auth probe, not a page.url probe. Verified 5 Aug 2026: when
    logged out chatgpt.com does NOT redirect to /auth or /login - the settings
    deep link silently no-ops and page.url stays put, so a url check reports a
    false "logged in". See research_freshness_note v1 section 2.
  * The click path is DISCOVERED from on-screen labels, never hardcoded. Two
    ChatGPT layouts are live simultaneously (new "Memory summary" vs legacy
    "Reference saved memories") and mobile web uses different wording again, so
    the script tries the documented label set, records which one it actually hit,
    and aborts with the observed screen text if none match.
  * The switch must actually change state. If memory is already ON the script
    aborts instead of filming a no-op or a fake flip.
  * Account email is blurred before the profile menu is ever opened.
"""
import argparse, io, json, re, subprocess, sys, time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record_demo import VIEW, MOBILE_UA, PROFILES, human_type  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
URL = "https://chatgpt.com"

SEED_LINE = ("I run a daily AI-education YouTube channel for beginners; "
             "I have about 45 minutes a day; keep answers short and concrete.")

# Labels come from research_freshness_note v1 (vendor-owned pages, 5 Aug 2026),
# corrected against a live logged-in DOM dump of the mobile build the same day.
# Ordered most- to least-current; the script reports which one it matched.
SETTINGS_ENTRY = ["Settings", "Settings & Beta"]
PERSONALIZATION_ENTRY = ["Personalization", "Customize ChatGPT"]
MEMORY_ENTRY = ["Memory"]                      # new experience only; optional
# switch rows. Measured 5 Aug 2026 logged in at 540x960: the row is
# "Enable memory" and the switch element itself carries NO accessible name,
# only aria-checked - the text-row fallback in find_switch is what matches.
MEMORY_SWITCH = ["Enable memory", "Memory", "Reference saved memories"]
CUSTOM_SWITCH = ["Enable customization"]
CUSTOM_FIELD_LABELS = ["Custom Instructions", "Custom instructions",
                       "Instructions", "About you"]
# Measured: the custom-instructions box is an unlabelled textarea identified
# only by its placeholder, and the underlying chat composer ("Ask anything")
# is ALSO a visible textarea - a bare `textarea` fallback would type the seed
# into the wrong surface. Placeholders first, always.
CUSTOM_FIELD_PLACEHOLDERS = ["Additional behavior, style, and tone preferences",
                             "Interests, values, or preferences to keep in mind"]
SAVE_LABELS = ["Save", "Done", "Update"]
# Measured: this layout autosaves; there may be no Save control at all. The
# honest end beat is then closing the settings sheet.
SHEET_CLOSE = ["button[aria-label='Close']", "[data-testid='modal-close-button']",
               "[data-testid='close-button']"]

HOLD_ON_TOGGLE = 1.2      # secs held on the switch so the flip reads on camera
# The gap must cover the punch windows the sidecar emits PLUS style_punch's
# ease ramps, or its overlap guard rejects the take:
#   (HOLD_ON_TOGGLE + 0.25 + PUNCH_OUT 0.65) + (0.30 + PUNCH_IN 0.55) = 2.95s.
# 1.5s passed the recorder but failed the style pass - same rule, two numbers.
MIN_BEAT_GAP = 3.0        # secs required between the toggle and typing beats
HOLD_ON_SAVE = 1.0
PRE_WAIT = 4              # page settle, trimmed out of the delivered file


# --------------------------------------------------------------------------
# guards

def assert_authenticated(page, when):
    """DOM-presence auth probe. A page.url check does NOT work here."""
    body = page.inner_text("body")
    if re.search(r"\bLog in\b|\bSign up for free\b", body):
        sys.exit(
            f"ABORT: chatgpt profile is LOGGED OUT ({when}). The memory UI does "
            f"not exist logged out - there is nothing real to film.\n"
            f"Fix: a human must run `python3 scripts/record_demo.py "
            f"--site chatgpt --setup-profile` and log in, then re-run this.\n"
            f"url was {page.url!r} (no auth redirect - this is expected)")


def redact_account_email(page):
    """Blur any on-screen email before the profile menu is opened.

    Compliance: the account email is visible in the profile menu and at the top
    of the settings sheet, and the click path documented by the vendor goes
    straight through it. This blurs the PII in place; it does not alter, relabel
    or invent any part of the vendor UI.
    """
    return page.evaluate("""() => {
      const rx = /[\\w.+-]+@[\\w-]+\\.[\\w.]+/;
      let n = 0;
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const hits = [];
      while (walk.nextNode()) if (rx.test(walk.currentNode.nodeValue)) hits.push(walk.currentNode);
      for (const t of hits) {
        const el = t.parentElement;
        if (el && !el.dataset.redacted) {
          el.dataset.redacted = '1';
          el.style.filter = 'blur(7px)';
          n++;
        }
      }
      return n;
    }""")


def redact_sidebar_pii(page):
    """Blur the operator's chat history titles and account name.

    Compliance: the mobile path to Settings goes THROUGH the sidebar, which
    renders the account's real conversation titles and the owner's name. Same
    policy as redact_account_email: hide the PII in place, never relabel or
    invent vendor UI. Injected as CSS so it also covers rows that mount later
    (the sidebar virtualizes its list), plus a text-walker pass for the name
    where it appears outside the profile button (the profile menu header).
    """
    page.add_style_tag(content="""
      a[href^='/c/'] { filter: blur(7px) !important; }
      [data-testid='accounts-profile-button'] { filter: blur(7px) !important; }
    """)
    return 0


def install_name_guard(page, name):
    """Blur the account holder's name the moment it MOUNTS, not after.

    Two takes proved a post-hoc sweep cannot win this race: the profile-menu
    header paints the name ~1s before any sweep that runs after the click
    (measured 5 Aug 2026, twice). A MutationObserver installed BEFORE the
    click runs as a microtask - before the next paint - so the name is
    blurred in the same frame it appears. The name must be captured from the
    sidebar profile row while it is still visible; once the menu covers it,
    its innerText reads empty.
    """
    if not name or len(name) < 3:
        return
    page.evaluate("""(name) => {
      const blurEl = (el) => {
        if (el && !el.dataset.redacted) {
          el.dataset.redacted = '1';
          el.style.filter = 'blur(7px)';
          window.__nameBlurCount = (window.__nameBlurCount || 0) + 1;
        }
      };
      const sweep = (root) => {
        if (root.nodeType === 3) {
          if (root.nodeValue.includes(name)) blurEl(root.parentElement);
          return;
        }
        if (!root.querySelectorAll) return;
        const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        while (walk.nextNode())
          if (walk.currentNode.nodeValue.includes(name))
            blurEl(walk.currentNode.parentElement);
      };
      sweep(document.body);
      const obs = new MutationObserver((muts) => {
        for (const m of muts) {
          if (m.type === 'characterData') { sweep(m.target); continue; }
          for (const node of m.addedNodes) sweep(node);
        }
      });
      obs.observe(document.body,
                  {childList: true, subtree: true, characterData: true});
      window.__nameGuard = obs;
    }""", name)


def assert_name_hidden(page, name):
    """Verify no visible text node still exposes the name; returns blur count."""
    if not name or len(name) < 3:
        return 0
    res = page.evaluate("""(name) => {
      let exposed = 0;
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walk.nextNode()) {
        if (!walk.currentNode.nodeValue.includes(name)) continue;
        let el = walk.currentNode.parentElement, blurred = false;
        while (el) {
          if (el.dataset && el.dataset.redacted) { blurred = true; break; }
          el = el.parentElement;
        }
        if (!blurred) exposed++;
      }
      return {exposed, blurred: window.__nameBlurCount || 0};
    }""", name)
    if res["exposed"]:
        sys.exit(f"ABORT: {res['exposed']} text node(s) still expose the "
                 f"account name unblurred - refusing to film PII.")
    return res["blurred"]


def visible_labels(page, limit=40):
    """What is actually on screen — used in abort messages, never guessed."""
    try:
        txt = page.inner_text("body")
    except Exception:
        return "<unreadable>"
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    return " · ".join(lines[:limit])


def click_first_label(page, labels, what, timeout=4000):
    """Click the first label that is actually present. Returns the label used.

    Measured 5 Aug 2026: chatgpt.com keeps hidden duplicates of sidebar
    controls in the DOM, so every locator is filtered to visible elements -
    a bare .first can resolve to the invisible copy and time out.
    """
    for lab in labels:
        for loc in (page.get_by_role("button", name=lab, exact=True),
                    page.get_by_role("menuitem", name=lab, exact=True),
                    page.get_by_role("tab", name=lab, exact=True),
                    page.get_by_text(lab, exact=True)):
            try:
                el = loc.locator("visible=true").first
                if el.is_visible(timeout=timeout // len(labels) or 500):
                    el.click()
                    return lab
            except Exception:
                continue
    sys.exit(f"ABORT: none of {labels} found for step '{what}'. The UI moved, or "
             f"this account renders the other live layout.\nOn screen: "
             f"{visible_labels(page)}")


def find_switch(page, labels):
    """Locate a real switch control next to one of the given row labels.

    Returns (locator, label, is_on). Reads aria-checked / data-state so the
    pre-flip state is measured, never assumed.
    """
    for lab in labels:
        for loc in (page.get_by_role("switch", name=re.compile(lab, re.I)),
                    page.get_by_role("checkbox", name=re.compile(lab, re.I))):
            try:
                el = loc.first
                if el.is_visible(timeout=1200):
                    return el, lab, _switch_on(el)
            except Exception:
                continue
        # fallback: the row is a text node with the switch as a sibling
        # control, possibly several container levels up (measured: the
        # "Enable memory" switch carries no accessible name at all, so THIS
        # path is the one that matches on the live mobile build)
        for depth in (1, 2, 3, 4):
            try:
                row = page.locator(
                    f"xpath=//*[normalize-space(text())={lab!r}]"
                    f"/ancestor::*[self::div or self::li][{depth}]").first
                if not row.count():
                    break
                el = row.locator(
                    "[role=switch], input[type=checkbox], button[aria-checked]"
                ).locator("visible=true").first
                if el.is_visible(timeout=600):
                    return el, lab, _switch_on(el)
            except Exception:
                continue
    return None, None, None


def _switch_on(el):
    for attr in ("aria-checked", "data-state", "checked"):
        v = el.get_attribute(attr)
        if v is not None:
            return v in ("true", "checked", "on")
    try:
        return bool(el.is_checked())
    except Exception:
        return None


def dismiss_popups(page):
    for label in ("Got It!", "Got it", "Accept", "Dismiss", "No thanks", "Maybe later"):
        try:
            b = page.get_by_role("button", name=label).first
            if b.is_visible(timeout=300):
                b.click(); time.sleep(0.4)
        except Exception:
            pass


# --------------------------------------------------------------------------
# the flow

def record(out, headed=False, seed=SEED_LINE):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmpdir = out.parent / f".rec_{out.stem}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    profile = PROFILES / "chatgpt"          # SAME session as demo_cold_ask

    notes = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(profile),
            headless=not headed,
            channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
            viewport=VIEW, user_agent=MOBILE_UA, device_scale_factor=2,
            is_mobile=True, has_touch=True,
            color_scheme="dark",   # episode look; account Appearance stays "System"
            record_video_dir=str(tmpdir), record_video_size=VIEW,
        )
        t0 = time.monotonic()               # context creation = video start
        mark = lambda: time.monotonic() - t0
        tl = {}

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(PRE_WAIT)
        dismiss_popups(page)
        assert_authenticated(page, "after goto")
        notes["emails_blurred"] = redact_account_email(page)

        # --- step 3: discover the path to the personalization screen ---------
        # Measured 5 Aug 2026 logged in at 540x960: the mobile header has NO
        # profile control; the path is sidebar button -> account row at the
        # sidebar's bottom -> profile menu, which carries a DIRECT
        # "Personalization" item (no Settings hop needed). The sidebar button
        # has no aria-label, only data-testid='open-sidebar-button'.
        notes["pii_rows_blurred"] = redact_sidebar_pii(page)
        opened = False
        for sel in ("[data-testid='open-sidebar-button']",
                    "[data-testid='profile-button']", "button[aria-label*='Profile']",
                    "button[aria-label*='Open sidebar']"):
            try:
                b = page.locator(sel).locator("visible=true").first
                if b.is_visible(timeout=1500):
                    b.click(); opened = True; break
            except Exception:
                continue
        if not opened:
            sys.exit(f"ABORT: no sidebar/profile entry control found at 540x960. "
                     f"On screen: {visible_labels(page)}")
        try:
            page.locator("[data-testid='close-sidebar-button']").first.wait_for(
                state="visible", timeout=8000)
        except Exception:
            pass
        time.sleep(0.8)
        notes["emails_blurred"] += redact_account_email(page)
        notes["pii_rows_blurred"] += redact_sidebar_pii(page)

        prof = page.locator("[data-testid='accounts-profile-button']").locator(
            "visible=true").first
        if not prof.is_visible(timeout=4000):
            sys.exit(f"ABORT: sidebar opened but no account/profile row found. "
                     f"On screen: {visible_labels(page)}")
        # capture the name NOW - once the menu covers this row it reads empty -
        # and arm the mount-time blur BEFORE the click that opens the menu
        acct_name = (prof.inner_text() or "").strip().split("\n")[0]
        install_name_guard(page, acct_name)
        prof.click()
        time.sleep(1.0)
        notes["emails_blurred"] += redact_account_email(page)
        notes["name_blurred"] = assert_name_hidden(page, acct_name)

        # the profile menu has a direct Personalization item; fall back to the
        # Settings sheet + Personalization tab if this account lacks it
        try:
            notes["personalization_label"] = click_first_label(
                page, PERSONALIZATION_ENTRY, "personalization (profile menu)",
                timeout=3000)
            notes["personalization_via"] = "profile-menu"
        except SystemExit:
            notes["settings_label"] = click_first_label(page, SETTINGS_ENTRY,
                                                        "settings entry")
            time.sleep(1.0)
            notes["emails_blurred"] += redact_account_email(page)
            notes["personalization_label"] = click_first_label(
                page, PERSONALIZATION_ENTRY, "personalization tab")
            notes["personalization_via"] = "settings-sheet"
        time.sleep(1.5)
        assert_authenticated(page, "on personalization screen")
        notes["emails_blurred"] += redact_account_email(page)

        # the new experience nests one level deeper; the legacy one does not
        sw, sw_label, is_on = find_switch(page, MEMORY_SWITCH + CUSTOM_SWITCH)
        if sw is None:
            try:
                click_first_label(page, MEMORY_ENTRY, "memory sub-screen", timeout=2500)
                time.sleep(1.0)
                notes["memory_subscreen"] = True
            except SystemExit:
                pass
            sw, sw_label, is_on = find_switch(page, MEMORY_SWITCH + CUSTOM_SWITCH)
        if sw is None:
            sys.exit(f"ABORT: no memory/customization switch on the personalization "
                     f"screen. On screen: {visible_labels(page)}")
        notes["switch_label"] = sw_label
        notes["switch_was_on"] = is_on
        if is_on:
            sys.exit(
                f"ABORT: '{sw_label}' is ALREADY ON. Filming this would be a no-op "
                f"click, and the episode's central proof beat is the state CHANGE. "
                f"Turn it off by hand in a headed session first "
                f"(`--headed` here, or record_demo.py --setup-profile), then re-run.\n"
                f"Do not film a switch that does not move.")

        # --- step 4: flip it ON and hold ------------------------------------
        sw.scroll_into_view_if_needed()
        time.sleep(0.5)
        box = sw.bounding_box() or {}
        tl["toggle_click"] = mark()
        sw.click()
        # Measured 5 Aug 2026 (takes 3+4): the click replaces the switch with
        # a SPINNER that does NOT resolve on this screen in filmable time -
        # take 4 still showed it 4s after the click, while aria-checked reads
        # true almost immediately and Playwright counts the spinner as a
        # "visible switch". The DOM latch is asserted here (abort logic), the
        # VISIBLE proof shot is a separate step after save - see step 7.
        latched = False
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if _switch_on(sw):
                latched = True
                break
            time.sleep(0.3)
        if not latched:
            sys.exit("ABORT: switch did not latch ON after the click - the UI "
                     "rejected it. Not shipping footage of a failed flip.")
        notes["switch_now_on"] = True
        time.sleep(HOLD_ON_TOGGLE)          # hold: the spinner IS the real
        # "processing" state; the settled ON pill is filmed in step 7
        if box:
            tl["toggle_center"] = [round((box["x"] + box["width"] / 2) / VIEW["width"], 3),
                                   round((box["y"] + box["height"] / 2) / VIEW["height"], 3)]

        # --- step 5: seed one "about me" line -------------------------------
        # Placeholders first: measured 5 Aug 2026, the custom-instructions box
        # has no label/name, only a placeholder, and the chat composer ("Ask
        # anything") is also a visible textarea underneath the sheet - a bare
        # `textarea` fallback types the seed into the WRONG surface.
        el = None
        for ph in CUSTOM_FIELD_PLACEHOLDERS:
            try:
                c = page.get_by_placeholder(ph).locator("visible=true").first
                if c.is_visible(timeout=1200):
                    el = c; notes["field_label"] = ph; break
            except Exception:
                continue
        if el is None:
            for lab in CUSTOM_FIELD_LABELS:
                for loc in (page.get_by_role("textbox", name=re.compile(lab, re.I)),
                            page.get_by_label(re.compile(lab, re.I))):
                    try:
                        c = loc.locator("visible=true").first
                        if c.is_visible(timeout=1200):
                            el = c; notes["field_label"] = lab; break
                    except Exception:
                        continue
                if el:
                    break
        if el is None:
            sys.exit(f"ABORT: no custom-instructions field found (and refusing "
                     f"to fall back to an arbitrary textarea - the composer is "
                     f"one). On screen: {visible_labels(page)}")

        el.scroll_into_view_if_needed()
        el.click()
        # keep the two beats legibly apart for the two in-points this clip
        # feeds. The toggle punch runs to click+1.45 plus a 0.65s out-ramp;
        # typing's punch leads its t0 by 0.1 with a 0.55s in-ramp
        # => 2.8s from the click clears it with margin.
        gap = (tl["toggle_click"] + 2.8) - mark()
        if gap > 0:
            time.sleep(gap)
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.press("Backspace")
        time.sleep(0.3)
        fbox = el.bounding_box() or {}
        tl["seed_typing_start"] = mark()
        human_type(el, seed)
        tl["seed_typing_end"] = mark()
        if fbox:
            tl["field_center"] = [round((fbox["x"] + fbox["width"] / 2) / VIEW["width"], 3),
                                  round((fbox["y"] + fbox["height"] / 2) / VIEW["height"], 3)]
        time.sleep(0.7)

        # --- step 6: save and hold ------------------------------------------
        # Measured 5 Aug 2026: this layout autosaves and may render no Save
        # control at all. Closing the sheet is then the honest end beat; which
        # control actually ended the take is recorded in `observed`.
        tl["save_click"] = mark()
        saved = None
        for lab in SAVE_LABELS:
            try:
                b = page.get_by_role("button", name=lab, exact=True).locator(
                    "visible=true").first
                if b.is_visible(timeout=1200) and b.is_enabled():
                    b.click(); saved = lab; break
            except Exception:
                continue
        if saved is None:
            el.blur()          # commit the autosave before closing
            time.sleep(0.6)
            for sel in SHEET_CLOSE:
                try:
                    b = page.locator(sel).locator("visible=true").first
                    if b.is_visible(timeout=1200):
                        b.click(); saved = f"<autosave; closed via {sel}>"; break
                except Exception:
                    continue
        if saved is None:
            sys.exit(f"ABORT: neither a save control nor a sheet-close control "
                     f"found after typing the seed line. On screen: "
                     f"{visible_labels(page)}")
        notes["save_label"] = saved
        time.sleep(HOLD_ON_SAVE)

        # --- step 7: the proof shot - the switch visibly ON ------------------
        # The spinner never resolves in place (measured, takes 3+4), but a
        # fresh render of the sheet shows the blue ON pill. So return to the
        # Memory row and wait on PIXELS, not DOM state: the ON pill is the
        # only saturated-blue element in the row. Reopen the sheet on camera
        # if the in-place render stays stuck - that is real usage, not a mock.
        def _row():
            r = page.locator("xpath=//*[normalize-space(text())='Enable memory']"
                             "/ancestor::div[2]").locator("visible=true").first
            return r if r.count() else None

        def _blue_frac(png):
            im = Image.open(io.BytesIO(png)).convert("RGB")
            px = list(im.getdata())
            return sum(1 for r, g, b in px
                       if b > 140 and b > r + 40 and b > g + 30) / max(1, len(px))

        def _wait_blue(timeout_s):
            end = time.monotonic() + timeout_s
            while time.monotonic() < end:
                row = _row()
                if row is not None:
                    try:
                        row.scroll_into_view_if_needed()
                        if _blue_frac(row.screenshot()) > 0.006:
                            return True
                    except Exception:
                        pass
                time.sleep(0.5)
            return False

        proof_ok = _wait_blue(6)
        if not proof_ok:
            # reopen the sheet on camera: close, profile menu, Personalization
            for sel in SHEET_CLOSE:
                try:
                    b = page.locator(sel).locator("visible=true").first
                    if b.is_visible(timeout=800):
                        b.click(); break
                except Exception:
                    continue
            time.sleep(0.8)
            page.locator("[data-testid='open-sidebar-button']").locator(
                "visible=true").first.click()
            time.sleep(0.8)
            install_name_guard(page, acct_name)
            page.locator("[data-testid='accounts-profile-button']").locator(
                "visible=true").first.click()
            time.sleep(0.8)
            assert_name_hidden(page, acct_name)
            click_first_label(page, PERSONALIZATION_ENTRY,
                              "personalization (proof reopen)", timeout=3000)
            time.sleep(1.5)
            notes["proof_via"] = "reopened-sheet"
            proof_ok = _wait_blue(10)
        else:
            notes["proof_via"] = "in-place"
        if not proof_ok:
            sys.exit("ABORT: the Enable-memory row never rendered the blue ON "
                     "pill, even after reopening the sheet. The visible state "
                     "IS the proof beat - not shipping footage without it.")
        tl["proof_settled"] = mark()
        row = _row()
        pbox = (row.bounding_box() or {}) if row is not None else {}
        if pbox:
            # centre on the switch at the row's right edge, not the row middle
            tl["proof_center"] = [round((pbox["x"] + pbox["width"] * 0.92) / VIEW["width"], 3),
                                  round((pbox["y"] + pbox["height"] / 2) / VIEW["height"], 3)]
        time.sleep(HOLD_ON_TOGGLE)          # hold on the blue ON pill
        tl["end"] = mark()

        video = page.video
        ctx.close()
        raw = Path(video.path())

    # webm -> 1080x1920 mp4, trim the page-load dead time
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw), "-ss", str(PRE_WAIT - 1),
        "-vf", "scale=1080:1920:flags=lanczos",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30", "-an", str(out),
    ], check=True, capture_output=True)
    for f in tmpdir.iterdir():
        f.unlink()
    tmpdir.rmdir()

    trim = max(PRE_WAIT - 1, 0)
    rel = lambda t: round(max(t - trim, 0.0), 3)
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(out),
    ], capture_output=True, text=True)
    try:
        duration = round(float(probe.stdout.strip()), 3)
    except ValueError:
        duration = rel(tl["end"])

    toggle, ts, te, save = (rel(tl["toggle_click"]), rel(tl["seed_typing_start"]),
                            rel(tl["seed_typing_end"]), rel(tl["save_click"]))
    proof = rel(tl["proof_settled"])
    # assert against the SAME windows the sidecar emits (plus style_punch's
    # 0.65s out / 0.55s in ramps) so the style pass cannot reject the take
    if (ts - 0.1 - 0.55) <= (toggle + HOLD_ON_TOGGLE + 0.25 + 0.65):
        sys.exit(f"ABORT: typing starts {ts - toggle:.2f}s after the toggle "
                 f"click - the two punch windows would overlap. Re-record; "
                 f"do not blend the beats in the edit.")
    if (proof - 0.2 - 0.55) <= (te + 0.40 + 0.65):
        sys.exit(f"ABORT: the proof shot lands {proof - te:.2f}s after typing "
                 f"ends - its punch window would overlap the seed punch. "
                 f"Re-record with a longer settle.")

    tog_c = tl.get("toggle_center", [0.5, 0.5])
    fld_c = tl.get("field_center", [0.5, 0.5])
    prf_c = tl.get("proof_center", tog_c)
    timeline = {
        "toggle_click": toggle,
        "seed_typing_start": ts,
        "seed_typing_end": te,
        "save_click": save,
        "proof_settled": proof,
        "duration": duration,
        "toggle_center": tog_c,
        "field_center": fld_c,
        "proof_center": prf_c,
        # style_punch.py multi-punch sidecar: land on the switch for the
        # click, on the text for the seed, then on the blue ON pill - the
        # visible proof - to close the clip
        "punches": [
            {"t0": max(0.0, toggle - 0.2), "t1": toggle + HOLD_ON_TOGGLE + 0.25,
             "center": tog_c, "zoom": 1.30, "label": "toggle"},
            {"t0": max(0.0, ts - 0.1), "t1": min(duration, te + 0.40),
             "center": fld_c, "zoom": 1.30, "label": "seed"},
            {"t0": max(0.0, proof - 0.2), "t1": min(duration, proof + 1.2),
             "center": prf_c, "zoom": 1.30, "label": "proof"},
        ],
        "observed": notes,
    }
    tl_path = out.with_suffix(".timeline.json")
    tl_path.write_text(json.dumps(timeline, indent=2))
    print(json.dumps(notes, indent=2))
    print(f"Timeline {tl_path}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="raw_memory.mp4")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--seed", default=SEED_LINE)
    args = ap.parse_args()
    print(f"OK {record(args.out, headed=args.headed, seed=args.seed)}")


if __name__ == "__main__":
    main()
