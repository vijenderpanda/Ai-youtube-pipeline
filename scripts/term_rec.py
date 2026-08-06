#!/usr/bin/env python3
"""
Deterministic terminal recorder (replaces VHS for Claude Code tapes).

Drives a real PTY via pexpect with scheduled keystrokes, emulates the
terminal with pyte, renders frames with PIL (Menlo + Catppuccin Mocha to
match the existing episode look), assembles mp4 via ffmpeg. No ttyd/Chrome,
no time compression — frame timestamps are wall-clock accurate.

Usage:  python3 scripts/term_rec.py --script tapes/ep09.json --out out.mp4
Script JSON:
  {"cols":52,"rows":31,"fps":12,"cwd":"~/demo-project","cmd":"claude",
   "steps":[{"wait":13},{"type":"/model","cps":10},{"wait":1.5},{"key":"enter"},
            {"wait":5},{"key":"down"},{"key":"enter"},{"mark":"menu_done"}]}
"key" values: enter, esc, tab, shift-tab, up, down, left, right, ctrl-c, space, backspace
"mark" prints MARK <name> <t> to stdout (for beat calibration).
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time

import pexpect, pyte
from PIL import Image, ImageDraw, ImageFont

# Catppuccin Mocha
BG = "#1e1e2e"; FG = "#cdd6f4"
PALETTE = {
    "black": "#45475a", "red": "#f38ba8", "green": "#a6e3a1",
    "brown": "#f9e2af", "yellow": "#f9e2af", "blue": "#89b4fa",
    "magenta": "#f5c2e7", "cyan": "#94e2d5", "white": "#bac2de",
    "brightblack": "#585b70", "brightred": "#f38ba8", "brightgreen": "#a6e3a1",
    "brightbrown": "#f9e2af", "brightyellow": "#f9e2af", "brightblue": "#89b4fa",
    "brightmagenta": "#f5c2e7", "brightcyan": "#94e2d5", "brightwhite": "#a6adc8",
    "default": None,
}
KEYS = {
    "enter": "\r", "esc": "\x1b", "tab": "\t", "shift-tab": "\x1b[Z",
    "up": "\x1b[A", "down": "\x1b[B", "left": "\x1b[D", "right": "\x1b[C",
    "ctrl-c": "\x03", "space": " ", "backspace": "\x7f",
}

def color(v, default):
    if v in PALETTE:
        return PALETTE[v] or default
    if v and re.fullmatch(r"[0-9a-fA-F]{6}", v):
        return "#" + v
    return default

class QueryResponder:
    """Answer terminal capability queries so TUIs don't block waiting."""
    def __init__(self, child, screen):
        self.child, self.screen = child, screen
    def scan(self, data: bytes):
        out = b""
        if b"\x1b[6n" in data:  # CPR
            out += f"\x1b[{self.screen.cursor.y+1};{self.screen.cursor.x+1}R".encode()
        if b"\x1b[5n" in data:  # DSR
            out += b"\x1b[0n"
        if b"\x1b[>c" in data or b"\x1b[>0c" in data:  # DA2
            out += b"\x1b[>0;276;0c"
        elif b"\x1b[c" in data or b"\x1b[0c" in data:  # DA1
            out += b"\x1b[?62;22c"
        if b"\x1b]10;?" in data:  # OSC fg query
            out += b"\x1b]10;rgb:cdcd/d6d6/f4f4\x07"
        if b"\x1b]11;?" in data:  # OSC bg query
            out += b"\x1b]11;rgb:1e1e/1e1e/2e2e\x07"
        if out:
            try:
                self.child.send(out)
            except Exception:
                pass

