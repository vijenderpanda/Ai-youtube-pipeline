#!/usr/bin/env python3
"""BC01 Android-app shoot, segment A: the REAL Claude app interview.

Mechanics verified live on the AVD (2026-08-13): tap composer, `input text`
(ASCII, %s for spaces), SHIFT+ENTER newline via `input keycombination 59 66`,
orange send button tapped by coordinate from the UI dump. Records via chained
`screenrecord` segments (3-min cap each), pulls them after, writes marks.

  python3 channels/claude-tricks/rec_bc01_app.py
"""
import json
import re
import subprocess
import time
from pathlib import Path

ADB = str(Path.home() / "Library/Android/sdk/platform-tools/adb")
OUT = Path(__file__).resolve().parent / "assets" / "bc01"
PROMPT = (OUT / "SHARE-PROMPT.txt").read_text().splitlines()

ANSWERS = [
    "Anita's Tiffin",
    "Home-style tiffin meals. Rajma Chawal Rs 120, Paneer Thali Rs 150, Dal + 4 Roti Rs 90",
    "Working folks and students in Indiranagar, Bengaluru - lunch and dinner",
    "99999 99999",
    "warm & homely",
    "Fresh ghar-ka-khana cooked the same morning. Free delivery within 3 km. Order by 10 AM for lunch.",
]

marks = {}
T0 = time.time()
REC_PROCS = []


def sh(*args, timeout=30):
    return subprocess.run([ADB, "shell", *args], capture_output=True,
                          text=True, timeout=timeout).stdout


def mk(k):
    marks[k] = round(time.time() - T0, 2)


def rec_start(name):
    p = subprocess.Popen(
        [ADB, "shell", "screenrecord", "--time-limit", "175",
         "--bit-rate", "12000000", f"/sdcard/{name}.mp4"])
    REC_PROCS.append((name, p))
    marks[f"rec_{name}_t0"] = round(time.time() - T0, 2)
    time.sleep(1.2)


def rec_stop():
    sh("killall", "-2", "screenrecord")
    time.sleep(2)


def ui_text():
    sh("uiautomator", "dump", "/sdcard/ui.xml", timeout=25)
    return sh("cat", "/sdcard/ui.xml", timeout=25)


def esc(t):
    """adb input text escaping: space -> %s, quote/paren/etc backslashed."""
    out = t.replace("\\", "\\\\").replace("%", "\\%")
    for ch in "()<>|;&*~\"'`$":
        out = out.replace(ch, "\\" + ch)
    return out.replace(" ", "%s")


def type_text(t):
    for chunk in [t[i:i + 120] for i in range(0, len(t), 120)]:
        sh("input", "text", esc(chunk), timeout=60)


def send_tap():
    """Find the send button from the dump (rightmost bottom button)."""
    x = ui_text()
    cands = re.findall(
        r'content-desc="(?:Send|Send message)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    if not cands:
        # fallback: fixed position measured on this AVD (keyboard open)
        sh("input", "tap", "954", "1396")
        return "fixed"
    x0, y0, x1, y1 = map(int, cands[-1])
    sh("input", "tap", str((x0 + x1) // 2), str((y0 + y1) // 2))
    return "desc"


def wait_for(rx, timeout=90, poll=3.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if re.search(rx, ui_text(), re.I | re.S):
            return True
        time.sleep(poll)
    return False


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # clear any residue in the composer
    sh("input", "tap", "540", "2088")
    time.sleep(1.5)
    sh("input", "keycombination", "113", "29")   # ctrl+a
    time.sleep(0.5)
    sh("input", "keyevent", "KEYCODE_DEL")
    time.sleep(0.8)

    # ---- SEG a1: prompt in + send + Q1 ----------------------------------
    rec_start("appA1")
    mk("prompt_type_start")
    for i, line in enumerate(PROMPT):
        if line:
            type_text(line)
        if i < len(PROMPT) - 1:
            sh("input", "keycombination", "59", "66")   # shift+enter
    mk("prompt_typed")
    time.sleep(1.2)
    print(">> send via", send_tap())
    mk("prompt_sent")
    ok = wait_for(r"business called|What'?s the business", timeout=60)
    print(">> Q1 seen:", ok)
    mk("q1_seen")
    time.sleep(2)

    # ---- answers (still seg a1; rec chain rolls) ------------------------
    for i, ans in enumerate(ANSWERS):
        if time.time() - T0 > 150 and f"rec_appA2_t0" not in marks:
            rec_stop()
            rec_start("appA2")
        sh("input", "tap", "540", "2088")
        time.sleep(1.0)
        mk(f"a{i + 1}_start")
        type_text(ans)
        time.sleep(0.5)
        send_tap()
        mk(f"a{i + 1}_sent")
        nxt = [r"sell or offer", r"who is it for|area", r"whatsapp",
               r"vibe|homely", r"mention|timings|tagline",
               r"index\.html|creating|building your"][i]
        wait_for(nxt, timeout=75)
        time.sleep(1.0)

    # ---- generation + hand-over ----------------------------------------
    if "rec_appA2_t0" not in marks:
        rec_stop()
        rec_start("appA2")
    mk("gen_wait")
    done = wait_for(r"download|index\.html", timeout=240, poll=5)
    print(">> generation done-ish:", done)
    mk("gen_done")
    # let it settle + then a third segment for the download exploration
    time.sleep(6)
    rec_stop()
    rec_start("appA3")
    sh("input", "swipe", "540", "1600", "540", "900", "400")
    time.sleep(2)
    subprocess.run([ADB, "exec-out", "screencap", "-p"],
                   stdout=open(OUT / "app_postgen.png", "wb"))
    mk("postgen_shot")
    # leave appA3 rolling — the download tap continues interactively
    (OUT / "tape_app.marks.json").write_text(json.dumps(marks, indent=1))
    print(json.dumps(marks, indent=1))
    print(">> appA3 still recording for the download pickup — drive it now")


if __name__ == "__main__":
    main()
