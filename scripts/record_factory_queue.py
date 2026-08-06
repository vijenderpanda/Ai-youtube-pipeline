#!/usr/bin/env python3
"""record_factory_queue.py — film OUR OWN control room while the factory runs.

Four real moments on https://vijender-ai-factory.netlify.app, in one unbroken
take, with no DOM staging of any kind:

  1. brief_open      /calendar → the episode's item drawer, human-written brief
  2. studio_list     /studio   → the episode card, N fragments + status counts
  3. generating_pulse /studio/:id → magenta `generating` tiles beside the green
                     approved ones + the queue-hint chip
  4. log_stream      /jobs     → a RUNNING job's drawer, log appending live

Honesty rules baked in:
  - the take is one continuous recording; beats are separated by real
    navigation time, never by a cut;
  - nothing about status is written, clicked or styled — if no asset flips
    state inside the window, the sidecar says so (`status_flip: null`);
  - the only DOM we touch is redaction (blur), and secrets are additionally
    masked in the API response body BEFORE React can paint them, because the
    job log is a single React-owned text node: span-wrapping matches inside it
    would detach that node and freeze the very live-append we came to film.

Auth: the factory token is injected into localStorage by an init script, so it
is never typed on camera and never appears in a URL.

Usage:
  python3 scripts/record_factory_queue.py \
      --calendar-id dcbd8c31-... -o renders_out/staged/.../demo_queue_live.mp4
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://vijender-ai-factory.netlify.app"
API = "https://xfqyovimnqdghiekicqr.supabase.co/functions/v1/factory-api"
ANON = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6In"
    "hmcXlvdmltbnFkZ2hpZWtpY3FyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExMTIyMzks"
    "ImV4cCI6MjA5NjY4ODIzOX0.CA_znXaUlgmChBLFSE_eRZ4X-xg2WhwIiZmxwXrZRlM"
)

VIEW = {"width": 540, "height": 960}
PRE_WAIT = 4.0          # page settle, trimmed off the final cut
MIN_GAP = 2.5           # seconds between the END of one beat and the START of
                        # the next — style_punch's ease ramps are 0.55 + 0.65,
                        # so this keeps every window provably non-overlapping
HOLDS = {               # on-screen hold per beat (seconds)
    "brief_open": 2.5,
    "studio_list": 2.5,
    "generating_pulse": 3.5,
    "log_stream": 8.0,
}
PUNCH_IN, PUNCH_OUT = 0.55, 0.65   # must match scripts/style_punch.py
Z_CAP = 1.30


# --------------------------------------------------------------------------
# factory API (used only to CHOOSE what to film and to observe truth, never to
# change anything)
# --------------------------------------------------------------------------
def factory_token():
    env = dict(
        line.split("=", 1)
        for line in (ROOT / "secrets/factory.env").read_text().strip().splitlines()
        if "=" in line and not line.startswith("#")
    )
    tok = env.get("FACTORY_TOKEN", "").strip()
    if not tok:
        sys.exit("ABORT: no FACTORY_TOKEN in secrets/factory.env")
    return tok


def api_get(query, token):
    req = urllib.request.Request(
        API + query,
        headers={"Authorization": f"Bearer {ANON}", "x-factory-token": token},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def asset_statuses(calendar_id, token):
    d = api_get(f"?r=episode_assets&calendar_id={calendar_id}", token)
    return {f"{a['asset_key']}v{a['version']}": a["status"] for a in d["assets"]}


def log_lengths(token, exclude_id):
    """(running jobs, log length per job) — the self-job excluded.

    The self-job can never be the subject: while this script sits in its
    capture hold its own worker emits nothing, so its log would be frozen on
    camera. A sibling fragment job is the one genuinely streaming.
    """
    running = [j for j in api_get("?r=jobs", token)["jobs"]
               if j["status"] == "running" and j["id"] != exclude_id]
    lengths = {}
    for j in running:
        logs = api_get(f"?r=job&id={j['id']}", token)["job"].get("logs") or ""
        lengths[j["id"]] = len("\n".join(logs) if isinstance(logs, list) else logs)
    return running, lengths


def pick_liveliest_job(running, base, now):
    """Whichever sibling job has written the most since the take started.

    Growth is measured over the ~45s between the pre-flight snapshot and the
    moment of choosing, not over a 2s probe: a claude run alternates streaming
    bursts with long silent tool executions, so a short probe mostly measures
    which phase the job happens to be in. A job that appeared mid-take has no
    baseline and counts its whole log as growth — it is, by definition, live.
    """
    if not running:
        return None, {}
    growth = {j["id"]: now[j["id"]] - base.get(j["id"], 0) for j in running}
    best = max(running, key=lambda j: growth[j["id"]])
    return best, growth


# --------------------------------------------------------------------------
# redaction
# --------------------------------------------------------------------------
# Every pattern below must never reach a pixel. Each is applied twice: once to
# the API response body (so React never receives it) and once as a DOM sweep +
# standing MutationObserver blur (so anything not fetch-borne is still covered).
INIT_JS = r"""
(() => {
  const TOKEN = %TOKEN%;
  try { localStorage.setItem('factory_token', TOKEN); } catch (e) {}

  const B = '█';
  const RULES = [
    [new RegExp(TOKEN.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), B.repeat(8)],
    [/eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}/g, 'eyJ' + B.repeat(7)],
    [/Bearer\s+[A-Za-z0-9._-]{16,}/g, 'Bearer ' + B.repeat(7)],
    [/\bsk-[A-Za-z0-9_-]{12,}/g, 'sk-' + B.repeat(7)],
    [/\bxi-[A-Za-z0-9_-]{12,}/g, 'xi-' + B.repeat(7)],
    [/\bhf_[A-Za-z0-9]{12,}/g, 'hf_' + B.repeat(7)],
    [/[a-z0-9]{12,}\.supabase\.co/g, B.repeat(8) + '.supabase.co'],
    [/\/Users\/[A-Za-z0-9._-]+/g, '/Users/' + B.repeat(5)],
    [/[\w.+-]+@[\w-]+\.[\w.]+/g, B.repeat(6) + '@' + B.repeat(4)],
  ];
  window.__maskHits = 0;
  const mask = (s) => {
    if (typeof s !== 'string' || !s) return s;
    let out = s;
    for (const [rx, rep] of RULES) {
      out = out.replace(rx, () => { window.__maskHits++; return rep; });
    }
    return out;
  };
  window.__mask = mask;

  // 1) transport-level: mask the response BODY before the app parses it. The
  //    job log is one React-owned text node; rewriting it in the DOM would
  //    detach the node React keeps updating and the live append would stop.
  const realFetch = window.fetch;
  window.fetch = async function (input, init) {
    const res = await realFetch.apply(this, arguments);
    let url = '';
    try { url = typeof input === 'string' ? input : (input && input.url) || ''; } catch (e) {}
    if (!/factory-api/.test(url)) return res;
    const body = await res.text();
    return new Response(mask(body), {
      status: res.status, statusText: res.statusText, headers: res.headers,
    });
  };

  // 2) DOM-level safety net for anything not fetch-borne. Whole-element blur,
  //    skipping the live log/prompt boxes (already masked at the transport
  //    layer) so their text nodes are never restructured.
  const SKIP = 'pre.logbox, pre.prompt-box';
  const DOM_RX = [
    /\/Users\/[A-Za-z0-9._-]+/,
    /[a-z0-9]{12,}\.supabase\.co/,
    /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}/,
    /\bsk-[A-Za-z0-9_-]{12,}/, /\bxi-[A-Za-z0-9_-]{12,}/, /\bhf_[A-Za-z0-9]{12,}/,
    /Bearer\s+[A-Za-z0-9._-]{16,}/, /[\w.+-]+@[\w-]+\.[\w.]+/,
  ];
  window.__blurHits = 0;
  const sweep = () => {
    if (!document.body) return;
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const hits = [];
    while (walk.nextNode()) {
      const v = walk.currentNode.nodeValue;
      if (v && DOM_RX.some((rx) => rx.test(v))) hits.push(walk.currentNode);
    }
    for (const t of hits) {
      let el = t.parentElement;
      if (!el || (el.closest && el.closest(SKIP))) continue;
      if (el.dataset.redacted) continue;
      el.dataset.redacted = '1';
      el.style.filter = 'blur(7px)';
      window.__blurHits++;
    }
  };
  window.__sweep = sweep;
  const arm = () => {
    sweep();
    new MutationObserver(sweep).observe(document.documentElement, {
      childList: true, subtree: true, characterData: true,
    });
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arm, { once: true });
  } else { arm(); }
})();
"""

EXPOSED_JS = r"""
() => {
  const RX = [
    /\/Users\/[A-Za-z0-9._-]+/,
    /[a-z0-9]{12,}\.supabase\.co/,
    /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}/,
    /\bsk-[A-Za-z0-9_-]{12,}/, /\bxi-[A-Za-z0-9_-]{12,}/, /\bhf_[A-Za-z0-9]{12,}/,
    /Bearer\s+[A-Za-z0-9._-]{16,}/, /[\w.+-]+@[\w-]+\.[\w.]+/,
  ];
  const out = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walk.nextNode()) {
    const n = walk.currentNode, v = n.nodeValue || '';
    const m = RX.map((rx) => v.match(rx)).find(Boolean);
    if (!m) continue;
    let el = n.parentElement, safe = false;
    while (el) {
      if (el.dataset && el.dataset.redacted) { safe = true; break; }
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none') { safe = true; break; }
      el = el.parentElement;
    }
    if (!safe) out.push(m[0].slice(0, 40));
  }
  return out;
}
"""

# every visible text-bearing element, viewport-clipped, normalised 0..1
RECTS_JS = r"""
() => {
  const W = innerWidth, H = innerHeight, out = [], seen = new Set();
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walk.nextNode()) {
    const n = walk.currentNode;
    if (!n.nodeValue || !n.nodeValue.trim()) continue;
    const el = n.parentElement;
    if (!el || seen.has(el)) continue;
    seen.add(el);
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue;
    const r = el.getBoundingClientRect();
    const x0 = Math.max(r.left, 0), y0 = Math.max(r.top, 0);
    const x1 = Math.min(r.right, W), y1 = Math.min(r.bottom, H);
    if (x1 - x0 < 3 || y1 - y0 < 3) continue;
    out.push([x0 / W, y0 / H, x1 / W, y1 / H]);
  }
  return out;
}
"""


def rects_of(page, selectors):
    """Viewport-clipped normalised union inputs for the given selectors."""
    return page.evaluate(
        """(sels) => {
      const W = innerWidth, H = innerHeight, out = [];
      for (const s of sels) {
        for (const el of document.querySelectorAll(s)) {
          const r = el.getBoundingClientRect();
          if (r.width < 3 || r.height < 3) continue;
          const x0 = Math.max(r.left, 0), y0 = Math.max(r.top, 0);
          const x1 = Math.min(r.right, W), y1 = Math.min(r.bottom, H);
          if (x1 - x0 < 3 || y1 - y0 < 3) continue;
          out.push([x0 / W, y0 / H, x1 / W, y1 / H]);
        }
      }
      return out;
    }""",
        selectors,
    )


# --------------------------------------------------------------------------
# framing: pick each punch's zoom from measured rects, not from taste
# --------------------------------------------------------------------------
def union(rects):
    if not rects:
        return None
    return [min(r[0] for r in rects), min(r[1] for r in rects),
            max(r[2] for r in rects), max(r[3] for r in rects)]


def crop_box(z, cx, cy):
    w, h = 1.0 / z, 1.0 / z
    x0 = min(max(cx - w / 2, 0.0), 1.0 - w)
    y0 = min(max(cy - h / 2, 0.0), 1.0 - h)
    return [x0, y0, x0 + w, y0 + h]


def contains(box, r, eps=1e-4):
    return (r[0] >= box[0] - eps and r[1] >= box[1] - eps
            and r[2] <= box[2] + eps and r[3] <= box[3] + eps)


def sliced(box, r, eps=1e-4):
    """Element center is inside the crop but part of the element is not.

    "No label cropped" reads as: nothing the viewer is reading is cut in half.
    Elements whose center falls outside the crop are simply out of shot.
    """
    ccx, ccy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    inside = box[0] <= ccx <= box[2] and box[1] <= ccy <= box[3]
    return inside and not contains(box, r, eps)


def in_focus(keep, r, pad=0.02):
    """Text that overlaps the region this beat is showing.

    Any punch-in necessarily pushes surrounding page chrome out of frame — that
    is framing, not cropping. The rule that has to hold is about labels inside
    the region on show, so the no-slice test is scoped to those.
    """
    return not (r[2] < keep[0] - pad or r[0] > keep[2] + pad
                or r[3] < keep[1] - pad or r[1] > keep[3] + pad)


def solve_zoom(keep, texts):
    """Largest zoom (<= Z_CAP) that keeps `keep` whole and slices no in-focus label."""
    if not keep:
        return 1.0, 0.5, 0.5, []
    focus = [r for r in texts if in_focus(keep, r)]
    kw, kh = keep[2] - keep[0], keep[3] - keep[1]
    cx, cy = (keep[0] + keep[2]) / 2, (keep[1] + keep[3]) / 2
    z_fit = min(1.0 / max(kw, 1e-6), 1.0 / max(kh, 1e-6)) * 0.985
    z = min(Z_CAP, z_fit)
    while z > 1.02:
        box = crop_box(z, cx, cy)
        if contains(box, keep) and not any(sliced(box, r) for r in focus):
            return round(z, 4), round(cx, 4), round(cy, 4), focus
        z -= 0.01
    return 1.0, round(cx, 4), round(cy, 4), focus


def sweep_margins(punches, duration, fps_list=(2, 5)):
    """Re-check containment across the WHOLE clip at 2 and 5 fps.

    Not just inside the holds: the ease ramps move both zoom and center, and a
    ramp that clips a must-keep rect is exactly as bad as a hold that does.
    """
    report = []
    for fps in fps_list:
        n = int(duration * fps) + 1
        for i in range(n):
            t = i / fps
            z, cx, cy = camera_at(punches, t)
            if z <= 1.0005:
                continue
            box = crop_box(z, cx, cy)
            p = owner(punches, t)
            if p is None:
                report.append((fps, round(t, 3), "zoom>1 outside any punch"))
                continue
            keep = p["keep"]
            if keep and not contains(box, keep, eps=2e-3):
                report.append((fps, round(t, 3), f"{p['label']}: must-keep clipped"))
            if p["t0"] - 1e-6 <= t <= p["t1"] + 1e-6:
                bad = [r for r in p["focus"] if sliced(box, r, eps=2e-3)]
                if bad:
                    report.append((fps, round(t, 3), f"{p['label']}: {len(bad)} label(s) sliced"))
    return report


def smoothstep(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3.0 - 2.0 * p)


def owner(punches, t):
    for p in punches:
        if p["t0"] - PUNCH_IN <= t <= p["t1"] + PUNCH_OUT:
            return p
    return None


def camera_at(punches, t):
    """Mirror of style_punch.MultiPunchCam.at() so the sweep checks the real path."""
    for p in punches:
        a, b = p["t0"] - PUNCH_IN, p["t1"] + PUNCH_OUT
        if t < a or t > b:
            continue
        if t < p["t0"]:
            f = smoothstep((t - a) / max(1e-6, p["t0"] - a))
        elif t <= p["t1"]:
            f = 1.0
        else:
            f = 1.0 - smoothstep((t - p["t1"]) / max(1e-6, b - p["t1"]))
        z = 1.0 + (p["zoom"] - 1.0) * f
        return z, 0.5 + (p["center"][0] - 0.5) * f, 0.5 + (p["center"][1] - 0.5) * f
    return 1.0, 0.5, 0.5


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calendar-id", required=True)
    ap.add_argument("--self-job", default="", help="job id to exclude as log subject")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    token = factory_token()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmpdir = out.parent / f".rec_{out.stem}"
    tmpdir.mkdir(parents=True, exist_ok=True)

    statuses_before = asset_statuses(args.calendar_id, token)
    # fail fast, before a single frame is recorded, if there is nothing live
    run0, len0 = log_lengths(token, args.self_job)
    if not run0:
        sys.exit("ABORT: no OTHER running job to film — a frozen log is not the beat.")
    print(f"pre-flight: {len(run0)} sibling job(s) running")

    notes = {}
    punches = []
    tl = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headed,
            channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            viewport=VIEW,
            device_scale_factor=2,
            color_scheme="dark",
            record_video_dir=str(tmpdir),
            record_video_size=VIEW,
        )
        ctx.add_init_script(INIT_JS.replace("%TOKEN%", json.dumps(token)))
        t0 = time.monotonic()
        mark = lambda: time.monotonic() - t0
        page = ctx.new_page()

        def beat(label, keep_sels, hold, extra=None):
            """Hold a moment on camera and measure its framing from the DOM.

            Measuring happens BEFORE the gap wait so the DOM probing does not
            inflate the gap: windows land exactly MIN_GAP apart, which is what
            keeps a ~26s take from stretching further.
            """
            page.wait_for_timeout(200)
            exposed = page.evaluate(EXPOSED_JS)
            if exposed:
                sys.exit(f"ABORT: {len(exposed)} unredacted secret(s) on screen at "
                         f"{label}: {exposed[:3]}")
            keep = union(rects_of(page, keep_sels))
            texts = page.evaluate(RECTS_JS)
            if keep is None:
                sys.exit(f"ABORT: nothing matched {keep_sels} at {label}")
            z, cx, cy, focus = solve_zoom(keep, texts)
            last = punches[-1]["t1"] if punches else None
            if last is not None:
                while mark() - last < MIN_GAP:
                    time.sleep(0.05)
            start = mark()
            observed = extra(hold) if extra else None
            if extra is None:
                time.sleep(hold)
            end = mark()
            punches.append({"label": label, "t0": start, "t1": end,
                            "zoom": z, "center": [cx, cy],
                            "keep": keep, "texts": texts, "focus": focus})
            tl[label] = start
            if observed is not None:
                notes[label] = observed
            print(f"  beat {label}: t={start:.2f}..{end:.2f} z={z:.3f} c=({cx:.2f},{cy:.2f})")

        # ---- load -------------------------------------------------------
        page.goto(f"{SITE}/calendar", wait_until="domcontentloaded", timeout=60000)
        time.sleep(PRE_WAIT)
        if page.locator(".lock-wrap").count():
            sys.exit("ABORT: lock screen on camera — the injected factory_token "
                     "was rejected (token rotated? edge fn redeployed?).")
        page.wait_for_selector(".cal-toolbar", timeout=20000)

        # ---- 1. IDEA IN -------------------------------------------------
        page.locator(".tab", has_text="Agenda").first.click()
        page.wait_for_timeout(700)
        card = page.locator(".cal-item", has_text="I Built an AI Factory").first
        card.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        cut_in = mark() - 0.6   # the final cut starts here: everything before
                                # is page-load and scroll-to-item dead time
        card.click()
        page.wait_for_selector(".drawer .prompt-box", timeout=15000)
        page.locator(".drawer .prompt-box").first.scroll_into_view_if_needed()
        beat("brief_open", [".drawer-title", ".drawer .prompt-box"], HOLDS["brief_open"])

        # ---- 2. PLANNED -------------------------------------------------
        page.locator(".drawer .icon-btn[aria-label='Close']").first.click()
        page.wait_for_timeout(300)
        page.locator("a.nav-item[href='/studio']").first.click()
        page.wait_for_selector(".studio-card", timeout=20000)
        beat("studio_list", [".studio-card"], HOLDS["studio_list"])

        # ---- 3. QUEUE WORKING -------------------------------------------
        page.locator(".studio-card", has_text="I Built an AI Factory").first.click()
        page.wait_for_selector(".filmstrip .fs-chip", timeout=25000)
        page.wait_for_timeout(800)
        # Pick the log subject here, ranked by what each sibling has written
        # since the take began — done during the board's own settle so it adds
        # no dead air to the gap before the log beat.
        run1, len1 = log_lengths(token, args.self_job)
        log_job, growth = pick_liveliest_job(run1, len0, len1)
        if log_job:
            print(f"log subject: {log_job['title'][:50]} "
                  f"(+{growth[log_job['id']]} chars this take)")
        gen = page.locator(".filmstrip .fs-generating").first
        if gen.count():
            gen.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        # .board-bar spans the full content column. Guarding it as well as the
        # tiles stops the crop from landing mid-column: a punch centred only on
        # the (right-heavy) tile union slices the board title and breadcrumb in
        # half at the left margin — measured, take 3.
        keep3 = [".board-bar", ".queue-hint", ".filmstrip .fs-generating"]
        if not page.locator(".queue-hint").count():
            notes["queue_hint"] = "absent — no generation job queued/running at capture"
            keep3 = [".board-bar", ".filmstrip .fs-generating"]
        beat("generating_pulse", keep3, HOLDS["generating_pulse"])
        board_state = page.evaluate(
            """() => ({
                 generating: document.querySelectorAll('.filmstrip .fs-generating').length,
                 approved: document.querySelectorAll('.filmstrip .fs-approved').length,
                 queued: document.querySelectorAll('.filmstrip .fs-queued').length,
                 hint: (document.querySelector('.queue-hint') || {}).textContent || null,
               })"""
        )

        # ---- 4. WORKER LOG ----------------------------------------------
        if not log_job:
            sys.exit("ABORT: no OTHER running job left to film.")

        page.locator("a.nav-item[href='/jobs']").first.click()
        page.wait_for_selector("table.table tbody tr", timeout=20000)
        row = page.locator("table.table tbody tr", has_text=log_job["title"][:44]).first
        row.scroll_into_view_if_needed()
        row.click()
        # The drawer mounts empty and fills from its own fetch, so "no logbox
        # yet" is the normal first state, not evidence of a recap — wait the
        # box out before concluding anything.
        page.wait_for_selector(".drawer .drawer-body", timeout=20000)
        try:
            page.wait_for_selector(".drawer pre.logbox", timeout=8000)
        except PWTimeout:
            if not page.locator(".drawer .details-toggle").count():
                raise
            # the job finished between the pick and the click: a recap now
            # fronts the drawer and the log sits behind "Show details"
            notes["log_job_finished_mid_take"] = True
            page.locator(".drawer .details-toggle").first.click()
            page.wait_for_selector(".drawer pre.logbox", timeout=10000)
        page.wait_for_function(
            "() => { const e = document.querySelector('.drawer pre.logbox');"
            " return e && e.textContent.trim().length > 40; }",
            timeout=25000,
        )
        page.evaluate("() => window.__sweep && window.__sweep()")
        exposed = page.evaluate(EXPOSED_JS)
        if exposed:
            sys.exit(f"ABORT: job log leaked {len(exposed)} secret(s): {exposed[:3]}")
        page.locator(".drawer pre.logbox").first.scroll_into_view_if_needed()

        # Sit on the open drawer until the log actually moves once, capped at
        # one poll interval plus slack. Starting the hold just after a confirmed
        # append means the next 4s poll lands inside it. This wait is mostly
        # absorbed by the beat gap that has to elapse anyway; if the log never
        # moves we film it anyway and say so, rather than hunt for a livelier
        # job until one happens to cooperate.
        len_js = ("() => { const e = document.querySelector('.drawer pre.logbox');"
                  " return e ? e.textContent.length : 0; }")
        n0, wait_end = page.evaluate(len_js), time.monotonic() + 5.0
        while time.monotonic() < wait_end:
            if page.evaluate(len_js) != n0:
                notes["log_preroll"] = "append seen before the hold opened"
                break
            time.sleep(0.25)
        else:
            notes["log_preroll"] = "no append in the 5s before the hold opened"

        tail_js = ("() => { const e = document.querySelector('.drawer pre.logbox');"
                   " if (!e) return [0, '']; const t = e.textContent;"
                   " return [t.length, t.trimEnd().split('\\n').slice(-1)[0].slice(0, 120)]; }")

        def watch_log(hold):
            series, tails, end = [], [], time.monotonic() + hold
            while time.monotonic() < end:
                n, tail = page.evaluate(tail_js)
                series.append(n)
                if not tails or tails[-1] != tail:
                    tails.append(tail)
                time.sleep(0.4)
            return {"log_chars": [series[0], series[-1]],
                    "appended": series[-1] - series[0],
                    "appends_seen": sum(1 for a, b in zip(series, series[1:]) if b != a),
                    "last_lines": tails[:6],
                    "samples": len(series)}

        beat("log_stream", [".drawer .drawer-section.grow"], HOLDS["log_stream"],
             extra=watch_log)

        counts = page.evaluate("() => [window.__maskHits || 0, window.__blurHits || 0]")
        final_exposed = page.evaluate(EXPOSED_JS)
        if final_exposed:
            sys.exit(f"ABORT: {len(final_exposed)} secret(s) exposed at end of take")
        time.sleep(0.4)
        video = page.video
        ctx.close()
        browser.close()
        raw = Path(video.path())

    statuses_after = asset_statuses(args.calendar_id, token)
    flips = {k: [statuses_before.get(k), v] for k, v in statuses_after.items()
             if statuses_before.get(k) not in (None, v)}

    # ---- raw -> 1080x1920, trimming only the page-load dead head ---------
    trim = round(max(cut_in, 0.0), 3)
    upscaled = out.with_name(out.stem + ".raw1080.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw), "-ss", str(trim),
        "-vf", "scale=1080:1920:flags=lanczos",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30", "-an", str(upscaled),
    ], check=True, capture_output=True)
    for f in tmpdir.iterdir():
        f.unlink()
    tmpdir.rmdir()

    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(upscaled)],
        capture_output=True, text=True).stdout.strip())

    rel = lambda t: round(max(t - trim, 0.0), 3)
    for pu in punches:
        pu["t0"], pu["t1"] = rel(pu["t0"]), rel(pu["t1"])
    for k in list(tl):
        tl[k] = rel(tl[k])

    margins = sweep_margins(punches, dur)
    timeline = {
        "duration": round(dur, 3),
        **tl,
        "punches": [{k: pu[k] for k in ("label", "t0", "t1", "zoom", "center")}
                    for pu in punches],
        "guards": {pu["label"]: {"keep": [round(v, 4) for v in pu["keep"]],
                                 "text_elements": len(pu["texts"]),
                                 "in_focus_labels": len(pu["focus"])} for pu in punches},
        "edge_margin_sweep": {"fps": [2, 5], "violations": margins},
        "observed": {
            "board": board_state,
            "log": notes.get("log_stream"),
            "log_job": {"title": log_job["title"], "type": log_job["type"],
                        "model": log_job.get("model"), "effort": log_job.get("effort")},
            "log_job_probe_growth_chars": growth.get(log_job["id"]),
            "status_flip": flips or None,
            "assets_before": statuses_before,
            "assets_after": statuses_after,
            "redaction": {"masked_in_transport": counts[0], "blurred_in_dom": counts[1],
                          "exposed_at_end": 0},
            **{k: v for k, v in notes.items() if k != "log_stream"},
        },
    }
    tl_path = out.with_suffix(".timeline.json")
    tl_path.write_text(json.dumps(timeline, indent=2))
    print(json.dumps({k: timeline[k] for k in
                      ("duration", "brief_open", "studio_list",
                       "generating_pulse", "log_stream")}, indent=2))
    print("violations:", margins or "none")
    print(f"raw {upscaled}\ntimeline {tl_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
