#!/usr/bin/env python3
"""Automated authentic screen recordings of AI tools for AI Unpacked shorts.

Records a real browser session (mobile 9:16 viewport) with human-speed typing,
no manual screen control needed. Output: 1080x1920 mp4 ready for assembly.

Usage:
  python3 scripts/record_demo.py --site duckai --prompt "Explain RAG in one line" -o demo.mp4
  python3 scripts/record_demo.py --site perplexity --prompt "..." -o demo.mp4
  python3 scripts/record_demo.py --url https://gemini.google.com --selector "textarea" --prompt "..." -o demo.mp4

Sites needing login (ChatGPT/Claude): run once with --setup-profile to log in
manually in a headed browser; the session persists in .browser-profiles/.

Recordings whose CONTENT depends on the account (memory / personalization /
saved chats) should add --require-login and --seed-terms:

  python3 scripts/record_demo.py --site chatgpt --require-login \
    --prompt "What should I work on first today?" \
    --seed-terms 'channel,beginner,45[- ]?min,short and concrete' \
    -o raw_reask.mp4

The "before" half of a memory demo belongs on the SAME logged-in account with
personalization switched off - not logged out. A login wall on camera reads as
a different account (or none), which is the one thing a before/after memory
proof cannot afford:

  python3 scripts/set_personalization_state.py --memory off --instructions ''
  python3 scripts/record_demo.py --site chatgpt --require-login --redact-pii \
    --prompt "What should I work on first today?" \
    --forbid-terms 'YouTube,channel,beginner,45[- ]?min' -o raw_cold.mp4

--require-login aborts on a dead session (DOM probe; chatgpt.com serves the
normal composer logged out and never redirects, so page.url cannot see it).
--forbid-terms is the cold-take gate (answer must stay generic) and
--redact-pii blurs the account email / saved-chat titles that only exist once
you are logged in.
--seed-terms turns "the answer must visibly use my context" into a measured
gate: the sidecar gains first_token / first_personalized /
personalized_delay_s, and the run exits non-zero if the personalized wording
never appears or trails the first token by more than --personalized-within.

FAIL -> FIX -> PROOF IN ONE SESSION (--followup)
------------------------------------------------
A "painful problem -> one-move fix" short needs the weak result, the one move,
and the fixed result to be the SAME chat - cutting between two sessions is a
claim, one continuous tape is a proof. --followup types a second prompt into
the same conversation after the first answer has settled:

  python3 scripts/record_demo.py --site chatgpt --no-profile --dark \
    --prompt "Write an email to my client..." \
    --followup "Rewrite it like I'd text a friend." \
    --fail-terms 'hope this email finds you well,do not hesitate' \
    --fix-forbid-terms 'hope this email finds you well,do not hesitate' \
    -o demo_human.mp4

Both halves are measured on the filmed text, same discipline as --seed-terms:
--fail-terms asserts the robotic tell the episode is about IS in the first
answer (>=1 match, all matches recorded), --fix-forbid-terms asserts it is gone
from the rewrite. Neither is eyeballed on a poster frame.

--fix-seed-terms is the positive twin of --fix-forbid-terms, for the class of
short where the fix ADDS something rather than removing it ("you described the
document; give it the document"). The proof there is not an absence in the
second answer, it is wording that could ONLY have come from the material the
viewer just watched land - so it is gated exactly like --seed-terms, and by the
Ep24 rule those regexes must be LEXICAL, never numeric (a generic answer will
happily emit a plausible number and pass a numeric gate).

--followup-paste FILE is how that material lands. Some things a user "gives"
an AI are pasted, not typed: --followup-paste inserts the file's text into the
composer in one motion (a real paste, not a 50-second human_type of a legal
clause) and then human-types --followup after it, so the filmed order is the
honest one - the page arrives, then the question. On a no-login preset this is
not a stylistic choice: chatgpt.com's logged-out file inputs are all
image-only (measured 2026-08-06 - a .txt returns "Unable to upload"), so paste
is the ONLY way an anonymous session can hand it a document.

The sidecar switches to style_punch.py's multi-punch form ("punches"): compose
-> robotic answer -> the one added line -> the human rewrite, each with a zoom
capped by the MEASURED ink extent of what it lands on. The recorder sleeps a
settle gap before the follow-up so those windows cannot overlap once
style_punch's ease ramps are included, and asserts it against the exact windows
it emits.
"""
import argparse, json, re, subprocess, sys, time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / ".browser-profiles"

# viewport recorded small (fast), upscaled 2x to 1080x1920 by ffmpeg
VIEW = {"width": 540, "height": 960}

SITES = {
    "duckai":     {"url": "https://duck.ai", "input": "textarea", "submit": "button[type=submit]"},
    "perplexity": {"url": "https://www.perplexity.ai", "input": "textarea, div[contenteditable=true]", "submit": "button[aria-label*='Submit']"},
    "chatgpt":    {"url": "https://chatgpt.com", "input": "#prompt-textarea, textarea", "submit": "[data-testid='send-button'], button[aria-label*='Send']", "profile": True},
    "claude":     {"url": "https://claude.ai/new", "input": "div[contenteditable=true]", "submit": "button[aria-label='Send message'], button[aria-label*='Send']", "profile": True},
    "gemini":     {"url": "https://gemini.google.com/app", "input": "div[contenteditable=true]", "submit": "button[aria-label*='Send']", "profile": True},
}

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

# Assistant-answer containers, most specific first. The FIRST two are the
# chatgpt.com *mobile web* app ("wm-app") markup, measured 5 Aug 2026 at
# 540x960 with MOBILE_UA; the third is the desktop markup. This distinction is
# load-bearing: the widely-quoted desktop selector
# [data-message-author-role="assistant"] matches NOTHING on mobile web, so a
# check written against it alone silently never fires and reports "no answer".
ANSWER_SELECTORS = [
    ".font-claude-response",                             # claude.ai (2026-08)
    'li[data-message-role="assistant"] [data-assistant-markdown]',
    'li[data-message-role="assistant"]',
    '[data-message-author-role="assistant"]',
    "div.markdown",
]