class Renderer:
    def __init__(self, cols, rows, font_px, pad):
        self.cols, self.rows, self.pad = cols, rows, pad
        self.font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", font_px, index=0)
        try:
            self.bold = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", font_px, index=1)
        except Exception:
            self.bold = self.font
        self.cw = self.font.getlength("M")
        self.ch = int(font_px * 1.3)
        self.W = int(cols * self.cw + 2 * pad)
        self.H = int(rows * self.ch + 2 * pad)
        # even dims for yuv420p
        self.W += self.W % 2; self.H += self.H % 2
    def frame(self, screen, cursor_on=True):
        img = Image.new("RGB", (self.W, self.H), BG)
        d = ImageDraw.Draw(img)
        buf = screen.buffer
        for y in range(self.rows):
            row = buf[y]
            for x in range(self.cols):
                ch = row[x]
                if ch.data in ("", " ") and ch.bg == "default":
                    continue
                px, py = self.pad + x * self.cw, self.pad + y * self.ch
                fg = color(ch.fg, FG); bg = color(ch.bg, None)
                if ch.reverse:
                    fg, bg = (bg or BG), (fg or FG)
                if bg:
                    d.rectangle([px, py, px + self.cw, py + self.ch], fill=bg)
                if ch.data and ch.data != " ":
                    d.text((px, py), ch.data, fill=fg,
                           font=self.bold if ch.bold else self.font)
        if cursor_on and not screen.cursor.hidden:
            cx = self.pad + screen.cursor.x * self.cw
            cy = self.pad + screen.cursor.y * self.ch
            d.rectangle([cx, cy, cx + self.cw, cy + self.ch], fill=FG)
            c = buf[screen.cursor.y][screen.cursor.x]
            if c.data and c.data != " ":
                d.text((cx, cy), c.data, fill=BG, font=self.font)
        return img

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = json.load(open(a.script))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cols, rows = cfg.get("cols", 52), cfg.get("rows", 31)
    fps = cfg.get("fps", 12)
    font_px = cfg.get("font_px", 30)
    pad = cfg.get("pad", 28)

    screen = pyte.Screen(cols, rows)
    stream = pyte.ByteStream(screen)
    env = dict(os.environ, TERM="xterm-256color", COLUMNS=str(cols), LINES=str(rows))
    child = pexpect.spawn("/bin/bash", ["-lc", cfg.get("cmd", "claude")],
                          cwd=os.path.expanduser(cfg.get("cwd", ".")),
                          env=env, dimensions=(rows, cols), encoding=None, timeout=None)
    resp = QueryResponder(child, screen)
    rend = Renderer(cols, rows, font_px, pad)
    tmp = tempfile.mkdtemp(prefix="term_rec_")

    # dynamic step interpreter: steps advance on time OR on-screen text,
    # so variable claude boot/response latency can't desync the keystrokes.
    steps = list(cfg["steps"])
    max_dur = float(cfg.get("max_duration", 180))
    tail = float(cfg.get("tail", 1.0))

    def screen_text():
        return "\n".join(screen.display)

    si = 0                 # current step index
    step_started = None    # monotonic when current step became active
    type_pos = 0           # chars sent of a "type" step
    ku_presses = 0         # key presses fired in a "key_until" step
    ku_last = 0.0          # monotonic of last key_until press
    done_at = None         # monotonic when all steps finished
    t0 = time.monotonic()
    f = 0
    while True:
        target = t0 + f / fps
        while True:
            now = time.monotonic()
            # pump output first so wait_for sees fresh screen state
            try:
                data = child.read_nonblocking(65536, timeout=0)
                if data:
                    resp.scan(data)
                    stream.feed(data)
                    continue
            except pexpect.TIMEOUT:
                pass
            except (pexpect.EOF, OSError):
                pass
            # advance steps
            while si < len(steps):
                s = steps[si]
                if step_started is None:
                    step_started = now
                    type_pos = 0
                    ku_presses = 0
                    ku_last = 0.0
                el = now - step_started
                if "wait" in s:
                    if el < float(s["wait"]):
                        break
                elif "wait_for" in s:
                    if s["wait_for"] in screen_text():
                        pass  # found -> advance
                    elif el < float(s.get("timeout", 30)):
                        break
                    else:
                        print(f"WARN wait_for timeout: {s['wait_for']!r}", flush=True)
                elif "type" in s:
                    cps = float(s.get("cps", 10))
                    due = int(el * cps) + 1
                    while type_pos < min(due, len(s["type"])):
                        child.send(s["type"][type_pos].encode())
                        type_pos += 1
                    if type_pos < len(s["type"]):
                        break
                elif "key_until" in s:
                    # press key repeatedly (gap apart) until text appears
                    if s["text"] in screen_text():
                        pass  # found -> advance
                    elif ku_presses < int(s.get("max", 5)):
                        if now - ku_last >= float(s.get("gap", 1.2)):
                            child.send(KEYS[s["key_until"]].encode())
                            ku_presses += 1
                            ku_last = now
                        break
                    elif now - ku_last >= float(s.get("gap", 1.2)):
                        print(f"WARN key_until exhausted: {s['text']!r}", flush=True)
                    else:
                        break
                elif "key" in s:
                    child.send(KEYS[s["key"]].encode())
                elif "mark" in s:
                    print(f"MARK {s['mark']} {now - t0:.2f}", flush=True)
                si += 1
                step_started = None
            if si >= len(steps) and done_at is None:
                done_at = now
            if now >= target:
                break
            time.sleep(min(0.005, target - now))
        blink = (f // (fps // 2 if fps >= 2 else 1)) % 2 == 0
        fp = os.path.join(tmp, f"fr_{f:05d}.png")
        rend.frame(screen, cursor_on=blink).save(fp)
        f += 1
        # if rendering lags wall time, duplicate the frame to keep
        # video time == wall time (marks stay accurate)
        now = time.monotonic()
        while f < int((now - t0) * fps):
            shutil.copy(fp, os.path.join(tmp, f"fr_{f:05d}.png"))
            f += 1
        if (done_at and now - done_at >= tail) or now - t0 >= max_dur:
            break

    try:
        child.kill(9)
    except Exception:
        pass
    try:
        child.close(force=True)
    except Exception:
        pass
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
                    "-i", os.path.join(tmp, "fr_%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", a.out],
                   check=True)
    shutil.rmtree(tmp)
    print(f">> {a.out}  ({f / fps:.1f}s, {f} frames, {rend.W}x{rend.H})")

if __name__ == "__main__":
    main()
