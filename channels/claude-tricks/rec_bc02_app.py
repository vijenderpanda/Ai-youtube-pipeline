#!/usr/bin/env python3
"""BC02 Android-app shoot — Chapter 2: the MODEL + EFFORT dial, on camera.

Story beats recorded (chained screenrecord segs, native 1080x2400, dark theme,
demo status bar — preflight per VJ 2026-08-16):
  m1  open the model sheet showing Haiku 4.5 selected (yesterday's build),
      switch to Opus 5, open Effort -> High, close  == THE dial moment
  m2  type the crisp polish prompt, attach yesterday's index.html
      (/sdcard/Download), send
  m3  Opus asks its few prod-ready questions -> answer like a text
      (keyword-matched answer bank; unknown -> sensible default)
  m4  generation + the finished file on screen

Prereqs (script checks): AVD booted, Claude app foreground on a NEW chat with
model pre-set to Haiku 4.5 + Effort Medium (rec starts on the dial), demo
status bar on, file pushed. ASCII-only typing (adb input text).

  python3 channels/claude-tricks/rec_bc02_app.py
"""
import json
import re
import subprocess
import time
from pathlib import Path

import rec_bc01_app as core  # sh/type_text/send_tap/wait_for/rec chain

# record to a NON-media-indexed path: our own segment files must never appear
# in the Files picker on camera (automation leak caught 2026-08-16)
import subprocess as _sp, time as _t
def _rec_start(name):
    p = _sp.Popen([core.ADB, "shell", "screenrecord", "--time-limit", "175",
                   "--bit-rate", "12000000", f"/data/local/tmp/{name}.mp4"])
    core.REC_PROCS.append((name, p))
    core.marks[f"rec_{name}_t0"] = round(_t.time() - core.T0, 2)
    _t.sleep(1.2)
core.rec_start = _rec_start

CH = Path(__file__).resolve().parent
OUT = CH / "assets" / "bc02"
core.OUT = OUT
core.marks = {}
marks = core.marks

PROMPT_LINES = [
    "You built this website for me yesterday - the file is attached.",
    "Make it PRODUCTION-READY: a premium polish pass, and add an Ask Us Anything box that instantly answers customer questions in English and Hinglish using only the info on the page. Everything stays in this ONE index.html file - no backend, no signup.",
    "First, ask me up to 3 short questions - only the ones that matter most to get this business production-ready. One at a time.",
]

# keyword -> texted answer (Opus picks the questions; we match)
BANK = [
    (r"deliver|radius|area|km", "3 km around Indiranagar, free. Beyond that we say no politely"),
    (r"pay|payment|upi|cash", "UPI or cash on delivery. UPI id anitas.tiffin@upi"),
    (r"time|timing|hours|open|order by|cut.?off", "Order by 10 AM for lunch, 6 PM for dinner. Closed Sundays"),
    (r"veg|menu|dish|item", "Pure veg only. Menu rotates daily, the 3 listed are always on"),
    (r"photo|image|picture", "No photos yet - keep it clean without them"),
    (r"social|instagram|link", "Nothing yet - that is tomorrow's chapter, keep footer simple"),
]
DEFAULT_ANS = "Your call - keep it simple and honest"



def fg_claude():
    out = subprocess.run([core.ADB, "shell", "dumpsys", "window"],
                         capture_output=True, text=True).stdout
    return "com.anthropic.claude" in out.split("mCurrentFocus")[-1][:200]


