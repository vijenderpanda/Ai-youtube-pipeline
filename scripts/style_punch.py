#!/usr/bin/env python3
"""
style_punch.py — "punch-zoom" pro framing renderer for native 9:16 screen
recordings of AI chat demos (YouTube Shorts).

Look:
  - z=1.0 at start
  - during typing: smoothstep ease-in to ~1.32 centered on the text input box
  - shortly after submit: ease back out to 1.0 so the answer is fully visible
  - while the answer streams (and after): very slow push 1.0 -> ~1.08
  - around any scroll moment the zoom relaxes to 1.0 so nothing readable is cut

Usage:
  python3 scripts/style_punch.py INPUT OUTPUT [--timeline TIMELINE.json]

Timeline sidecar JSON (seconds, relative to the trimmed INPUT):
  {"typing_start": f, "typing_end": f, "submit": f, "answer_start": f,
   "answer_end": f, "scrolls": [f,...], "duration": f,
   // optional extras (normalized 0..1 coords), auto-detected if absent:
   "input_center": [cx, cy], "answer_center": [cx, cy],
   // optional zoom caps (default Z_TYPE / Z_PUSH) when content runs wide:
   "type_zoom": f, "push_zoom": f}

Multi-punch sidecar (used by settings/UI-flow recordings such as
record_memory_demo.py, where there is no single prompt->answer arc but two or
more separate moments to land on). When "punches" is present it REPLACES the
prompt->answer camera above:
  {"duration": f,
   "punches": [{"t0": f, "t1": f, "center": [cx, cy], "zoom": f,
                "label": "toggle"}, ...]}
Each punch eases 1.0 -> zoom over PUNCH_IN secs before t0, holds centred through
t1, then eases back to full frame over PUNCH_OUT. Punches must not overlap once
their ease ramps are included; overlapping windows are a hard error rather than a
silently blended camera move.

Without --timeline the moments are auto-detected by frame differencing:
the page-transition spike marks submit, sustained small activity before it is
typing, activity after it is the streaming answer, and the centroid of pixel
changes during typing locates the input box.

Rendering: frames are decoded via an ffmpeg rawvideo pipe, each frame gets a
subpixel crop+scale (PIL Image.resize with a float `box`, Lanczos) — this is
smoother at slow zooms than zoompan — and re-encoded H.264 crf 18 yuv420p
1080x1920 30fps, no audio.
"""

import argparse
import json
import math
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

OUT_W, OUT_H = 1080, 1920
FPS = 30

# ---- look parameters -------------------------------------------------------
Z_TYPE = 1.30          # punch-in level while typing (1.28-1.35 band)
Z_PUSH = 1.08          # slow push level while the answer streams
EASE_OUT_DELAY = 0.30  # seconds after submit before easing back out
EASE_OUT_DUR = 0.85    # seconds for the ease back to 1.0
SCROLL_PRE = 0.5       # zoom fully relaxed this long before a scroll…
SCROLL_HOLD = 1.0      # …and stays relaxed this long after it
SCROLL_RAMP = 0.6      # seconds to blend the relax envelope in/out
PUNCH_IN = 0.55        # ease-in before a multi-punch window opens
PUNCH_OUT = 0.65       # ease back to full frame after it closes


def smoothstep(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3.0 - 2.0 * p)


