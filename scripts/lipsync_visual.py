#!/usr/bin/env python3
"""lipsync_visual — VISUAL lip-sync QC: do the LIPS move when the VOICE speaks?

Why this exists (VJ, 2026-08-15, bc01 v5 review): lipsync_align.py correlates the
clip's EMBEDDED AUDIO against the VO — that catches container audio shifts but is
structurally blind to the failure the viewer actually sees: HeyGen rendering the
mouth early/late relative to its own audio (the ledger records +123ms and +234ms
video offsets that shipped past the audio-only gate). This tool measures the lips
themselves.

Method (MediaPipe FaceMesh, pinned mediapipe==0.10.x for the bundled legacy model):
  1. Per frame: mouth aperture = |upper_lip(13) - lower_lip(14)| normalized by
     face height — a clean 30 Hz "how open is the mouth" signal.
  2. From the audio track: RMS envelope resampled to the same frame clock.
  3. Cross-correlate (z-scored, ±500 ms search): the lag that best aligns mouth
     movement with speech energy = the offset the VIEWER perceives.

Reading the numbers:
  visual_lag_ms  > 0 → lips move LATE (video behind audio); < 0 → lips early.
  corr           peak normalized correlation. Human sync-error detectability is
                 ~±45 ms (ITU-R BT.1359 puts acceptability at about −125…+45 ms;
                 lips-late is far more forgivable than lips-early).
Gate (BUILD-CLUB §7 gate 2, upgraded):
  PASS  |visual_lag_ms| <= 80 and corr >= 0.30
  WARN  |visual_lag_ms| <= 120                (write it down as a trade)
  FAIL  otherwise — fix with an in-point cut (lipsync_align.py cut), never ship.
  (corr < 0.15 with a detected face usually means the clip is NOT a talking-head
   segment for most of its length — measure the speaking window instead.)

Heavier option, researched and deliberately NOT plugged (2026-08-15): SyncNet /
Wav2Lip's LSE-C/LSE-D scorer is the academic gold standard, but it needs PyTorch
+ a ~50MB pretrained model + face-tracking pipeline — overkill for a single
fixed-framing synthetic host. Revisit if multi-face/real-footage channels need it.

Usage:
  python3 scripts/lipsync_visual.py CLIP.mp4 [CLIP2.mp4 ...] [--fps 30]
          [--start S] [--dur S] [--json out.json]
"""
import argparse, json, os, subprocess, sys, tempfile

import numpy as np


def mouth_signal(path, start, dur, fps):
    """Per-frame normalized mouth aperture via FaceMesh. Returns np.array (NaN = no face)."""
    import cv2
    import mediapipe as mp
    cap = cv2.VideoCapture(path)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or fps
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    n_frames = int(dur * src_fps) if dur else int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fm = mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1,
                                         refine_landmarks=False,
                                         min_detection_confidence=0.4)
    sig = []
    for _ in range(n_frames):
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        if w > 640:  # downscale for speed; landmarks are relative anyway
            frame = cv2.resize(frame, (640, int(h * 640 / w)))
        res = fm.process(np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        if not res.multi_face_landmarks:
            sig.append(np.nan)
            continue
        lm = res.multi_face_landmarks[0].landmark
        # 13/14 = inner upper/lower lip; 10/152 = forehead/chin (face height norm)
        aperture = abs(lm[13].y - lm[14].y) / max(abs(lm[10].y - lm[152].y), 1e-6)
        sig.append(aperture)
    cap.release()
    fm.close()
    return np.array(sig, dtype=float), src_fps


def audio_envelope(path, start, dur, n, sr_frame):
    """RMS envelope of the clip's audio resampled onto the video frame clock."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
        wav = t.name
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-i", path]
    if dur:
        cmd += ["-t", str(dur)]
    # aresample first_pts=0 materializes any container start-time offset as
    # leading silence — without it a delayed audio stream loses its delay on
    # extraction and the measurement goes blind to container-level desync.
    cmd += ["-af", "aresample=async=1:first_pts=0",
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav]
    subprocess.run(cmd, check=True)
    import wave
    w = wave.open(wav)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    w.close()
    os.unlink(wav)
    hop = int(16000 / sr_frame)
    m = (len(a) // hop) * hop
    env = np.sqrt((a[:m].reshape(-1, hop) ** 2).mean(axis=1))
    return env[:n]


def zscore(x):
    x = x - np.nanmean(x)
    s = np.nanstd(x)
    return x / s if s > 1e-9 else x


def measure(path, start, dur, fps):
    mouth, src_fps = mouth_signal(path, start, dur, fps)
    face_pct = float(np.mean(~np.isnan(mouth))) if len(mouth) else 0.0
    if face_pct < 0.3:
        return {"clip": path, "status": "no_face",
                "face_frames_pct": round(face_pct * 100, 1)}
    env = audio_envelope(path, start, dur, len(mouth), src_fps)
    n = min(len(mouth), len(env))
    mouth, env = mouth[:n], env[:n]
    # fill face gaps by interpolation so one dropped detection doesn't spike
    idx = np.arange(n)
    good = ~np.isnan(mouth)
    mouth = np.interp(idx, idx[good], mouth[good])
    m, e = zscore(mouth), zscore(env)
    max_lag = int(0.5 * src_fps)  # ±500 ms
    lags = range(-max_lag, max_lag + 1)
    corrs = []
    for L in lags:
        if L >= 0:
            a, b = m[L:], e[:n - L] if L else e
        else:
            a, b = m[:n + L], e[-L:]
        k = min(len(a), len(b))
        corrs.append(float(np.mean(a[:k] * b[:k])) if k > src_fps else -1)
    best = int(np.argmax(corrs))
    lag_frames = list(lags)[best]
    lag_ms = round(lag_frames * 1000.0 / src_fps, 1)
    corr = round(corrs[best], 3)
    verdict = ("PASS" if abs(lag_ms) <= 80 and corr >= 0.30 else
               "WARN" if abs(lag_ms) <= 120 and corr >= 0.15 else "FAIL")
    return {"clip": path, "status": "ok", "visual_lag_ms": lag_ms,
            "corr": corr, "face_frames_pct": round(face_pct * 100, 1),
            "frames": n, "verdict": verdict}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=0.0)
    ap.add_argument("--json", dest="out", default=None)
    a = ap.parse_args()
    results = []
    for c in a.clips:
        r = measure(c, a.start, a.dur, a.fps)
        results.append(r)
        if r["status"] != "ok":
            print(f"{os.path.basename(c):<24} {r['status']} (face {r.get('face_frames_pct')}%)")
        else:
            print(f"{os.path.basename(c):<24} lag {r['visual_lag_ms']:+7.1f} ms  "
                  f"corr {r['corr']:.3f}  face {r['face_frames_pct']:.0f}%  {r['verdict']}")
    if a.out:
        json.dump(results, open(a.out, "w"), indent=1)
        print(f">> {a.out}")


if __name__ == "__main__":
    main()
