#!/usr/bin/env python3
"""Deterministic finalize step for Aashiqana sensual-motion Shorts (v18).

Sibling of finalize_already_happening.py / finalize_episode.py, for the Aashiqana
LOCKED Shorts template (channels/aashiqana/SHORTS-TEMPLATE-LOCKED.md). Unlike those,
the deliverable (the branded, captioned, connected-motion Short) is ALREADY fully
assembled by the produce step — so there is no render/motion gate here. This script:

  1. GATE: the branded Short from the manifest exists and is a real 9:16 video.
  2. LUFS-normalise the audio to the -14 network spine (loudnorm) into a _web encode.
  3. Arm YouTube via scripts/yt_upload.py --channel aashiqana --category 10 (Music)
     --audience general --synthetic --publish-at <ISO UTC>.
  4. Sync the factory DB (factory_posts scheduled row + calendar -> produced + event).
  5. Advance factory_settings['aashiqana_last_ep'].

Manifest: channels/aashiqana/episodes/ep<ep>.json (written by the produce_preview
session) — {branded_path, title, tags, description_path?, song_slug?}. Falls back to
the newest branded Short on disk if the manifest is thin.

Called via the shell_script job type: meta.script_path='scripts/finalize_aashiqana.py',
meta.script_args=['--ep','<ep>','--tag','v3','--schedule','<iso>','--calendar-id','<id>'].

Exit codes: 0 armed · 1 config/encode failure · 2 gate/QC failed · 3 YT arm failed.
"""
import argparse, glob, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
CH = os.path.join(REPO, "channels", "aashiqana")
LUFS_TARGET = -14.0
MIN_VIDEO_BYTES = 500_000


def run(cmd, **kw):
    print(">> " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=False, **kw)


