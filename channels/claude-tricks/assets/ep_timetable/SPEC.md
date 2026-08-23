# _timetable — production spec (idea-first slate, 2026-08-21)

Ranked 90/100 of 15 candidates generated with NO component constraint.
Arithmetic verified against the real calendar before any frame was designed.

# PRODUCTION SPEC — `_timetable`

**Title:** `I Built A Study Timetable By Typing One Line 📚` (44 chars + emoji)
**Composition:** 1080×1920, 30fps, `durationInFrames = 1035` (34.5s)
**Pinned prompt (given in-video AND in first comment, manually):**
> `Build me a study timetable: I'll type my exam date and my chapter list, and you show me the days I actually have left and put a chapter on each one.`

**The arithmetic this episode is built on — computed, not assumed:**

| | |
|---|---|
| Top tile (today) | **Sat 22 Aug 2026** |
| Bottom tile (exam) | **Mon 28 Sep 2026** |
| Day tiles between, exclusive of exam | **37** |
| Rule the viewer types | "I can only study on Saturday and Sunday" |
| Surviving tiles | **12** (22/23, 29/30 Aug · 5/6, 12/13, 19/20, 26/27 Sep) |
| Killed tiles | **25**, in **5 clean runs of 5 weekdays** → 5 fold groups, regular cadence |
| Chapters | **14** |
| Splits required | **2** (12 whole − 2 + 4 halves = **14 slots** = 14 chips) |

Conservation on screen: 37 → 12 → 2 doubled → 14 slots → 14 chips. Every number is countable on the same frame it appears. Verified with `python3` against the real calendar (script in §4).

---

## 1. VO — 8 lines, 88 words, 34.5s

