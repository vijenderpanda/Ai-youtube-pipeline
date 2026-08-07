#!/usr/bin/env python3
"""GPU / NVENC preflight for the factory worker.

Run on the worker machine to confirm the RTX (or any NVIDIA GPU) is actually
usable for video encoding, and to see the real speedup:

    python3 scripts/gpu_check.py

Reports: nvidia-smi, ffmpeg build + nvenc encoder, a live test-encode, and a
short libx264-vs-NVENC benchmark. Exit code 0 means NVENC works and the worker
will use it automatically (FACTORY_FFMPEG_HWACCEL=auto).
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ffmpeg_util as fu  # noqa: E402

G = "\033[1;32m"; R = "\033[1;31m"; Y = "\033[1;33m"; C = "\033[1;36m"; Z = "\033[0m"


def run_ok(cmd, timeout=120):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout, text=True)
        return p.returncode == 0, p.stdout
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)


def section(t):
    print(f"\n{C}── {t} {'─' * max(0, 40 - len(t))}{Z}")


def main():
    ff = fu.FFMPEG
    print(f"{C}Factory GPU preflight{Z}")
    print(f"ffmpeg binary: {ff}")

    section("NVIDIA driver (nvidia-smi)")
    ok, out = run_ok(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                      "--format=csv,noheader"])
    if ok:
        print(f"{G}✓ {out.strip()}{Z}")
    else:
        print(f"{Y}! nvidia-smi not found or no GPU. On Windows-native this is normal;")
        print(f"  what matters is whether ffmpeg's NVENC encoder works (below).{Z}")

    section("ffmpeg has the h264_nvenc encoder")
    ok, out = run_ok([ff, "-hide_banner", "-encoders"])
    has = ok and "h264_nvenc" in out
    print(f"{G}✓ h264_nvenc present{Z}" if has else
          f"{R}✗ h264_nvenc not in this ffmpeg build — install an NVENC-enabled ffmpeg{Z}")

    section("Live test-encode (0.2s to null)")
    works = fu._probe_nvenc()
    print(f"{G}✓ NVENC encodes successfully{Z}" if works else
          f"{R}✗ NVENC test-encode failed (driver/GPU unavailable){Z}")

    if works:
        section("Benchmark: 8s 1080p, libx264 vs NVENC")
        src = "-f lavfi -i testsrc=size=1920x1080:rate=30:duration=8".split()
        t0 = time.time()
        run_ok([ff, "-y", "-hide_banner", "-loglevel", "error", *src,
                "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-f", "null", "-"])
        cpu = time.time() - t0
        t0 = time.time()
        run_ok([ff, "-y", "-hide_banner", "-loglevel", "error", *src,
                "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "18",
                "-f", "null", "-"])
        gpu = time.time() - t0
        print(f"  libx264 medium : {cpu:5.1f}s")
        print(f"  h264_nvenc p5  : {gpu:5.1f}s")
        if gpu > 0:
            print(f"{G}  ≈ {cpu / gpu:.1f}× faster on the GPU{Z}")

    section("Verdict")
    print(f"  FACTORY_FFMPEG_HWACCEL={fu._mode()}  ->  encoder: {fu.label()}")
    if works:
        print(f"{G}✓ The worker will offload video encoding to the GPU automatically.{Z}")
        return 0
    print(f"{Y}! The worker will use CPU (libx264). It still runs correctly —")
    print(f"  just without GPU acceleration. Fix ffmpeg/driver above to enable NVENC.{Z}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
