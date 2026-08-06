#!/usr/bin/env python3
"""Suno-via-Chrome song auditions in one command (PRODUCTION-PLAYBOOK §2, §15).

Every Pipeline-A channel buys its bed from Suno Pro, and until now every song was
a hand-flown Chrome session: click Custom, paste the style, fight the lyrics box,
click Create twice, hunt the song ids, curl the CDN, retry the 403, then eyeball
which take opens softest. Four productions land inside a week on that same flow.
This script IS that checklist, with every §2 gotcha baked in as code:

  1. It attaches to the operator's REAL Chrome over CDP -- never a fresh Playwright
     profile. The Suno session (and its Pro seat) lives in real Chrome, the same
     reason §10b routes Google SSO through real Chrome. No debug port up? It prints
     the exact claude-in-chrome recipe instead of silently doing the wrong thing.
  2. Style field is a real <textarea> -> plain fill. Lyrics is a Lexical
     contenteditable DIV -> fill() raises "DIV not supported", so we click in and
     insert text through the keyboard.
  3. A big lyrics insert can throw a CDP "renderer frozen" timeout -- THE TEXT
     STILL LANDS. We swallow that timeout, wait ~18s, verify by reading the DOM,
     and never re-type (re-typing is how you get the lyrics twice).
  4. --double clicks Create twice; the form retains its inputs, so that is
     2 gens x 2 variations = 4 candidates for the §15 audition pool, free.
  5. Song ids: §2 says scrape a[href*="/song/"]. 🔴 THAT SELECTOR IS DEAD on the
     live v5.5 UI (checked 6 Aug 2026) -- workspace rows are virtualised React
     components with no anchor and no id in any attribute, and /me is the same. So
     ids are harvested primarily by watching the app's OWN authenticated API
     responses (we cannot call that API ourselves: it wants a Clerk bearer token,
     cookies alone give 401). The anchor scrape is kept as a secondary source.
     Audio still comes from cdn1.suno.ai/{id}.mp3, and the 2nd variation still
     403s for ~1 min, so downloads retry with backoff.
  6. It asserts the logged-in account is a PAID seat BEFORE generating, by reading
     "Current Plan" on /account. Free-tier songs stay non-commercial even after you
     upgrade; the only fix is regenerating on Pro, so the check belongs before the
     credits are spent. It must NOT be done by word-scanning /create -- the left
     rail says "Upgrade to Premier" on a free account, which reads as a pass.
  7. It ranks candidates by first-2s attack (ffmpeg volumedetect) into
     candidates.json -- loudest-first by default, --invert for calm channels
     (Lulla, Poly) that want the softest cold open at the top.

HUMAN-IN-THE-LOOP IS UNCHANGED (§1.2): this generates, downloads and RANKS.
A human picks the winner with their ears. The ranking is a reading order, not a verdict.

Usage:
  # once, in the operator's own terminal -- real Chrome with a debug port:
  python3 scripts/suno_gen.py --print-chrome-recipe

  # then, per song:
  python3 scripts/suno_gen.py \
      --style 'gentle lullaby, music box' \
      --lyrics channels/pip-moonlit-garden/songs/07_lyrics.txt \
      --exclude-styles 'drums, percussion, brass' \
      --double --invert \
      --out-dir channels/pip-moonlit-garden/songs/candidates/07/

  # re-rank mp3s that are already on disk (no browser, no credits):
  python3 scripts/suno_gen.py --rank-only channels/.../candidates/07/ --invert

  # no debug port / CDP wedged -> the hand-flown fallback, step by step:
  python3 scripts/suno_gen.py --print-recipe --style '...' --lyrics lyrics.txt
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CDP = os.environ.get("SUNO_CDP_URL", "http://127.0.0.1:9222")
DEFAULT_BASE = "https://suno.com"
DEFAULT_CDN = "https://cdn1.suno.ai"
# a dedicated user-data-dir is mandatory: Chrome 136+ refuses --remote-debugging-port
# on the default profile, so "real Chrome" here means a real-Chrome profile you log
# into once, not the Default one. Same one-time-login doctrine as §10b.
CDP_PROFILE = Path.home() / ".chrome-suno-cdp"

SONG_ID_RE = re.compile(r"/song/([0-9a-fA-F-]{36})")
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# cdn1.suno.ai/<id>.mp3 is the audio; cdn2.suno.ai/image_<id>.jpeg is that clip's
# cover art -- and the cover art is what the workspace loads the moment a take
# appears, which makes it the FIRST place a new song id becomes visible.
CDN_ID_RE = re.compile(rf"cdn\d?\.suno\.(?:ai|com)/(?:image_)?({_UUID})", re.I)
UUID_JSON_RE = re.compile(rf'"(?:id|clip_id|song_id)"\s*:\s*"({_UUID})"', re.I)
PAID_WORDS = ("pro", "premier", "plus", "enterprise", "team")


# --------------------------------------------------------------------------- utils
def log(msg):
    print(f"[suno] {msg}", flush=True)


def warn(msg):
    print(f"[suno] !! {msg}", flush=True)


def die(msg, code=1):
    print(f"[suno] FATAL: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def http_json(url, timeout=4):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ------------------------------------------------------------------- the recipes
def chrome_recipe(cdp_url):
    port = cdp_url.rsplit(":", 1)[-1].strip("/")
    return f"""