def bounds_of(rx):
    x = core.ui_text()
    m = re.search(rx + r'[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    if not m:
        return None
    x0, y0, x1, y1 = map(int, m.groups())
    return (x0 + x1) // 2, (y0 + y1) // 2


def must(cond, why):
    if not cond:
        core.rec_stop()
        raise SystemExit(f"!! ABORT (no garbage frames): {why}")

def tap(x, y, pause=1.2):
    core.sh("input", "tap", str(x), str(y))
    time.sleep(pause)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # push yesterday's real file where the Files picker can see it
    src = CH / "assets" / "bc01" / "site" / "index.html"
    subprocess.run([core.ADB, "push", str(src), "/sdcard/Download/index.html"],
                   check=True, capture_output=True)
    core.sh("am", "broadcast", "-a",
            "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
            "-d", "file:///sdcard/Download/index.html")

    ui = core.ui_text()
    if "Haiku 4.5" not in ui:
        print("!! pre-set the composer model chip to Haiku 4.5 first "
              "(story: yesterday's model). Aborting before any frame records.")
        return

    # ---- m1: THE DIAL — Haiku -> Opus 5, Effort -> High ------------------
    chip = bounds_of(r'text="Haiku 4.5"')
    if chip is None:
        chip = (360, 2215)
    core.rec_start("appM1")
    time.sleep(2.0)
    core.mk("sheet_open")
    tap(chip[0], chip[1], 2.4)     # model chip -> sheet (Haiku checked)
    core.mk("sheet_shown")
    op = bounds_of(r'text="Opus 5"')
    must(op is not None, "model sheet: Opus 5 row not found")
    tap(op[0], op[1], 2.2)         # Opus 5 (sheet closes on select)
    core.mk("opus_selected")
    chip2 = bounds_of(r'text="Opus 5"') or (360, 2215)
    tap(chip2[0], chip2[1], 2.4)   # reopen -> Opus checked
    ef = bounds_of(r'text="Effort"')
    must(ef is not None, "model sheet: Effort row not found")
    tap(ef[0], ef[1], 2.2)
    core.mk("effort_open")
    # effort subsheet: pick High (dump-driven; rows are text nodes)
    x = core.ui_text()
    m = re.search(r'text="High"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    if m:
        x0, y0, x1, y1 = map(int, m.groups())
        tap((x0 + x1) // 2, (y0 + y1) // 2, 1.6)
    core.mk("effort_high")
    # close ONLY if the sheet is still up — a blind BACK exits the app
    xb = bounds_of(r'content-desc="(?:Close|Dismiss)"')
    if xb and "Select model" in core.ui_text():
        tap(xb[0], xb[1], 1.6)
    elif "Select model" in core.ui_text():
        tap(100, 1345, 1.6)
    time.sleep(1.2)

    # ---- m2: crisp prompt + attach + send --------------------------------
    must(fg_claude(), "Claude app not foreground before m2")
    cb = bounds_of(r'text="Chat with Claude')
    must(cb is not None, "composer not found")
    tap(cb[0], cb[1], 1.4)
    core.mk("prompt_type_start")
    for i, line in enumerate(PROMPT_LINES):
        core.type_text(line)
        if i < len(PROMPT_LINES) - 1:
            core.sh("input", "keycombination", "59", "66")  # shift+enter
    core.mk("prompt_typed")
    time.sleep(1.0)
    must("PRODUCTION" in core.ui_text(), "typed prompt not visible in composer")
    plus = bounds_of(r'content-desc="(?:Add|Attach|Plus)"') or (126, 2215)
    tap(plus[0], plus[1], 2.2)
    core.mk("attach_open")
    ft = bounds_of(r'text="Files"')
    must(ft is not None, "attach sheet: Files tile not found")
    tap(ft[0], ft[1], 3.2)
    core.mk("files_picker")
    # system picker: Documents tab -> index.html (Recents only shows media)
    dt = bounds_of(r'text="Documents"')
    if dt:
        tap(dt[0], dt[1], 2.5)
    x = core.ui_text()
    m = re.search(r'text="index\.html"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    if m:
        x0, y0, x1, y1 = map(int, m.groups())
        tap((x0 + x1) // 2, (y0 + y1) // 2, 3.0)
        core.mk("file_attached")
    else:
        must(False, "file picker: index.html not found")
    time.sleep(2.5)
    must(fg_claude(), "not back in Claude after file pick")
    sb = bounds_of(r'content-desc="(?:Send|Send message)"')
    must(sb is not None, "send button not found (no blind taps)")
    tap(sb[0], sb[1], 1.0)
    core.mk("prompt_sent")

    import sys as _sys
    if "--until-send" in _sys.argv:
        # leave appM1 recording chained into appM2; Q&A is driven manually
        core.rec_stop()
        core.rec_start("appM2")
        (OUT / "tape_app.marks.json").write_text(json.dumps(marks, indent=1))
        print(json.dumps(marks, indent=1))
        print(">> appM2 rolling — Q&A driven manually from here")
        return

    # ---- m3: Opus asks -> we answer like a text --------------------------
    core.rec_stop()
    core.rec_start("appM2")
    answered = 0
    for turn in range(8):
        # wait for either a question or the finished file
        t0 = time.time()
        while time.time() - t0 < 240:
            x = core.ui_text()
            if re.search(r"index\.html|Download", x, re.I):
                break
            if "?" in x[-1500:]:
                break
            time.sleep(4)
        x = core.ui_text()
        if re.search(r"index\.html|Download", x, re.I) and answered >= 1:
            break
        tail = x[-2000:]
        ans = DEFAULT_ANS
        for rx, a in BANK:
            if re.search(rx, tail, re.I):
                ans = a
                break
        tap(540, 2088, 1.0)
        core.mk(f"ans{answered + 1}_start")
        core.type_text(ans)
        time.sleep(0.6)
        core.send_tap()
        core.mk(f"ans{answered + 1}_sent")
        answered += 1
        if answered >= 4:
            break
        time.sleep(6)

    # ---- m4: generation --------------------------------------------------
    core.rec_stop()
    core.rec_start("appM3")
    core.mk("gen_wait")
    done = core.wait_for(r"Download|index\.html", timeout=600, poll=6)
    print(">> generation done-ish:", done)
    core.mk("gen_done")
    time.sleep(8)
    subprocess.run([core.ADB, "exec-out", "screencap", "-p"],
                   stdout=open(OUT / "app_postgen.png", "wb"))
    (OUT / "tape_app.marks.json").write_text(json.dumps(marks, indent=1))
    print(json.dumps(marks, indent=1))
    print(">> appM3 rolling — download pickup is driven next")


if __name__ == "__main__":
    main()
