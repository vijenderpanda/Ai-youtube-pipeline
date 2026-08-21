#!/usr/bin/env python3
"""qc_motion.py — machine-QC gate suite for the motion-graphics Shorts pipeline.

Spec: docs/MOTION-PIPELINE.md (PART I laws U1-U10, PART II QUALITY GATES table).
Runs on a rendered MP4; the FILM MANIFEST (--manifest) is the spec for the
manifest-assisted gates. A gate that cannot run reports SKIPPED with the reason
— it never silently passes.

GATES (id — law — threshold):

  G1  dead-frame      (U1)  FAIL if every content-carrying 100px band has zero
                            ink-delta for >=1.0s (the doc's U1 test: "delta==0
                            in every band containing rendered content"), or the
                            full frame freezes (raw luma) >=0.5s. The worst
                            single-band static run is reported as detail —
                            references legally park one element (100x parks a
                            header 1.6s), so one static band alone is not dead.
                            "Content" = band mean ink > 0.5%. Ink = high-pass
                            mask: |luma - gauss(luma, sigma=24@1080w)| > 7 OR
                            |sat - gauss(sat)| > 18.
  G2  visual-twin     (U2)  MANIFEST vo_phrases [{t0,t1,text}]: every phrase
                            needs an ink-delta event (max band delta >= p60 of
                            the whole video) within [t0-0.5, t1+0.5]. FAIL per
                            phrase with no aligned event.
  G3  carry           (U3)  MANIFEST carry [{t, bbox:[x,y,w,h]}] (px or 0-1
                            normalized): at every detected cut the declared
                            carry bbox must hold ink (>0.5%) in the last
                            pre-cut frame AND in one of the first 12 post-cut
                            frames. FAIL any boundary missing either side.
  G4  cut-budget      (U4)  ffmpeg select='gt(scene,0.28)' cuts / duration
                            <= 0.45 cuts/s. (A declared beat grid would excuse
                            more — not implemented until an episode needs A7.)
  G6  palette         (U6)  k-means (k=8, hue on the unit circle, clusters
                            within 15 deg merged) over pixels with S>25%,
                            V in [10%,95%], sampled every 0.5s: <=6 hue
                            clusters with >2% share.
  G7  chips           (U7/N1) MANIFEST chips [{t,text}]: <=3 words per chip;
                            no gap >1.5s between chip advances during speech
                            (speech = vo_phrases if present, else whole film).
  G8  payoff          (U8)  MANIFEST payoff_first_at >= 0.75 x duration.
  G9  knee-event      (U9)  knee signal = per-second (mask-delta + luma-delta)
                            — luma added because Fusion's 5.0s world inversion
                            is a flat color flip the high-pass mask cannot see.
                            PASS iff max inside 4.0-8.0s >= 0.12 absolute AND
                            >= 55% of the film's loudest second. (The doc's
                            "knee >= p90 of own seconds" is replaced: measured
                            references are loud in every second, so their own
                            p90 fails them, while a globally dead film passes
                            its own tiny p90 — the relative-only test rewards
                            exactly the habit U9 exists to kill.) The loudest
                            second is reported.
  G12 loop            (—)   histogram distance (mean 32-bin RGB, 0.5*L1)
                            first-12 vs last-12 frames <= 0.30. WARN only
                            (first-month policy), never FAIL.
  C1  exposure-score  (C1)  per-second mean luma: sigma >= 15 AND at least one
                            second < 25% of peak inside the middle third.
                            WARN only (craft-tier, not a gate).

CLI:
  python3 scripts/qc_motion.py --video <mp4> [--manifest <json>] [--json <out.json>]

Exit code 1 if any gate FAILs, else 0 (WARN/SKIPPED do not fail the run).
"""

import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

