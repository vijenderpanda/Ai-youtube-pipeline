# Bookends — reusable intro / outro stitching

A **bookend** is a short, reusable clip that plays before (intro) or after (outro) every
episode on a channel — a branded sting, a "subscribe" outro card, a musical logo, etc.
`scripts/add_bookends.py` prepends the intro and appends the outro onto a finished episode
in one pass, re-encoding everything to a single uniform spec so the joins are seamless.

## Per-channel convention

```
channels/<slug>/bookends/
├── intro.mp4     # played BEFORE the episode   (optional)
└── outro.mp4     # played AFTER the episode     (optional)
```

- Both files are **optional**. A missing intro or outro is skipped with a warning — the
  stitcher never crashes. If **both** are missing, the episode is stream-copied through
  unchanged.
- Bookends are rendered **separately, once per channel**, and reused across every episode.
- They may be **any** resolution / fps / codec / sample-rate. `add_bookends.py` detects the
  **episode's** spec and conforms the bookends to it (see below), so you never have to match
  them by hand.

Channel notes:
| Channel (`slug`) | Orientation | Bookend style |
|---|---|---|
| `pip-moonlit-garden` | 16:9 | calm musical intro sting + gentle "goodnight / subscribe" outro |
| `language-abc` | 16:9 | character logo intro + outro card |
| `vehicles` | 16:9 | energetic engine-rev intro + outro card |
| `claude-tricks` | **9:16 Shorts** | **no musical intro** — use `--intro-none` (or a silent title card) + short outro |

## What the stitcher guarantees (uniform target)

`add_bookends.py` **probes the `--episode`** for width, height and fps, then re-encodes
**every** segment (intro, episode, outro) to that uniform target:

- **Resolution** = episode's WxH. Mismatched bookends are scaled to fit **without stretching**
  and letterbox-padded (so a 1:1 or 720p bookend still lands clean on a 1920x1080 episode).
- **fps** = episode's frame rate (e.g. 30). `9:16` Shorts episodes keep their own vertical size.
- **Pixel format** = `yuv420p` (also fixes `yuvj420p` full-range sources).
- **Audio** = AAC, **48000 Hz stereo**, 192k.
- **Loudness** = each segment is normalised to **-14 LUFS integrated** (EBU R128 `loudnorm`,
  measured two-pass) so the bookends and the episode sit at exactly equal level.
- **Clean joins** = segments are joined with the **concat filter** (not the demuxer), which
  decodes and reclocks every stream in-graph — no audio pops, no A/V drift.

Because the target is derived from the episode, the **same** command works for 16:9 channels
and 9:16 `claude-tricks` Shorts with no extra flags.

## 1. Render an intro / outro clip (once per channel)

Any tool that produces an mp4 works. The house tool is `scripts/assemble_video.py`, the same
Ken-Burns + crossfade + audio assembler used for episodes — just point it at a short shots
list and a short Suno sting:

```bash
# Write a tiny shots list, e.g. channels/vehicles/bookends/intro_shots.json:
#   [{"img": "channels/vehicles/assets/scenes/logo.jpg", "dur": 3, "motion": "zoom_in"}]

python3 scripts/assemble_video.py \
  --shots channels/vehicles/bookends/intro_shots.json \
  --audio channels/vehicles/bookends/intro_sting.mp3 \
  --out   channels/vehicles/bookends/intro.mp4
```

Notes:
- Keep bookends short (~2–5 s). The intro sting/song is produced on **Suno via Chrome** like
  any other track (see `docs/WORKFLOW.md`), then dropped into `channels/<slug>/bookends/`.
- The bookend's own resolution/fps/codec does **not** need to match anything —
  `add_bookends.py` normalises it. `assemble_video.py` happens to emit 1920x1080@30 / yuv420p /
  AAC, which is already ideal for the 16:9 channels.
- A **silent** bookend is fine too (e.g. a title card): the stitcher fills matched-length
  silence so the concat stays balanced.
