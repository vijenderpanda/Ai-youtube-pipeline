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

## For the factory-app / template session
Surface **two** per-channel (and per-template) selectors:
- `voice_track`: **ElevenLabs (paid) · CosyVoice 2 (free · local)**
- `image_track`: **Leonardo (paid) · FLUX-schnell (free · local)**

Each only writes `factory_channels.meta.{voice_track,image_track}`; the pipeline
(`vo_render` / `img_render`) is already wired to honor them. Don't call the providers
directly from the app — go through the fields so all sessions stay in sync.