──────────────────────────────────────────────────────────────────────────────
 Start REAL Chrome with a debug port (once per boot; log into Suno once, ever)
──────────────────────────────────────────────────────────────────────────────
Chrome 136+ refuses --remote-debugging-port on the DEFAULT profile, so this uses
a dedicated real-Chrome profile. It is still real Chrome (real fingerprint, real
extensions, a real human-logged-in session) -- just not the Default user-data-dir.
Run this in YOUR OWN terminal, not from an agent shell:

  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\
      --remote-debugging-port={port} \\
      --user-data-dir="{CDP_PROFILE}" \\
      --no-first-run --no-default-browser-check \\
      https://suno.com/create

FIRST TIME ONLY: log into Suno in that window with the PRO account. The session
persists in that profile forever after -- §10b's "log in once, film many" rule.
Confirm the port is live:

  curl -s {cdp_url}/json/version

Then re-run this script. Leave that Chrome window open while it drives.
──────────────────────────────────────────────────────────────────────────────
"""


def cic_recipe(args, lyrics_text):
    """The hand-flown claude-in-chrome fallback -- the §2 checklist, verbatim."""
    n_create = 2 if args.double else 1
    n_cand = 4 if args.double else 2
    excl = args.exclude_styles or "(none)"
    head = (lyrics_text or "").strip().splitlines()
    head = head[0] if head else "(empty)"
    return f"""
──────────────────────────────────────────────────────────────────────────────
 FALLBACK: drive Suno by hand through claude-in-chrome (no CDP port available)
──────────────────────────────────────────────────────────────────────────────
 1. tabs_create_mcp, then navigate -> {args.base_url}/account
 2. CONFIRM THE ACCOUNT IS A PAID SEAT before generating anything. Read the
    "Current Plan" block -- it says "Pro Plan" / "Free Plan" outright. Do NOT
    judge by the left rail: it says "Upgrade to Premier" on a FREE account too,
    and free-tier songs stay non-commercial even after you upgrade (§2).
 3. navigate -> {args.base_url}/create and select the "Advanced" tab (v5.5
    renamed "Custom"); you need BOTH a Styles box and a Lyrics box on screen.
 4. Styles field is a real <textarea> -> form_input works. Paste:
      {args.style}
    Genre descriptors ONLY. Suno silently strips artist names ("kumar sanu" ->
    Bollywood / Playback / Ghazal) and toasts about it -- and it is our
    compliance rule anyway (§8).
 5. Exclude styles: {excl}
    (open "Advanced Options" if the field is not visible)
 6. Lyrics box is a Lexical contenteditable DIV. form_input FAILS on it
    ("DIV not supported"). Instead: left_click into the box, then `type` the
    whole lyric. First line should read:
      {head}
 7. That big type will very likely throw a CDP "renderer frozen" timeout.
    THE TEXT STILL LANDED. Do NOT re-type -- wait ~15-20s, then screenshot to
    confirm. Re-typing is how you end up with the lyrics pasted twice.
 8. Click Create. The click works fine even when the type "timed out".
 9. --double: the form RETAINS all inputs after submit, so click Create a
    second time for {n_cand} candidates from one typing session (§15 audition trick).
    This run wants {n_create} Create click(s).
10. Two variations render per click. §2 says scrape a[href*="/song/"] -- that
    returns ZERO on v5.5 (rows are virtualised, no anchor, no id attribute).
    Through the extension the reliable move is to CLICK each new row and read the
    id out of the address bar (it navigates to /song/<uuid>), then go back.
    read_network_requests filtered to 'cdn1.suno' also surfaces them once the
    player touches a take.
11. Download each: {args.cdn_base}/{{id}}.mp3
    The 2nd variation's mp3 403s for ~1 min after the 1st goes live -- retry.
12. Drop the mp3s in {args.out_dir} and rank them without a browser:
      python3 scripts/suno_gen.py --rank-only {args.out_dir}{' --invert' if args.invert else ''}