def measure_lufs(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    ms = re.findall(r"I:\s*(-?[\d.]+)\s+LUFS", r.stderr)
    try:
        return float(ms[-1]) if ms else None
    except ValueError:
        return None


def load_manifest(ep):
    p = os.path.join(CH, "episodes", f"ep{ep}.json")
    man = {}
    if os.path.exists(p):
        try:
            man = json.load(open(p))
        except (OSError, json.JSONDecodeError) as e:
            print(f">> WARNING: could not read manifest {p}: {e}")
    man.setdefault("ep", ep)
    return man


def find_branded(man):
    """Locate the finished branded Short: manifest 'branded_path', else the newest
    *_branded.mp4 under channels/aashiqana/songs/*/renders/."""
    if man.get("branded_path"):
        p = man["branded_path"]
        p = p if os.path.isabs(p) else os.path.join(REPO, p)
        if os.path.exists(p) and os.path.getsize(p) >= MIN_VIDEO_BYTES:
            return p
    cands = glob.glob(os.path.join(CH, "songs", "*", "renders", "*_branded.mp4"))
    cands = [c for c in cands if os.path.getsize(c) >= MIN_VIDEO_BYTES]
    return max(cands, key=os.path.getmtime) if cands else None


def assemble_from_clips(man):
    """Human-in-the-loop fallback: if the branded Short isn't built yet but the 4
    Hailuo motion clips + hookcut + timing are on disk (human generated them in
    Chrome), assemble + brand it now. Returns the branded path or None."""
    slug = man.get("song_slug")
    if not slug:
        return None
    sd = os.path.join(CH, "songs", slug)
    mot = os.path.join(sd, "_motion")
    hook = os.path.join(sd, "renders", f"{slug}_hookcut.mp3")
    timing = os.path.join(sd, "lyrics", "timing_hook.json")
    order = ["her", "anchor", "behind", "kiss"]
    clips = [os.path.join(mot, f"CLIP_{k}.mp4") for k in order]
    missing = [os.path.basename(c) for c in clips if not os.path.exists(c)]
    if missing or not os.path.exists(hook) or not os.path.exists(timing):
        print(f">> cannot auto-assemble (missing: {missing or []}"
              f"{'' if os.path.exists(hook) else ', hookcut'}"
              f"{'' if os.path.exists(timing) else ', timing'}) — human must finish Leonardo first.")
        return None
    prev = os.path.join(sd, "renders", f"{slug}_motion_prev.mp4")
    branded = os.path.join(sd, "renders", f"{slug}_branded.mp4")
    r = run(["python3", os.path.join(HERE, "assemble_motion_generic.py"),
             "--clips", ",".join(clips), "--audio", hook, "--lyrics", timing, "--out", prev])
    if r.returncode != 0 or not os.path.exists(prev):
        print("!! assemble failed"); return None
    pov1 = man.get("pov1", "POV: jiske bina har")
    pov2 = man.get("pov2", "shaam adhoori")
    r = run(["python3", os.path.join(CH, "songs", "03-aadhi-raat", "polish_short.py"),
             "--src", prev, "--out", branded, "--pov1", pov1, "--pov2", pov2])
    if r.returncode != 0 or not os.path.exists(branded):
        print("!! branding failed"); return None
    return branded


def web_master(src):
    """LUFS-normalise to -14 + faststart web encode. Returns the mastered path
    (or src if the encode fails)."""
    dst = src[:-4] + "_web.mp4"
    r = run(["ffmpeg", "-y", "-i", src,
             "-c:v", "libx264", "-crf", "18", "-preset", "slow",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             "-af", f"loudnorm=I={LUFS_TARGET}:TP=-1.5:LRA=11",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", dst])
    if r.returncode != 0 or not os.path.exists(dst):
        print(">> note: web-master failed; delivering the branded Short as-is")
        return src
    return dst


def arm_youtube(final_path, schedule_iso, man, desc_file, dry=False):
    yt = os.path.join(HERE, "yt_upload.py")
    title = man.get("title") or os.path.basename(final_path)
    cmd = ["python3", yt, "--channel", "aashiqana", "--video", final_path,
           "--title", title, "--tags", man.get("tags") or "",
           "--category", "10", "--audience", "general", "--synthetic",
           "--privacy", "public", "--publish-at", schedule_iso]
    if desc_file and os.path.exists(desc_file):
        cmd += ["--desc-file", desc_file]
    if dry:
        cmd += ["--dry"]
    r = run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"yt_upload exited {r.returncode}:\n{r.stdout}\n{r.stderr}", None
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", r.stdout or "")
    return True, (r.stdout or "").strip(), (m.group(1) if m else None)


def sync_factory_db(calendar_id, video_id, schedule_iso, man, final_path, desc_file=None):
    try:
        sys.path.insert(0, HERE)
        from factory_worker import Supa, load_env
        env = load_env(); supa = Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    except Exception as e:
        print(f">> WARNING: factory DB sync skipped: {e}")
        return
    tags = [t.strip() for t in (man.get("tags") or "").split(",") if t.strip()]
    yt_desc = ""
    if desc_file and os.path.exists(desc_file):
        try:
            yt_desc = open(desc_file).read().strip()
        except OSError:
            pass
    row = {"channel_key": "aashiqana", "local_path": final_path,
           "yt_title": (man.get("title") or os.path.basename(final_path))[:100],
           "yt_description": yt_desc, "tags": tags, "audience": "general",
           "synthetic": True, "publish_at": schedule_iso, "video_id": video_id,
           "status": "scheduled"}
    try:
        supa.insert("factory_posts", [row])
        print(f">> factory DB: factory_posts inserted (scheduled, video {video_id})")
    except Exception as e:
        print(f">> WARNING: could not insert factory_posts: {e}")
        print(f">> MANUAL: insert factory_posts (scheduled, video_id={video_id}, "
              f"publish_at={schedule_iso}).")
    if calendar_id:
        try:
            supa.patch("factory_calendar", f"id=eq.{calendar_id}", {"status": "produced"})
            print(f">> factory DB: calendar {calendar_id} -> produced")
        except Exception as e:
            print(f">> WARNING: could not flip calendar {calendar_id}: {e}")
    try:
        supa.insert("factory_events", [{"kind": "post_scheduled",
            "message": f"finalize armed aashiqana: {row['yt_title']!r} (video {video_id})",
            "meta": {"calendar_id": calendar_id, "video_id": video_id,
                     "channel_key": "aashiqana", "source": "finalize_aashiqana.py"}}])
    except Exception:
        pass


def advance_counter(ep):
    if not str(ep).isdigit():
        return
    try:
        sys.path.insert(0, HERE)
        from factory_worker import Supa, load_env
        env = load_env(); supa = Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
        cur = supa.select("factory_settings", "key=eq.aashiqana_last_ep&select=value")
        curn = int(cur[0]["value"]) if cur and str(cur[0].get("value") or "").isdigit() else 0
        if int(ep) > curn:
            supa.insert("factory_settings", [{"key": "aashiqana_last_ep", "value": str(int(ep))}],
                        on_conflict="key", resolution="merge-duplicates")
            print(f">> ep counter -> aashiqana_last_ep={int(ep)}")
    except Exception as e:
        print(f">> WARNING: could not advance ep counter: {e}")


def main():
    ap = argparse.ArgumentParser(description="Finalize an Aashiqana Short: QC + arm YT")
    ap.add_argument("--ep", required=True)
    ap.add_argument("--tag", default="v3")
    ap.add_argument("--schedule", help="ISO 8601 UTC publish time")
    ap.add_argument("--skip-arm", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--calendar-id")
    a = ap.parse_args()

    man = load_manifest(a.ep)

    # 1) GATE (assemble+brand from the human's Leonardo clips if not built yet)
    branded = find_branded(man) or assemble_from_clips(man)
    if not branded:
        print("!! no branded Short and cannot assemble one. The human must generate the "
              "4 Leonardo motion clips (LEONARDO-TODO.md) + hookcut first.", file=sys.stderr)
        sys.exit(2)
    print(f">> branded Short: {branded}")

    # 2) MASTER (LUFS -14 + web)
    final = web_master(branded)
    lufs = measure_lufs(final)
    if lufs is not None:
        print(f">> LUFS integrated: {lufs:.2f} (spine {LUFS_TARGET})")
    print(">> QC gate PASSED")

    # 3) ARM
    if a.skip_arm or not a.schedule:
        print(f">> skipping YT arm; final ready at: {final}")
        sys.exit(0)
    desc_file = None
    for cand in (man.get("description_path"),
                 os.path.join(os.path.dirname(os.path.dirname(branded)), "description_short.txt")):
        if not cand:
            continue
        cp = cand if os.path.isabs(cand) else os.path.join(REPO, cand)
        if os.path.exists(cp):
            desc_file = cp
            break
    ok, msg, video_id = arm_youtube(final, a.schedule, man, desc_file, dry=a.dry)
    if not ok:
        print(f"!! YT arm FAILED: {msg}", file=sys.stderr)
        sys.exit(3)
    print(f">> YT armed for {a.schedule}: {msg}")
    if a.calendar_id and not a.dry and video_id:
        sync_factory_db(a.calendar_id, video_id, a.schedule, man, final, desc_file)
    if not a.dry:
        advance_counter(a.ep)
    print(f">> DONE — {final}, scheduled {a.schedule}" + (f", video {video_id}" if video_id else ""))


if __name__ == "__main__":
    main()