Sol, style 0.4. Rate held at 2.65–2.78 w/s on every line. The two deliberate silences are placed where the picture needs them: **6.00–6.35s** (the count flip) and **17.0–17.6s** (the overflow freeze, inside L5's own sentence gap).

| # | in | out | dur | w | w/s | Line |
|---|---|---|---|---|---|---|
| 1 | 0.00 | 2.25 | 2.25 | 6 | 2.67 | **You don't have five weeks left.** |
| 2 | 2.25 | 6.00 | 3.75 | 10 | 2.67 | Type in your exam date, your chapters, and one rule. |
| 3 | 6.35 | 10.10 | 3.75 | 10 | 2.67 | Mine was: I can only study on Saturday and Sunday. |
| 4 | 10.35 | 15.20 | 4.85 | 13 | 2.68 | Thirty-seven days on the calendar. Only twelve you'd actually sit down and study. |
| 5 | 15.40 | 20.10 | 4.70 | 13 | 2.77 | Then it runs out of days. Fourteen chapters, twelve weekends — two don't fit. |
| 6 | 20.40 | 25.25 | 4.85 | 13 | 2.68 | So two days do double duty. Fourteen chapters, fourteen slots, nothing quietly dropped. |
| 7 | 25.50 | 29.65 | 4.15 | 11 | 2.65 | Count the days yourself once — it's arithmetic, and it can slip. |
| 8 | 29.75 | 34.25 | 4.50 | 12 | 2.67 | It can't remind you — screenshot it. The full line's in the comments. |

L1 lands the whole hook in 2.25s, under the 2.5s floor. L7 is the mandated caution line and is **not cuttable**. L8 contains the literal mandated string "It can't remind you — screenshot it."

**Banned from VO and from every frame:** remind, reminder, alarm, notify, notification, schedule, sync, "add to calendar", "sets it up for you". Sol never says Claude knows the viewer's exam, school, or syllabus.

---

## 2. Beat sheet — 8 beats, frame-exact

Safe area: header floor **y=132**; all mechanism lives **y ∈ [132, 1500]**; caption plate from **y=1560**; nothing load-bearing below **y=1590**.

**Beat 1 — COLD OPEN · 0.00–2.30s (f0–f68)**
Frame opens already loaded: a single column of **38 dim slate rungs** (37 days + 1 red EXAM rung) running y=360→1484, pitch 30px (rung h 23, gap 7), width 760 centred. Each rung carries its date at 20px mono, 34% opacity, left-inset 24px. Header rail at y=150: `22 AUG → 28 SEP` in 34px mono. Count plate at y=215–330: numeral **37** at 104px + label `DAYS` at 28px. Motion: whole ladder slow push-in, `scale 1.000 → 1.045` over f0–f180, easeOutQuad; the exam rung breathes (opacity 0.86↔1.00, 40-frame sine). Nothing else moves. The eye reads *long, grey, and finite* before a word is spoken.

**Beat 2 — THE LINE + THE RULE · 2.30–4.00s (f69–f119)**
f68: the burned prompt plate fades in at y=1300–1440 (full one-liner, 34px, 2 lines, 88% opacity) and **holds until f180 — 3.75s on screen, clear of the 1.6s floor.**
f96–f112: the rule types itself into a **right-aligned user bubble with a live caret**, 1 char/frame, bubble rising y=1560→1470 on `spring({damping:200, mass:0.6})`. Text: `I can only study Sat + Sun`.
**f114: bubble lands and locks.** Caret stops.
**Gate: first fold is f120 — 6 frames later.** The rule is visibly the viewer's before anything is deleted.

**Beat 3 — THE FOLD RIPPLE + HOLD · 4.00–6.00s (f120–f179)**
Five weekday runs fold **bottom-to-top** (from the exam upward — reads as counting back), stride 10 frames:

| group | rungs | fires |
|---|---|---|
| G1 | Mon 21 – Fri 25 Sep | f120 |
| G2 | Mon 14 – Fri 18 Sep | f130 |
| G3 | Mon 7 – Fri 11 Sep | f140 |
| G4 | Mon 31 Aug – Fri 4 Sep | f150 |
| G5 | Mon 24 – Fri 28 Aug | f160 |

Per group: rungs stagger 1 frame within the group; each rung rotates `rotateX 0 → −88°` about its **top edge** (perspective 800px) over 7 frames, fill lerps `#2A2E37 → #15171C`, opacity 0.62 → 0.26, and height lerps 23 → 5 over the fold's last 4 frames. The fold *is* the collapse. Everything below a folding group translates up by the reclaimed height (per-rung `yOffset(frame)` accumulator — **do not use flex layout; this must be frame-pure**). Each group fires a **3-frame white leading-edge flash** — that is the visible "click". Five clicks, evenly spaced, countable at 2x.
f168–f179: **hold.** No positional change. The 12 survivors pulse together once, brightness 1.00 → 1.18 → 1.00 over 12 frames. VO is silent from 6.00.

**Beat 4 — THE 6.00 FRAME + FIRST CHIPS · 6.00–8.20s (f180–f245)**
**f180 is the single hard cut of the video. Four things change on that one frame:**
1. Count numeral **hard-swaps 37 → 12** — no tween, plus a 2-frame 8% scale overshoot on the new numeral. Label swaps `DAYS` → `STUDY DAYS`.
2. Camera scale jumps `1.045 → 0.980` in one frame (the cut).
3. Exam rung blows to full white for exactly 1 frame, returns red.
4. **Direction reversal begins.** Survivor rungs expand `h 23 → 58`, gap `7 → 12`, on `spring({stiffness:180, damping:22, mass:0.9})` across f180–f198; dead slivers stay at 5px. The column re-flows and settles downward, and the eye's travel flips from upward (ripple) to downward (chips).

f189 (6.30s): first chapter chip spawns above frame at y=−120. f189–f245: CH 01–CH 04 fall and seat. **Every one of seconds 4, 5, 6, 7 and 8 carries a discrete mechanical event** — fold click, fold click, cut+digit+expand, chip fall, chip seat.

**Beat 5 — CHIPS SEAT · 8.20–14.50s (f246–f435)**
CH 05–CH 12 fall from the top edge on staggered arcs (stride 18 frames), each magnetising to the next open survivor slot top-down. Seat = tile scale `1.06 → 1.00` over 5 frames (spring) + the tile's date text right-shifts 12px to make room + a 2-frame contact shadow bloom. **No tick. No fill. No colour change to green. No streak chain.** (Habit-tracker adjacency guard.) By f435 all 12 survivors are loaded.

**Beat 6 — OVERFLOW · 14.50–20.00s (f435–f600)**
CH 13 and CH 14 arrive and find nothing open. They **hover at y≈260**, recolour to amber `#E8A33D`, and jitter ±4px on a 5-frame period, opacity pulsing 0.80–1.00. f510–f540 (17.0–18.0s): **freeze-and-jitter hold** — every other element's animation clock is suspended for 30 frames; only the two amber chips move. This is a freeze, **not a second cut**. f540–f600: the two bottom survivor tiles (Sat 26 / Sun 27 Sep) begin a 1° stress-shear, telegraphing the crack.

**Beat 7 — THE SPLIT · 20.00–27.00s (f600–f810)**
f600 / f606: survivors index 10 and 11 **crack horizontally** at their midpoint — a hairline opens, halves separate by 6px with a 3-frame shear and a dust-mote puff. The already-seated CH 11 and CH 12 slide to the **top** halves over 12 frames (easeInOutCubic). f624 and f636: the two amber chips drop into the **bottom** halves and recolour amber → ink on seat. f660–f720: count plate label animates `12 STUDY DAYS` → `12 DAYS · 14 SLOTS` (numerals hard-swap, label crossfades). The days closest to the exam are the ones doing double duty — semantically true and visually obvious without a caption.

**Beat 8 — THE CARD · 27.00–34.50s (f810–f1035)**
f810–f830: all 25 slivers animate `h 5 → 0`, opacity → 0. f830–f860: the 12 survivors close up, then expand into a **12-row screenshot card**: row h 84, gap 6, y=340→1414, each row `SAT 22 AUG · CH 01`, the two split rows showing two chips. Exam row at y=1424–1500 in red. Header rail becomes `22 AUG → 28 SEP · 12 DAYS · 14 CHAPTERS`. Card footer line, 28px, inside the card at y=1466: `Claude can't remind you.`
f900: **EXAMPLE** stamp, rotated −7°, scale 1.30 → 1.00 over 6 frames, opacity 0 → 0.85, positioned top-right of the card.
**f930–f1035 (31.0–34.5s): the frame is completely static.** 3.5 seconds of a clean, screenshot-able artifact under the CTA. This is the payoff and it must not move.

---

## 3. New components

Zero existing cookbook pieces are used. Two new components plus one shared pure-layout helper. Both are `useCurrentFrame()`-driven, no `useState`, no `Date.now()` — fully deterministic.

### 3.1 `DayLadder` — `remotion-studio/src/components/DayLadder.tsx`

**What it does.** Renders a vertical day-tile column between two dates, eliminates tiles by grouped domino fold-down driven by a viewer-typed rule chip, reports the survivor count as a hard-swapping numeral, expands survivors into seatable slots, cracks designated survivors into halves, and finally collapses the whole thing into a static readable card. It **owns all geometry** and exports a pure layout function so `ChipDrop` never has to guess where a slot is.

```ts
export type DayLadderProps = {
  span: { startISO: string; examISO: string };        // "2026-08-22", "2026-09-28"

  rule: {
    chipText: string;                                  // "I can only study Sat + Sun"
    keepDayOfWeek: number[];                           // [5,6]  (Sat, Sun — JS getDay 0=Sun → use [0,6])
    typeStartFrame: number;                            // 96
    landFrame: number;                                 // 114   MUST be <= foldStart - 4
  };

  // HONESTY ASSERTION — build throws if derived !== asserted.
  assert: { dayTiles: 37; survivors: 12; foldGroups: 5; chips: 14; splits: 2 };

  timing: {
    foldStart: number;          // 120
    foldGroupStride: number;    // 10
    foldDuration: number;       // 7   (per rung)
    holdEnd: number;            // 180
    cutFrame: number;           // 180  the one hard cut
    expandDuration: number;     // 18
    splitFrames: [number, number];   // [600, 606]
    collapseFrame: number;      // 810
    cardSettleFrame: number;    // 860
    stampFrame: number;         // 900
    freezeWindow: [number, number];  // [510, 540]  suspends all clocks except overflow chips
  };

  count: {
    preNumeral: string;  preLabel: string;             // "37", "DAYS"
    postNumeral: string; postLabel: string;            // "12", "STUDY DAYS"
    finalLabel: string;                                // "12 DAYS · 14 SLOTS"
    revealFrame: number;                               // 660
  };

  splits: { survivorIndex: number; frame: number }[];  // [{10,600},{11,606}]

  card: {
    headerText: string;      // "22 AUG → 28 SEP · 12 DAYS · 14 CHAPTERS"
    footerText: string;      // "Claude can't remind you."
    stampText: "EXAMPLE";
  };

  layout?: Partial<{
    top: number;      // 360
    width: number;    // 760
    rungH: number;    // 23
    rungGap: number;  // 7
    tileH: number;    // 58
    tileGap: number;  // 12
    sliverH: number;  // 5
    rowH: number;     // 84
  }>;

  theme: {
    slate: "#2A2E37"; slateDead: "#15171C"; ink: "#F2EFE9";
    bright: "#FFFFFF"; exam: "#D93A3A"; amber: "#E8A33D"; paper: "#0E1014";
  };
};

// Pure. Same frame in → same rects out. ChipDrop and DayLadder both call this.
export function dayLadderLayout(
  props: DayLadderProps, frame: number
): { slots: SlotRect[]; rungs: RungRect[]; ladderHeight: number };

export type SlotRect = {
  id: string;        // "2026-08-22" | "2026-09-26#top" | "2026-09-26#bot"
  x: number; y: number; w: number; h: number;
  openFrame: number; // frame from which a chip may seat here
  half: "none" | "top" | "bot";
};
```

**Motion, phase by phase (all `interpolate` with `extrapolateLeft/Right: "clamp"`):**

- **Idle** — global `scale = interpolate(f, [0,180], [1.000, 1.045], {easing: Easing.out(Easing.quad)})`.
- **RuleBubble** (inline sub-component, ~30 lines, not a cookbook entry) — right-aligned, `translateY = spring({frame: f - typeStartFrame, fps, config:{damping:200, mass:0.6}})` mapped 1560→1470; text sliced `chipText.slice(0, f - typeStartFrame)`; caret 2-on/2-off blink, killed at `landFrame`.
- **Fold** — rung *r* in group *g* has `foldF = f - (foldStart + g*stride + indexInGroup)`. `rotateX = interpolate(foldF,[0,7],[0,-88])`, `fill = interpolateColors(foldF,[0,7],[slate, slateDead])`, `h = interpolate(foldF,[3,7],[rungH, sliverH])`. Flash: `opacity = interpolate(foldF,[0,3],[0.9,0])` on a 2px top edge. Reclaimed height accumulates into `yOffset` for every rung below.
- **Hold** — `brightness = 1 + 0.18 * Math.sin(Math.PI * clamp((f-168)/12))` applied to survivors only.
- **Cut (f180)** — `frame < 180 ? preNumeral : postNumeral` (no tween). `scale = f < 180 ? interpolate(...) : 0.98 + 0.02*spring(f-180)`. Exam rung `filter: brightness(f===180 ? 6 : 1)`.
- **Expand** — `tileH_now = interpolate(spring({frame: f-180, fps, config:{stiffness:180, damping:22, mass:0.9}}), [0,1], [rungH, tileH])`.
- **Seat response** — `DayLadder` accepts `seatedAt: Record<slotId, number>` (frames, supplied by `ChipDrop` via the shared layout, or precomputed in the episode JSON — prefer precomputed, it keeps both components pure).
- **Split** — `gap = interpolate(f-splitFrame,[0,3],[0,6])`, `skewY = interpolate(f-splitFrame,[0,3],[0,1])` then back to 0 over 3 more frames.
- **Freeze** — `const fx = f > freezeWindow[0] && f < freezeWindow[1] ? freezeWindow[0] : (f >= freezeWindow[1] ? f - 30 : f)`. Every phase above reads `fx`, never `f`. The overflow chips read raw `f`.
- **Collapse to card** — slivers `h = interpolate(f-810,[0,20],[5,0])`, `opacity` likewise; survivors `h = interpolate(f-830,[0,30],[tileH, rowH])`, `gap → 6`.
- **Stamp** — `scale = interpolate(f-900,[0,6],[1.3,1.0], {easing: Easing.out(Easing.back(1.6))})`, `opacity → 0.85`, `rotate: -7deg`.
- **f930+** — all interpolations clamp; the tree renders identically for the last 105 frames.

**Hard prohibitions enforced in code review of this file:** no bell/clock/alarm/toggle glyph; no `%`; no bar, ring, or fill of any kind; no green; no checkmark; no flame; no filled-circle chain; no element whose width or height encodes a ratio.

### 3.2 `ChipDrop` — `remotion-studio/src/components/ChipDrop.tsx`

**What it does.** Drops labelled chips from above the frame, magnetises each to the next open slot from a supplied slot list, seats them with a scale overshoot, and — when chips outnumber open slots — leaves the remainder **hovering, amber and jittering** rather than silently discarding them. The overflow state is the whole reason this component exists; it must be a first-class render state, not an error path.

```ts
export type ChipDropProps = {
  chips: { id: string; label: string }[];   // 14: "CH 01" … "CH 14"
  slots: SlotRect[];                        // from dayLadderLayout(props, frame)

  timing: {
    firstDropFrame: number;   // 189
    dropStride: number;       // 18
    fallDuration: number;     // 22
    seatOvershoot: number;    // 5
  };

  spawn: { y: number; xJitterSeed: number };  // y: -120, deterministic jitter from seed

  overflow: {
    parkY: number;            // 260
    color: string;            // "#E8A33D"
    jitterAmpPx: number;      // 4
    jitterPeriodFrames: number; // 5
    holdFrames: [number, number]; // [510, 540] — chips keep moving through the freeze
  };

  chipStyle: { w: 168; h: 46; radius: 10; fontPx: 30; fill: string; ink: string };
};
```

**Motion.** Each chip *i* has `dropF = f - (firstDropFrame + i*dropStride)`. Target = the *i*-th slot whose `openFrame <= f`, in slot order. If none exists, the chip is in overflow.

- **Fall** — `y = interpolate(dropF, [0, fallDuration], [spawn.y, target.y], {easing: Easing.bezier(0.4, 0.0, 0.2, 1)})`, `x` eases from a seeded lateral offset (±90px) toward `target.x` on a slower curve so the path reads as an arc, not a drop line. Chip rotates `interpolate(dropF,[0,fallDuration],[seedAngle, 0])`, `seedAngle ∈ [-8°, 8°]` from `xJitterSeed`.
- **Seat** — at `dropF === fallDuration`: `scale = 1 + 0.06 * (1 - clamp((dropF - fallDuration)/seatOvershoot))`, plus a 4-frame contact shadow bloom under the chip (`boxShadow` blur 0 → 24 → 12).
- **Overflow** — chip settles at `parkY`, `fill` lerps to `overflow.color` over 8 frames, then `y += jitterAmpPx * Math.sin(2π * f / jitterPeriodFrames)` and `opacity = 0.8 + 0.2*Math.sin(2π * f / 14)` indefinitely until a slot opens.
- **Late seat** — when a split creates a new slot at frame *S*, the overflow chip's fall restarts with `dropF = f - S - delay`, recolours amber → `chipStyle.ink` over 6 frames on contact.

**Reusability note:** `ChipDrop` is deliberately generic (chips + slots + overflow). It is the reusable half of this build and should go into the cookbook registry; `DayLadder` is calendar-specific and registers as an episode-tier component.

### 3.3 Registration
Both register in `remotion-studio/src/cookbook/registry.ts` with `DataShape: "calendar"` (new) for `DayLadder` and `DataShape: "chips"` for `ChipDrop`. `demos.ts` gets a demo prop set for each so the composer can offer them. Run the cookbook sync check after registering — count should go 23 → 25.

---

## 4. Verified before a single frame renders

**Blocking — arithmetic (the video is this number):**

1. Re-run the calendar count on render morning and paste the output into the episode JSON as a comment:
```bash
python3 -c "
from datetime import date,timedelta
s,e=date(2026,8,22),date(2026,9,28)
d=[];x=s
while x<e: d.append(x); x+=timedelta(days=1)
w=[t for t in d if t.weekday()>=5]
print(len(d),'day tiles /',len(w),'weekend survivors')
print([t.strftime('%a %d %b') for t in w])"
```
Expected: `37 day tiles / 12 weekend survivors`. If it disagrees, **the render stops** — do not adjust the picture to keep 12.
2. Both dates must be legible **in the same frame as the count numeral**, at every moment the numeral is on screen (header rail y=150 + count plate y=215 satisfy this). This is what converts 37 and 12 from claims into a sum the viewer can redo.
3. Run the exact pinned one-liner on a **real free account, on a phone, in India**. Confirm it returns (a) a day count, (b) a day-by-day allocation, (c) arithmetic matching the script above. If Claude's number disagrees with the calendar, the render uses the **calendar's** number and VO L7 covers the discrepancy. Screenshot the run into `channels/claude-tricks/assets/ep_timetable/verify/`.
4. Reconcile **14** everywhere — chips array length, `assert.chips`, the split count, the card header string, VO L5 and L6. `assert` must throw at build time, not warn.
5. Rule-chip provenance: confirm in the built frames (not the brief) that the bubble is right-aligned, carries a caret, and lands at f114 with the first fold at f120.

**Blocking — art direction gates (check against rendered frames, not intent):**

6. Grep the component files and the episode JSON for: `remind|reminder|alarm|notify|notification|schedule|sync|calendar app|add to`. Zero hits outside VO L8's "can't remind you". No bell, clock face, alarm, toggle or chime glyph in any frame.
7. Habit-tracker adjacency: render f435 (all 12 seated) side by side with the shipped habit-tracker frames. If a reviewer can mistake one for the other, the seat treatment changes. No green, no ticks, no streak chain — matte fold and contact shadow only.
8. Cut count: exactly **one** hard cut, at f180. Confirm the overflow at f510–f540 renders as a freeze, not a cut.
9. `EXAMPLE` stamp present from f900 and never occluded.
10. Contact-sheet QC across the full 1035 frames at 1 frame/0.5s. **No frozen frame anywhere in f120–f930.** Any dead half-second in 4–8s is a re-cut.
11. Safe-area sweep: nothing load-bearing below y=1590; burned prompt plate on screen 2.30→6.00s (3.7s, clear of the 1.6s floor); the story readable with audio disabled at 2x.

**Operational:**

12. `outro_cta` reads calendar `planned_date`, **not** `--schedule`. Set `planned_date = 2026-08-22` to match the 00:30 IST publish, or the outro promises the wrong day.
13. **Promise-debt check before locking the script:** read what the previously-armed `_style` episode's outro teased for 22 Aug. There is unresolved tease debt. If it promised something other than a timetable, either the tease is honoured first or the outro of this cut acknowledges it.
14. Pin the exact prompt as the first comment manually after publish (the API cannot pin). The full line is given on screen in-video regardless — give, don't promise.
15. Shelve the EchoArc study-timetable variant permanently. Do not ship the Punched Card "Study Plan" within 7 days, and retitle it off the word "Study" when it does ship — same noun, cannibalised CTR.

**Files:** `remotion-studio/src/components/DayLadder.tsx`, `remotion-studio/src/components/ChipDrop.tsx`, `remotion-studio/src/cookbook/registry.ts`, `remotion-studio/src/cookbook/demos.ts`, `channels/claude-tricks/episodes/timetable.v1.json`, `channels/claude-tricks/assets/ep_timetable/`.