# ---------------------------------------------------------------- constants
EXTRACT_W = 270          # extraction width (px)
EXTRACT_FPS = 8          # >= 4fps required for G1/G9
INK_SIGMA_AT_1080 = 24.0 # high-pass gaussian sigma at 1080px width
INK_LUMA_T = 7           # |luma - blur| threshold
INK_SAT_T = 18           # |sat - blur| threshold
BAND_SRC_PX = 100        # G1 band height in source pixels
CONTENT_INK = 0.005      # band "carries content" above this mean ink
BAND_STATIC_EPS = 0.0004 # band delta at/below this = "zero ink-delta"
DEAD_BAND_SECS = 1.0     # G1: static content band fails at this duration
FREEZE_LUMA_EPS = 0.20   # full-frame mean |luma delta| below this = frozen
FREEZE_SECS = 0.5        # G1: full freeze fails at this duration
SCENE_T = 0.28           # G4 scdet threshold
CUTS_PER_S = 0.45        # G4 budget
PALETTE_SAMPLE_S = 0.5   # G6 sampling interval
PALETTE_K = 8            # G6 k-means k
PALETTE_MERGE_DEG = 15.0 # G6 merge clusters closer than this
PALETTE_MIN_SHARE = 0.02 # G6 cluster counts if share above this
PALETTE_MAX = 6          # G6 max clusters
TWIN_PCTL = 60           # G2 event percentile
TWIN_SLOP_S = 0.5        # G2 alignment slop
CARRY_POST_FRAMES = 12   # G3 post-cut search depth
CHIP_MAX_WORDS = 3       # G7
CHIP_MAX_GAP_S = 1.5     # G7 stale-caption limit during speech
PAYOFF_FRAC = 0.75       # G8
KNEE_WIN = (4.0, 8.0)    # G9 window
KNEE_ABS_MIN = 0.12      # G9 absolute floor for the knee second (comb signal)
KNEE_REL = 0.55          # G9 knee must be >= this fraction of the loudest second
LOOP_HIST_MAX = 0.30     # G12 histogram distance ceiling
LOOP_FRAMES = 12         # G12 frames compared each end
EXPO_SIGMA_MIN = 15.0    # C1
EXPO_DIP_FRAC = 0.25     # C1 dip below this fraction of peak
# ---------------------------------------------------------------------------

PASS, FAIL, WARN, SKIP = "PASS", "FAIL", "WARN", "SKIPPED"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(video):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate:format=duration",
             "-of", "json", video])
    if r.returncode != 0:
        raise RuntimeError("ffprobe failed: " + r.stderr.strip())
    j = json.loads(r.stdout)
    st = j["streams"][0]
    dur = float(j["format"]["duration"])
    num, den = st["r_frame_rate"].split("/")
    return int(st["width"]), int(st["height"]), float(num) / float(den), dur


def extract_frames(video, outdir):
    """One ffmpeg pass: EXTRACT_FPS fps, EXTRACT_W wide, PNG."""
    pat = os.path.join(outdir, "f%05d.png")
    r = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video,
             "-vf", "fps=%d,scale=%d:-2" % (EXTRACT_FPS, EXTRACT_W),
             "-pix_fmt", "rgb24", pat])
    if r.returncode != 0:
        raise RuntimeError("ffmpeg extraction failed: " + r.stderr.strip())
    files = sorted(f for f in os.listdir(outdir) if f.endswith(".png"))
    return [os.path.join(outdir, f) for f in files]


def detect_cuts(video):
    """ffmpeg scdet metadata pass -> list of cut timestamps (s)."""
    r = run(["ffmpeg", "-hide_banner", "-i", video, "-an",
             "-vf", "select='gt(scene,%g)',metadata=print:file=-" % SCENE_T,
             "-f", "null", "-"])
    cuts = []
    for line in r.stdout.splitlines():
        if "pts_time:" in line:
            try:
                cuts.append(float(line.split("pts_time:")[1].split()[0]))
            except ValueError:
                pass
    return cuts


def ink_mask(rgb, sigma):
    """High-pass content mask per the existing auditor:
    |luma - gauss(luma)| > 7  OR  |sat - gauss(sat)| > 18.
    Aurora/gradient backgrounds measure 0."""
    im = Image.fromarray(rgb)
    luma = np.asarray(im.convert("L"), dtype=np.int16)
    sat = np.asarray(im.convert("HSV"), dtype=np.int16)[:, :, 1]
    lb = np.asarray(Image.fromarray(luma.astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(sigma)), dtype=np.int16)
    sb = np.asarray(Image.fromarray(sat.astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(sigma)), dtype=np.int16)
    return (np.abs(luma - lb) > INK_LUMA_T) | (np.abs(sat - sb) > INK_SAT_T)