# chatgpt.com does NOT redirect to /auth when the session is dead - it serves
# the normal composer with login chrome, so page.url looks logged in. Presence
# in the DOM is the only reliable signal.
LOGIN_MARKERS = re.compile(r"\bLog in\b|\bSign up for free\b|\bStay logged out\b")

# Google's logged-out chrome says "Sign in" / "Use your Google Account" and DOES
# bounce to accounts.google.com — neither of which LOGIN_MARKERS above matches
# (it was written for chatgpt.com, which says "Log in" and never redirects).
# Measured 2026-08-06: a preflight using only LOGIN_MARKERS reported
# logged_in=true on a page whose entire body was the Google sign-in form. Same
# family as §10b's "a check written against the wrong selector doesn't error, it
# just never fires" — so the auth probe is per-vendor text PLUS the auth host.
GOOGLE_LOGIN_MARKERS = re.compile(
    r"\bSign in\b|\bUse your Google Account\b|\bForgot email\?|\bCreate account\b")
AUTH_HOSTS = ("accounts.google.com", "/auth", "/login", "signin")

# style_punch.py's ease ramps, mirrored here so the recorder can GUARANTEE the
# gaps its own sidecar needs instead of discovering the overlap in the style
# pass (playbook §10c: one number, both ends).
PUNCH_IN, PUNCH_OUT = 0.55, 0.65
MIN_PUNCH_GAP = PUNCH_IN + PUNCH_OUT + 0.20      # 1.40s between punch windows
SETTLE_BEFORE_FOLLOWUP = 3.0                     # secs held on the weak answer
PROOF_HOLD = 3.0                                 # secs held STILL on the scrolled proof


def box_norm(page, selector, last=False):
    """Normalized [x0, y0, x1, y1] of a visible element, or None.

    Punch centers and zoom caps are derived from MEASURED element extents, not
    from guessed constants — a mobile chat answer runs edge to edge and a 1.08
    push clips its outermost characters (playbook §10c).
    """
    try:
        loc = page.locator(selector).locator("visible=true")
        if not loc.count():
            return None
        b = (loc.last if last else loc.first).bounding_box(timeout=1500)
    except Exception:
        return None
    if not b or not b["width"] or not b["height"]:
        return None
    w, h = VIEW["width"], VIEW["height"]
    return [b["x"] / w, b["y"] / h, (b["x"] + b["width"]) / w,
            (b["y"] + b["height"]) / h]


def punch_from_box(box, want, floor=1.02):
    """(center, zoom) for a punch that keeps `box` fully inside the frame.

    A centred crop at zoom z shows 1/z of each axis, so the widest safe zoom is
    1/span — 98% of it, and never past the requested look. style_punch clamps
    the crop window into the frame, so a center near an edge is fine.

    This is the DOM's idea of the element, which is a floor, not the answer: a
    composer element is full-width but its typed ink is not, and app chrome
    that shares the box (a "+" icon, a nav pill) is not content worth
    protecting. Re-probe the shipped clip before the render —
    `probe_frames.py ink CLIP --window T0 T1 --region ...` measures the pixels
    that actually have to survive, and it typically buys back 0.03-0.06 of zoom.
    """
    if not box:
        return [0.5, 0.5], floor
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cap = min(1.0 / max(1e-3, x1 - x0), 1.0 / max(1e-3, y1 - y0)) * 0.98
    return [round(cx, 3), round(cy, 3)], round(max(floor, min(want, cap)), 3)


def human_type(el, text, cps=14):
    """Type like a human: variable per-char delay around given chars/sec."""
    import random
    for ch in text:
        el.type(ch, delay=0)
        time.sleep(random.uniform(0.5, 1.5) / cps)


def assert_not_login_wall(page, when):
    """Abort loudly rather than filming a login/signup wall.

    Profile sessions log out silently and the no-login presets can start
    gating at any time; either way the redirect only shows up in page.url.
    """
    u = page.url or ""
    if "/auth" in u or "/login" in u:
        sys.exit(f"ABORT: login redirect {when} -> {u} "
                 f"(re-run with --setup-profile, or drop --no-profile)")


def assert_logged_in(page, when, site=None):
    """Abort if the page is showing logged-out chrome.

    Only call this for recordings whose CONTENT depends on the account
    (memory, personalization, saved chats). A cold/anonymous ask is a valid
    thing to film logged out, so this is opt-in via --require-login.
    """
    try:
        body = page.inner_text("body", timeout=5000)[:4000]
    except Exception:
        return
    if LOGIN_MARKERS.search(body):
        sys.exit(
            f"ABORT: profile is LOGGED OUT {when} (url was {page.url!r} - note "
            f"there is NO auth redirect, so a page.url probe would have passed "
            f"this).\nPersonalization/memory does not exist logged out, so this "
            f"recording would film a generic answer and call it personalized.\n"
            f"Fix: python3 scripts/record_demo.py --site {site or 'chatgpt'} "
            f"--setup-profile   # headed; log in; CLOSE the window")


