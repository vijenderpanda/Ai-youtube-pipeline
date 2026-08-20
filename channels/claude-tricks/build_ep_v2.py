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


# =============================================================================
# _upi cookbook props. Numbers are LOADED, never retyped — R3 in the shooting
# spec: the same figure lives in the VO, two prop sets, the lane counter, the
# hook still, the mirror JSON and the description, and one numeral edit
# re-synths the whole VO cache. One file owns them.
# =============================================================================
def _upi_numbers():
    import json as _json
    with open(os.path.join(CH, "assets", "ep_upi", "locked_numbers.json")) as f:
        return _json.load(f)

def _build_upi_cookbook():
    n = _upi_numbers()
    hero, whole, sched = n["hero"], n["whole"], n["digit_schedule"]
    lanes = [
        {"key": "blinkit", "label": "BLINKIT", "emoji": "\U0001F6F5", "tint": "#F8CB46"},
        {"key": "other", "label": "OTHER APPS", "emoji": "\U0001F4F1", "tint": "#5FA82C"},
        {"key": "food", "label": "FOOD", "emoji": "\U0001F37D", "tint": "#E23744"},
        {"key": "shop", "label": "SHOPPING", "emoji": "\U0001F6CD", "tint": "#FF9900"},
    ]
    # Every row is a transaction that ACTUALLY APPEARS in the source recording.
    # masked rows carry merchant "" — the identity is absent from the props.
    rows = [
        {"id": "u01", "merchant": "Blinkit", "amount": 560, "day": "18 AUG", "cat": "blinkit", "counted": True},
        {"id": "u02", "merchant": "Zomato", "amount": 1072, "day": "18 AUG", "cat": "food", "counted": True},
        {"id": "u03", "merchant": "Zomato", "amount": 897, "day": "18 AUG", "cat": "food", "counted": True},
        {"id": "u04", "merchant": "Amazon", "amount": 1414, "day": "18 AUG", "cat": "shop", "counted": True},
        {"id": "u05", "merchant": "", "amount": 100, "day": "18 AUG", "masked": True},
        {"id": "u06", "merchant": "Blinkit", "amount": 710, "day": "17 AUG", "cat": "blinkit", "counted": True},
        {"id": "u07", "merchant": "Blinkit", "amount": 649, "day": "17 AUG", "cat": "blinkit", "counted": True},
        {"id": "u08", "merchant": "Snabbit", "amount": 399, "day": "17 AUG", "cat": "other", "counted": True},
        {"id": "u09", "merchant": "DMart", "amount": 5931, "day": "17 AUG", "cat": "shop", "counted": True},
        {"id": "u10", "merchant": "Blinkit", "amount": 1843, "day": "16 AUG", "cat": "blinkit", "counted": True},
        {"id": "u11", "merchant": "", "amount": 2800, "day": "16 AUG", "masked": True},
        {"id": "u12", "merchant": "Maestro", "amount": 199, "day": "15 AUG", "cat": "other", "counted": True},
        {"id": "u13", "merchant": "Gas Bill", "amount": 1500, "day": "14 AUG", "cat": "other", "counted": True},
        {"id": "u14", "merchant": "Box8", "amount": 372, "day": "12 AUG", "cat": "food", "counted": True},
        {"id": "u15", "merchant": "Snabbit", "amount": 248, "day": "12 AUG", "cat": "other", "counted": True},
        {"id": "u16", "merchant": "", "amount": 250, "day": "12 AUG", "masked": True},
        {"id": "u17", "merchant": "Snabbit", "amount": 323, "day": "09 AUG", "cat": "other", "counted": True},
        {"id": "u18", "merchant": "Blinkit", "amount": 923, "day": "03 AUG", "cat": "blinkit", "counted": True},
        {"id": "u19", "merchant": "Blinkit", "amount": 1215, "day": "03 AUG", "cat": "blinkit", "counted": True},
        {"id": "u20", "merchant": "Blinkit", "amount": 841, "day": "02 AUG", "cat": "blinkit", "counted": True},
        {"id": "u21", "merchant": "Blinkit", "amount": 598, "day": "02 AUG", "cat": "blinkit", "counted": True},
        {"id": "u22", "merchant": "Zepto", "amount": 1560, "day": "02 AUG", "cat": "other", "counted": True},
    ]
    hud = {"label": "BLINKIT SO FAR", "value": hero["total"], "prefix": "\u20b9 "}
    # ---- beat 0: the designed hook (TapStack) ------------------------------
    # Replaces the pick.mp4 gallery tape. VJ 2026-08-20: "for 0-3s hook i dont
    # want my phone screenshots ... lets create some animation which stands on
    # our existing shorts where creating hooks was our forte".
    #
    # WHY A GRAPHIC IS SAFE HERE: it never claims to BE the input. It says the
    # provenance in words ("FROM MY OWN SCREENSHOTS"), and it recedes to an
    # EMPTY container that beat 1's real tape fills — a graphic may hand off a
    # container, never an artifact. The actual upload is still demonstrated on
    # real tape at 2.55s (ask.mp4), which is where provenance is proven.
    #
    # It also cannot spoil the payoff: TapStack has no HUD, no tally and no
    # digit plate, so the withheld Rs 7,339 keeps its shape until 20.43s. Only
    # 3 of the 8 Blinkit addends are ever on screen (710/649/1843 = 3,202), so
    # the total is not derivable from the hook.
    _tap_cat = {"blinkit": "grocery", "food": "food", "shop": "shopping",
                "other": "other"}
    tap_cards = []
    for r in rows[1:13]:   # u02-u13 — 12 arrivals is what fits 2.55s without strobing
        c = {"id": r["id"], "merchant": r["merchant"], "amount": r["amount"],
             "day": r["day"]}
        if r.get("masked"):
            c["masked"] = True
        elif r.get("cat"):
            c["cat"] = _tap_cat[r["cat"]]
        if r["id"] == "u09":
            c["hot"] = True     # the Rs 5,931 ghost that beat 6 kills at 16.31s
        tap_cards.append(c)
    base = {"rows": rows, "lanes": lanes, "scrollFrom": 0, "scrollTo": 0}
    br = {b["beat"]: b for b in sched["breaks"]}
    return {
        # --- designed hook (beat 0) -----------------------------------------
        "TapStack": {
            "cards": tap_cards,
            # front-loaded then floored at 4 frames: contraction is spent before
            # 0.8s (where relativeRetentionPerformance first samples) and the
            # floor is the densest rate that still resolves at 2x playback.
            "gaps": [0, 0.3, 0.5, 0.667, 0.8, 0.933, 1.067, 1.2,
                     1.333, 1.467, 1.6, 1.733],
            "provenance": "FROM MY OWN SCREENSHOTS",
            "unitLabel": "ONE TAP",       # the denominator line 6 completes at 20.43s
            "claimLines": ["I SCREENSHOTTED", "MY UPI HISTORY"],
            "claimHot": "UPI", "claimAt": 0.467, "claimOut": 1.8,
            "debt": "I NEVER ADDED THEM UP", "debtHot": "NEVER", "debtAt": 1.933,
            "handoffAt": 2.2,
        },
        # --- real tape ------------------------------------------------------
        # pick.mp4 is RETIRED — beat 0 is TapStack. Left here unreferenced would
        # be dead config, so it is gone; tape_lengths_needed in
        # locked_numbers.json no longer asks for it.
        "ScreenStage#ask":    {"src": "assets/ep_upi/ask.mp4",    "chip": "NO CONNECTOR \u00b7 NO LOGIN",
                               "host": True, "hostSize": 300},
        "ScreenStage#answer": {"src": "assets/ep_upi/answer.mp4", "chip": "WHAT IT SENT BACK"},
        # --- designed -------------------------------------------------------
        "LedgerFlow#rush": dict(base, phase="rush", ingest={"count": 3, "at": 0}, scrollTo=14,
                                hud=dict(hud, revealed=br["rush"]["revealed"], revealAt=br["rush"]["revealAt"]),
                                tally={"label": "ROWS READ", "from": 0, "to": 22},
                                # claimLines RETIRED: TapStack burns this line at
                                # 0.467s. Repeating it at 5.91s reads as a loop,
                                # and its words are line 0's, not line 2's.
                                contentStart=0.37),
        "LedgerFlow#floor": dict(base, phase="floor", scrollFrom=8, scrollTo=8,
                                 hud=dict(hud, revealed=br["floor"]["revealed"], revealAt=br["floor"]["revealAt"]),
                                 bracket={"from": 2, "to": 12, "label": "WHAT THE SHOTS SHOWED",
                                          "ghostLabel": "NOT IN THE PICTURES"},
                                 skipLabel="DUPLICATE \u2014 SKIPPED",
                                 footNote="FREE CHATS TRAIN THE MODEL \u2014 TURN IT OFF IN SETTINGS"),
        "LedgerFlow#sort": dict(base, phase="sort", scrollFrom=6, scrollTo=6,
                                hud=dict(hud, revealed=br["sort"]["revealed"], revealAt=br["sort"]["revealAt"]),
                                ghostGuess={"value": 5931, "label": "ONE SUPERMARKET TRIP",
                                            "killAt": 2.21, "prefix": "\u20b9"},
                                # the rows have departed by mid-beat, so mid-left is a genuine
                                # void — a small corner card there would waste half the frame
                                host=True, hostSize=470, hostAnchor="ml"),
        "LedgerFlow#grow": dict(base, phase="grow", scrollFrom=6, scrollTo=6, focusLane="blinkit",
                                hud=dict(hud, revealed=br["grow"]["revealed"], revealAt=br["grow"]["revealAt"]),
                                spill={"atPct": 0.78, "releaseAt": 1.4},
                                counter={"label": "BLINKIT ORDERS", "to": hero["orders"], "at": 0, "roll": 0.7},
                                handoff={"w": 750, "h": 930, "at": 0.6}),
        "ShareSplit": {
            "runLabel": "FROM MY OWN SCREENSHOTS",
            "meta": [{"k": "ROWS READ", "v": str(n["rows"]["in_props"])},
                     {"k": "SKIPPED", "v": str(n["rows"]["excluded_failed"])},
                     {"k": "ORDERS", "v": str(hero["orders"])}, {"k": "COST", "v": "FREE"}],
            "total": {"value": hero["total"], "label": "BLINKIT",
                      "sub": "%d orders \u00b7 \u20b9%d a tap" % (hero["orders"], hero["average"])},
            "whole": {"value": whole["value"], "label": whole["label"]},
            "atoms": hero["orders"],
            "shareLabel": whole["share_words"],
            "openFrost": {"w": 750, "h": 930, "dur": 0.5},
            "splitAt": 1.15,
            "capSafe": 1200,
            "atLeast": {"at": 3.5, "word": "",
                        "note": "A FLOOR \u2014 NOT A STATEMENT"},
            "ghostBars": 5,
            # top-right: the hero figure owns y700-950 on the LEFT
            "host": True, "hostSize": 420, "hostAnchor": "tr",
        },
    }

_UPI_COOKBOOK = _build_upi_cookbook()

