#!/usr/bin/env python3
"""
style_steal.py — point it at a channel, get back everything you need to study
how that creator actually builds a video.

    python3 scripts/style_steal.py @Sanji_Chien --n 8

For each of the channel's top-N shorts by view count it produces:
  subs/<id>.txt      timecoded transcript, rolling-caption duplicates removed
  video/<id>.mp4     the source file
  sheets/<id>.jpg    a 30-frame contact sheet, 6x5, so you can read the cut
  sheets/HOOK_<id>.jpg   the first 6 seconds at 4fps — where the hook craft is
  INDEX.md           views, duration, and links, sorted

Everything lands under research/swipe-<handle>/.

Why a contact sheet and not "watch the video": a grid makes the *structure*
legible at a glance — how often the frame changes, where the host is, what the
type does — which is exactly what you cannot see while being entertained by it.

Requires: yt-dlp, ffmpeg (both already in this repo's toolchain).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def resolve(handle: str) -> str:
    h = handle if handle.startswith("@") else "@" + handle
    return f"https://www.youtube.com/{h}"


def list_shorts(url: str, n: int):
    """Flat-list the shorts tab and take the top n by view count."""
    r = sh(["yt-dlp", "--flat-playlist", "--dump-json", f"{url}/shorts"])
    rows = []
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append(
            {
                "id": d.get("id"),
                "title": (d.get("title") or "").strip(),
                "views": d.get("view_count") or 0,
            }
        )
    rows.sort(key=lambda x: -x["views"])
    return rows[:n], len(rows)


VTT_TS = re.compile(r"(\d\d:\d\d:\d\d\.\d\d\d) --> (\d\d:\d\d:\d\d\.\d\d\d)")


def vtt_to_text(path: Path) -> str:
    """YouTube auto-captions roll: each cue repeats the previous line. Strip that
    or the transcript triples in length and every word-count is wrong."""
    segs, seen = [], ""
    for blk in path.read_text(encoding="utf-8", errors="replace").split("\n\n"):
        m = VTT_TS.search(blk)
        if not m:
            continue
        txt = re.sub(r"<[^>]+>", "", blk[m.end():]).strip()
        txt = " ".join(l.strip() for l in txt.split("\n") if l.strip())
        txt = re.sub(r"align:\S+\s*", "", txt)
        txt = re.sub(r"position:\S+\s*", "", txt).strip()
        if not txt or txt == seen:
            continue
        if seen and txt.startswith(seen):
            txt = txt[len(seen):].strip()
        if not txt:
            continue
        segs.append((m.group(1)[3:], txt))
        seen = txt
    out, buf, mark = [], [], None

    def secs(t):
        mm, ss = t.split(":")
        return int(mm) * 60 + float(ss)

    for t, x in segs:
        if mark is None:
            mark = t
        buf.append(x)
        if secs(t) - secs(mark) >= 10:
            out.append(f"[{mark}] " + " ".join(buf))
            buf, mark = [], None
    if buf:
        out.append(f"[{mark or '00:00.000'}] " + " ".join(buf))
    return "\n".join(out)


def duration(p: Path) -> float:
    r = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(p)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("handle")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    url = resolve(a.handle)
    slug = a.handle.lstrip("@").lower()
    root = Path(a.out or f"channels/claude-tricks/research/swipe-{slug}")
    for d in ("subs", "video", "sheets"):
        (root / d).mkdir(parents=True, exist_ok=True)

    print(f"> {url}")
    picks, total = list_shorts(url, a.n)
    if not picks:
        sys.exit("no shorts found — check the handle")
    print(f"ok  {total} shorts found — taking top {len(picks)} by views")

    index = []
    for i, v in enumerate(picks, 1):
        vid = v["id"]
        print(f"> [{i}/{len(picks)}] {vid}  {v['views']:,} views")

        sh(["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
            "--sub-langs", "en.*", "--sub-format", "vtt",
            "-o", str(root / "subs" / "%(id)s.%(ext)s"),
            f"https://www.youtube.com/watch?v={vid}"])
        words = 0
        for cand in sorted((root / "subs").glob(f"{vid}*.vtt")):
            if cand.name.endswith(".en.vtt") or ".en-" not in cand.name:
                txt = vtt_to_text(cand)
                (root / "subs" / f"{vid}.txt").write_text(txt)
                words = len(txt.split())
                break
        print(f"  ok  transcript — {words} words")

        mp4 = root / "video" / f"{vid}.mp4"
        if not mp4.exists():
            sh(["yt-dlp", "-f", "bv*[height<=1280]+ba/b[height<=1280]",
                "--merge-output-format", "mp4", "-o", str(mp4),
                f"https://www.youtube.com/shorts/{vid}"])
        dur = duration(mp4)

        # 30 frames across the whole runtime — the cut, readable at a glance
        sh(["ffmpeg", "-v", "error", "-i", str(mp4),
            "-vf", f"fps=30/{max(dur,1):.3f},scale=260:-2,tile=6x5:margin=4:padding=4",
            "-frames:v", "1", "-q:v", "3", "-y", str(root / "sheets" / f"{vid}.jpg")])
        # and the first 6s at 4fps — hooks are decided here
        sh(["ffmpeg", "-v", "error", "-ss", "0", "-t", "6", "-i", str(mp4),
            "-vf", "fps=4,scale=300:-2,tile=6x4:margin=4:padding=4",
            "-frames:v", "1", "-q:v", "3", "-y", str(root / "sheets" / f"HOOK_{vid}.jpg")])
        print(f"  ok  contact sheet — {dur:.0f}s in 30 frames")
        index.append({**v, "dur": dur, "words": words})

    lines = [f"# swipe — {a.handle}", "", f"{total} shorts on the channel; top {len(picks)} below.", ""]
    lines.append("| views | dur | words | id | title |")
    lines.append("|---|---|---|---|---|")
    for v in index:
        lines.append(f"| {v['views']:,} | {v['dur']:.0f}s | {v['words']} | `{v['id']}` | {v['title'][:70]} |")
    (root / "INDEX.md").write_text("\n".join(lines) + "\n")

    print(f"ok  {len(index)} studied — {root}/INDEX.md")


if __name__ == "__main__":
    main()
