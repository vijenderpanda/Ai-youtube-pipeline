# AI YouTube Channel Network

A human-in-the-loop content factory that **generates, publishes, and schedules** premium videos across multiple YouTube channels from one shared toolchain.

## Layout — global vs. channel
```
Ai-youtube-pipeline/
├── README.md              ← this file (network guidelines)
├── .env                   ← Leonardo API key (gitignored)
├── requirements.txt
├── secrets/               ← GLOBAL YouTube OAuth: client_secret.json + token_<key>.json  (never commit)
├── scripts/               ← GLOBAL shared tools (generate · assemble · motion · cards · thumbnail · upload)
├── docs/                  ← GLOBAL docs (PRODUCTION-PLAYBOOK.md ← READ FIRST, OAUTH-SETUP.md, WORKFLOW.md)
└── channels/
    ├── README.md              ← channel index + status
    ├── pip-moonlit-garden/    ← Pip / Lulla (calm bedtime) — Made-for-Kids
    ├── language-abc/          ← Poly the Parrot (multilingual) — Made-for-Kids
    ├── vehicles/              ← (planned) hyper-active vehicles — Made-for-Kids
    └── claude-tricks/         ← (planned) AI/dev how-to — NOT Made-for-Kids
```
**Rule:** anything global (tools, OAuth, network guidelines) lives at root. Anything **channel-specific** (BRAND-BIBLE, BUILD-PLAN, songs, assets, renders, per-video upload kits) lives inside `channels/<key>/`.

## Doctrine
- **Human-in-the-loop**, never full autopilot (YouTube July-2025 authenticity rule). Automate rendering/metadata/upload; humans own the character, the songs, and a 60-second QC gate.
- **Premium = process:** a signature character + original songs + a locked style, not raw tool output.
- **Budget:** hybrid motion **~$1.35/video** (2–3 Leonardo Motion hero clips + free Ken Burns stills). Suno **Pro** for commercial-licensed songs. (Ep1 of Poly was a one-off ~$4 full-motion flagship.)

## Two pipelines
- **A — Kids music video** (pip · language-abc · vehicles): Claude writes song → **Suno Pro** → **Leonardo** stills (fixed-seed consistency) → **hybrid motion** (Motion 2.0 heroes + Ken Burns) → **word cards** → thumbnail → upload/schedule → multi-language dub fan-out.
- **B — Avatar explainer** (claude-tricks, planned): script → synthetic voice → AI host + screen capture → captions → upload. NOT Made-for-Kids (higher RPM).

## Shared tools (`scripts/`)
| Tool | Purpose |
|---|---|
| `leo_generate.sh` | Leonardo text→image; **lead prompts with FLAT tokens + fixed seed** = character consistency |
| `leo_ref_gen.py` | Leonardo img2img / character-reference gen |
| `leo_motion.py` | Leonardo **Motion 2.0** image→video. `--no-enhance` locks composition. ~$0.45 / 720p clip |
| `assemble_video.py` | Ken Burns + crossfade + audio (stills → video) |
| `assemble_motion.py` | Boomerang-loop short motion clips + crossfade + song |
| `build_final.py` | Overlay timed **word-cards** onto a finished video |
| `word_cards.py` | Render rounded word-cards (flag + word + romanization; Devanagari-capable) |
| `make_thumb_lang.py` · `make_thumbnail.py` · `make_channel_art.py` | Thumbnails / channel art from local assets (no generation) |
| `new_channel.py` | Scaffold a new `channels/<key>/` (dirs + stub brand bible / build plan) |
| **`yt_upload.py`** | **GLOBAL uploader + scheduler** — per-channel OAuth, Made-for-Kids, `--publish-at`, thumbnail, playlist |

## Make a video (any channel)
1. **Song** — Claude writes lyrics → generate on **Suno Pro** → save `channels/<key>/songs/songNN.mp3`.
2. **Scenes** — `leo_generate.sh` (locked style + seed) → keep the on-model stills.
3. **Motion (hybrid)** — `leo_motion.py` on the 2–3 hero scenes; Ken Burns the rest.
4. **Assemble** — `assemble_motion.py` (+ `build_final.py` for word cards).
5. **Thumbnail** — `make_thumb_lang.py` / `make_thumbnail.py` (2 variants for A/B).
6. **QC gate (mandatory before Studio)** — the channel's BUILD-PLAN checklist **plus**: **watch the full cut end-to-end**, and confirm it **opens on the star with energy in the first ~2s — never a dead/empty/no-character establishing shot**. Character on-model throughout, pronunciation verified, audio-safe, Made-for-Kids correct. Nothing gets uploaded/scheduled without this pass.
7. **Publish / schedule** — `yt_upload.py` (below).

## Publish & schedule — `yt_upload.py`
One GCP project (**lulla-pipeline**, YouTube Data API enabled) + `secrets/client_secret.json` for **all** channels. **One token per channel.**

**Authorize a channel once** (signed into *that* channel's Google account in your browser):
```bash
python3 scripts/yt_upload.py --channel <key> --auth
```
**Upload (private draft) or schedule:**
```bash
python3 scripts/yt_upload.py --channel <key> --audience kids \
  --video channels/<key>/renders/epNN_final.mp4 \
  --title "…" --desc-file channels/<key>/docs/epNN_description.txt \
  --tags "a,b,c" --category 27 \
  --thumbnail channels/<key>/assets/thumbnail/thumb_A.jpg \
  --publish-at 2026-08-05T15:00:00Z      # omit → uploads as private draft
```
Channel keys → token files: `lulla`→`token.json`, others→`token_<key>.json`. See `docs/OAUTH-SETUP.md`.
⚠️ Set the OAuth **consent screen to "In production"** so refresh tokens don't expire every 7 days.

## Channels
See `channels/README.md` for the live index and per-channel status.
```
pip-moonlit-garden  A  MFK  pre-launch (5 songs drafted, #1 built)
language-abc        A  MFK  Ep1 "Five Ways to Say Hello" — animated + cards + thumbnail + SEO ready
vehicles            A  MFK  planned
claude-tricks       B  —    planned (fully synthetic)
```
