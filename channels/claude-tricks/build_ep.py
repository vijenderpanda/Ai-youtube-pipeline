#!/usr/bin/env python3
"""
Generic AI Unpacked episode builder. Each episode = one config dict below.

Pipeline per episode:
  hook/payoff cards (Pillow) + terminal casts (term_anim.py) + ElevenLabs VO
  (Hrithik, 0.4s breaks between lines for comprehension) -> spec JSON -> assemble_short.py

Usage:
  python3 channels/claude-tricks/build_ep.py --ep 02          # build assets + spec + render
  python3 channels/claude-tricks/build_ep.py --ep 03 --no-render
"""
import argparse, json, os, subprocess, sys
from PIL import Image, ImageDraw

CH = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(CH))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, CH)
from build_poc import bg, ffont, DISPLAY, MONO, SANS, W, H, MAG, WHITE, DIM, GREEN, clean

ELEVEN_VOICE = "ZZ5OIPIzxVJswEhc0UXt"   # Hrithik (locked)
STYLE = 0.4                              # comprehension > frenzy (user feedback 2026-08-01)
BREAK = '<break time="0.4s" />'

YELLOW = (255, 214, 10)

# ---------------- episode configs ----------------
EPISODES = {
  "01": {
    "title": "Stop Letting Claude Code Wreck Your Files! (1 Shortcut Fixes It) 🛑",
    "tags": "claude code,claude code tips,claude code tricks,plan mode,claude ai,ai coding,ai coding assistant,anthropic claude,coding with ai,ai tips",
    "topic": ["CLAUDE CODE:", "PLAN MODE"],
    "emojis": "🛑🧠✅",
    "lines": [
      "Stop letting Claude Code wreck your files.",
      "One shortcut fixes it, and almost nobody uses it.",
      "Watch. You ask for a refactor, and it starts editing fourteen files. No plan. No warning.",
      "Now press Shift Tab. That's Plan Mode.",
      "Same request. But this time, Claude thinks first.",
      "It writes the full plan, step by step, and waits for your yes.",
      "Nothing touches your code until you approve it.",
      "That's the difference between chaos and control.",
      "Try it today. And follow, one AI trick every day.",
    ],
    "hot": ["STOP", "WRECK", "ONE", "SHORTCUT", "SHIFT", "TAB", "PLAN", "MODE",
            "THINKS", "FIRST", "FULL", "YES", "CONTROL", "ZERO", "REWRITES",
            "FOLLOW", "EVERY", "DAY"],
    "hook": {"top": ">_ claude code is editing 14 files...", "big1": "STOP",
             "big2": "LETTING AI", "big3": "WRECK FILES", "col3": "yellow"},
    "payoff": {"l1": "ZERO SURPRISE", "l2": "REWRITES", "cta": "Follow for a new AI trick"},
    "casts": {
      "c1": {"title": "claude-code — ~/project", "steps": [
        {"type": "type", "text": "> refactor the auth module", "color": "white", "cps": 22},
        {"type": "pause", "dur": 0.4},
        {"type": "out", "lps": 7, "lines": [["", "white"],
          ["editing 14 files...", "dim"], ["  ~/auth/login.ts", "red"],
          ["  ~/auth/session.ts", "red"], ["  ~/api/routes.ts", "red"],
          ["  + 11 more", "red"], ["", "white"],
          ["wait — what did it just change?!", "magenta"]]},
        {"type": "pause", "dur": 1.2}]},
      "c2": {"title": "claude-code — ~/project", "steps": [
        {"type": "badge", "text": "[plan mode: ON]  (shift+tab)", "color": "green"},
        {"type": "pause", "dur": 0.5},
        {"type": "type", "text": "> refactor the auth module", "color": "white", "cps": 24},
        {"type": "out", "lps": 6, "lines": [["", "white"],
          ["thinking through the change", "dim"],
          ["before touching your code...", "dim"]]},
        {"type": "pause", "dur": 1.0}]},
      "c3": {"title": "claude-code — ~/project", "steps": [
        {"type": "out", "lps": 6, "lines": [
          ["Here's my plan:", "white"], ["", "white"],
          ["  1. extract session helper", "blue"],
          ["  2. add token refresh", "blue"],
          ["  3. update 3 call sites", "blue"],
          ["  4. add tests", "blue"], ["", "white"],
          ["Approve this plan? (y/n)", "green"]]},
        {"type": "type", "text": "waiting for your ok…", "color": "magenta", "cps": 16},
        {"type": "pause", "dur": 1.2}]},
    },
    "beats": ["hook", "hook", "c1", "c2", "c2", "c3", "c3", "payoff", "payoff"],
  },
  "02": {
    "title": "Claude Code Forgets EVERYTHING! (1 File Fixes It Forever) 🛑",
    "tags": "claude code,claude md,claude code memory,claude code tips,claude ai,ai coding,ai coding assistant,anthropic claude,coding with ai,ai tips",
    "topic": ["CLAUDE.md =", "PERMANENT MEMORY"],
    "emojis": "🧠📝♾️",
    "lines": [
      "Claude Code forgets everything, every single session.",
      "Here's the one file that fixes it forever.",
      "You tell it to use your conventions, and it has no idea what you mean.",
      "So create one file. CLAUDE dot MD, right in your repo.",
      "Put your stack in it. Your rules. Your do-not-touch list.",
      "Now start a fresh session, and watch.",
      "It follows your style, skips your legacy folder, no reminders needed.",
      "One file. Permanent memory.",
      "Follow for one practical AI trick, every single day.",
    ],
    "hot": ["FORGETS", "EVERYTHING", "ONE", "FILE", "FOREVER", "CLAUDEMD", "CLAUDE",
            "MD", "STACK", "RULES", "EVERY", "AUTOMATICALLY", "REMEMBERS", "FOLLOW"],
    "hook": {"top": ">_ new session... context lost", "big1": "CLAUDE",
             "big2": "FORGETS", "big3": "EVERYTHING", "col3": "yellow"},
    "payoff": {"l1": "IT JUST", "l2": "REMEMBERS", "cta": "Follow for a new AI trick"},
    "casts": {
      "c1": {"title": "claude-code — ~/project", "steps": [
        {"type": "type", "text": "> use our api conventions", "color": "white", "cps": 20},
        {"type": "out", "lps": 6, "lines": [["", "white"],
          ["which conventions? I don't", "dim"], ["have that context.", "dim"],
          ["", "white"], ["...every. single. session.", "magenta"]]},
        {"type": "pause", "dur": 1.2}]},
      "c2": {"title": "~/project/CLAUDE.md", "steps": [
        {"type": "type", "text": "# CLAUDE.md", "color": "magenta", "cps": 22},
        {"type": "out", "lps": 5, "lines": [
          ["stack: Next.js + Supabase", "blue"],
          ["style: functional, no classes", "blue"],
          ["tests: vitest, colocated", "blue"],
          ["never touch: /legacy", "red"]]},
        {"type": "pause", "dur": 1.2}]},
      "c3": {"title": "claude-code — ~/project", "steps": [
        {"type": "badge", "text": "[loaded: CLAUDE.md]", "color": "green"},
        {"type": "type", "text": "> add the orders endpoint", "color": "white", "cps": 22},
        {"type": "out", "lps": 5, "lines": [["", "white"],
          ["Following your conventions:", "white"],
          ["  functional + vitest tests ✓", "green"],
          ["  skipping /legacy ✓", "green"]]},
        {"type": "pause", "dur": 1.2}]},
    },
    # visual beat per line: card / cast key
    "beats": ["hook", "hook", "c1", "c2", "c2", "c3", "c3", "payoff", "payoff"],
  },
  "03": {
    "title": "You Type The SAME Prompt Every Day! (Save It As A Command) 🛑",
    "tags": "claude code,slash commands,claude code commands,claude code tips,claude ai,ai coding,ai coding assistant,prompt engineering,coding with ai,ai tips",
    "topic": ["CUSTOM", "SLASH COMMANDS"],
    "emojis": "⌨️⚡🔁",
    "lines": [
      "You type the same prompt into AI, every single day.",
      "Stop. There's a one-keystroke fix.",
      "That long review prompt you keep retyping? Yeah, that one.",
      "Make a folder: dot claude, slash commands.",
      "Drop your prompt in a markdown file. Name it review.",
      "Now just type slash review. That's it.",
      "The whole workflow runs. Reviews, tests, refactors. One key.",
      "Save it once. Use it forever.",
      "Follow for one practical AI trick, every single day.",
    ],
    "hot": ["SAME", "PROMPT", "EVERY", "DAY", "STOP", "SAVE", "SLASH", "COMMAND",
            "MARKDOWN", "ONE", "KEYSTROKE", "WORKFLOW", "REVIEWS", "TESTS",
            "REFACTORS", "FOLLOW"],
    "hook": {"top": ">_ typing that prompt... again", "big1": "STOP",
             "big2": "RETYPING", "big3": "PROMPTS", "col3": "yellow"},
    "payoff": {"l1": "ONE KEY.", "l2": "WHOLE FLOW", "cta": "Follow for a new AI trick"},
    "casts": {
      "c1": {"title": "claude-code — ~/project", "steps": [
        {"type": "type", "text": "> review this diff for bugs, style,", "color": "white", "cps": 26},
        {"type": "type", "text": "  perf, and missing tests...", "color": "white", "cps": 26},
        {"type": "out", "lps": 6, "lines": [["", "white"],
          ["(you typed this yesterday.", "dim"], [" and the day before.)", "magenta"]]},
        {"type": "pause", "dur": 1.1}]},
      "c2": {"title": ".claude/commands/review.md", "steps": [
        {"type": "badge", "text": "$ mkdir -p .claude/commands", "color": "green"},
        {"type": "type", "text": "# review.md", "color": "magenta", "cps": 22},
        {"type": "out", "lps": 5, "lines": [
          ["Review this diff for bugs,", "blue"],
          ["style, perf and missing", "blue"],
          ["tests. Rank by severity.", "blue"]]},
        {"type": "pause", "dur": 1.2}]},
      "c3": {"title": "claude-code — ~/project", "steps": [
        {"type": "type", "text": "> /review", "color": "magenta", "cps": 14},
        {"type": "out", "lps": 5, "lines": [["", "white"],
          ["Running your full review", "white"],
          ["workflow...", "white"],
          ["  3 issues found, ranked ✓", "green"]]},
        {"type": "pause", "dur": 1.2}]},
    },
    "beats": ["hook", "hook", "c1", "c2", "c2", "c3", "c3", "payoff", "payoff"],
  },
  "04": {
    "title": "Claude Just Got SKILLS! (Teach It Once, It's Expert Forever) 🤯",
    "tags": "claude skills,agent skills,claude code skills,claude ai,claude code tips,ai coding,ai coding assistant,anthropic claude,ai agents,ai tips",
    "topic": ["CLAUDE SKILLS:", "TEACH IT ONCE"],
    "emojis": "🧠📁🤯",
    "lines": [
      "Claude just got skills. Real, reusable skills.",
      "And almost nobody is using them yet.",
      "You keep re-explaining the same workflow, every single time.",
      "Now make a skill. One folder, one skill file.",
      "Instructions, scripts, examples. All packed inside.",
      "Claude loads it automatically, only when the task matches.",
      "So it stays fast, and it nails the job every time.",
      "Teach it once. It's skilled forever.",
      "Follow for one practical AI trick, every single day.",
    ],
    "hot": ["SKILLS", "REUSABLE", "NOBODY", "ONE", "FOLDER", "SKILL", "FILE",
            "AUTOMATICALLY", "MATCHES", "FAST", "EVERY", "ONCE", "FOREVER", "FOLLOW"],
    "hook": {"top": ">_ new: agent skills", "big1": "CLAUDE",
             "big2": "JUST GOT", "big3": "SKILLS", "col3": "yellow"},
    "payoff": {"l1": "TEACH ONCE.", "l2": "SKILLED FOREVER", "cta": "Follow for a new AI trick"},
    "casts": {
      "c1": {"title": "claude-code — ~/project", "steps": [
        {"type": "type", "text": "> format this report our way", "color": "white", "cps": 22},
        {"type": "out", "lps": 6, "lines": [["", "white"],
          ["which format? walk me", "dim"], ["through it again?", "dim"],
          ["", "white"], ["(you've explained this 12 times)", "magenta"]]},
        {"type": "pause", "dur": 1.2}]},
      "c2": {"title": ".claude/skills/report-style/SKILL.md", "steps": [
        {"type": "badge", "text": "$ mkdir -p .claude/skills/report-style", "color": "green"},
        {"type": "type", "text": "# SKILL.md", "color": "magenta", "cps": 22},
        {"type": "out", "lps": 5, "lines": [
          ["name: report-style", "blue"],
          ["use when: formatting reports", "blue"],
          ["+ steps, template, examples", "blue"]]},
        {"type": "pause", "dur": 1.2}]},
      "c3": {"title": "claude-code — ~/project", "steps": [
        {"type": "badge", "text": "[skill matched: report-style]", "color": "green"},
        {"type": "type", "text": "> format this report our way", "color": "white", "cps": 22},
        {"type": "out", "lps": 5, "lines": [["", "white"],
          ["Loading your skill...", "white"],
          ["  applying your template ✓", "green"],
          ["  zero re-explaining ✓", "green"]]},
        {"type": "pause", "dur": 1.2}]},
    },
    "beats": ["hook", "hook", "c1", "c2", "c2", "c3", "c3", "payoff", "payoff"],
  },
  "05": {
    "title": "Claude Ships Code While You SLEEP! (Background Agents) 🤯",
    "tags": "claude code,subagents,background agents,ai agents,claude ai,claude code tips,ai coding,ai coding assistant,anthropic claude,ai tips",
    "topic": ["AI AGENTS THAT", "SHIP PRs"],
    "emojis": "🤖😴⚡", "icon": "pr",
    "lines": [
      "Claude now ships code while you sleep.",
      "Not hype. This shipped in July.",
      "Right now, you give AI a task, and you babysit the terminal.",
      "Not anymore. Subagents run in the background, by default.",
      "Fire one off, and just keep working.",
      "When it finishes, it commits, and it pushes.",
      "Then it opens a draft pull request. On its own.",
      "You review it with your coffee.",
      "Follow for one practical AI trick, every single day.",
    ],
    "hot": ["SHIPS", "SLEEP", "JULY", "BABYSIT", "SUBAGENTS", "BACKGROUND",
            "DEFAULT", "COMMITS", "PUSHES", "DRAFT", "PULL", "REQUEST",
            "COFFEE", "FOLLOW", "EVERY", "DAY"],
    "hook": {"top": ">_ agent finished: PR opened", "big1": "CLAUDE",
             "big2": "SHIPS WHILE", "big3": "YOU SLEEP", "col3": "yellow"},
    "payoff": {"l1": "REVIEW IT WITH", "l2": "YOUR COFFEE", "cta": "Follow for a new AI trick"},
    "casts": {
      "c1": {"title": "claude-code — ~/project", "steps": [
        {"type": "type", "text": "> fix the flaky auth tests", "color": "white", "cps": 22},
        {"type": "out", "lps": 6, "lines": [["", "white"],
          ["working... (23 minutes)", "dim"], ["", "white"],
          ["(you, watching every line)", "magenta"]]},
        {"type": "pause", "dur": 1.2}]},
      "c2": {"title": "claude-code — ~/project", "steps": [
        {"type": "badge", "text": "[subagent: runs in background]", "color": "green"},
        {"type": "type", "text": "> agent: fix the flaky auth tests", "color": "white", "cps": 24},
        {"type": "out", "lps": 5, "lines": [["", "white"],
          ["task started in background ✓", "green"],
          ["you: free to keep coding", "blue"]]},
        {"type": "pause", "dur": 1.2}]},
      "c3": {"title": "claude-code — ~/project", "steps": [
        {"type": "badge", "text": "[agent finished]", "color": "green"},
        {"type": "out", "lps": 5, "lines": [
          ["committed: fix auth race ✓", "green"],
          ["pushed to origin ✓", "green"],
          ["draft PR #142 opened ✓", "magenta"]]},
        {"type": "pause", "dur": 1.2}]},
    },
    "beats": ["hook", "hook", "c1", "c2", "c2", "c3", "c3", "payoff", "payoff"],
  },
}