class FrameStats(object):
    """Everything computed in the single pass over extracted frames."""

    def __init__(self, paths, src_w, src_h):
        sigma = INK_SIGMA_AT_1080 * EXTRACT_W / 1080.0
        first = np.asarray(Image.open(paths[0]))
        h, w = first.shape[:2]
        self.w, self.h = w, h
        self.n = len(paths)
        band_px = max(4, int(round(BAND_SRC_PX * h / float(src_h))))
        self.band_px = band_px
        self.nbands = max(1, int(math.ceil(h / float(band_px))))
        self.src_scale = src_h / float(h)  # extract px -> source px

        n, nb = self.n, self.nbands
        self.band_ink = np.zeros((n, nb))      # mean ink per band
        self.band_delta = np.zeros((n, nb))    # mask XOR fraction per band (0 @ f0)
        self.frame_delta = np.zeros(n)         # full-frame mask XOR fraction
        self.luma_delta = np.zeros(n)          # full-frame raw mean |luma diff|
        self.mean_luma = np.zeros(n)
        self.masks = []                        # kept for G3 bbox checks
        self.rgbs_first = []
        self.rgbs_last = []
        self.palette_px = []                   # sampled hue-eligible pixels

        prev_mask = None
        prev_luma = None
        pal_every = max(1, int(round(PALETTE_SAMPLE_S * EXTRACT_FPS)))
        for i, p in enumerate(paths):
            rgb = np.asarray(Image.open(p).convert("RGB"))
            mask = ink_mask(rgb, sigma)
            self.masks.append(np.packbits(mask))  # packed to save memory
            luma = np.asarray(Image.fromarray(rgb).convert("L"), dtype=np.float32)
            self.mean_luma[i] = luma.mean()
            for b in range(nb):
                y0, y1 = b * band_px, min((b + 1) * band_px, h)
                self.band_ink[i, b] = mask[y0:y1].mean()
            if prev_mask is not None:
                x = mask ^ prev_mask
                self.frame_delta[i] = x.mean()
                self.luma_delta[i] = np.abs(luma - prev_luma).mean()
                for b in range(nb):
                    y0, y1 = b * band_px, min((b + 1) * band_px, h)
                    self.band_delta[i, b] = x[y0:y1].mean()
            prev_mask, prev_luma = mask, luma
            if i < LOOP_FRAMES:
                self.rgbs_first.append(rgb)
            if i >= self.n - LOOP_FRAMES:
                self.rgbs_last.append(rgb)
            if i % pal_every == 0:
                hsv = np.asarray(Image.fromarray(rgb).convert("HSV"),
                                 dtype=np.float32).reshape(-1, 3)
                sel = hsv[(hsv[:, 1] > 0.25 * 255)
                          & (hsv[:, 2] >= 0.10 * 255)
                          & (hsv[:, 2] <= 0.95 * 255)]
                if len(sel) > 4000:  # cap per sample for speed
                    sel = sel[np.random.RandomState(i).choice(
                        len(sel), 4000, replace=False)]
                self.palette_px.append(sel[:, 0] * (360.0 / 255.0))

    def mask_at(self, i):
        return np.unpackbits(self.masks[i])[: self.h * self.w] \
            .reshape(self.h, self.w).astype(bool)


# ------------------------------------------------------------------- gates

def gate_g1(fs, dur):
    """U1 NO-DEAD-FRAME."""
    t_per = 1.0 / EXTRACT_FPS
    worst = None  # (secs, t_start, kind, band) — worst single-band static run
    for b in range(fs.nbands):
        run_len = 0
        for i in range(1, fs.n):
            static = (fs.band_delta[i, b] <= BAND_STATIC_EPS
                      and fs.band_ink[i, b] > CONTENT_INK)
            if static:
                run_len += 1
                secs = run_len * t_per
                if worst is None or secs > worst[0]:
                    y0 = int(b * fs.band_px * fs.src_scale)
                    worst_t = (i - run_len) * t_per
                    worst = (secs, worst_t, "band y~%dpx" % y0, b)
            else:
                run_len = 0
    # the doc's U1 test: delta==0 in EVERY band containing rendered content
    dead = None  # (secs, t_start)
    run_len = 0
    for i in range(1, fs.n):
        content = fs.band_ink[i] > CONTENT_INK
        all_static = bool(content.any()) and bool(
            (fs.band_delta[i][content] <= BAND_STATIC_EPS).all())
        if all_static:
            run_len += 1
            secs = run_len * t_per
            if dead is None or secs > dead[0]:
                dead = (secs, (i - run_len) * t_per)
        else:
            run_len = 0
    band_fail = dead is not None and dead[0] >= DEAD_BAND_SECS
    # full-frame freeze
    fworst = None
    run_len = 0
    for i in range(1, fs.n):
        if fs.luma_delta[i] <= FREEZE_LUMA_EPS:
            run_len += 1
            secs = run_len * t_per
            if fworst is None or secs > fworst[0]:
                fworst = (secs, (i - run_len) * t_per)
        else:
            run_len = 0
    freeze_fail = fworst is not None and fworst[0] >= FREEZE_SECS
    parts = []
    if dead:
        parts.append("all-content-bands static %.2fs @%.1fs" % (dead[0], dead[1]))
    if worst:
        parts.append("worst single band %.2fs @%.1fs (%s)"
                     % (worst[0], worst[1], worst[2]))
    else:
        parts.append("no static content band")
    if fworst:
        parts.append("worst freeze %.2fs @%.1fs" % (fworst[0], fworst[1]))
    else:
        parts.append("no full freeze")
    status = FAIL if (band_fail or freeze_fail) else PASS
    return status, "; ".join(parts), \
        "all-bands-static<%.1fs & freeze<%.1fs" % (DEAD_BAND_SECS, FREEZE_SECS)


