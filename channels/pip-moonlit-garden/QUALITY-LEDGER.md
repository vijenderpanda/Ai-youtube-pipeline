# Lulla's Moonlit Garden — Quality Ledger

> **The apple-to-apple ratchet.** Every new episode on THIS channel must beat the last
> *published* episode from THIS channel on the scored axes below. Same character, same
> world, same format → the only fair comparison. No episode ships until it clears the gate.
>
> Created 2026-08-02. Baseline = the 5-episode launch runway (v1 static pipeline).
> Channel: @LullasMoonlitGarden · `UCKBJGCpvHAYbtUTBWOcmpLQ` · Made-for-Kids.

---

## 1. The current bar (what "last published" means today)

**Pipeline v1 (Pipeline A):** Leonardo *Lucid Origin* stills (seed `1926068932`, face-locked
prompt) → `assemble_video.py` (19 shots × 10s Ken-Burns zoom/pan, xfade 1.2s, `breathe 0.05`,
plain audio fade in/out) → `youtube_upload.py` (schedule + thumbnail + Made-for-Kids).

| # | Title | Video ID | Publishes | Notes |
|---|---|---|---|---|
| 1 | Little Light, Goodnight | `KGh-hbdvrGE` | 31 Jul (LIVE) | first episode — current public bar |
| 2 | Count the Fireflies | `hfwxEYiVYTA` | 3 Aug | full pipeline validated end-to-end |
| 3 | Goodnight Little Garden | `jQBezjCjZUI` | 6 Aug | features supporting cast |
| 4 | Breathe with Lulla | `fBLAEbxPv5s` | 9 Aug | face-lock fix applied |
| 5 | Sleepy Little Colors | `Mjhz4DGTZHU` | 12 Aug | **newest/best-produced — the bar #6 must beat** |

Cadence: +3 days at 16:00 IST. Next NEW episode = **#6 (~15 Aug)**.

---

## 2. The scorecard (rate every episode on these axes)

Legend: ✓✓ strong · ✓ ok · △ weak · ✗ missing. #5 = the standing bar.

| Axis | What "good" looks like | #5 (bar) | Notes |
|---|---|---|---|
| A. Character consistency | On-model Lulla, face-locked, no drift | ✓✓ | Lucid Origin + seed + face-lock negatives |
| B. Palette / brand discipline | Muted periwinkle/amber, dim, no neon | ✓✓ | Bible §4 held |
| C. Calm pacing (on-brand slow) | 10s takes, slow pans, no whip cuts | ✓✓ | This is the differentiator — keep it |
| D. **Visual freshness (anti-templating)** | **<50% frame overlap with any prior ep** | **△** | #5 shares 15/19 frames with #1 |
| E. **Sing-along lyric support** | Soft one-line lyrics, synced, Nunito | **✗** | `word_cards.py` unused; Bible §7 wants echo hooks |
| F. **Branded bookend + goodnight ritual** | Intro sting + belly-dim "Goodnight" outro | **✗** | Only mp3 candidates exist; never rendered/stitched |
| G. Motion richness | ≥1 real moving hero shot (blink/glow) | ✗ | All static Ken Burns |
| H. Audio finish | Clean level, gentle fades | ✓ | No master needed (song, not TTS+bed) |
| I. Thumbnail | Per-song, on-model, readable at grid size | ✓✓ | Face-fixed on #4/#5 |
| J. SEO / metadata / compliance | Title+desc+tags, Made-for-Kids, no cross-link | ✓✓ | Solid |
| K. Format depth | Compilation / playlist / sleep-stream | ✗ | 30–60min compilation not built yet |

**Gate rule:** #6 must be **≥ the bar on every axis and strictly better on ≥1 of D/E/F/G**
(the four that are currently △/✗). No regressions on A/B/C — those are the brand's spine.

---

## 3. The delta queue (ranked — what to spend the next episode's effort on)

1. **D — Fresh scenes (biggest lever, ~free).** ⏳ TODO for #6. Generate ≥6–8 NEW on-model
   Lulla scenes tied to the episode's theme so the shot list is <50% reused. Kills the
   templating / inauthentic-content risk and is the clearest "better than last."
2. **E — Lyric overlays.** ✅ **BUILT & WIRED (2026-08-02).** `scripts/lulla_captions.py`
   renders soft cream one-line captions (rounded font, blurred shadow, alpha fades — NOT the
   punchy Shorts style). Pass `--lyrics <spec.json>` to `publish_song.py`. Spec format:
   `{"lines":[{"text","start","end","pos":"lower","size":64,"fade":0.9}]}`. Time the lines to
   the Suno vocal when producing #6. *Lands in a published video with #6.*
