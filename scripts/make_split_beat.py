#!/usr/bin/env python3
"""
make_split_beat.py — pre-compose a SPLIT-SCREEN beat (screen on top, host below)
as a standalone 1080x1920 clip that a `rec:` beat can point at.

Why this exists (AI Unpacked Ep25 v3, 2026-08-05). The locked opening structure
(playbook §13) wants the host on camera early and "split-screen (host + screen)
where a beat benefits". Short.tsx CAN do a split — but only via the whole-episode
`newsSplit` layout, which needs one HeyGen host clip spanning the ENTIRE VO. On a
re-assembly (glue only, no regeneration) that clip does not exist and cannot be
made, so the split has to be baked into a source clip instead of asked of the
renderer. Geometry is copied from Short.tsx's newsSplit panes on purpose — a
split beat must read as the channel's existing grammar, not a new language.

HONESTY RULE. The host asset for a re-cut is lip-synced to the lines it was
rendered for. Playing it under a DIFFERENT VO line is fake lip-sync, which the
playbook bans outright (§6 / host_payoff_clip spec). So the host pane here is a
FROZEN, mouth-closed frame with a slow push — a still-host beat. `--host-at`
picks the frame; probe it, don't guess.

  python3 scripts/make_split_beat.py \
      --screen channels/claude-tricks/assets/ep25/demo_queue_live.mp4 --screen-at 9.85 \
      --host   channels/claude-tricks/assets/ep25/host_payoff.mp4      --host-at 1.20 \
      --dur 4.389 --out channels/claude-tricks/assets/ep25/split_setup.mp4

--- v4 additions (AI Unpacked Ep25 v4, 2026-08-05) --------------------------
`--host-live` : when the host clip IS lip-synced to the very line this beat
plays under, the frozen pane is no longer the honest option — it is just worse.
The pane then carries the host's REAL motion, sample-aligned to the beat
(host in-point = beat in-point), so the lips match the VO exactly. Only pass
this when the host asset was rendered from this line's audio; otherwise the
default freeze is the correct behaviour and the ban still applies.

`--lead-full S` : hold the host FULL-FRAME for the first S seconds of the beat,
then cut to the split for the rest. Playbook §13's locked opening wants the host
on camera full-frame right after the title card, while narrate-what-you-see
(§1.4) wants the thing the VO names visible when it is named. On a line that
does both ("That's the real board." / "Every green tile…") one beat can serve
both: full-frame for the first sentence, split from the word that points at the
screen. S is derived from the VO word onset, never eyeballed.

  python3 scripts/make_split_beat.py --host-live --lead-full 1.312 \
      --screen channels/claude-tricks/assets/ep25/demo_queue_live.mp4 --screen-at 11.60 \
      --host   channels/claude-tricks/assets/ep25/v2_setup.mp4        --host-at 0.0 \
      --dur 4.389 --out channels/claude-tricks/assets/ep25/setup_beat.mp4
"""
import argparse, os, shutil, subprocess

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
W, H = 1080, 1920

# --- newsSplit geometry, mirrored from remotion-studio/src/Short.tsx ----------
# the host lives in the bottom pane behind a magenta top border; the screen gets
# the rest. 1050/6/864 keeps the divider on an even pixel row for yuv420p.
TOP_H, RULE_H = 1050, 6
BOT_Y = TOP_H + RULE_H          # 1056
BOT_H = H - BOT_Y               # 864
MAG = "0xE0218A"

# --- host pane framing --------------------------------------------------------
# Region of the 1080x1920 host frame that becomes the bottom pane. 780x624 is
# exactly the pane's 1.25 aspect, so the scale is uniform (no distortion), and
# it lands a chest-up shot with the face on the right third — the same framing
# the full-frame host beat uses, just cropped in.
HOST_CROP = (300, 300, 780, 624)   # x, y, w, h
PUSH = 0.045                        # slow 1.000 -> 1.045 drift over the beat


