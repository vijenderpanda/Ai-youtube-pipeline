#!/usr/bin/env python3
"""Read / stage the ChatGPT personalization state used by the memory episode.

A before/after memory demo needs the SAME logged-in account in two different
states: personalization OFF for the "cold" ask, ON for the payoff. Recording
the "before" logged out (what demo_cold_ask v1 did) is not the same claim -
the viewer sees a login wall and rightly asks why an account-less session is
being used to prove something about that account's memory.

This is the state-staging half of that, deliberately kept OUT of the
recorders: it never films anything, so it can drive the settings sheet without
any of the PII / beat-timing constraints a take has to satisfy.

  python3 scripts/set_personalization_state.py --show
  python3 scripts/set_personalization_state.py --memory off --customization off
  python3 scripts/set_personalization_state.py --memory on  --customization on

Rules (same family as record_memory_demo.py, and for the same measured reasons):
  * DOM-presence auth probe - chatgpt.com does NOT redirect when logged out.
  * Click paths are DISCOVERED from on-screen labels, never hardcoded.
  * Every switch write is verified by re-reading aria-checked, and a switch
    already in the wanted state is left alone (no pointless writes).
  * Prefer flipping "Enable customization" over deleting the instruction text:
    the text is the account owner's data and survives the round trip.
"""
import argparse, json, re, sys, time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record_demo import VIEW, MOBILE_UA, PROFILES  # noqa: E402
from record_memory_demo import (  # noqa: E402
    CUSTOM_FIELD_PLACEHOLDERS, CUSTOM_SWITCH, MEMORY_ENTRY, MEMORY_SWITCH,
    PERSONALIZATION_ENTRY, SETTINGS_ENTRY, SHEET_CLOSE, _switch_on,
    assert_authenticated, click_first_label, dismiss_popups, find_switch,
    visible_labels,
)

URL = "https://chatgpt.com"
# Turning memory OFF can raise a confirmation step; ON never has.
CONFIRM_OFF = ["Turn off", "Disable", "Confirm", "Yes", "Turn off memory"]


def open_personalization(page):
    """Sidebar -> account row -> Personalization. Returns how it got there."""
    opened = False
    for sel in ("[data-testid='open-sidebar-button']",
                "[data-testid='profile-button']", "button[aria-label*='Profile']"):
        try:
            b = page.locator(sel).locator("visible=true").first
            if b.is_visible(timeout=1500):
                b.click(); opened = True; break
        except Exception:
            continue
    if not opened:
        sys.exit(f"ABORT: no sidebar entry control. On screen: {visible_labels(page)}")
    time.sleep(1.0)
    prof = page.locator("[data-testid='accounts-profile-button']").locator(
        "visible=true").first
    if not prof.is_visible(timeout=4000):
        sys.exit(f"ABORT: no account row in the sidebar. On screen: {visible_labels(page)}")
    prof.click()
    time.sleep(1.0)
    try:
        click_first_label(page, PERSONALIZATION_ENTRY, "personalization (profile menu)",
                          timeout=3000)
        via = "profile-menu"
    except SystemExit:
        click_first_label(page, SETTINGS_ENTRY, "settings entry")
        time.sleep(1.0)
        click_first_label(page, PERSONALIZATION_ENTRY, "personalization tab")
        via = "settings-sheet"
    time.sleep(1.8)
    return via


def instruction_fields(page):
    """[(placeholder, locator, current_value)] for the custom-instruction boxes.

    Placeholder-keyed, never a bare `textarea`: the chat composer is also a
    visible textarea underneath the sheet (measured 5 Aug 2026).
    """
    out = []
    for ph in CUSTOM_FIELD_PLACEHOLDERS:
        try:
            el = page.get_by_placeholder(ph).locator("visible=true").first
            if el.is_visible(timeout=900):
                out.append((ph, el, (el.input_value() or "").strip()))
        except Exception:
            continue
    return out


def probe_switches(page):
    """EVERY switch on the screen with its row text and state.

    Named-label lookup is not enough to certify a "cold" account: measured
    5 Aug 2026, "Enable memory" reading false while custom instructions were
    empty STILL produced a personalized answer, because a second control
    (chat-history reference) is a separate row this script had never looked
    at. Enumerate the screen instead of asking it about labels you already
    know; emails are stripped from the row text before printing.
    """
    return page.evaluate("""() => {
      const rx = /[\\w.+-]+@[\\w-]+\\.[\\w.]+/g;
      const els = [...document.querySelectorAll(
        "[role=switch], input[type=checkbox], button[aria-checked]")];
      return els.map(el => {
        const cs = getComputedStyle(el);
        let row = el, txt = "";
        for (let i = 0; i < 5 && row; i++) {
          row = row.parentElement;
          if (row && row.innerText && row.innerText.trim().length > 2) {
            txt = row.innerText.trim(); break;
          }
        }
        return {
          text: txt.replace(rx, "<email>").split("\\n").slice(0, 3).join(" | "),
          checked: el.getAttribute("aria-checked") || el.getAttribute("data-state"),
          name: el.getAttribute("aria-label") || "",
          visible: cs.visibility !== "hidden" && cs.display !== "none",
        };
      });
    }""")


