# AI YouTube Channel Network

This repo began as a single channel (**Pip / calm bedtime**) and is now a **multi-channel content network** built on one shared, human-in-the-loop factory.

## Doctrine (every channel obeys this)
- **Human-in-the-loop content factory**, never full autopilot — YouTube's July-2025 "inauthentic content" rule demonetizes mass-produced slop.
- Automate rendering / dubbing / metadata / upload / scheduling. Humans own the **character, the songs/scripts, and a 60-second QC gate**. That gate is the anti-slop moat.
- **Lean spend:** reuse Suno Pro + Leonardo + free tools. Pay for a new tool only after a channel proves out. Target ~$15–30/mo across the whole network.

## Two production pipelines
- **Pipeline A — Kids music video** (Made-for-Kids, RPM ~$0.30–1):
  Claude writes song → **Suno Pro** (commercial rights) → **Leonardo** stills (fixed-seed consistency) → **Leonardo Motion 2.0** clips (`scripts/leo_motion.py`, `--no-enhance`) → text overlay → **FFmpeg** assembly → QC → thumbnail → SEO → upload → **multi-language dub fan-out**.
  Powers: Pip, Language/ABC, Vehicles.

### Network standards (locked, apply to every Pipeline-A channel)
1. **Motion standard:** every episode shot is animated with Leonardo Motion 2.0 (`leo_motion.py --no-enhance` to preserve composition) from a **clean still (no text)**. Ken Burns is the fallback only if motion fails QC.
2. **Text standard:** on-screen words/numbers/letters are overlaid as crisp brand-typography PNGs **after** motion (static text over moving scene). Never bake text before AI motion (it warps), never use floating card panels (rejected — looks bolted-on).
3. **Sync standard:** shot cuts and text-overlay windows are derived from **Whisper word-level timestamps of the final song** (`faster-whisper`, then `scripts/assemble_synced.py --plan <plan.json>`). Never fixed per-shot durations — audio races ahead of scenes otherwise. The plan json holds absolute `at:`/`st:`/`en:` seconds taken from the transcript.
4. **Thumbnail standard:** thumbnails must use **scene-quality Leonardo art** (same locked seed + style tokens as episode scenes, generated 16:9 with text space) + brand-typography text overlay. No flat cutout composites — thumbnail quality must match scene quality.
- **Pipeline B — Avatar explainer** *(planned, NEW)* — NOT Made-for-Kids, RPM ~$8–25 + affiliate/sponsors:
  script → **synthetic voice (TTS)** → **AI character host + real screen capture** → captions/edit → SEO → upload.
  Powers: Claude-tricks.

## Channels
| Location | Channel (working name) | Lane | Pipeline | MFK | Status |
|---|---|---|---|---|---|
| repo root (migrate later) | **Pip's Moonlit Garden** | Calm bedtime | A | Yes | 5 songs drafted, #1 built — **pre-launch** |
| `channels/language-abc/` | **Poly the Parrot** | Multilingual early-learning | A | Yes | **Scaffolding (now)** |
| `channels/vehicles/` *(todo)* | TBD | Hyper-active vehicles | A + energetic-motion module | Yes | Planned |
| `channels/claude-tricks/` | **AI Unpacked** | AI tips + news | B (fully synthetic) | **No** | **Building — free POC (host "Sol" + Shorts assembler)** |

## Repo layout
- **Shared scripts** live at repo-root `scripts/` — they take explicit file-path args, so they are already channel-agnostic (point `--out` / outdir at any channel).
- **Per-channel content** lives under `channels/<name>/`: `BRAND-BIBLE.md`, `BUILD-PLAN.md`, `songs/`, `assets/`, `renders/`, `docs/`.
- `.env` (Leonardo key) stays at repo root; every channel reuses it.

> **Pip migration deferred on purpose.** Pip's files stay at repo root until its first videos are live, so we don't break the imminent first upload's relative paths. Migrate into `channels/pip-moonlit-garden/` afterward.

## Agreed build order
1. Get **Pip** live. → 2. **Language/ABC** (this scaffold). → 3. **Claude-tricks**. → 4. **Vehicles** (hardest for AI; do last).

*Living document — update the status column as channels ship.*
