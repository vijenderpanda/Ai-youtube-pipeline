#!/usr/bin/env python3
"""rec_web_tour.py — scripted tour recorder for REAL web pages (web-tour template).

Generalizes scripts/record_demo.py's proven capture recipe (viewport tables,
box_norm/punch_from_box geometry, the monotonic timebase rebased by the ffmpeg
trim, the chromium-channel launch fallback) into a page-walk driven by a tour
script JSON, for the web-tour Shorts template. The tape is the REAL page —
this tool never retimes, never alters vendor pixels, and never draws on the
page: selection sweeps and camera punches are MEASURED here (normalized rects,
center+zoom) and rendered later by the Remotion WebTour component as additive
overlays. The manifest is the provenance record.

Tour script JSON:
  { "url": "https://github.com/...", "view": "desktop"|"mobile", "dark": true,
    "steps": [
      {"do":"wait","s":1.2},
      {"do":"scroll","to_selector":"article.markdown-body","smooth":true,"dur":1.6},
      {"do":"scroll","by":600,"smooth":true,"dur":1.0},
      {"do":"focus","selector":"#repo-stars-counter-star","label":"stars","hold":2.0,"zoom":2.2},
      {"do":"select","selector":"article.markdown-body","text":"exact on-page phrase","hold":1.5},
      {"do":"click","selector":"..."} ] }

Output: <out>.mp4 (tape) + <out>.tour.json manifest with events (scroll_start/
scroll_end WITH scrollTop values — record_demo only stamps times; that gap is
fixed here), focus windows (normalized box + punch center/zoom), and selection
rects (per-LINE via Range.getClientRects, viewport-relative normalized, plus
the scroll_top they were measured at — the rects are valid exactly for the
frames where that scroll_top holds).

Usage:
  python3 channels/claude-tricks/rec_web_tour.py --tour tour.json --out tape.mp4
          [--pre-wait 4] [--headed] [--redact] [--staged "note"]
"""
import argparse, json, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FPS = 30

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
DESKTOP_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36")

# Record small, upscale with ffmpeg — never record at output size
# (record_demo.py VIEWS table). Desktop is the GitHub/default lane: 1280x720
# CSS px recorded (Playwright records CSS px regardless of dsf), lanczos to
# 1920x1080. Mobile lane (540x960 → 1080x1920) for mobile-shaped sites; the
# iPhone UA + is_mobile/has_touch combo is what passes claude.ai's bot wall.
VIEWS = {
    "desktop": {
        "viewport": {"width": 1280, "height": 720},
        "user_agent": DESKTOP_UA,
        "device_scale_factor": 2,
        "is_mobile": False, "has_touch": False,
        "scale": "1920:1080",
    },
    "mobile": {
        "viewport": {"width": 540, "height": 960},
        "user_agent": MOBILE_UA,
        "device_scale_factor": 2,
        "is_mobile": True, "has_touch": True,
        "scale": "1080:1920",
    },
}
VIEW = VIEWS["desktop"]["viewport"]  # module global; geometry helpers read it

# style-pass ease ramps mirrored so the recorder GUARANTEES the gaps its own
# manifest needs (record_demo.py:183-184 — one number, both ends).
PUNCH_IN, PUNCH_OUT = 0.55, 0.65
MIN_FOCUS_GAP = PUNCH_IN + PUNCH_OUT + 0.20  # 1.40s between focus windows

SCROLL_TOP_JS = "() => (document.scrollingElement || document.documentElement).scrollTop"

# NOTE: scrolls the DOCUMENT scroller. Sites that scroll an inner div
# (claude.ai) need a container option before this tool can tour them.
# CSS scroll-behavior MUST be forced to auto first: GitHub ships
# `scroll-behavior: smooth`, which turns every scrollTop assignment into an
# async browser glide — the page keeps moving after the loop ends and the
# stamped scroll_top values read mid-glide (measured: end stamp 171 vs true
# 1012). This tool owns the easing; the browser must not double-smooth it.
SMOOTH_SCROLL_JS = """async ({ y, ms }) => {
  document.documentElement.style.scrollBehavior = 'auto';
  if (document.body) document.body.style.scrollBehavior = 'auto';
  const el = document.scrollingElement || document.documentElement;
  const y0 = el.scrollTop;
  const yT = Math.max(0, Math.min(y, el.scrollHeight - el.clientHeight));
  if (ms <= 0) { el.scrollTop = yT; return el.scrollTop; }
  const t0 = performance.now();
  const ease = t => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  await new Promise(done => {
    const step = now => {
      const p = Math.min(1, (now - t0) / ms);
      el.scrollTop = y0 + (yT - y0) * ease(p);
      if (p < 1) requestAnimationFrame(step); else done();
    };
    requestAnimationFrame(step);
  });
  return el.scrollTop;
}"""