def redact_pii(page):
    """Blur account email / saved-chat titles in place. Returns a count.

    A logged-in take (--require-login) films the account's own UI, so the
    PII class that a logged-out recording simply does not have comes back:
    the email, the owner's name on the profile row, and other people's - i.e.
    the operator's own - conversation titles in the sidebar. Blurring hides
    them in place; it never relabels or invents any part of the vendor UI.
    record_memory_demo.py carries the fuller version (mount-time observer)
    because its click path walks THROUGH the profile menu; a prompt->answer
    take never opens it, so a sweep plus standing CSS is enough here.
    """
    # 2026-08-11: claude.ai chat links moved to /chat/ + /code/ (were /c/) and the
    # account row is now [data-testid='user-menu-button'] (was accounts-profile-button)
    # -- the old two selectors matched NOTHING, so the recents sidebar leaked real
    # personal chat titles on camera. Blur every recents surface + the account row;
    # the demo runs in the main column so this never touches the taught content.
    page.add_style_tag(content="""
      a[href^='/c/'], a[href^='/chat/'], a[href^='/code/'] { filter: blur(7px) !important; }
      [data-row-main-button], [aria-label^='More options for'] { filter: blur(7px) !important; }
      .dframe-recents-by-mode, .df-recents-anchor, [class*='recents'] { filter: blur(8px) !important; }
      [data-testid='accounts-profile-button'], [data-testid='user-menu-button'] { filter: blur(7px) !important; }
    """)
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


def assert_no_visible_pii(page, when):
    """Abort if an email is on screen unblurred. Cheap, and it has to hold."""
    exposed = page.evaluate("""() => {
      const rx = /[\\w.+-]+@[\\w-]+\\.[\\w.]+/;
      let n = 0;
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walk.nextNode()) {
        if (!rx.test(walk.currentNode.nodeValue)) continue;
        let el = walk.currentNode.parentElement, ok = false;
        while (el) {
          if (el.dataset && el.dataset.redacted) { ok = true; break; }
          const cs = getComputedStyle(el);
          if (cs.visibility === 'hidden' || cs.display === 'none') { ok = true; break; }
          el = el.parentElement;
        }
        if (!ok) n++;
      }
      return n;
    }""")
    if exposed:
        sys.exit(f"ABORT: {exposed} unblurred email(s) on screen {when} - "
                 f"refusing to film account PII.")


def read_answer(page):
    """(selector, text) of the newest assistant answer, or (None, '')."""
    for sel in ANSWER_SELECTORS:
        try:
            if page.locator(sel).count():
                txt = page.locator(sel).last.inner_text(timeout=700).strip()
                if txt:
                    return sel, txt
        except Exception:
            continue
    return None, ""


def watch_answer(page, seconds, mark, seed_terms=(), forbid_terms=()):
    """Film the streaming answer, measuring when text actually appears.

    record_demo.py used to stamp answer_start immediately after submit and
    sleep, so answer_start == submit and no sidecar carried a real
    first-token time. This polls the answer container instead and returns the
    measured moments, without changing how long the answer is filmed.
    """
    out = {"first_token": None, "first_personalized": None,
           "matched_term": None, "selector": None, "answer_head": "",
           "forbidden_term": None, "answer_chars": 0, "seen_terms": []}
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        sel, txt = read_answer(page)
        if txt:
            if out["first_token"] is None:
                out["first_token"] = mark()
                out["selector"] = sel
            out["answer_head"] = txt[:400]
            out["answer_chars"] = len(txt)
            # every seed/tell term that ever appears is recorded (the tells of a
            # "fail" take arrive throughout a long answer, not just in its head);
            # first_personalized still marks the FIRST one, for the delay gate
            for term in seed_terms:
                if term in out["seen_terms"] or not re.search(term, txt, re.I):
                    continue
                out["seen_terms"].append(term)
                if out["first_personalized"] is None:
                    out["first_personalized"] = mark()
                    out["matched_term"] = term
            # the WHOLE answer is scanned, not just the head: a "cold" take is
            # only cold if personalization is absent everywhere, including the
            # part the viewer reaches on the scroll pass
            if forbid_terms and out["forbidden_term"] is None:
                for term in forbid_terms:
                    if re.search(term, txt, re.I):
                        out["forbidden_term"] = term
                        break
        time.sleep(0.2)
    return out


def build_punches(timeline, tl, duration):
    """style_punch.py multi-punch camera for a fail -> fix -> proof tape.

    Four beats: composing the ask, the robotic answer, the one added line, the
    human rewrite. Composer beats punch hard (the typed words are the content);
    answer beats punch gently and only as far as their MEASURED ink allows —
    a mobile chat answer runs edge to edge, so a fixed 1.08 would slice the
    outermost characters (playbook §10c).
    """
    def win(label, t0, t1, box, want):
        if t0 is None or t1 is None or t1 <= t0:
            print(f"!! punch {label!r} skipped (missing/degenerate window)")
            return None
        center, zoom = punch_from_box(box, want)
        return {"t0": round(max(0.0, t0), 3), "t1": round(min(t1, duration), 3),
                "center": center, "zoom": zoom, "label": label}

    g = timeline.get
    punches = [
        win("compose", g("typing_start", 0) - 0.1, g("typing_end", 0) + 0.3,
            tl.get("composer_box"), 1.20),
        win("robotic", (g("first_token") or 0) - 0.2, g("answer_end", 0) - 0.2,
            tl.get("answer_box"), 1.06),
        win("fixline", g("fix_typing_start", 0) - 0.1, g("fix_typing_end", 0) + 0.3,
            tl.get("fix_composer_box"), 1.20),
        win("human", (g("fix_first_token") or 0) - 0.2, g("fix_answer_end", 0) - 0.1,
            tl.get("fix_answer_box"), 1.06),
    ]
    punches = [p for p in punches if p]
    # assert the SAME windows the sidecar emits, ramps included, so the style
    # pass cannot reject a take the recorder already accepted
    for a, b in zip(punches, punches[1:]):
        if b["t0"] - PUNCH_IN < a["t1"] + PUNCH_OUT:
            sys.exit(
                f"ABORT: punches {a['label']!r} and {b['label']!r} are "
                f"{b['t0'] - a['t1']:.2f}s apart, under the {MIN_PUNCH_GAP:.2f}s "
                f"the ease ramps need. Re-record with a longer settle "
                f"(SETTLE_BEFORE_FOLLOWUP is {SETTLE_BEFORE_FOLLOWUP}s); do not "
                f"blend two beats into one camera move.")
    return punches


