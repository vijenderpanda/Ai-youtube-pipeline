#!/usr/bin/env python3
"""
Stitch a reusable intro + outro ("bookends") onto a finished episode.

  intro.mp4  ─┐
  episode.mp4 ├─►  [normalize each to a uniform target]  ─►  concat  ─►  out.mp4
  outro.mp4  ─┘

The three inputs may have DIFFERENT resolution / fps / codec / sample-rate, so we
never naive-concat them. Instead we:
  1. probe the EPISODE to learn the target spec (WxH + fps), and
  2. re-encode every segment to that uniform target: episode's WxH (letterbox-padded,
     never stretched), episode's fps, yuv420p, AAC 48000 Hz stereo, and
  3. loudness-normalize each segment to -14 LUFS integrated (EBU R128 loudnorm,
     measured two-pass so bookends and episode sit at exactly equal level), then
  4. join with the concat FILTER (decodes+reclocks everything in-graph — robust to
     re-encoded segments, no audio pops, no A/V desync), in a single final encode.

A missing intro OR outro is skipped with a warning (never a crash). If BOTH are
missing the episode is stream-copied to --out unchanged.

Convention (per channel):
  channels/<slug>/bookends/intro.mp4
  channels/<slug>/bookends/outro.mp4
(rendered separately, e.g. with scripts/assemble_video.py — see channels/BOOKENDS.md)

Usage:
  python3 scripts/add_bookends.py --channel vehicles \
      --episode channels/vehicles/renders/ep01_final.mp4 \
      --out     channels/vehicles/renders/ep01_bookended.mp4

  # path overrides / explicit skips:
  python3 scripts/add_bookends.py --channel vehicles \
      --episode channels/vehicles/renders/ep01_final.mp4 \
      --intro   path/to/other_intro.mp4 --outro-none \
      --out     channels/vehicles/renders/ep01_bookended.mp4
"""
import argparse, json, os, subprocess, sys
from ffmpeg_util import venc  # GPU (NVENC) encode when available, else libx264

# Repo root = parent of this scripts/ dir; channel paths resolve against it so the
# tool works regardless of the caller's CWD.
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# Fixed half of the target spec (the other half — WxH + fps — is probed from the
# episode so 9:16 Shorts channels like claude-tricks are handled too).
PIX_FMT = "yuv420p"
A_RATE = 48000          # Hz
A_CH = 2                # stereo
A_BITRATE = "192k"      # matches assemble_video.py add_audio()
# EBU R128 loudness target.
LUFS_I = -14.0          # integrated
LUFS_TP = -1.5          # true peak ceiling
LUFS_LRA = 11.0         # loudness range


def run(cmd):
    """Run a command, echoing it; raise CalledProcessError on non-zero exit.

    NB: never pipe ffmpeg through tail/grep — that would report the pager's exit
    status, not ffmpeg's, masking real failures. We surface the real code (see main).
    """
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def probe_video(path):
    """Return (width, height, fps_fraction_str) of the first video stream."""
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "json", path])
    st = json.loads(out)["streams"][0]
    return int(st["width"]), int(st["height"]), st.get("r_frame_rate", "30/1")


def probe_dur(path):
    """Container duration in seconds (matches assemble_video.py's helper)."""
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path])
    return float(out.strip())


def has_audio(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=index", "-of", "csv=p=0", path])
    return bool(out.strip())


def fps_float(frac):
    try:
        n, d = frac.split("/")
        return float(n) / float(d)
    except (ValueError, ZeroDivisionError):
        return float(frac)


def measure_loudness(path):
    """Two-pass loudnorm: measure a segment's integrated loudness (print_format=json).

    Returns a dict of measured_* params for a linear correction pass, or None if
    measurement fails (caller then falls back to single-pass dynamic loudnorm).
    """
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0",
           "-af", f"loudnorm=I={LUFS_I}:TP={LUFS_TP}:LRA={LUFS_LRA}:print_format=json",
           "-f", "null", "-"]
    print("+", " ".join(str(c) for c in cmd))
    p = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
    if p.returncode != 0:
        print(f"!! loudness measurement failed ({path}) — will use dynamic loudnorm")
        return None
    err = p.stderr
    try:
        blob = err[err.rindex("{"):err.rindex("}") + 1]
        j = json.loads(blob)
        return {
            "measured_I": j["input_i"],
            "measured_TP": j["input_tp"],
            "measured_LRA": j["input_lra"],
            "measured_thresh": j["input_thresh"],
            "offset": j["target_offset"],
        }
    except (ValueError, KeyError) as e:
        print(f"!! could not parse loudnorm JSON ({path}: {e}) — will use dynamic loudnorm")
        return None


def resolve_bookend(kind, override, none_flag, channel):
    """Resolve an intro/outro path. Returns a real existing path, or None (skip)."""
    if none_flag:
        print(f".. {kind}: skipped (--{kind}-none)")
        return None
    path = override or os.path.join(REPO, "channels", channel, "bookends", f"{kind}.mp4")
    if not os.path.isfile(path):
        where = "override path" if override else "default path"
        print(f"!! WARNING: {kind} not found at {where}: {path} — skipping {kind}")
        return None
    return path


