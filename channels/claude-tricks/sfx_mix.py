#!/usr/bin/env python3
"""sfx_mix.py — synthesize the ep3 SFX kit and mix it onto a built master.

The manifest's film.sfx events carry @beatN+x anchors; beats resolve from the
MEASURED clock (the props file's segment durations), same rule as everything
else in the film pipeline. SFX ride ~9 dB under the -14 LUFS VO spine so they
punctuate without fighting the read.

Usage:
  python3 sfx_mix.py --manifest films/lpa.manifest.json \
      --props ../../renders_out/props_ep_lpa_draft.json \
      --video renders/ep_lpa_draft_outro.mp4 --out renders/ep_lpa_draft_sfx.mp4
"""
import argparse, json, re, subprocess, tempfile
from pathlib import Path
import numpy as np

SR = 48000

def env(n, a=0.004, r=0.12):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr and nr < n: e[-nr:] = np.linspace(1, 0, nr)
    return e

def noise(n): return np.random.default_rng(7).standard_normal(n)

def lowpass(x, cut):
    f = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR)
    f[fr > cut] *= np.exp(-(fr[fr > cut] - cut) / (cut * 0.5))
    return np.fft.irfft(f, len(x))

def tone(freq, dur, decay=6.0):
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)

def synth(name):
    if name == "knife_cut":
        n = int(0.22 * SR)
        wh = lowpass(noise(n), 2600) * env(n, 0.002, 0.16) * 0.5
        th = tone(95, 0.22, 14) * 0.9
        return wh + th
    if name == "digit_slam":
        return tone(52, 0.5, 5) * 1.0 + lowpass(noise(int(0.5 * SR)), 900) * env(int(0.5 * SR), 0.001, 0.4) * 0.25
    if name in ("tax_tick", "tax_tick_hard"):
        n = int(0.09 * SR)
        cl = lowpass(noise(n), 5200) * env(n, 0.001, 0.06) * 0.5 + tone(1050, 0.09, 30) * 0.4
        if name == "tax_tick_hard":
            low = tone(70, 0.2, 12) * 0.6
            out = np.zeros(max(len(cl), len(low)))
            out[:len(cl)] += cl * 1.25
            out[:len(low)] += low
            return out
        return cl
    if name == "whoosh_up":
        n = int(0.35 * SR)
        x = noise(n)
        sweep = np.interp(np.arange(n), [0, n], [500, 3800])
        f = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1 / SR)
        f[fr > 2200] *= 0.2
        x = np.fft.irfft(f, n) * env(n, 0.12, 0.1)
        return x * 0.45
    if name == "credit_chime":
        return (tone(523, 0.7, 4) + tone(659, 0.7, 4) * 0.8 + tone(784, 0.7, 4) * 0.6) * 0.4
    if name == "ring_close":
        n = int(0.6 * SR)
        wh = lowpass(noise(n), 3000) * env(n, 0.25, 0.2) * 0.3
        return wh + (tone(659, 0.6, 5) + tone(988, 0.6, 5) * 0.7) * 0.35
    # --- web-tour kit (reference cue map, wf1_r4: whoosh in VO gaps, pop ON
    # content, keys for terminal beats, ONE slam at ~85% runtime) ---
    if name == "pop":
        # broadband 60-6k thump, ~120ms — lands ON content (highlight hits)
        n = int(0.12 * SR)
        return (lowpass(noise(n), 6000) * env(n, 0.001, 0.09) * 0.45
                + tone(90, 0.12, 22) * 0.7 + tone(180, 0.12, 26) * 0.35)
    if name == "keys":
        # 5-hit high-freq click cluster over ~1.2s (terminal typing); the 5th
        # hit is broadband-capped like the reference run at 25.3-26.9s
        out = np.zeros(int(1.25 * SR))
        src = noise(len(out))
        for k, (t0, amp) in enumerate(
                [(0.0, .8), (.28, .7), (.55, .9), (.83, .75), (1.08, 1.0)]):
            n = int(0.05 * SR)
            cl = src[k * 977:k * 977 + n]
            cl = (cl - lowpass(cl, 3200)) * env(n, 0.001, 0.035)
            cl = cl / (np.abs(cl).max() or 1.0) * 0.75 * amp  # slam owns the ceiling
            i = int(t0 * SR)
            out[i:i + n] += cl
        i = int(1.08 * SR)
        out[i:i + int(0.12 * SR)] += tone(140, 0.12, 24) * 0.4
        return out
    if name == "slam":
        # stop-and-slam payoff: hardest broadband hit, low-heavy, ~350ms.
        # The 140ms of near-silence BEFORE it is authored by the MIX (--duck /
        # film.duck), never baked into the sample.
        n = int(0.35 * SR)
        return (tone(48, 0.35, 5) * 1.1 + tone(85, 0.35, 9) * 0.6
                + lowpass(noise(n), 1400) * env(n, 0.001, 0.3) * 0.4
                + lowpass(noise(n), 7000) * env(n, 0.001, 0.06) * 0.25)
    if name == "riser":
        # 1.2s noise+pitch riser INTO a hit — author the payoff hit as its own
        # event at riser.at + 1.2 (the riser hard-stops, it carries no impact)
        n = int(1.2 * SR)
        t = np.arange(n) / SR
        ramp = (t / t[-1]) ** 1.8
        f = 110 + 550 * (t / t[-1]) ** 1.4
        sweep = np.sin(2 * np.pi * np.cumsum(f) / SR)
        return (lowpass(noise(n), 5200) * ramp * 0.5
                + sweep * ramp * 0.35) * env(n, 0.05, 0.02)
    if name == "whoosh_down":
        # falling counterpart of whoosh_up: bright attack decaying into the low
        # band (fall-off transitions)
        n = int(0.38 * SR)
        x = noise(n)
        hi = x - lowpass(x, 1400)
        lo = lowpass(x, 900)
        fall = np.linspace(1, 0, n) ** 1.6
        rise = np.linspace(0.2, 1, n)
        return (hi * fall * 0.5 + lo * rise * 0.3) * env(n, 0.03, 0.14)
    return np.zeros(int(0.1 * SR))