def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def build_live(screen, screen_at, host, host_at, dur, out, fps=30,
               host_crop=HOST_CROP, lead_full=0.0, screen_y=0):
    """LIVE host pane (+ optional full-frame lead). One ffmpeg pass, so the cut
    from full-frame to split is frame-exact and there is no intermediate encode.

    The host clip is tpad/clone-extended by 1s before trimming: a HeyGen render
    can land a few frames short of the VO line it was made from (here 4.28s of
    clip for a 4.389s beat) and a missing tail would otherwise silently shorten
    the beat and desync every later segment. The padded frames are the clip's
    own mouth-closed last frame.
    """
    hx, hy, hw, hh = host_crop
    S = round(float(lead_full), 3)
    assert 0 <= S < dur, f"--lead-full {S} must be inside the beat ({dur}s)"
    split_dur = round(dur - S, 3)

    parts = []
    fc = [
        # host: normalise to the episode fps, then clone-extend so the trims below
        # can never run off the end of a short render.
        f"[0:v]fps={fps},setsar=1,tpad=stop_mode=clone:stop_duration=1,"
        f"format=yuv420p,split=2[hv1][hv2]",
        # bottom pane: 1:1 crop of the host frame, uniformly scaled into the pane
        # (780x624 is exactly the pane's 1.25 aspect). No push — the pane already
        # carries real motion, and a camera drift on top of it reads as a wobble.
        f"[hv2]trim=start={host_at + S}:end={host_at + dur},setpts=PTS-STARTPTS,"
        f"crop={hw}:{hh}:{hx}:{hy},scale={W}:{BOT_H}:flags=lanczos,setsar=1[hostp]",
        # screen pane: 1:1 crop of the frame — no rescale, so every dashboard
        # label stays exactly as legible as in the full-frame beat. `screen_y`
        # slides the 1050px window down: the default 0 keeps the top of the page,
        # but the thing the VO names is not always at the top (Ep25 v4: the green
        # filmstrip tiles sit at y 930-1140, i.e. sliced in half by a top-aligned
        # pane). Pick it from measured ink, not by eye.
        f"[1:v]fps={fps},setsar=1,trim=start={screen_at}:end={screen_at + split_dur},"
        f"setpts=PTS-STARTPTS,crop={W}:{TOP_H}:0:{screen_y}[scr]",
        f"color=c={MAG}:s={W}x{H}:d={split_dur}:r={fps},format=rgb24[bg]",
        "[bg][scr]overlay=0:0:shortest=0[sa]",
        f"[sa][hostp]overlay=0:{BOT_Y}:shortest=1,format=yuv420p[split]",
    ]
    if S > 0:
        fc.append(f"[hv1]trim=start={host_at}:end={host_at + S},"
                  f"setpts=PTS-STARTPTS,format=yuv420p[lead]")
        fc.append("[lead][split]concat=n=2:v=1:a=0[v]")
    else:
        fc.append("[hv1]nullsink")
        fc.append("[split]null[v]")
    run([FFMPEG, "-y", "-loglevel", "error", "-i", host, "-i", screen,
         "-filter_complex", ";".join(fc), "-map", "[v]",
         "-r", str(fps), "-frames:v", str(int(round(dur * fps))),
         "-c:v", "libx264", "-crf", "17", "-preset", "slow",
         "-pix_fmt", "yuv420p", out])
    print(f">> SPLIT(live) lead={S}s split={split_dur}s", out)
    return out


def build(screen, screen_at, host, host_at, dur, out, fps=30,
          host_crop=HOST_CROP, push=PUSH):
    tmp = out + ".host_still.png"
    run([FFMPEG, "-y", "-loglevel", "error", "-ss", str(host_at), "-i", host,
         "-frames:v", "1", tmp])

    hx, hy, hw, hh = host_crop
    nframes = int(round(dur * fps))
    # Supersample 2x, then zoompan for the slow push. Playbook §15: zoompan is
    # reserved for true push-ins on stills and must be fed a 2x-supersampled
    # source, which is exactly this case (the pane is a frozen frame).
    host_chain = (
        f"[1:v]scale={W*2}:{H*2}:flags=lanczos,"
        f"crop={hw*2}:{hh*2}:{hx*2}:{hy*2},"
        f"scale={W*2}:{BOT_H*2}:flags=lanczos,"
        f"zoompan=z='min({1+push},1+{push}*on/{max(nframes-1,1)})':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s={W}x{BOT_H}:fps={fps},setsar=1[host]"
    )
    # screen pane: 1:1 crop of the top of the frame — no rescale, so every
    # dashboard label stays exactly as legible as it is in the full-frame beat.
    screen_chain = f"[0:v]crop={W}:{TOP_H}:0:0,setsar=1,fps={fps}[scr]"
    fc = (
        f"{screen_chain};{host_chain};"
        f"color=c={MAG}:s={W}x{H}:d={dur}:r={fps},format=rgb24[bg];"
        f"[bg][scr]overlay=0:0:shortest=0[a];"
        f"[a][host]overlay=0:{BOT_Y}:shortest=0,format=yuv420p[v]"
    )
    run([FFMPEG, "-y", "-loglevel", "error",
         "-ss", str(screen_at), "-t", str(dur), "-i", screen,
         "-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", tmp,
         "-filter_complex", fc, "-map", "[v]",
         "-r", str(fps), "-frames:v", str(int(round(dur * fps))),
         "-c:v", "libx264", "-crf", "17", "-preset", "slow",
         "-pix_fmt", "yuv420p", out])
    os.remove(tmp)
    print(">> SPLIT", out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", required=True)
    ap.add_argument("--screen-at", type=float, required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--host-at", type=float, required=True)
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--host-live", action="store_true",
                    help="host pane carries the clip's REAL motion (only valid "
                         "when the host asset was lip-synced to THIS line)")
    ap.add_argument("--lead-full", type=float, default=0.0,
                    help="hold the host full-frame for the first N seconds, then "
                         "cut to the split (N from a VO word onset)")
    ap.add_argument("--screen-y", type=int, default=0,
                    help="y offset of the 1050px screen-pane window (default 0 = "
                         "top of the page)")
    a = ap.parse_args()
    if a.host_live or a.lead_full:
        assert a.host_live, "--lead-full is only implemented for --host-live"
        build_live(a.screen, a.screen_at, a.host, a.host_at, a.dur, a.out, a.fps,
                   lead_full=a.lead_full, screen_y=a.screen_y)
    else:
        build(a.screen, a.screen_at, a.host, a.host_at, a.dur, a.out, a.fps)