def main():
    ap = argparse.ArgumentParser(description="Prepend intro + append outro onto an episode.")
    ap.add_argument("--channel", required=True, help="channel slug, e.g. vehicles")
    ap.add_argument("--episode", required=True, help="finished episode mp4 (defines target spec)")
    ap.add_argument("--out", required=True, help="output mp4")
    ap.add_argument("--intro", default="", help="override intro path (default channels/<slug>/bookends/intro.mp4)")
    ap.add_argument("--outro", default="", help="override outro path (default channels/<slug>/bookends/outro.mp4)")
    ap.add_argument("--intro-none", action="store_true", help="force-skip the intro")
    ap.add_argument("--outro-none", action="store_true", help="force-skip the outro")
    ap.add_argument("--crf", default="19", help="libx264 CRF for the final encode (default 19)")
    ap.add_argument("--preset", default="medium", help="libx264 preset (default medium)")
    args = ap.parse_args()

    if not os.path.isfile(args.episode):
        sys.exit(f"!! episode not found: {args.episode}")

    intro = resolve_bookend("intro", args.intro, args.intro_none, args.channel)
    outro = resolve_bookend("outro", args.outro, args.outro_none, args.channel)

    W, H, fps = probe_video(args.episode)
    print(f".. target spec from episode: {W}x{H} @ {fps} ({fps_float(fps):.3f} fps), "
          f"{PIX_FMT}, aac {A_RATE}Hz x{A_CH}, loudnorm I={LUFS_I} LUFS")

    # Ordered list of segments to stitch.
    segments = [s for s in (intro, args.episode, outro) if s]
    if segments == [args.episode]:
        # Nothing to add — stream-copy the episode through untouched (lossless, fast).
        print("!! no intro or outro available — copying episode to --out unchanged")
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        try:
            run(["ffmpeg", "-y", "-i", args.episode, "-c", "copy",
                 "-movflags", "+faststart", args.out])
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
        print(f">> DONE (no bookends): {args.out}")
        return

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    n = len(segments)
    afmt = f"aformat=sample_fmts=fltp:sample_rates={A_RATE}:channel_layouts=stereo"

    # Which segments lack an audio track (need synthetic silence to keep concat balanced)?
    needs_silence = [not (seg == args.episode or has_audio(seg)) for seg in segments]

    # Inputs: the n real segment files first (segment i -> input index i), then one
    # appended anullsrc per silent segment (in order) at indices n, n+1, ...
    inputs = []
    for seg in segments:
        inputs += ["-i", seg]
    silent_order = [i for i, s in enumerate(needs_silence) if s]
    for i in silent_order:
        dur = probe_dur(segments[i])
        print(f".. {os.path.basename(segments[i])} has no audio — filling {dur:.2f}s of silence")
        inputs += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"anullsrc=r={A_RATE}:cl=stereo"]

    # Build one filtergraph: normalize every segment, then concat once.
    filt = []
    concat_in = ""
    for i, seg in enumerate(segments):
        # Video: fit inside WxH without stretching, pad to exact WxH, lock sar/fps/pix_fmt.
        filt.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,"
            f"fps={fps},format={PIX_FMT}[v{i}]")

        # Audio: loudnorm to -14 LUFS (linear two-pass when we could measure), then
        # force 48k/stereo/fltp so the concat filter joins cleanly (no pops/desync).
        if needs_silence[i]:
            a_input = n + silent_order.index(i)
            filt.append(f"[{a_input}:a]{afmt}[a{i}]")
        else:
            m = measure_loudness(seg)
            ln = f"loudnorm=I={LUFS_I}:TP={LUFS_TP}:LRA={LUFS_LRA}"
            if m:
                ln += (f":measured_I={m['measured_I']}:measured_TP={m['measured_TP']}"
                       f":measured_LRA={m['measured_LRA']}:measured_thresh={m['measured_thresh']}"
                       f":offset={m['offset']}:linear=true")
            filt.append(f"[{i}:a]{ln},aresample={A_RATE},{afmt}[a{i}]")

        concat_in += f"[v{i}][a{i}]"

    filt.append(f"{concat_in}concat=n={n}:v=1:a=1[vout][aout]")

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", ";".join(filt),
        "-map", "[vout]", "-map", "[aout]",
        *venc(str(args.crf), args.preset),
        "-pix_fmt", PIX_FMT, "-r", fps,
        "-c:a", "aac", "-b:a", A_BITRATE, "-ar", str(A_RATE), "-ac", str(A_CH),
        "-movflags", "+faststart", args.out]

    ordered = " + ".join(("intro" if s == intro else "outro" if s == outro else "episode")
                         for s in segments)
    print(f".. stitching: {ordered}  ({n} segments)")
    try:
        run(cmd)
    except subprocess.CalledProcessError as e:
        # Surface ffmpeg's REAL exit code (never masked).
        sys.exit(e.returncode)

    total = probe_dur(args.out)
    print(f">> DONE: {args.out}  ({total:.2f}s, {ordered})")


if __name__ == "__main__":
    main()
