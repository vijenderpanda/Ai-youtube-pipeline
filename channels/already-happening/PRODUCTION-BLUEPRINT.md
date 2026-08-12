# Already Happening — Production Blueprint (locked from Ep01)
_The canonical, repeatable recipe. Ep02+ = change only the "per-episode variables"; everything else is frozen. Goal: minute-to-minute revisions, not a rebuild each time._

## 0. Canonical builder
**`build_ep01_v3.py` is the template.** Per episode: copy it to `build_ep0N.py` and edit ONLY the four marked spots (§2). Do not touch the opener/bug/end-card/grade/score/encode code — those are the locked brand frame.

## 1. Locked format (never changes)
- **Shorts-only, 9:16, 1080×1920, 30fps, −14 LUFS.** Target **25–40s** (front-loads retention; earn longer later).
- **Spine:** cold-open hook → TODAY anchor → +5yr extrapolation → gut-punch impact → binary button.
- **Tone:** grounded speculation (real anchor + disciplined leap). **Angle alternates** wonder ↔ provocation episode to episode.
- **Signature brand frame (identical every ep):** black typewriter cold-open "THE FUTURE ISN'T COMING", `● ALREADY HAPPENING` top-left bug, running teal-keyword captions, branded end card with SUBSCRIBE/SHARE CTAs, electric-teal `#22D3EE` identity, bed_3 score.

## 2. Per-episode variables (the ONLY things that change)
1. **Topic + script** — 6 beats, punchy AI-Unpacked style (short lines, curiosity gaps). Alternate wonder/provocation vs previous ep.
2. **VO** — `renders/epN/vo/beat{1..6}.wav` (see §3).
3. **6 Seedance shots** — `assets/epN/motion/…mp4` (see §4).
4. In `build_ep0N.py`: `VO` dir, `MOT` dir, the `BEATS` clip filenames, and the `HOT` keyword set. That's it.

⚠️ **Anti-throttle rule (July-2025 inauthentic-content policy):** keep the brand frame consistent but genuinely VARY per ep — topic, all 6 shot visuals, opening shot *type*, script, HOT words, beat rhythm. Never "only slightly different."

## 3. VO recipe (locked)
- `scripts/eleven_vo.py --voice nPczCjzI2devNBz1zQrb --text "<beat>" --out beatN.wav --style 0.32 --speed 1.0`
- Voice = **Brian** (deep, non-robotic — clears the "AI-slop" bar). One wav per beat (drives per-beat timing + captions via the `.words.json` sidecar).
- Total VO ~30–35s; the builder adds a 3.2s cold-open + 2.6s end card → ~41s.

## 4. Motion shot recipe (locked) — see [[leonardo-motion-via-chrome]]
- **Model: Wan 2.6** (Video tab), **9:16, 5s, audio OFF.** **~175 web-tokens/clip** — 10× cheaper than the retired Seedance 2.5 (1752), 3.4× cheaper than Gemini Omni Flash (600). Carries the "Unlimited" badge (may be free on our plan). **Natively outputs Full HD 1080×1920** — pick the "Full HD 1080×1920" dimension so NO builder upscale is needed (still works at HD 720 + lanczos upscale if you want cheaper/faster). Picked 2026-08-12 after a same-prompt 3-way QC bake-off (Wan 2.6 / Gemini Omni Flash / Seedance 2.0 Mini): Wan 2.6 was clean + coherent (stable subject, on-theme panel motion, no distortion) at a fraction of the cost.
  - **Fallback 1 — Gemini Omni Flash (@600):** a dramatic-lit hero shot with push-in/gesture camera; moodier "film" look when a beat wants it.
  - **Fallback 2 — Seedance 2.0 Mini (@960):** rock-solid human identity for a tight face close-up / Start-frame continuity.
  - ❌ **Seedance 2.5 (1752) retired** — too expensive; do not use. Hailuo 2.3 is also "Unlimited"/free but distortion-prone — avoid.
- **Reuse an approved still as the Start frame** (menu: image icon → **Start frame**, NOT "Image Reference") for composition continuity; OR text-to-video for a new concept beat (e.g. Ep01's phone→pod).
- Prompt each shot for clean, coherent motion ("coherent stable shapes", explicit camera move). Set the prompt with the **form_input tool** (the field won't take focus after a frame swap).
- Download free via `scripts/leo_fetch_videos.py <dir> <n>` (API GET, no tokens/screenshots).
- Fire all 6 back-to-back (concurrent), poll from the terminal.

## 5. Locked build params (in build_ep01_v3.py — do not change)
- Colors: `TEAL=(34,211,238)`. Fonts: Arial Bold. Timing: `COLD=3.2, TAIL=GAP=0.5`.
- **Cold-open:** pure black + faint teal glow-pool + grain + vignette; lone teal cursor pulse → auto-fit type-out of "THE FUTURE ISN'T COMING" with glow → teal underline draws → blinking-cursor hold → hard cut.
- **Captions:** running word-by-word, ≤5 words/line, keyword-colored (`HOT` set = numbers + punchy nouns for that topic), dark pill @ y≈0.70.
- **Grade:** `eq=contrast=1.05:saturation=1.08, noise=alls=3, vignette=PI/6`.
- **Score:** `../claude-tricks/assets/music/bed_3.mp3` (calmest/most cinematic bed; distinct from AI Unpacked's active bed), start `-ss 20`, `highpass=90 + 2.2kHz −3dB scoop`, `−13dB` under VO, `loudnorm I=-14`.
- **Brand bug:** top-left `● ALREADY HAPPENING`, on beats only (not opener/end card).
- **End card:** ALREADY / HAPPENING wordmark + tagline + SUBSCRIBE FOR MORE (filled) / SHARE THIS (outline) + "new drops from the near future, weekly".
- **Delivery encode:** `crf 21, preset slow, maxrate 12M, faststart, aac 192k, ar 48000` → `epN_v3_web.mp4`.

## 6. Fact-check gate (MANDATORY — the channel's whole wedge)
Every on-screen number/claim needs a **dated primary source** logged in `episodes/epN.receipts.md`. Keep stated figures **conservative** (Ep01 used 50k/week vs Waymo's larger reported numbers). One wrong stat detonates the "this is REAL" brand.

## 7. Upload metadata (per ep)
- **Title formula:** `[searchable keyword first 3–5 words] + [provocation/curiosity] + [stake/timeframe]`, 40–55 chars, sentence case, keyword front-loaded. Mostly provocation titles; ~1-in-3 a question title for search.
- **Description + hashtags:** template in `CHANNEL-SETUP.md`. 3–5 hashtags led by `#Shorts`.
- **Schedule:** Tue / Wed / Thu @ **2:00 PM ET** (18:00 UTC / 11:30 PM IST) — global, fixed.
- **Publish path:** factory (draft in `factory_posts` → arm on dashboard → worker uploads via `yt_upload.py`) with `--audience general --synthetic` (AI-generated footage → disclose). Channel wired in `factory_worker.py` (`UPLOAD_DEFAULTS`/`CHANNEL_SEED`/`DISPLAY_MAP`), token `secrets/token_already-happening.json`.

## 8. Ep02 fast path (the whole loop)
1. Lock topic + title (provocation, ≠ transport). Write 6-beat script; fact-check anchor.
2. `eleven_vo.py` ×6 → `renders/ep02/vo/`.
3. Seedance ×6 (Chrome) → `assets/ep02/motion/`; fetch.
4. `cp build_ep01_v3.py build_ep02.py`; set VO/MOT dirs, BEATS filenames, HOT words.
5. Render → frame-check → web encode → deliver.
6. Metadata from §7 → draft → VJ arms → publish.