──────────────────────────────────────────────────────────────────────────────
"""


# ------------------------------------------------------------------ style hygiene
def lint_style(style, allow_names=False):
    """§2: Suno auto-strips artist names from the style prompt (and §8 forbids them).

    Cheap heuristic -- flag Title Case bigrams that are not known genre words. It
    warns, it does not block; a false positive must never cost a production run.
    """
    genre_ok = {
        "Bollywood", "Lo", "Fi", "Hip", "Hop", "R", "B", "Music", "Box", "BPM",
        "Indian", "Hindi", "Latin", "Afro", "Cuban", "Bossa", "Nova", "New", "Age",
        "West", "Coast", "East", "Trip", "Drum", "Bass", "K", "Pop", "J",
    }
    bigrams = re.findall(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b", style)
    hits = [f"{a} {b}" for a, b in bigrams if a not in genre_ok and b not in genre_ok]
    if hits and not allow_names:
        warn(f"style prompt looks like it names a person: {hits}")
        warn("Suno strips artist names anyway, and §8 forbids them -- use genre "
             "descriptors. Pass --allow-artist-names to silence this.")
    return hits


# ------------------------------------------------------------------------- ffmpeg
def ffprobe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return round(float(out), 2)
    except Exception:
        return None


def attack_db(path, seconds=2.0):
    """Mean/peak dBFS of the first N seconds -- the objective cold-open attack (§15).

    -t before -i so ffmpeg only decodes the head of the file.
    """
    try:
        p = subprocess.run(
            ["ffmpeg", "-v", "info", "-t", str(seconds), "-i", str(path),
             "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=120)
    except Exception as e:
        warn(f"volumedetect failed on {Path(path).name}: {e}")
        return {"mean_db": None, "max_db": None}
    err = p.stderr
    mean = re.search(r"mean_volume:\s*(-?[\d.]+) dB", err)
    peak = re.search(r"max_volume:\s*(-?[\d.]+) dB", err)
    return {
        "mean_db": float(mean.group(1)) if mean else None,
        "max_db": float(peak.group(1)) if peak else None,
    }


def rank_candidates(cands, invert=False, window=2.0):
    """Rank by first-`window` attack. Default loudest-first; --invert softest-first.

    A mean_db of None (unreadable audio) always sorts last, either way.
    """
    for c in cands:
        c["first_%gs" % window] = attack_db(c["file"], window)
        c["duration_s"] = ffprobe_duration(c["file"])
    key = "first_%gs" % window

    def sort_key(c):
        v = c[key]["mean_db"]
        if v is None:
            return (1, 0.0)
        return (0, v if invert else -v)

    ordered = sorted(cands, key=sort_key)
    for i, c in enumerate(ordered, 1):
        c["rank"] = i
    return ordered


def write_candidates_json(out_dir, cands, meta, invert, window):
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ranking": {
            "metric": f"ffmpeg volumedetect over the first {window:g}s",
            "order": "softest attack first (--invert, calm channels)" if invert
                     else "strongest attack first",
            "doctrine": "PRODUCTION-PLAYBOOK §1.2 -- ranking is a listening order, "
                        "not a verdict. A human picks the winner by ear.",
        },
        **meta,
        "candidates": cands,
    }
    path = Path(out_dir) / "candidates.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def print_ranking(cands, window):
    key = "first_%gs" % window
    log("")
    log("  rank  candidate                              first-%gs mean / peak   len" % window)
    for c in cands:
        a = c[key]
        mean = f"{a['mean_db']:>7.1f}" if a["mean_db"] is not None else "      ?"
        peak = f"{a['max_db']:>7.1f}" if a["max_db"] is not None else "      ?"
        dur = f"{c['duration_s']:>6.1f}s" if c.get("duration_s") else "      ?"
        log(f"  {c['rank']:>4}  {Path(c['file']).name:<38}  {mean} /{peak} dB  {dur}")
    log("")
    log("Ranking is a listening ORDER, not a pick (§1.2). Play them top-down and")
    log("choose with your ears; log the winner in the channel QUALITY-LEDGER.md.")


# ----------------------------------------------------------------------- download
def download_mp3(cdn_base, song_id, dest, tries=14, first_delay=6):
    """§2: the 2nd variation's mp3 403s for ~1 min after the 1st goes live -> retry."""
    url = f"{cdn_base}/{song_id}.mp3"
    delay = first_delay
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "suno_gen/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            if len(data) < 20_000:
                raise urllib.error.URLError(f"suspiciously small body ({len(data)}B)")
            Path(dest).write_bytes(data)
            log(f"    downloaded {Path(dest).name}  ({len(data)/1e6:.1f} MB, try {attempt})")
            return url, len(data)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                log(f"    {song_id[:8]}… {e.code} (still rendering) — retry in {delay}s"
                    f" [{attempt}/{tries}]")
            else:
                log(f"    {song_id[:8]}… HTTP {e.code} — retry in {delay}s [{attempt}/{tries}]")
        except Exception as e:
            log(f"    {song_id[:8]}… {type(e).__name__}: {e} — retry in {delay}s "
                f"[{attempt}/{tries}]")
        if attempt < tries:
            time.sleep(delay)
            delay = min(delay + 4, 25)
    warn(f"gave up downloading {url}")
    return url, 0


