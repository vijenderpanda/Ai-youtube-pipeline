# One Desk — the factory app design

The locked design for `webapp/`. This file exists because the previous mockups
never landed: each one lived in a chat, the next session re-derived it slightly
differently, and the app ended up "in bits and pieces". **This is the reference.
When the app and this file disagree, one of them is a bug — decide which, then
fix it. Do not let them drift.**

---

## Why the app was redesigned

The old app had ten destinations and no direction. The complaint that started
this: *"right now I feel the app is cluttered and directionless... we have
created multiple mockups in the past but nothing actually landed completely,
always in bits and pieces."*

Three specific failures drove the rebuild:

1. **Rooms, not work.** Nav was organised by system concept (Studio, Library,
   Activity, Assets, Workers) rather than by what the owner is trying to do. A
   single episode's life was smeared across six screens.
2. **The app asserted things it had not checked.** Today counted still-rendering
   pieces as needing attention; the ledger said "passes at finalize" without
   having measured anything; a button offered an upload that would dead-end.
3. **Verdicts before evidence.** Analytics let a two-day-old Short be called a
   flop, which is noise, not signal.

---

## The six destinations

Everything the owner does is one of six things. There are no other top-level
rooms, and a seventh is a design failure until proven otherwise.

| Destination | The question it answers | Route |
|---|---|---|
| **Today** | What needs me right now? | `/` |
| **Make** | I want a new piece for a channel. | `/make` |
| **Plan** | What is going out, and when? | `/plan` |
| **Piece** | Move this one episode forward. | `/piece/:calendarId` |
| **Looks** | What does the channel look like? | `/looks` |
| **Scoreboard** | How did the published work do? | `/scoreboard` |
| **Machines** | Are the boxes healthy and what is quota doing? | `/machines` |

**Retire by redirect, never by deletion.** Legacy routes still resolve so old
links and cross-links keep working: `/analytics` → `/scoreboard` (the old charts
survive at `/analytics/legacy`), `/calendar` → `/plan` (the month grid survives
at `/calendar/legacy`), `/studio/templates` → `/looks`. `/overview`
keeps the old dashboard. `/studio/templates/:key` is deliberately **not**
redirected — it is the sequence designer that Looks links into.

**A room is only retired once its unique signal has somewhere to live.** Before
Activity left the nav, its irreplaceable signal — background work that failed and
belongs to no piece — moved into Today's health row. Apply this test before
removing anything.

---

## The journey

The spine is one loop, and every destination is a station on it.

```
Make  →  Piece (plan → produce → review → schedule)  →  Scoreboard
  ↑                        │                                │
  └──── what worked ───────┴──── Looks (the house style) ───┘
```

1. **Make** — paste the freshest numbers from YouTube, pick a channel and which
   machines may work, press the one button. Ideas come back ranked; choosing one
   creates a Piece.
2. **Piece** — the whole life of one episode, on one screen, as a gate rail.
3. **Scoreboard** — what actually happened, on a clock that refuses to judge too
   early.
4. **Looks** — the cast, the frames, the composition. Locked versions are
   immutable; editing one opens a draft.

### The gate rail

A Piece shows five gates in order — **PLAN → PRODUCE → REVIEW → SCHEDULE →
VERDICT** — and exactly one is current. The current gate owns the screen's single
primary button. Passed gates collapse to a line. Future gates are visible but
inert, so the owner can always see what is coming without being able to skip.

- **PLAN is the only money gate.** Producing spends real API budget; nothing
  before it does. That is why the decision is deliberate and why the gate shows
  what is about to be built before it is built.
- **The rail is bidirectional.** Approving a cut moves REVIEW → SCHEDULE;
  un-approving moves it back. A gate that can only advance will strand work.
- **A gate must pre-flight its own button.** If SCHEDULE cannot succeed — no
  produce job carrying an episode key — it says so instead of offering a button
  that dead-ends.

### Verdict lockout

The VERDICT gate is **locked until the piece is old enough to judge**, and the
clock depends on how the piece is being found:

