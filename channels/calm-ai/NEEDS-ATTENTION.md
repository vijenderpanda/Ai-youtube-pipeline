# Calm AI — Needs Attention (human steps)
_Scaffolded 2026-08-12. The factory cannot do any of these; each needs VJ at a browser. Ordered by what blocks what._

## 0. 🔴 FIRST — does this channel still exist? (decide before anything else)
The wizard created `calm-ai` in Supabase at **11:01:34 UTC on 2026-08-12** (event `channel_created`) and queued the scaffold job. While that job was running, the **`factory_channels` row, the wizard draft, and the scaffold job row itself were all deleted** from the database. The scaffold on disk is therefore **orphaned** — the app has no channel to attach it to.

Two possible readings, and only VJ knows which:
- **It was deliberate** (wizard test, changed mind) → delete `channels/calm-ai/`, revert the `calm-ai` entries in `scripts/factory_worker.py` and the row in `docs/PRODUCTION-PLAYBOOK.md` §14. Nothing else was touched.
- **It was accidental / a cleanup overreach** → re-run the channel wizard with the same answers (name "Calm AI", key `calm-ai`, accent `#6366F1`), then **uncomment the `calm-ai` entry in `CHANNEL_SEED`** in `scripts/factory_worker.py`. Everything below stays valid.

Until then the `CHANNEL_SEED` entry is deliberately commented out — it runs on every worker start and would otherwise resurrect the deleted channel row without anyone noticing.

## Blocking Ep01 publish
1. **Create the YouTube channel** and claim the handle — try `@calmai` and take the first free fallback (`CHANNEL-SETUP.md` §1). Claim the same string on TikTok / Instagram / X the same day.
2. **OAuth token → `secrets/token_calm-ai.json`.** Run the existing auth flow for the new channel and **include the `youtube.force-ssl` scope in that same consent** — without it the API can never post/moderate comments, and re-consenting later is a separate manual round trip (`yt-engage-scope-and-pin-limits`).
3. **Upload brand assets** (no API path — Studio UI only):
   - icon → `channels/calm-ai/assets/brand/icon.png`
   - banner → `channels/calm-ai/assets/brand/banner.png`
4. **Paste the About description + keywords** from `CHANNEL-SETUP.md` §2–§3.

## Blocking Ep01 production (can run in parallel)
5. **Pick the ElevenLabs voice** — audition ≥3 warm, low, unhurried voices on the same beat at style 0.25 / speed 0.95. Must not be Brian (`already-happening`) or Hrithik (AI Unpacked). Record the winner in `BRAND-BIBLE.md` §8 and `PRODUCTION-BLUEPRINT.md` §3.
6. **Confirm Leonardo/Wan 2.6 access** in the claude-in-chrome session before the first shot batch (the account has been API-token-blocked before — preflight, don't assume).

## Decide before Ep03
7. **Is this channel actually distinct from AI Unpacked?** Watch Ep01–02 back to back against a recent AI Unpacked Short. If a viewer couldn't tell them apart in 3 seconds, change the format or fold the channel in rather than running three AI channels that split the same audience.

## Not blocking
8. Monetisation, end screens, playlists — nothing to do until there are ~10 uploads and a retention read.