TP_MAX = -1.0  # dBTP ship ceiling (PRODUCTION-PLAYBOOK)
LIMITER = "alimiter=limit=0.85:attack=3:release=60:level=false"

def measure_peak(path):
    """(true_peak_dBTP, integrated_LUFS) via ffmpeg loudnorm summary; (None, None) on parse fail."""
    out = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", path,
                          "-af", "loudnorm=print_format=summary", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    tp = re.search(r"Input True Peak:\s*([-+]?[\d.]+)", out)
    lu = re.search(r"Input Integrated:\s*([-+]?[\d.]+)", out)
    return (float(tp.group(1)) if tp else None, float(lu.group(1)) if lu else None)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--props", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gain_db", type=float, default=-9.0)
    ap.add_argument("--duck", default=None,
                    help='"t0,t1" — multiply the VIDEO\'s own audio by 0.06 in '
                         'that window before amix (the 140ms dead-stop device; '
                         'end it exactly on the slam). @beatN+x anchors allowed. '
                         'Falls back to film.duck in the manifest.')
    a = ap.parse_args()

    man = json.load(open(a.manifest))
    props = json.load(open(a.props))

    def find_segs(o):
        if isinstance(o, dict):
            if "segments" in o and isinstance(o["segments"], list):
                return o["segments"]
            for v in o.values():
                r = find_segs(v)
                if r is not None: return r
        if isinstance(o, list):
            for v in o:
                r = find_segs(v)
                if r is not None: return r
    segs = find_segs(props)
    starts = [0.0]
    for s in segs: starts.append(starts[-1] + s["dur"])
    total = starts[-1]

    def resolve(at):
        if isinstance(at, str) and at.startswith("@beat"):
            head, _, off = at[5:].partition("+")
            return starts[int(head)] + (float(off) if off else 0.0)
        return float(at)  # int/float/numeric string; garbage raises ValueError

    # probe video duration (film + outro; sfx only lands inside the film)
    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", a.video]).strip())
    mix = np.zeros(int(dur * SR) + SR)

    n_placed = 0
    for ev in man.get("film", {}).get("sfx", []):
        if "_note" in ev: continue
        t0 = resolve(ev["at"])
        if t0 >= total: continue
        # per-event gain_db = offset vs kit level (default 0). Relative levels
        # survive the global peak-normalize below; the loudest event (slam, by
        # design) sets the ceiling — exactly the reference's dynamics.
        w = synth(ev["name"]) * (10 ** (float(ev.get("gain_db", 0.0)) / 20))
        i = int(t0 * SR)
        if i >= len(mix): continue
        end = min(i + len(w), len(mix))
        mix[i:end] += w[: end - i]
        n_placed += 1
    peak = np.abs(mix).max() or 1.0
    mix = mix / peak * (10 ** (a.gain_db / 20))

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        import wave
        wv = wave.open(f.name, "w")
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
        wv.close()
        sfx_wav = f.name

    # --duck "t0,t1": the VIDEO's own audio (VO+bed, post-loudnorm) drops to
    # ~0.06x inside the window — the reference's 140ms dead-stop (45.65-45.79s)
    # before the 45.8s slam. Everything falls together (edit-master gap), which
    # is why this ducks input 0, not the bed alone.
    duck = a.duck or man.get("film", {}).get("duck")
    vsrc, note = "[0:a]", ""
    if duck:
        d0, d1 = (resolve(p.strip()) for p in str(duck).split(","))
        vsrc = (f"[0:a]volume=0.06:enable='between(t,{d0:.3f},{d1:.3f})'[da];"
                "[da]")
        note = f" | duck {d0:.2f}-{d1:.2f}s"
    subprocess.run([
        "ffmpeg", "-nostdin", "-loglevel", "error", "-y",
        "-i", a.video, "-i", sfx_wav,
        "-filter_complex", vsrc + "[1:a]amix=inputs=2:duration=first:normalize=0[am];"
        # TRUE-PEAK LIMITER (ship gate): the summed slam pushed _lpa to +0.6 dBTP
        # (spec <= -1 dBTP). Fast attack / 0.85 ceiling keeps AAC overshoot under
        # the line; the mix level (integrated LUFS) is untouched.
        "[am]" + LIMITER + "[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        a.out], check=True)
    print(f">> SFX: {n_placed} events mixed at {a.gain_db} dB{note} -> {a.out}")
    tp, lufs = measure_peak(a.out)
    flag = "PASS" if tp is not None and tp <= TP_MAX else "FAIL"
    print(f">> SFX peak gate: {lufs} LUFS / {tp} dBTP (limit {TP_MAX}) {flag}")
    if flag == "FAIL":
        raise SystemExit(f"!! true peak {tp} dBTP > {TP_MAX} after limiter — refusing to ship")

if __name__ == "__main__":
    main()
