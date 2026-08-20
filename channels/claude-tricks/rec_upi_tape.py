#!/usr/bin/env python3
"""Beat 1 (ask) + beat 4 (answer) tape for episode _upi — filmed on the REAL
Claude Android app, natively, on the AVD.

WHY THE APP AND NOT THE WEB. claude.ai serves a Cloudflare "Verify you are
human" checkbox to Playwright (confirmed 2026-08-21 02:00 IST, Ray ID
a2e433167a96a70b, and again on 2026-08-20 16:49-16:52 where five sequential
__cf_chl_rt_tk challenges burned every retry in rec_upi_gate.py). Re-fingerprinting
the browser to slip past a bot wall is not something we do. The native app has
no such wall: it is the real signed-in Claude app on the owner's own account,
so nothing is being defeated -- the surface is simply the correct one.

WHAT THESE TWO CLIPS CARRY. Since pick.mp4 was retired (beat 0 is now the
designed TapStack hook), ask.mp4 is the ONLY place provenance is proven: the
viewer sees real screenshots attached to a real chat with no connector and no
login. These clips are load-bearing, not decorative.

REDACTION IS MANDATORY AND POST-PROCESS -- see locked_numbers.json "redaction":
solid drawbox plates, never blur (a blur on small type stays legible at video
bitrate and reads as something being hidden; a plate reads as deliberate).
Mask the "Alcohol (Liquor Fort)" category line, every person-to-person row, the
app's greeting name, and any UPI handles or account digits. The alcohol Rs 1,000
stays COUNTED in the denominator -- deleting real spending to get a better
number is the exact massaging this episode argues against.

The take is LONG on purpose. ScreenStage accepts a `from` prop (threaded by
build_ep_v2), so the beat window is selected in config; the tape only has to
CONTAIN the right 3.36s and 2.97s.

Usage:
  python3 rec_upi_tape.py            # full run
  python3 rec_upi_tape.py --probe    # dump the attach sheet and exit, film nothing
"""
import re
import subprocess
import sys
import time
from pathlib import Path

import rec_bc01_app as core  # sh / ui_text / type_text / mk / wait_for

CH = Path(__file__).resolve().parent
OUT = CH / "assets" / "ep_upi"
SP = Path("/private/tmp/claude-501/-Users-vijenderpanda-Ai-youtube-pipeline/"
          "b2fdbc7d-44b8-4f9f-9e97-025e976bb199/scratchpad")
SHOTS = sorted((SP / "upi_all").glob("upi_*.jpg"))
ADB = core.ADB

# char-for-char what episodes/_upi.v2.json desc_prompt and the pinned comment
# carry. locked_numbers.json "prompt".surfaces_must_match requires all four to
# be identical, and the first 50-word attempt FAILED (grouped by recipient and
# printed five real names), so this exact string is the one that was gate-tested.
PROMPT = (
    "My UPI history - the shots overlap so count each payment once, group by category, "
    "keep people as one line with no names, and tell me which app took the most."
)

core.OUT = OUT
marks = core.marks


def sh(*a, **k):
    return core.sh(*a, **k)