def probe(path):
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,nb_frames,r_frame_rate",
         "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    st = j["streams"][0]
    dur = float(j["format"]["duration"])
    num, den = st["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    return int(st["width"]), int(st["height"]), dur, fps


# ---- auto-detection --------------------------------------------------------

def detect_timeline(path, duration):
    """Frame-difference detection of typing / submit / answer moments."""
    dw, dh, dfps = 135, 240, 6.0
    proc = subprocess.run(
        [FFMPEG, "-v", "error", "-i", path,
         "-vf", f"fps={dfps},scale={dw}:{dh}", "-pix_fmt", "gray",
         "-f", "rawvideo", "-"],
        capture_output=True, check=True)
    raw = np.frombuffer(proc.stdout, dtype=np.uint8)
    n = len(raw) // (dw * dh)
    frames = raw[: n * dw * dh].reshape(n, dh, dw).astype(np.float32)
    if n < 6:
        raise RuntimeError("input too short for auto-detection")

    diffs = np.abs(np.diff(frames, axis=0))          # (n-1, dh, dw)
    mean_diff = diffs.mean(axis=(1, 2))              # per-step mean change
    t_of = lambda i: (i + 1) / dfps                  # time of step i

    # submit = the page-transition spike. Several large spikes can exist
    # (overlay dismissals, answer pop-in), so take the FIRST spike that is
    # comparable to the global max, not the max itself.
    spike_thr = 0.5 * float(mean_diff.max())
    i_sub = int(np.argmax(mean_diff > spike_thr))
    submit = t_of(i_sub)

    med = float(np.median(mean_diff))
    act_thr = max(0.25, 4.0 * med)                   # "something is happening"

    # typing: sustained small activity before the transition
    pre = mean_diff[:i_sub]
    active = np.where(pre > act_thr)[0]
    if len(active):
        typing_start = max(0.0, t_of(int(active[0])) - 0.3)
        typing_end = min(submit - 0.15, t_of(int(active[-1])) + 0.15)
    else:  # fallback: assume typing filled most of the pre-submit stretch
        typing_start, typing_end = 0.15 * submit, submit - 0.3
    if typing_end - typing_start < 0.5:
        typing_start = max(0.0, typing_end - 0.5)

    # answer streaming: activity after the transition; it ends at the first
    # sustained quiet gap (>=1.5s below threshold) rather than the very last
    # blip (banners/cursors keep twitching long after the answer landed)
    j0 = min(len(mean_diff) - 1, i_sub + int(0.4 * dfps))
    post = np.where(mean_diff[j0:] > act_thr)[0]
    if len(post):
        answer_start = t_of(j0 + int(post[0]))
        gap = int(1.5 * dfps)
        end_i = int(post[-1])
        for k in range(len(post) - 1):
            if post[k + 1] - post[k] >= gap:
                end_i = int(post[k])
                break
        answer_end = min(duration, t_of(j0 + end_i) + 0.3)
    else:
        answer_start = min(duration, submit + 0.8)
        answer_end = min(duration, answer_start + 2.0)

    # input box = pixel changes while typing. Typed text is left-anchored,
    # so don't just take the centroid: fit the full x-extent of the typing
    # activity inside the punch window (reduce the zoom if it can't fit)
    a0 = int(typing_start * dfps)
    a1 = max(a0 + 1, int(typing_end * dfps))
    acc = diffs[a0:a1].sum(axis=0)
    _, cy0 = _centroid(acc, default=(0.5, 0.5))
    type_zoom = Z_TYPE
    thr = acc.max() * 0.2 if acc.max() > 0 else 1.0
    cols = np.nonzero((acc >= thr).any(axis=0))[0]
    if len(cols):
        x_min = max(0.0, cols[0] / dw - 0.03)
        x_max = min(1.0, (cols[-1] + 1) / dw + 0.03)
        type_zoom = min(Z_TYPE, max(1.12, 0.98 / max(1e-6, x_max - x_min)))
        input_center = ((x_min + x_max) / 2.0, cy0)
    else:
        input_center = (0.5, cy0)
    # answer region centroid (kept in the readable upper-middle band)
    b0 = min(len(diffs) - 1, int(answer_start * dfps))
    b1 = max(b0 + 1, min(len(diffs), int(answer_end * dfps)))
    acc2 = diffs[b0:b1].sum(axis=0)
    acx, acy = _centroid(acc2, default=(0.5, 0.47))
    answer_center = (0.5, min(0.55, max(0.35, acy)))

    return {
        "typing_start": round(typing_start, 2),
        "typing_end": round(typing_end, 2),
        "submit": round(submit, 2),
        "answer_start": round(answer_start, 2),
        "answer_end": round(answer_end, 2),
        "scrolls": [],
        "duration": round(duration, 2),
        "input_center": [round(input_center[0], 3), round(input_center[1], 3)],
        "answer_center": [round(answer_center[0], 3), round(answer_center[1], 3)],
        "type_zoom": round(type_zoom, 3),
    }


def _centroid(acc, default):
    thr = acc.max() * 0.25 if acc.max() > 0 else 1.0
    mask = acc >= thr
    if not mask.any():
        return default
    ys, xs = np.nonzero(mask)
    w = acc[mask]
    return (float((xs * w).sum() / w.sum()) / acc.shape[1],
            float((ys * w).sum() / w.sum()) / acc.shape[0])


# ---- camera path -----------------------------------------------------------

class PunchCamera:
    """Camera for recordings made of N discrete moments rather than one arc.

    Sits at full frame, eases in onto each punch's center, holds, eases out.
    Used by the settings-flow recordings (toggle beat, then typing beat), which
    have no submit/answer structure for `Camera` to hang its path on.
    """

    def __init__(self, tl, duration):
        dur = min(float(tl.get("duration") or duration), duration)
        self.punches = []
        for i, p in enumerate(tl["punches"]):
            t0, t1 = float(p["t0"]), float(p["t1"])
            if t1 <= t0:
                raise ValueError(f"punch {i} ({p.get('label')}): t1 <= t0")
            cx, cy = p.get("center") or (0.5, 0.5)
            self.punches.append({
                "a": max(0.0, t0 - PUNCH_IN), "t0": t0,
                "t1": min(t1, dur), "b": min(t1 + PUNCH_OUT, dur),
                "c": (float(cx), float(cy)), "z": float(p.get("zoom") or Z_TYPE),
                "label": p.get("label") or f"punch{i}",
            })
        self.punches.sort(key=lambda p: p["a"])
        for x, y in zip(self.punches, self.punches[1:]):
            if y["a"] < x["b"]:
                raise ValueError(
                    f"punches {x['label']!r} and {y['label']!r} overlap once "
                    f"ease ramps are included ({x['b']:.2f}s > {y['a']:.2f}s) - "
                    f"separate the beats in the recording, don't blend them here")

    def at(self, t):
        for p in self.punches:
            if t < p["a"] or t > p["b"]:
                continue
            if t < p["t0"]:
                f = smoothstep((t - p["a"]) / max(1e-6, p["t0"] - p["a"]))
            elif t <= p["t1"]:
                f = 1.0
            else:
                f = 1.0 - smoothstep((t - p["t1"]) / max(1e-6, p["b"] - p["t1"]))
            z = 1.0 + (p["z"] - 1.0) * f
            cx = 0.5 + (p["c"][0] - 0.5) * f
            cy = 0.5 + (p["c"][1] - 0.5) * f
            return z, cx, cy
        return 1.0, 0.5, 0.5


class Camera:
    """Piecewise smoothstep zoom/center path built from the timeline."""

    def __init__(self, tl, duration):
        self.scrolls = list(tl.get("scrolls") or [])
        icx, icy = tl.get("input_center") or (0.5, 0.5)
        acx, acy = tl.get("answer_center") or (0.5, 0.47)
        c_full = (0.5, 0.5)
        c_input = (icx, icy)
        c_answer = (acx, acy)

        z_type = float(tl.get("type_zoom") or Z_TYPE)
        # answer text can run edge-to-edge (mobile chat UIs); cap the push from
        # the sidecar when 1.08 would clip the outermost readable characters
        z_push = float(tl.get("push_zoom") or Z_PUSH)
        t_ts = float(tl["typing_start"])
        t_te = float(tl["typing_end"])
        t_sub = float(tl["submit"])
        dur = float(tl.get("duration") or duration)
        dur = min(dur, duration)

        t_hold_end = min(t_sub + EASE_OUT_DELAY, dur)
        t_out_end = min(t_hold_end + EASE_OUT_DUR, dur)

        # segments: (t0, t1, z0, z1, c0, c1) — smoothstep inside each
        self.segs = []
        add = self.segs.append
        add((0.0, t_ts, 1.0, 1.0, c_full, c_full))
        add((t_ts, t_te, 1.0, z_type, c_input, c_input))
        add((t_te, t_hold_end, z_type, z_type, c_input, c_input))
        add((t_hold_end, t_out_end, z_type, 1.0, c_input, c_answer))
        add((t_out_end, max(t_out_end + 0.01, dur), 1.0, z_push,
             c_answer, c_answer))
        self.push_t0 = t_out_end

    def at(self, t):
        for i, (t0, t1, z0, z1, c0, c1) in enumerate(self.segs):
            if t < t1 or i == len(self.segs) - 1:
                tt = min(max(t, t0), t1)
                p = smoothstep((tt - t0) / (t1 - t0)) if t1 > t0 else 1.0
                z = z0 + (z1 - z0) * p
                cx = c0[0] + (c1[0] - c0[0]) * p
                cy = c0[1] + (c1[1] - c0[1]) * p
                # near scrolls, relax any push-zoom back to 1.0 so scrolling
                # content is never cropped
                if t >= self.push_t0 and self.scrolls:
                    z = 1.0 + (z - 1.0) * self._scroll_relax(t)
                return z, cx, cy
        return 1.0, 0.5, 0.5

    def _scroll_relax(self, t):
        r = 1.0
        for s in self.scrolls:
            a, b = s - SCROLL_PRE, s + SCROLL_HOLD
            if a - SCROLL_RAMP <= t <= b + SCROLL_RAMP:
                if t < a:
                    r = min(r, smoothstep((a - t) / SCROLL_RAMP))
                elif t > b:
                    r = min(r, smoothstep((t - b) / SCROLL_RAMP))
                else:
                    return 0.0
        return r


# ---- rendering -------------------------------------------------------------

def render(inp, outp, cam, src_w, src_h):
    dec = subprocess.Popen(
        [FFMPEG, "-v", "error", "-i", inp,
         "-vf", f"fps={FPS},scale={OUT_W}:{OUT_H}:flags=lanczos",
         "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
        stdout=subprocess.PIPE)
    enc = subprocess.Popen(
        [FFMPEG, "-v", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-an",
         "-movflags", "+faststart", outp],
        stdin=subprocess.PIPE)

    frame_bytes = OUT_W * OUT_H * 3
    n = 0
    while True:
        buf = dec.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        t = n / FPS
        z, cx, cy = cam.at(t)
        if z <= 1.0005:
            enc.stdin.write(buf)
        else:
            im = Image.frombuffer("RGB", (OUT_W, OUT_H), buf, "raw",
                                  "RGB", 0, 1)
            cw, ch = OUT_W / z, OUT_H / z
            x0 = min(max(cx * OUT_W - cw / 2.0, 0.0), OUT_W - cw)
            y0 = min(max(cy * OUT_H - ch / 2.0, 0.0), OUT_H - ch)
            out = im.resize((OUT_W, OUT_H), Image.LANCZOS,
                            box=(x0, y0, x0 + cw, y0 + ch))
            enc.stdin.write(out.tobytes())
        n += 1
    dec.stdout.close()
    enc.stdin.close()
    dec.wait()
    enc.wait()
    if enc.returncode != 0:
        raise RuntimeError("ffmpeg encode failed")
    return n


def main():
    ap = argparse.ArgumentParser(description="punch-zoom framing renderer")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--timeline", help="sidecar timeline JSON")
    args = ap.parse_args()

    src_w, src_h, duration, src_fps = probe(args.input)

    if args.timeline:
        with open(args.timeline) as f:
            tl = json.load(f)
        # centers are optional in the sidecar — detect them if missing
        if not tl.get("punches") and (
                "input_center" not in tl or "answer_center" not in tl):
            det = detect_timeline(args.input, duration)
            tl.setdefault("input_center", det["input_center"])
            tl.setdefault("answer_center", det["answer_center"])
    else:
        tl = detect_timeline(args.input, duration)
        print("detected timeline:", json.dumps(tl))

    cam = PunchCamera(tl, duration) if tl.get("punches") else Camera(tl, duration)
    n = render(args.input, args.output, cam, src_w, src_h)
    print(f"rendered {n} frames -> {args.output}")


if __name__ == "__main__":
    main()