def record(url, input_sel, prompt, out, wait_after=14, pre_wait=4, profile=None,
           headed=False, submit_sel=None, require_login=False, seed_terms=(),
           site=None, dark=False, forbid_terms=(), redact=False,
           followup=None, followup_wait=None, fail_terms=(),
           fix_forbid_terms=(), fix_seed_terms=(), followup_paste=None,
           followup_scroll=False):
    out = Path(out)
    tmpdir = out.parent / f".rec_{out.stem}"
    tmpdir.mkdir(parents=True, exist_ok=True)

    launch_args = dict(
        headless=not headed,
        channel="chromium",  # full build in new headless mode, far less bot-detectable than headless shell
        args=["--disable-blink-features=AutomationControlled"],
    )
    with sync_playwright() as p:
        common = dict(
            viewport=VIEW,
            user_agent=MOBILE_UA,
            device_scale_factor=2,
            is_mobile=True, has_touch=True,
            record_video_dir=str(tmpdir),
            record_video_size=VIEW,
        )
        if dark:
            common["color_scheme"] = "dark"  # episode look; account setting untouched
        if profile:
            ctx = p.chromium.launch_persistent_context(str(profile), **launch_args, **common)
        else:
            browser = p.chromium.launch(**launch_args)
            ctx = browser.new_context(**common)
        t0 = time.monotonic()  # context creation = video start
        mark = lambda: time.monotonic() - t0
        tl = {"scrolls": []}

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(pre_wait)  # page settle; this footage is trimmed later
        assert_not_login_wall(page, "after goto")
        if require_login:
            assert_logged_in(page, "after goto", site)

        def dismiss_popups():
            for label in ("Got It!", "Got it", "Accept", "Dismiss", "No thanks", "Maybe later"):
                try:
                    b = page.get_by_role("button", name=label).first
                    if b.is_visible(timeout=300):
                        b.click()
                        time.sleep(0.4)
                except Exception:
                    pass
            for close_sel in ("[aria-label=Close]", "[aria-label='Dismiss']", "button:has-text('×')"):
                try:
                    b = page.locator(close_sel).last
                    if b.is_visible(timeout=300):
                        b.click()
                        time.sleep(0.4)
                except Exception:
                    pass
        dismiss_popups()
        if redact:
            tl["pii_blurred"] = redact_pii(page)
            assert_no_visible_pii(page, "before typing")

        # visible-filtered: the logged-in mobile build keeps a HIDDEN fallback
        # <textarea name="prompt-textarea"> in the DOM while the real composer
        # is a different element - a bare .first resolves to the hidden copy
        # and times out (measured 5 Aug 2026)
        def ask(text, pre, film, seeds=(), forbids=(), paste=None):
            """Type `text` into the composer, send it, film the answer.

            Stamps <pre>typing_start/typing_end/submit/first_token/answer_end
            and the measured composer + answer extents the punch camera needs.

            `paste` lands a block of text in ONE motion before the typing, the
            way a person actually hands an AI a document. It is stamped
            <pre>paste_end so a beat can cut to the moment the material is on
            screen; typing_start deliberately opens BEFORE the paste so the
            punch window covers the whole "give it the page, then ask" move
            rather than only the question typed after it.
            """
            el = page.locator(input_sel).locator("visible=true").first
            el.wait_for(state="visible", timeout=30000)
            el.click()
            time.sleep(0.4)
            page.keyboard.press("ControlOrMeta+A")  # clear any draft persisted in the profile
            page.keyboard.press("Backspace")
            time.sleep(0.4)
            tl[pre + "composer_box"] = box_norm(page, input_sel)
            tl[pre + "typing_start"] = mark()
            if paste:
                page.keyboard.insert_text(paste)
                time.sleep(1.0)          # the composer grows; let it settle on camera
                tl[pre + "paste_end"] = mark()
                # re-measure: a pasted document expands the composer far past
                # the empty-state box, and the punch camera must frame what is
                # actually there (playbook §10c - the DOM box is a floor)
                tl[pre + "composer_box"] = box_norm(page, input_sel)
            human_type(el, text)
            tl[pre + "typing_end"] = mark()
            time.sleep(0.6)
            # Submit: prefer the VISIBLE send button (claude.ai keeps hidden
            # duplicates in the DOM, so a bare .first can resolve to an invisible
            # one and silently fall through to Enter — which does NOT send on the
            # current claude.ai build, leaving the prompt stuck in the composer).
            _sb = page.locator(submit_sel).locator("visible=true").first if submit_sel else None
            _clicked = False
            if _sb is not None:
                try:
                    if _sb.count() and _sb.is_visible():
                        _sb.click()
                        _clicked = True
                except Exception:
                    _clicked = False
            if not _clicked:
                page.keyboard.press("Enter")
            tl[pre + "submit"] = mark()
            # Verify the send actually fired (composer emptied / navigation);
            # if not, fall back to the other method once before giving up.
            time.sleep(0.8)
            try:
                still = (el.inner_text(timeout=500) or "").strip()
            except Exception:
                still = ""
            if still and text[:12] in still:
                if _clicked:
                    page.keyboard.press("Enter")
                elif _sb is not None and _sb.count():
                    try:
                        _sb.click()
                    except Exception:
                        pass
            time.sleep(2)
            assert_not_login_wall(page, "after submit")  # some sites gate on send
            dismiss_popups()
            # response streams in on camera, and we measure it while it does
            w = watch_answer(page, film - 2, mark, seeds, forbids)
            tl[pre + "answer_end"] = mark()
            if w["selector"]:
                tl[pre + "answer_box"] = box_norm(page, w["selector"], last=True)
            return w

        watch = ask(prompt, "", wait_after,
                    seed_terms or fail_terms, forbid_terms)
        tl["answer_start"] = tl["submit"]  # kept for back-compat; == submit by design
        tl.update({k: watch[k] for k in
                   ("first_token", "first_personalized", "matched_term",
                    "selector", "answer_head", "forbidden_term", "answer_chars")})
        if fail_terms:
            # every tell that actually made it on camera, not just the first
            # (measured on the full streamed text, not the 400-char head)
            tl["fail_matched"] = list(watch["seen_terms"])
            if not seed_terms:
                # same measurement, honest name: on a fail take the first match
                # is the moment the robotic tell lands, not a personalization
                tl["first_tell"] = tl.pop("first_personalized", None)
                tl["tell_term"] = tl.pop("matched_term", None)

        dismiss_popups()  # late banners (e.g. duck.ai "Get Browser") appear near answer end
        if redact:
            tl["pii_blurred"] = tl.get("pii_blurred", 0) + redact_pii(page)
            assert_no_visible_pii(page, "after the answer")

        if followup:
            # hold on the weak answer, then ask the one-line fix in the SAME
            # chat. The sleep is the punch-gap guarantee, asserted below against
            # the exact windows this sidecar emits.
            time.sleep(SETTLE_BEFORE_FOLLOWUP)
            fix = ask(followup, "fix_", followup_wait or wait_after,
                      fix_seed_terms, fix_forbid_terms, paste=followup_paste)
            tl.update({"fix_first_token": fix["first_token"],
                       "fix_selector": fix["selector"],
                       "fix_answer_head": fix["answer_head"],
                       "fix_answer_chars": fix["answer_chars"],
                       "fix_forbidden_term": fix["forbidden_term"],
                       "fix_seeded": fix["first_personalized"],
                       "fix_seed_matched": fix["matched_term"],
                       "fix_seen_terms": list(fix["seen_terms"])})
            if followup_scroll:
                # A pasted document is TALL, so the grounded answer renders
                # below the fold and the viewport never moves on its own — the
                # payoff line the episode is measured on streams off camera.
                # §10b's "never scroll to hunt for the sentence" is about a
                # payoff that arrives late in the TEXT; this one arrives at
                # +0.97s and is only off-SCREEN, so the honest fix is the thing
                # a reader does next. Scroll to the bottom of the conversation
                # (deterministic: the end of the answer, not a guessed offset),
                # then hold STILL so the beat has a readable, motionless frame.
                tl["fix_scrolls"] = []
                prev = -1
                for _ in range(8):
                    top = page.evaluate(
                        "() => { const e = document.scrollingElement || "
                        "document.body; return e.scrollTop; }")
                    if top == prev:
                        break            # bottom reached
                    prev = top
                    page.mouse.wheel(0, 220)
                    tl["fix_scrolls"].append(mark())
                    time.sleep(0.7)
                time.sleep(PROOF_HOLD)
                tl["fix_proof_end"] = mark()
            if redact:
                tl["pii_blurred"] = tl.get("pii_blurred", 0) + redact_pii(page)
                assert_no_visible_pii(page, "after the rewrite")
        else:
            # gentle scroll to show the full answer
            for _ in range(3):
                page.mouse.wheel(0, 260)
                tl["scrolls"].append(mark())
                time.sleep(1.2)

        video = page.video
        ctx.close()
        raw = Path(video.path())

    # webm -> 1080x1920 mp4, trim page-load dead time
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw), "-ss", str(pre_wait - 1),
        "-vf", "scale=1080:1920:flags=lanczos",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30", "-an", str(out),
    ], check=True, capture_output=True)
    for f in tmpdir.iterdir():
        f.unlink()
    tmpdir.rmdir()

    # timeline sidecar: event times in secs relative to the FINAL trimmed video
    trim = max(pre_wait - 1, 0)
    rel = lambda t: round(max(t - trim, 0.0), 3)
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(out),
    ], capture_output=True, text=True)
    try:
        duration = round(float(probe.stdout.strip()), 3)
    except ValueError:
        duration = rel(tl["scrolls"][-1]) if tl["scrolls"] else rel(tl["answer_end"])
    timeline = {
        "typing_start": rel(tl["typing_start"]),
        "typing_end": rel(tl["typing_end"]),
        "submit": rel(tl["submit"]),
        "answer_start": rel(tl["answer_start"]),
        "answer_end": rel(tl["answer_end"]),
        "scrolls": [rel(t) for t in tl["scrolls"]],
        "duration": duration,
    }
    # measured moments (None when the answer never rendered / no terms given).
    # first_token is what beat-map in-points want; answer_start is not it.
    if tl.get("first_token") is not None:
        timeline["first_token"] = rel(tl["first_token"])
    if tl.get("first_personalized") is not None:
        timeline["first_personalized"] = rel(tl["first_personalized"])
        timeline["matched_term"] = tl.get("matched_term")
        if tl.get("first_token") is not None:
            timeline["personalized_delay_s"] = round(
                timeline["first_personalized"] - timeline["first_token"], 3)
    timeline["observed"] = {
        "answer_selector": tl.get("selector"),
        "answer_head": tl.get("answer_head", "")[:400],
        "answer_chars": tl.get("answer_chars", 0),
        "logged_in": bool(require_login) or None,
        "pii_blurred": tl.get("pii_blurred"),
        "forbidden_term": tl.get("forbidden_term"),
    }
    if fail_terms:
        timeline["observed"]["fail_matched"] = tl.get("fail_matched") or []
        timeline["observed"]["tell_term"] = tl.get("tell_term")
        if tl.get("first_tell") is not None:
            timeline["first_tell"] = rel(tl["first_tell"])
    if followup:
        for k in ("typing_start", "paste_end", "typing_end", "submit",
                  "answer_end", "first_token"):
            v = tl.get("fix_" + k)
            if v is not None:
                timeline["fix_" + k] = rel(v)
        if tl.get("fix_scrolls"):
            timeline["fix_scrolls"] = [rel(t) for t in tl["fix_scrolls"]]
            timeline["fix_proof_end"] = rel(tl["fix_proof_end"])
            # the still, readable window the payoff beat should cut to
            timeline["fix_proof_start"] = round(
                timeline["fix_proof_end"] - PROOF_HOLD, 3)
        timeline["observed"].update({
            "fix_answer_selector": tl.get("fix_selector"),
            "fix_answer_head": (tl.get("fix_answer_head") or "")[:400],
            "fix_answer_chars": tl.get("fix_answer_chars", 0),
            "fix_forbidden_term": tl.get("fix_forbidden_term"),
        })
        if fix_seed_terms:
            timeline["observed"]["fix_seed_matched"] = tl.get("fix_seen_terms") or []
            timeline["observed"]["fix_seed_first"] = tl.get("fix_seed_matched")
            if tl.get("fix_seeded") is not None:
                timeline["fix_seeded"] = rel(tl["fix_seeded"])
                if tl.get("fix_first_token") is not None:
                    timeline["fix_seeded_delay_s"] = round(
                        timeline["fix_seeded"] - timeline["fix_first_token"], 3)
        timeline["punches"] = build_punches(timeline, tl, duration)
    tl_path = out.with_suffix(".timeline.json")
    tl_path.write_text(json.dumps(timeline, indent=2))
    print(f"Timeline {tl_path}")
    return out, timeline