def bounds_of(rx, xml=None):
    x = xml if xml is not None else core.ui_text()
    m = re.search(rx + r'[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    if not m:
        return None
    x0, y0, x1, y1 = map(int, m.groups()[-4:])
    return ((x0 + x1) // 2, (y0 + y1) // 2)


def tap(x, y, wait=1.0):
    sh("input", "tap", str(x), str(y))
    time.sleep(wait)


def must(cond, msg):
    if not cond:
        print(f"!! ABORT: {msg}")
        try:
            sh("killall", "-2", "screenrecord")
        except Exception:
            pass
        sys.exit(3)


def fg_claude():
    return "com.anthropic.claude" in sh("dumpsys", "window")


def rec_start(name):
    """Record to /data/local/tmp, NOT /sdcard -- our own segment files must never
    show up in the app's media picker on camera (automation leak, 2026-08-16)."""
    p = subprocess.Popen([ADB, "shell", "screenrecord", "--time-limit", "175",
                          "--bit-rate", "12000000", f"/data/local/tmp/{name}.mp4"])
    core.REC_PROCS.append((name, p))
    core.mk(f"rec_{name}_t0")
    time.sleep(1.2)


def main():
    probe = "--probe" in sys.argv

    # ---- stage the real screenshots where the picker can see them ----------
    # /sdcard/Pictures IS media-indexed (unlike the recording path above) --
    # these are meant to be visible; they are the input the film is about.
    sh("rm", "-rf", "/sdcard/Pictures/UPI")
    sh("mkdir", "-p", "/sdcard/Pictures/UPI")
    for i, s in enumerate(SHOTS, 1):
        must(s.exists(), f"missing source screenshot {s}")
        dest = f"/sdcard/Pictures/UPI/upi_{i:02d}.jpg"
        subprocess.run([ADB, "push", str(s), dest], capture_output=True, timeout=90)
        # scan PER FILE. A MEDIA_MOUNTED broadcast re-indexes all of /sdcard and
        # drags our own screencaps into the picker -- that is the automation leak
        # bc02 documented on 2026-08-16, and it happened again here.
        sh("am", "broadcast", "-a",
           "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{dest}")
        time.sleep(0.6)
    time.sleep(2.5)
    print(f">> pushed {len(SHOTS)} real screenshots to /sdcard/Pictures/UPI")

    # ---- fresh chat --------------------------------------------------------
    # back out of anything left on top. force-stop only kills Claude; a system
    # photo picker from an aborted run survives it and steals the foreground.
    for _ in range(5):
        if fg_claude() and "com.google.android" not in sh("dumpsys", "window").split(
                "mCurrentFocus")[-1][:120]:
            break
        sh("input", "keyevent", "KEYCODE_BACK")
        time.sleep(1.0)
    sh("am", "force-stop", "com.anthropic.claude")
    time.sleep(2.0)
    sh("monkey", "-p", "com.anthropic.claude", "-c",
       "android.intent.category.LAUNCHER", "1")
    time.sleep(7)
    must(fg_claude(), "Claude app did not come to the foreground")

    xml = core.ui_text()
    # dismiss the model-usage nudge if it is up, it eats composer real estate
    close = bounds_of(r'content-desc="(?:Close|Dismiss)"', xml)
    if close:
        tap(*close, 0.8)
        xml = core.ui_text()

    # ALWAYS start a new chat. Relaunch reopens the last conversation, and this
    # tape must not be appended to the 3-shot run whose reply said Rs 1,843.
    nc = bounds_of(r'content-desc="(?:New chat|New conversation|Start new chat)"', xml)
    if nc:
        tap(*nc, 3.0)
        xml = core.ui_text()
    must("Chat with Claude" in xml or "What shall we" in xml,
         "not on a fresh chat screen -- refusing to append to an existing thread")

    if probe:
        plus = bounds_of(r'content-desc="(?:Add to chat|Add|Attach|Plus|Add attachment)"')
        print(">> composer plus:", plus)
        if plus:
            tap(*plus, 2.2)
            x = core.ui_text()
            (SP / "upi_attach_sheet.xml").write_text(x)
            tiles = re.findall(r'text="([^"]{2,24})"', x)
            print(">> attach sheet tiles:", tiles)
            sh("screencap", "-p", "/data/local/tmp/_probe.png")
            subprocess.run([ADB, "pull", "/data/local/tmp/_probe.png",
                            str(SP / "upi_attach_sheet.png")], capture_output=True)
            print(">> wrote upi_attach_sheet.png / .xml")
        return

    # ---- ASK: type the prompt, attach the shots, send ----------------------
    rec_start("upi_ask")
    core.mk("ask_t0")

    box = (bounds_of(r'text="Chat with Claude')
           or bounds_of(r'text="Reply to Claude')
           or bounds_of(r'class="android.widget.EditText"'))
    must(box is not None, "composer not found")
    tap(*box, 1.2)
    core.type_text(PROMPT)
    core.mk("prompt_typed")
    time.sleep(1.0)
    must("group by category" in core.ui_text(), "typed prompt not visible in composer")

    plus = bounds_of(r'content-desc="(?:Add to chat|Add|Attach|Plus|Add attachment)"')
    must(plus is not None, "attach (+) button not found -- no blind taps")
    tap(*plus, 2.4)
    core.mk("attach_open")

    x = core.ui_text()
    tile = (bounds_of(r'text="Photos"', x) or bounds_of(r'text="Gallery"', x)
            or bounds_of(r'text="Camera roll"', x) or bounds_of(r'text="Image"', x)
            or bounds_of(r'text="Media"', x))
    must(tile is not None,
         "attach sheet: no Photos/Gallery tile -- run --probe and read the dump")
    tap(*tile, 3.4)
    core.mk("picker_open")

    # select the three shots. The system photo picker exposes each item with a
    # content-desc carrying the filename on API 36.
    x = core.ui_text()
    dis = bounds_of(r'text="Dismiss"', x)
    if dis:
        tap(*dis, 1.0)
        x = core.ui_text()

    # THE LEAK CHECK IS ON THE MEDIA STORE, NOT THE GRID. uiautomator only dumps
    # the cells currently on screen, so counting tiles proves nothing. Ask the
    # provider how many images exist -- if anything but our shots is indexed it
    # would appear in the picker on camera (the 2026-08-16 leak).
    q = sh("content", "query", "--uri", "content://media/external/images/media",
           "--projection", "_display_name", timeout=40)
    names = re.findall(r"_display_name=(\S+)", q)
    must(len(names) == len(SHOTS),
         f"media store holds {len(names)} images ({names[:6]}), expected exactly "
         f"{len(SHOTS)} -- purge strays before filming")

    # the grid scrolls; tap every cell, scroll, repeat until all are selected
    picked, seen, guard = 0, set(), 0
    while picked < len(SHOTS) and guard < 20:
        guard += 1
        x = core.ui_text()
        cells = re.findall(r'content-desc="(Photo taken on [^"]*)"[^>]*'
                           r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
        fresh = 0
        for desc, x0, y0, x1, y1 in cells:
            # the picker's selection bar ("N | Preview | Done") floats over the
            # bottom ~300px. Tapping a cell under it hits the BAR, not the photo,
            # which is why the first attempt stalled at 3 selected.
            if int(y1) > 2050:
                continue
            key = (desc, x0, y0)
            if key in seen:
                continue
            seen.add(key)
            tap((int(x0) + int(x1)) // 2, (int(y0) + int(y1)) // 2, 0.5)
            picked += 1
            fresh += 1
            if picked >= len(SHOTS):
                break
        if picked >= len(SHOTS):
            break
        if fresh == 0:
            break
        sh("input", "swipe", "540", "1900", "540", "1150", "700")
        time.sleep(1.2)
    core.mk(f"picked_{picked}")
    must(picked == len(SHOTS),
         f"photo picker: selected {picked}/{len(SHOTS)} screenshots")

    conf = (bounds_of(r'text="Add"') or bounds_of(r'text="Done"')
            or bounds_of(r'content-desc="Done"') or bounds_of(r'text="Select"'))
    if conf:
        tap(*conf, 3.0)
    core.mk("attached")
    time.sleep(6.0)          # thumbnails must finish uploading before send
    must(fg_claude(), "not back in Claude after the picker")

    sb = bounds_of(r'content-desc="(?:Send|Send message)"')
    must(sb is not None, "send button not found -- no blind taps")
    tap(*sb, 1.0)
    core.mk("sent")
    print(">> sent; waiting for the reply")

    # ---- ANSWER: let it stream, then scroll it -----------------------------
    # NOT a keyword match -- the prompt itself contains "category", which fired
    # 2.1s after send last run and filmed a half-streamed reply. Wait for the UI
    # to stop changing instead.
    got, last, stable = False, "", 0
    for _ in range(75):
        time.sleep(4.0)
        cur = core.ui_text()
        if cur == last:
            stable += 1
            if stable >= 3:
                got = True
                break
        else:
            stable, last = 0, cur
    core.mk(f"reply_seen_{bool(got)}")
    time.sleep(6.0)
    sh("killall", "-2", "screenrecord")
    time.sleep(2.5)

    rec_start("upi_answer")
    core.mk("answer_t0")
    time.sleep(1.0)
    for _ in range(6):       # slow read-scroll through the grouped reply
        sh("input", "swipe", "540", "1750", "540", "900", "900")
        time.sleep(1.4)
    core.mk("scrolled")
    time.sleep(1.5)
    sh("killall", "-2", "screenrecord")
    time.sleep(3.0)

    # ---- pull + transcode --------------------------------------------------
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("upi_ask", "upi_answer"):
        subprocess.run([ADB, "pull", f"/data/local/tmp/{name}.mp4",
                        str(OUT / f"raw_{name}.mp4")], capture_output=True, timeout=180)
    (OUT / "tape_marks.json").write_text(
        __import__("json").dumps(marks, indent=2))

    # the full reply text, so the cut can be checked against locked_numbers.json
    (SP / "upi_reply.txt").write_text(core.ui_text())
    sh("screencap", "-p", "/data/local/tmp/_reply.png")
    subprocess.run([ADB, "pull", "/data/local/tmp/_reply.png", str(SP / "upi_reply.png")],
                   capture_output=True)
    print(">> marks:", marks)
    print(f">> raw tape -> {OUT}/raw_upi_ask.mp4 , raw_upi_answer.mp4")


if __name__ == "__main__":
    main()
