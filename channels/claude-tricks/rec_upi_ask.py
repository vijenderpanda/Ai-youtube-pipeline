#!/usr/bin/env python3
"""ask.mp4 only — the composer loaded, then SEND tapped.

WHY THIS IS SEPARATE FROM rec_upi_tape.py. That script rolls the camera before
the attach, and the attach is slow: selecting 11 photos with a verify-every-tap
loop took 153 seconds, so `screenrecord --time-limit 175` ended 38 seconds
BEFORE the send. 174 seconds of tape, none of it the moment the beat needs.

The fix is structural, not a longer limit: do the slow work off camera, roll
only for the 6 seconds that matter. Beat 1 is 3.36s and shows exactly one thing
— real screenshots attached, the line sitting there, send tapped.

Numbers never appear in this beat, so it takes 3 screenshots rather than 11.
The reply that carries the numbers is a different beat and already filmed.
"""
import re
import subprocess
import sys
import time
from pathlib import Path

import rec_bc01_app as core

CH = Path(__file__).resolve().parent
OUT = CH / "assets" / "ep_upi"
SP = Path("/private/tmp/claude-501/-Users-vijenderpanda-Ai-youtube-pipeline/"
          "b2fdbc7d-44b8-4f9f-9e97-025e976bb199/scratchpad")
SHOTS = sorted((SP / "upi_all").glob("upi_*.jpg"))[:3]
ADB = core.ADB
PROMPT = (
    "My UPI history - the shots overlap so count each payment once, group by category, "
    "keep people as one line with no names, and tell me which app took the most."
)


def sh(*a, **k):
    return core.sh(*a, **k)


def bounds_of(rx, xml=None):
    x = xml if xml is not None else core.ui_text()
    m = re.search(rx + r'[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    if not m:
        return None
    g = list(map(int, m.groups()[-4:]))
    return ((g[0] + g[2]) // 2, (g[1] + g[3]) // 2)


def tap(x, y, w=1.0):
    sh("input", "tap", str(x), str(y))
    time.sleep(w)


def must(c, m):
    if not c:
        print(f"!! ABORT: {m}")
        sh("killall", "-2", "screenrecord")
        sys.exit(3)


def sel_count(xml=None):
    m = re.search(r'content-desc="(\d+) photos? or videos? selected"',
                  xml if xml is not None else core.ui_text())
    return int(m.group(1)) if m else 0


def main():
    sh("rm", "-rf", "/sdcard/Pictures/UPI")
    sh("mkdir", "-p", "/sdcard/Pictures/UPI")
    for i, s in enumerate(SHOTS, 1):
        dest = f"/sdcard/Pictures/UPI/upi_{i:02d}.jpg"
        subprocess.run([ADB, "push", str(s), dest], capture_output=True, timeout=90)
        sh("am", "broadcast", "-a",
           "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{dest}")
        time.sleep(0.5)
    time.sleep(2)

    for _ in range(4):
        sh("input", "keyevent", "KEYCODE_BACK")
        time.sleep(0.7)
    sh("am", "force-stop", "com.anthropic.claude")
    time.sleep(2)
    sh("monkey", "-p", "com.anthropic.claude", "-c",
       "android.intent.category.LAUNCHER", "1")
    time.sleep(7)

    xml = core.ui_text()
    c = bounds_of(r'content-desc="(?:Close|Dismiss)"', xml)
    if c:
        tap(*c, 0.8)
    box = bounds_of(r'text="Chat with Claude') or bounds_of(r'text="Reply to Claude')
    must(box is not None, "composer not found")
    tap(*box, 1.2)
    core.type_text(PROMPT)
    time.sleep(1.0)
    must("group by category" in core.ui_text(), "prompt not in composer")

    plus = bounds_of(r'content-desc="Add to chat"')
    must(plus is not None, "no attach button")
    tap(*plus, 2.4)
    t = bounds_of(r'text="Photos"')
    must(t is not None, "no Photos tile")
    tap(*t, 3.6)
    x = core.ui_text()
    d = bounds_of(r'text="Dismiss"', x)
    if d:
        tap(*d, 1.0)
    # 3 photos fit one screen, so no scroll and no re-tap hazard
    guard = 0
    while sel_count() < len(SHOTS) and guard < 14:
        guard += 1
        x = core.ui_text()
        before = sel_count(x)
        pts = []
        for n in re.findall(r'<node[^>]*content-desc="Photo taken on [^"]*"[^>]*>', x):
            b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', n)
            if b:
                x0, y0, x1, y1 = map(int, b.groups())
                if 260 < y0 and y1 < 2050:
                    pts.append(((x0 + x1) // 2, (y0 + y1) // 2))
        if before < len(pts):
            tap(*pts[before], 0.8)
    must(sel_count() == len(SHOTS), f"only {sel_count()}/{len(SHOTS)} selected")

    dn = bounds_of(r'text="Done"')
    must(dn is not None, "Done not found")
    tap(*dn, 3.0)
    # let the uploads finish COMPLETELY -- off camera, so it costs nothing
    prev, quiet = "", 0
    for _ in range(40):
        time.sleep(2.0)
        cur = core.ui_text()
        if cur == prev:
            quiet += 1
            if quiet >= 4:
                break
        else:
            quiet, prev = 0, cur
    sb = bounds_of(r'content-desc="(?:Send|Send message)"')
    must(sb is not None, "send button not found")

    # ---- ONLY NOW does the camera roll ------------------------------------
    p = subprocess.Popen([ADB, "shell", "screenrecord", "--time-limit", "20",
                          "--bit-rate", "12000000", "/data/local/tmp/ask.mp4"])
    time.sleep(2.2)          # a beat of the loaded composer before the tap
    tap(*sb, 0.2)
    time.sleep(4.5)          # the send lands and the bubble rises
    sh("killall", "-2", "screenrecord")
    time.sleep(2.5)
    p.wait(timeout=30)

    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([ADB, "pull", "/data/local/tmp/ask.mp4",
                    str(OUT / "raw_upi_ask.mp4")], capture_output=True, timeout=120)
    print(">> raw_upi_ask.mp4 pulled")


if __name__ == "__main__":
    main()
