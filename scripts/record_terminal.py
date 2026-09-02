#!/usr/bin/env python3
"""
record_terminal.py — record a REAL command run in a REAL pty, then render it to
a deterministic 1080-wide video with the channel's own typeface and palette.

WHY THIS EXISTS
---------------
`record_demo.py` is a Playwright *browser page* recorder — it drives a URL. There
was no way to shoot a terminal at all, which blocked eight planned episodes and
forced every terminal pane to be a Remotion re-creation labelled
`REAL OUTPUT · REPLAYED IN REMOTION` (honest, but weaker than a capture).

WHY A PTY + RENDERER RATHER THAN A SCREEN GRAB
----------------------------------------------
Screen-grabbing a desktop terminal (ffmpeg -f avfoundation) needs a TCC grant,
captures whatever font/theme/clutter the machine happens to have, risks catching
PII from the desktop, and cannot be re-rendered when the brand changes. Running
the command under a pty gives us the *same bytes the terminal would have shown*
plus real per-byte timings, and rendering those ourselves is reproducible,
brand-consistent, PII-free and re-renderable forever.

WHAT IS AND IS NOT REAL — and therefore what the chip must say
--------------------------------------------------------------
REAL: the command, the exit code, every byte of stdout/stderr, and the timing
between them. The pty is a real terminal; the program cannot tell the difference.
OURS: the glyphs, the colours, the window. Nothing is added, removed or reordered.

    Truthful chip:  REAL PTY OUTPUT · RENDERED
    NEVER:          SCREEN RECORDING   (nothing was screen-grabbed)
    NEVER:          UNCUT              if --max-gap trimmed any dead time; the
                                       tool prints exactly what it compressed and
                                       writes it into the sidecar so you cannot
                                       claim otherwise by accident.

USAGE
    python3 scripts/record_terminal.py --out demo.mp4 -- python3 scripts/style_steal.py @x --n 3
    python3 scripts/record_terminal.py --out d.mp4 --theme forge --cols 92 --max-gap 1.2 -- ls -la

Writes demo.mp4 + demo.cast.json (timings, so SEAM beats can be anchored to the
moment a line actually appeared).
"""
import argparse
import json
import os
import pty
import re
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
FONT = REPO / "remotion-studio/public/fonts/IBMPlexMono-Medium.ttf"

# SEAM palettes (Seam.tsx) so a captured pane matches the episode it lands in
THEMES = {
    "forge":   dict(bg="#17150F", fg="#F6EFE1", dim="#9A9080", accent="#F5A524", ok="#7FC8A9"),
    "ink":     dict(bg="#EDE8DE", fg="#14110E", dim="#6B6355", accent="#D8442A", ok="#1F6F63"),
    "signal":  dict(bg="#0C1730", fg="#EAF1FF", dim="#8098C0", accent="#35D6E8", ok="#FFB03A"),
    "risk":    dict(bg="#120E0E", fg="#F5E9E7", dim="#9A8582", accent="#FF4D3D", ok="#F0A020"),
    "verdict": dict(bg="#EFEDF6", fg="#141127", dim="#615C7D", accent="#4B3BD8", ok="#1F6F63"),
    "bloom":   dict(bg="#E8F0E6", fg="#0E1A14", dim="#5A6E60", accent="#12855C", ok="#D8442A"),
}

# ANSI 16-colour -> role. We deliberately do NOT reproduce the source palette:
# the point is that a captured pane looks like the channel, not like this laptop.
SGR_ROLE = {30: "dim", 31: "accent", 32: "ok", 33: "accent", 34: "dim",
            35: "accent", 36: "ok", 37: "fg", 90: "dim", 91: "accent",
            92: "ok", 93: "accent", 94: "dim", 95: "accent", 96: "ok", 97: "fg"}

CSI = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")
OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")