def check_personalized(timeline, prompt, within):
    """Hard acceptance: the answer must use the seeded context almost at once.

    A personalized sentence that only arrives after a long generic preamble is
    not the beat - the payoff has to play, not be hunted for with a scroll.
    """
    ft, fp = timeline.get("first_token"), timeline.get("first_personalized")
    if ft is None:
        return ("FAIL: no answer text ever rendered - nothing to accept. "
                "Check the answer selector in observed.answer_selector.")
    if fp is None:
        return (f"FAIL: the answer never referenced the seeded context.\n"
                f"  answer opened: {timeline['observed']['answer_head'][:200]!r}\n"
                f"  RE-RECORD (do NOT scroll to find it): reseed, or rephrase "
                f"the prompt slightly, e.g. {prompt!r} -> 'What should I do "
                f"first today?'")
    delay = timeline.get("personalized_delay_s", fp - ft)
    if delay > within:
        return (f"FAIL: personalized wording arrived {delay:.2f}s after the "
                f"answer started streaming (limit {within:.1f}s) - that is a "
                f"generic preamble the viewer has to sit through.\n"
                f"  RE-RECORD with a slightly rephrased prompt, e.g. {prompt!r}"
                f" -> 'What should I do first today?'")
    return None


def check_generic(timeline, forbid_terms):
    """Hard acceptance for a COLD take: the answer must NOT be personalized.

    The mirror image of check_personalized, and needed for the same reason:
    "the answer is visibly generic" is the whole argument of a before/after
    memory demo, so it has to be measured on the text that was filmed rather
    than eyeballed on a poster frame. Recording the cold ask logged IN (which
    is what makes the before/after honest - same account, personalization off)
    is exactly what makes this gate necessary: unlike a logged-out session,
    a stale custom instruction or a memory setting left on WILL personalize
    the answer and quietly destroy the contrast.
    """
    ft = timeline.get("first_token")
    if ft is None:
        return ("FAIL: no answer text ever rendered - nothing to accept. "
                "Check the answer selector in observed.answer_selector.")
    hit = timeline["observed"].get("forbidden_term")
    if hit:
        return (f"FAIL: the 'cold' answer matched {hit!r} - it is personalized, "
                f"so there is no contrast left to film.\n"
                f"  answer opened: {timeline['observed']['answer_head'][:200]!r}\n"
                f"  Personalization is still live on this account. Clear it "
                f"(python3 scripts/set_personalization_state.py --memory off "
                f"--instructions '') and RE-RECORD.")
    return None