def probe_fields(page):
    """EVERY editable field on the screen: placeholder, length, emptiness.

    CUSTOM_FIELD_PLACEHOLDERS only knows the two boxes record_memory_demo.py
    types into. The personalization sheet also carries Nickname / Occupation /
    More-about-you, and ANY of them personalizes the answer - clearing two of
    four and calling the account cold is how a 'cold' take came back talking
    about the operator's job (measured 5 Aug 2026). Values are never printed,
    only their length.
    """
    return page.evaluate("""() => {
      const els = [...document.querySelectorAll(
        "input[type=text], input:not([type]), textarea, [contenteditable=true]")];
      return els.map(el => {
        const cs = getComputedStyle(el);
        const v = el.value !== undefined ? el.value : el.innerText;
        return {
          placeholder: el.getAttribute("placeholder") || el.getAttribute("aria-label") || "",
          len: (v || "").trim().length,
          tag: el.tagName.toLowerCase(),
          visible: cs.visibility !== "hidden" && cs.display !== "none",
        };
      }).filter(f => f.visible);
    }""")


def screen_text(page, limit=60):
    """Visible lines on the current screen, emails stripped."""
    txt = page.inner_text("body")
    lines = [re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", l.strip())
             for l in txt.splitlines() if l.strip()]
    return lines[:limit]


def read_state(page):
    st = {"switches": {}, "instructions": {}}
    for label_set in (MEMORY_SWITCH, CUSTOM_SWITCH):
        sw, lab, on = find_switch(page, label_set)
        if sw is not None:
            st["switches"][lab] = on
    if not any(l in st["switches"] for l in MEMORY_SWITCH):
        # the new experience nests memory one screen deeper
        try:
            click_first_label(page, MEMORY_ENTRY, "memory sub-screen", timeout=2000)
            time.sleep(1.2)
            sw, lab, on = find_switch(page, MEMORY_SWITCH)
            if sw is not None:
                st["switches"][lab] = on
                st["memory_subscreen"] = True
        except SystemExit:
            pass
    for ph, _el, val in instruction_fields(page):
        st["instructions"][ph] = val
    return st


def set_switch(page, labels, want, what):
    """Drive one switch to `want`. Returns a dict describing what happened."""
    sw, lab, is_on = find_switch(page, labels)
    if sw is None:
        return {"label": None, "found": False, "what": what}
    if is_on == want:
        return {"label": lab, "was": is_on, "now": is_on, "changed": False}
    sw.scroll_into_view_if_needed()
    time.sleep(0.3)
    sw.click()
    if not want:                      # turning OFF can ask for confirmation
        for cl in CONFIRM_OFF:
            try:
                b = page.get_by_role("button", name=cl, exact=True).locator(
                    "visible=true").first
                if b.is_visible(timeout=1200):
                    b.click()
                    break
            except Exception:
                continue
    deadline = time.monotonic() + 8
    now = None
    while time.monotonic() < deadline:
        # re-locate: the click can swap the element for a spinner and back
        sw2, _l, now = find_switch(page, [lab])
        if now == want:
            break
        time.sleep(0.4)
    if now != want:
        sys.exit(f"ABORT: '{lab}' did not reach {'ON' if want else 'OFF'} "
                 f"(reads {now!r}). Refusing to continue with an unknown state.")
    return {"label": lab, "was": is_on, "now": now, "changed": True}


