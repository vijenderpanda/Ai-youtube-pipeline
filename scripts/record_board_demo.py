#!/usr/bin/env python3
"""
record_board_demo.py — film OUR OWN staged-production board (/studio/<id>) as
the hero screen recording for the "AI factory" episode.

Sibling of record_demo.py / record_memory_demo.py: same launch flags, same
540x960 dsf2 dark context, same t0/mark() timeline convention, same
lanczos-2x -> 1080x1920 crf 18 encode, and the same multi-punch sidecar that
scripts/style_punch.py consumes.

Differences that matter:
  - AUTH is injected, never typed: FACTORY_TOKEN from secrets/factory.env goes
    into localStorage via context.add_init_script BEFORE the first navigation
    (webapp/src/api.js reads localStorage['factory_token']). The token never
    appears in a URL and never appears on camera. After load we assert the
    LockScreen is gone and that .bin-tile elements exist - filming a login wall
    is exactly the failure this check exists to prevent.
  - REDACTION IS ARMED BEFORE THE PAGE PAINTS (Ep24 lesson: a post-load sweep
    loses the race). add_init_script installs a MutationObserver at document
    start that blurs home paths, *.supabase.co hosts, JWT-looking strings,
    sk-/xi-/hf_/Bearer tokens, emails and the factory token itself. Our own
    channel names, episode titles and asset keys are OURS and stay sharp.
  - There is no prompt->answer arc; the shot list is settle -> progress label
    -> filmstrip scroll -> click one approved tile -> bin grid, each stamped
    into the sidecar and each spaced far enough apart that the punch windows
    (plus PUNCH_IN 0.55 / PUNCH_OUT 0.65 ramps) never overlap.

Usage:
  python3 scripts/record_board_demo.py --calendar-id <uuid> --out raw_board.mp4
  python3 scripts/record_board_demo.py --calendar-id <uuid> --probe   # geometry only, no film
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
APP = "https://vijender-ai-factory.netlify.app"
VIEW = {"width": 540, "height": 960}

# The board must not be filmed behind the lock screen; these strings are what
# webapp/src/components/LockScreen.jsx renders.
LOCK_MARKERS = re.compile(r"Factory token|Unlock", re.I)

# style_punch.py constants, restated so the recorder can enforce the spacing it
# emits (Ep24: one number, both ends).
PUNCH_IN, PUNCH_OUT = 0.55, 0.65


def read_env(path):
    env = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v.strip().strip('"').strip("'")
    return env


# ---- redaction ------------------------------------------------------------
# Armed at document_start so a node is blurred in the same frame it mounts.
#
# TEXT NODES ONLY, deliberately. An earlier pass also matched attributes and
# blurred every element whose src/href carried the storage host — which is
# every thumbnail, every bin tile and the draft-preview monitor, i.e. the whole
# shot. An `src` is not on camera; rendered text is. What the redactor must
# cover is what a frame can show, so it walks text nodes (plus the counted
# assert below re-walks them at the end of the take).
REDACT_JS = r"""
(secrets) => {
  const PATTERNS = [
    /\/Users\/[A-Za-z0-9._-]+/,           // home paths
    /[a-z0-9-]+\.supabase\.co/i,          // project host
    /eyJ[A-Za-z0-9_-]{10,}\./,            // JWT-looking
    /\b(sk-|xi-|hf_)[A-Za-z0-9_-]{8,}/,   // vendor api keys
    /Bearer\s+[A-Za-z0-9._-]{8,}/i,       // bearer headers
    /[\w.+-]+@[\w-]+\.[\w.]{2,}/,         // email
  ];
  const extra = (secrets || []).filter((s) => s && s.length >= 8);
  const hit = (s) => !!s && (PATTERNS.some((r) => r.test(s)) || extra.some((x) => s.includes(x)));

  window.__redactCount = 0;
  const blur = (el) => {
    if (!el || el.nodeType !== 1 || el.dataset.redacted) return;
    el.dataset.redacted = '1';
    el.style.filter = 'blur(7px)';
    window.__redactCount++;
  };
  const sweep = (root) => {
    if (!root) return;
    if (root.nodeType === 3) { if (hit(root.nodeValue)) blur(root.parentElement); return; }
    if (root.nodeType !== 1) return;
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walk.nextNode()) if (hit(walk.currentNode.nodeValue)) blur(walk.currentNode.parentElement);
  };

  const arm = () => {
    sweep(document.body);
    const obs = new MutationObserver((muts) => {
      for (const m of muts) {
        if (m.type === 'characterData') { sweep(m.target); continue; }
        for (const n of m.addedNodes) sweep(n);
      }
    });
    obs.observe(document.documentElement,
                {childList: true, subtree: true, characterData: true});
    window.__redactObserver = obs;
  };
  if (document.body) arm();
  else document.addEventListener('DOMContentLoaded', arm, {once: true});
}
"""

ASSERT_JS = r"""
(secrets) => {
  const PATTERNS = [
    /\/Users\/[A-Za-z0-9._-]+/,
    /[a-z0-9-]+\.supabase\.co/i,
    /eyJ[A-Za-z0-9_-]{10,}\./,
    /\b(sk-|xi-|hf_)[A-Za-z0-9_-]{8,}/,
    /Bearer\s+[A-Za-z0-9._-]{8,}/i,
    /[\w.+-]+@[\w-]+\.[\w.]{2,}/,
  ];
  const extra = (secrets || []).filter((s) => s && s.length >= 8);
  const hit = (s) => !!s && (PATTERNS.some((r) => r.test(s)) || extra.some((x) => s.includes(x)));
  const guarded = (el) => {
    while (el) {
      if (el.dataset && el.dataset.redacted) return true;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') return true;
      el = el.parentElement;
    }
    return false;
  };
  const exposed = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walk.nextNode()) {
    const n = walk.currentNode;
    if (hit(n.nodeValue) && !guarded(n.parentElement)) exposed.push(n.nodeValue.trim().slice(0, 80));
  }
  return {exposed, blurred: window.__redactCount || 0,
          samples: [...document.querySelectorAll('[data-redacted]')]
                     .map((el) => (el.innerText || '').trim().slice(0, 60)).slice(0, 12)};
}
"""


def assert_clean(page, when, secrets):
    res = page.evaluate(ASSERT_JS, secrets)
    if res["exposed"]:
        sys.exit(f"ABORT: {len(res['exposed'])} unredacted secret-ish node(s) on screen {when}:\n"
                 + "\n".join("  - " + e for e in res["exposed"][:12]))
    print(f"redaction {when}: {res['blurred']} blurred, 0 exposed  {res['samples']}")
    return res["blurred"]


def assert_unlocked(page, when):
    """The whole point of the auth injection: never film a login wall."""
    body = page.inner_text("body", timeout=10000)[:6000]
    if LOCK_MARKERS.search(body):
        sys.exit(f"ABORT: LockScreen visible {when} — the injected factory_token "
                 f"did not take. Refusing to film a login wall.\nOn screen: "
                 + " · ".join(l.strip() for l in body.splitlines() if l.strip())[:400])


def board_geometry(page):
    """Real ink extents + status counts, measured — never assumed."""
    return page.evaluate(r"""() => {
      const box = (sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return {x: r.x, y: r.y, w: r.width, h: r.height,
                top: r.top + scrollY, bottom: r.bottom + scrollY};
      };
      const cnt = (sel) => document.querySelectorAll(sel).length;
      return {
        scrollH: document.documentElement.scrollHeight,
        vh: innerHeight, vw: innerWidth, scrollY,
        title: (document.querySelector('.page-head h1') || {}).innerText || null,
        chanTag: (document.querySelector('.chan-tag') || {}).innerText || null,
        progressLabel: (document.querySelector('.progress-label') || {}).innerText || null,
        queueHint: (document.querySelector('.queue-hint') || {}).innerText || null,
        binCount: (document.querySelector('.asset-section-count') || {}).innerText || null,
        boxes: {
          head: box('.page-head'), bar: box('.board-bar'),
          progress: box('.progress'), label: box('.progress-label'),
          filmstrip: box('.filmstrip'), stage: box('.stage-row'),
          binSection: box('.bin-section'), bin: box('.bin'),
          docs: box('.docs-rail'),
        },
        counts: {
          chips: cnt('.fs-chip'), chipsApproved: cnt('.fs-chip.fs-approved'),
          tiles: cnt('.bin-tile'), tilesApproved: cnt('.bin-tile.fs-approved'),
          tilesGenerating: cnt('.bin-tile.fs-generating'),
          tilesQueued: cnt('.bin-tile.fs-queued'),
          docs: cnt('.doc-row'),
        },
        strip: (() => {
          const s = document.querySelector('.filmstrip');
          if (!s) return null;
          return {scrollW: s.scrollWidth, clientW: s.clientWidth, scrollLeft: s.scrollLeft};
        })(),
        approvedTiles: [...document.querySelectorAll('.bin-tile.fs-approved')].map((el, i) => ({
          i,
          name: (el.querySelector('.bin-name') || {}).innerText || '',
          num: (el.querySelector('.bin-num') || {}).innerText || '',
          // a real still (vs a kind glyph) means the stage will render
          // .stage-img / a video poster rather than an audio player
          hasStill: !!el.querySelector('.bin-thumb img, img.bin-thumb'),
        })),
      };
    }""")


def norm_center(b, page_scroll_y, vw, vh):
    """Viewport-normalized center of a box, given the scroll position it is
    filmed at. style_punch centers are 0..1 of the FRAME."""
    cx = (b["x"] + b["w"] / 2) / vw
    cy = (b["top"] - page_scroll_y + b["h"] / 2) / vh
    return [round(min(max(cx, 0.0), 1.0), 4), round(min(max(cy, 0.0), 1.0), 4)]


def safe_zoom(b, vw, vh, pad=16, cap=2.4):
    """Largest zoom that keeps the box (plus pad) inside the frame.

    A zoom that crops a label is the recurring bug, so this is measured from
    the real rect rather than picked. `pad` is the guaranteed margin in
    viewport px (doubled in the 1080-wide output), which is also what the
    edge sweep on the styled file re-checks.
    """
    zx = vw / max(1.0, b["w"] + 2 * pad)
    zy = vh / max(1.0, b["h"] + 2 * pad)
    return round(max(1.0, min(zx, zy, cap)), 3)


def run(calendar_id, out, probe_only=False, headed=False, settle=4.0):
    env = read_env(ROOT / "secrets" / "factory.env")
    token = env.get("FACTORY_TOKEN")
    if not token:
        sys.exit("ABORT: FACTORY_TOKEN missing from secrets/factory.env")
    secrets = [token, env.get("SUPABASE_SERVICE_KEY") or "", env.get("SUPABASE_URL") or ""]

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmpdir = out.parent / f".rec_{out.stem}"
    tmpdir.mkdir(parents=True, exist_ok=True)

    url = f"{APP}/studio/{calendar_id}"
    launch_args = dict(
        headless=not headed,
        channel="chromium",
        args=["--disable-blink-features=AutomationControlled"],
    )
    tl = {"scrolls": [], "marks": {}}
    geo_before = geo_after = None

    with sync_playwright() as p:
        common = dict(
            viewport=VIEW,
            device_scale_factor=2,
            color_scheme="dark",  # the app is dark by default; this just pins it
        )
        if not probe_only:
            common.update(record_video_dir=str(tmpdir), record_video_size=VIEW)
        browser = p.chromium.launch(**launch_args)
        ctx = browser.new_context(**common)

        # AUTH + REDACTION, both before the first navigation and before paint.
        # NOTE: add_init_script evaluates the SOURCE — a bare `() => {...}` is
        # an expression nothing ever calls. Both scripts must be IIFEs.
        ctx.add_init_script(f"(() => {{ try {{ localStorage.setItem('factory_token', {json.dumps(token)}); }} catch (e) {{}} }})()")
        ctx.add_init_script(f"({REDACT_JS})({json.dumps(secrets)})")

        t0 = time.monotonic()
        mark = lambda: round(time.monotonic() - t0, 3)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Board data arrives over the API; wait for real tiles, not a spinner.
        try:
            page.wait_for_selector(".bin-tile", timeout=45000)
        except Exception:
            assert_unlocked(page, "while waiting for .bin-tile")
            sys.exit("ABORT: zero .bin-tile elements after 45s — nothing to film.")
        page.wait_for_selector(".progress-label", timeout=15000)
        time.sleep(settle)

        assert_unlocked(page, "after load")
        blurred = assert_clean(page, "before filming", secrets)
        geo_before = board_geometry(page)
        if geo_before["counts"]["tiles"] == 0:
            sys.exit("ABORT: zero .bin-tile elements — nothing to film.")

        if probe_only:
            # POSITIVE CONTROL. Our own board renders no secrets, so "0 blurred,
            # 0 exposed" is indistinguishable from a guard that silently never
            # armed. Mount decoys and require the observer to catch each one in
            # the same frame (this runs in --probe only; the filmed take is
            # never touched).
            # MutationObserver callbacks are MICROTASKS: they run at the end of
            # the current task, before the next paint. The check therefore has
            # to yield once — reading dataset.redacted synchronously in the
            # same task reports "missed" for a guard that is working fine.
            selftest = page.evaluate(r"""async () => {
              const decoys = {
                home: '/Users/someone/Ai-youtube-pipeline/secrets',
                host: 'abcdefghij.supabase.co',
                jwt: 'eyJhbGciOiJIUzI1NiJ9.payloadpayload.sig',
                sk: 'sk-abcdefgh12345678',
                xi: 'xi-abcdefgh12345678',
                hf: 'hf_abcdefgh12345678',
                bearer: 'Bearer abcdefgh12345678',
                email: 'someone@example.com',
              };
              const box = document.createElement('div');
              document.body.appendChild(box);
              const out = {};
              for (const [k, v] of Object.entries(decoys)) {
                const d = document.createElement('span');
                d.textContent = v;
                box.appendChild(d);
                out[k] = d;
              }
              await new Promise((r) => queueMicrotask(r));  // observer flush, still pre-paint
              const res = {};
              for (const [k, el] of Object.entries(out)) res[k] = el.dataset.redacted === '1';
              const painted = await new Promise((r) => requestAnimationFrame(() => r(true)));
              res.__prePaint = painted;
              box.remove();
              return res;
            }""")
            missed = [k for k, ok in selftest.items() if not ok and not k.startswith("__")]
            print("redaction self-test:", json.dumps(selftest))
            if missed:
                sys.exit(f"ABORT: redaction observer missed decoys {missed} — the guard is not armed.")
            ctx.close()
            browser.close()
            print(json.dumps({"geo": geo_before, "blurred": blurred}, indent=2))
            return None, {"geo": geo_before, "blurred": blurred, "selftest": selftest}

        vw, vh = geo_before["vw"], geo_before["vh"]
        boxes = geo_before["boxes"]

        # --- SHOT 1: settle on the header (title + channel chip) -------------
        tl["marks"]["header_hold_start"] = mark()
        time.sleep(1.0)
        tl["marks"]["header_hold_end"] = mark()

        # --- SHOT 2: the progress bar + its label ----------------------------
        # Already in frame at scrollY 0 on this layout; hold it as its own beat.
        tl["marks"]["progress_hold_start"] = mark()
        time.sleep(2.0)
        tl["marks"]["progress_hold_end"] = mark()
        tl["progress_center"] = norm_center(boxes["progress"], 0, vw, vh)
        tl["progress_zoom"] = safe_zoom(boxes["bar"], vw, vh)

        # --- SHOT 3: slow scroll to the filmstrip, let step chips pass -------
        strip_y = max(0, int(boxes["filmstrip"]["top"] - vh * 0.30))
        tl["marks"]["scroll_to_strip"] = mark()
        page.evaluate("(y) => scrollTo({top: y, behavior: 'smooth'})", strip_y)
        time.sleep(1.4)
        tl["scrolls"].append(mark())

        strip = geo_before["strip"]
        chip_hold = None
        if strip and strip["scrollW"] > strip["clientW"] + 20:
            # Horizontal strip: walk 4-6 numbered chips past the frame slowly.
            span = strip["scrollW"] - strip["clientW"]
            steps = 6
            tl["marks"]["strip_pan_start"] = mark()
            for i in range(1, steps + 1):
                page.evaluate("([x]) => document.querySelector('.filmstrip').scrollTo({left: x, behavior: 'smooth'})",
                              [round(span * i / steps)])
                time.sleep(0.58)
            tl["marks"]["strip_pan_end"] = mark()
        else:
            tl["marks"]["strip_pan_start"] = mark()
            time.sleep(2.4)
            tl["marks"]["strip_pan_end"] = mark()

        # Land on a GREEN chip and hold it — the money frame. The punch is
        # anchored on the chip's OWN rect (not the whole strip) so the beat
        # actually lands; the zoom is capped from that rect so its number and
        # title stay inside the frame.
        strip_box = page.locator(".filmstrip").bounding_box()
        chips = page.locator(".fs-chip.fs-approved")
        chip_box = None
        if chips.count():
            # a green chip that is fully inside the strip's visible window
            for i in range(chips.count()):
                b = chips.nth(i).bounding_box()
                if b and b["x"] >= strip_box["x"] and b["x"] + b["width"] <= strip_box["x"] + strip_box["width"]:
                    chip_box = b
                    break
            if chip_box is None:
                chips.first.scroll_into_view_if_needed()
                time.sleep(0.5)
                chip_box = chips.first.bounding_box()
        time.sleep(0.5)  # let the strip come to rest before the punch ramps in
        tl["marks"]["chip_hold_start"] = mark()
        time.sleep(1.8)
        tl["marks"]["chip_hold_end"] = mark()
        if chip_box:
            # widen to a 3-chip window so the punch reads as "the strip",
            # then clamp it to the strip's own visible box
            cw = chip_box["width"] * 3
            cx0 = max(strip_box["x"], chip_box["x"] + chip_box["width"] / 2 - cw / 2)
            cx1 = min(strip_box["x"] + strip_box["width"], cx0 + cw)
            win = {"x": cx0, "w": cx1 - cx0, "top": strip_box["y"], "h": strip_box["height"]}
            chip_hold = {
                "center": [round((win["x"] + win["w"] / 2) / vw, 4),
                           round((win["top"] + win["h"] / 2) / vh, 4)],
                "zoom": safe_zoom(win, vw, vh, pad=14, cap=1.6),
                "chip_box": chip_box, "window": win,
            }
        tl["chip_hold"] = chip_hold

        # --- SHOT 4: click ONE approved tile so the stage loads a real asset --
        # Never press play; tool audio stays muted and the poster/cover is the
        # frame we want anyway.
        # Choose the tile BEFORE filming: an approved tile that carries a real
        # still, preferring the cover/poster, so the stage lands on an image
        # rather than an audio player. (First take clicked the VO master and
        # the hero shot was a wav player.)
        cand = page.locator(".bin-tile.fs-approved")
        stills = [t for t in geo_before["approvedTiles"] if t["hasStill"]]
        # ranked, most photogenic first: the episode's own cover beats a
        # frozen-chat still, which beats "whatever has a thumbnail"
        pick = None
        for pat in (r"cover|poster", r"thumbnail", r"frame", r"."):
            pick = next((t for t in stills if re.search(pat, t["name"], re.I)), None)
            if pick:
                break
        if pick is None:
            sys.exit("ABORT: no approved tile carries a real still — nothing to put on the stage.")
        el = cand.nth(pick["i"])
        clicked = pick["name"]
        el.scroll_into_view_if_needed()
        time.sleep(0.4)
        tl["marks"]["tile_click"] = mark()
        el.click()
        time.sleep(0.9)
        # bring the stage back into frame (pickAndShow scrolls, but be explicit)
        page.evaluate("() => { const s = document.querySelector('.stage-row'); if (s) s.scrollIntoView({behavior: 'smooth', block: 'center'}); }")
        time.sleep(1.0)
        tl["marks"]["stage_hold_start"] = mark()
        time.sleep(1.5)
        tl["marks"]["stage_hold_end"] = mark()
        tl["clicked_tile"] = clicked
        tl["stage_media"] = page.evaluate(
            "() => ({img: !!document.querySelector('.stage-img'), video: !!document.querySelector('.stage-video'),"
            " audio: !!document.querySelector('.stage-audio'), file: (document.querySelector('.stage-file')||{}).innerText || null})")

        # --- SHOT 5: the bin grid of green tiles — the hook still / thumbnail --
        tl["marks"]["scroll_to_bin"] = mark()
        page.evaluate("() => { const b = document.querySelector('.bin'); if (b) b.scrollIntoView({behavior: 'smooth', block: 'center'}); }")
        time.sleep(1.6)
        tl["scrolls"].append(mark())
        gbin = board_geometry(page)
        tl["marks"]["bin_hold_start"] = mark()
        time.sleep(2.5)
        tl["marks"]["bin_hold_end"] = mark()
        bb = gbin["boxes"]["bin"]
        tl["bin_center"] = [round((bb["x"] + bb["w"] / 2) / vw, 4),
                            round(min(max((bb["top"] - gbin["scrollY"] + bb["h"] / 2) / vh, 0.0), 1.0), 4)]
        tl["bin_zoom"] = safe_zoom({"x": bb["x"], "w": bb["w"],
                                    "top": bb["top"] - gbin["scrollY"], "h": bb["h"]}, vw, vh)
        tl["bin_box_viewport"] = {"x": bb["x"], "y": bb["top"] - gbin["scrollY"],
                                  "w": bb["w"], "h": bb["h"]}
        time.sleep(0.35)

        blurred2 = assert_clean(page, "at end of take", secrets)
        assert_unlocked(page, "at end of take")
        geo_after = gbin
        tl["redactions"] = max(blurred, blurred2)
        tl["raw_end"] = mark()

        video = page.video
        ctx.close()
        browser.close()
        raw = Path(video.path())

    # webm -> 1080x1920 mp4 (lanczos 2x), trimming the page-load dead time
    trim = round(tl["marks"]["header_hold_start"] - 0.4, 3)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw), "-ss", str(max(trim, 0)),
        "-vf", "scale=1080:1920:flags=lanczos",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30", "-an", str(out),
    ], check=True, capture_output=True)
    for f in tmpdir.iterdir():
        f.unlink()
    tmpdir.rmdir()

    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
        capture_output=True, text=True).stdout.strip())

    rel = lambda t: round(max(t - max(trim, 0), 0.0), 3)
    meta = {
        "url": url,
        "duration": round(dur, 3),
        "marks": {k: rel(v) for k, v in tl["marks"].items()},
        "scrolls": [rel(t) for t in tl["scrolls"]],
        "redactions": tl["redactions"],
        "clicked_tile": tl.get("clicked_tile"),
        "stage_media": tl.get("stage_media"),
        "geometry": {
            "progress_center": tl.get("progress_center"), "progress_zoom": tl.get("progress_zoom"),
            "chip_hold": tl.get("chip_hold"),
            "bin_center": tl.get("bin_center"), "bin_zoom": tl.get("bin_zoom"),
            "bin_box_viewport": tl.get("bin_box_viewport"),
        },
        "observed": {
            "title": geo_before["title"], "channel_chip": geo_before["chanTag"],
            "progress_label": geo_before["progressLabel"],
            "queue_hint": geo_before["queueHint"],
            "bin_count_label": geo_before["binCount"],
            "counts_before": geo_before["counts"],
            "counts_after": (geo_after or {}).get("counts"),
            "approved_tiles": [t["name"] for t in geo_before["approvedTiles"]],
        },
    }
    meta_path = out.with_suffix(".raw.json")
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"Raw {out}  ({meta['duration']}s)")
    print(f"Meta {meta_path}")
    return out, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calendar-id", required=True)
    ap.add_argument("--out", default="renders_out/raw_board.mp4")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--settle", type=float, default=4.0)
    a = ap.parse_args()
    run(a.calendar_id, a.out, probe_only=a.probe, headed=a.headed, settle=a.settle)


if __name__ == "__main__":
    main()