- For `claude-tricks` (9:16, no musical intro): either render a silent vertical title card, or
  skip the intro entirely with `--intro-none`.

## 2. Stitch bookends onto an episode

```bash
python3 scripts/add_bookends.py \
  --channel vehicles \
  --episode channels/vehicles/renders/ep01_final.mp4 \
  --out     channels/vehicles/renders/ep01_bookended.mp4
```

By default it uses `channels/<slug>/bookends/intro.mp4` and `.../outro.mp4`.

Flags:
| Flag | Purpose |
|---|---|
| `--channel <slug>` | channel slug; resolves the default `bookends/` dir |
| `--episode <mp4>` | finished episode; **defines the target spec** |
| `--out <mp4>` | output file |
| `--intro <mp4>` | override the intro path |
| `--outro <mp4>` | override the outro path |
| `--intro-none` | force-skip the intro (e.g. `claude-tricks`) |
| `--outro-none` | force-skip the outro |
| `--crf <n>` | libx264 CRF for the final encode (default 19) |
| `--preset <p>` | libx264 preset (default `medium`) |

Exit code: `add_bookends.py` surfaces ffmpeg's **real** exit code on failure (never masked
behind a pipe), so it composes safely in scripts.

## 3. Where it plugs into the pipeline

Bookending is the **last render step, right before upload** — after the episode is fully
finished (motion + word-cards + audio), before it goes to YouTube.

### Music channels (`publish_song.py` → `youtube_upload.py`)

`publish_song.py` today does *render → upload* in one shot. To insert bookends, render first
(`--no-upload`), stitch, then upload the bookended file:

```bash
# 1) render the episode only
python3 scripts/publish_song.py --no-upload \
  --audio channels/pip-moonlit-garden/songs/song02.mp3 \
  --shots channels/pip-moonlit-garden/songs/02_shots.json \
  --title x --out channels/pip-moonlit-garden/renders/song02.mp4

# 2) add the reusable intro + outro
python3 scripts/add_bookends.py --channel pip-moonlit-garden \
  --episode channels/pip-moonlit-garden/renders/song02.mp4 \
  --out     channels/pip-moonlit-garden/renders/song02_bookended.mp4

# 3) upload the bookended cut
python3 scripts/youtube_upload.py \
  --file channels/pip-moonlit-garden/renders/song02_bookended.mp4 \
  --title "…" --desc-file … --tags "…" --category 10 \
  --thumbnail … --publish-at "2026-08-07T16:00:00+05:30"
```

(If you prefer one command, `publish_song.py` could grow an optional `--bookends`/`--no-bookends`
step between its render and upload calls — not wired in yet, kept additive.)

### Card/learning channels (`build_final.py` → `yt_upload.py`)

`build_final.py` overlays word-cards to produce `channels/<slug>/renders/epNN_final.mp4`. Bookend
that, then upload with the network uploader:

```bash
# after build_final.py has produced epNN_final.mp4
python3 scripts/add_bookends.py --channel language-abc \
  --episode channels/language-abc/renders/ep01_final.mp4 \
  --out     channels/language-abc/renders/ep01_bookended.mp4

python3 scripts/yt_upload.py --channel poly --audience kids \
  --video channels/language-abc/renders/ep01_bookended.mp4 \
  --title "…" --desc-file … --tags "…" --category 27 --thumbnail …
```

### Shorts (`claude-tricks`, 9:16)

Same command; skip the musical intro:

```bash
python3 scripts/add_bookends.py --channel claude-tricks \
  --episode channels/claude-tricks/renders/epNN_final.mp4 \
  --intro-none \
  --out     channels/claude-tricks/renders/epNN_bookended.mp4
```

## QC reminder

The network doctrine (`README.md`) requires the cut to **open on the star with energy in the
first ~2 s**. A slow/branded intro can violate that — keep intros short and lively, and always
re-watch the bookended file end-to-end before scheduling.
