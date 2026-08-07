#!/usr/bin/env python3
"""Shared ffmpeg encoder selection — transparently uses NVIDIA NVENC when present.

Every assembly script builds its ffmpeg command with an inline
``"-c:v", "libx264", "-crf", CRF, "-preset", PRESET`` sequence. Import ``venc``
and splat it in place of those tokens:

    from ffmpeg_util import venc
    run(["ffmpeg", "-y", "-i", src, *venc("18", "slow"), "-pix_fmt", "yuv420p", out])

On a machine with a working NVENC encoder (e.g. an RTX 3060) this returns an
``h264_nvenc`` command that offloads encoding to the GPU; everywhere else it
returns the original libx264 command, so behaviour is identical on machines
without an NVIDIA GPU.

Control with the env var ``FACTORY_FFMPEG_HWACCEL``:
    auto   (default) probe once; use NVENC only if a real test-encode succeeds
    nvenc  same as auto (probe-gated)
    force  use NVENC without probing (for when you KNOW it works)
    cpu    always libx264 (also: none/off/0)

``FACTORY_FFMPEG`` overrides the ffmpeg binary path (handy on Windows).
"""
import os
import shutil
import subprocess

FFMPEG = os.environ.get("FACTORY_FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"

_CACHE = None  # None = not yet probed; True/False = NVENC usable


def _mode():
    return (os.environ.get("FACTORY_FFMPEG_HWACCEL", "auto") or "auto").strip().lower()


def _probe_nvenc():
    """Real 0.2s test-encode to /dev/null. True only if the GPU actually encodes.

    Listing the encoder (``-encoders``) is not enough — the encoder can be
    compiled in while the driver/GPU is unavailable, which fails at runtime.
    """
    try:
        r = subprocess.run(
            [FFMPEG, "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", "color=c=black:s=64x64:r=5:d=0.2",
             "-c:v", "h264_nvenc", "-f", "null", "-"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def nvenc_available():
    """Whether the encoder tokens will use NVENC, honouring env + a cached probe."""
    global _CACHE
    m = _mode()
    if m in ("cpu", "none", "off", "0", "libx264"):
        return False
    if m == "force":
        return True
    if _CACHE is None:
        _CACHE = _probe_nvenc()
    return _CACHE


def _nv_preset(x264_preset):
    """Map a libx264 preset to an NVENC quality preset (p1 fastest … p7 slowest)."""
    p = (x264_preset or "medium").lower()
    if p in ("ultrafast", "superfast", "veryfast", "faster", "fast"):
        return "p4"
    if p in ("slow", "slower", "veryslow"):
        return "p6"
    return "p5"  # medium / unknown


def venc(crf="18", preset="medium"):
    """Video-codec + quality tokens for an ffmpeg command.

    Splat with ``*venc(...)`` exactly where a script had
    ``"-c:v","libx264","-crf",crf,"-preset",preset``. A trailing
    ``"-pix_fmt","yuv420p"`` (if the caller has one) stays valid for both paths.
    ``crf`` maps to NVENC constant-quality ``-cq`` (near-equivalent perceptual
    target); bitrate stays uncapped (``-b:v 0``) so quality, not size, is fixed.
    """
    crf = str(crf)
    if nvenc_available():
        return ["-c:v", "h264_nvenc", "-preset", _nv_preset(preset),
                "-tune", "hq", "-rc", "vbr", "-cq", crf, "-b:v", "0"]
    return ["-c:v", "libx264", "-crf", crf, "-preset", preset or "medium"]


def label():
    return "h264_nvenc (GPU)" if nvenc_available() else "libx264 (CPU)"


if __name__ == "__main__":
    # Quick self-report: `python3 scripts/ffmpeg_util.py`
    print(f"ffmpeg:   {FFMPEG}")
    print(f"mode:     FACTORY_FFMPEG_HWACCEL={_mode()}")
    print(f"encoder:  {label()}")
    print(f"example:  ffmpeg ... {' '.join(venc('18', 'slow'))} -pix_fmt yuv420p out.mp4")