EPISODES_V2 = {
  # ===========================================================================
  # _upi — "I Audited My UPI Spending By Typing One Line" (2026-08-20)
  #
  # THE FIRST TIER-0 EPISODE: zero setup, no connector, no login. The viewer
  # screenshots their own UPI history and uploads it. Everything Claude does
  # here it does to PICTURES THE USER SENT — never a feed, never a live account.
  #
  # CUT BACKWARDS FROM ONE FACT: across 10 real retention curves this channel's
  # worst single second is 6s (median -7.3pp) and 15 of 30 steepest drops fall
  # in 4-8s. There is no 15s cliff. So the masked-HUD digit schedule pays its
  # FIRST digit at exactly 6.00s absolute — the most-abandoned second becomes
  # the first second the viewer is paid. It costs zero runtime; it is a prop.
  #
  # NUMBERS ARE LOCKED IN assets/ep_upi/locked_numbers.json. Blinkit Rs 7,339
  # across 8 orders = Rs 917 a tap, against Rs 25,136 of merchant spend visible
  # in the shots (nearly a third). Change them THERE, never here first — they
  # appear in seven places and one numeral re-synths the whole VO cache.
  #
  # HONESTY, structural not editorial: person-to-person rows carry merchant:""
  # and masked:true, so no name enters the props at all. The Rs 5,931 "ghost"
  # at beat 6 is NOT a remembered guess (VJ never gave one, and inventing it
  # after seeing the answer would fabricate the beat) — it is the biggest real
  # single purchase in the same data, which the eight small taps beat.
  # ===========================================================================
  "_upi": {
    "title": "I Audited My UPI Spending By Typing One Line \U0001F4B8",
    "tags": ("upi,upi spending,phonepe,gpay,blinkit,expense tracker,where my money went,claude ai,"
             "ai for beginners,screenshot,money saving india,spending tracker,ai tips"),
    # NO `hook` BLOCK — TapStack *is* the hook. HookCard renders full-frame over
    # beat 0, so it would cover the receipt during the exact 0-0.3s window the
    # receipt has to be recognised in, and burn the same headline twice (its own
    # at 0.0s, TapStack's again at 0.467s). `baked: true` exists to guarantee a
    # legible frame 0; TapStack does that natively, with motion instead of a
    # 0.3s freeze. build_ep_v2 opens straight on beat 0 when neither hook nor
    # cover is set.
    "outro": True,
    "outro_dur": 0,
    "outro_src": "ep_upi/outro_card.mp4",
    "outro_cta": "Screenshot your own month and ask the same line. Which app eats your money? Tell me below.",
    "lines": [
      "Screenshots of my UPI history.",
      "One line in Claude. Nothing connected.",
      "It read every row I'd forgotten.",
      "It only saw the pictures. And threw out the doubles.",
      "Here's what it sent back. Grouped by where it went.",
      "One supermarket trip: five thousand nine hundred.",
      "Eight quick taps cost more. Seven thousand, three hundred and thirty nine.",
      "Nearly a third of what I spent. Nobody spends money badly - we just never add it up.",
    ],
    "hot_words": ["SCREENSHOTS", "UPI", "HISTORY", "ONE", "LINE", "CLAUDE", "NOTHING", "CONNECTED", "READ", "EVERY", "ROW", "FORGOTTEN", "ONLY", "PICTURES", "THREW", "DOUBLES", "SENT", "BACK", "GROUPED", "WENT", "SUPERMARKET", "TRIP", "THOUSAND", "HUNDRED", "EIGHT", "QUICK", "TAPS", "MORE", "THIRD", "SPENT", "BADLY", "ADD", "UP"],
    # 8 lines : 8 beats. Real tape carries beats 0, 1 and 4 — the previous cut
    # was 5-of-7 motion graphics, which is how a designed number ends up
    # asserting something the tool cannot guarantee.
    "beats": ["cook:TapStack",             # 0.0-2.55 DESIGNED HOOK, LEGIBLE AT FRAME 0
              "cook:ScreenStage#ask",      # 3.0-5.0  the line lands, send tapped (Sol PIP)
              "cook:LedgerFlow#rush",      # 5.0-8.0  DIGIT 1 BREAKS AT 6.00s ABSOLUTE
              "cook:LedgerFlow#floor",     # 8.0-12.0 the blind spot admitted + digit 2
              "cook:ScreenStage#answer",   # 12.0-17.0 the REAL grouped reply, scrolling
              "cook:LedgerFlow#sort",      # 17.0-22.0 the big single buy loses + digit 3
              "cook:LedgerFlow#grow",      # 22.0-27.0 Blinkit overflows + FINAL digit 24.5s
              "cook:ShareSplit"],          # 27.0-34.0 the one un-eased cut, then the >= twist
    "steps": [],   # RETIRED — empty, not absent (build_ep_v2 requires the key)
    "epTag": "",
    "header_scrim": True,   # claude.ai mobile is a cream column; the lockup would vanish
    "cookbook": _UPI_COOKBOOK,
  },

  # First fill for the post-pivot standalone-tips slot (PIVOT-DECISION.md, 2026-08-18):
  # the Artifacts short. Reverse hook = the finished Rs400 app in frame 0 (hook_art.png),
  # then rebuild it live. Footage: rec_artifacts_app.py capture (type->build->card) +
  # a baked still-hold of the opened app (hold_app.mp4). 7-beat shape (critic fix #2).
  "_artifacts": {
    "title": "I Built A Working App By Typing One Line 🤯",
    "tags": "claude artifacts,build app with ai,no code,claude ai,ai for beginners,vibe coding,ai tools,ai tips",
    "hook": {"image": "ep_artifacts/still_hero_rs400.png", "until": 2.2,
             "lines": ["I BUILT THIS", "BY TYPING ONE LINE"], "hot": "ONE"},
    "outro": True,
    "outro_dur": 0,
    "outro_src": "ep_artifacts/outro_card.mp4",   # LOCKED Ep11-style question-CTA card (gen_outro_card.py), not the old generic sting
    "outro_cta": "auto",   # Sol speaks the CTA over the card (approved treatment); line 7 is a loopback, not a CTA
    "lines": [
      "I typed one line — and Claude built me this working app. No code.",
      "Empty chat, one sentence, a real app you can use. Watch.",
      "In Claude, I type one line: build me a bill splitter.",
      "A few seconds later, it's built — a real, working app.",
      "Twelve hundred, split three ways — four hundred each. It just works.",
      "That's Artifacts. Ask for a tool, and Claude builds the working thing, right there.",
      "One line of plain English — and you've got a real, working app.",
    ],
    "hot_words": ["TYPED", "CLAUDE", "BUILT", "ENGLISH", "WORKS", "ZERO", "CODE", "ASKED", "ONE", "LINE", "EMPTY",
                  "SENTENCE", "REAL", "APP", "WATCH", "TYPE", "BUILD", "SPLITTER",
                  "SECONDS", "BUILT", "WORKING", "TWELVE", "HUNDRED", "THREE",
                  "FOUR", "ARTIFACTS", "TOOL", "THING", "FOLLOW", "SKILL", "DAY"],
    "beats": ["host", "host",
              "rec:ep_artifacts/raw_capture_v2.mp4@12",   # type one line
              "rec:ep_artifacts/raw_capture_v2.mp4@46",   # seconds later: the app card (clean window, before a stray feedback modal at ~52s)
              "rec:ep_artifacts/hold_app.mp4@0.0",        # the working app — Rs400 (payoff)
              "host2", "host2"],
    "host_panels": [
      {"lines": ["I TYPED", "ONE LINE", "NO CODE"]},
      {"lines": ["EMPTY CHAT", "TO A WORKING", "APP — WATCH"]},
    ],
    "steps": [   # 4th = corner in DEAD SPACE (prompt bubble is top; empty chat is bottom)
      ("STEP 1/3 — TYPE ONE LINE", 2, 2, "bl"),
      ("STEP 2/3 — CLAUDE BUILDS IT", 3, 3, "bl"),
      ("STEP 3/3 — IT JUST WORKS", 4, 4, "tl"),
    ],
  },
  # Post-pivot standalone tip #2 (2026-08-19): the Habit Tracker short. Doubles down
  # on the winning "one line -> real working app" magic from _artifacts (pTXcKAw9qj4,
  # 30.4% stayed-to-watch vs 19-20% norm). SAME proven 7-beat spine: reverse hook =
  # the finished tracker in frame 0 (still_hero.png) -> rebuild it live (mobile tape)
  # -> baked still-hold of the opened app (payoff) -> Sol outro. Fresh theme (habits,
  # not money) so the franchise reads as range, not repetition. Payoff a still can
  # honestly show: Mon-Fri checked, a 5-day streak (beat 5 states the RESULT, no live
  # motion needed - the _artifacts Rs400 pattern).
  "_habit": {
    "title": "I Built A Habit Tracker By Typing One Line 🔥",
    "tags": "claude artifacts,habit tracker,build app with ai,no code,claude ai,ai for beginners,vibe coding,ai tools,ai tips",
    "hook": {"image": "ep_habit/still_hero.png", "until": 2.2,
             "lines": ["I BUILT THIS", "BY TYPING ONE LINE"], "hot": "ONE"},
    "outro": True,
    "outro_dur": 0,
    "outro_src": "ep_habit/outro_card.mp4",   # LOCKED Ep11-style question-CTA card (gen_outro_card.py)
    "outro_cta": "auto",   # Sol speaks the CTA over the card; line 7 is a loopback, not a CTA
    "lines": [
      "I typed one line — and Claude built me this habit tracker. No code.",
      "Empty chat, one sentence, an app that counts my streak. Watch.",
      "In Claude, I type one line: build me a weekly habit tracker.",
      "A few seconds later, it's built — seven days, tap to check one off.",
      "Monday to Friday done — a five-day streak. It actually keeps count.",
      "That's Artifacts. Ask for a tool, and Claude builds the working thing, right there.",
      "One line of plain English — and you've got a habit tracker that works.",
    ],
    "hot_words": ["TYPED", "CLAUDE", "HABIT", "TRACKER", "CODE", "ONE", "LINE", "EMPTY",
                  "SENTENCE", "COUNTS", "STREAK", "WATCH", "TYPE", "WEEKLY",
                  "SECONDS", "BUILT", "SEVEN", "DAYS", "TAP", "CHECK",
                  "MONDAY", "FRIDAY", "FIVE", "COUNT", "ARTIFACTS", "TOOL",
                  "THING", "ENGLISH", "WORKS", "FOLLOW", "SKILL", "DAY"],
    "beats": ["host", "host",
              "rec:ep_habit/raw_capture.mp4@11",   # type one line (account-name greeting redacted, <=12.0s)
              "rec:ep_habit/card_hold.mp4@0.0",     # seconds later: the built 'Habit tracker' card (real t84 frame, held)
              "rec:ep_habit/hold_app.mp4@0.0",      # the working app — 5-day streak (payoff)
              "host2", "host2"],
    "host_panels": [
      {"lines": ["I TYPED", "ONE LINE", "NO CODE"]},
      {"lines": ["EMPTY CHAT", "TO A HABIT", "TRACKER — WATCH"]},
    ],
    "steps": [   # 4th = corner in DEAD SPACE (prompt bubble is top; empty chat is bottom)
      ("STEP 1/3 — TYPE ONE LINE", 2, 2, "bl"),
      ("STEP 2/3 — CLAUDE BUILDS IT", 3, 3, "bl"),
      ("STEP 3/3 — IT KEEPS YOUR STREAK", 4, 4, "tl"),
    ],
  },
  # FRANCHISE ENTRY #3 (2026-08-20) — the Spin-The-Wheel dinner picker.
  # WHY THIS EXISTS: tip #3 (_style) failed frame-by-frame QC — ~14 of 39s were two
  # FROZEN SCREENSHOTS sitting in the 3-15s sustain window, because a *text* payoff
  # has nothing that appears. VJ called it: the format capped the wow. This returns to
  # the proven form (_artifacts 30.4% stayed; _habit 213 views / 38.6% AVP): a real
  # thing MATERIALIZES. Upgrade over both: the payoff is no longer a baked still-hold
  # — rec_wheel_app.py films the artifact OPENED AND RUNNING, so the wheel physically
  # spins on camera. Continuous motion is the direct lever on Shorts-feed selection
  # (22.9%, mid-typical), which is the measured ceiling. Every beat below is real tape.
  "_wheel": {
    "title": "I Built A Dinner Decider By Typing One Line 🎰",
    "tags": "claude artifacts,dinner decider,what to eat,spin the wheel,decision wheel,build app with ai,no code,claude ai,ai for beginners,vibe coding,ai tools,ai tips",
    # VJ 2026-08-19: "for hook start with spin wheel not static". `until` is now
    # only long enough to own frame 0 (the feed thumbnail keeps the burned claim);
    # by 0.3s we are on the SpinWheel, already mid-spin.
    # baked=True is MANDATORY: HookCard ramps headline opacity over frames 2-12,
    # so without it frame 0 ships with the claim text BLANK — and this channel
    # cannot set a custom thumbnail, so frame 0 IS the thumbnail everywhere.
    # headTop 96 aligns this headline with SpinWheel's own claim (also top 96) so
    # the 0.3s cross-dissolve doesn't show two offset ghost copies of the words.
    "hook": {"image": "ep_wheel/hook.png", "until": 0.3, "baked": True, "headTop": 96,
             "lines": ["I BUILT THIS", "BY TYPING ONE LINE"], "hot": "ONE"},
    "outro": True,
    "outro_dur": 0,
    "outro_src": "ep_wheel/outro_card.mp4",
    "outro_cta": "That's the exact prompt. Follow for more simple, fast AI tools you can actually use.",
    "lines": [
      "I typed one line — and Claude built me this.",
      "Can't decide what to eat? Empty chat, one sentence, a real app.",
      "In Claude, I type one line: build me a spin-the-wheel dinner picker.",
      "It writes the whole app itself — every slice, the spin, the result.",
      "I tap SPIN, and it actually spins. Real animation, not a picture.",
      "Biryani it is. Dinner decided — by an app that didn't exist a minute ago.",
      "One line of plain English — and you've got a real app you can use.",
    ],
    "hot_words": ["TYPED", "ONE", "LINE", "CLAUDE", "BUILT", "WATCH", "SPIN", "SPINS",
                  "DECIDE", "EAT", "EMPTY", "SENTENCE", "REAL", "APP", "TYPE", "WHEEL",
                  "DINNER", "PICKER", "WRITES", "WHOLE", "SLICE", "RESULT", "TAP",
                  "ACTUALLY", "ANIMATION", "PICTURE", "BIRYANI", "DECIDED", "MINUTE",
                  "ENGLISH", "USE", "FOLLOW", "SKILL", "DAY"],
    # Beat 0 is the NEW cookbook component SpinWheel (invented for this episode):
    # designed, on-brand motion for the swipe window — a wheel that accelerates,
    # smears, eases onto the winner and lands with a flare. Its options and winner
    # MIRROR THE REAL APP EXACTLY (same six dishes, same Biryani result), so it is a
    # stylized restatement of what the tape then proves, never a fabricated result.
    # Beats 2-5 are ALL REAL TAPE — timings verified frame-by-frame. The proof is
    # never a graphic (COOKBOOK.md honesty bar).
    "beats": ["cook:SpinWheel",                      # DESIGNED motion in the swipe window (see cookbook note below)
              "host",
              "cook:GenerativeUI",                   # the ASK, Plate 08 style: components land, not prose
              "cook:ScreenStage#code",              # REAL Claude writing the app — code STREAMS (the evidence)
              # app_shift.mp4 = tape[115..127] raised ~100px so the app's result pill
              # clears the karaoke caption band (the caption was landing ON "Biryani
              # it is!"); the same crop also removes claude's top chrome. 0s == t115.
              "cook:ScreenStage#spin",              # SPIN #1 — REAL tape, staged (Plates 01/05/07)
              "cook:ScreenStage#result",            # SPIN #2 — REAL tape, lands "Biryani it is!"
              "host2"],
    "cookbook": {
      # GenerativeUI — Plate 08 ("tool call -> component, NOT tokens -> prose").
      # This is the ILLUSTRATIVE beat: the one-line ask, then the built thing
      # LANDING as UI objects (spec card -> preview tile -> action row). The
      # earlier chat-bubble version was the wrong port — bubbles are prose, i.e.
      # the fallback, not the interface. The tile image is a REAL frame of the
      # real app, and the next two beats are real tape, so evidence is untouched.
      "GenerativeUI": {
        "promptLabel": "ONE LINE",
        "prompt": "build me a spin-the-wheel dinner picker",
        "items": [
          {"kind": "spec", "title": "Dinner wheel", "chips": ["6 OPTIONS", "SPIN BUTTON", "SINGLE FILE"]},
          {"kind": "tile", "media": "assets/ep_wheel/hook.png", "title": "Ready to run",
           "subtitle": "HTML \u00b7 NO SETUP", "mediaHeight": 440},
          {"kind": "action", "title": "Open it", "value": "\u21b3"},
        ],
        "start": 0.1,
        "promptHold": 0.7,
        "perItem": 0.5,
      },
      # ScreenStage — the REAL recording, staged with the plates that port to a
      # frame clock (07 depth-without-3D on a scripted camera, 01 glass bezel,
      # 05 bounding-box morph). The pixels inside are untouched evidence; only
      # the presentation changes. Instance #1 travels in from an inset card;
      # #2 is already hero so the payoff never re-animates its own frame.
      "ScreenStage#code": {
        "src": "assets/ep_wheel/raw_capture.mp4",
        "from": 68,
        "morph": False,          # already hero — the writing shouldn't re-animate its frame
        "sheen": False,
        "heroAspect": 1.62,      # the chat view is content-light; a shorter card crops the dead space
        "host": True,            # VJ: host PIP on the Claude code beat ONLY — the payoff stays clean
      },
      "ScreenStage#spin": {
        "src": "assets/ep_wheel/app_shift.mp4",
        "from": 4,
        "label": "REAL SCREEN RECORDING",
        "morph": True,
        "morphStart": 0.15,
        "morphDur": 0.85,
        "insetScale": 0.66,
      },
      "ScreenStage#result": {
        "src": "assets/ep_wheel/app_shift.mp4",
        "from": 14,
        "morph": False,
        "sheen": False,
      },
      "SpinWheel": {
        "kicker": "",   # the burned claim already says this; keeping both collided
        "title": "What's for dinner?",
        "options": [
          {"label": "Biryani", "emoji": "🍛"},
          {"label": "Pizza", "emoji": "🍕"},
          {"label": "Pasta", "emoji": "🍝"},
          {"label": "Tacos", "emoji": "🌮"},
          {"label": "Sushi", "emoji": "🍣"},
          {"label": "Burger", "emoji": "🍔"},
        ],
        "winner": 0,                # Biryani — exactly what the real app landed on
        "resultPrefix": "Tonight:",
        "spinStart": 0.05,          # already spinning when the 0.3s hook clears
        "claimLines": ["I BUILT THIS", "BY TYPING ONE LINE"],
        "claimHot": "ONE",
        "claimHold": 2.4,   # readable over the motion instead of flashing past
        "contentStart": 0.32,  # wait for the 0.3s hook to clear — else the hook's
                               # headline and this claim ghost as two offset copies
        "spinDur": 2.7,
        "turns": 5,
      },
    },
    # authored idea lines — they AGREE with the VO without transcribing it, and
    # render through IdeaKinetic (Plate 03) instead of the running caption
    "host_panels": [
      {"lines": ["CAN'T DECIDE", "WHAT TO EAT?", "ONE LINE."], "hot": "ONE"},
      {"lines": ["ONE LINE", "OF ENGLISH", "= A REAL APP"], "hot": "REAL"},
    ],
    "steps": [],   # RETIRED — empty, not absent (build_ep_v2 requires the key)
    # STEP CHIPS RETIRED (VJ, 2026-08-19). The "STEP n/3 — ..." chips are gone:
    # they narrated what the frame already showed, they were a standing collision
    # risk with the content (the reason `pos` corners existed at all), and the
    # authored IdeaKinetic panel now carries the through-line. No `steps` key =
    # no chips. Do NOT reintroduce them on new episodes.
  },
  # ===========================================================================
  # Franchise entry #4 (2026-08-20): the PLAYABLE reaction test.
  #
  # Why a game, and why THIS game. The build franchise wins distribution (median
  # 228 views) but bleeds retention — tip #2 held 39.8% AVP against a 50.9% tip
  # median — and two builds in a row drew ZERO comments on 218 views. A reaction
  # test is the one build shape that attacks both at once:
  #   · RETENTION — the payoff is a NUMBER the viewer waits for. The measured
  #     killer on tip #2 was the 0:15–0:25 drop-off, which mapped exactly onto
  #     two FROZEN STILL-HOLDS. Every beat here is live motion; nothing freezes.
  #   · COMMENTS — "what should I build next?" is homework, and it returned
  #     nothing. "What's your reaction time?" is answerable in two seconds and
  #     the viewer already has the answer in their hand.
  #
  # HONESTY NOTE (important, read before re-capturing). The capture script taps
  # by polling the artifact frame's computed background colour, which detects
  # green in ~36ms — faster than any human can be (physiological floor ~100ms,
  # the well-known benchmark ~250ms). A 36ms readout makes a CORRECTLY WORKING
  # app look broken, and reporting it as a personal score would be a false claim.
  # rec_game_app.py therefore waits --tap-delay before tapping, and this episode's
  # VO never brags a reflex: it says what the app MEASURES ("it clocks you to the
  # millisecond") and hands the number to the viewer as a challenge. The three
  # rounds on tape are real and unedited: 231ms, 271ms, 269ms.
  "_game": {
    "title": "I Built A Reaction Game By Typing One Line ⚡",
    "tags": "claude artifacts,reaction time game,reaction game,build app with ai,no code,claude ai,ai for beginners,vibe coding,reaction time test,ai tools,ai tips",
    # frame 0 IS the thumbnail everywhere (this channel cannot set a custom one),
    # so baked=True is mandatory — without it HookCard ramps the headline in over
    # frames 2-12 and ships a blank claim. hook.png is the REAL 231ms result frame
    # with a top scrim, so the claim reads on near-black over full-bleed red.
    "hook": {"image": "ep_game/hook.png", "until": 0.3, "baked": True, "headTop": 96,
             "lines": ["I BUILT THIS", "BY TYPING ONE LINE"], "hot": "ONE"},
    "outro": True,
    "outro_dur": 0,
    "outro_src": "ep_game/outro_card.mp4",
    # the ask is answerable in two seconds — that is the whole point of this episode
    "outro_cta": "Drop your reaction time in the comments. Follow for more simple, fast AI tools you can actually use.",
    "lines": [
      "I typed one line — and Claude built me a reaction test. Can you beat it?",
      "Red means wait. Green means tap. It clocks you to the millisecond.",
      "In Claude, I type one line — the whole game, described in plain English.",
      "It writes the whole thing itself — the timer, the colours, the score.",
      "Open it, tap to start, and wait. The screen holds on red…",
      "Green. Tap. Two hundred and sixty nine milliseconds, measured live.",
      "One line of plain English — and you've got a real game you can play.",
    ],
    "hot_words": ["TYPED", "ONE", "LINE", "CLAUDE", "BUILT", "REACTION", "TEST",
                  "BEAT", "RED", "WAIT", "GREEN", "TAP", "CLOCKS", "MILLISECOND",
                  "TYPE", "GAME", "FULL", "SCREEN", "WRITES", "WHOLE", "TIMER",
                  "COLOURS", "SCORE", "OPEN", "START", "HOLDS", "SIXTY", "NINE", "PLAIN",
                  "MILLISECONDS", "MEASURED", "LIVE", "ENGLISH", "REAL", "PLAY",
                  "FOLLOW", "SKILL", "DAY"],
    # Beat 0 is the NEW cookbook component ReactionMeter (invented for this
    # episode): the library's Plate 09 block — WAIT, a hard snap to GREEN, then a
    # number that ARRIVES on a drawn ring. It mirrors the real app EXACTLY (same
    # 231ms, same red/green grammar), so it is a stylized restatement of what the
    # tape then proves, never a fabricated result.
    # Beats 3-5 are ALL REAL TAPE from one continuous 80s recording — timings
    # verified frame-by-frame against a colour-transition scan of take4.mp4:
    #   49.23s app opens fullscreen | 58.03-58.33 green #1 -> 231ms (held to 65.47)
    #   65.47 green #2 -> 271ms     | 73.00 green #3 -> 269ms (held to 80.47 end)
    "beats": ["cook:ReactionMeter",          # DESIGNED motion in the swipe window
              "host",
              "cook:GenerativeUI",           # the ASK, Plate 08: components land, not prose
              "cook:ScreenStage#code",       # REAL Claude writing the app — code STREAMS
              "cook:ScreenStage#play",       # REAL: red hold -> GREEN -> the tap
              "cook:ScreenStage#score",      # REAL: 231ms, same unbroken hold (no rewind)
              "host2"],
    "cookbook": {
      "ReactionMeter": {
        "kicker": "",   # the burned claim already says this; keeping both collided
        "title": "How fast are you?",
        "ms": 269,                  # EXACTLY what the real app measured on round 3 (the round on tape)
        "avgMs": 250,
        "challenge": "CAN YOU BEAT IT?",
        "start": 0.05,              # already running when the 0.3s hook clears
        # WAIT breathes, so a longer wait keeps the beat ALIVE and shrinks the
        # static tail after the number lands (QC: 1.15 left ~3s of held readout)
        "waitDur": 1.9,
        "greenDur": 0.45,
        "claimLines": ["I BUILT THIS", "BY TYPING ONE LINE"],
        "claimHot": "ONE",
        "claimHold": 2.4,   # readable over the motion instead of flashing past
        "contentStart": 0.32,  # wait for the 0.3s hook to clear — else the hook's
                               # headline and this claim ghost as two offset copies
      },
      # GenerativeUI — Plate 08 ("tool call -> component, NOT tokens -> prose").
      "GenerativeUI": {
        "promptLabel": "ONE LINE",
        # THE REAL TYPED PROMPT, verbatim. The earlier short paraphrase was a
        # FABRICATED QUOTATION: the tape 4s later shows this long text in the
        # prompt bubble and the outro brands it "THE EXACT PROMPT", so the cut
        # contradicted itself — in the flattering direction, making the result
        # look cheaper to get than it was.
        "prompt": 'Build me a reaction time game that fills the whole screen edge to edge - no borders, no header, just colour. Red means wait, green means tap, and show my reaction time in milliseconds in huge numbers.',
        "items": [
          {"kind": "spec", "title": "Reaction game", "chips": ["FULL BLEED", "RANDOM DELAY", "SINGLE FILE"]},
          {"kind": "tile", "media": "assets/ep_game/ready.png", "title": "Ready to play",
           "subtitle": "HTML · NO SETUP", "mediaHeight": 300},
          {"kind": "action", "title": "Open it", "value": "↳"},
        ],
        "start": 0.1,
        "promptHold": 0.7,
        "perItem": 0.5,
      },
      # ScreenStage — the REAL recording, staged with the plates that port to a
      # frame clock (07 depth, 01 glass bezel, 05 bounding-box morph). The pixels
      # inside are untouched evidence; only the presentation changes.
      "ScreenStage#code": {
        "src": "assets/ep_game/app_clean.mp4",
        # 34.6-35.8 is the ONLY sustained WRITING motion in the tape: the spec
        # bullets stream in one by one, then the file card lands. src 29 looked
        # like code but was a FROZEN, already-finished block (YAVG locked, message
        # stamped "just now", idle composer) — 3.6s of a still under a VO saying
        # "It writes the whole thing itself", and at 32.7 the block vanished so a
        # caption landed on an empty panel. The streamed bullets also happen to
        # name the timer, the colours and the score, which is the line verbatim.
        "from": 34.0,
        "morph": False,          # already hero — the writing shouldn't re-animate its frame
        "sheen": False,
        "heroAspect": 1.62,      # the chat view is content-light; crop the dead space
        "host": True,            # VJ: host PIP on the Claude code beat ONLY
      },
      "ScreenStage#play": {
        "src": "assets/ep_game/app_clean.mp4",
        # VO: "Open it, tap to start, and wait. The screen holds on red." The app's
        # own idle screen literally reads "WAIT / Tap to start" and is up from 49.23
        # to the first arm — so this window matches the line word for word AND is
        # long enough (round 3's armed wait is only 4.05s, shorter than this beat,
        # which forced the green into this beat and stranded it before the word).
        "from": 49.3,
        "label": "REAL SCREEN RECORDING",
        "morph": True,
        "morphStart": 0.15,
        "morphDur": 0.85,
        "insetScale": 0.66,
      },
      "ScreenStage#score": {
        # ROUND 3 IS THE ONLY ROUND WITH A LONG TAIL. Round 1's 231ms is on screen
        # for just 3.2s (58.33 -> ~61.5, when the script arms round 2), so the first
        # cut ran the payoff beat straight into round 2 and showed 271ms under a VO
        # saying "two hundred and thirty one". Round 3's 269ms holds 73.27 -> 80.47
        # (7.2s, to the end of tape). Picks up later in that same unbroken hold, so
        # the payoff never rewinds onto moving footage.
        "src": "assets/ep_game/app_clean.mp4",
        # Green is only 267ms long (73.000-73.267). At from=73.45 the beat opened
        # AFTER it, so "Green. Tap." was narrated over the red result and the magenta
        # caption GREEN sat on a bright red screen — reading as a caption-sync bug.
        # Beat 6 starts at master 23.30 and the word GREEN is spoken 23.30-23.78, so
        # from=72.90 puts the flash at master 23.40 — inside the word.
        "from": 72.90,
        "morph": False,
        # sheen ON. The app's result screen is a FLAT COLOUR that genuinely does not
        # move, so without it the payoff sits near-static for seconds — the exact
        # still-hold pattern that cost tip #2 its retention. The sheen and the deeper
        # parallax drift are chrome AROUND the evidence; the recording's own pixels
        # are untouched.
        "sheen": True,
        "drift": 24,
      },
    },
    # authored idea lines — they AGREE with the VO without transcribing it, and
    # render through IdeaKinetic (Plate 03) instead of the running caption
    "host_panels": [
      {"lines": ["RED = WAIT", "GREEN = TAP", "IT CLOCKS YOU"], "hot": "GREEN"},
      {"lines": ["ONE LINE", "OF ENGLISH", "= A REAL GAME"], "hot": "REAL"},
    ],
    "steps": [],   # RETIRED — empty, not absent (build_ep_v2 requires the key)
  },
  # Post-pivot standalone tip #3 (2026-08-20): the "paste an example" writing tip.
  # Promised by tip #2's (_habit) outro tease. prompt-teardown cluster (PIVOT-DECISION §4 #8).
  # SLATE RISK: "Stop X" abstract hooks flopped in-feed + muted text before/after is weaker than
  # an app-appears. MITIGATION: proof-first CONTRAST hook (generic vs distinct, side by side),
  # BEFORE state legible early, real single-tape proof (chatgpt no-login, describe->paste-example).
  "_style": {
    "title": "Stop DESCRIBING The Style — Paste 1 Example 🎯",
    "tags": "chatgpt tips,ai writing,prompt tips,writing style,ai for beginners,better ai answers,paste example,ai tools,ai tips",
    # HOOK SHORTENED 2.4 -> 1.6 (2026-08-19 analytics): on tip #2 (Ag9tBHbyrbo) AVP
    # 38.6% was ABOVE typical but Shorts-feed selection 22.9% only mid-typical — i.e.
    # the ceiling is the swipe window, not retention. The static contrast frame states
    # the claim fast; beat 0 then ANIMATES it (cook:DiffReveal) so motion lands by ~1.6s.
    "hook": {"image": "ep_style/hook.png", "until": 1.6, "baked": True,
             "lines": ["SAME ASK.", "ONE PASTED LINE"], "hot": "ONE"},
    "outro": True,
    "outro_dur": 0,
    "outro_src": "ep_style/outro_card.mp4",   # LOCKED Ep11-style question-CTA card (gen_outro_card.py)
    "outro_cta": "That's the whole trick. Follow for more simple, fast AI tools you can actually use.",
    "lines": [
      "Same request to the same AI — but one pasted line changes everything. Watch.",
      "Don't describe the style — show it one example.",
      "First, I describe it — bold, punchy, modern. I get this: generic, every-brand copy.",
      "So I paste one line in the exact voice I want, and ask for the same thing.",
      "Now it's a real voice — punchy and specific. It copied my example, not my adjectives.",
      "Describing a style makes AI guess. Give it one real example, and it nails the voice.",
      "Stop describing the vibe — paste one line that already has it.",
    ],
    "hot_words": ["SAME", "REQUEST", "ONE", "PASTED", "LINE", "CHANGES", "WATCH",
                  "DESCRIBE", "STYLE", "SHOW", "EXAMPLE", "BOLD", "PUNCHY", "MODERN",
                  "GENERIC", "COPY", "PASTE", "EXACT", "VOICE", "SPECIFIC",
                  "COPIED", "ADJECTIVES", "GUESS", "NAILS", "STOP", "VIBE",
                  "FOLLOW", "SKILL", "DAY"],
    # FIRST PRODUCTION USE OF THE VISUAL COOKBOOK (2026-08-19). The library was
    # "inert demos" until now; `cook:<id>` beats + cfg["cookbook"][id] props are the
    # wired path (build_ep_v2 -> Short.tsx CookbookBlock). Two components earn their
    # place here (honesty bar — each serves the beat, neither replaces real proof):
    #   beat 0 DiffReveal  — MOTION in the swipe window; animates the very thing the
    #                        episode is about (vague in -> sharp out) using the REAL
    #                        before/after text verbatim. Fixes the feed-selection ceiling.
    #   beat 6 KineticQuote— the takeaway lands as designed typography, not a 3rd host card.
    # Beats 2-4 stay REAL TAPE — the proof is never a graphic.
    "beats": ["cook:DiffReveal", "host",
              "rec:ep_style/demo.mp4@16",   # describe -> generic answer (the fail: "your new coffee obsession has officially arrived")
              "rec:ep_style/demo.mp4@29",   # paste ONE example line + ask again
              "rec:ep_style/matched_hold.mp4@0.0",  # matched, distinct voice held (the fix/proof: "no weak brews... rocket fuel") — still-hold for the ~5s payoff line
              "host2", "cook:KineticQuote"],
    # props for the cook: beats above, keyed by component id (JSON-safe only)
    "cookbook": {
      "DiffReveal": {
        "filename": "brand-copy.txt",
        "kicker": "SAME ASK · ONE PASTED LINE",
        "title": "Describe the style, and AI guesses.",
        "lines": [
          {"text": "# launch my coffee brand", "kind": "same"},
          {"text": "Wake up to bold. Sip something unforgettable.", "kind": "del"},
          {"text": "Your new coffee obsession has officially arrived.", "kind": "del"},
          {"text": "No weak brews. No sleepy mornings.", "kind": "add"},
          {"text": "Just a punch of dark-roasted rocket fuel", "kind": "add"},
          {"text": "that makes 6 a.m. flinch.", "kind": "add"},
        ],
        # footer auto-truncates around ~30 chars — keep it short or it renders "…"
        "footer": "Show it. Don't describe it.",
        # hold the BEFORE state a beat longer so the generic copy reads before it melts
        "start": 0.5,
      },
      "KineticQuote": {
        "kicker": "The whole trick",
        "parts": [
          {"text": "Don't describe"},
          {"text": "the vibe."},
          {"text": "PASTE ONE LINE", "hot": True},
          {"text": "that already"},
          {"text": "HAS IT.", "hot": True},
        ],
        # no footer — the outro card already says "one AI trick, every single day"
        "highlight": "bar",
      },
    },
    "host_panels": [
      {"lines": ["SAME ASK", "ONE PASTED", "LINE — WATCH"], "hot": "ONE"},
      {"lines": ["DESCRIBE =", "A GUESS —", "EXAMPLE = VOICE"], "hot": "EXAMPLE"},
    ],
    "steps": [],   # RETIRED 2026-08-19 (empty, not absent — build requires the key)
  },
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
  "11_retired": {
    "_note": "RETIRED — YrjPbZK28Oo deleted from YT. Key renamed 2026-08-11 so build key '11' falls through to the JSON spec (episodes/11.v2.json = the new '6 Commands Ranked' episode).",
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
  "12_retired": {
    "_note": "RETIRED 2026-08-12 — never shipped. Key renamed so build '12' falls "
             "through to episodes/12.v2.json (the armed Ep12 'Ask For A Table'). "
             "Ep numbers are assigned at ARM time, sequentially; do not reuse '12'.",
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

def outro_fc(pre, fst, ratio=None, gain_db=None):
    """Filtergraph for the outro concat (inputs: 0=mastered body, 1=outro card,
    2=music bed looped, 3=CTA wav — 3 only in the spoken-CTA variant).
    gain_db=None -> the shipped silent-card graph, byte-for-byte. gain_db set ->
    spoken-CTA variant: card retimed by `ratio` (slower Ken-Burns, same frames),
    VO leveled onto the -14 spine rides over the 0.30 bed, limiter mirrors the
    master chain. Module-level so audition_outro_cta.py exercises the SAME
    graph the builder ships — a test harness with its own copy would drift."""
    if gain_db is None:
        return ("[1:v]fps=30,format=yuv420p[ov];"
                f"[2:a]{pre}volume=0.30,afade=t=out:st={fst}:d=1.2,apad[oa];"
                "[0:v][0:a][ov][oa]concat=n=2:v=1:a=1[v][a]")
    ov = (f"[1:v]setpts={ratio:.5f}*PTS,fps=30,format=yuv420p[ov];"
          if ratio and ratio > 1.001 else "[1:v]fps=30,format=yuv420p[ov];")
    return (ov +
            f"[2:a]{pre}volume=0.30,afade=t=out:st={fst}:d=1.2[bed];"
            "[3:a]aformat=channel_layouts=stereo,"
            f"volume={gain_db}dB,adelay=450:all=1[cta];"
            "[bed][cta]amix=inputs=2:duration=first:normalize=0,"
            "alimiter=limit=0.95,apad[oa];"
            "[0:v][0:a][ov][oa]concat=n=2:v=1:a=1[v][a]")

# --- Studio asset-lock resolution (docs/STUDIO-ASSET-VERSIONING.md Phase 2) ---------
# Root-cause fix for the 2026-08-18 stale-outro bug: resolve a reusable asset from its
# LOCKED version instead of a silent hardcoded fallback. None-safe by design — any failure
# (no env, table absent, offline) returns None so today's literal default is used unchanged.
_LOCK_CFG_KEY = {"music_bed": "music", "outro_sting": "outro_src",
                 "hook_image": None, "host_outfit": None, "remotion_comp": None}
_LOCK_CACHE = None
CHANNEL_KEY_FOR_PROV = "claude-tricks"
# Phase 3 provenance: what THIS build actually resolved, and the
# factory_asset_versions.id behind each pick (keyed by (source, asset_type)).
_RESOLVED = []
_VERSION_ID_BY = {}
# S4 block reconciliation: what THIS build rendered for each locked _sequence
# block (position, block_type, layout, ref, rendered). The SEQUENCE twin of
# _RESOLVED — flushed to factory_episode_blocks_used so a produced Short can be
# diffed against its locked composition._sequence.
_RESOLVED_BLOCKS = []


class CastUnrenderable(Exception):
    """A chosen cast slot cannot render this format and the build refuses to
    silently substitute a different one. Raised loudly (recorded to provenance,
    aborts the build) instead of the old silent fall-through to a dead avatar id
    — a cast switcher that gets quietly overridden at render time is worse than
    none (VJ 2026-08-19, the EP15 outfit_12→outfit_11 silent swap)."""


def _supa():
    """factory_worker.Supa client from the repo env. Callers ALWAYS wrap this in the
    try that owns their never-raise contract — it is the exact statement sequence
    _lock_lookup ran inline before Phase 4, lifted verbatim so the template layer
    can reuse it without touching the lock path's behavior."""
    _scripts = os.path.join(REPO, "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)
    import factory_worker as fw
    env = fw.load_env()
    return fw.Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])


def _lock_lookup(ch, asset_type):
    """meta.build_ref of the LOCKED version for (ch, asset_type), else None. One batched
    read, cached per process. Never raises."""
    global _LOCK_CACHE
    if _LOCK_CACHE is None:
        _LOCK_CACHE = {}
        try:
            supa = _supa()
            locks = supa.select("factory_asset_locks",
                                f"channel_key=eq.{ch}&select=asset_type,locked_version_id")
            ids = [l["locked_version_id"] for l in locks if l.get("locked_version_id")]
            if ids:
                vers = supa.select("factory_asset_versions",
                                   f"id=in.({','.join(ids)})&select=id,asset_type,meta")
                bref = {v["id"]: (v.get("meta") or {}).get("build_ref") for v in vers}
                for l in locks:
                    ref = bref.get(l.get("locked_version_id"))
                    if ref:
                        _LOCK_CACHE[l["asset_type"]] = ref
                        _VERSION_ID_BY[("lock", l["asset_type"])] = l.get("locked_version_id")
            print(f">> asset locks resolved: {_LOCK_CACHE}")
        except Exception as e:
            print(f"!! asset-lock lookup unavailable ({e}); using built-in defaults")
    return _LOCK_CACHE.get(asset_type)


# --- Studio template-version composition (Phase 4) ---------------------------
# Layered ABOVE the channel lock, BELOW the per-episode cfg override. Same
# never-raise contract as _lock_lookup: any failure returns None and the older
# layer wins, so no wiring / no env / no table == today's behavior exactly.
_TPL_VERSION_ID = None   # bound once by build(); None = layer disabled
_TPL_CACHE = None        # {asset_type: build_ref} from the frozen composition
_TPL_SETTINGS = None     # {name: value} cast SETTINGS frozen with the composition
_TPL_SEQUENCE = None     # [block,...] ordered composition._sequence frozen at lock (Sprint-2)
_TPL_INFO = {}


def _cast_override_allowed(flag):
    """The two operator escape hatches for the divergence gate: the --allow-cast-
    override CLI flag OR a truthy FACTORY_ALLOW_CAST_OVERRIDE env."""
    return bool(flag) or os.environ.get("FACTORY_ALLOW_CAST_OVERRIDE", "").strip().lower() \
        in ("1", "true", "yes", "on")


def _print_divergence_banner(chosen, cal_pin, allow):
    """Loud, un-missable banner naming BOTH pinned casts on a divergence."""
    print("\n" + "!" * 74)
    print("!! CAST PIN DIVERGENCE — "
          + ("OVERRIDDEN (operator-approved)" if allow else "REFUSED"))
    print(f"!!   spec/CLI/env template_version : {chosen}")
    print(f"!!   calendar's pinned cast        : {cal_pin}")
    if allow:
        print("!!   proceeding with the spec/CLI/env pick per --allow-cast-override "
              "/ FACTORY_ALLOW_CAST_OVERRIDE=1")
    else:
        print("!!   the owner's calendar pin is DELIBERATE; NOT silently swapping the cast.")
        print("!!   re-run with --allow-cast-override (or FACTORY_ALLOW_CAST_OVERRIDE=1) "
              "ONLY if this override is intended.")
    print("!" * 74 + "\n")


def _bind_template_version(ch, explicit=None, cfg=None, calendar_id=None,
                           allow_cast_override=False, ep=None, tag="v2"):
    """Resolve WHICH template version this build runs with, first hit wins:
      1. --template-version <uuid>            (explicit, an operator re-cut)
      2. cfg["template_version"]              (a spec pins its own cast)
      3. FACTORY_TEMPLATE_VERSION env         (worker/job override)
      4. factory_calendar.template_version_id (the durable record, --calendar-id)
      5. factory_channels.template -> factory_templates.active_version_id
      6. None -> layer disabled, resolution is byte-for-byte today's.

    Phase 2 (2026-08-19) divergence guard: a rank-1/2/3 pick that CONTRADICTS the
    calendar's rank-4 pin (BOTH present, DIFFERENT) is no longer silently accepted
    — that is exactly how the EP15 agent re-pinned the whole cast (it wrote
    cfg["template_version"]=<v1> over the calendar's v2). The contradiction path
    REFUSES (records the divergence to provenance, prints a loud banner, raises
    CastUnrenderable) unless an operator override is set (--allow-cast-override or
    FACTORY_ALLOW_CAST_OVERRIDE=1), in which case it proceeds with the higher-rank
    pick after the same banner + provenance marker.

    Never raises on the normal (agreeing / only-one-present / offline) path — ONLY
    the un-overridden contradiction raises."""
    global _TPL_VERSION_ID
    chosen = explicit or (cfg or {}).get("template_version") \
        or os.environ.get("FACTORY_TEMPLATE_VERSION") or None
    # The calendar's durable rank-4 pin. Fetched EVEN when a higher-rank pick
    # exists, so a contradiction can be caught instead of silently winning.
    # Never raises: an offline/absent lookup leaves cal_pin=None (no divergence).
    cal_pin = None
    if calendar_id:
        try:
            rows = _supa().select("factory_calendar",
                                  f"id=eq.{calendar_id}&select=template_version_id")
            cal_pin = (rows[0].get("template_version_id") if rows else None)
        except Exception as e:
            print(f"!! calendar pin lookup unavailable ({e}); divergence check skipped")
            cal_pin = None
    # Divergence guard — the ONLY path in this function that may raise.
    if chosen and cal_pin and chosen != cal_pin:
        allow = _cast_override_allowed(allow_cast_override)
        _print_divergence_banner(chosen, cal_pin, allow)
        _RESOLVED.append({"asset_type": "template_version",
                          "build_ref": f"{chosen} OVER calendar {cal_pin}",
                          "resolved_from": ("cast_override" if allow else
                                            "divergence_refused"),
                          "version_id": chosen})
        if not allow:
            try:                      # persist the refusal marker (mirrors Phase 0)
                _flush_provenance(CHANNEL_KEY_FOR_PROV, ep, tag, calendar_id)
            except Exception:
                pass
            raise CastUnrenderable(
                f"cast pin conflict: template_version {chosen} (from the spec/CLI/env) "
                f"contradicts the calendar's pinned cast {cal_pin}. The owner's calendar "
                f"pin is DELIBERATE — refusing to silently swap the whole cast. Re-run "
                f"with --allow-cast-override (or FACTORY_ALLOW_CAST_OVERRIDE=1) ONLY if "
                f"this override is intended.")
        _TPL_VERSION_ID = chosen
        return _TPL_VERSION_ID
    # Normal path — never raises, byte-for-byte today's resolution.
    if chosen:
        _TPL_VERSION_ID = chosen
        return _TPL_VERSION_ID
    _TPL_VERSION_ID = cal_pin
    if not _TPL_VERSION_ID:
        try:
            crow = _supa().select("factory_channels", f"key=eq.{ch}&select=template")
            tkey = crow[0].get("template") if crow else None
            if tkey:
                trow = _supa().select("factory_templates",
                                      f"key=eq.{tkey}&select=active_version_id")
                _TPL_VERSION_ID = (trow[0].get("active_version_id") if trow else None)
        except Exception as e:
            print(f"!! template-version bind unavailable ({e}); using channel locks")
            _TPL_VERSION_ID = None
    return _TPL_VERSION_ID


def _tpl_lookup(ch, asset_type):
    """build_ref from the bound version's FROZEN composition, else None. One read,
    cached per process. Never raises."""
    global _TPL_CACHE
    if _TPL_CACHE is None:
        _TPL_CACHE = {}
        if _TPL_VERSION_ID:
            try:
                rows = _supa().select(
                    "factory_template_versions",
                    f"id=eq.{_TPL_VERSION_ID}"
                    "&select=template_key,channel_key,version,status,composition")
                row = rows[0] if rows else None
                # only a LOCKED version of THIS channel may drive a build — a draft cast
                # is still being edited and must never leak into a render.
                if row and row.get("status") == "locked" and row.get("channel_key") == ch:
                    comp = row.get("composition") or {}
                    for atype, slot in comp.items():
                        # Skip the non-slot sections (_settings dict, _sequence list) —
                        # only per-asset slot dicts carry a build_ref. The isinstance
                        # guard also keeps _sequence (a LIST) from raising .get() here.
                        if not isinstance(slot, dict):
                            continue
                        ref = slot.get("build_ref")
                        if ref:
                            _TPL_CACHE[atype] = ref
                            _VERSION_ID_BY[("template", atype)] = slot.get("version_id")
                    globals()["_TPL_SETTINGS"] = dict(comp.get("_settings") or {})
                    # Sprint-2: freeze the ordered block sequence alongside _settings so
                    # build resolves the whole locked cast+sequence from this ONE row
                    # (migration-020 one-select invariant). Absent -> None -> no-op.
                    _seq = comp.get("_sequence")
                    globals()["_TPL_SEQUENCE"] = list(_seq) if isinstance(_seq, list) else None
                    _TPL_INFO.update(template_key=row.get("template_key"),
                                     version=row.get("version"), id=_TPL_VERSION_ID)
                    print(f">> template version: {row.get('template_key')} "
                          f"v{row.get('version')} -> {sorted(_TPL_CACHE)}")
                elif row:
                    print(f"!! template version {_TPL_VERSION_ID} is {row.get('status')} / "
                          f"channel {row.get('channel_key')}; ignoring, using channel locks")
                else:
                    print(f"!! template version {_TPL_VERSION_ID} not found; using channel locks")
            except Exception as e:
                print(f"!! template composition unavailable ({e}); using channel locks")
    return _TPL_CACHE.get(asset_type)


# --- Sprint-2 composition _sequence reader -----------------------------------
# A LOCKED template version may freeze an ordered block sequence in
# composition["_sequence"] (rides alongside composition["_settings"], captured by
# _tpl_lookup above into _TPL_SEQUENCE). These two helpers turn those frozen blocks
# into Remotion segment dicts using the EXACT Sprint-1 Short.tsx field names. When
# no version is bound (or it carries no _sequence) _TPL_SEQUENCE is None and
# _composed_sequence() returns [] — the classic beat path is byte-for-byte unchanged.

def _composed_sequence(ch="claude-tricks"):
    """Ordered frozen blocks from the bound locked composition's _sequence, or []
    when none is bound. Probes _tpl_lookup first so the version row is loaded even
    if no earlier resolve happened to touch it. Never raises."""
    try:
        _tpl_lookup(ch, "__seq_probe__")   # ensure _TPL_SEQUENCE is populated
    except Exception:
        pass
    seq = _TPL_SEQUENCE
    if not seq:
        return []
    return sorted([b for b in seq if isinstance(b, dict)],
                  key=lambda b: b.get("position", 0))


def _seq_segment(block):
    """Convert one frozen _sequence block to a Remotion segment dict, or None if it
    carries nothing renderable here. EXACT contract shapes (Short.tsx consumes
    seg["cookbook"]["id"]/["props"] and seg["slot"]["layout"]/["host"]/["broll"]):
      cookbook: {"kind":"cookbook","dur":d,"cookbook":{"id":..,"props":{..}}}
      slot:     {"kind":"slot","dur":d,"slot":{"layout":..,"host":{..},"broll":{..}}}
    """
    if not isinstance(block, dict):
        return None
    conf = block.get("config") or {}
    dur = conf.get("dur")
    btype = block.get("block_type")
    if btype == "slot":
        host_in = conf.get("host") or {}
        broll_in = conf.get("broll") or {}
        slot = {"layout": conf.get("layout") or block.get("layout")}
        host = {}
        if host_in.get("src"):
            host["src"] = host_in["src"]
        # config's host carries an `id` (an outfit id); the segment's host uses
        # `label` for that id per the contract.
        label = host_in.get("label") or host_in.get("id")
        if label:
            host["label"] = label
        if host:
            slot["host"] = host
        if isinstance(broll_in, dict) and broll_in.get("id"):
            slot["broll"] = {"kind": "cookbook", "id": broll_in["id"],
                             "props": broll_in.get("props") or {}}
        if conf.get("tag"):
            slot["tag"] = conf["tag"]
        return {"kind": "slot", "dur": dur, "slot": slot}
    # any block whose config carries a cookbook payload (e.g. block_type "broll")
    cb = conf.get("cookbook")
    if isinstance(cb, dict) and isinstance(cb.get("id"), str) and cb.get("id"):
        seg = {"kind": "cookbook", "dur": dur,
               "cookbook": {"id": cb["id"], "props": cb.get("props") or {}}}
        if "transparent" in cb:
            seg["cookbook"]["transparent"] = cb["transparent"]
        return seg
    return None


def _block_ref(block):
    """A stable identity string for a locked _sequence block — WHAT filled it: the
    cookbook/broll component id, else the host label/id, else the layout, else the
    block_type. The build_ref analog for sequence provenance, so the app can diff
    built.ref against the same identity derived from the locked block's config."""
    if not isinstance(block, dict):
        return "—"
    conf = block.get("config") or {}
    cb = conf.get("cookbook")
    if isinstance(cb, dict) and isinstance(cb.get("id"), str) and cb.get("id"):
        return cb["id"]
    broll = conf.get("broll")
    if isinstance(broll, dict) and broll.get("id"):
        return str(broll["id"])
    host = conf.get("host") or {}
    if host.get("label") or host.get("id"):
        return "host:" + str(host.get("label") or host.get("id"))
    return conf.get("layout") or block.get("layout") or block.get("block_type") or "—"


def resolve_locked(asset_type, default, ch="claude-tricks", cfg=None):
    """Precedence: per-episode cfg override > bound template version's frozen
    composition > channel lock row > built-in default.
    Returns a value in the SAME namespace as `default` (assets-relative path or bare id).

    Every resolution is recorded in _RESOLVED so build() can write the episode's
    real cast to factory_episode_assets_used (Phase 3). Without that record a
    later lock move would make every PAST episode look like it used the new
    revision — history must not be rewritten by a lock change."""
    def _note(ref, src):
        _RESOLVED.append({"asset_type": asset_type, "build_ref": ref,
                          "resolved_from": src,
                          "version_id": _VERSION_ID_BY.get((src, asset_type))})
        return ref

    key = _LOCK_CFG_KEY.get(asset_type)
    if cfg is not None and key:
        ov = cfg.get(key)
        if ov is not None:
            return _note(ov, "cfg")
    composed = _tpl_lookup(ch, asset_type)          # NEW layer (no-op when unbound)
    if composed is not None:
        return _note(composed, "template")
    locked = _lock_lookup(ch, asset_type)
    if locked is not None:
        return _note(locked, "lock")
    return _note(default, "default")


def resolve_setting(name, default=None, ch="claude-tricks", cfg=None):
    """A cast SETTING (not a file): per-episode cfg > locked template version >
    built-in default.

    Some of what ships is behaviour, not an asset. `outro_cta:"auto"` makes Sol
    SPEAK a freshly-composed CTA over whatever card is in the outro slot — there
    is no file to pick, but it is absolutely part of the cast, and a cast that
    only described frames did not describe what we actually publish.

    Phase 1 (2026-08-19): records the resolution in _RESOLVED too, symmetric with
    resolve_locked's _note, so _flush_provenance captures outro_cta — the exact
    slot that let Sol speak over EP15's own question card with NO provenance row.
    Never raises: an unbound/unavailable version leaves today's behaviour, and a
    list append cannot fail the render."""
    if cfg is not None and name in cfg:
        val, src = cfg.get(name), "cfg"
    else:
        _tpl_lookup(ch, "__settings_probe__")      # ensures the version is loaded
        if _TPL_SETTINGS and name in _TPL_SETTINGS:
            val, src = _TPL_SETTINGS.get(name), "template"
        else:
            val, src = default, "default"
    _RESOLVED.append({"asset_type": name,
                      "build_ref": ("none" if val is None else str(val)),
                      "resolved_from": src, "version_id": None})
    return val


def resolve_cast(cfg, ch="claude-tricks"):
    """Resolve the reusable cast slots the LATER render lines consume — music bed,
    outro sting, outro_cta setting — ONCE, up front, before the Remotion raw render
    (reached in BOTH preview and finalize). Returns them in a dict the render lines
    read from, so no slot is resolved (and appended to _RESOLVED) twice.

    Why this exists (EP15 missing rows): produce_preview RETURNS right after the raw
    render, BEFORE the master's music resolve and the outro block's outro/outro_cta
    resolves ever ran — so a preview's _flush_provenance only ever held host_outfit
    + remotion_comp. Pulling these resolves up front means _flush_provenance records
    the WHOLE cast (host_outfit, remotion_comp, music_bed, outro_sting, outro_cta) on
    every build, preview included.

    host_outfit and remotion_comp are intentionally NOT re-resolved here: host_outfit
    is resolved (and Phase-0-gated) at its own consumer above, remotion_comp at the
    Remotion run() call — both already reached before the preview flush, so resolving
    them here would double-append. Defaults MUST match the later consumer lines.
    Never raises (same contract as resolve_locked / resolve_setting)."""
    return {
        "music_bed":  resolve_locked("music_bed", "music/bed_active.mp3", ch=ch, cfg=cfg),
        "outro_sting": resolve_locked("outro_sting", "outro/outro_sub_comment.mp4",
                                      ch=ch, cfg=cfg),
        "outro_cta":  resolve_setting("outro_cta", None, ch=ch, cfg=cfg),
    }


def _flush_provenance(ch, ep, tag, calendar_id):
    """Record what this build ACTUALLY resolved (Phase 3 backlinks).

    Never raises: provenance is bookkeeping, and a bookkeeping failure must never
    fail a render that already succeeded. A re-cut of the same (calendar, tag)
    replaces its own rows, so re-running a build does not double-count."""
    if not _RESOLVED:
        return
    try:
        by_type = {r["asset_type"]: r for r in _RESOLVED}   # last pick per slot wins
        rows = [{"calendar_id": calendar_id, "channel_key": ch, "ep": str(ep),
                 "build_tag": tag, "asset_type": atype,
                 "version_id": r.get("version_id"), "build_ref": r["build_ref"],
                 "resolved_from": r["resolved_from"]}
                for atype, r in sorted(by_type.items())]
        sp = _supa()
        if calendar_id:
            # Supa has no delete(); go straight at PostgREST with its own headers.
            import requests
            requests.delete(
                f"{sp.url}/rest/v1/factory_episode_assets_used"
                f"?calendar_id=eq.{calendar_id}&build_tag=eq.{tag}",
                headers=sp.headers, timeout=30)
        sp.insert("factory_episode_assets_used", rows)
        srcs = sorted({r["resolved_from"] for r in rows})
        print(f">> provenance: {len(rows)} slot(s) recorded ({', '.join(srcs)})")
    except Exception as e:
        print(f"!! provenance not recorded ({e}) — render is unaffected")


def _flush_sequence_provenance(ch, ep, tag, calendar_id):
    """Record the composition SEQUENCE this build actually rendered — the block
    twin of _flush_provenance (S4 block reconciliation). One row per locked
    _sequence block, in play order, carrying whether it produced a segment: a
    locked block that renders NOTHING is a real divergence the reviewer must see,
    so dropped blocks are recorded too (rendered=False), not skipped.

    Never raises (bookkeeping must not fail a successful render). A re-cut of the
    same (calendar, tag) replaces its own rows, so re-running does not double."""
    if not _RESOLVED_BLOCKS:
        return
    try:
        by_pos = {b["position"]: b for b in _RESOLVED_BLOCKS}   # last write per position wins
        rows = [{"calendar_id": calendar_id, "channel_key": ch, "ep": str(ep),
                 "build_tag": tag, "position": pos,
                 "block_type": b.get("block_type"), "layout": b.get("layout"),
                 "ref": b.get("ref"), "rendered": bool(b.get("rendered")),
                 "resolved_from": "template"}
                for pos, b in sorted(by_pos.items())]
        sp = _supa()
        if calendar_id:
            # Supa has no delete(); go straight at PostgREST with its own headers.
            import requests
            requests.delete(
                f"{sp.url}/rest/v1/factory_episode_blocks_used"
                f"?calendar_id=eq.{calendar_id}&build_tag=eq.{tag}",
                headers=sp.headers, timeout=30)
        sp.insert("factory_episode_blocks_used", rows)
        drops = sum(1 for r in rows if not r["rendered"])
        note = f", {drops} rendered nothing" if drops else ""
        print(f">> sequence provenance: {len(rows)} block(s) recorded{note}")
    except Exception as e:
        print(f"!! sequence provenance not recorded ({e}) — render is unaffected")


def _sequence_mode():
    """The bound composition's sequence_mode from its frozen _settings: 'replace'
    (the composed _sequence IS the whole short — its scenes supply the VO script and
    the segments) or 'augment' (default — the sequence adds b-roll AFTER the classic
    beats). Absent / unbound => 'augment', so the classic path is byte-for-byte
    unchanged (Sprint-5, VJ per-composition decision 2026-08-19)."""
    try:
        _tpl_lookup(CHANNEL_KEY_FOR_PROV, "__seq_probe__")   # populate _TPL_SETTINGS if a version is bound
    except Exception:
        pass
    s = _TPL_SETTINGS or {}
    m = s.get("sequence_mode")
    return m if m in ("replace", "augment") else "augment"


def _outro_source():
    """WHO OWNS THE OUTRO: the look's outro_sting FILE ('sting', the default) or a
    scene in the composed sequence ('sequence').

    Both currently claim it. cfg["outro"] appends the flat question-CTA card that
    gen_outro_card.py bakes, while an augment sequence appends its scenes after
    the classic beats -- so dropping a cook:OutroGlass scene into a look today
    ships TWO outros, one after the other.

    It is DECLARED, not sniffed. The alternative was inferring it from the
    component (OutroGlass registers beats ["cta","punchline"]), but that registry
    is TypeScript and this is Python: the inference would have to be duplicated
    and would silently rot the moment a new outro component landed. A setting the
    designer sets is one fact in one place, and 'sting' by default keeps every
    existing look byte-for-byte unchanged.

    NOTE when you switch a look to 'sequence': cfg["outro_cta"] -- Sol speaking
    the CTA over the card -- rides the classic filtergraph, so it goes with it.
    The sequence scene has to carry its own words.
    """
    try:
        _tpl_lookup(CHANNEL_KEY_FOR_PROV, "__seq_probe__")   # populate _TPL_SETTINGS
    except Exception:
        pass
    v = (_TPL_SETTINGS or {}).get("outro_source")
    return v if v in ("sting", "sequence") else "sting"


def _emit_manifest(ep, tag, cfg, replace_scenes, calendar_id, quiet=False):
    """Sprint-5 --manifest: build the pre-render GENERATION MANIFEST for REVIEW and
    (when calendar_id) persist it to factory_calendar.generation_manifest — WITHOUT
    rendering or spending on VO/HeyGen. Lists every asset the build WILL make, each
    linked to its scene(s), tagged free|paid, low-confidence flagged. Cast resolve is
    IDENTITY-ONLY (resolve_locked/resolve_cast look up which asset, they don't
    generate), so this is a read pass. Never raises on the persist (bookkeeping)."""
    lines = cfg.get("lines") or []
    n = len(lines)
    assets, low_conf, host_scenes = [], [], []

    # VO is the clock; captions derive from its word-timings.
    assets.append({"type": "vo", "engine": "elevenlabs", "cost": "paid",
                   "scenes": list(range(n)), "detail": f"{n} line(s)"})
    assets.append({"type": "captions", "cost": "free", "scenes": list(range(n)),
                   "detail": "derived from VO word-timings"})

    if replace_scenes:
        # REPLACE: one visual per scene, straight from the composed blocks.
        for i, b in enumerate(replace_scenes):
            conf = (b.get("config") or {}).get("confidence")
            cb = (((b.get("config") or {}).get("cookbook") or {}).get("id")
                  or ((b.get("config") or {}).get("broll") or {}).get("id"))
            if b.get("block_type") == "host" or ((b.get("config") or {}).get("host") or {}).get("id"):
                host_scenes.append(i)
            entry = {"type": "cookbook" if cb else b.get("block_type"), "scene": i, "cost": "free"}
            if cb:
                entry["id"] = cb
            if conf is not None:
                entry["confidence"] = conf
                if conf < 0.5:
                    low_conf.append(i)
            assets.append(entry)
    else:
        # CLASSIC / AUGMENT: enumerate the hand-authored beats, then any augment blocks.
        for i, bt in enumerate(cfg.get("beats") or []):
            b0 = str(bt).split("|")[0]
            if b0 in ("host", "host2"):
                host_scenes.append(i); assets.append({"type": "host", "scene": i, "cost": "paid"})
            elif b0.startswith("cook:"):
                assets.append({"type": "cookbook", "id": b0[5:].split("#", 1)[0], "scene": i, "cost": "free"})
            elif b0.startswith("pip:"):
                assets.append({"type": "pip", "ref": b0[4:], "scene": i, "cost": "free"})
            elif b0.startswith("rec:"):
                assets.append({"type": "recording", "ref": b0[4:].split("@")[0], "scene": i, "cost": "free"})
            elif b0.startswith("stat:"):
                assets.append({"type": "statbars", "scene": i, "cost": "free"})
        for b in _composed_sequence(CHANNEL_KEY_FOR_PROV):
            cb = ((b.get("config") or {}).get("cookbook") or {}).get("id")
            if cb:
                assets.append({"type": "cookbook", "id": cb, "cost": "free", "augment": True})

    if host_scenes:
        try:
            href = resolve_locked("host_outfit", "character/host_library/outfit_11_sol_magenta", cfg=cfg)
        except Exception:
            href = None
        assets.append({"type": "host_outfit", "ref": href, "cost": "paid", "scenes": host_scenes})

    try:
        cast = resolve_cast(cfg)
    except Exception:
        cast = {}
    assets.append({"type": "music_bed", "ref": cast.get("music_bed"), "cost": "free"})
    assets.append({"type": "outro_sting", "ref": cast.get("outro_sting"), "cost": "free"})
    if cast.get("outro_cta"):
        assets.append({"type": "outro_cta", "cost": "paid", "detail": "host speaks the CTA card"})
    assets.append({"type": "hook" if cfg.get("hook") else "cover", "cost": "free",
                   "detail": "illustration opener" if cfg.get("hook") else "poster opener"})
    try:
        rc = resolve_locked("remotion_comp", "Short", cfg=cfg)
    except Exception:
        rc = "Short"
    assets.append({"type": "remotion_comp", "ref": rc, "cost": "free"})

    manifest = {
        "version": 1,
        "sequence_mode": _sequence_mode(),
        "outro_source": _outro_source(),
        "template_version_id": _TPL_VERSION_ID,
        "scene_count": n,
        "paid_asset_count": sum(1 for a in assets if a.get("cost") == "paid"),
        "low_confidence_scenes": low_conf,
        "assets": assets,
    }
    print(f">> MANIFEST — {len(assets)} assets, {manifest['paid_asset_count']} paid, "
          f"mode={manifest['sequence_mode']}, {n} scenes"
          + (f", {len(low_conf)} low-confidence" if low_conf else ""))
    if not quiet:
        print(json.dumps(manifest, indent=1))
    if calendar_id:
        try:
            _supa().patch("factory_calendar", f"id=eq.{calendar_id}",
                          {"generation_manifest": manifest, "manifest_version_lock": _TPL_VERSION_ID})
            print(f">> manifest persisted to factory_calendar {calendar_id}")
        except Exception as e:
            print(f"!! manifest not persisted ({e}) — review it above")
    return manifest


def build(ep, dry=False, tag="v2", preview=False, calendar_id=None, template_version=None,
          allow_cast_override=False, manifest=False):
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
    # Phase 4: bind the composed cast BEFORE the first resolve_locked() call.
    # Never raises on the normal path (None = layer disabled = today's channel-lock
    # resolution); Phase 2 divergence guard may raise CastUnrenderable when the spec
    # pins a template_version that CONTRADICTS the calendar's pin (unless overridden).
    _bind_template_version("claude-tricks", explicit=template_version,
                           cfg=cfg, calendar_id=calendar_id,
                           allow_cast_override=allow_cast_override, ep=ep, tag=tag)

    # Sprint-5 REPLACE mode: when the bound locked composition declares
    # sequence_mode='replace', the composed _sequence IS the whole short — its scenes
    # supply the VO script (1 scene : 1 VO line) and the segments, so the classic
    # hand-authored beats are cleared. The append loop below then times each scene
    # segment from the VO (seg_durs), not its placeholder config.dur. Inert (byte-
    # identity) in the default 'augment' mode and whenever nothing is bound
    # (_composed_sequence() == []), so classic produces are unchanged.
    _replace_scenes = _composed_sequence(CHANNEL_KEY_FOR_PROV) if _sequence_mode() == "replace" else []
    if _replace_scenes:
        cfg = dict(cfg)  # never mutate a shared EPISODES_V2 entry
        cfg["lines"] = [str((b.get("config") or {}).get("line") or "") for b in _replace_scenes]
        cfg["beats"] = []                 # segments come from the scenes, not classic beats
        cfg.setdefault("hot_words", [])
        cfg.setdefault("steps", [])
        # no cover/hook default: a replace auto-short opens straight on scene 0
        # (build()'s opener now tolerates neither — see the elif below).

    # Sprint-5 --manifest: emit the pre-render GENERATION MANIFEST and STOP, BEFORE
    # any VO/HeyGen/render spend — a planning surface for REVIEW (what it WILL make).
    if manifest:
        return _emit_manifest(ep, tag, cfg, _replace_scenes, calendar_id)

    A = os.path.join(CH, "assets", f"ep{ep}"); os.makedirs(A, exist_ok=True)
    R = os.path.join(CH, "renders"); os.makedirs(R, exist_ok=True)

    # 1) VO with word timings (breaks between lines)
    from eleven_vo import load_key, synth
    import hashlib
    vo = os.path.join(A, "vo_v2.wav")
    # CONTENT-ADDRESSED CACHE. File existence alone is NOT a valid cache key, and
    # trusting it shipped a real defect: on `_game` the script's payoff line was
    # edited from "two hundred and thirty one" to "two hundred and sixty nine",
    # the rebuild silently reused the old audio, and the master ended up showing
    # 269ms on screen while the voice said 231. Hash the script instead — when it
    # moves, the VO is stale, and so is every host clip CUT FROM that VO.
    vo_txt = f" {BREAK} ".join(cfg["lines"])
    vo_sig_p = os.path.join(A, "vo_v2.sig")
    sig = hashlib.sha256(vo_txt.encode("utf-8")).hexdigest()[:16]
    prev = open(vo_sig_p).read().strip() if os.path.exists(vo_sig_p) else None
    if not os.path.exists(vo):
        synth(load_key(), ELEVEN_VOICE, vo_txt, vo, speed=1.0, style=STYLE)
    elif prev is None:
        # An episode built before this guard existed. Adopt the cached VO rather
        # than re-spending (and re-cutting an already-shipped master's audio);
        # every edit from here on is protected.
        print(f">> vo_v2.sig absent for ep{ep} — adopting cached VO, guarding future edits")
    elif prev != sig:
        print(f">> SCRIPT CHANGED ({prev} -> {sig}) — re-synthesizing VO and all host clips")
        synth(load_key(), ELEVEN_VOICE, vo_txt, vo, speed=1.0, style=STYLE)
        # host clips are cut from VO slices, so changed line timings invalidate them
        os.environ["FACTORY_REBUILD_HOSTS"] = "1"
    open(vo_sig_p, "w").write(sig)
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
    # 2026-08-11 (VJ directive): host generations are PINNED to the Ep11 host
    # (outfit_11_sol_magenta). Random per-episode outfit rotation
    # (host_outfit.pick_and_register_pool) is HELD until HOST_OUTFIT_POOL=on.
    #
    # v16.4 host layout (Short.tsx FramedHost) is a WIDE 16:9 talking-head CARD.
    # So the framed host clips (host/host2 beats) MUST render 16:9 from the WIDE
    # avatar (.heygen_photo_id_wide, wide.jpg) — exactly what shipped Ep11 used.
    # The near-square PIP crop (.heygen_photo_id_pip, cropeed_center_final.jpeg)
    # is ONLY for the small pipCallout box; feeding it to the host letterboxes +
    # over-crops the face (the Ep32 regression this fixes). `framed_tid` = the
    # wide avatar for host beats; `tid` stays the pip for the small box.
    _HOST_DEFAULT = "character/host_library/outfit_11_sol_magenta"
    _host_ref = resolve_locked("host_outfit", _HOST_DEFAULT)
    _o11 = os.path.join(CH, "assets", _host_ref)
    _o11_pip = os.path.join(_o11, ".heygen_photo_id_pip")
    _o11_wide = os.path.join(_o11, ".heygen_photo_id_wide")
    framed_tid = open(_o11_wide).read().strip() if os.path.exists(_o11_wide) else None
    _pool_on = os.environ.get("HOST_OUTFIT_POOL", "").lower() in ("on", "1", "yes", "true")
    if _pool_on and os.environ.get("HOST_OUTFIT", "on").lower() not in ("off", "0", "no"):
        try:
            import host_outfit
            _outfit, _tids = host_outfit.pick_and_register_pool(ep)
            tid = _tids[0]
            tid_3q = _tids[-1]            # collapses to center if 3q is missing
            open(os.path.join(A, "host_outfit.txt"), "w").write(_outfit["name"] + "\n")
            print(f">> host wardrobe for ep{ep}: {_outfit['name']}  "
                  f"(center {tid[:8]}..., 3q {tid_3q[:8]}...)")
        except Exception as e:
            print(f"!! host_outfit unavailable ({e}); using ep11 pinned host")
            tid = tid_3q = open(_o11_pip if os.path.exists(_o11_pip) else CACHE).read().strip()
    elif os.path.exists(_o11_pip):
        tid = tid_3q = open(_o11_pip).read().strip()   # small pipCallout box only
        open(os.path.join(A, "host_outfit.txt"), "w").write(
            f"{os.path.basename(_host_ref)} (PINNED)\n")
        print(f">> host PINNED to {os.path.basename(_host_ref)} "
              f"(framed host = WIDE {(framed_tid or '?')[:8]}..., "
              f"pip box = {tid[:8]}...) — rotation held until HOST_OUTFIT_POOL=on")
    else:
        # Phase 0 (2026-08-19): the resolved host outfit has no .heygen_photo_id_pip,
        # so a Short cannot render its host from it. This is exactly the long-form
        # outfit_12 case: it has closeup/rest ids but not the pip/wide a Short needs.
        # The old line here opened the legacy CACHE id, which HeyGen now 404s — so a
        # chosen-but-unrenderable cast shipped as a DIFFERENT host (outfit_11) with no
        # signal. REFUSE loudly: record the refused slot to provenance, then abort.
        _RESOLVED.append({"asset_type": "host_outfit", "build_ref": _host_ref,
                          "resolved_from": "refused",
                          "version_id": _VERSION_ID_BY.get(("template", "host_outfit"))})
        try:
            _flush_provenance(CHANNEL_KEY_FOR_PROV, ep, tag, calendar_id)
        except Exception:
            pass
        _chosen = bool(_TPL_VERSION_ID) or _host_ref != _HOST_DEFAULT
        raise CastUnrenderable(
            f"host_outfit '{os.path.basename(_host_ref)}' has no pip/wide photo-avatar "
            f"ids — it is a long-form host and cannot render a Short. "
            + ("Chosen via a locked cast — pick a short-fit host (pip+wide) or generate "
               "them; NOT silently substituting a different host."
               if _chosen else
               "This is the channel default and is missing its ids — an infra problem."))
    if not framed_tid:
        framed_tid = tid   # fallback if the wide-avatar id file is missing
    # Phase 4 provenance: WHICH composed cast produced this episode, on disk beside
    # host_outfit.txt. "- v- (none)" means no template version drove the build.
    try:
        open(os.path.join(A, "template_version.txt"), "w").write(
            f"{_TPL_INFO.get('template_key','-')} v{_TPL_INFO.get('version','-')} "
            f"({_TPL_INFO.get('id','none')})\n")
    except Exception as e:
        print(f"!! could not write template_version.txt ({e})")
    def host_clip(name, t0, t1, photo=None, aspect="9:16"):
        wav = os.path.join(A, f"{name}.wav"); mp4 = os.path.join(A, f"{name}.mp4")
        # v16: also skip cache when FACTORY_REBUILD_HOSTS is set — lets a shell
        # wrapper force fresh HeyGen renders across ALL runs (hook/mid/payoff)
        # without needing shell-portable glob deletion (zsh nullglob failure
        # bit Ep 10 v3: 'no matches' aborted the whole rm before v2_hook/payoff
        # were removed, so the master reused stale clips).
        stale = os.environ.get("FACTORY_REBUILD_HOSTS", "").lower() in ("1", "true", "yes")
        if stale or not os.path.exists(mp4):
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t0), "-t", str(t1 - t0),
                 "-i", vo, "-c:a", "pcm_s16le", wav])
            generate(photo or tid, upload_audio(wav), mp4, aspect=aspect)
            # v16 inline lipsync auto-correct: a HeyGen render adds a
            # per-clip audio lead (measured 123-234 ms on Ep25); left
            # uncorrected, the host's mouth trails the voice by that much
            # and the whole clip reads out of sync. Measure the clip vs the
            # master VO from the beat's in-point; if lag > 45 ms (the
            # audio-ahead-of-video detection threshold), regenerate a
            # sync-corrected copy in place. Correlation < 0.85 = the render
            # is NOT a straight time-shift and no cut fixes it (log a
            # warning, ship as-is, human decides).
            try:
                sys.path.insert(0, os.path.join(REPO, "scripts"))
                import lipsync_align
                lag, corr = lipsync_align.measure(mp4, vo, at=t0, search=0.7)
                print(f">> lipsync {name}: lag={lag*1000:+.0f}ms corr={corr:.3f}")
                if corr < 0.85:
                    print(f"!! lipsync corr low — leaving {name} uncut (human review)")
                elif abs(lag) > 0.045:
                    sync_mp4 = mp4 + ".sync.mp4"
                    lipsync_align.cut(mp4, lag=lag, dur=(t1 - t0), out=sync_mp4)
                    os.replace(sync_mp4, mp4)
                    print(f">> lipsync corrected {name}: cut lag={lag*1000:+.0f}ms")
            except Exception as e:
                print(f"!! lipsync check failed for {name}: {e}")
        return mp4

    beats = cfg["beats"]
    news_split = cfg.get("layout") == "newsSplit"
    # v16 host_runs: previously the beat parser only accepted a leading run of
    # "host" + a trailing run of "host2", so a plan with mid-beat Sol cutaways
    # (Ep 10 planned 7s/18s/35s/50s cutaways -- none rendered) was silently
    # collapsed to hook + payoff only. Now we walk beats, collect every
    # host-or-host2 run at its actual position, render one HeyGen clip per
    # run, and alternate the tid across runs so yaw variety travels through
    # the whole episode not just the bookends.
    host_runs = []  # list of (kind, seg_start, seg_end_exclusive, t0, t1)
    _seg_t = [0.0]
    for d in seg_durs:
        _seg_t.append(_seg_t[-1] + d)
    i = 0
    while i < len(beats):
        b = beats[i]
        if b in ("host", "host2"):
            j = i
            while j + 1 < len(beats) and beats[j + 1] == b:
                j += 1
            host_runs.append((b, i, j + 1, _seg_t[i], _seg_t[j + 1]))
            i = j + 1
        else:
            i += 1
    n_hook = beats.count("host")
    n_pay = beats.count("host2")
    hook_end = sum(seg_durs[:n_hook]) if beats[:1] == ["host"] else 0.0
    if news_split:
        full_host = host_clip("v2_host", 0, total)
        hook_mp4 = pay_mp4 = None
        hook_end = 0.0
        host_clip_by_run = {}
    else:
        # Per-run HeyGen clips. Alternate photo across runs (index parity) so
        # even runs use center (tid) and odd runs use 3q (tid_3q) — the yaw
        # rotation the wardrobe pool was registered for. Continuity note: the
        # legacy hook/payoff files stay as-is (v2_hook.mp4, v2_payoff.mp4) so
        # existing episodes rebuild identically; new interleaved runs get
        # v2_host_02.mp4 / v2_host_03.mp4 etc.
        host_clip_by_run = {}
        for run_idx, (kind, si, sj, t0, t1) in enumerate(host_runs):
            if run_idx == 0 and kind == "host":
                name = "v2_hook"
            elif run_idx == len(host_runs) - 1 and kind == "host2":
                name = "v2_payoff"
            else:
                name = f"v2_host_{run_idx:02d}"
            # v16.4: the FramedHost card is 16:9, so render the host WIDE from the
            # wide avatar (framed_tid). No yaw rotation — the wide talking head is
            # a single premium landscape shot (the Ep11 look), not the old 9:16
            # portrait pool that letterboxes inside the 16:9 card.
            host_clip_by_run[(si, sj)] = host_clip(name, t0, t1, photo=framed_tid, aspect="16:9")
        # Preserve names old code paths still expect (segment builder below)
        first_hook = next((k for k in host_clip_by_run
                           if beats[k[0]] == "host"), None)
        last_pay = next((k for k in reversed(list(host_clip_by_run))
                         if beats[k[0]] == "host2"), None)
        hook_mp4 = host_clip_by_run[first_hook] if first_hook else None
        pay_mp4 = host_clip_by_run[last_pay] if last_pay else None

    # v16 Vaibhav-DNA: pipCallout beats ("pip:<id>"). Each renders a HeyGen host
    # clip of ITS OWN VO slice, shown small in the bottom-left rounded-square PIP
    # while the beat's product screencap plays in the top zone. Consistent center
    # tid across all pip beats so Sol reads as one continuous take across the
    # numbered list (Vaibhav keeps the same PIP framing for every point).
    pip_clip_by_beat = {}
    if not news_split:
        for bi, bb in enumerate(beats):
            if bb.startswith("pip:"):
                pip_clip_by_beat[bi] = host_clip(
                    f"v2_pip_{bb[4:]}", _seg_t[bi], _seg_t[bi + 1], photo=tid)

    # v16.4 MIX ENGINE — each command (pip:) beat is randomly assigned a
    # presentation mode so no two episodes feel templated: "splitWide" (recording
    # + the SAME wide landscape host + #NN) or "recFull" (full-screen recording
    # with a Ken-Burns pan + #NN, no host). Balanced half-and-half, shuffled with
    # a seed derived from the episode key so the mix is varied but reproducible.
    import hashlib as _hl, random as _rnd
    _pids = [bb[4:] for bb in beats if bb.startswith("pip:")]
    _rng = _rnd.Random(int(_hl.md5(str(ep).encode()).hexdigest(), 16))
    _modes = (["splitWide"] * ((len(_pids) + 1) // 2)) + (["recFull"] * (len(_pids) // 2))
    _rng.shuffle(_modes)
    pip_mode = dict(zip(_pids, _modes))

    # splitWide beats show a LANDSCAPE host — generate it through host_clip so it
    # is cut from the master-VO slice AND lipsync-corrected (same path as the
    # full-frame host clips). This fixes the desync from the earlier hand-rolled
    # wide clips. Uses the WIDE photo-avatar (16:9 via generate(aspect=...)).
    _wide_id = _o11_wide  # reuse the lock-resolved outfit so splitWide beats track the same host lock
    WIDE_TID = open(_wide_id).read().strip() if os.path.exists(_wide_id) else None
    wpip_by_pid = {}
    if not news_split and WIDE_TID:
        for bi, bb in enumerate(beats):
            if bb.startswith("pip:") and pip_mode.get(bb[4:]) == "splitWide":
                pid = bb[4:]
                wpip_by_pid[pid] = host_clip(f"v2_wpip_{pid}", _seg_t[bi], _seg_t[bi + 1],
                                             photo=WIDE_TID, aspect="16:9")

    # 3) segments for remotion (paths relative to remotion public/)
    def rel(p): return os.path.relpath(p, os.path.join(CH, "assets")).replace("\\", "/")
    segments, t0 = [], 0.0
    i = 0
    while i < len(beats):
        start_i = i                           # v16: remember run start for host_clip_by_run lookup
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
        elif b in ("host", "host2"):
            # v16 interleaved-cutaway: find the run this beat belongs to (by the
            # start_beat_index recorded when we walked beats above) and use ITS
            # HeyGen clip. Legacy leading-run / trailing-run beats still land on
            # v2_hook.mp4 / v2_payoff.mp4 unchanged.
            run_src = hook_mp4 if b == "host" else pay_mp4
            for (si, sj), clip in host_clip_by_run.items():
                if si <= start_i <= sj - 1:
                    run_src = clip
                    break
            # v16.2: framed=True renders the host as a contained rounded card on
            # the gradient bg (not a full-bleed giant face) — see Short.tsx FramedHost.
            segments.append({"src": "assets/" + rel(run_src), "dur": round(dur, 3),
                             "framed": True})
        elif b.startswith("rec:"):
            src, frm = b[4:].split("@")
            seg = {"src": f"assets/{src}", "dur": round(dur, 3), "from": float(frm)}
            if news_split and mode:
                seg["mode"] = mode
            # v16.5: on an episode whose recording IS the taught content edge to
            # edge (a comparison table), the default Anton-78 caption at bottom
            # 21% lands on the cells. cap_low_rec drops every rec beat's running
            # caption into the low plain strip instead — measured, not guessed
            # (probe_frames corner on this tape: no corner is clean at bottom).
            if cfg.get("cap_low_rec"):
                seg["capLow"] = True
            # Build Club "|phone" suffix: case the recording in the drawn
            # high-end Android bezel (PhoneFrame) + captions to the low strip
            # (the device ends well above it). The rsplit("|") above already
            # stripped the suffix into `mode` for ALL layouts.
            if mode == "phone":
                seg["frame"] = "phone"
                seg["capLow"] = True
            segments.append(seg)
        elif b.startswith("stat:"):
            # chart beat: locked StatBars comp draws it in-frame at 1080x1920
            # (playbook §4 — never a pre-baked card video that gets cover-cropped)
            seg = {"kind": "statBars", "dur": round(dur, 3)}
            if news_split and mode:
                seg["mode"] = mode
            seg["stat"] = cfg["stats"][b[5:]]
            segments.append(seg)
        elif b == "chapter":
            # Build Club (bc eps): full-frame chapter-book opener, drawn in-comp
            # (components/BuildClub.tsx ChapterCard). Payload key is
            # cfg["chapter_card"] — plain cfg["chapter"] is the series' chapter
            # NUMBER, consumed by finalize_episode.apply_series_suffix.
            segments.append({"kind": "chapterCard", "dur": round(dur, 3),
                             "chapter": cfg["chapter_card"]})
        elif b == "pause":
            # Build Club: the pause-and-copy prompt card. The lines shown MUST be
            # the real shared prompt (BUILD-CLUB.md: never a simplified version
            # of the pinned one).
            segments.append({"kind": "pauseCard", "dur": round(dur, 3),
                             "pause": cfg["pause"]})
        elif b == "recipe":
            # Build Club: recap checklist + homework ending card.
            segments.append({"kind": "recipeCard", "dur": round(dur, 3),
                             "recipe": cfg["recipe"]})
        elif b.startswith("pip:"):
            # v16.4 MIX ENGINE: recording + #NN callout, rendered as either a
            # wide-host split-screen or a full-screen recording (see pip_mode).
            pid = b[4:]
            p = cfg["pips"][pid]
            mode = pip_mode.get(pid, "splitWide")
            if mode == "splitWide" and pid not in wpip_by_pid:
                mode = "recFull"                                      # no wide clip -> fall back
            seg = {
                "kind": mode,                                         # "splitWide" | "recFull"
                "dur": round(dur, 3),
                "src": f"assets/{p['src']}",
                "from": float(p.get("from", 0)),
                "num": str(p.get("num", "")),   # optional: single-tip callouts have no rank
                "lines": p["lines"],
            }
            if mode == "splitWide":
                # host_clip already cut this to the beat's VO slice + lipsync-
                # corrected it, so play it from the top (pipFrom 0), in sync.
                seg["pip"] = "assets/" + rel(wpip_by_pid[pid])
                seg["pipFrom"] = 0.0
            segments.append(seg)
        elif b.startswith("cook:"):
            # Sprint-2 cookbook beat ("cook:<componentId>"): draw a Visual-Cookbook
            # component in-frame for this beat's VO slice. Mirrors the pip: branch —
            # the beat's merged dur is the segment dur; props come from
            # cfg["cookbook"][<componentId>] (a dict keyed by component id), default {}.
            # Emits the EXACT Short.tsx contract shape: seg["cookbook"]["id"]/["props"].
            # "cook:<Id>" or "cook:<Id>#<variant>" — the variant suffix lets ONE
            # component appear on several beats with different props (e.g. two
            # ScreenStage beats pointing at different offsets of the same tape).
            # Component id is before the '#'; the FULL string is the props key.
            raw_cid = b[5:]
            cid = raw_cid.split("#", 1)[0]
            if isinstance(cid, str) and cid:
                cb_props = cfg.get("cookbook") or {}
                props = dict(cb_props.get(raw_cid, cb_props.get(cid, {})))
                # `host: true` -> generate a HeyGen clip cut from THIS beat's own
                # VO slice (so the lipsync matches the words spoken over it) and
                # swap the real path in. Same path pip: beats use.
                if props.get("host") is True:
                    # The pinned PIP photo-avatar (dc9533a1...) is GONE from the
                    # HeyGen account — /v3/videos returns avatar_not_found. The
                    # WIDE avatar is alive (the host beats render from it), so the
                    # PIP is cut from the wide 16:9 avatar and shown as a small
                    # landscape card rather than a square crop.
                    _pip_tid = WIDE_TID or framed_tid or tid
                    _hc = host_clip(f"v2_cook_{raw_cid.replace('#', '_')}",
                                    _seg_t[i], _seg_t[i + 1],
                                    photo=_pip_tid, aspect="16:9")
                    props["host"] = "assets/" + rel(_hc)
                segments.append({"kind": "cookbook", "dur": round(dur, 3),
                                 "cookbook": {"id": cid, "props": props or {}}})
            else:
                print(f"!! cook: beat with empty component id — skipped ({b!r})")
        i += 1

    # Sprint-2: a LOCKED composition may freeze an ordered block sequence
    # (composition["_sequence"], resolved from the SAME row the cast came from).
    # When present, append each block's cookbook/slot segment (EXACT Short.tsx
    # contract shapes) to augment the classic beat segments above. When no
    # _sequence is bound, _composed_sequence() is [] and this is a no-op — the
    # classic beat path stays byte-for-byte unchanged.
    _seq_replace = _sequence_mode() == "replace"
    for _idx, _blk in enumerate(_composed_sequence(CHANNEL_KEY_FOR_PROV)):
        _seg = _seq_segment(_blk)
        if _seg is not None:
            # REPLACE: the scene IS a VO line, so time it from seg_durs (the VO
            # clock, 1 scene:1 line) instead of the block's placeholder config.dur.
            # AUGMENT keeps config.dur (extra b-roll after the spoken beats).
            if _seq_replace and _idx < len(seg_durs):
                _seg["dur"] = round(seg_durs[_idx], 3)
            segments.append(_seg)
        # S4 block reconciliation: record EVERY locked block, rendered or not.
        # A locked block _seq_segment() dropped (rendered=False) is a real
        # divergence — the reviewer sees it in the sequence-reconciliation card.
        _RESOLVED_BLOCKS.append({
            "position": _blk.get("position", 0),
            "block_type": _blk.get("block_type"),
            "layout": (_seg or {}).get("slot", {}).get("layout")
                      if isinstance(_seg, dict) else None,
            "ref": _block_ref(_blk),
            "rendered": _seg is not None,
        })

    # steps -> absolute times
    line_starts = []
    acc = 0.0
    for d in seg_durs:
        line_starts.append(acc); acc += d
    # optional 4th tuple element = chip corner (tl/tr/bl/br) — put the chip in
    # dead space, never over the content the beat is teaching (user feedback Ep11).
    # optional 5th tuple element = style ("chip"|"hashtag") — v16 Vaibhav-DNA:
    # "hashtag" renders a lime Playfair #NN badge to keep the numbered-list count
    # alive over host-hero beats between pipCallout beats.
    steps = []
    for tup in cfg["steps"]:
        lab, a, b = tup[0], tup[1], tup[2]
        st = {"label": lab, "start": round(line_starts[a], 2),
              "end": round(line_starts[b] + seg_durs[b], 2)}
        if len(tup) > 3:
            st["pos"] = tup[3]
        if len(tup) > 4:
            st["style"] = tup[4]
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
        "watermark": True,
        "epTag": cfg.get("epTag"),
        # v16.5: dark scrim under the global header for episodes cut from a LIGHT
        # recording (claude.ai's cream chat column) — without it the white/magenta
        # lockup washes out and collides with the app's own header text.
        "headerScrim": bool(cfg.get("header_scrim")),
    }
    # v16.3: illustration hook opener REPLACES the poster cover on premium
    # episodes (VJ: a title card reads as an intro + gets scrolled past). When
    # cfg["hook"] is present we emit `hook` and drop `cover`; otherwise the
    # legacy poster cover is emitted exactly as before.
    if cfg.get("hook"):
        hk = dict(cfg["hook"])
        if not hk["image"].startswith(("assets/", "http")):
            hk["image"] = "assets/" + hk["image"]
        hk.setdefault("until", round(min(max(hook_end + 0.6, 1.6), 3.0), 2))
        spec["hook"] = hk
    elif cfg.get("cover"):
        spec["cover"] = {**cfg["cover"],
                         "until": cfg["cover"].get(
                             "until",
                             round(min(max(hook_end + 0.6, 0.7), 1.8), 2) if not news_split else 2.2)}
    # else (Sprint-5 replace auto-short): no cover/hook — open straight on scene 0.
    # v16.3: attach the static key line that fills each framed-host "THE IDEA"
    # panel (order matches the framed segments: hook run, then payoff run, ...).
    host_panels = cfg.get("host_panels", [])
    framed_segs = [s for s in segments if s.get("framed")]
    for s, panel in zip(framed_segs, host_panels):
        s["hostLines"] = panel["lines"]
        if panel.get("hot"):
            s["hostHot"] = panel["hot"]
        if panel.get("hot"):
            s["hostHot"] = panel["hot"]
    if news_split:
        spec["layout"] = "newsSplit"
        spec["host"] = "assets/" + rel(full_host)
    # Build Club rail (bc eps): persistent PROMPT->FILE->LIVE progress rail over
    # the teaching window. cfg["rail"] = {labels, start_lines (0-based line idx
    # where each node becomes ACTIVE), until_line (rail hides at its start)}.
    if cfg.get("rail"):
        _r = cfg["rail"]
        spec["rail"] = {
            "labels": _r["labels"],
            "starts": [round(line_starts[i], 2) for i in _r["start_lines"]],
            "until": round(line_starts[_r["until_line"]], 2),
        }
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

    # Phase 1 (2026-08-19): resolve the reusable cast slots (music bed, outro sting,
    # outro_cta) ONCE, up front — BEFORE the preview return below — so the whole cast
    # lands in _RESOLVED and _flush_provenance records it on EVERY build, preview
    # included (host_outfit + remotion_comp are already resolved above / at the raw
    # render). The master + outro lines below CONSUME cast[...] instead of calling
    # resolve_locked again, so no slot is double-appended.
    cast = resolve_cast(cfg)

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
    run(["npx", "remotion", "render", resolve_locked("remotion_comp", "Short"), raw,
         f"--props={sp}", *rflags],
        cwd=os.path.join(REPO, "remotion-studio"))

    if preview:
        # v16: stop after raw. Skip mastering, endcard, outro. The raw IS the
        # preview — 1080x1920 with clean unmastered VO, no music bed, no polish.
        # Human review happens on this file; scripted finalize_episode.py picks
        # up the SAME cfg later and runs mastering + endcard + outro to publish.
        print(f">> PREVIEW mode — stopped after raw: {raw}")
        _flush_provenance(CHANNEL_KEY_FOR_PROV, ep, tag, calendar_id)
        _flush_sequence_provenance(CHANNEL_KEY_FOR_PROV, ep, tag, calendar_id)
        # S6 (Sprint 5): stamp the generation manifest onto the calendar row so the
        # review board can show what this produce made (scene-linked, free|paid,
        # low-confidence). Additive + never fails the produce (render already done).
        if calendar_id:
            try:
                _rs = _composed_sequence(CHANNEL_KEY_FOR_PROV) if _sequence_mode() == "replace" else []
                _emit_manifest(ep, tag, cfg, _rs, calendar_id, quiet=True)
            except Exception as e:
                print(f"!! manifest stamp skipped ({e}) — render is unaffected")
        return raw

    # 5) master: sidechain-ducked music + limiter
    out = os.path.join(R, f"ep{ep}_{tag}.mp4")
    # per-episode bed override (cfg["music"], relative to assets/); defaults to
    # the channel's locked active bed
    # _LOCK_CFG_KEY["music_bed"] == "music", so a per-episode cfg["music"]
    # override still wins — this only adds the lock/template layers beneath it.
    # Phase 1: consume the up-front resolve_cast() result (already recorded in
    # provenance) instead of re-resolving here (which would double-append).
    music = os.path.join(CH, "assets", cast["music_bed"])
    assert os.path.exists(music), f"music bed missing: {music}"
    # The locked 0.35 mix ratio (playbook §3) was calibrated against the channel's
    # standing bed at -8.3 LUFS. A per-episode bed at a different programme level
    # would land the master off the channel's shipped -18.8 LUFS spine, so a
    # substituted bed is LEVEL-MATCHED to that reference first. Chain topology
    # itself stays locked.
    mg = float(cfg.get("music_gain_db", 0.0))
    pre = f"volume={mg}dB," if mg else ""
    # v16 mix rebalance + Vaibhav-DNA loudness target:
    #   Music 0.20 · VO +14 dB · sidechain gives VO ~5 LU dominance
    #   (radio-quality talking-head ratio) — see Ep 10 v3 measurement.
    #   loudnorm=I=-14:TP=-1:LRA=11 pulls the integrated to YouTube's
    #   reference level (competitor teardown 2026-08-11: Vaibhav Sisinty's
    #   360K-view Short 'MYOdDsEAMns' ships -14.4 LUFS; ours at -18.4 was
    #   4 LU quieter in the feed). Single-pass loudnorm adds trivial
    #   distortion at these low LRA values; alimiter catches any residual
    #   over-shoot at -0.45 dBFS (raised from -1.0 to give the louder mix
    #   room to breathe under YT's -1 TP recommendation).
    fc = (f"[1:a]{pre}volume=0.20,afade=t=in:st=0:d=1.5[m];"
          "[0:a]volume=14dB,asplit=2[v1][v2];"
          "[m][v2]sidechaincompress=threshold=0.05:ratio=8:attack=40:release=600[duck];"
          "[v1][duck]amix=inputs=2:duration=first:normalize=0,"
          "loudnorm=I=-14:TP=-1:LRA=11,alimiter=limit=0.95[a]")
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
    _outro_owner = _outro_source()
    if cfg.get("outro") and _outro_owner == "sequence":
        print(">> OUTRO owned by the composed sequence — classic sting SKIPPED "
              "(look setting outro_source=sequence). The sequence scene must carry "
              "the question and the CTA words itself.")
    if cfg.get("outro") and _outro_owner == "sting":
        # v16.2: per-episode outro override (cfg["outro_src"], relative to assets/)
        # so premium episodes can use a stronger question-CTA card instead of the
        # shared subscribe/comment sting.
        # Phase 1: consume resolve_cast()'s outro sting (already in provenance);
        # re-resolving here would double-append the slot.
        outro = os.path.join(CH, "assets", cast["outro_sting"])
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
        # 2026-08-13 subscriber-conversion experiment: cfg["outro_cta"] makes Sol
        # SPEAK a series CTA (next-episode tease from factory_calendar, or the
        # series promise) OVER the question card. Absent (all locked templates
        # today) -> the shipped filtergraph below runs unchanged. HELD pending
        # VJ approval of the test render — do not add outro_cta to the locked
        # templates until then. See channels/claude-tricks/outro_cta.py.
        cta = None
        # Phase 1: consume resolve_cast()'s outro_cta setting (already recorded in
        # provenance via resolve_setting); resolving it again would double-append.
        _cta_mode = cast["outro_cta"]
        if _cta_mode:
            if CH not in sys.path:
                sys.path.insert(0, CH)
            from outro_cta import prepare_cta, probe_dur
            # prepare_cta reads the mode from cfg["outro_cta"], so a mode that
            # came from the CAST (not the episode spec) has to be handed over
            # explicitly — otherwise a cast-set CTA would resolve here and then
            # be dropped one call later.
            cta = prepare_cta({**cfg, "outro_cta": _cta_mode}, A, ELEVEN_VOICE,
                              style=STYLE, calendar_id=calendar_id)
        if cta:
            # The card must HOLD until the spoken line lands: retime the card
            # (slower Ken-Burns push, same frames) instead of re-rendering the
            # branding asset (§15 bookends hygiene). 0.45s lead-in before Sol
            # speaks, 0.8s hold after. A sting trimmed by outro_dur keeps its
            # trim (the cut point is a measurement) and is then retimed.
            base = probe_dur(outro)
            if odur:
                base = min(base, odur)
                print(f"!! outro_cta over a trimmed sting ({odur}s) — retiming "
                      "the trimmed cut; check the sting's element schedule")
            need = 0.45 + cta["dur_s"] + 0.8
            T = round(max(base, need), 3)
            fst = round(max(T - 1.6, 0.3), 3)
            fc2 = outro_fc(pre, fst, ratio=T / base, gain_db=cta["gain_db"])
            run(["ffmpeg", "-y", "-i", out] + tin + ["-i", outro,
                 "-stream_loop", "-1", "-i", music, "-i", cta["wav"],
                 "-filter_complex", fc2, "-map", "[v]", "-map", "[a]",
                 *venc("18", "veryfast"),
                 "-c:a", "aac", "-b:a", "192k", "-shortest", out2])
            print(f">> OUTRO APPENDED + SPOKEN CTA ({T}s, {cta['note']})", out2)
            out = out2
        else:
            fst = round(max(odur - 1.2, 0.0), 3) if odur else 2.6
            fc2 = outro_fc(pre, fst)
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
    _flush_provenance(CHANNEL_KEY_FOR_PROV, ep, tag, calendar_id)
    _flush_sequence_provenance(CHANNEL_KEY_FOR_PROV, ep, tag, calendar_id)
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", required=True,
                    help="episode key from EPISODES_V2, OR a key with a "
                         "fallback spec at episodes/<ep>.v2.json (v16)")
    ap.add_argument("--dry", action="store_true",
                    help="regenerate the episode spec JSON only (no render/master)")
    ap.add_argument("--manifest", action="store_true",
                    help="Sprint-5: emit the pre-render generation manifest (assets + "
                         "scene links + free/paid + low-confidence) and stop, BEFORE any "
                         "VO/HeyGen/render spend. Persists to factory_calendar when "
                         "--calendar-id is given.")
    ap.add_argument("--preview", action="store_true",
                    help="v16: stop after Remotion raw render — no master, "
                         "no endcard, no outro. For produce_preview jobs.")
    ap.add_argument("--tag", default="v2",
                    help="render stem: ep<NN>_<tag>.mp4 (use v3 for a re-cut so "
                         "the shipped v2 file survives for comparison)")
    ap.add_argument("--calendar-id",
                    help="this episode's factory_calendar row id — only used to "
                         "EXCLUDE it from the outro_cta next-episode tease lookup "
                         "(finalize_episode.py passes it through)")
    ap.add_argument("--template-version",
                    help="Phase 4: factory_template_versions.id of the composed CAST "
                         "to render with. Only a status='locked' version of this "
                         "channel is honoured; anything else (or omitted) falls "
                         "through to the channel's factory_asset_locks")
    ap.add_argument("--allow-cast-override", action="store_true",
                    help="Phase 2: proceed even when the spec/CLI/env template_version "
                         "CONTRADICTS the calendar's pinned cast. Without this (and "
                         "without FACTORY_ALLOW_CAST_OVERRIDE=1) a divergence REFUSES "
                         "the build (CastUnrenderable) instead of silently swapping the "
                         "owner's deliberate cast pin. Operator escape hatch only.")
    a = ap.parse_args()
    build(a.ep, dry=a.dry, tag=a.tag, preview=a.preview, calendar_id=a.calendar_id,
          template_version=a.template_version, allow_cast_override=a.allow_cast_override,
          manifest=a.manifest)
