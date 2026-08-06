# Build Plan — "AI Unpacked" (`claude-tricks`)

> Pipeline **B (avatar explainer)**. **NOT Made-for-Kids** → high RPM + affiliate/sponsors. Uploader key `claude-tricks`.
> **Locked decisions (2026-07-31):** fully-synthetic host **Sol** · **electric magenta** accent · **avatar-cutaway over real-screen** format · **~70% tips / ~30% news** · **Shorts-first** · **no paid signups until a free proof-of-concept is approved.**

## Verified facts that shape the build (2026-07-31)
- **HeyGen:** a *custom* avatar (our Sol) **cannot** export transparent/alpha video — only HeyGen's own stock studio avatars can. → Render Sol on a **solid green background** (supported for custom avatars + uploaded audio) and **matte every clip ourselves** (FFmpeg chroma-key, or RVM for hair edges). Uploaded ElevenLabs audio drives lip-sync (`audio_asset_id`). Cheapest = Avatar III Digital Twin $0.017/sec; Photo Avatar ~$0.043–0.05/sec. $5 min top-up, credits valid 12 mo. No 4K.
- **ElevenLabs:** Creator $22/mo (first month $11), ~121k chars/mo, commercial license, `/with-timestamps` endpoint returns **character-level** times → must **group chars → words** for captions.
- **YouTube disclosure:** settable via API — `status.containsSyntheticMedia=true` on `videos.insert`. So automated batch publishing with disclosure works (add the field to `yt_upload.py`).
- **Affiliates at 0 subs:** only **ElevenLabs** + **Writesonic** are open; HeyGen/Descript/Jasper need an audience; Notion closed. Approval ≠ revenue (needs traffic).
- **Shorts:** max length 3 min; ad RPM ~$0.03–0.07/1k; YPP ad-share needs 1,000 subs + 10M Shorts views/90d (fan funding at 500 + 3M/90d).

## Phase 0 — FREE proof-of-concept (NOW, $0)
Goal: let the user judge the *format* before any spend. Content = existing `episodes/01-three-tricks.md`.
- [x] Generate host **Sol** candidates via Leonardo (`assets/character/sol_v1_*.jpg`) → pick + lock canonical Sol.
- [ ] Build **`scripts/assemble_short.py`**: 1080×1920, b-roll base + Sol-corner overlay (chroma-key-ready) + **magenta ASS karaoke captions** + ducked music; per-episode timeline JSON.
- [ ] Mock b-roll: styled "Claude screen" panels (HTML/really-simple) as placeholders for real screen recordings.
- [ ] Voiceover via macOS `say` (placeholder for ElevenLabs).
- [ ] Render **Episode 1 mockup** → `renders/`. Show the user. **Decision gate: approve spend to make the real thing?**

## Phase 1 — Paid pilot (only if approved: ~$27 to start)
- HeyGen $5 top-up + ElevenLabs Creator. Make Sol a **HeyGen Photo Avatar**; pin an ElevenLabs voice.
- Wire the real pipeline: `elevenlabs_vo.py` (with-timestamps) → `heygen_render.py` (green bg + uploaded audio) → chroma-key/RVM matte → `assemble_short.py`.
- Capture **real screen recordings** of each trick (Screen Studio/OBS, tool audio muted, no third-party copyrighted media on screen).
- Create **@AIUnpacked** channel + authorize (`yt_upload.py --channel claude-tricks --auth`). Add `containsSyntheticMedia` + not-MFK to the uploader.
- Ship **3–5 Shorts privately** → test uncanny-valley + retention before committing to daily cadence.

## Phase 2 — Cadence + funnel
- 1–2 quality Shorts/day (batch 5–10 scripts/sitting from an idea backlog; news batched weekly).
- Stand up **newsletter** + lead magnet ("2026 AI Tools Cheat Sheet"); affiliate links on the **About tab**.
- Apply to **ElevenLabs + Writesonic** affiliate programs; build a **$19–39 Gumroad** product.
- Package series into named playlists. Instrument avg-%-viewed + swipe-away per Short; iterate hooks off retention.

## Phase 3 — Monetize deeper (once subs scale)
- 1 **long-form/week** (tutorials convert Shorts subs; real ad RPM). Pursue 500-sub fan-funding → 1,000-sub ad tier.
- Add HeyGen/Jasper affiliates once we have followers; nano-sponsorships; newsletter ad inventory.

## QC gate (mandatory before Studio)
- [ ] Trick is **accurate** + actually demoed on screen — verify keybindings/paths against current Claude Code.
- [ ] Hook lands in ≤1.5s; captions readable + synced; **Sol on-model, zero uncanny frame** (watch full cut).
- [ ] `containsSyntheticMedia = true`; Made-for-Kids = NO; "Not affiliated with Anthropic" note; affiliate + newsletter links.

## Open decisions carried
- Pick final **Sol face** from candidates; confirm **@AIUnpacked** handle availability (+ backup).
- **Spend sign-off** (pending POC review). Confirm launch affiliate programs (ElevenLabs + Writesonic).