def gate_g2(fs, manifest):
    """U2 VISUAL-TWIN (manifest vo_phrases)."""
    phrases = (manifest or {}).get("vo_phrases")
    if not phrases:
        return SKIP, "no manifest / no vo_phrases", "event within ±%.1fs" % TWIN_SLOP_S
    series = fs.band_delta[1:].max(axis=1)  # per-frame max band delta
    p60 = float(np.percentile(series, TWIN_PCTL))
    misses = []
    for ph in phrases:
        t0 = float(ph["t0"]) - TWIN_SLOP_S
        t1 = float(ph["t1"]) + TWIN_SLOP_S
        i0 = max(1, int(t0 * EXTRACT_FPS))
        i1 = min(fs.n - 1, int(math.ceil(t1 * EXTRACT_FPS)))
        seg = fs.band_delta[i0:i1 + 1].max(axis=1) if i1 >= i0 else np.array([])
        if seg.size == 0 or seg.max() < p60:
            misses.append(ph.get("text", "@%.1fs" % float(ph["t0"]))[:24])
    if misses:
        return FAIL, "%d/%d phrases w/o visual event: %s" % (
            len(misses), len(phrases), "; ".join(misses[:4])), ">=p60 band event / phrase"
    return PASS, "all %d phrases have an aligned event (p60=%.4f)" % (
        len(phrases), p60), ">=p60 band event / phrase"


def _norm_bbox(bbox, src_w, src_h, fs):
    x, y, w, h = [float(v) for v in bbox]
    if max(x, y, w, h) <= 1.0:  # normalized
        x, y, w, h = x * src_w, y * src_h, w * src_w, h * src_h
    s = fs.w / float(src_w)
    x0, y0 = int(x * s), int(y * s)
    x1, y1 = int(math.ceil((x + w) * s)), int(math.ceil((y + h) * s))
    return max(0, x0), max(0, y0), min(fs.w, x1), min(fs.h, y1)


def gate_g3(fs, manifest, cuts, src_w, src_h):
    """U3 CARRY-ELEMENT (manifest carry bbox track x detected cuts)."""
    carry = (manifest or {}).get("carry")
    if not carry:
        return SKIP, "no manifest / no carry track", "ink both sides of every cut"
    if not cuts:
        return PASS, "0 cuts — carry trivially survives", "ink both sides of every cut"
    entries = sorted(carry, key=lambda e: float(e["t"]))
    bad = []
    for tc in cuts:
        pre = [e for e in entries if float(e["t"]) <= tc]
        post = [e for e in entries if float(e["t"]) >= tc]
        if not pre or not post:
            bad.append("cut@%.1fs: no declared bbox %s the cut"
                       % (tc, "before" if not pre else "after"))
            continue
        ok = True
        for e, frames in ((pre[-1], [max(0, int(tc * EXTRACT_FPS) - 1)]),
                          (post[0], list(range(int(tc * EXTRACT_FPS) + 1,
                                               min(fs.n, int(tc * EXTRACT_FPS) + 1
                                                   + CARRY_POST_FRAMES))))):
            x0, y0, x1, y1 = _norm_bbox(e["bbox"], src_w, src_h, fs)
            if x1 <= x0 or y1 <= y0:
                ok = False
                continue
            found = False
            for fi in frames:
                if fi < fs.n and fs.mask_at(fi)[y0:y1, x0:x1].mean() > CONTENT_INK:
                    found = True
                    break
            ok = ok and found
        if not ok:
            bad.append("cut@%.1fs: carry bbox empty on one side" % tc)
    if bad:
        return FAIL, "; ".join(bad[:4]), "ink both sides of every cut"
    return PASS, "carry present across all %d cuts" % len(cuts), \
        "ink both sides of every cut"


