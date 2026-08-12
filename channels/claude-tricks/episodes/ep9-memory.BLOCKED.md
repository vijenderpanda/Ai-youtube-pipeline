# Ep 9 (Short A) — PRODUCTION HALTED AT PEG GATE

**Status:** BLOCKED before any paid generation. No VO, no HeyGen, no render.
**Date:** 2026-08-10
**Gate that fired:** brief's own PROOF SOURCE clause — *"VERIFY /save command still
exists and behaves as described on day of production. NEVER ship a stale product
claim."* — plus PRODUCTION-PLAYBOOK §144 (fabricated claims = brand kill).

---

## Two independent factual failures in the locked plan

### 1. There is no `/save` command on claude.ai
The locked VO line 2 — *"Pin it inside a Project. Then hit /save. That's it."* — names a
command that does not exist. This is not a rename (the brief anticipated
"checkpoint, snapshot, etc."); no slash-command mechanism for pinning a thread to a
Project exists at all.

**Actual mechanism:** open the chat's dropdown → **"Add to project"** → pick the
project in the *Move chat* dialog. Projects are a paid-plan feature.

### 2. "It remembers. Verbatim." is false — and it is the payoff beat
Locked VO line 3 — *"One day later. Ask it. It remembers. Verbatim."* — inverts how
Claude memory actually works. Memory builds a **synthesis** of past chats that
refreshes roughly every 24 hours; **specific turns and exact wording are paraphrased
away** when that synthesis is built. A new chat opens with an empty context window.

This kills beat b3 as specified. Its proof was
`fix_seed_terms=["<specific callback term only in the pinned thread>"]` — i.e. the
beat was designed to demonstrate on camera exactly the verbatim recall that does not
happen. There is no truthful way to film it.

**Actual mechanism for cross-chat recall:** Settings → Capabilities → Memory →
**"Search and reference chats"** (on by default). Claude searches past conversations
and pulls relevant excerpts into the current session — **only when you prompt it to**.
Paid plans only (Pro, Max, Team, Enterprise), on web, Desktop and Mobile.

### Knock-on
Locked line 4's SO-WHAT card — *"Chats are sessions. Projects are shelves. /save =
bookmark."* — inherits failure 1. Three of five VO lines are unshippable as written,
so this is past "adapt line 2" and needs a human re-approval of the angle.

---

## Corrected script (fact-checked, ready for review)

Same pillar (memory), same title promise, same 26–30s band, same wardrobe
(outfit_07_olive_overshirt), same "MEMORY LOST" thumbnail. Only the mechanism changes
— to one that is real, evergreen, and still a genuinely useful trick.

1. "You closed the tab. Claude forgot everything."
2. "Open the chat's menu. Hit Add to project. It lives on a shelf now."
3. "Then turn on Search and reference chats, in Settings, Capabilities, Memory."
4. "SO WHAT? Chats are sessions. Projects are shelves. Memory is the search."
5. "Follow. I unpack one AI trick every single day."

**Title stays shippable** — "Stop Losing Your Claude Chats 🛑 (One Setting Locks Them
Forever) 🤯" (swap "Command" → "Setting"; still exactly 2 emojis).

**Thumbnail unchanged:** "MEMORY LOST" strikethrough yellow Anton. The alternate
"3,400 TOKENS" variant stays killed — never measured, never ledger-recorded.

---

## What is still blocking, after the rewrite

Proof footage. The brief requires a **real screen recording of claude.ai**, and none
exists for ep9 (`channels/claude-tricks/assets/ep9/` does not exist). Two of the three
proof screens are cheap to capture live, but the third is not:

- b1 new-chat empty state — capturable any time
- b2 "Add to project" dropdown + Memory settings pane — capturable any time
- b3 recall payoff — **requires a real ≥24h gap**, because the memory synthesis
  refreshes on roughly a 24-hour cycle. It cannot be staged inside a 25-minute
  session without faking it, which is the exact thing this gate exists to prevent.

So b3 needs a genuine two-sitting capture: seed a chat today, film the recall
tomorrow. That is a scheduling decision, not a production one.

---

## Recommended next step

Approve (or amend) the corrected script above, then queue a capture job that seeds a
Project chat today and films the recall ≥24h later. Once
`assets/ep9/proof_memory.mp4` exists, the spec at `episodes/9.v2.json` is a
fill-in-the-blank away from rendering — note ep key `"9"` is deliberately distinct
from the shipped `"09"` (Fast vs Deep) entry in EPISODES_V2, so there is no collision.

## Money not spent
ElevenLabs $0 · HeyGen $0 · Leonardo $0. The HeyGen pool for ep 9 *was* registered
(that call is free and idempotent): outfit_07_olive_overshirt →
center `180722082348429f8722e4591b9ecd08`, 3q `559faad62d064dca998028e24c93b41d`.
Registering it evicted outfit_10_heather_grey from HeyGen's 3-photo-avatar cap.