3. **F — Branded bookends.** ✅ **SHIPPED (2026-08-02).** `scripts/make_bookends.py` rendered
   `bookends/intro.mp4` (title over the establishing wide) + `bookends/outro.mp4` (belly-dim
   "Goodnight" + amber heart + Subscribe — the BRAND-BIBLE §6 ritual). `publish_song.py` now
   auto-stitches them via `add_bookends.py` (`--no-bookends` to skip). *Lands with #6.*
4. **G — One hero moving shot (~$0.45).** ⏳ TODO. Leonardo Motion 2.0 on a single Lulla
   blink/glow clip as opener or closer — a premium lift without breaking the calm.
5. **K — First compilation (separate track).** 🟡 **SPEC DONE, BLOCKED ON INPUTS (2026-08-06).**
   Target moved 30min → **60min** ("1 HOUR of Calm" — the duration goes in the title).
   `comp/60min_calm.json` binds all six published songs (each **once, unmodified**) with
   nine Suno instrumental reprises over fresh seed-locked stills; 15 segments, a
   2.5→5.0s crossfade ramp, dim arc, **3601.04 s = 1:00:01**. Join/duration/dim/loudness
   behaviour is **validated end-to-end** (synthetic 15-segment full-scale build: predicted
   3583.04 s vs actual 3583.03 s). ⛔ Cannot render: **Leonardo is out of API tokens** and
   **Suno has no reachable browser session** (no CDP port, no `~/.chrome-suno-cdp` profile,
   extension disconnected). Both are account actions — see `comp/README.md`.
   *This is a derivative, not an episode — it does NOT go on the per-episode log or get
   scored against the anti-templating ceiling (§15 / the Aashiqana hook-cut precedent).
   Its own gate is the binding rule: every song present once, unedited.*

**Pipeline now (v1.1):** render → `lulla_captions` (if `--lyrics`) → `add_bookends` → upload.
So #6 already clears **E + F** vs the #5 bar; add **D** (fresh scenes) and it's a decisive
apple-to-apple win. Validated end-to-end 2026-08-02 (intro 8s + episode + outro 10s, unified
−14 LUFS; captions fade correctly in both windows).

---

## 4. Per-episode log (append one row per new episode — record HOW it beat the bar)

| # | Title | Beat prev on | Held (no regression) | Video ID | Date |
|---|---|---|---|---|---|
| 6 | Time for Bed, Little Light | **D** (8 fresh scenes, 57% fresh) + **E** (19 whisper-timed sing-along lines) + **F** (branded intro + goodnight outro) | A,B,C (even calmer: 12s takes), H,I,J | `B7LUUqPjNYg` | sched 7 Aug |

**Cadence: DAILY as of 2026-08-02** (was +3 days). Each new ep = previous +1 day, 16:00 IST.
⚠️ Daily means #7+ need a fresh gate-passing song **every day** from 8 Aug — the ledger gate now
runs daily, not every 3 days.

**#6 build notes:** song = Suno Pro "Sleepy Little Lullaby" var A (`song06.mp3`, 2:28), lyrics timed
via `faster_whisper` base → `06_lyrics.json`. Final `renders/song06_final.mp4` = 166s (intro 8 +
episode 148 + outro 10). Fresh scenes `s06_*` via `scripts/gen_song06_scenes.sh` (Lucid Origin,
seed 1926068932, face-locked). Thumb = `thumb06_final.jpg` (s06_tuck). **This is the new bar #7
must beat** once it publishes.

---

## 5. Global-worthy findings (candidates for `docs/PRODUCTION-PLAYBOOK.md`)

Discovered here, reusable across ALL channels — promote when confirmed:
- **The apple-to-apple ratchet itself** — a per-channel QUALITY-LEDGER that forces each new
  episode to beat the last published one from the same channel. → propose Playbook §15.
- **Pipeline-A scene-reuse ceiling:** no new episode may reuse >50% of any prior episode's
  frames (anti-templating / July-2025 rule). → Playbook §13.
- **Bookends hygiene:** a designed sting isn't shipped until it's rendered to `intro.mp4`/
  `outro.mp4` AND wired into the publish path. Candidate mp3s ≠ a branded video. → Playbook §9.
- **The asset column in a calendar/ledger is a CLAIM, not a fact.** Five of six SHIPPED rows
  here pointed at `*_breathe.mp4`, which are video-only Ken-Burns passes with **no audio
  stream**; the files actually uploaded are `songNN.mp4` / `song06_final.mp4`. A compilation
  built off those paths would have been ~57 minutes of silence that passed every frame check.
  `ffprobe -select_streams a:0` every input. Fixed in `CONTENT-CALENDAR.csv` 2026-08-06.
  → promoted to Playbook §15.
- **`atempo` upstream of a fixed `atrim` deletes the end of the audio.** Cost: would have cut
  ~15 s — a full closing cadence — off the songs deepest in the compilation, invisibly.
  → promoted to Playbook §15.
