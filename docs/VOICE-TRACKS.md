# Voice tracks — ElevenLabs (paid) ↔ CosyVoice 2 (free / local)

Single contract shared across sessions (pipeline, factory app, template/asset library)
so the "voice track" a template/channel picks maps to one mechanism. Established
2026-08-18 after CosyVoice 2 was chosen as the closest free-local match to ElevenLabs
for the Sol voice.

## The `voice_track` field
Per **channel** (and overridable per **template**). Values:

| value | backend | cost | where it runs |
|---|---|---|---|
| `elevenlabs` (default) | ElevenLabs API (`scripts/eleven_vo.py`) | paid (~$22/mo) | Mac, synchronous |
| `cosyvoice2` | CosyVoice 2 zero-shot on the RTX 3060 worker | **free** | `DESKTOP-DEIR7RS`, dispatched job |

Store on `factory_channels.meta.voice_track` (template may override via
`factory_templates.meta.voice_track`). Absent = `elevenlabs`.

## Per-channel voice config (both tracks)
Kept together so switching tracks needs no other change. For **claude-tricks / Sol**:
- `elevenlabs`: voice_id `ZZ5OIPIzxVJswEhc0UXt` (Hrithik), style 0.4
- `cosyvoice2`: reference clip `factory-renders/gpu-refs/sol_ref_energetic.wav`
  + its exact transcript (zero-shot needs a ref + transcript, no training)

Registry lives in `scripts/vo_render.py::VOICE_TRACKS` (extend per channel).

## The one entrypoint: `scripts/vo_render.py`
Everything that needs VO calls this router, never ElevenLabs directly:
```
python scripts/vo_render.py --channel claude-tricks --text "..." --out vo.wav [--track cosyvoice2]
```
- `elevenlabs` → `eleven_vo.synth` (unchanged behaviour).
- `cosyvoice2` → enqueues a pinned `shell_script` job (`deploy/gpu/cv2_clone.ps1`,
  `target_worker=DESKTOP-DEIR7RS`) with the channel's ref + text, polls, downloads the
  result. Requires the worker up (CosyVoice 2 already installed at
  `C:\Users\panda\AppData\Local\cv`).

## Switching a channel to the free track ("try the free track")
1. App/template sets `factory_channels.meta.voice_track = 'cosyvoice2'`.
2. Nothing else changes — `vo_render` routes automatically.
3. Coordinate the flip (this is the "when we try the free track" moment): confirm the
   worker is up, do one test render, compare, then flip.

## Image track (same pattern) — `image_track`
Per-channel `factory_channels.meta.image_track` (template-overridable):

| value | backend | cost | where |
|---|---|---|---|
| `leonardo` (default) | Leonardo (existing `leo_chrome.py` / generation MCP) | paid | Mac/Chrome |
| `flux_local` | **FLUX.1-schnell** (GGUF) in ComfyUI on the RTX 3060 worker | **free** | `DESKTOP-DEIR7RS` |

Entrypoint: `scripts/img_render.py --channel X --prompt "..." --out img.png [--track flux_local]`.
`flux_local` dispatches a pinned `deploy/gpu/flux_gen.ps1` job (ComfyUI already installed
at `%LOCALAPPDATA%\comfy`) and downloads the PNG. Caveat: FLUX-schnell can't render
legible **text-in-image** — for text-heavy thumbnails keep `leonardo` or (future) add a
Qwen-Image track. Everything else (hooks, b-roll, character stills) is thumbnail-grade.

## Avatar track (same pattern) — `avatar_track`
Router: **`scripts/avatar_render.py`** (`--channel --audio vo.wav --out host.mp4 [--image
frame.png] [--track ...]`). **Source of truth today = the router's in-file `AVATAR_TRACKS`
registry** (same as `vo_render`/`img_render` — the DB has no `meta` column; the per-channel
DB field + template-UI selector is the shared TODO for all three tracks). The value is also
stashed in `factory_channels.brand.avatar_track` (`= echomimic_local`, `avatar_fallback =
heygen`) so the template session can surface it.

| value | backend | cost | where |
|---|---|---|---|
| `echomimic_local` (claude-tricks default) | **EchoMimic V1** audio-driven portrait on the RTX 3060 | **free** | `DESKTOP-DEIR7RS` |
| `heygen` | HeyGen talking-photo (`heygen_avatar.py`) | paid | cloud |

**`echomimic_local` is the free quality track (VJ-approved 2026-08-19).** A host portrait +
a VO wav → `deploy/gpu/echomimic_gen.ps1` (`-SrcUrl -AudioUrl`) → 512×512 talking head with
whole-face diffusion (natural head/eye motion, **no** mouth-inpaint seam). It **always
dispatches to the worker** (pinned `shell_script`, `target_worker=DESKTOP-DEIR7RS`) and on
**any** failure (job failed/timeout/download) **automatically falls back to `heygen`** — so a
worker hiccup never breaks a build. Pass `--no-fallback` to fail hard instead. Output is
512×512; upscale (lanczos/AI) or composite onto the 1080p brand frame for a Short.

The router also uploads the local image/audio to `gpu-inputs/` to hand the worker public URLs.
Per-channel config (host portrait storage path + heygen fallback `talking_photo_id`) lives in
`avatar_render.py::AVATAR_TRACKS`.

**Superseded:** `musetalk_local` (MuseTalk 1.5) + the LivePortrait-motion combo — rejected on
quality (mouth-inpaint blur + looping driving clip); EchoMimic replaces them. Scripts remain
on the worker but are no longer the avatar track.

## For the factory-app / template session
Surface **three** per-channel (and per-template) selectors:
- `voice_track`: **ElevenLabs (paid) · CosyVoice 2 (free · local)**
- `image_track`: **Leonardo (paid) · FLUX-schnell (free · local)**
- `avatar_track`: **HeyGen (paid) · MuseTalk (free · local)**

Each only writes `factory_channels.meta.{voice_track,image_track,avatar_track}`; the pipeline
(`vo_render` / `img_render`) is already wired to honor them. Don't call the providers
directly from the app — go through the fields so all sessions stay in sync.