# -------------------------------------------------------------------- the browser
def attach(pw, cdp_url):
    """Attach to the operator's real Chrome. Returns (browser, context) or None."""
    try:
        ver = http_json(f"{cdp_url}/json/version")
    except Exception:
        return None
    log(f"attached to {ver.get('Browser', 'Chrome')} via {cdp_url}")
    browser = pw.chromium.connect_over_cdp(cdp_url)
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    return browser, ctx


def open_create_page(ctx, base_url):
    """Reuse an already-open Suno tab if there is one; else open a new one."""
    for pg in ctx.pages:
        try:
            if base_url.split("//")[-1].split("/")[0] in (pg.url or ""):
                pg.bring_to_front()
                if "/create" not in pg.url:
                    pg.goto(f"{base_url}/create", wait_until="domcontentloaded")
                return pg
        except Exception:
            continue
    pg = ctx.new_page()
    pg.goto(f"{base_url}/create", wait_until="domcontentloaded")
    return pg


def assert_paid_seat(page, base_url, allow_free=False):
    """§2 trap: free-tier songs stay non-commercial FOREVER, even after upgrading.

    Checked BEFORE a single credit is spent, on /account -- and ONLY on /account.

    Two tempting shortcuts are both wrong, verified against the live site on
    6 Aug 2026: studio-api-prod.suno.com wants a Clerk bearer token the app mints
    (cookies alone -> 401 on every endpoint), and a plain word-scan of /create
    matches "Upgrade to Premier" in the left rail, which reports a FREE account as
    Premier -- the exact false pass this gate exists to prevent. The account page
    states it unambiguously: "Current Plan" / "Pro Plan".
    """
    state = {"logged_in": None, "plan": None, "source": None}
    try:
        page.goto(f"{base_url}/account", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        body = page.inner_text("body") or ""
    except Exception as e:
        die(f"could not open {base_url}/account to check the seat: {e}", 4)

    low = body.lower()
    if "sign in" in low and "current plan" not in low:
        state["logged_in"] = False
    else:
        state["logged_in"] = True

    # "Current Plan\nPro Plan" -- take the line AFTER the label, never a loose word.
    m = re.search(r"current plan\s*\n\s*([^\n]+)", low)
    if m:
        state["plan"], state["source"] = m.group(1).strip(), "/account Current Plan"
    else:
        m2 = re.search(r"\b(free|pro|premier|plus|enterprise|team)\s+plan\b", low)
        if m2:
            state["plan"], state["source"] = f"{m2.group(1)} plan", "/account plan text"

    credits = re.search(r"credits remaining\s*\n\s*([\d,]+)", low)
    if credits:
        state["credits"] = credits.group(1)

    plan = (state["plan"] or "").lower()
    # "Free Plan" is an explicit NO, never a near-miss on a paid word.
    paid = "free" not in plan and any(w in plan for w in PAID_WORDS)

    if state["logged_in"] is False:
        die("not logged into Suno in that Chrome profile. Open the CDP Chrome "
            "window, sign in with the PRO account, and re-run.", 3)
    if paid:
        log(f"account check: PAID seat ({state['plan']}, via {state['source']}"
            f"{', ' + state['credits'] + ' credits' if state.get('credits') else ''}) "
            "— songs are commercial-eligible")
        return state
    if allow_free:
        warn(f"account plan reads '{state['plan'] or 'unknown'}' and --allow-free-tier "
             "was passed. Anything generated now stays NON-COMMERCIAL forever, even "
             "if you upgrade later (§2). Do not ship it on a monetised channel.")
        return state
    die(f"could not confirm a paid Suno seat (plan reads '{state['plan'] or 'unknown'}'). "
        "Free-tier songs stay non-commercial even after you upgrade -- regenerating on "
        "Pro is the only fix, so this refuses to burn the typing. Fix the account, or "
        "pass --allow-free-tier if you truly want a throwaway.", 4)


def ensure_advanced_mode(page):
    """Expose BOTH the Styles textarea and the Lyrics editor.

    v5.5 renamed the old "Custom" toggle to a Simple / Advanced / Sounds tab strip
    (verified live 6 Aug 2026); "Advanced" is the one with a Lyrics box. Both names
    are tried, and success is decided by what is on screen, not by the click.
    """
    if find_style_box(page) is not None and find_lyrics_box(page) is not None:
        return True
    for label in ("Advanced", "Custom"):
        try:
            el = page.locator(f'button:has-text("{label}")').first
            if el.count() and el.is_visible():
                el.click(timeout=3000)
                page.wait_for_timeout(1200)
                if find_lyrics_box(page) is not None:
                    log(f"    switched the create form to {label} mode")
                    return True
        except Exception:
            continue
    return False


def first_visible(page, selectors):
    """First selector that resolves to a VISIBLE element.

    count() happily matches display:none nodes, so probing on count() alone finds the
    exclude-styles box while it is still collapsed behind Advanced Options and then
    hangs for 30s in fill(). Visibility is the only useful existence test here.
    """
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.count() and el.is_visible():
                return el
        except Exception:
            continue
    return None


def find_style_box(page):
    """§2: the Styles field is a REAL <textarea> -> ordinary fill() works.

    Do NOT match on placeholder: v5.5 fills it with a ROTATING genre example
    ("kawaii edm, triplet, experimental beats…" one load, "eletrônico, bridge,
    torchy…" the next), so a placeholder selector passes locally and fails on the
    operator's next page load. The stable anchor is the wrapper attribute.
    """
    return first_visible(page, ('[data-testid="create-form-styles-wrapper"] textarea',
                                'div[class*="styles" i] textarea',
                                'textarea[aria-label*="style" i]',
                                'textarea[placeholder*="style" i]'))


def find_exclude_box(page):
    """Exclude-styles usually hides behind an Advanced Options disclosure."""
    def probe():
        return first_visible(page, ('textarea[placeholder*="exclude" i]',
                                    'input[placeholder*="exclude" i]',
                                    'textarea[aria-label*="exclude" i]'))

    el = probe()
    if el is not None:
        return el
    for sel in ('button:has-text("Advanced")', 'text="Advanced Options"',
                'button:has-text("More Options")'):
        try:
            d = page.locator(sel).first
            if d.count() and d.is_visible():
                d.click(timeout=2500)
                page.wait_for_timeout(700)
                el = probe()
                if el is not None:
                    return el
        except Exception:
            continue
    return None


def find_lyrics_box(page):
    """§2: the Lyrics editor is a Lexical contenteditable DIV, not a textarea."""
    return first_visible(page, ('[aria-label="Lyrics editor"][contenteditable="true"]',
                                'div[contenteditable="true"][data-lexical-editor="true"]',
                                '[role="textbox"][contenteditable="true"]',
                                'div[contenteditable="true"]'))


def type_lexical(page, el, text, settle=18):
    """Put a full lyric into the Lexical DIV and survive the frozen renderer (§2).

    fill() raises "DIV not supported", so: click in, clear, and push the text
    through the keyboard. insert_text is one CDP command rather than N keystrokes,
    which is the same shape as the documented working path but far less likely to
    wedge the renderer -- and when it DOES wedge, the text has already landed, so
    we swallow the timeout, wait, and VERIFY instead of re-typing. Re-typing is how
    the lyrics end up in the box twice.
    """
    el.click()
    page.wait_for_timeout(400)
    try:
        page.keyboard.press("Meta+A" if sys.platform == "darwin" else "Control+A")
        page.keyboard.press("Backspace")
    except Exception:
        pass

    froze = False
    try:
        page.keyboard.insert_text(text)
    except Exception as e:
        froze = True
        warn(f"lyrics insert threw ({type(e).__name__}) — this is the known §2 "
             f"'renderer frozen' timeout. The text almost certainly LANDED; "
             f"waiting {settle}s and verifying instead of re-typing.")
    page.wait_for_timeout(int((settle if froze else 2.5) * 1000))

    landed = read_lexical(el)
    if _matches(landed, text):
        log(f"    lyrics verified in the editor ({len(landed)} chars"
            f"{', after a frozen-renderer timeout' if froze else ''})")
        return True

    if landed.strip():
        warn(f"lyrics editor holds {len(landed)} chars but does not match the source "
             f"({len(text)} chars). NOT re-typing — inspect the tab before Create.")
        return False

    warn("editor still empty — falling back to character typing (slow path).")
    try:
        el.click()
        page.keyboard.type(text, delay=1)
    except Exception as e:
        warn(f"character typing threw too ({type(e).__name__}); waiting {settle}s.")
    page.wait_for_timeout(settle * 1000)
    landed = read_lexical(el)
    ok = _matches(landed, text)
    log(f"    lyrics {'verified' if ok else 'NOT verified'} after fallback "
        f"({len(landed)} chars)")
    return ok


def _matches(landed, want):
    """Lexical normalises whitespace, so compare on squashed alphanumerics."""
    def norm(s):
        return re.sub(r"\W+", "", s or "").lower()
    a, b = norm(landed), norm(want)
    if not a or not b:
        return False
    return a[:400] == b[:400] and abs(len(a) - len(b)) <= max(20, len(b) * 0.05)


def read_lexical(el):
    try:
        return el.inner_text() or ""
    except Exception:
        try:
            return el.text_content() or ""
        except Exception:
            return ""


def dom_song_ids(page):
    """§2's original scrape: a[href*="/song/"].

    🔴 UPDATED 6 Aug 2026 — this now returns NOTHING on the live v5.5 UI. The
    workspace rows are virtualised React components with no anchor and no id in any
    attribute; /me is the same. It is kept because it still works on /song pages and
    older layouts, but it can no longer be the only source. See sniff_song_ids.
    """
    try:
        hrefs = page.eval_on_selector_all(
            'a[href*="/song/"]', "els => els.map(e => e.getAttribute('href'))")
    except Exception:
        return []
    out = []
    for h in hrefs or []:
        m = SONG_ID_RE.search(h or "")
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def start_sniffer(page):
    """Watch the app's OWN traffic for song ids -- the replacement for the dead scrape.

    Calling studio-api-prod.suno.com ourselves is a dead end (it wants a Clerk
    bearer token the app mints; cookies alone -> 401 on every endpoint, verified
    6 Aug 2026). Watching what the app already fetches needs no token at all.

    The winning signal, confirmed on the live Lulla #07 audition: the workspace
    pulls each new take's cover art from cdn2.suno.ai/image_<clip-id>.jpeg the
    moment the row appears -- so the id shows up in a plain image request, well
    before any audio is touched. URLs are captured (not bodies) for that, and
    JSON bodies are read for the API case.

    Responses are queued and read OUTSIDE the event handler -- calling .text()
    inside a sync-API handler can deadlock the driver.
    """
    queue = []
    page.on("response", lambda r: queue.append(r))
    page.on("request", lambda r: queue.append(r))
    return queue


def drain_sniffer(queue, found):
    """Pull ids out of queued responses. `found` maps id -> source, best source wins.

    Source ranking matters: a uuid that appears as a cdn1 audio URL IS a song, while
    a bare "id" in some /api/ payload might be a user, a workspace or a persona.
    Weak-source ids are used only to fill a shortfall, and are labelled in the log.
    """
    while queue:
        ev = queue.pop(0)
        try:
            url = ev.url
        except Exception:
            continue
        # the URL alone carries the id for audio and cover-art hits
        for m in CDN_ID_RE.finditer(url):
            found[m.group(1)] = "cdn-url"             # definitive
        if "/api/" not in url:
            continue
        try:
            if "json" not in (ev.headers or {}).get("content-type", ""):
                continue
            body = ev.text()                          # Response only; Request has no .text
        except Exception:
            continue
        for m in CDN_ID_RE.finditer(body):
            found[m.group(1)] = "cdn-url"
        for m in UUID_JSON_RE.finditer(body):
            found.setdefault(m.group(1), "api-json")  # weak, fills shortfalls only
    return found


def click_create(page):
    for sel in ('button:has-text("Create")', '[data-testid="create-button"]',
                'button[type="submit"]:has-text("Create")'):
        try:
            el = page.locator(sel).first
            if el.count() and el.is_enabled():
                el.click(timeout=6000)
                return True
        except Exception:
            continue
    return False


def collect_ids(page, queue, found):
    """Union of every id source, each id tagged with the strongest source that saw it."""
    drain_sniffer(queue, found)
    for i in dom_song_ids(page):
        found[i] = "cdn-url" if found.get(i) == "cdn-url" else "song-anchor"
    return found


def wait_for_new_ids(page, queue, found, before, want, timeout_s):
    """Poll every source until `want` NEW ids show up (or we run out of patience).

    Strong-source ids (a real audio URL / a /song/ anchor) are taken first; weak
    /api/ uuids only fill a shortfall, and say so in the log.
    """
    deadline = time.time() + timeout_s
    reported = 0
    while True:
        collect_ids(page, queue, found)
        fresh = {i: s for i, s in found.items() if i not in before}
        strong = [i for i, s in fresh.items() if s in ("cdn-url", "song-anchor")]
        weak = [i for i, s in fresh.items() if s == "api-json"]
        picked = strong + weak[: max(0, want - len(strong))]
        if len(picked) > reported:
            reported = len(picked)
            log(f"    {len(picked)}/{want} new song id(s): "
                f"{', '.join(i[:8] for i in picked)}"
                f"{'  (incl. %d unconfirmed)' % max(0, reported - len(strong)) if len(strong) < reported else ''}")
        if len(picked) >= want or time.time() >= deadline:
            return picked[:want] if len(picked) >= want else picked
        page.wait_for_timeout(4000)


# ---------------------------------------------------------------------- run modes
def do_rank_only(args):
    d = Path(args.rank_only)
    if not d.is_dir():
        die(f"--rank-only wants a directory; {d} is not one")
    files = sorted(p for p in d.glob("*.mp3"))
    if not files:
        die(f"no .mp3 files in {d}")
    log(f"ranking {len(files)} mp3(s) in {d}")
    cands = [{"file": str(p), "song_id": p.stem, "bytes": p.stat().st_size}
             for p in files]
    ranked = rank_candidates(cands, invert=args.invert, window=args.attack_window)
    meta = {"mode": "rank-only", "source_dir": str(d)}
    # optional provenance: what these takes were auditioned FOR
    if args.style:
        meta["style"] = args.style
    if args.exclude_styles:
        meta["exclude_styles"] = args.exclude_styles
    if args.lyrics and Path(args.lyrics).is_file():
        meta["lyrics_file"] = str(Path(args.lyrics).resolve())
    out = write_candidates_json(d, ranked, meta, args.invert, args.attack_window)
    print_ranking(ranked, args.attack_window)
    log(f"wrote {out}")
    return 0


def do_generate(args, lyrics_text):
    from playwright.sync_api import sync_playwright

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n_clicks = 2 if args.double else 1
    want = n_clicks * 2  # Suno renders two variations per Create

    with sync_playwright() as pw:
        att = attach(pw, args.cdp_url)
        if att is None:
            warn(f"no CDP endpoint at {args.cdp_url} — refusing to fall back to a "
                 "fresh Playwright profile (the Suno session lives in real Chrome).")
            print(chrome_recipe(args.cdp_url))
            print(cic_recipe(args, lyrics_text))
            return 2
        browser, ctx = att

        page = open_create_page(ctx, args.base_url)
        page.wait_for_timeout(2500)
        log(f"create page: {page.url}")

        account = assert_paid_seat(page, args.base_url, allow_free=args.allow_free_tier)

        # the seat check navigates to /account; come back to the form.
        sniff = start_sniffer(page)
        page.goto(f"{args.base_url}/create", wait_until="domcontentloaded")
        page.wait_for_timeout(3500)

        if not ensure_advanced_mode(page):
            log("could not find an Advanced/Custom toggle — assuming the form is "
                "already showing both Styles and Lyrics")

        style_el = find_style_box(page)
        if style_el is None:
            die("no style <textarea> found on the create page. Suno probably shipped "
                "a new create UI — re-run with --print-recipe and drive it by hand "
                "while the selectors get fixed.", 5)
        style_el.fill(args.style)          # §2: a REAL textarea, plain fill works
        log(f"    style set ({len(args.style)} chars)")

        if args.exclude_styles:
            ex = find_exclude_box(page)
            if ex is None:
                warn("no 'exclude styles' field found (even behind Advanced Options) "
                     "— continuing WITHOUT it. The style prompt still applies.")
            else:
                ex.fill(args.exclude_styles)
                log(f"    exclude-styles set ({len(args.exclude_styles)} chars)")

        lyr_el = find_lyrics_box(page)
        if lyr_el is None:
            die("no contenteditable lyrics editor found on the create page.", 5)
        typed_ok = type_lexical(page, lyr_el, lyrics_text, settle=args.settle)
        if not typed_ok and not args.force:
            die("lyrics did not verify in the editor. Look at the Chrome tab: if the "
                "text IS there, re-run with --force to proceed anyway. NEVER re-type "
                "blind (§2) — you get the lyrics twice.", 6)

        found = collect_ids(page, sniff, {})
        before = set(found)
        log(f"    {len(before)} pre-existing song id(s) (baseline)")

        for i in range(n_clicks):
            if not click_create(page):
                die("could not click Create.", 7)
            log(f"    Create clicked ({i+1}/{n_clicks})")
            if i + 1 < n_clicks:
                # §15: the form RETAINS its inputs after submit -> a second click
                # buys 2 more candidates for zero extra typing.
                page.wait_for_timeout(args.between_clicks * 1000)

        log(f"waiting for {want} new song id(s) (up to {args.wait_songs}s)…")
        ids = wait_for_new_ids(page, sniff, found, before, want, args.wait_songs)
        if not ids:
            die("no new song ids appeared. Check the Chrome tab for a quota/error "
                "toast.", 8)
        if len(ids) < want:
            warn(f"only {len(ids)}/{want} candidates appeared — proceeding with those.")

        try:
            browser.close()  # detaches CDP; the operator's Chrome stays open
        except Exception:
            pass

    log(f"downloading {len(ids)} mp3(s) from {args.cdn_base} …")
    cands = []
    for n, sid in enumerate(ids, 1):
        dest = out_dir / f"cand{n:02d}_{sid[:8]}.mp3"
        url, size = download_mp3(args.cdn_base, sid, dest, tries=args.dl_tries)
        if size:
            cands.append({"file": str(dest), "song_id": sid, "url": url, "bytes": size,
                          "song_page": f"{args.base_url}/song/{sid}"})
    if not cands:
        die("every download failed — the ids are in the log; retry with --rank-only "
            "after pulling them by hand.", 9)

    ranked = rank_candidates(cands, invert=args.invert, window=args.attack_window)
    meta = {
        "mode": "generate",
        "style": args.style,
        "exclude_styles": args.exclude_styles,
        "lyrics_file": str(Path(args.lyrics).resolve()) if args.lyrics else None,
        "double": bool(args.double),
        "create_clicks": n_clicks,
        "account_plan": account.get("plan"),
        "commercial_eligible": bool(account.get("plan") and any(
            w in (account.get("plan") or "").lower() for w in PAID_WORDS)),
    }
    out = write_candidates_json(out_dir, ranked, meta, args.invert, args.attack_window)
    print_ranking(ranked, args.attack_window)
    log(f"wrote {out}")
    return 0


# ----------------------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser(
        description="Suno-via-Chrome auditions in one command (PRODUCTION-PLAYBOOK §2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="The tool generates, downloads and RANKS. A human picks the winner (§1.2).")
    ap.add_argument("--style", help="Suno 'Styles' prompt — genre descriptors, no artist names")
    ap.add_argument("--lyrics", help="path to a lyrics .txt (keep the [Verse]/[Chorus] tags)")
    ap.add_argument("--exclude-styles", default=None, help="Suno 'Exclude styles' prompt")
    ap.add_argument("--double", action="store_true",
                    help="click Create twice → 4 candidates from one typing session (§15)")
    ap.add_argument("--out-dir", default="songs/candidates/",
                    help="where the mp3s + candidates.json land (default: %(default)s)")
    ap.add_argument("--invert", action="store_true",
                    help="rank SOFTEST attack first — for calm channels (Lulla, Poly)")
    ap.add_argument("--attack-window", type=float, default=2.0,
                    help="seconds of head measured by volumedetect (default: %(default)s)")

    ap.add_argument("--rank-only", metavar="DIR",
                    help="skip the browser: re-rank mp3s already in DIR")
    ap.add_argument("--print-recipe", action="store_true",
                    help="print the claude-in-chrome hand-flown fallback and exit")
    ap.add_argument("--print-chrome-recipe", action="store_true",
                    help="print how to start real Chrome with a debug port, and exit")

    ap.add_argument("--cdp-url", default=DEFAULT_CDP,
                    help="real Chrome's debug endpoint (default: %(default)s)")
    ap.add_argument("--base-url", default=DEFAULT_BASE, help=argparse.SUPPRESS)
    ap.add_argument("--cdn-base", default=DEFAULT_CDN, help=argparse.SUPPRESS)
    ap.add_argument("--allow-free-tier", action="store_true",
                    help="generate even if the seat is not paid (stays NON-COMMERCIAL)")
    ap.add_argument("--allow-artist-names", action="store_true",
                    help="silence the artist-name lint on the style prompt")
    ap.add_argument("--force", action="store_true",
                    help="click Create even if the lyrics could not be verified")
    ap.add_argument("--settle", type=int, default=18,
                    help="seconds to wait out a frozen renderer (default: %(default)s)")
    ap.add_argument("--between-clicks", type=int, default=10,
                    help="seconds between the two --double Create clicks")
    ap.add_argument("--wait-songs", type=int, default=420,
                    help="seconds to wait for song ids to appear (default: %(default)s)")
    ap.add_argument("--dl-tries", type=int, default=14,
                    help="download attempts per mp3 (the 2nd variation 403s ~1 min)")
    args = ap.parse_args()

    if args.print_chrome_recipe:
        print(chrome_recipe(args.cdp_url))
        return 0

    if args.rank_only:
        return do_rank_only(args)

    if not args.style or not args.lyrics:
        ap.error("--style and --lyrics are required (or use --rank-only / "
                 "--print-chrome-recipe)")
    lyr = Path(args.lyrics)
    if not lyr.is_file():
        die(f"lyrics file not found: {lyr}")
    lyrics_text = lyr.read_text().strip()
    if not lyrics_text:
        die(f"lyrics file is empty: {lyr}")

    lint_style(args.style, allow_names=args.allow_artist_names)

    if args.print_recipe:
        print(cic_recipe(args, lyrics_text))
        return 0

    if not shutil.which("ffmpeg"):
        die("ffmpeg not on PATH — the attack ranking needs it")

    return do_generate(args, lyrics_text)


if __name__ == "__main__":
    sys.exit(main())