def preflight(url, profile, expect_terms, site=None, dark=False,
              shot=None, settle=6.0):
    """Answer 'can this account film this feature?' WITHOUT filming anything.

    Playbook §10b's standing lesson is that a demo chain whose capability is
    tier-gated or behind auth dequeues into a blocker at RECORD time, hours
    after the plan was written and the VO was rendered. The cheap fix is to ask
    the account the day before. This mode loads the real profile, DOM-probes the
    login state the same way `assert_logged_in` does (never `page.url` — §10b),
    then searches the rendered body for the affordance the episode needs.

    Exit codes are the plan-time branch, so a brief can encode PATH A / PATH B:
      0  AVAILABLE   — logged in and every --expect term is on screen
      3  LOGGED_OUT  — needs an interactive `--setup-profile` (a human step)
      4  GATED       — logged in, but the affordance is absent (tier-gated /
                       not rolled out to this account): take the fallback path
    Prints a JSON verdict on stdout so a build script can branch on it.
    """
    verdict = {"url": url, "site": site, "logged_in": None,
               "expect": list(expect_terms), "found": [], "missing": []}
    with sync_playwright() as p:
        common = dict(viewport=VIEW, user_agent=MOBILE_UA, device_scale_factor=2,
                      is_mobile=True, has_touch=True)
        if dark:
            common["color_scheme"] = "dark"
        # channel="chromium" is the recorder's default (playbook §10b: the full
        # build is far less bot-detectable than headless-shell). Measured
        # 2026-08-06 on this machine: EVERY channel-pinned launch — "chromium"
        # AND "chrome" — hangs until the launch timeout, while the *same*
        # Chrome-for-Testing binary launched with no channel comes up in 0.5s.
        # A preflight that dies on that is worse than useless, so it falls back
        # to the bundled launch and records which one it used.
        ctx = None
        for chan in ("chromium", None):
            la = dict(headless=True, timeout=45000,
                      args=["--disable-blink-features=AutomationControlled"])
            if chan:
                la["channel"] = chan
            try:
                if profile:
                    ctx = p.chromium.launch_persistent_context(str(profile), **la, **common)
                else:
                    ctx = p.chromium.launch(**la).new_context(**common)
                verdict["launch_channel"] = chan or "bundled"
                break
            except Exception as e:
                verdict.setdefault("launch_failures", []).append(
                    f"channel={chan or 'bundled'}: {type(e).__name__}")
        if ctx is None:
            verdict["error"] = "no chromium build would launch"
            print(json.dumps(verdict, indent=2))
            return 5
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            verdict["error"] = f"goto failed: {e}"
            print(json.dumps(verdict, indent=2))
            ctx.close()
            return 5
        time.sleep(settle)          # SPA shells paint their chrome late
        try:
            body = page.inner_text("body", timeout=8000)
        except Exception:
            body = ""
        verdict["url_after"] = page.url
        verdict["body_chars"] = len(body)
        verdict["body_head"] = body[:400]
        if shot:
            Path(shot).parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shot), full_page=False)
            verdict["screenshot"] = str(shot)
        walls = []
        if LOGIN_MARKERS.search(body):
            walls.append("login_text")
        if GOOGLE_LOGIN_MARKERS.search(body):
            walls.append("google_login_text")
        if any(h in (page.url or "") for h in AUTH_HOSTS):
            walls.append(f"auth_redirect:{(page.url or '').split('?')[0]}")
        if not body.strip():
            walls.append("empty_body")
        verdict["auth_walls"] = walls
        verdict["logged_in"] = not walls
        for t in expect_terms:
            (verdict["found"] if re.search(t, body, re.I) else verdict["missing"]).append(t)
        ctx.close()

    if not verdict["logged_in"]:
        verdict["state"] = "LOGGED_OUT"
        verdict["next"] = (f"python3 scripts/record_demo.py --site {site or 'custom'} "
                           f"--setup-profile   # headed, human-only")
        code = 3
    elif verdict["missing"]:
        verdict["state"] = "GATED"
        verdict["next"] = ("this account cannot show the feature on camera — "
                           "take the fallback demo path; never claim it in vision")
        code = 4
    else:
        verdict["state"] = "AVAILABLE"
        verdict["next"] = "film it"
        code = 0
    print(json.dumps(verdict, indent=2))
    return code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", choices=SITES.keys())
    ap.add_argument("--url"); ap.add_argument("--selector")
    ap.add_argument("--prompt", required=False)
    ap.add_argument("-o", "--out", default="demo.mp4")
    ap.add_argument("--wait-after", type=float, default=14, help="secs to film the streaming answer")
    ap.add_argument("--setup-profile", action="store_true", help="open headed browser to log in once")
    ap.add_argument("--no-profile", action="store_true",
                    help="ignore the site's saved session (clean logged-out state, no memory/personalization)")
    ap.add_argument("--require-login", action="store_true",
                    help="abort unless the profile is logged in (DOM probe, not "
                         "page.url - chatgpt.com does not redirect). Use for any "
                         "recording whose content depends on the account.")
    ap.add_argument("--seed-terms",
                    help="comma-separated regexes the answer must contain, e.g. "
                         "'channel,beginner,45[- ]?min,short and concrete'. "
                         "Enables the personalized-answer acceptance check.")
    ap.add_argument("--personalized-within", type=float, default=3.0,
                    help="max secs between first answer token and the first "
                         "token matching --seed-terms (default 3.0)")
    ap.add_argument("--forbid-terms",
                    help="comma-separated regexes the answer must NOT contain. "
                         "Acceptance gate for a COLD/no-memory take recorded on "
                         "a logged-in account, e.g. 'YouTube,channel,beginner'.")
    ap.add_argument("--redact-pii", action="store_true",
                    help="blur account email / saved-chat titles before filming "
                         "and assert none are exposed (use with --require-login)")
    ap.add_argument("--dark", action="store_true",
                    help="record with prefers-color-scheme: dark (the account's "
                         "Appearance setting is untouched)")
    ap.add_argument("--followup",
                    help="second prompt typed into the SAME chat after the "
                         "first answer settles (fail -> fix -> proof in one "
                         "tape). Switches the sidecar to the multi-punch form.")
    ap.add_argument("--followup-wait", type=float,
                    help="secs to film the follow-up answer (default: --wait-after)")
    ap.add_argument("--fail-terms",
                    help="comma-separated regexes the FIRST answer must contain "
                         "(>=1) — the measured proof that the problem the short "
                         "is about is actually on screen, e.g. "
                         "'hope this email finds you well,do not hesitate'")
    ap.add_argument("--fix-forbid-terms",
                    help="comma-separated regexes the FOLLOW-UP answer must NOT "
                         "contain — the measured proof that the one-line fix "
                         "worked")
    ap.add_argument("--fix-seed-terms",
                    help="comma-separated regexes the FOLLOW-UP answer MUST "
                         "contain (>=1) — for a fix that ADDS context rather "
                         "than removing a tell: wording that could only come "
                         "from the material just handed over. Keep them "
                         "LEXICAL, never numeric (Ep24).")
    ap.add_argument("--followup-paste",
                    help="path to a text file inserted into the composer in one "
                         "motion (a real paste) before --followup is typed — the "
                         "only way a logged-out session can hand over a document, "
                         "since the anonymous file inputs are image-only")
    ap.add_argument("--followup-scroll", action="store_true",
                    help="after the follow-up answer, scroll to the bottom of "
                         "the conversation and hold still — needed when the "
                         "handed-over material is tall enough to push the "
                         "answer below the fold. Stamps fix_scrolls + a "
                         "fix_proof_start/end window for the payoff beat.")
    ap.add_argument("--preflight", action="store_true",
                    help="PLAN-TIME check: load the profile, DOM-probe login, and "
                         "assert --expect-terms are visible — films nothing. "
                         "Exit 0 AVAILABLE / 3 LOGGED_OUT / 4 GATED so a brief can "
                         "branch PATH A vs PATH B before any VO is rendered.")
    ap.add_argument("--expect-terms",
                    help="comma-separated regexes the page must show for the "
                         "capability to be filmable (--preflight only)")
    ap.add_argument("--shot", help="write a screenshot of the preflight page here")
    args = ap.parse_args()

    submit = None
    if args.site:
        cfg = SITES[args.site]
        url, sel, submit = cfg["url"], cfg["input"], cfg.get("submit")
        profile = PROFILES / args.site if cfg.get("profile") else None
    else:
        if not (args.url and args.selector):
            sys.exit("need --site or (--url and --selector)")
        url, sel, profile = args.url, args.selector, None

    if args.no_profile and not args.setup_profile:
        profile = None

    if args.setup_profile:
        profile = profile or PROFILES / (args.site or "custom")
        profile.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                str(profile), headless=False, channel="chromium",
                viewport={"width": 900, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.goto(url)
            print(f"[{args.site}] Log in in the browser window, then CLOSE the window to save the session.")
            try:
                pg.wait_for_event("close", timeout=15 * 60 * 1000)
            except Exception:
                pass
            try:
                ctx.close()
            except Exception:
                pass
        print(f"Session saved to {profile}")
        return

    if args.preflight:
        expect = [t.strip() for t in (args.expect_terms or "").split(",") if t.strip()]
        sys.exit(preflight(args.url or url, profile, expect, site=args.site,
                           dark=args.dark, shot=args.shot))

    if not args.prompt:
        sys.exit("--prompt required")
    terms = [t.strip() for t in (args.seed_terms or "").split(",") if t.strip()]
    forbid = [t.strip() for t in (args.forbid_terms or "").split(",") if t.strip()]
    if terms and forbid:
        sys.exit("--seed-terms and --forbid-terms are opposite acceptance gates; "
                 "a take is either the personalized one or the cold one.")
    fail = [t.strip() for t in (args.fail_terms or "").split(",") if t.strip()]
    fixforbid = [t.strip() for t in (args.fix_forbid_terms or "").split(",") if t.strip()]
    fixseed = [t.strip() for t in (args.fix_seed_terms or "").split(",") if t.strip()]
    if (fail or fixforbid or fixseed) and not args.followup:
        sys.exit("--fail-terms / --fix-forbid-terms / --fix-seed-terms gate the "
                 "two halves of a --followup tape; there is only one answer "
                 "without it.")
    paste_text = None
    if args.followup_paste:
        if not args.followup:
            sys.exit("--followup-paste is the material handed over BEFORE the "
                     "follow-up question; it needs --followup.")
        paste_text = Path(args.followup_paste).read_text()
    if terms and fail:
        sys.exit("--seed-terms and --fail-terms both gate the FIRST answer; "
                 "pick one.")
    out, timeline = record(url, sel, args.prompt, args.out,
                           wait_after=args.wait_after, profile=profile,
                           submit_sel=submit, require_login=args.require_login,
                           seed_terms=terms, site=args.site, dark=args.dark,
                           forbid_terms=forbid, redact=args.redact_pii,
                           followup=args.followup,
                           followup_wait=args.followup_wait,
                           fail_terms=fail, fix_forbid_terms=fixforbid,
                           fix_seed_terms=fixseed, followup_paste=paste_text,
                           followup_scroll=args.followup_scroll)
    if timeline.get("first_token") is not None:
        print(f"first_token {timeline['first_token']}s")
    if forbid:
        problem = check_generic(timeline, forbid)
        if problem:
            sys.exit(f"ACCEPTANCE {problem}\n(kept {out} for inspection)")
        print(f"cold OK: none of {forbid} in {timeline['observed']['answer_chars']} "
              f"answer chars")
    if terms:
        # the footage is written first either way, so a failed take can be
        # inspected rather than just described
        problem = check_personalized(timeline, args.prompt,
                                     args.personalized_within)
        if problem:
            sys.exit(f"ACCEPTANCE {problem}\n(kept {out} for inspection)")
        print(f"first_personalized {timeline['first_personalized']}s "
              f"(+{timeline['personalized_delay_s']}s, "
              f"matched {timeline['matched_term']!r})")
    if fail:
        hit = timeline["observed"].get("fail_matched") or []
        if not hit:
            sys.exit(f"ACCEPTANCE FAIL: none of {fail} appeared in the first "
                     f"answer, so the problem this short is about is not on "
                     f"camera.\n  answer opened: "
                     f"{timeline['observed']['answer_head'][:200]!r}\n"
                     f"  RE-RECORD with a prompt more likely to draw the tell "
                     f"(kept {out} for inspection)")
        print(f"fail tells on camera: {hit}")
    if fixforbid:
        hit = timeline["observed"].get("fix_forbidden_term")
        if hit:
            sys.exit(f"ACCEPTANCE FAIL: the rewrite still matched {hit!r} — the "
                     f"one-line fix did not visibly work, so there is no proof "
                     f"beat.\n  rewrite opened: "
                     f"{timeline['observed']['fix_answer_head'][:200]!r}\n"
                     f"  RE-RECORD (kept {out} for inspection)")
        print(f"fix OK: none of {fixforbid} in "
              f"{timeline['observed']['fix_answer_chars']} rewrite chars")
    if fixseed:
        hit = timeline["observed"].get("fix_seed_matched") or []
        if not hit:
            sys.exit(f"ACCEPTANCE FAIL: the second answer never used wording "
                     f"from the material handed over ({fixseed}), so the payoff "
                     f"beat has nothing to prove — the two answers are just two "
                     f"answers.\n  second answer opened: "
                     f"{timeline['observed']['fix_answer_head'][:200]!r}\n"
                     f"  RE-RECORD (kept {out} for inspection)")
        print(f"fix grounded on camera: {hit} "
              f"(first at {timeline.get('fix_seeded')}s, "
              f"+{timeline.get('fix_seeded_delay_s')}s after first token)")
    print(f"OK {out}")


if __name__ == "__main__":
    main()