# querySelectorAll + first NON-ZERO rect, not querySelector: GitHub keeps a
# hidden duplicate of file-row links whose rect is 0x0 at (0,0) — measured:
# scrolling to it computed target = scrollTop - margin and the beat landed
# mid-README instead of on the file list. Same family as record_demo's
# "hidden duplicate composers" gotcha, ported to the JS side.
TARGET_Y_JS = """({ sel, margin }) => {
  const el = document.scrollingElement || document.documentElement;
  for (const e of document.querySelectorAll(sel)) {
    const r = e.getBoundingClientRect();
    if (r.width > 0 && r.height > 0)
      return el.scrollTop + r.top - margin;
  }
  return null;
}"""

# Find the needle, build a Range, measure per-line client rects. The range is
# NEVER added to the window selection — the tape stays untouched; the sweep is
# drawn by the Remotion component from these measured rects. Descends to the
# deepest element wholly containing the needle, then walks its text nodes by
# char offset so a phrase spanning inline markup still ranges correctly.
SELECT_JS = """({ rootSel, needle }) => {
  const root = (rootSel && document.querySelector(rootSel)) || document.body;
  let el = root;
  if (!(el.textContent || '').includes(needle)) return { err: 'text not under root' };
  for (let descend = true; descend;) {
    descend = false;
    for (const c of el.children)
      if ((c.textContent || '').includes(needle)) { el = c; descend = true; break; }
  }
  const i0 = el.textContent.indexOf(needle);
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  let acc = 0, start = null, end = null;
  while (walker.nextNode()) {
    const n = walker.currentNode, len = n.nodeValue.length;
    if (start === null && acc + len > i0) start = [n, i0 - acc];
    if (acc + len >= i0 + needle.length) { end = [n, i0 + needle.length - acc]; break; }
    acc += len;
  }
  if (!start || !end) return { err: 'offset walk failed' };
  const r = document.createRange();
  r.setStart(start[0], start[1]); r.setEnd(end[0], end[1]);
  const rects = [];
  for (const q of r.getClientRects()) {
    if (q.width < 2 || q.height < 2) continue;   // zero-width artifacts
    const last = rects[rects.length - 1];
    if (last && Math.abs(last[1] - q.top) < 2 && Math.abs(last[3] - q.bottom) < 2) {
      last[0] = Math.min(last[0], q.left); last[2] = Math.max(last[2], q.right);
    } else rects.push([q.left, q.top, q.right, q.bottom]);
  }
  const sc = document.scrollingElement || document.documentElement;
  return { rects, scrollTop: sc.scrollTop };
}"""

# --redact: blur any on-screen email in place (CSS filter, record_demo.py
# recipe). Generic only — logged-in chrome selectors are per-vendor and this
# tool's default lane is anonymous browsing.
REDACT_JS = """() => {
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
}"""


