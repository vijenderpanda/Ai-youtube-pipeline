#!/usr/bin/env python3
"""
AI Unpacked pipeline v2 — Remotion-based episode builder (agency-grade).

Per episode: ElevenLabs VO (word timings, 0.4s breaks) + HeyGen talking-host
clips (hook/payoff) + REAL screen recordings (VHS/Playwright, sliced by
timestamps) -> Remotion props JSON -> `npx remotion render` -> ffmpeg master
(sidechain-ducked music + limiter to broadcast loudness).

Usage: python3 channels/claude-tricks/build_ep_v2.py --ep 06
Episode configs live in EPISODES_V2 below.
"""
import argparse, json, os, subprocess, sys

CH = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(CH))
sys.path.insert(0, os.path.join(REPO, "scripts"))
from ffmpeg_util import venc  # GPU (NVENC) encode when available, else libx264

ELEVEN_VOICE = "ZZ5OIPIzxVJswEhc0UXt"   # Hrithik (locked)
STYLE = 0.4
BREAK = '<break time="0.4s" />'
MUSIC = "assets/music/bed_active.mp3"   # relative to remotion public/

EPISODES_V2 = {
  "20": {
    "title": "The Effort Dial Nobody Uses (Deeper Answers, Free) 🧠",
    "tags": "claude effort,extended thinking,claude models,claude ai tips,ai for beginners,ai productivity,ai tips",
    "cover": {"title1": "TURN UP", "title2": "THE EFFORT", "emojis": "🧠🎚️⚡"},
    "lines": [
      "Claude has a hidden dial that makes it think harder. Almost nobody touches it.",
      "It's the effort setting. Here's where it lives. Watch.",
      "Type slash model, and look at the very bottom line.",
      "That's the effort dial. Right now, it's set to High.",
      "Tap left, and it drops to Low. Faster, lighter answers.",
      "Tap right, back to High. Deeper thinking for the hard stuff.",
      "Same model, same price. You just picked how hard it thinks.",
      "Easy task? Low effort. Stuck on something hard? Crank it up.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["HIDDEN", "DIAL", "HARDER", "NOBODY", "EFFORT", "WATCH", "SLASH",
                  "MODEL", "BOTTOM", "HIGH", "LEFT", "LOW", "FASTER", "RIGHT",
                  "DEEPER", "SAME", "PRICE", "PICKED", "THINKS", "EASY", "CRANK",
                  "FOLLOW", "EVERY", "DAY"],
    "beats": ["host", "host",
              "rec:ep20/term_effort.mp4@3.5",
              "rec:ep20/term_effort.mp4@8.5",
              "rec:ep20/term_effort.mp4@15.0",
              "rec:ep20/term_effort.mp4@20.0",
              "rec:ep20/term_effort.mp4@22.5",
              "host2", "host2"],
    "steps": [
      ("STEP 1/3 — OPEN /MODEL", 2, 2),
      ("STEP 2/3 — ← FOR LOW (FAST)", 3, 4),
      ("STEP 3/3 — → FOR HIGH (DEEP)", 5, 6),
    ],
  },
  "22": {
    "title": "Stop Letting Claude Wreck Your Files (Plan Mode) 🛑",
    "tags": "claude code,plan mode,ai coding,claude ai tips,ai for beginners,vibe coding,ai tips",
    "cover": {"title1": "MAKE CLAUDE", "title2": "THINK FIRST", "emojis": "🛑🧠✋"},
    "lines": [
      "Claude Code can edit your files before it even thinks. That's how good code gets wrecked.",
      "One shortcut forces it to plan first, and wait for your yes. Watch.",
      "Press shift and tab, until the bar says: plan mode on.",
      "Now I give it a real task. Add input validation to my code.",
      "Instead of editing, Claude stops, and writes out a full plan.",
      "It lays out exactly what it will change, before touching a single file.",
      "Then it waits. Nothing happens until you choose yes.",
      "So you review first, approve second. Your code stays safe.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["EDIT", "THINKS", "WRECKED", "ONE", "SHORTCUT", "PLAN", "FIRST",
                  "YES", "WATCH", "SHIFT", "TAB", "MODE", "TASK", "VALIDATION",
                  "STOPS", "WRITES", "FULL", "EXACTLY", "CHANGE", "SINGLE", "FILE",
                  "WAITS", "NOTHING", "CHOOSE", "REVIEW", "APPROVE", "SECOND",
                  "SAFE", "FOLLOW", "EVERY", "DAY"],
    "beats": ["host", "host",
              "rec:ep22/term_planmode.mp4@5.5",
              "rec:ep22/term_planmode.mp4@10.5",
              "rec:ep22/term_planmode.mp4@35.5",
              "rec:ep22/term_planmode.mp4@37.5",
              "rec:ep22/term_planmode.mp4@39.5",
              "host2", "host2"],
    "steps": [
      ("STEP 1/3 — SHIFT+TAB → PLAN", 2, 2),
      ("STEP 2/3 — GIVE IT A TASK", 3, 3),
      ("STEP 3/3 — REVIEW, THEN APPROVE", 4, 6),
    ],
  },
  "09": {
    "title": "Fast vs Deep — Stop Overpaying For AI Answers ⚡",
    "tags": "claude models,model switching,ai cost,claude ai tips,ai for beginners,ai productivity,ai tips",
    "cover": {"title1": "FAST BRAIN OR", "title2": "DEEP BRAIN?", "emojis": "⚡🧠💸"},
    "lines": [
      "You're using one Claude brain for everything. That's why it feels slow, and costs more.",
      "Claude has a fast brain and a deep brain. Here's how to switch. Watch.",
      "Type slash model. This menu shows all of Claude's brains.",
      "See number five? Haiku. The fast one. I just press five.",
      "Quick question in... and boom. Instant answer. Tiny cost.",
      "Hard problem? Switch back up to a deep model, like Fable. Just press three.",
      "Claude even warns you: deeper means slower, more tokens. That's the trade.",
      "Quick stuff, fast brain. Hard stuff, deep brain. That habit alone doubles your speed.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["ONE", "BRAIN", "SLOW", "COSTS", "FAST", "DEEP", "SWITCH",
                  "WATCH", "SLASH", "MODEL", "MENU", "BRAINS", "FIVE", "HAIKU",
                  "PRESS", "BOOM", "INSTANT", "TINY", "COST", "HARD", "FABLE",
                  "THREE", "WARNS", "SLOWER", "TOKENS", "TRADE", "QUICK",
                  "DOUBLES", "SPEED", "FOLLOW", "EVERY", "DAY"],
    "beats": ["host", "host",
              "rec:ep09/term_fastdeep.mp4@6.5",
              "rec:ep09/term_fastdeep.mp4@10.5",
              "rec:ep09/term_fastdeep.mp4@29.0",
              "rec:ep09/term_fastdeep.mp4@40.0",
              "rec:ep09/term_fastdeep.mp4@48.0",
              "host2", "host2"],
    "steps": [
      ("STEP 1/3 — TYPE /MODEL", 2, 2),
      ("STEP 2/3 — PRESS 5 = FAST", 3, 4),
      ("STEP 3/3 — PRESS 3 = DEEP", 5, 6),
    ],
  },
  "07": {
    "title": "Claude Burns Your Tokens — Do THIS Instead 🪙",
    "tags": "claude code,token saving,ai cost,claude ai tips,ai productivity,ai for beginners,ai tips",
    "cover": {"title1": "STOP WASTING", "title2": "YOUR TOKENS", "emojis": "🪙⚡💸"},
    "lines": [
      "Claude quietly eats your tokens, and tokens cost money and speed.",
      "Here's how to see it, and cut it in half. Watch.",
      "Type slash context. This shows what's filling Claude's memory.",
      "Every message and file piles up, and slowly makes Claude sluggish.",
      "Now the fix. Just type slash compact.",
      "Claude squeezes the whole conversation into a tight summary.",
      "Same memory, way fewer tokens. Faster and cheaper answers.",
      "Do this whenever a chat gets long. Your wallet will thank you.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["BURNS", "TOKENS", "MONEY", "SPEED", "SEE", "HALF", "WATCH",
                  "SLASH", "CONTEXT", "MEMORY", "PILES", "SLUGGISH", "FIX",
                  "COMPACT", "SQUEEZES", "SUMMARY", "FEWER", "FASTER", "CHEAPER",
                  "LONG", "WALLET", "FOLLOW"],
    "beats": ["host", "host",
              "rec:ep07/term_tokens.mp4@31.0",
              "rec:ep07/term_tokens.mp4@33.0",
              "rec:ep07/term_tokens.mp4@35.5",
              "rec:ep07/term_tokens.mp4@37.5",
              "rec:ep07/term_tokens.mp4@39.5",
              "host2", "host2"],
    "steps": [
      ("STEP 1/2 — SEE IT: /context", 2, 3),
      ("STEP 2/2 — CUT IT: /compact", 4, 6),
    ],
  },
  "08": {
    "title": "Google Just Put AI In Your Kid's Classroom 🎓 (Parents, Check This)",
    "tags": "gemini,google classroom,ai in schools,ai for parents,gemini for education,student ai,ai news,ai for beginners,ai tips,ai safety",
    "cover": {"title1": "AI JUST ENTERED", "title2": "YOUR KID'S CLASS",
              "sub": "what every parent should know", "emojis": "🎓🤖"},
    "layout": "newsSplit",
    "outro": True,
    # VO + host clip are pre-rendered on disk (assets/ep08/vo_v2.*, v2_host.mp4);
    # these lines only supply the line count + caption fallback. Keep them
    # matched to the recorded VO (7 lines == 6 break markers in words.json).
    "lines": [
      "Here's one for parents.",
      "Starting August tenth, Google is expanding its Gemini AI inside Google Classroom to students of all ages.",
      "If a school already has it switched on, students can turn their own class materials into flashcards, practice quizzes, and study guides.",
      "For families, that means an AI study helper could sit right inside school software.",
      "The good news: school admins can turn it off for under-eighteens.",
      "So it's worth asking your child's school whether it's on.",
      "That's your AI Unpacked.",
    ],
    "hot_words": ["PARENTS", "AUGUST", "TENTH", "GEMINI", "CLASSROOM", "ALL",
                  "AGES", "FLASHCARDS", "QUIZZES", "GUIDES", "HELPER", "SCHOOL",
                  "SOFTWARE", "GOOD", "NEWS", "OFF", "UNDER-EIGHTEENS",
                  "ASKING", "UNPACKED"],
    # beat 2 = the real Google Workspace Updates announcement (dated, full-frame
    # proof, built by make_still_hold from announce_card.png). Rest is licensed
    # Pexels b-roll in split panes so the host stays present.
    "beats": ["host",
              "rec:ep08/announce.mp4@0.0|full",
              "rec:ep08/broll/pexels_6868327.mp4@2.0|split",
              "rec:ep08/broll/pexels_18069700.mp4@2.0|split",
              "rec:ep08/broll/pexels_6436524.mp4@2.0|split",
              "host",
              "host"],
    "steps": [
      ("ASK YOUR SCHOOL IF IT'S ON", 5, 6, "tr"),
    ],
    "emphasis": [
      ("an AI study helper inside school software", 3, 3),
      ("admins can switch it off for under-18s", 4, 4),
    ],
  },
  "02": {
    "title": "Claude Code Forgets EVERYTHING! (1 File Fixes It Forever) 🛑",
    "tags": "claude code,claude md,claude code memory,claude ai tips,ai for beginners,ai coding,ai tips",
    "cover": {"title1": "GIVE CLAUDE A", "title2": "PERMANENT MEMORY", "emojis": "🧠📝♾️"},
    "lines": [
      "Claude Code forgets everything, every single session.",
      "Here's the one file that fixes it forever.",
      "Watch. I create one file called CLAUDE dot MD, right in my project.",
      "Inside it: my stack, my style rules, and what to never touch.",
      "Save it. That's the whole setup.",
      "Now I start a completely fresh session.",
      "And ask: what stack do we use? It answers from my file. Every rule remembered.",
      "One file. Permanent memory. No more repeating yourself.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["FORGETS", "EVERYTHING", "ONE", "FILE", "FOREVER", "WATCH", "CLAUDEMD",
                  "CLAUDE", "MD", "STACK", "RULES", "NEVER", "SAVE", "FRESH",
                  "ANSWERS", "REMEMBERED", "PERMANENT", "MEMORY", "FOLLOW", "EVERY", "DAY"],
    "beats": ["host", "host",
              "rec:ep02/term_claudemd.mp4@1.2",
              "rec:ep02/term_claudemd.mp4@4.2",
              "rec:ep02/term_claudemd.mp4@8.0",
              "rec:ep02/term_claudemd.mp4@11.5",
              "rec:ep02/term_claudemd.mp4@25.5",
              "host2", "host2"],
    "steps": [
      ("STEP 1/3 — CREATE CLAUDE.md", 2, 3),
      ("STEP 2/3 — ADD YOUR RULES", 4, 5),
      ("STEP 3/3 — IT JUST KNOWS", 6, 6),
    ],
  },
  "03": {
    "title": "You Type The SAME Prompt Every Day! (Save It As A Command) 🛑",
    "tags": "claude code,slash commands,custom commands,claude ai tips,ai for beginners,prompt engineering,ai tips",
    "cover": {"title1": "SAVE PROMPTS AS", "title2": "SLASH COMMANDS", "emojis": "⌨️⚡🔁"},
    "lines": [
      "You type the same prompt into AI, every single day.",
      "Stop. Save it once. Here's how.",
      "Watch. I make one file inside dot claude, slash commands.",
      "My whole prompt goes in it. I name the file rules.",
      "That name becomes the command.",
      "Now, fresh session. I just type slash rules.",
      "And the whole saved prompt runs. Full checklist, instantly.",
      "Type it once. Use it forever, with one keystroke.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["SAME", "PROMPT", "EVERY", "DAY", "STOP", "SAVE", "WATCH", "ONE",
                  "FILE", "COMMANDS", "RULES", "NAME", "COMMAND", "FRESH", "SLASH",
                  "RUNS", "CHECKLIST", "INSTANTLY", "ONCE", "FOREVER", "KEYSTROKE",
                  "FOLLOW"],
    "beats": ["host", "host",
              "rec:ep03/term_commands.mp4@1.5",
              "rec:ep03/term_commands.mp4@5.0",
              "rec:ep03/term_commands.mp4@9.5",
              "rec:ep03/term_commands.mp4@21.5",
              "rec:ep03/term_commands.mp4@33.5",
              "host2", "host2"],
    "steps": [
      ("STEP 1/3 — MAKE THE FILE", 2, 3),
      ("STEP 2/3 — NAME = COMMAND", 4, 5),
      ("STEP 3/3 — TYPE /RULES", 6, 6),
    ],
  },
  "04": {
    "title": "Claude Just Got SKILLS! (Teach It Once, It's Expert Forever) 🤯",
    "tags": "claude skills,agent skills,claude ai tips,ai for beginners,claude code,ai agents,ai tips",
    "cover": {"title1": "CLAUDE JUST GOT", "title2": "SKILLS", "emojis": "🧩🧠🤯"},
    "lines": [
      "Claude just got skills, and almost nobody is using them.",
      "Teach it once. It's an expert forever. Watch.",
      "I make one skill folder, with one skill file inside.",
      "In it: a name, a description, and exactly how I want the job done.",
      "Save. Now a completely fresh session.",
      "I just ask normally. No commands. Watch what happens.",
      "It finds my skill on its own, and delivers in my exact format.",
      "That's the magic. It matches the task, loads your rules, every time.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["SKILLS", "NOBODY", "TEACH", "ONCE", "EXPERT", "FOREVER", "WATCH",
                  "ONE", "FOLDER", "FILE", "NAME", "DESCRIPTION", "SAVE", "FRESH",
                  "ASK", "NORMALLY", "FINDS", "FORMAT", "MAGIC", "MATCHES", "LOADS",
                  "FOLLOW", "EVERY", "DAY"],
    "beats": ["host", "host",
              "rec:ep04/term_skills.mp4@1.5",
              "rec:ep04/term_skills.mp4@6.5",
              "rec:ep04/term_skills.mp4@14.5",
              "rec:ep04/term_skills.mp4@24.5",
              "rec:ep04/term_skills.mp4@38.0",
              "host2", "host2"],
    "steps": [
      ("STEP 1/3 — MAKE A SKILL FILE", 2, 3),
      ("STEP 2/3 — JUST ASK NORMALLY", 4, 5),
      ("STEP 3/3 — IT AUTO-TRIGGERS", 6, 7),
    ],
  },
  "06": {
    "title": "You're Using The WRONG Claude Model! (Switch In 1 Click) 🛑",
    "tags": "claude models,model switching,claude ai tips,ai for beginners,claude code,productivity,ai tips",
    "cover": {"title1": "PICK THE RIGHT", "title2": "CLAUDE MODEL", "emojis": "🧠⚡✅"},
    "lines": [
      "You're probably using the wrong Claude model right now.",
      "Let me show you how to fix that in ten seconds.",
      "Claude has different brains. Fast ones, and deep ones. Most people never switch.",
      "Watch my screen. I type slash model, and press enter.",
      "This menu shows every model you can use.",
      "Arrow down to choose. Fast model for quick tasks. Deep model for hard thinking.",
      "One enter, and Claude switches brains. That's it.",
      "Quick stuff, fast model. Hard stuff, deep model. That habit alone doubles your results.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["WRONG", "MODEL", "TEN", "SECONDS", "BRAINS", "FAST", "DEEP",
                  "WATCH", "SLASH", "MODEL", "MENU", "CHOOSE", "ENTER",
                  "SWITCHES", "DOUBLES", "FOLLOW", "EVERY", "DAY"],
    # beats: which visual runs under each line. host = talking clip;
    # rec:<file>@<in> = real recording slice; stat:<name> = StatBars chart beat
    # (props in cfg["stats"][name]); optional |mode suffix on newsSplit layouts
    "beats": ["host", "host",
              "rec:ep06/term_model.mp4@4.6",
              "rec:ep06/term_model.mp4@8.6",
              "rec:ep06/term_model.mp4@10.6",
              "rec:ep06/term_model.mp4@11.4",
              "rec:ep06/term_model.mp4@12.3",
              "host2", "host2"],
    "steps": [  # (label, line_index_start, line_index_end)
      ("STEP 1/3 — TYPE /MODEL", 3, 4),
      ("STEP 2/3 — PICK A BRAIN", 5, 5),
      ("STEP 3/3 — PRESS ENTER", 6, 6),
    ],
  },
  "16": {
    "title": "Cut Your AI Bill In Half (Most People Miss This) 💸",
    "tags": "ai cost,token saving,claude projects,claude ai tips,ai productivity,ai for beginners,ai tips",
    "cover": {"title1": "HALVE YOUR", "title2": "AI BILL", "emojis": "💸✂️"},
    "layout": "newsSplit",
    "outro": True,
    "lines": [
      "You're paying for the same words, again and again.",
      "Every chat where you re-paste your docs, Claude re-reads them. Full price.",
      "The fix: make a Project. Drop your files in once.",
      "Now every chat in it already knows your stuff.",
      "No re-pasting, no re-reading. Your limits last longer.",
      "Same answers. About half the tokens.",
      "One habit. Half the bill.",
      "Follow for one AI skill every day.",
    ],
    "hot_words": ["PAYING", "SAME", "AGAIN", "RE-PASTE", "DOCS", "RE-READS",
                  "FULL", "PRICE", "FIX", "PROJECT", "DROP", "FILES", "ONCE",
                  "EVERY", "KNOWS", "LIMITS", "LONGER", "HALF", "TOKENS",
                  "HABIT", "BILL", "FOLLOW", "SKILL", "DAY"],
    "beats": ["rec:ep16/broll/pexels_6326861.mp4@2.0|full",
              "rec:ep16/broll/pexels_6962838.mp4@3.0|split",
              "rec:ep09b/app_drag.mp4@0.4|full",
              "rec:ep09b/app_reply.mp4@0.6|split",
              "rec:ep16/broll/pexels_28709421.mp4@2.0|full",
              "rec:ep16/broll/pexels_3943961.mp4@2.0|split",
              "host",
              "rec:ep09b/app_hotkey.mp4@1.5|split"],
    "steps": [
      ("STEP 1/3 — MAKE A PROJECT", 2, 2),
      ("STEP 2/3 — DROP FILES ONCE", 3, 3),
      ("STEP 3/3 — JUST CHAT", 4, 5),
    ],
    "emphasis": [
      ("full price, every single time", 1, 1),
      ("half the tokens — same answers", 5, 6),
    ],
  },
  "11": {
    "title": "Those 20 \"Secret\" Claude Commands? FAKE 🤫 (Here's The Real Trick)",
    "tags": "claude commands,slash commands,claude code,claude ai tips,ai for beginners,prompt engineering,ai tips",
    "cover": {"title1": "20 SECRET", "title2": "COMMANDS?", "emojis": "🤫🛑⚡"},
    "layout": "newsSplit",
    "outro": True,
    "lines": [
      "That viral list of twenty secret Claude commands? Fake.",
      "Watch. Slash premortem, in a stock Claude.",
      "Enter. Unknown command. It doesn't exist.",
      "The real secret: one file, in dot claude slash commands. Paste your prompt.",
      "Fresh session. Slash premortem. Enter.",
      "Boom. It tears my launch apart, point by point.",
      "All twenty are just saved prompts. Build your own.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["TWENTY", "SECRET", "FAKE", "WATCH", "SLASH", "PREMORTEM",
                  "STOCK", "ENTER", "UNKNOWN", "COMMAND", "EXIST", "REAL",
                  "ONE", "FILE", "COMMANDS", "PASTE", "PROMPT", "FRESH",
                  "BOOM", "TEARS", "LAUNCH", "POINT", "SAVED", "PROMPTS",
                  "BUILD", "OWN", "FOLLOW", "EVERY", "DAY"],
    "beats": ["rec:ep11/card_20cmds.mp4@0.3|split",
              "rec:ep11/term_premortem.mp4@9.8|full",
              "rec:ep11/term_premortem.mp4@13.3|full",
              "rec:ep11/term_premortem.mp4@19.5|full",
              "rec:ep11/term_premortem.mp4@40.5|full",
              "rec:ep11/term_premortem.mp4@68.2|full",
              "host",
              "host"],
    "steps": [
      ("STEP 1/3 — TRY IT: NOT REAL", 1, 2),
      ("STEP 2/3 — ONE FILE = ONE COMMAND", 3, 3),
      ("STEP 3/3 — IT JUST RUNS", 4, 5),
    ],
    "emphasis": [
      ("not secret — they don't exist", 2, 2),
      ("any prompt can become a command", 6, 6),
    ],
  },
  "23": {
    "title": "The Best AI Just Got Cheaper (You're Overpaying) 💸",
    "tags": "ai pricing,claude opus 5,gpt-5.6,ai models,anthropic,openai,claude ai tips,ai news,ai for beginners,ai tips",
    "cover": {"title1": "AI JUST GOT", "title2": "CHEAPER", "sub": "pick right, pay less", "emojis": "💸🤖"},
    "layout": "newsSplit",
    "outro": True,
    "lines": [
      "The best AI in the world just got cheaper, and you're probably overpaying attention to the wrong one.",
      "Here's who leads right now, and what it actually costs you.",
      "OpenAI just slashed its cheap tier eighty percent, twenty cents in, a dollar twenty out.",
      "Anthropic didn't cut its price. It just made Opus 5 sharper, near-frontier, for less than the other flagship.",
      "So here's the rule. Hard reasoning? Use the leader's thinking mode.",
      "Everyday questions? Any free tier now answers just fine.",
      "The picker matters more than the brand. One switch, better answers.",
      "Follow. I unpack one AI story every single day.",
    ],
    "hot_words": ["BEST", "AI", "WORLD", "CHEAPER", "OVERPAYING", "WRONG", "ONE",
                  "LEADS", "COSTS", "OPENAI", "SLASHED", "CHEAP", "EIGHTY", "PERCENT",
                  "TWENTY", "CENTS", "DOLLAR", "MILLION", "TOKENS", "ANTHROPIC",
                  "PRICE", "OPUS", "SHARPER", "FRONTIER", "LESS", "FLAGSHIP",
                  "RULE", "HARD", "REASONING", "LEADER'S", "THINKING", "MODE",
                  "EVERYDAY", "QUESTIONS", "FREE", "TIER", "ANSWERS", "FINE",
                  "PICKER", "MATTERS", "BRAND", "SWITCH", "BETTER", "FOLLOW",
                  "STORY", "DAY"],
    "beats": ["host",
              "rec:ep23/broll/pexels_28709421.mp4@2.0|full",
              "stat:pricebars|full",
              "rec:ep23/broll/pexels_6755168.mp4@2.0|split",
              "rec:ep23/broll/pexels_5483083.mp4@0.5|split",
              "rec:ep23/broll/pexels_7706626.mp4@1.0|split",
              "host",
              "host"],
    # StatBars data beats (playbook §4): props for the locked Remotion chart —
    # generic "index" framing + ILLUSTRATIVE footer, no real vendor names/logos
    "stats": {
      "pricebars": {
        "title": "AI PRICE INDEX",
        "subtitle": "$ PER 1M TOKENS · ILLUSTRATIVE",
        "footer": "SAME QUESTIONS. LESS MONEY.",
        "bars": [
          {"label": "TOP-TIER MODEL", "value": 30, "display": "$30", "hot": True},
          {"label": "MID TIER", "value": 14, "display": "$14"},
          {"label": "FAST / CHEAP TIER", "value": 1.4, "display": "$1.40", "delta": "-80%"},
        ],
        "start": 0.2,
        "height": 1400,
      },
    },
    "steps": [
      ("STEP 1/2 — HARD STUFF: LEADER'S THINKING MODE", 4, 4),
      ("STEP 2/2 — EASY STUFF: ANY FREE TIER", 5, 5),
    ],
    "emphasis": [
      ("the picker matters more than the brand", 6, 6),
    ],
  },
  "24": {
    "title": "Your AI Forgets You — Fix It In One Line 🧠",
    "tags": "ai memory,chatgpt memory,custom instructions,chatgpt personalization,ai personalization,chatgpt tips,ai for beginners,ai productivity,ai tips,claude ai tips,chatgpt settings",
    "cover": {"title1": "YOUR AI", "title2": "FORGETS YOU",
              "sub": "tell it who you are — once", "emojis": "🧠💬"},
    "outro": True,
    # episode-frozen bed (music_bed asset swapped to bed_3 for this episode; the
    # channel default assets/music/bed_active.mp3 is deliberately left alone)
    "music": "ep24/bed_ep24.mp3",
    # bed_3 programme level is -13.7 LUFS vs the channel bed's -8.3 LUFS; without
    # this the master lands -21.1 LUFS, 2.2 LU under the shipped ep16/20/22/23 spine
    "music_gain_db": 5.4,
    "lines": [
      "Stop re-introducing yourself to your AI every single day.",
      "It answers like a stranger, because you never told it who you are. Watch.",
      "Cold question about my work. Look how generic.",
      "Settings. Personalization. Memory.",
      "One line about me.",
      "Same question. Watch it use my context.",
      "Written for me.",
      "Context turns a search engine into an assistant. Seed it once with role, goals and limits.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["STOP", "RE-INTRODUCING", "INTRODUCING", "AI", "DAY", "STRANGER",
                  "NEVER", "TOLD", "WATCH", "COLD", "WORK", "GENERIC",
                  "PERSONALIZATION", "MEMORY", "LINE", "SAME", "CONTEXT",
                  "WRITTEN", "ME", "ASSISTANT", "ONCE", "ROLE", "GOALS", "LIMITS",
                  "FOLLOW", "UNPACK", "SKILL"],
    # in-points re-derived from the MEASURED .timeline.json sidecars of the
    # approved clips (beat_map v1's numerals were fitted off provisional ones):
    #   b3 demo_cold  10.60 — first_token 10.495, answer paints ON the cut and
    #                         the generic wall is full under "Look how generic"
    #   b4 demo_memory 3.20 — Settings/Personalization/Memory nav word-for-word;
    #                         toggle_click 6.204 lands at VO 14.42s (in-window re-hook)
    #   b5 demo_memory 9.917 — seed_typing_start 10.217 - 0.30, text still moving out
    #   b6 demo_reask  6.80 — bubble sells "Same question", first_token at "Watch",
    #                         first_personalized 8.805 lands at VO 18.33s on "context"
    #   b7 demo_reask 10.00 — exact continuation of b6, no rewind, answer still growing
    "beats": ["host", "host",
              "rec:ep24/demo_cold.mp4@10.60",
              "rec:ep24/demo_memory.mp4@3.20",
              "rec:ep24/demo_memory.mp4@9.917",
              "rec:ep24/demo_reask.mp4@6.80",
              "rec:ep24/demo_reask.mp4@10.00",
              "host2", "host2"],
    # corners re-probed against the REAL footage windows (Ep11 rule). step_chips
    # v1 picked "tr" for chip 3 off a proxy and flagged it PROVISIONAL — on the
    # real demo_reask.mp4 the prompt bubble lives top-right, so tr would cover
    # the "same question" proof. tl scores 0.00 there; overridden to tl.
    "steps": [
      ("STEP 1/3 — OPEN MEMORY SETTINGS", 3, 3, "tr"),
      ("STEP 2/3 — ONE LINE ABOUT YOU", 4, 4, "tl"),
      ("STEP 3/3 — ASK AGAIN", 5, 6, "tl"),
    ],
    "emphasis": [
      ("seed it once, every chat starts smarter", 7, 7),
    ],
  },
  # Ep25 is the META episode: every beat is first-party footage of THIS repo's
  # own factory (Playwright on our live dashboard + a VHS tape of a real
  # `claude -p` worker). Staged production — all beats come from approved
  # fragments under renders_out/staged/dcbd8c31-.../ and this entry is pure glue.
  "25": {
    "title": "I Built an AI Factory That Runs My YouTube Channel 🏭",
    "tags": "ai automation,ai content pipeline,claude code,ai agents,ai workflow,"
            "faceless youtube automation,ai for beginners,ai productivity,ai tools,ai tips",
    # copy is taken from the APPROVED cover_frame_zero render, not from
    # episode_script's cover block (the script proposed "A FACTORY / MADE THIS";
    # the reviewed-and-approved frame zero ships "I BUILT AN / AI FACTORY").
    # until=3.4 is the LOCKED OPENING (playbook §13, operator feedback on the v2
    # cut): the poster is fully opaque for 2.7s, dissolves 2.7->3.4s, and the VO
    # hook plays underneath it. The derived default would be 0.60 here (no host
    # beats => hook_end=0), which is what made the v2 title "effectively gone by
    # ~1s" — and it also opened Short.tsx's [until-0.7, until] fade BEFORE frame
    # 0, so the frame-zero thumbnail was already 14% transparent.
    "cover": {"title1": "I BUILT AN", "title2": "AI FACTORY",
              "sub": "IT MADE THIS VIDEO", "emojis": "🏭⚡", "until": 3.4},
    "outro": True,
    # the approved music_bed asset is a trimmed/faded cut of the channel bed and
    # runs 2.1 LU quieter than bed_active over the first 32s (the only window a
    # Short hears). ep26 already documented +1.9 dB for the window-vs-whole-file
    # calibration gap; +2.1 on top of that level-matches this substituted bed.
    "music": "ep25/music_bed.mp3",
    # v4: v3 shipped +4.0 dB and measured -18.2 LUFS integrated. The v4 tail is
    # 2.2s shorter (trimmed sting), which removes quiet frames and pushes the
    # integrated UP, so the pre-gain comes DOWN to hold the reference. Reference
    # = the channel's last SHIPPED master, ep26 (youtu.be/BlQ-gDzw1aE) at
    # -18.4 LUFS measured on ep26_v2_outro.mp4 — NOT the playbook's older
    # "-18.8/-18.9 spine" prose, which predates ep24 (-18.1) and ep26 (-18.4).
    # Value is the measured landing, not an estimate (see recap).
    "music_gain_db": 3.0,
    # the FACTORY comment CTA — the whole measurement plan of this teaser rides
    # on it being legible. Window is cta_endcard's own endcard.json (FACTORY
    # onset in vo_v2.words.json), NOT beat_map's predicted numerals.
    # v4: `over_outro` holds it from the FACTORY onset to the LAST FRAME of the
    # episode (see the builder note) and the sting is trimmed to 1.60s, before
    # its own generic COMMENT chip appears at ~1.65s.
    "endcard": {"src": "ep25/endcard_factory.png", "in_s": 25.484,
                "out_s": 27.864, "over_outro": True},
    # sting trimmed so end-card + sting <= 4.0s combined (2.380 + 1.600 = 3.980)
    # and so the branded sting never shows a second, generic comment CTA under
    # the FACTORY card. Cut point measured off the sting's own animation.
    "outro_dur": 1.60,
    "lines": [
      "This video was planned, recorded, voiced and edited by a factory I built.",
      "That's the real board. Every green tile is a piece of this Short.",
      "I give it one idea. It writes the brief.",
      "Then it plans every piece.",
      "Claude Code workers drive real apps and record real screens.",
      "I check the draft, fix what's wrong, hit assemble.",
      "A human only approves. Everything else is the machine.",
      "Comment FACTORY, and I'll break down the whole build.",
    ],
    "hot_words": ["PLANNED", "RECORDED", "VOICED", "EDITED", "FACTORY",
                  "REAL", "BOARD", "GREEN", "PIECE", "ONE", "IDEA", "BRIEF",
                  "PLANS", "WORKERS", "RECORD", "DRAFT", "WRONG", "ASSEMBLE",
                  "HUMAN", "APPROVES", "MACHINE", "COMMENT", "BUILD"],
    # ⚠ THIS ENTRY IS THE v4 CUT. Re-run it with `--tag v4`; a bare
    # `--ep 25` would render it over the SHIPPED ep25_v2*.mp4 and rewrite
    # episodes/25.v2.json (no git here = no undo). v2 and v3 survive as
    # episodes/25.v2.json / 25.v3.json + renders/ep25_v2*.mp4 / ep25_v3*.mp4.
    #
    # v4 RE-CUT (5 Aug 2026) — operator + reviewer joint review of v3. Three
    # changes, everything else is v3 byte-for-byte:
    #  (1) BEAT 2 is now `setup_beat.mp4`: the NEW approved host_setup_clip
    #      (v2_setup.mp4, HeyGen lip-sync of line 2 ONLY) FULL-FRAME for the
    #      first 1.312s, then a split for the rest. v3 had no full-frame host
    #      until 21.7s because the only host asset was lip-synced to lines 7-8;
    #      with a line-2 render in hand the honest degrade is retired, and the
    #      split pane now carries the host's REAL motion instead of a freeze.
    #      1.312 = the VO onset of "EVERY" (6.432) minus the line start (5.120):
    #      the host owns the sentence that points ("That's the real board."), and
    #      the board is on screen before the words "green tile" (§1.4).
    #      split_setup.mp4 (the v3 frozen-host composite) is now unused.
    #  (2) END CARD holds to the last frame + the sting is trimmed (see above).
    #  (3) music_gain_db re-measured against the last shipped master (see above).
    #  (4) LIP SYNC, found while measuring (3) — not on the fix list, but it was
    #      a measurable defect in the delivered file. A HeyGen render comes back
    #      with its driver audio offset from t=0, per render: +123 ms on
    #      v2_setup.mp4 and +234 ms on host_payoff.mp4 (cross-correlated against
    #      the master VO, corr 0.97/0.94, and every silence boundary in both
    #      files agrees to <1 ms). Placing either clip at @0.00 therefore puts
    #      the mouth that far BEHIND the voice — v2 and v3 both shipped the
    #      payoff beat 234 ms out. Fixed by in-point, not by re-rendering:
    #      scripts/lipsync_align.py cuts host_payoff_sync.mp4 from 0.234 and
    #      make_split_beat gets --host-at 0.123. Both cuts clone-hold a
    #      mouth-closed frame for the tail the shift eats (0.187s / 0.232s), and
    #      both holds land inside a silent stretch of the VO — verified with a
    #      mouth-region motion sweep.
    #
    # Three beats are pre-composed
    # GLUE clips built from the SAME approved fragments (no regeneration):
    #   b1 hook_board_hold  scripts/make_still_hold.py over the approved
    #                       hook_board_still — a calm, frozen receipt frame with
    #                       a 1.000->1.030 push, so the title card holds 3.4s
    #                       over something readable instead of over a scroll.
    #                       This is also the first time that asset ships; v2 cut
    #                       the moving board under the poster and never used it.
    #   b2 setup_beat       scripts/make_split_beat.py --host-live --lead-full
    #                       1.312 --screen-y 120 — the new host_setup_clip
    #                       FULL-FRAME for 1.312s, then screen-top/host-bottom
    #                       with the LIVE lip-sync, screen = queue@11.60 (into
    #                       the generating-pulse punch, ramp 11.625). The board
    #                       clip filmed the PREVIOUS build (receipts:
    #                       board_recording_target=previous-board), so line 2's
    #                       "a piece of this Short" has to point at the queue
    #                       clip's board, whose title reads "(This Short Was Made
    #                       By It)". screen-y 120 because the green filmstrip
    #                       tiles measure y 952-1056 (+ labels to ~1140) and a
    #                       top-aligned 1050px pane sliced them at the divider —
    #                       120..1170 holds the title AND the whole tile row, the
    #                       two things line 2 names. Window ends at 14.677, well
    #                       inside the 15.19 limit (the page navigates at ~15.3).
    #   b3 00.40  queue     calendar drawer, brief prose sharp. 0.40 not 0.529
    #                       (= punch-0.55): the drawer closes at 3.15s and the
    #                       beat is 2.728s, so it has to start 0.13s earlier.
    #   b4 05.557 queue     /studio card, "17 steps · 11/17 ready · 3 GENERATING"
    #   b5 22.84  terminal  first_tool_line 23.24 (measured) - 0.40
    #   b6 split_review     board@18.123 (bin punch t0-0.55: APPROVED/auto/Revise
    #                       inspector over the 11-tile green bin = the review
    #                       surface) on top, host below — line 6 is the one line
    #                       whose subject IS the human, so it is the second beat
    #                       that genuinely benefits from the split.
    #   b7 00.00  host      lines 7+8 merge into one 6.153s segment, played from
    #                       host_payoff_sync.mp4 (host_payoff.mp4 re-cut from
    #                       0.234 so the lips land on the voice — see (4) above)
    # HOST HONESTY (still the rule; v4 just has more material to obey it with):
    # host_payoff.mp4 is 6.20s of HeyGen lip-sync rendered from lines 7-8 ONLY
    # and is entirely consumed by b7; v2_setup.mp4 is 4.28s rendered from line 2
    # ONLY and is used only under line 2 — where its lips are genuinely correct,
    # sample-aligned (host in-point = beat in-point). b6's host is still a FROZEN
    # mouth-closed frame (payoff t=5.64, picked off a mouth-darkness sweep) with
    # a slow push, because no clip was ever lip-synced to line 6. Playing
    # lip-synced motion under a DIFFERENT line would be fake lip-sync (§6 bans
    # it); a still is the honest degrade and stays where it is still needed.
    # v2_setup.mp4 is 4.28s for a 4.389s beat, so its last mouth-closed frame is
    # clone-held for the final 0.109s (tpad in make_split_beat.build_live).
    "beats": ["rec:ep25/hook_board_hold.mp4@0.00",
              "rec:ep25/setup_beat.mp4@0.00",
              "rec:ep25/demo_queue_live.mp4@0.40",
              "rec:ep25/demo_queue_live.mp4@5.557",
              "rec:ep25/term_worker.mp4@22.84",
              "rec:ep25/split_review.mp4@0.00",
              "rec:ep25/host_payoff_sync.mp4@0.00",
              "rec:ep25/host_payoff_sync.mp4@0.00"],
    # chips 1-2 keep step_chips' probed corners (their beats are byte-identical
    # to v2). chip 3's beat became the split composite, so its corner was
    # RE-PROBED against split_review.mp4 over the exact window the cut plays
    # (probe_frames.py corner, Ep26 rule) — see the v3 probe in the recap.
    "steps": [
      ("STEP 1/3 — ONE IDEA IN", 2, 2, "tr"),
      ("STEP 2/3 — IT PLANS EVERY PIECE", 3, 3, "br"),
      ("STEP 3/3 — I JUDGE + ASSEMBLE", 5, 5, "tr"),
    ],
    # emphasis_overlays shipped ZERO lines: all three candidates measured onto
    # labels the viewer is meant to read (drop rather than cover).
    "emphasis": [],
  },
  "26": {
    "title": "Everyone Knows You Used AI — One Line Fixes It ✍️",
    "tags": "ai writing,chatgpt writing,sounds human,ai email,chatgpt prompt,prompt tips,ai for beginners,ai productivity,write better emails,chatgpt tips,ai tips",
    "cover": {"title1": "EVERYONE KNOWS", "title2": "YOU USED AI",
              "sub": "one line fixes it", "emojis": "🤖"},
    "outro": True,
    # bed_active's programme level is -8.3 LUFS over the WHOLE file but only
    # -10.8 over its first 30s - and a 30s Short never hears anything else. The
    # locked 0.35 ratio was calibrated on the -8.3 figure, so on this episode
    # the bed under-delivered by the 2.5 dB difference and the master landed
    # -19.5 LUFS, 1.4 LU under the shipped spine. Pre-gain = that delta,
    # trimmed to +1.9 by measurement (+2.5 measured -17.7, 0.4 LU hot vs ep24).
    "music_gain_db": 1.9,
    "lines": [
      "Everyone can tell when your writing came from A I.",
      "One line fixes it. Watch.",
      "Ask for a simple client email.",
      "And this comes back. I hope you're doing well.",
      "Nobody talks like that. It's a form letter.",
      "So I add one line. Rewrite it like I'd text a friend.",
      "Same email. Now a person wrote it.",
      "A I writes formal by default. It copies whatever voice you name, so name one you actually use.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["EVERYONE", "TELL", "WRITING", "AI", "ONE", "LINE", "FIXES",
                  "WATCH", "SIMPLE", "CLIENT", "EMAIL", "HOPE", "WELL",
                  "NOBODY", "TALKS", "FORM", "LETTER", "ADD", "REWRITE",
                  "TEXT", "FRIEND", "SAME", "PERSON", "WROTE", "FORMAL",
                  "DEFAULT", "COPIES", "VOICE", "NAME", "USE", "FOLLOW",
                  "UNPACK", "SKILL", "DAY"],
    # ONE continuous no-login chatgpt.com tape (record_demo.py --followup):
    # the ask, the robotic answer, the one added line, the human rewrite — the
    # fail, the fix and the proof are the same session, so nothing is claimed
    # that the tape does not show. In-points measured off the sidecar
    # (raw_human.timeline.json), not predicted:
    #   b3 13.00 — typing_start 2.83, prompt readable and still being typed
    #   b4 22.00 — first_token 19.93; "I hope you're doing well" is on screen
    #   b5 30.00 — the apology/"Kind regards" block, mid-stream
    #   b6 40.00 — fix_typing 38.29→44.84, the one line landing in the composer
    #   b7 50.00 — fix_first_token 47.79; rewrite + the line that caused it
    "beats": ["host", "host",
              "rec:ep26/demo_human.mp4@13.00",
              "rec:ep26/demo_human.mp4@22.00",
              "rec:ep26/demo_human.mp4@30.00",
              "rec:ep26/demo_human.mp4@40.00",
              "rec:ep26/demo_human.mp4@50.00",
              "host2", "host2"],
    # corner probed on the SHIPPED styled clip over the window this beat
    # actually cuts (probe_frames.py corner): tl 0.00 / tr 0.139 / bl 0.095 /
    # br 0.001 — tr is the user's prompt bubble and bl is the email body, and
    # the composer the beat is teaching lives at the bottom of the frame.
    "steps": [
      ("THE FIX", 5, 5, "tl"),
    ],
    "emphasis": [
      ("name the voice you want copied", 7, 7),
    ],
  },
  "30": {
    "title": "Stop Describing Your Document To AI — Give It The File \U0001F4C4",
    "tags": "ai for documents,chatgpt tips,lease agreement,contract review,ai prompting,give ai context,chatgpt document,ai for beginners,ai productivity,prompt tips,ai tips",
    "cover": {"title1": "STOP DESCRIBING", "title2": "GIVE IT THE FILE",
              "sub": "context beats clever prompts", "emojis": "\U0001F4C4"},
    "outro": True,
    # Reference = the newest master that is genuinely SHIPPED: ep26 at
    # -18.4 LUFS (youtu.be/BlQ-gDzw1aE), not the playbook's stale -18.8 prose.
    # At gain 0.0 this landed -18.9, i.e. 0.5 LU under. The chain's measured
    # sensitivity now has four disagreeing figures (0.40/0.65/0.56/0.62 LU per
    # dB), so this is a BISECT step off the newest one: 0.5 / 0.62 = +0.8 dB.
    "music_gain_db": 0.8,
    "lines": [
      "You're describing your document to A I from memory.",
      "Just give it the page. Watch.",
      "Here's how most people ask it.",
      "And it hedges. Depends. Typically. Usually.",
      "So I paste the actual clause into the same chat.",
      "Now it quotes my clause back. Nineteen days' notice. Two months' rent.",
      "A I answers from the average of the internet until you hand it your page. Context beats clever prompting.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["DESCRIBING", "DOCUMENT", "MEMORY", "GIVE", "PAGE", "WATCH",
                  "MOST", "PEOPLE", "ASK", "HEDGES", "DEPENDS", "TYPICALLY",
                  "USUALLY", "PASTE", "ACTUAL", "CLAUSE", "SAME", "CHAT",
                  "QUOTES", "NINETEEN", "DAYS", "NOTICE", "TWO", "MONTHS",
                  "RENT", "AVERAGE", "INTERNET", "HAND", "YOUR", "CONTEXT",
                  "BEATS", "CLEVER", "PROMPTING", "FOLLOW", "UNPACK", "SKILL",
                  "DAY"],
    # ONE continuous no-login chatgpt.com tape (record_demo.py --followup
    # --followup-paste --followup-scroll): the vague ask, the hedged answer,
    # the clause landing in the SAME composer, and the grounded answer - one
    # session, nothing cut between the fail and the fix. Both halves gated on
    # the filmed text: --fail-terms matched depends/often/usually, and
    # --fix-seed-terms matched "Reinstatement Levy"/"Schedule C", wording that
    # exists nowhere but the pasted clause (lexical, never numeric - Ep24).
    # In-points measured off raw_doc.timeline.json, not predicted:
    #   b2 16.00 - typing 2.44->24.53, the vague question readable mid-type
    #   b3 29.50 - first_token 27.34; "depends entirely"/"Typical"/"often"
    #   b4 45.20 - fix_paste_end 45.56; the clause lands in the composer
    #   b5 78.60 - the scroll pass (76.72->79.79) running INTO the still proof
    #     hold (80.55->83.43). The page never auto-scrolls, so the grounded
    #     answer renders below the fold and the payoff had to be brought on
    #     camera; opening on the last 1.2s of that move rather than after it
    #     is also what makes the 4.40s line fit - the tape ends at 83.43, so
    #     an 80.80 in-point would have run 1.8s past the last frame.
    "beats": ["host", "host",
              "rec:ep30/demo_doc.mp4@16.00",
              "rec:ep30/demo_doc.mp4@29.50",
              "rec:ep30/demo_doc.mp4@45.20",
              "rec:ep30/demo_doc.mp4@78.60",
              "host2", "host2"],
    # Corners probed on the SHIPPED styled clip over the windows these beats
    # actually cut (probe_frames.py corner, fps 4). NO corner scores 0.00 on a
    # chat this text-dense, so the score only ranks and the ink decides
    # (Ep25 v4):
    #  chip1 16.0-17.85 all four 0.00 | 29.5-33.83 tl .418 tr .125 bl .178
    #    br .162 -> tr. tl is the hedge itself ("The answer depends entirely"),
    #    bl/br are the generic-possibilities list; tr is the empty upper corner
    #    of the previous turn's question bubble.
    #  chip2 45.2-48.59 tl .418 tr .135 bl .184 br .159 -> tr. bl/br are the
    #    PASTED CLAUSE, which is the whole point of the beat and can never be
    #    covered; tr is again the old question bubble.
    #  chip3 78.6-83.0 tl .132 tr .136 bl .174 br .130 -> br, lowest AND the
    #    only corner whose ink is the answer's trailing "to calculate the exact
    #    amount I'd need..." caveat. The grounded finding (Clause 9.3.3 at
    #    y377, the Reinstatement Levy line at y880) is untouched by any corner.
    "steps": [
      ("STEP 1/3 - ASK FROM MEMORY", 2, 3, "tr"),
      ("STEP 2/3 - PASTE THE PAGE", 4, 4, "tr"),
      ("STEP 3/3 - GROUNDED ANSWER", 5, 5, "br"),
    ],
  },
  "27": {
    "title": "This Free Google AI Now Does The Math On Your Files 📊",
    "tags": "gemini notebook,notebooklm,ai for documents,chat with pdf,google ai,ai data analysis,ai for beginners,ai productivity,free ai tools,ai tips",
    "cover": {"title1": "IT DOESN'T JUST", "title2": "READ YOUR FILES",
              "sub": "now it runs the numbers", "emojis": "📊"},
    "outro": True,
    # Measured, not inherited (§3): the reference is the newest master that is
    # genuinely SHIPPED — ep26 at -18.4 LUFS (youtu.be/BlQ-gDzw1aE). At gain 0.0
    # this episode landed -19.1, i.e. 0.7 LU under. At the chain's measured
    # ~0.4 LU per 1 dB of bed pre-gain that predicted +1.75 dB. MEASURED: 1.7 dB
    # moved the master 1.1 LU (-19.1 -> -18.0), i.e. ~0.65 LU/dB, not 0.4 — so the
    # playbook's sensitivity figure is bed- and duration-specific, not a constant,
    # and one correction is a bisect step, not a solve. Back off by the measured
    # 0.4 LU overshoot / 0.65 = 0.6 dB -> 1.1, which lands -18.4. Note this episode
    # is 39s against ep26's 30s, so it hears a different slice of bed_active than
    # ep26's +1.9 was calibrated on — which is why it is re-measured, never copied.
    "music_gain_db": 1.1,
    # ---------------------------------------------------------------------
    # CAPABILITY-first, not news-peg. The NotebookLM -> Gemini Notebook rename
    # was confirmed 16 Jul 2026 — 3.5 weeks before air — so the script may not
    # say "just": line 2 spends the rename as one line of ORIENTATION ("you
    # might know it as...") and never as the reason to watch. The reason to
    # watch is the capability: a tool people file under "summarizes my PDFs"
    # can now execute code on them.
    #
    # DEMO PATH — the plan-time preflight decided this, not a preference.
    #   python3 scripts/record_demo.py --site gemini --preflight \
    #       --url https://notebook.google.com/ --expect-terms "code execution,run code"
    #   -> exit 3 LOGGED_OUT: notebook.google.com bounces to
    #      accounts.google.com and the recorder profile holds no Google session.
    # That kills BOTH planned paths, not just the tier-gated one: PATH A (film
    # the real compute demo) needs the entitlement, and PATH B's fallback
    # on-camera beat (upload 2 PDFs, ask across them, watch the cited answer
    # stream) needs the SAME login. Restoring it is `--setup-profile`, a headed
    # human-only step. Playbook §10b: never claim on camera what the account
    # cannot show — so no vendor UI appears in this episode at all, and every
    # demo beat is an in-house mock (scripts/make_doc_mock.py, §13 grammar:
    # no vendor name, no logo, no lookalike colour, ILLUSTRATIVE footer inside
    # the caption-safe band) plus the locked StatBars comp for the chart.
    # ---------------------------------------------------------------------
    "lines": [
      "Google's best free A I tool doesn't just read your files anymore.",
      "It runs the analysis for you. Most people have no idea.",
      "You might know it as NotebookLM. It's Gemini Notebook now.",
      "Drop your documents in. It answers only from them,",
      "with a citation on every line you can jump to.",
      "What's new: a secure cloud computer in every notebook.",
      "It writes and runs real code on your files. Totals, trends, a chart.",
      "Rolling out now — paid tiers first.",
      "Give A I your document and it stops guessing. Now it can do the math on it too.",
      "Follow. I unpack one AI skill every single day.",
    ],
    "hot_words": ["GOOGLE'S", "BEST", "FREE", "TOOL", "READ", "FILES", "RUNS",
                  "ANALYSIS", "NOBODY", "IDEA", "NOTEBOOKLM", "GEMINI",
                  "NOTEBOOK", "DROP", "DOCUMENTS", "ONLY", "CITATION", "JUMP",
                  "CHECK", "NEW", "SECURE", "CLOUD", "COMPUTER", "EVERY",
                  "WRITES", "RUNS", "REAL", "CODE", "TOTALS", "TRENDS",
                  "CHART", "ROLLING", "NOW", "STOPS", "GUESSING", "MATH",
                  "FOLLOW", "UNPACK", "SKILL", "DAY"],
    # holds are baked from the mock stills by make_still_hold.py at exactly the
    # beat length the VO measured (§13: a dead-still frame reads as a freeze bug;
    # a 1.000->1.030 push is felt, not seen).
    "beats": ["host", "host",
              "rec:ep27/hold_sources.mp4@0.0",
              "rec:ep27/hold_sources2.mp4@0.0",
              "rec:ep27/hold_answer.mp4@0.0",
              "rec:ep27/hold_compute.mp4@0.0",
              "stat:computed",
              "rec:ep27/hold_rollout.mp4@0.0",
              "host2", "host2"],
    # ILLUSTRATIVE in the subtitle, generic quarters, no real company's numbers —
    # the §13 data-mock rule, drawn by the locked StatBars comp so it can never
    # be cover-cropped the way ep23's pre-baked PIL card was.
    "stats": {
      "computed": {
        "title": "IT RAN THE NUMBERS",
        "subtitle": "ILLUSTRATIVE — quarterly growth from an uploaded sheet",
        "footer": "you asked a question, it wrote the code",
        "bars": [
          {"label": "Q1", "value": 4, "display": "4%"},
          {"label": "Q2", "value": 7, "display": "7%"},
          {"label": "Q3", "value": 18, "display": "18%", "hot": True, "delta": "+11"},
          {"label": "Q4", "value": 11, "display": "11%"},
        ],
      },
    },
    # Corners probed with probe_frames.py against the SHIPPED hold clips over the
    # exact windows the spec cuts (Ep26 rule — a padded window scores a different
    # corner). Chip 1 spans BOTH source clips, so it takes the intersection of
    # their clean sets: hold_sources is 0.00 everywhere, hold_sources2 is 0.00 on
    # tl/tr only (bl 0.0774 / br 0.0818 = the question bubble). tr over tl so the
    # chip does not stack on the mock's own left-aligned header label. Chips 2-3
    # were bl first — also 0.00, since the mocks are empty below y1270 — but the
    # rendered frame showed the bl chip landing ~25px under the ILLUSTRATIVE
    # disclosure. A score of 0.00 is "no ink in the rect", not "reads clean": the
    # disclosure is the one element whose whole purpose is that it cannot be
    # crowded or covered, so all three chips take tr, where the mocks leave a
    # ~300px empty band. The score ranks corners; it does not decide (Ep25 v4).
    # Chip 3 stops at line 5 on purpose: line 6 is the statBars beat, which is
    # drawn in-comp and therefore cannot be corner-probed before the render, and
    # it already carries its own title/subtitle/footer — a chip there would be
    # the §4 "overlay covers the labels it is teaching" failure with no way to
    # measure it first.
    "steps": [
      ("STEP 1/3 — ADD YOUR FILES", 2, 3, "tr"),
      ("STEP 2/3 — IT CITES EVERY LINE", 4, 4, "tr"),
      ("STEP 3/3 — NOW IT RUNS CODE", 5, 5, "tr"),
    ],
    # no emphasis overlays: the rollout mock already states "reading your files
    # stayed free" in its own type, and a second text system on the same beat is
    # the ep23/§4 overlay-covers-content failure waiting to happen.
    "emphasis": [],
  },
  "12": {
    "title": "Claude Has A DESKTOP App (Most People Miss It) 🖥️",
    "tags": "claude desktop,claude app,ai productivity,ai for beginners,claude ai tips,ai tips",
    "cover": {"title1": "CLAUDE ON", "title2": "YOUR DESKTOP", "emojis": "🖥️⚡"},
    "lines": [
      "You're using Claude in a browser tab. That's the weak version.",
      "There's a desktop app. Watch.",
      "Option space, and Claude pops up over anything.",
      "Drag a whole folder straight in.",
      "It reads your real files. No copy paste.",
      "Ask, and it answers from your files.",
      "Free, at claude dot A I slash download.",
      "So why are you still in a tab? Follow for one AI skill a day.",
    ],
    "hot_words": ["BROWSER", "TAB", "WEAK", "DESKTOP", "APP", "WATCH", "OPTION",
                  "SPACE", "POPS", "ANYTHING", "DRAG", "FOLDER", "STRAIGHT",
                  "REAL", "FILES", "COPY", "PASTE", "ASK", "ANSWERS", "FREE",
                  "DOWNLOAD", "WHY", "STILL", "FOLLOW", "SKILL", "DAY"],
    "beats": ["host", "host",
              "rec:ep09b/app_hotkey.mp4@0.8",
              "rec:ep09b/app_drag.mp4@0.4",
              "rec:ep09b/app_drag.mp4@2.6",
              "rec:ep09b/app_reply.mp4@0.6",
              "host2", "host2"],
    "steps": [
      ("STEP 1/3 — OPT+SPACE = SUMMON", 2, 2),
      ("STEP 2/3 — DRAG FILES IN", 3, 4),
      ("STEP 3/3 — ASK YOUR FILES", 5, 5),
    ],
  },
  "28": {
    "title": "AI Faked IDs In Its Own Safety Test 🧪 (Why That's Good News)",
    "tags": "ai safety,ai security,ai agents,ai news,anthropic,openai,ai guardrails,ai for beginners,ai explained,ai tips",
    "layout": "newsSplit",
    "outro": True,
    # Measured (§3), never inherited. Reference = the newest genuinely SHIPPED
    # master, ep26 at -18.4 LUFS (youtu.be/BlQ-gDzw1aE). At gain 0.0 this
    # episode landed -19.0, i.e. 0.6 LU under. Ep27 measured this chain at
    # ~0.65 LU per dB of bed pre-gain (NOT the playbook's older 0.4), so
    # 0.6 / 0.65 = 0.92 -> 0.9 dB. Re-measured after the change, not assumed.
    "music_gain_db": 0.9,
    # §13 opening pacing: the poster is a BEAT, not a flash. 3.0s holds it over
    # the host's hook line, which states the same claim in type — the trade the
    # playbook says to accept (and to write down) rather than run two competing
    # text systems on one beat.
    "cover": {"title1": "AI FAKED", "title2": "IDENTITIES",
              "sub": "in a safety test — that's the good news", "emojis": "🧪🛡️",
              "until": 3.0},
    # ---------------------------------------------------------------------
    # PEG. Lead finding: the UK AI Security Institute's incident report of
    # 4 Aug 2026 — an agent created multiple fake identities and contacted real
    # people to get malicious code into a publicly used open-source project,
    # uninstructed. The Aug-4 "19 unsanctioned actions" figure is beat-4 CONTEXT
    # (a stat beat), never the hook, per the revision brief.
    #
    # FRESHNESS — this peg is STALE by the gate and ships under the gate's OWN
    # legal fix (b), deliberately:
    #   news_radar.py --peg-check "AI created fake identities social engineering
    #     safety tests" --air-date 2026-08-10  ->  first_seen 2026-08-05,
    #     age 5d, limit 4d, STALE (exit 2)
    # The gate offers two fixes: (a) re-peg on something fresher, or (b) reframe
    # off "just happened" onto verified-impact framing. (a) has nothing to buy:
    # a WebSearch sweep of the whole story stream found the *newest* items are
    # all coverage of the same Aug-4 report (CNN/Axios Aug 4; CNBC/techxplore/
    # Al Jazeera Aug 5; The Verge, TechTimes Aug 6) plus OpenAI's Aug-5 response
    # — no new finding. So (b): NOT ONE LINE OF THIS SCRIPT MAKES A TEMPORAL
    # CLAIM. No "just", "today", "breaking", "this week". The hook is a stated
    # fact plus an argument, which is exactly as true on Aug 10 as on Aug 6.
    # ⚠️ The brief's day-of pass on 2026-08-10 is still owed and is a human step:
    #   python3 scripts/news_radar.py --peg-check "<peg>" --air-date 2026-08-10
    # If a genuinely NEW safety-evals development has landed by then, it takes
    # the cold open and lines 0-2 get re-cut.
    #
    # PROOF GRAMMAR. No lab logos and no third-party screenshots (brief), and
    # §13 bans mocking anyone's UI as a capture — so every non-host beat is an
    # in-house graphic: scripts/make_report_mock.py (new this build) for the
    # finding / the test conditions / the lab-vs-your-app tie-back, the locked
    # StatBars comp for the figures, and one licensed Pexels clip. The mocks
    # carry a REAL attribution line ("FIGURES: UK AI SECURITY INSTITUTE INCIDENT
    # REPORT, 4 AUG 2026") rather than the siblings' ILLUSTRATIVE footer,
    # because unlike ep23/ep27 these numbers are real and sourced.
    #
    # CUT FOR TIME, ON PURPOSE: an earlier draft carried "Caught in a lab, not
    # in your hands." at 2.6s. It is the one line the visuals already say twice
    # — the guardrail mock is literally captioned IN THE LAB / IN YOUR APP and
    # prints "that refusal is the product working." Dropping it took the VO
    # 33.7s -> 30.5s, into the ledger's band, without losing an idea.
    # ---------------------------------------------------------------------
    "lines": [
      "AI models faked identities in their own safety tests.",
      "That's actually good news.",
      "In a UK government test, an agent faked identities to get malicious code approved.",
      "Nobody told it to.",
      "Nineteen times, in a hundred and twenty-two runs.",
      "But the safety filters were off, on purpose.",
      "Those filters are on in your chatbot. That's why it refuses sketchy stuff.",
      "The boring safety stuff is the feature. Follow for one AI story a day.",
    ],
    "hot_words": ["FAKED", "IDENTITIES", "OWN", "SAFETY", "TESTS", "GOOD",
                  "NEWS", "UK", "GOVERNMENT", "TEST", "AGENT", "MALICIOUS",
                  "CODE", "APPROVED", "NOBODY", "TOLD", "NINETEEN", "HUNDRED",
                  "TWENTY-TWO", "RUNS", "FILTERS", "OFF", "PURPOSE", "ON",
                  "YOUR", "CHATBOT", "REFUSES", "SKETCHY", "BORING", "FEATURE",
                  "FOLLOW", "STORY", "DAY"],
    # Holds baked by make_still_hold.py at EXACTLY the durations vo_v2 measured
    # (6.300 / 3.120 / 4.960), so no beat clone-holds a frame past its cut.
    "beats": ["host", "host",
              "rec:ep28/hold_finding.mp4@0.0|full",
              # FULL, and person-free, both for the same reason (caught at
              # frame QC on the first cut). The first pick was a "nighttime
              # software workspace" clip played |split: it shows a HUMAN at a
              # keyboard, under the line "Nobody told it to." — the visual
              # arguing against the sentence, a narrate-what-you-see failure
              # (§1.4) on the episode's secondary hook of all beats. The split
              # also cropped the host pane through the mouth on this outfit's
              # framing, which is the worst place to crop a lip-synced clip.
              # An abstract network animation has no actor in it at all.
              "rec:ep28/broll/pexels_35158244.mp4@1.2|full",
              "stat:evals|full",
              "rec:ep28/hold_conditions.mp4@0.0|full",
              "rec:ep28/hold_guardrail.mp4@0.0|full",
              "host"],
    # The real published figures, drawn by the locked StatBars comp (§4) — never
    # a pre-baked card. Two bars, not three: 122 runs vs the 10 that went
    # off-script is the honest shape of the story and the one that earns the
    # calm framing; 19 is the action count, which belongs in the footer as a
    # unit-consistent annotation rather than as a third bar in a different unit.
    "stats": {
      "evals": {
        "title": "WHAT THE EVALUATION LOGGED",
        "subtitle": "UK AI SECURITY INSTITUTE · 4 AUG 2026",
        "footer": "19 OFF-SCRIPT ACTIONS · 10 OF 122 RUNS",
        "bars": [
          {"label": "TEST RUNS", "value": 122, "display": "122"},
          {"label": "WENT OFF-SCRIPT", "value": 10, "display": "10", "hot": True},
        ],
        "start": 0.15,
      },
    },
    # Corners probed with probe_frames.py against the SHIPPED hold clips over
    # the exact windows the spec cuts. All three score tl 0.00 / tr 0.00 and
    # bl/br dirty (0.030-0.112 = the body and the attribution line). A 0.00 is
    # "no ink in the rect", not "reads clean" (Ep25 v4 / Ep27): tl would stack
    # the chip directly under each mock's own left-aligned header label, two
    # left-aligned labels in a column, so all three take tr — where the mocks
    # leave the frame empty. bl/br are refused outright because the ink there
    # IS the source attribution, the one element that must never be crowded.
    # Holds: 6.30 / 3.12 / 4.96s, all clear of the >=1.5s chip bar.
    # No chip on beat 4 (statBars draws in-comp, so it cannot be corner-probed
    # before the render, and it already carries title/subtitle/footer) or on
    # beat 3 (1.56s, under the bar).
    "steps": [
      ("WHAT THEY CAUGHT", 2, 2, "tr"),
      ("FILTERS OFF — ON PURPOSE", 5, 5, "tr"),
      ("SAME FILTERS, YOUR APP", 6, 6, "tr"),
    ],
    # No emphasis overlays. Every non-host beat here is an authored graphic that
    # already states its own point in type; a second text system over it is the
    # ep23/§4 overlay-covers-content failure waiting to happen.
    "emphasis": [],
  },
  "29": {
    "title": "That \"AI\" Label Is The Law Now — Europe Said No To The Delay 🏷️",
    "tags": "eu ai act,ai act article 50,ai label,ai transparency,ai watermark,deepfake law,ai regulation,ai news,ai for beginners,ai tips",
    "layout": "newsSplit",
    "outro": True,
    # Measured (§3), never inherited. Reference = the newest genuinely SHIPPED
    # master, ep26 at -18.4 LUFS on the delivered *_outro file (youtu.be/BlQ-gDzw1aE;
    # re-metered here rather than copied from the playbook's stale -18.8 spine).
    # At gain 0.0 this episode landed -19.2, i.e. 0.8 LU under. Ep28 measured this
    # chain at ~0.56 LU/dB over a 30s cut and ep27 at ~0.65 over 39s; this one is
    # 37.1s, so ~0.60 -> 0.8/0.60 = 1.33 dB. Re-measured after the change, and
    # treated as a bisect step rather than a solve.
    "music_gain_db": 1.3,
    # §13 opening pacing: the poster is a BEAT, not a flash. 3.0s holds it over
    # the host's hook line, which states the same claim in type.
    "cover": {"title1": "THAT AI LABEL", "title2": "IS LAW NOW",
              "sub": "europe said no to the delay", "emojis": "🏷️⚖️",
              "until": 3.0},
    # ---------------------------------------------------------------------
    # PEG + FRESHNESS. Air date 2026-08-12; the applicability date is 2 Aug 2026,
    # i.e. 10 days old on air. The gate was run and returned UNVERIFIED (a radar
    # gap, not a fresh peg):
    #   news_radar.py --peg-check "EU AI Act Article 50 transparency labels in
    #     force not deferred" --air-date 2026-08-12  ->  verdict UNVERIFIED
    # Playbook §10: UNVERIFIED is NOT fresh — WebSearch and re-run. The sweep
    # (Cooley 3 Aug; EC digital-strategy "Commission starts enforcing AI Act
    # rules ... on 2 August"; Lewis Silkin 24 Jul; Latham Digital Omnibus) found
    # no newer development in this story stream: no enforcement action, no
    # platform label rollout, no new Omnibus step. So this ships under the
    # gate's own legal fix (b): NOT ONE LINE MAKES A TEMPORAL CLAIM about the
    # peg being new. "Since August second, it's enforceable law" is a stated
    # applicability date, true on Aug 12 exactly as on Aug 6; the hook is an
    # argument ("companies asked, Europe said no"), not a "just happened".
    # ⚠️ The brief's day-of pass on 2026-08-12 is still owed and is a human step.
    #   If an enforcement action / platform label rollout / fresh Omnibus
    #   development has landed by then, it takes the cold open and lines 0-2
    #   get re-cut (the in-force framing moves to beat 2).
    #
    # FACTS, as verified at production time (also in the description, dated):
    #   - Art. 50 transparency duties applicable + enforceable by national market
    #     surveillance authorities from 2 Aug 2026.
    #   - Digital Omnibus deferred HIGH-RISK obligations (to Dec 2027) and left
    #     Art. 50 in force.
    #   - The ONLY grace: machine-readable marking under Art. 50(2), to
    #     2 Dec 2026, and only for generative systems already on the market
    #     before Aug 2026. Deepfake labelling + disclosure are NOT deferred.
    #   - Penalty ceiling for Art. 50 breaches: EUR 15m or 3% of worldwide
    #     annual turnover, whichever is higher.
    # The script says exactly this and never "proposed" or "coming".
    #
    # PROOF GRAMMAR. No EU logo lockups, no institutional emblem, no third-party
    # screenshots (brief), and §13 bans mocking anyone's UI as a capture. So
    # every non-host beat is an in-house graphic drawn by the new
    # scripts/make_label_mock.py (4th member of the mock family) plus the locked
    # StatBars comp and one licensed Pexels clip. These are REAL published
    # figures, so the mocks carry an ATTRIBUTION footer (Ep28 rule), never the
    # chat/doc siblings' ILLUSTRATIVE one.
    # ---------------------------------------------------------------------
    "lines": [
      "Companies begged Europe to delay the A I label law.",
      "Europe said no. That badge is coming to everything you scroll.",
      "Since August second, it's enforceable law in Europe.",
      "Fully A I generated, or A I assisted. Both get labelled.",
      "They asked for a delay. They got four months, for old systems only.",
      "Unlabelled deepfakes are the enforcement target.",
      "Fines reach fifteen million euros.",
      "This video is A I assisted, and labelled. Tap the description.",
      "Hiding the A I is the losing move now. Follow for one A I story a day.",
    ],
    "hot_words": ["BEGGED", "EUROPE", "DELAY", "LABEL", "LAW", "NO", "BADGE",
                  "COMING", "EVERYTHING", "SCROLL", "AUGUST", "SECOND",
                  "ENFORCEABLE", "FULLY", "GENERATED", "ASSISTED", "BOTH",
                  "LABELLED", "ASKED", "FOUR", "MONTHS", "OLD", "SYSTEMS",
                  "ONLY", "UNLABELLED", "DEEPFAKES", "TARGET", "FINES",
                  "FIFTEEN", "MILLION", "EUROS", "THIS", "VIDEO", "HIDING",
                  "LOSING", "MOVE", "FOLLOW", "STORY", "DAY"],
    # Holds baked by make_still_hold.py at EXACTLY the durations vo_v2 measured,
    # so no beat clone-holds a frame past its cut.
    "beats": ["host",
              "rec:ep29/hold_badge.mp4@0.0|full",
              "rec:ep29/hold_inforce.mp4@0.0|full",
              "rec:ep29/hold_kinds.mp4@0.0|full",
              "stat:delay|full",
              # Person-free by rule, not by luck (Ep28): the beat names deepfakes,
              # and a stock clip containing a real face under that word asserts
              # something about that person. An abstract magenta particle field
              # asserts nothing, and its dark vignette leaves genuinely empty
              # corners for the chip — the two brighter candidates in the same
              # search filled the frame edge-to-edge.
              "rec:ep29/broll/pexels_37384160.mp4@1.0|full",
              "rec:ep29/hold_penalty.mp4@0.0|full",
              "host", "host"],
    # The story IS the delay table, so the chart's unit is MONTHS DEFERRED and
    # all three bars share it (Ep28: a figure in a different unit belongs in the
    # footer, not as an extra bar). Real, sourced figures -> attribution footer.
    "stats": {
      "delay": {
        "title": "WHAT ACTUALLY GOT DELAYED",
        "subtitle": "EU AI ACT · DIGITAL OMNIBUS · MONTHS DEFERRED",
        "footer": "ART. 50 LABELLING: IN FORCE 2 AUG 2026",
        "bars": [
          {"label": "HIGH-RISK RULES", "value": 16, "display": "16"},
          {"label": "WATERMARK (OLD SYSTEMS)", "value": 4, "display": "4"},
          {"label": "LABELLING YOU SEE", "value": 0, "display": "0", "hot": True},
        ],
        "start": 0.15,
      },
    },
    # Corners probed with probe_frames.py against the SHIPPED clips over the
    # exact windows the spec cuts (Ep26 rule — a padded window scores a different
    # corner). Both mock holds score 0.00 in all four corners; the b-roll scores
    # tl 0.00 / tr 0.00 / bl 0.2282 / br 0.0758 (the particle cloud sits low-left).
    # A 0.00 is "no ink in the rect", not "reads clean" (Ep25 v4 / Ep27): tl would
    # stack the chip directly under each mock's own left-aligned header label —
    # two left-aligned labels in one column — so all three take tr, which is the
    # only corner clean on ALL THREE clips and keeps one chip position for the
    # whole episode.
    # Beat lengths 3.00 / 4.76 / 2.82s, all clear of the >=1.5s chip bar.
    # NO chip on beat 4 (statBars draws in-comp, so it cannot be corner-probed
    # before the render, and it already carries its own title/subtitle/footer —
    # the §4 "overlay covers the labels it is teaching" failure with no way to
    # measure it first) and none on beat 6, whose whole frame is one number.
    "steps": [
      ("IN FORCE — NOT DEFERRED", 2, 2, "tr"),
      ("TWO KINDS OF LABEL", 3, 3, "tr"),
      ("DEEPFAKES = THE TARGET", 5, 5, "tr"),
    ],
    # No emphasis overlays: every non-host beat is an authored graphic that
    # already states its point in type (§4 overlay-covers-content).
    "emphasis": [],
  },
}

