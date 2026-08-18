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

## For the factory-app / template session
Surface `voice_track` as a per-channel (and per-template) selector: **ElevenLabs
(paid) · CosyVoice 2 (free · local)**. It only needs to write
`factory_channels.meta.voice_track`; the pipeline side (`vo_render`) is already wired.
Don't call ElevenLabs/CosyVoice directly from the app — go through the field.