def gate_g4(cuts, dur):
    """U4 CUT-BUDGET."""
    rate = len(cuts) / dur if dur > 0 else 0.0
    status = PASS if rate <= CUTS_PER_S else FAIL
    return status, "%d cuts / %.1fs = %.2f cuts/s" % (len(cuts), dur, rate), \
        "<=%.2f cuts/s" % CUTS_PER_S


def gate_g6(fs):
    """U6 LOCKED-PALETTE (numpy k-means on hue circle)."""
    if not fs.palette_px or sum(len(p) for p in fs.palette_px) < 500:
        return SKIP, "too few saturated pixels to cluster", \
            "<=%d hue clusters >%d%% share" % (PALETTE_MAX, int(PALETTE_MIN_SHARE * 100))
    hues = np.concatenate(fs.palette_px)
    if len(hues) > 60000:
        hues = hues[np.random.RandomState(0).choice(len(hues), 60000, replace=False)]
    rad = np.deg2rad(hues)
    pts = np.stack([np.cos(rad), np.sin(rad)], axis=1)
    k = min(PALETTE_K, len(np.unique(np.round(hues))) or 1)
    rng = np.random.RandomState(0)
    centers = pts[rng.choice(len(pts), k, replace=False)]
    for _ in range(20):
        d = ((pts[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        lab = d.argmin(axis=1)
        new = np.array([pts[lab == j].mean(axis=0) if (lab == j).any()
                        else centers[j] for j in range(k)])
        if np.allclose(new, centers, atol=1e-4):
            centers = new
            break
        centers = new
    shares = np.array([(lab == j).mean() for j in range(k)])
    cdeg = (np.degrees(np.arctan2(centers[:, 1], centers[:, 0])) + 360) % 360
    # merge clusters within PALETTE_MERGE_DEG on the hue circle
    order = np.argsort(cdeg)
    merged = []  # [hue, share]
    for j in order:
        placed = False
        for m in merged:
            dd = abs(cdeg[j] - m[0])
            if min(dd, 360 - dd) <= PALETTE_MERGE_DEG:
                m[0] = (m[0] * m[1] + cdeg[j] * shares[j]) / (m[1] + shares[j])
                m[1] += shares[j]
                placed = True
                break
        if not placed:
            merged.append([cdeg[j], shares[j]])
    big = [(h, s) for h, s in merged if s > PALETTE_MIN_SHARE]
    hue_str = ", ".join("%.0fdeg:%.0f%%" % (h, s * 100)
                        for h, s in sorted(big, key=lambda x: -x[1]))
    status = PASS if len(big) <= PALETTE_MAX else FAIL
    return status, "%d hue families >%.0f%% [%s]" % (
        len(big), PALETTE_MIN_SHARE * 100, hue_str), \
        "<=%d clusters" % PALETTE_MAX


def gate_g7(manifest, dur):
    """U7/N1 CHIP CADENCE (manifest chips; no OCR — tesseract not installed)."""
    chips = (manifest or {}).get("chips")
    if not chips:
        return SKIP, "no manifest / no chips", \
            "<=%d words; gap<=%.1fs in speech" % (CHIP_MAX_WORDS, CHIP_MAX_GAP_S)
    chips = sorted(chips, key=lambda c: float(c["t"]))
    fat = [c["text"] for c in chips if len(str(c["text"]).split()) > CHIP_MAX_WORDS]
    phrases = (manifest or {}).get("vo_phrases")

    def speech_overlap(a, b):
        """Seconds of (a,b) that fall inside VO speech."""
        if not phrases:
            return b - a
        return sum(max(0.0, min(b, float(p["t1"])) - max(a, float(p["t0"])))
                   for p in phrases)

    stale = []
    times = [float(c["t"]) for c in chips]
    for a, b in zip(times, times[1:] + [dur]):
        if b - a > CHIP_MAX_GAP_S and speech_overlap(a, b) > CHIP_MAX_GAP_S:
            stale.append("%.1f-%.1fs" % (a, b))
    probs = []
    if fat:
        probs.append("%d chips >%d words (e.g. '%s')"
                     % (len(fat), CHIP_MAX_WORDS, str(fat[0])[:30]))
    if stale:
        probs.append("%d stale windows: %s" % (len(stale), ", ".join(stale[:3])))
    if probs:
        return FAIL, "; ".join(probs), \
            "<=%d words; gap<=%.1fs in speech" % (CHIP_MAX_WORDS, CHIP_MAX_GAP_S)
    return PASS, "%d chips, all <=%d words, cadence ok" % (len(chips), CHIP_MAX_WORDS), \
        "<=%d words; gap<=%.1fs in speech" % (CHIP_MAX_WORDS, CHIP_MAX_GAP_S)


def gate_g8(manifest, dur):
    """U8 WITHHELD-PAYOFF."""
    t = (manifest or {}).get("payoff_first_at")
    if t is None:
        return SKIP, "no manifest / no payoff_first_at", \
            ">=%.0f%% of runtime" % (PAYOFF_FRAC * 100)
    t = float(t)
    frac = t / dur if dur > 0 else 0
    status = PASS if frac >= PAYOFF_FRAC else FAIL
    return status, "payoff first at %.1fs = %.0f%% of %.1fs" % (t, frac * 100, dur), \
        ">=%.0f%% of runtime" % (PAYOFF_FRAC * 100)


def gate_g9(fs, dur):
    """U9 KNEE-EVENT. Signal = per-second mean(mask XOR + raw luma delta) so
    both content motion and world/palette inversions register."""
    thr = ">=%.2f abs & >=%.0f%% of loudest sec" % (KNEE_ABS_MIN, KNEE_REL * 100)
    nsec = int(math.floor(dur))
    if nsec <= int(KNEE_WIN[0]):
        return SKIP, "video shorter than the knee window", thr
    per_sec = np.zeros(nsec)
    for s in range(nsec):
        i0 = max(1, int(s * EXTRACT_FPS))
        i1 = min(fs.n, int((s + 1) * EXTRACT_FPS))
        if i1 > i0:
            per_sec[s] = (fs.frame_delta[i0:i1]
                          + fs.luma_delta[i0:i1] / 255.0).mean()
    loud = int(per_sec.argmax())
    allmax = float(per_sec.max())
    k0, k1 = int(KNEE_WIN[0]), min(nsec, int(KNEE_WIN[1]))
    knee_max = float(per_sec[k0:k1].max()) if k1 > k0 else 0.0
    ok = knee_max >= KNEE_ABS_MIN and knee_max >= KNEE_REL * allmax
    status = PASS if ok else FAIL
    return status, ("knee(4-8s) max %.3f vs loudest %.3f @%ds"
                    % (knee_max, allmax, loud)), thr


def _hist(rgbs):
    h = np.zeros(96)
    for rgb in rgbs:
        for c in range(3):
            hh, _ = np.histogram(rgb[:, :, c], bins=32, range=(0, 256))
            h[c * 32:(c + 1) * 32] += hh
    return h / h.sum()


def gate_g12(fs):
    """Loop compatibility — WARN-only per the first-month policy."""
    if len(fs.rgbs_first) < 2 or len(fs.rgbs_last) < 2:
        return SKIP, "too few frames", "hist dist <=%.2f" % LOOP_HIST_MAX
    d = 0.5 * np.abs(_hist(fs.rgbs_first) - _hist(fs.rgbs_last)).sum()
    status = PASS if d <= LOOP_HIST_MAX else WARN
    return status, "first/last-%d-frame histogram distance %.3f" % (LOOP_FRAMES, d), \
        "<=%.2f (WARN only)" % LOOP_HIST_MAX


def gate_c1(fs, dur):
    """C1 EXPOSURE-SCORE — WARN-only (craft tier)."""
    nsec = int(math.floor(dur))
    if nsec < 3:
        return SKIP, "video too short", "sigma>=15 & mid-third dip"
    per_sec = np.array([fs.mean_luma[int(s * EXTRACT_FPS):
                                     max(int(s * EXTRACT_FPS) + 1,
                                         int((s + 1) * EXTRACT_FPS))].mean()
                        for s in range(nsec)])
    sigma = float(per_sec.std())
    peak = float(per_sec.max())
    m0, m1 = nsec // 3, max(nsec // 3 + 1, (2 * nsec) // 3)
    dip = bool((per_sec[m0:m1] < EXPO_DIP_FRAC * peak).any())
    probs = []
    if sigma < EXPO_SIGMA_MIN:
        probs.append("luma sigma %.1f < %.0f" % (sigma, EXPO_SIGMA_MIN))
    if not dip:
        probs.append("no mid-third second under 25%% of peak (peak %.0f)" % peak)
    if probs:
        return WARN, "; ".join(probs), "sigma>=15 & mid-third dip (WARN only)"
    return PASS, "luma sigma %.1f, mid-third dip present" % sigma, \
        "sigma>=15 & mid-third dip (WARN only)"


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Machine-QC gates for motion Shorts")
    ap.add_argument("--video", required=True)
    ap.add_argument("--manifest", help="FILM MANIFEST json (enables G2/G3/G7/G8)")
    ap.add_argument("--json", dest="json_out", help="write machine report here")
    args = ap.parse_args()

    if not os.path.exists(args.video):
        sys.exit("no such video: %s" % args.video)
    manifest = None
    if args.manifest:
        with open(args.manifest) as f:
            manifest = json.load(f)

    src_w, src_h, src_fps, dur = probe(args.video)

    import tempfile, shutil
    tmp = tempfile.mkdtemp(prefix="qc_motion_")
    try:
        paths = extract_frames(args.video, tmp)
        if len(paths) < 4:
            sys.exit("extraction produced <4 frames")
        fs = FrameStats(paths, src_w, src_h)
        cuts = detect_cuts(args.video)

        rows = []  # (id, law, status, measured, threshold)

        def add(gid, law, res):
            rows.append((gid, law, res[0], res[1], res[2]))

        add("G1", "U1 dead-frame", gate_g1(fs, dur))
        add("G2", "U2 visual-twin", gate_g2(fs, manifest))
        add("G3", "U3 carry", gate_g3(fs, manifest, cuts, src_w, src_h))
        add("G4", "U4 cut-budget", gate_g4(cuts, dur))
        add("G6", "U6 palette", gate_g6(fs))
        add("G7", "U7/N1 chips", gate_g7(manifest, dur))
        add("G8", "U8 payoff", gate_g8(manifest, dur))
        add("G9", "U9 knee-event", gate_g9(fs, dur))
        add("G12", "loop", gate_g12(fs))
        add("C1", "C1 exposure", gate_c1(fs, dur))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    name = os.path.basename(args.video)
    print("\nqc_motion — %s  (%dx%d, %.1fs, %d cuts, extracted %dfps@%dpx)"
          % (name, src_w, src_h, dur, len(cuts), EXTRACT_FPS, EXTRACT_W))
    wid = (4, 16, 8)
    print("-" * 110)
    print("%-*s %-*s %-*s %s" % (wid[0], "GATE", wid[1], "LAW", wid[2], "STATUS",
                                 "MEASURED  |  THRESHOLD"))
    print("-" * 110)
    for gid, law, status, meas, thr in rows:
        print("%-*s %-*s %-*s %s  |  %s"
              % (wid[0], gid, wid[1], law, wid[2], status, meas, thr))
    print("-" * 110)
    fails = [r for r in rows if r[2] == FAIL]
    warns = [r for r in rows if r[2] == WARN]
    skips = [r for r in rows if r[2] == SKIP]
    print("RESULT: %s  (%d fail, %d warn, %d skipped)\n"
          % ("FAIL" if fails else "PASS", len(fails), len(warns), len(skips)))

    if args.json_out:
        report = {
            "video": os.path.abspath(args.video),
            "width": src_w, "height": src_h, "duration": dur,
            "src_fps": src_fps, "cuts": cuts,
            "extract_fps": EXTRACT_FPS, "extract_width": EXTRACT_W,
            "manifest": os.path.abspath(args.manifest) if args.manifest else None,
            "result": "FAIL" if fails else "PASS",
            "gates": [{"id": g, "law": l, "status": s,
                       "measured": m, "threshold": t}
                      for g, l, s, m, t in rows],
        }
        with open(args.json_out, "w") as f:
            json.dump(report, f, indent=2)
        print("json report -> %s" % args.json_out)

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