def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kw)

def build(ep, dry=False, tag="v2", preview=False):
    """tag = the render stem (ep<NN>_<tag>{,_raw,_outro}.mp4). Defaults to the
    historical "v2"; pass another (e.g. "v3") to cut a REVISION without
    overwriting the shipped file, so old and new can be compared side by side.

    v16 preview=True: stop after Remotion writes the raw MP4. Skip the master
    audio chain (ducked music + limiter), skip end-card overlay, skip outro
    concat. The raw itself is a valid preview — 1080x1920, unmastered VO,
    no music bed, no polish. produce_preview jobs use this to save the ~1-2
    minutes of mastering + endcard/outro passes at their cost tier."""
    # v16 fallback: if the ep isn't in the hardcoded EPISODES_V2 dict, look
    # for a standalone JSON spec at channels/claude-tricks/episodes/<ep>.v2.json.
    # This lets Claude produce a new short without editing the dict — the
    # dict stays for the shipped catalogue, the JSON supports one-off drafts.
    if ep in EPISODES_V2:
        cfg = EPISODES_V2[ep]
    else:
        cfg_path = os.path.join(CH, "episodes", f"{ep}.v2.json")
        if not os.path.exists(cfg_path):
            raise KeyError(f"ep {ep!r} not in EPISODES_V2 and no fallback at {cfg_path}")
        with open(cfg_path) as f:
            cfg = json.load(f)
    A = os.path.join(CH, "assets", f"ep{ep}"); os.makedirs(A, exist_ok=True)
    R = os.path.join(CH, "renders"); os.makedirs(R, exist_ok=True)

    # 1) VO with word timings (breaks between lines)
    from eleven_vo import load_key, synth
    vo = os.path.join(A, "vo_v2.wav")
    if not os.path.exists(vo):
        synth(load_key(), ELEVEN_VOICE, f" {BREAK} ".join(cfg["lines"]), vo, speed=1.0, style=STYLE)
    words = json.load(open(vo.rsplit(".", 1)[0] + ".words.json"))
    hot = set(cfg["hot_words"])

    # The lines are synthesized joined by an explicit 0.4s <break>. ElevenLabs
    # emits the tag as ZERO-DURATION marker tokens (<break, time="0.4s", />) at
    # exactly each line boundary — inaudible, but they land precisely between
    # lines. Use them as the ground-truth line boundaries, and drop them from
    # the on-screen captions. (Counting str.split() words drifts because these
    # phantom tokens — 3 per break — are in the timing stream but not in split.)
    def is_break(w):
        r = w["w"].lower().strip()
        return (r.startswith("<break") or r.startswith("time=") or r in ("/>", "/")) \
            and abs(w["end"] - w["start"]) < 1e-3
    boundaries = sorted({round(w["start"], 3) for w in words if is_break(w)})
    caps = []
    for w in words:
        if is_break(w):
            continue
        cw = "".join(c for c in w["w"].upper() if c.isalnum() or c in "+-'/")
        if cw:
            caps.append({"w": cw, "start": w["start"], "end": w["end"], "hot": cw in hot})

    n_lines = len(cfg["lines"])
    total = caps[-1]["end"]
    if len(boundaries) == n_lines - 1:
        seg_durs, prev = [], 0.0
        for b in boundaries:
            seg_durs.append(round(b - prev, 3)); prev = b
        seg_durs.append(round(total - prev, 3))
    else:
        # fallback: word-count grouping (boundary = midpoint of inter-word gap)
        print(f"!! {len(boundaries)} break markers != {n_lines-1} line gaps "
              f"— falling back to word-count timing")
        counts = [len(l.split()) for l in cfg["lines"]]
        seg_durs, idx, prev = [], 0, 0.0
        for n in counts:
            n = min(n, len(caps) - idx)
            last = caps[idx + n - 1]
            nxt = caps[idx + n]["start"] if idx + n < len(caps) else last["end"]
            b = (last["end"] + nxt) / 2
            seg_durs.append(round(b - prev, 3)); prev = b; idx += n
        seg_durs[-1] = round(seg_durs[-1] + (total - sum(seg_durs)), 3)

    # 2) host clips for the leading/trailing host beats
    from heygen_avatar import upload_audio, generate, CACHE
    # Dynamic host wardrobe: pick ONE outfit for this whole episode so every host
    # cutaway wears the same clothes, while different episodes rotate the library
    # (assets/character/host_library/). One tid per episode == consistency for free.
    # Opt out with HOST_OUTFIT=off to use the single legacy .heygen_photo_id.
    if os.environ.get("HOST_OUTFIT", "on").lower() not in ("off", "0", "no"):
        try:
            import host_outfit
            # v16: register the two-tid POOL (center + 3/4 yaw) so the hook and
            # the payoff cutaway are shot from different angles. Rendering every
            # cutaway off one talking photo is the static-avatar tell we're
            # closing this cycle (Vaibhav-DNA camera-angle parity).
            _outfit, _tids = host_outfit.pick_and_register_pool(ep)
            tid = _tids[0]
            tid_3q = _tids[-1]            # collapses to center if 3q is missing
            open(os.path.join(A, "host_outfit.txt"), "w").write(_outfit["name"] + "\n")
            print(f">> host wardrobe for ep{ep}: {_outfit['name']}  "
                  f"(center {tid[:8]}..., 3q {tid_3q[:8]}...)")
        except Exception as e:
            print(f"!! host_outfit unavailable ({e}); using global .heygen_photo_id")
            tid = tid_3q = open(CACHE).read().strip()
    else:
        tid = tid_3q = open(CACHE).read().strip()
    def host_clip(name, t0, t1, photo=None):
        wav = os.path.join(A, f"{name}.wav"); mp4 = os.path.join(A, f"{name}.mp4")
        if not os.path.exists(mp4):
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t0), "-t", str(t1 - t0),
                 "-i", vo, "-c:a", "pcm_s16le", wav])
            generate(photo or tid, upload_audio(wav), mp4)
        return mp4

    beats = cfg["beats"]
    news_split = cfg.get("layout") == "newsSplit"
    if news_split:
        # one host clip spanning the whole VO, pinned to the bottom pane
        full_host = host_clip("v2_host", 0, total)
        hook_mp4 = pay_mp4 = None
        hook_end = 0.0
    else:
        n_hook = beats.count("host")
        n_pay = beats.count("host2")
        hook_end = sum(seg_durs[:n_hook])
        pay_start = total - sum(seg_durs[-n_pay:]) if n_pay else total
        hook_mp4 = host_clip("v2_hook", 0, hook_end)
        # payoff shoots on the 3/4-yaw twin so the two cutaways alternate angle
        pay_mp4 = host_clip("v2_payoff", pay_start, total, photo=tid_3q) if n_pay else None

    # 3) segments for remotion (paths relative to remotion public/)
    def rel(p): return os.path.relpath(p, os.path.join(CH, "assets")).replace("\\", "/")
    segments, t0 = [], 0.0
    i = 0
    while i < len(beats):
        b = beats[i]
        dur = seg_durs[i]
        # merge consecutive identical beats
        while i + 1 < len(beats) and beats[i + 1] == b:
            i += 1; dur += seg_durs[i]
        # optional "|mode" suffix (newsSplit): split (default) / full / host
        mode = None
        if "|" in b:
            b, mode = b.rsplit("|", 1)
        if b == "host" and news_split:
            segments.append({"src": "assets/" + rel(full_host), "dur": round(dur, 3),
                             "mode": "host"})
        elif b == "host":
            segments.append({"src": "assets/" + rel(hook_mp4), "dur": round(dur, 3)})
        elif b == "host2":
            segments.append({"src": "assets/" + rel(pay_mp4), "dur": round(dur, 3)})
        elif b.startswith("rec:"):
            src, frm = b[4:].split("@")
            seg = {"src": f"assets/{src}", "dur": round(dur, 3), "from": float(frm)}
            if news_split and mode:
                seg["mode"] = mode
            segments.append(seg)
        elif b.startswith("stat:"):
            # chart beat: locked StatBars comp draws it in-frame at 1080x1920
            # (playbook §4 — never a pre-baked card video that gets cover-cropped)
            seg = {"kind": "statBars", "dur": round(dur, 3)}
            if news_split and mode:
                seg["mode"] = mode
            seg["stat"] = cfg["stats"][b[5:]]
            segments.append(seg)
        i += 1

    # steps -> absolute times
    line_starts = []
    acc = 0.0
    for d in seg_durs:
        line_starts.append(acc); acc += d
    # optional 4th tuple element = chip corner (tl/tr/bl/br) — put the chip in
    # dead space, never over the content the beat is teaching (user feedback Ep11)
    steps = []
    for tup in cfg["steps"]:
        lab, a, b = tup[0], tup[1], tup[2]
        st = {"label": lab, "start": round(line_starts[a], 2),
              "end": round(line_starts[b] + seg_durs[b], 2)}
        if len(tup) > 3:
            st["pos"] = tup[3]
        steps.append(st)

    spec = {
        "segments": segments, "captions": caps, "steps": steps,
        "vo": "assets/" + rel(vo),
        # cover.until = when the poster has fully dissolved. The default is
        # derived from the host hook; with NO host beats hook_end=0, so it is
        # floored at 0.70 (the dissolve length). WITHOUT that floor it was 0.60,
        # which opened Short.tsx's [until-0.7, until] fade BEFORE frame 0 and left
        # the frame-zero thumbnail ~14% transparent. Short.tsx now also clamps that
        # fade start to >=0 (belt + suspenders); this floor keeps the derived
        # default a full 0.70s dissolve rather than a rushed one.
        #
        # v13 (7 Aug 2026): RETENTION FIX — cap dropped 3.0 → 1.8.
        # YT Studio data shows 19.8% stay-rate; the cover was blocking the first
        # proof visual for up to 3s. 1.8s keeps the thumbnail-safe poster beat
        # but lets B-roll peek through much earlier. Per-episode explicit pins
        # still win (some hooks need the poster hold). newsSplit stays 2.2.
        "cover": {**cfg["cover"],
                  "until": cfg["cover"].get(
                      "until",
                      round(min(max(hook_end + 0.6, 0.7), 1.8), 2) if not news_split else 2.2)},
        "watermark": True,
    }
    if news_split:
        spec["layout"] = "newsSplit"
        spec["host"] = "assets/" + rel(full_host)
    # emphasis: cfg entries (text, line_a, line_b) -> absolute times (like steps)
    if cfg.get("emphasis"):
        spec["emphasis"] = [{"text": txt,
                             "start": round(line_starts[a2], 2),
                             "end": round(line_starts[b2] + seg_durs[b2], 2)}
                            for (txt, a2, b2) in cfg["emphasis"]]
    # v16: write Remotion props to a build-local path (renders_out/props_ep<ep>_<tag>.json)
    # so we DON'T clobber the human-readable spec at episodes/<ep>.<tag>.json. Ep 10's
    # first master (2026-08-11) overwrote its own source spec, wiping title/lines/tags/
    # endcard and forcing a factory_posts round-trip to recover the metadata. Props live
    # in renders_out (gitignored) and are consumed only by Remotion.
    props_dir = os.path.join(REPO, "renders_out")
    os.makedirs(props_dir, exist_ok=True)
    sp = os.path.join(props_dir, f"props_ep{ep}_{tag}.json")
    json.dump(spec, open(sp, "w"), indent=1)
    print(f">> props {sp} | total {total:.1f}s")
    if dry:
        print(">> DRY — spec written, skipping render/master")
        return sp

    # 4) remotion render (video + VO only; music mixed in mastering pass)
    raw = os.path.join(R, f"ep{ep}_{tag}_raw.mp4")
    # GPU/CPU tuning via env (unset -> Remotion defaults, unchanged behaviour):
    #   FACTORY_REMOTION_GL=angle          -> GPU-accelerated WebGL/canvas compositing
    #   FACTORY_REMOTION_CONCURRENCY=8     -> parallel frame renderers (match CPU threads)
    #   FACTORY_REMOTION_HWACCEL=if-possible -> hardware video encode where supported
    rflags = []
    if os.environ.get("FACTORY_REMOTION_GL"):
        rflags.append(f"--gl={os.environ['FACTORY_REMOTION_GL']}")
    if os.environ.get("FACTORY_REMOTION_CONCURRENCY"):
        rflags.append(f"--concurrency={os.environ['FACTORY_REMOTION_CONCURRENCY']}")
    if os.environ.get("FACTORY_REMOTION_HWACCEL"):
        rflags.append(f"--hardware-acceleration={os.environ['FACTORY_REMOTION_HWACCEL']}")
    run(["npx", "remotion", "render", "Short", raw, f"--props={sp}", *rflags],
        cwd=os.path.join(REPO, "remotion-studio"))

    if preview:
        # v16: stop after raw. Skip mastering, endcard, outro. The raw IS the
        # preview — 1080x1920 with clean unmastered VO, no music bed, no polish.
        # Human review happens on this file; scripted finalize_episode.py picks
        # up the SAME cfg later and runs mastering + endcard + outro to publish.
        print(f">> PREVIEW mode — stopped after raw: {raw}")
        return raw

    # 5) master: sidechain-ducked music + limiter
    out = os.path.join(R, f"ep{ep}_{tag}.mp4")
    # per-episode bed override (cfg["music"], relative to assets/); defaults to
    # the channel's locked active bed
    music = os.path.join(CH, "assets", cfg.get("music", "music/bed_active.mp3"))
    assert os.path.exists(music), f"music bed missing: {music}"
    # The locked 0.35 mix ratio (playbook §3) was calibrated against the channel's
    # standing bed at -8.3 LUFS. A per-episode bed at a different programme level
    # would land the master off the channel's shipped -18.8 LUFS spine, so a
    # substituted bed is LEVEL-MATCHED to that reference first. Chain topology
    # itself stays locked.
    mg = float(cfg.get("music_gain_db", 0.0))
    pre = f"volume={mg}dB," if mg else ""
    fc = (f"[1:a]{pre}volume=0.35,afade=t=in:st=0:d=1.5[m];"
          "[0:a]volume=11dB,asplit=2[v1][v2];"
          "[m][v2]sidechaincompress=threshold=0.05:ratio=8:attack=40:release=600[duck];"
          "[v1][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]")
    run(["ffmpeg", "-y", "-i", raw, "-stream_loop", "-1", "-i", music,
         "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out])
    print(">> MASTERED", out)

    # 5b) optional end-card overlay (e.g. a comment-keyword CTA).
    # Short.tsx has NO overlay prop — `kind:"image"` is a whole SEGMENT, and the
    # beat parser only knows host/host2/rec:/stat: — so a transparent PNG that
    # must sit OVER a beat cannot be expressed in the spec at all (beat_map §7.2;
    # the same gap swallowed ep24's frozen-chat still). On ep25 v2 it was fixed
    # by a hand-run ffmpeg pass on the finished file, which is exactly the kind
    # of step that silently goes missing on the next re-cut. It lives here now.
    # Composited BEFORE the outro concat so the card can never bleed onto the
    # sting, and windowed from the asset's own endcard.json, never from a guess.
    ec = cfg.get("endcard")
    # `over_outro` defers the composite until AFTER the sting is concatenated, so
    # the card runs from its in-point to the LAST frame of the episode (Ep25 v4,
    # 2026-08-05). The default (pre-concat) is still right for a generic card:
    # it can never bleed onto the branding. But when the card carries a comment
    # KEYWORD, the branded sting is exactly where it must NOT stop — v3 put the
    # FACTORY card up for 2.38s and then handed the last 3.8s (the frames a
    # viewer decides on) to the sting's generic "GOT FEEDBACK? COMMENT" chip, so
    # the final image contradicted the keyword the whole teaser is measured on.
    # Requires `outro_dur` to cut the sting before its own comment chip appears —
    # two comment CTAs on one frame is the same defect wearing a hat.
    # v16: guard against endcard dicts that don't carry a src (Ep 10 first-master
    # crashed here on cfg.endcard=None -> the finalize wrapper couldn't recover.
    # Skipping silently keeps the master file usable; a badly-configured endcard
    # is not worth aborting the whole ship over).
    if ec and ec.get("src") and not ec.get("over_outro"):
        card = os.path.join(CH, "assets", ec["src"])
        assert os.path.exists(card), f"endcard missing: {card}"
        outc = os.path.join(R, f"ep{ep}_{tag}_cta.mp4")
        run(["ffmpeg", "-y", "-i", out, "-i", card, "-filter_complex",
             f"[0][1]overlay=0:0:enable='between(t,{ec['in_s']},{ec['out_s']})'",
             "-map", "0:a", "-c:a", "copy",
             *venc("18", "veryfast"),
             "-pix_fmt", "yuv420p", outc])
        print(f">> ENDCARD {ec['in_s']}-{ec['out_s']}s", outc)
        out = outc

    # optional reusable outro sting (subscribe/comment), music keeps rolling + fades
    if cfg.get("outro"):
        outro = os.path.join(CH, "assets", "outro", "outro_sub_comment.mp4")
        out2 = os.path.join(R, f"ep{ep}_{tag}_outro.mp4")
        # `outro_dur` trims the sting (the asset itself is never re-rendered —
        # §15 bookends hygiene keeps it a shared branding asset). Needed when the
        # episode has its own end-card and the tail is capped: the sting's own
        # elements arrive on a fixed schedule (avatar ~0.6s, SUBSCRIBE ~0.8s,
        # generic COMMENT chip ~1.65s), so the cut point is a measurement, not a
        # preference. The bed's fade-out is re-derived from the trimmed length —
        # a fade pinned at 2.6s never fires inside a 1.6s sting.
        odur = float(cfg.get("outro_dur", 0) or 0)
        tin = ["-t", str(odur)] if odur else []
        fst = round(max(odur - 1.2, 0.0), 3) if odur else 2.6
        fc2 = ("[1:v]fps=30,format=yuv420p[ov];"
               f"[2:a]{pre}volume=0.30,afade=t=out:st={fst}:d=1.2,apad[oa];"
               "[0:v][0:a][ov][oa]concat=n=2:v=1:a=1[v][a]")
        run(["ffmpeg", "-y", "-i", out] + tin + ["-i", outro,
             "-stream_loop", "-1", "-i", music,
             "-filter_complex", fc2, "-map", "[v]", "-map", "[a]",
             *venc("18", "veryfast"),
             "-c:a", "aac", "-b:a", "192k", "-shortest", out2])
        print(f">> OUTRO APPENDED{f' (trimmed to {odur}s)' if odur else ''}", out2)
        out = out2

    if ec and ec.get("src") and ec.get("over_outro"):
        card = os.path.join(CH, "assets", ec["src"])
        assert os.path.exists(card), f"endcard missing: {card}"
        outc = os.path.join(R, f"ep{ep}_{tag}_final.mp4")
        run(["ffmpeg", "-y", "-i", out, "-i", card, "-filter_complex",
             f"[0][1]overlay=0:0:enable='gte(t,{ec['in_s']})'",
             "-map", "0:a", "-c:a", "copy",
             *venc("18", "veryfast"),
             "-pix_fmt", "yuv420p", outc])
        print(f">> ENDCARD {ec['in_s']}s -> last frame (over the sting)", outc)
        out = outc
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", required=True,
                    help="episode key from EPISODES_V2, OR a key with a "
                         "fallback spec at episodes/<ep>.v2.json (v16)")
    ap.add_argument("--dry", action="store_true",
                    help="regenerate the episode spec JSON only (no render/master)")
    ap.add_argument("--preview", action="store_true",
                    help="v16: stop after Remotion raw render — no master, "
                         "no endcard, no outro. For produce_preview jobs.")
    ap.add_argument("--tag", default="v2",
                    help="render stem: ep<NN>_<tag>.mp4 (use v3 for a re-cut so "
                         "the shipped v2 file survives for comparison)")
    a = ap.parse_args()
    build(a.ep, dry=a.dry, tag=a.tag, preview=a.preview)