def box_norm(page, selector, last=False):
    """Normalized [x0, y0, x1, y1] of a visible element, or None.

    Punch centers/zoom caps come from MEASURED extents, not guessed constants
    (record_demo.py:189 — a fixed zoom clips edge-running content).
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
    """(center, zoom) keeping `box` fully inside a centred crop at zoom z:
    the crop shows 1/z of each axis, so the widest safe zoom is 1/span — 98%
    of it, never past the requested look, never under the floor."""
    if not box:
        return [0.5, 0.5], floor
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cap = min(1.0 / max(1e-3, x1 - x0), 1.0 / max(1e-3, y1 - y0)) * 0.98
    return [round(cx, 3), round(cy, 3)], round(max(floor, min(want, cap)), 3)


def do_scroll(page, step, mark, events):
    dur = float(step.get("dur", 1.2))
    smooth = step.get("smooth", True)
    if "to_selector" in step:
        # margin = viewport px kept above the target after the scroll
        y = page.evaluate(TARGET_Y_JS, {"sel": step["to_selector"],
                                        "margin": float(step.get("margin", 90))})
        if y is None:
            sys.exit(f"ABORT: scroll target {step['to_selector']!r} not found")
    else:
        y = page.evaluate(SCROLL_TOP_JS) + float(step.get("by", 600))
    top0 = page.evaluate(SCROLL_TOP_JS)
    events.append({"t": mark(), "kind": "scroll_start", "scroll_top": round(top0, 1)})
    top1 = page.evaluate(SMOOTH_SCROLL_JS, {"y": y, "ms": int(dur * 1000) if smooth else 0})
    events.append({"t": mark(), "kind": "scroll_end", "scroll_top": round(top1, 1)})


def do_focus(page, step, mark, focus):
    sel = step["selector"]
    hold = float(step.get("hold", 2.0))
    box = box_norm(page, sel, last=bool(step.get("last")))
    if box is None:
        sys.exit(f"ABORT: focus target {sel!r} not found/visible — fix the "
                 f"selector in the tour script (footage discarded)")
    # Playwright "visible" means rendered, not on-screen: an element scrolled
    # out of the viewport still returns a box (negative/overflowing coords).
    # A focus window pointing off-tape is garbage — abort, don't ship it.
    if box[3] <= 0 or box[1] >= 1 or box[2] <= 0 or box[0] >= 1:
        sys.exit(f"ABORT: focus target {sel!r} is off-screen (box={box}) — "
                 f"add/fix a scroll step so the target is in view first")
    center, zoom = punch_from_box(box, float(step.get("zoom", 1.8)))
    focus.append({"t": mark(), "hold": round(hold, 3),
                  "label": step.get("label", sel[:32]),
                  "box": [round(v, 4) for v in box],
                  "center": center, "zoom": zoom})
    time.sleep(hold)


def do_select(page, step, mark, selections):
    needle = step["text"]
    hold = float(step.get("hold", 1.5))
    res = page.evaluate(SELECT_JS, {"rootSel": step.get("selector"), "needle": needle})
    if not res or res.get("err") or not res.get("rects"):
        why = (res or {}).get("err", "no rects")
        sys.exit(f"ABORT: select {needle!r}: {why} — the phrase must exist "
                 f"VERBATIM on the page (honesty rule: measured, never faked)")
    w, h = VIEW["width"], VIEW["height"]
    rects = [[round(x0 / w, 4), round(y0 / h, 4), round(x1 / w, 4), round(y1 / h, 4)]
             for x0, y0, x1, y1 in res["rects"]]
    if not any(r[3] > 0 and r[1] < 1 for r in rects):
        print(f"!! select {needle!r}: rects fully off-screen at scroll_top="
              f"{res['scrollTop']} — sweep will not be visible", file=sys.stderr)
    selections.append({"t": mark(), "hold": round(hold, 3), "label": needle,
                       "rects": rects, "scroll_top": round(res["scrollTop"], 1)})
    time.sleep(hold)


def do_click(page, step, mark, events):
    sel = step["selector"]
    loc = page.locator(sel).locator("visible=true")
    if not loc.count():
        sys.exit(f"ABORT: click target {sel!r} not found/visible")
    loc.first.click()
    events.append({"t": mark(), "kind": "click", "selector": sel})


def run_tour(tour, out, pre_wait=4.0, headed=False, redact=False, staged=None):
    global VIEW
    view_name = tour.get("view", "desktop")
    cfg = VIEWS[view_name]
    VIEW = cfg["viewport"]
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmpdir = out.parent / f".rec_{out.stem}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    for f in tmpdir.glob("*.webm"):  # purge stale takes; webms are hash-named
        f.unlink()

    events, focus, selections = [], [], []
    with sync_playwright() as p:
        common = dict(
            viewport=VIEW,
            user_agent=cfg["user_agent"],
            device_scale_factor=cfg["device_scale_factor"],
            is_mobile=cfg["is_mobile"], has_touch=cfg["has_touch"],
            record_video_dir=str(tmpdir),
            record_video_size=VIEW,
        )
        if tour.get("dark"):
            common["color_scheme"] = "dark"  # page look; no account setting involved
        # channel-pinned launches have been measured to hang on this machine;
        # fall back to the bundled build (record_demo.py:477-498)
        ctx = None
        for chan in ("chromium", None):
            launch_args = dict(
                headless=not headed, timeout=45000,
                args=["--disable-blink-features=AutomationControlled"],
            )
            if chan:
                launch_args["channel"] = chan
            try:
                browser = p.chromium.launch(**launch_args)
                ctx = browser.new_context(**common)
                if not chan:
                    print("!! channel='chromium' launch failed; using bundled build",
                          file=sys.stderr)
                break
            except Exception as e:
                print(f"!! launch channel={chan or 'bundled'}: "
                      f"{type(e).__name__}: {e}"[:300], file=sys.stderr)
        if ctx is None:
            sys.exit("ABORT: no chromium build would launch (see failures above)")
        t0 = time.monotonic()  # context creation = video start
        mark = lambda: time.monotonic() - t0

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(tour["url"], wait_until="domcontentloaded", timeout=60000)
        time.sleep(pre_wait)  # settle; this footage is trimmed at transcode
        if redact:
            n = page.evaluate(REDACT_JS)
            print(f"redact: {n} email node(s) blurred")

        for step in tour["steps"]:
            do = step.get("do")
            if do == "wait":
                time.sleep(float(step.get("s", 1.0)))
            elif do == "scroll":
                do_scroll(page, step, mark, events)
            elif do == "focus":
                do_focus(page, step, mark, focus)
            elif do == "select":
                do_select(page, step, mark, selections)
            elif do == "click":
                do_click(page, step, mark, events)
            else:
                sys.exit(f"ABORT: unknown step {step!r}")

        video = page.video
        ctx.close()  # finalizes the webm
        raw = Path(video.path()) if video else None

    if raw is None or not raw.exists():
        webms = sorted(tmpdir.glob("*.webm"), key=lambda f: f.stat().st_mtime)
        if not webms:
            sys.exit("ABORT: no webm produced")
        raw = webms[-1]  # newest by mtime; Playwright names webms by hash

    # webm -> mp4 at the view's output size, forced CFR 30 (Playwright webm is
    # variable-fps), trim page-load dead time. Straight transcode — the tape
    # is never retimed.
    trim = max(pre_wait - 1, 0)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw), "-ss", str(trim),
        "-vf", f"scale={cfg['scale']}:flags=lanczos",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", str(out),
    ], check=True, capture_output=True)
    for f in tmpdir.iterdir():
        f.unlink()
    tmpdir.rmdir()

    # manifest times in secs relative to the FINAL trimmed tape
    rel = lambda t: round(max(t - trim, 0.0), 3)
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(out),
    ], capture_output=True, text=True)
    try:
        duration = round(float(probe.stdout.strip()), 3)
    except ValueError:
        duration = None
    for coll in (events, focus, selections):
        for e in coll:
            e["t"] = rel(e["t"])

    # the style pass's ease ramps need clear air between focus windows —
    # guarantee it here, not discover it downstream (record_demo build_punches)
    for a, b in zip(focus, focus[1:]):
        gap = b["t"] - (a["t"] + a["hold"])
        if b["t"] - PUNCH_IN < a["t"] + a["hold"] + PUNCH_OUT:
            print(f"ABORT: focus {a['label']!r} -> {b['label']!r} gap {gap:.2f}s "
                  f"is under the {MIN_FOCUS_GAP:.2f}s the ease ramps need. "
                  f"Add a wait between them in the tour script. Tape + manifest "
                  f"kept for inspection.", file=sys.stderr)
            _write_manifest(tour, cfg, out, duration, events, focus, selections,
                            staged, gap_violation=True)
            sys.exit(2)

    _write_manifest(tour, cfg, out, duration, events, focus, selections, staged)
    print(f"\nTape     {out}  ({duration}s)")
    print(f"Manifest {out.with_suffix('.tour.json')}")
    print(f"Summary  events={len(events)}  focus={len(focus)}  "
          f"selections={len(selections)}")
    for f_ in focus:
        print(f"  focus  t={f_['t']:>6.2f} hold={f_['hold']:.1f} zoom={f_['zoom']:.2f} "
              f"{f_['label']}")
    for s in selections:
        print(f"  select t={s['t']:>6.2f} lines={len(s['rects'])} "
              f"scroll_top={s['scroll_top']} \"{s['label'][:48]}\"")
    return out, duration


def _write_manifest(tour, cfg, out, duration, events, focus, selections,
                    staged=None, gap_violation=False):
    manifest = {
        "tool": "rec_web_tour.py",
        "view": {"w": VIEW["width"], "h": VIEW["height"],
                 "dsf": cfg["device_scale_factor"]},
        "fps": FPS,
        "url": tour["url"],
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dark": bool(tour.get("dark")),
        "duration": duration,
        "events": events,
        "focus": focus,
        # rects are viewport-relative (normalized to the tape frame) and valid
        # for the frames where their scroll_top holds — the component glues
        # them to tape pixels through the same transform as the camera
        "selections": selections,
    }
    if staged:
        manifest["staged"] = True
        manifest["note"] = staged
    if gap_violation:
        manifest["gap_violation"] = True
    out.with_suffix(".tour.json").write_text(json.dumps(manifest, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tour", required=True, help="tour script JSON path")
    ap.add_argument("--out", required=True, help="output tape .mp4 path")
    ap.add_argument("--pre-wait", type=float, default=4.0,
                    help="page settle secs before the tour (trimmed to 1s at transcode)")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--redact", action="store_true",
                    help="blur on-screen emails in place (logged-in chrome)")
    ap.add_argument("--staged", metavar="NOTE",
                    help="label the manifest STAGED (local/staged page, not a live site)")
    args = ap.parse_args()
    tour = json.loads(Path(args.tour).read_text())
    run_tour(tour, args.out, pre_wait=args.pre_wait, headed=args.headed,
             redact=args.redact, staged=args.staged)


if __name__ == "__main__":
    main()