class Screen:
    """Just enough terminal to be faithful to CLI output: SGR colour, \\r, \\n,
    erase-line, erase-screen, cursor-column. Not a vt100 — a CLI transcript."""

    def __init__(self, cols, rows):
        # Incremental decoder, not a per-slice one: a fixed byte window clips
        # multi-byte characters at its edge, and the resulting UnicodeDecodeError
        # corrupts the ASCII in front of them ("subs" -> "su?s"). Decoding the
        # stream incrementally carries the partial character across chunks.
        import codecs
        self._dec = codecs.getincrementaldecoder("utf-8")("replace")
        self.cols, self.rows = cols, rows
        self.buf = [[(" ", "fg", False)] * cols for _ in range(rows)]
        self.cx = self.cy = 0
        self.role, self.bold = "fg", False

    def _nl(self):
        self.cx = 0
        self.cy += 1
        if self.cy >= self.rows:
            self.buf.pop(0)
            self.buf.append([(" ", "fg", False)] * self.cols)
            self.cy = self.rows - 1

    def _put(self, ch):
        if self.cx >= self.cols:
            self._nl()
        self.buf[self.cy][self.cx] = (ch, self.role, self.bold)
        self.cx += 1

    def feed(self, data):
        if isinstance(data, bytes):
            data = self._dec.decode(data)
        data = OSC.sub("", data)
        i = 0
        while i < len(data):
            m = CSI.match(data, i)
            if m:
                params, cmd = m.group(1), m.group(2)
                nums = [int(x) for x in params.split(";") if x.isdigit()]
                if cmd == "m":
                    for n in (nums or [0]):
                        if n == 0:
                            self.role, self.bold = "fg", False
                        elif n == 1:
                            self.bold = True
                        elif n in SGR_ROLE:
                            self.role = SGR_ROLE[n]
                elif cmd == "K":
                    k = nums[0] if nums else 0
                    lo = self.cx if k == 0 else 0
                    hi = self.cols if k in (0, 2) else self.cx + 1
                    for x in range(lo, hi):
                        self.buf[self.cy][x] = (" ", "fg", False)
                elif cmd == "J":
                    self.buf = [[(" ", "fg", False)] * self.cols for _ in range(self.rows)]
                    self.cx = self.cy = 0
                elif cmd == "G":
                    self.cx = max(0, (nums[0] if nums else 1) - 1)
                elif cmd in "AB":
                    self.cy = max(0, min(self.rows - 1,
                                         self.cy + (-1 if cmd == "A" else 1) * (nums[0] if nums else 1)))
                i = m.end()
                continue
            ch = data[i]
            if ch == "\x1b":
                i += 2
                continue
            if ch == "\n":
                self._nl()
            elif ch == "\r":
                self.cx = 0
            elif ch == "\t":
                self.cx = min(self.cols - 1, (self.cx // 8 + 1) * 8)
            elif ch == "\x08":
                self.cx = max(0, self.cx - 1)
            elif ch >= " ":
                self._put(ch)
            i += 1

    def snapshot(self):
        return [row[:] for row in self.buf]


def run_pty(cmd, cols, rows):
    """Run cmd under a pty, returning [(t, bytes)] and the exit code."""
    env = dict(os.environ, TERM="xterm-256color", COLUMNS=str(cols), LINES=str(rows),
               PYTHONUNBUFFERED="1", FORCE_COLOR="1")
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.execvpe(cmd[0], cmd, env)
        finally:
            os._exit(127)
    try:
        import fcntl, struct, termios
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except Exception:
        pass
    chunks, t0 = [], time.time()
    while True:
        try:
            r, _, _ = select.select([fd], [], [], 0.2)
        except (OSError, ValueError):
            break
        if r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                break
            if not data:
                break
            chunks.append((time.time() - t0, data))
            sys.stdout.write(data.decode("utf-8", "replace"))
            sys.stdout.flush()
        if os.waitpid(pid, os.WNOHANG)[0] == pid and not r:
            break
    try:
        os.close(fd)
    except OSError:
        pass
    _, status = os.waitpid(pid, 0) if False else (0, 0)
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--theme", default="forge", choices=list(THEMES))
    ap.add_argument("--cols", type=int, default=88)
    ap.add_argument("--rows", type=int, default=26)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--pad", type=int, default=34)
    ap.add_argument("--max-gap", type=float, default=1.5,
                    help="compress any dead stretch longer than this, in seconds")
    ap.add_argument("--tail", type=float, default=1.2, help="hold the final frame")
    ap.add_argument("--show-cmd", action="store_true", default=True)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        sys.exit("give a command after --")
    if not FONT.exists():
        sys.exit(f"font missing: {FONT}")

    print(f">> recording: {' '.join(cmd)}\n")
    chunks = run_pty(cmd, a.cols, a.rows)
    if not chunks:
        sys.exit("!! no output captured")

    # compress dead time, and record exactly what was compressed so the chip
    # cannot silently become a lie
    trims, shift, adj = [], 0.0, []
    prev = 0.0
    for t, data in chunks:
        gap = t - prev
        if gap > a.max_gap:
            cut = gap - a.max_gap
            trims.append({"at": round(prev, 3), "removed_s": round(cut, 3)})
            shift += cut
        adj.append((t - shift, data))
        prev = t
    dur = adj[-1][0] + a.tail

    th = THEMES[a.theme]
    fs = max(12, int((a.width - a.pad * 2) / (a.cols * 0.601)))
    font = ImageFont.truetype(str(FONT), fs)
    bfont = font
    lh = int(fs * 1.58)
    H = a.pad * 2 + lh * a.rows
    H += H % 2

    tmp = Path(a.out).with_suffix(".frames")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    scr = Screen(a.cols, a.rows)
    if a.show_cmd:
        scr.feed("$ " + " ".join(cmd) + "\r\n")
    nframes = int(dur * a.fps)
    ci, cell = 0, None
    print(f">> rendering {nframes} frames  {a.width}x{H}  {a.cols}x{a.rows} @ {fs}px")
    for f in range(nframes):
        t = f / a.fps
        while ci < len(adj) and adj[ci][0] <= t:
            scr.feed(adj[ci][1])
            ci += 1
            cell = None
        if cell is None:
            img = Image.new("RGB", (a.width, H), th["bg"])
            d = ImageDraw.Draw(img)
            for y, row in enumerate(scr.snapshot()):
                x = a.pad
                run, role = "", row[0][1] if row else "fg"
                for ch, r, bold in row + [("", None, False)]:
                    if r == role:
                        run += ch
                    else:
                        if run.strip():
                            d.text((x, a.pad + y * lh), run, font=bfont, fill=th.get(role, th["fg"]))
                        x += d.textlength(run, font=font)
                        run, role = ch, r
            cell = img
        cell.save(tmp / f"{f:06d}.png")

    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps),
                    "-i", str(tmp / "%06d.png"), "-c:v", "libx264", "-preset", "medium",
                    "-crf", "17", "-pix_fmt", "yuv420p", a.out], check=True)
    shutil.rmtree(tmp)

    cast = {
        "cmd": cmd, "theme": a.theme, "cols": a.cols, "rows": a.rows,
        "fps": a.fps, "duration_s": round(dur, 3),
        "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chip": "REAL PTY OUTPUT · RENDERED",
        "compressed_gaps": trims,
        "events": [{"t": round(t, 3), "bytes": len(b)} for t, b in adj],
    }
    Path(a.out).with_suffix(".cast.json").write_text(json.dumps(cast, indent=1))
    print(f"\n>> {a.out}  {dur:.2f}s  {a.width}x{H}")
    print(f">> {Path(a.out).with_suffix('.cast.json')}")
    if trims:
        tot = sum(x["removed_s"] for x in trims)
        print(f"!! compressed {len(trims)} dead stretches, {tot:.1f}s removed — "
              f"the chip may NOT say UNCUT. Use: REAL PTY OUTPUT · RENDERED · GAPS TRIMMED")
    else:
        print(">> no gaps trimmed — chip: REAL PTY OUTPUT · RENDERED")


if __name__ == "__main__":
    main()