def set_instructions(page, text):
    """Overwrite the custom-instruction boxes.

    `text` is either a string (same value into every box, '' clears) or a
    {placeholder: value} map, which is what --instructions-from replays so a
    staged state restores byte-for-byte instead of approximately.

    Do NOT press Escape to blur: measured 5 Aug 2026, Escape DISCARDS the edit
    and closes the sheet, so a clear that read 0 chars in the live DOM was
    still 121 chars after a reload - and the "cold" take that followed it came
    back personalized. The sheet only autosaves some edits; once a field is
    touched a real Save button appears and clicking it is what persists. The
    write is not believed until --verify re-reads it on a fresh load.
    """
    done = []
    for ph, el, old in instruction_fields(page):
        want = text.get(ph, "") if isinstance(text, dict) else text
        if want == old:
            done.append({"placeholder": ph, "old_len": len(old), "unchanged": True})
            continue
        el.scroll_into_view_if_needed()
        el.click()
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.press("Backspace")
        if want:
            el.fill(want)
        time.sleep(0.3)
        done.append({"placeholder": ph, "old_len": len(old), "new_len": len(want)})
    if done:
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        time.sleep(0.6)
        saved = None
        for lab in ("Save", "Done", "Update", "Save changes"):
            try:
                b = page.get_by_role("button", name=lab, exact=True).locator(
                    "visible=true").first
                if b.is_visible(timeout=1200) and b.is_enabled():
                    b.click(); saved = lab; break
            except Exception:
                continue
        done.append({"saved_via": saved or "<autosave; no Save control appeared>"})
        time.sleep(1.5)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="print state, change nothing")
    ap.add_argument("--probe", action="store_true",
                    help="also dump EVERY switch + the visible screen lines "
                         "(emails stripped) - use when a state reads clean but "
                         "the answer is still personalized")
    ap.add_argument("--memory", choices=["on", "off"])
    ap.add_argument("--customization", choices=["on", "off"])
    ap.add_argument("--instructions", help="overwrite the instruction boxes ('' clears)")
    ap.add_argument("--dump", help="write the FULL state (instruction text included) "
                                   "to this file so it can be restored exactly")
    ap.add_argument("--instructions-from", help="restore the instruction boxes from a --dump file")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    restore = None
    if args.instructions_from:
        restore = json.loads(Path(args.instructions_from).read_text())["before"]["instructions"]

    result = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILES / "chatgpt"), headless=not args.headed, channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
            viewport=VIEW, user_agent=MOBILE_UA, device_scale_factor=2,
            is_mobile=True, has_touch=True, color_scheme="dark",
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(4)
        dismiss_popups(page)
        assert_authenticated(page, "after goto")
        result["via"] = open_personalization(page)
        assert_authenticated(page, "on personalization screen")
        result["before"] = read_state(page)
        if args.probe:
            result["screen"] = screen_text(page)
            result["all_switches"] = probe_switches(page)
            result["all_fields"] = probe_fields(page)
        if args.dump:
            # the only place the instruction text is written out: a local file
            # the operator asked for, never stdout/logs
            Path(args.dump).write_text(json.dumps(result, indent=2))

        if not args.show:
            if args.memory:
                result["memory"] = set_switch(page, MEMORY_SWITCH,
                                              args.memory == "on", "memory")
            if args.customization:
                result["customization"] = set_switch(page, CUSTOM_SWITCH,
                                                     args.customization == "on",
                                                     "customization")
            if restore is not None:
                result["instructions"] = set_instructions(page, restore)
            elif args.instructions is not None:
                result["instructions"] = set_instructions(page, args.instructions)
            time.sleep(1.0)
            result["after"] = read_state(page)

            # RELOAD and re-read. The live DOM lies: a discarded edit still
            # reads as applied until the page is rebuilt from the server.
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)
            dismiss_popups(page)
            open_personalization(page)
            result["verified"] = read_state(page)
            want_instr = (restore if restore is not None else
                          ({} if args.instructions is None else args.instructions))
            bad = []
            for ph, got in result["verified"]["instructions"].items():
                if isinstance(want_instr, dict):
                    exp = want_instr.get(ph, None)
                elif want_instr == {}:
                    exp = None
                else:
                    exp = want_instr
                if exp is not None and got != exp:
                    bad.append(f"{ph!r}: wanted {len(exp)} chars, reloaded as {len(got)}")
            if args.memory:
                want_on = args.memory == "on"
                for lab, on in result["verified"]["switches"].items():
                    if lab in MEMORY_SWITCH and on != want_on:
                        bad.append(f"{lab!r}: wanted {want_on}, reloaded as {on}")
            if bad:
                print(json.dumps(result, indent=2, default=str))
                sys.exit("ABORT: the write did NOT persist -> " + "; ".join(bad) +
                         "\nDo not record against this state; the take would be "
                         "personalized while claiming to be cold.")

        for sel in SHEET_CLOSE:
            try:
                b = page.locator(sel).locator("visible=true").first
                if b.is_visible(timeout=800):
                    b.click(); break
            except Exception:
                continue
        time.sleep(1.0)
        ctx.close()

    # never print the instruction text itself - it is account-owner data
    def scrub(st):
        if isinstance(st, dict) and "instructions" in st and isinstance(st["instructions"], dict):
            st = dict(st)
            st["instructions"] = {k: f"<{len(v)} chars>" for k, v in st["instructions"].items()}
        return st
    for k in ("before", "after", "verified"):
        if k in result:
            result[k] = scrub(result[k])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