# ---------------- builders ----------------
def make_hook(cfg, out):
    im = bg(); d = ImageDraw.Draw(im)
    d.text((70, 300), cfg["top"], font=ffont(MONO, 34), fill=GREEN)
    d.text((70, 460), cfg["big1"], font=ffont(DISPLAY, 220), fill=MAG)
    d.text((70, 700), cfg["big2"], font=ffont(DISPLAY, 165), fill=WHITE)
    col = YELLOW if cfg.get("col3") == "yellow" else WHITE
    d.text((70, 880), cfg["big3"], font=ffont(DISPLAY, 185), fill=col)
    d.rounded_rectangle([70, 1120, 690, 1132], radius=6, fill=MAG)
    im.save(out)

def _emoji(ch, size):
    """Render one emoji as RGBA (Apple Color Emoji strikes are fixed-size; scale after)."""
    try:
        from PIL import ImageFont
        f = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 160)
        im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
        return im.resize((size, size), Image.LANCZOS)
    except Exception:
        return None

def _icon_pr(size):
    """Generic pull-request/branch glyph (no trademarked logos)."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    u = size / 100.0; w = max(4, int(8 * u))
    d.ellipse([12*u, 12*u, 34*u, 34*u], outline=(255, 214, 10, 255), width=w)
    d.ellipse([12*u, 66*u, 34*u, 88*u], outline=(255, 214, 10, 255), width=w)
    d.ellipse([66*u, 66*u, 88*u, 88*u], outline=MAG + (255,), width=w)
    d.line([23*u, 34*u, 23*u, 66*u], fill=(255, 214, 10, 255), width=w)
    d.arc([23*u, 23*u, 77*u, 77*u], start=270, end=360, fill=MAG + (255,), width=w)
    d.line([77*u, 50*u, 77*u, 66*u], fill=MAG + (255,), width=w)
    return im

ICONS = {"pr": _icon_pr}

def make_topic_banner(lines2, out, emojis="", icon=None):
    """Thumbnail-style cover card: 2-line topic + emoji/icon row. Fades out at play start."""
    Wb, Hb = 1000, 460
    im = Image.new("RGBA", (Wb, Hb), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, Wb - 1, Hb - 1], radius=40, fill=(10, 10, 16, 215))
    d.rounded_rectangle([0, 0, Wb - 1, Hb - 1], radius=40, outline=MAG, width=6)
    d.text((50, 30), lines2[0], font=ffont(DISPLAY, 100), fill=WHITE)
    d.text((50, 160), lines2[1], font=ffont(DISPLAY, 112), fill=MAG)
    x = 50
    for ch in emojis:
        e = _emoji(ch, 130)
        if e:
            im.alpha_composite(e, (x, 300)); x += 150
    if icon and icon in ICONS:
        im.alpha_composite(ICONS[icon](130), (Wb - 190, 295))
    im.save(out)

def make_payoff(cfg, out):
    im = bg(); d = ImageDraw.Draw(im)
    d.text((70, 480), cfg["l1"], font=ffont(DISPLAY, 150), fill=WHITE)
    d.text((70, 640), cfg["l2"], font=ffont(DISPLAY, 185), fill=MAG)
    d.rounded_rectangle([70, 930, 970, 1080], radius=24, outline=MAG, width=5)
    d.text((100, 962), cfg["cta"], font=ffont(SANS, 46), fill=WHITE)
    d.text((100, 1017), "every day  ·  link in profile", font=ffont(SANS, 40), fill=DIM)
    im.save(out)

def build(ep, render=True):
    cfg = EPISODES[ep]
    A = os.path.join(CH, "assets", f"ep{ep}"); os.makedirs(A, exist_ok=True)
    R = os.path.join(CH, "renders"); os.makedirs(R, exist_ok=True)

    # cards
    hook_p = os.path.join(A, "hook.png"); make_hook(cfg["hook"], hook_p)
    pay_p = os.path.join(A, "payoff.png"); make_payoff(cfg["payoff"], pay_p)

    # terminal casts
    clips = {}
    for key, cast in cfg["casts"].items():
        cj = os.path.join(A, f"cast_{key}.json"); json.dump(cast, open(cj, "w"))
        cv = os.path.join(A, f"term_{key}.mp4")
        subprocess.run([sys.executable, os.path.join(REPO, "scripts", "term_anim.py"),
                        "--cast", cj, "--out", cv], check=True)
        clips[key] = cv

    # VO: single call, 0.4s breaks between lines (timestamps include the gaps)
    from eleven_vo import load_key, synth
    vo = os.path.join(A, "vo.wav")
    script = f" {BREAK} ".join(cfg["lines"])
    synth(load_key(), ELEVEN_VOICE, script, vo, speed=1.0, style=STYLE)
    words = json.load(open(vo.rsplit(".", 1)[0] + ".words.json"))
    hot = set(cfg["hot"])
    caps = []
    for w in words:
        cw = clean(w["w"])
        if not cw:
            continue
        caps.append({"w": cw, "start": w["start"], "end": w["end"], "hot": cw in hot})

    # per-line durations from word counts
    counts = [len(l.split()) for l in cfg["lines"]]
    # words json may drop punctuation-only tokens; recount against caps stream
    seg_durs, idx, prev = [], 0, 0.0
    for n in counts:
        n = min(n, len(caps) - idx)
        last = caps[idx + n - 1]
        nxt = caps[idx + n]["start"] if idx + n < len(caps) else last["end"]
        bound = round((last["end"] + nxt) / 2, 3)
        seg_durs.append(round(bound - prev, 3)); prev = bound; idx += n
    total = caps[-1]["end"]
    seg_durs[-1] = round(seg_durs[-1] + (total - sum(seg_durs)), 3)

    # segments from beats
    segments = []
    for i, beat in enumerate(cfg["beats"]):
        if beat == "hook":
            segments.append({"img": hook_p, "dur": seg_durs[i], "motion": "zoom_in"})
        elif beat == "payoff":
            segments.append({"img": pay_p, "dur": seg_durs[i], "motion": "zoom_out"})
        else:
            segments.append({"vid": clips[beat], "dur": seg_durs[i], "punch": True})
    # merge consecutive identical cast beats into one longer segment
    merged = []
    for s in segments:
        if merged and s.get("vid") and merged[-1].get("vid") == s.get("vid"):
            merged[-1]["dur"] = round(merged[-1]["dur"] + s["dur"], 3)
        else:
            merged.append(s)

    # ---- VAIBHAV FORMAT: full-frame lip-synced host on hook + payoff (HeyGen talking photo) ----
    # hook = beats[0] lines, payoff = beats[-1] line(s); terminals fill the middle.
    n_hook = 0
    while n_hook < len(cfg["beats"]) and cfg["beats"][n_hook] == "hook":
        n_hook += 1
    n_pay = 0
    while n_pay < len(cfg["beats"]) and cfg["beats"][-1 - n_pay] == "payoff":
        n_pay += 1
    hook_end = round(sum(seg_durs[:n_hook]), 3)
    pay_start = round(total - sum(seg_durs[-n_pay:]), 3)

    def slice_wav(src, start, dur, out_wav):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start),
                        "-t", str(dur), "-i", src, "-c:a", "pcm_s16le", out_wav], check=True)

    from heygen_avatar import upload_audio as hg_audio, generate as hg_generate, CACHE as HG_CACHE
    tid = open(HG_CACHE).read().strip()
    hook_wav = os.path.join(A, "host_hook.wav"); slice_wav(vo, 0, hook_end, hook_wav)
    pay_wav = os.path.join(A, "host_payoff.wav"); slice_wav(vo, pay_start, total - pay_start, pay_wav)
    hook_clip = os.path.join(A, "host_hook.mp4")
    pay_clip = os.path.join(A, "host_payoff.mp4")
    if not os.path.exists(hook_clip):
        hg_generate(tid, hg_audio(hook_wav), hook_clip)
    if not os.path.exists(pay_clip):
        hg_generate(tid, hg_audio(pay_wav), pay_clip)

    # rebuild segment list: ONE host clip for all hook lines, casts, ONE for all payoff lines
    mid = []
    for i, beat in enumerate(cfg["beats"][n_hook:len(cfg["beats"]) - n_pay], start=n_hook):
        mid.append({"vid": clips[beat], "dur": seg_durs[i], "punch": True})
    m2 = []
    for sgm in mid:
        if m2 and m2[-1]["vid"] == sgm["vid"]:
            m2[-1]["dur"] = round(m2[-1]["dur"] + sgm["dur"], 3)
        else:
            m2.append(sgm)
    merged = ([{"vid": hook_clip, "dur": hook_end}] + m2
              + [{"vid": pay_clip, "dur": round(total - pay_start, 3)}])

    topic_p = os.path.join(A, "topic.png")
    if cfg.get("topic"):
        make_topic_banner(cfg["topic"], topic_p, emojis=cfg.get("emojis", ""),
                          icon=cfg.get("icon"))
    spec = {
        "w": W, "h": H, "fps": 30, "accent": "E0218A", "caption_size": 115,
        "vo": vo, "music": os.path.join(CH, "assets", "music", "bed_active.mp3"), "music_gain": 0.30, "segments": merged,
        "watermark": os.path.join(CH, "assets", "watermark.png"),
        "banners": ([{"img": topic_p, "start": 0.0, "end": round(min(hook_end + 0.8, 3.2), 2),
                       "fade_out": 0.7, "scale": 0.94}]
                    if cfg.get("topic") else []),
        "logo_pop": os.path.join(CH, "assets", "logo_pop.png"),
        "captions": caps,
    }
    sp = os.path.join(CH, "episodes", f"{ep}.short.json")
    json.dump(spec, open(sp, "w"), indent=1)
    print(f">> ep{ep}: spec {sp} | total ~{total:.1f}s | lines={seg_durs}")

    if render:
        out = os.path.join(R, f"ep{ep}.mp4")
        subprocess.run([sys.executable, os.path.join(REPO, "scripts", "assemble_short.py"),
                        "--spec", sp, "--out", out], check=True)
        print(">> rendered", out)
        return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", required=True, choices=sorted(EPISODES))
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    build(a.ep, render=not a.no_render)