- Traffic that is mostly **Shorts feed**: 7 days, callable from day 3.
- Traffic that is mostly **search / suggested**: 90 days, callable from day 30.
- **Below 20 views there is not enough traffic to read the mix at all** — the
  channel's format clock applies instead. Without this floor a four-view video
  looks like a search video, gets a 90-day clock, and every flop stays buried.

Age is measured from **public-since** — `min(posts.publish_at, first_date)` —
never from `first_date` alone, which is when tracking started and makes
three-week-old videos look newborn.

Verdicts are graded against **the channel's own percentiles**, not absolute
numbers, and **verdicts only ever upgrade**. A piece that was called quiet and
then takes off becomes a hit; a hit never silently becomes a flop. When a piece
is a flop, the app says **which kind** — it did not get shown, or it got shown
and not clicked, or it got clicked and not watched — because those have different
fixes.

---

## The rules

These are not style preferences. A violation is a bug.

**Scope.** Every rebuilt page's root is `className="piece <name>"`. `.piece` is
the selector the frozen rules hang off — `.piece .pc-card`, `.piece .pc-eyebrow`.
A page that omits it renders unstyled but not *broken*, which is exactly how this
language erodes unnoticed. Plan shipped that way for one deploy.

**Language.** New surfaces use `.pc-card` (flat `--input-bg`, hairline border)
and `.pc-eyebrow` (mono, muted, `.14em` tracking). **Never** the old `.card` or
`.field-label` — those belong to the retired app. Type is Bricolage Grotesque
with JetBrains Mono for data, both loaded in `webapp/index.html`.

**Tokens.** The app defines `--success`, `--danger`, `--warn`. **`--ok` and
`--dead` DO NOT EXIST.** Using them fails silently and renders white on white —
this shipped once across thirteen call sites before anyone saw it. Before using a
custom property, confirm it is defined in `styles.css`.

**One primary button per screen.** If two things look equally like the next
action, neither is.

**Plain language.** The owner is not a visitor to his own system, but the screen
still says *"nothing is awake to send the wake signal"*, not
*"no worker with last_seen < 5m"*. Job types, table names, status enums and raw
ids do not appear in user-facing copy.

**Every number is captioned.** A figure states what it measures and over what
window. `$7.55` is meaningless; `$7.55 spent in this 5h window · 3 jobs · resets
12:40 IST` is a fact.

**Measure the thing that matters, not its proxy.** A disk warning keyed to
percent-used cried wolf at 89% on a 460 GB disk with 51 GB free. What stops a
render is gigabytes. Pick the unit the failure actually happens in.

**Never claim state you have not verified.** This is the cardinal rule. The app
may say "not measured yet". It may not say "passes".

---

## What the design refuses to do

- **No AI challenger loop.** Retired 2026-08-20. The strategist used to write a
  row proposing to replace an already-planned piece, and the app asked you to
  decide within 72 hours of publish. It is gone at the source: the prompt no
  longer runs a challenge pass and the worker refuses a stray one, because a
  generator still writing rows nothing renders is the bits-and-pieces failure in
  miniature.
- **No overnight proposer.** `claude -p` quota is per *account*, not per machine —
  all three workers capped within four seconds on 2026-08-18. Proposing is
  on-demand, from Make, when the owner wants a piece.
- **No dollar figure on the plan gate.** There is no cost oracle. A wrong number
  would be worse than no number, so the gate shows engine categories and the
  free-local toggle instead.
- **Adding a machine does not add quota.** Machines states this outright, because
  the instinct when jobs fail on quota is to add a box, and concurrency is what
  actually spends it.

---

## Open, and honest about it

- The gate ledger shows thresholds and "at finalize" rather than measured
  numbers. Until `finalize_episode.py` stamps its measurements somewhere the app
  can read, the ledger is a promise, not a report.
- The PLAN gate shows per-beat detail only when a look has designed scenes;
  host and recording beats cannot be sequence blocks, so a plan built from
  classic beats has nothing to preview.
- Cadence has no single owner — `channels/<key>/channel.json` in git and the
  database both describe it. Pick one before adding a third.

**There are seven channels, not six.** A hard-coded count is how the old Assets
page died.
