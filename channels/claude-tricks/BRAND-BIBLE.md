# Brand Bible — "AI Unpacked"

> **Public channel name: AI Unpacked.** Internal/uploader key stays `claude-tricks` (keeps existing OAuth/token wiring). Verify handle **@AIUnpacked** on YouTube + TikTok + a newsletter domain; backups: @AIUnpackedHQ, @UnpackedAI.
> Audience: **general + pro adults — NOT Made-for-Kids** → high RPM + affiliate. **Fully synthetic host "Sol."**
> One line: **No hype. Just what actually works.** — short, tested AI tips & AI news with real on-screen proof, hosted by an AI guide.
>
> _(Supersedes the earlier "Prompt Pilot" working name. Pipeline B — avatar explainer.)_

---

## 1. The wedge — why this is the money channel
- AI/dev tips is a **top-RPM niche (~$8–25 long-form RPM vs $0.30–1 for kids)** — one tech view ≈ 10–30× a kids view. Real upside is **beyond ads:** affiliate (AI tools), sponsorships, newsletter/product.
- **Counter-positioning:** be the **calm, proof-driven, Claude-native** channel in a sea of hype-toned, ChatGPT-centric, faceless AI slop. Three moats:
  1. Under-served **Claude/Anthropic power-user** content (Projects, MCP, sub-agents, artifacts, Claude Code) vs the ChatGPT flood.
  2. Every tip is a **real workflow we actually ran** — an authenticity moat slop farms can't fake.
  3. Structural signature: **"shown working on a real screen."** The proof pane IS the anti-slop credential.
- **We teach people to use AI, so our own output must be flawless.** The polish is the brand argument.

## 2. ⚠️ Trademark / brand safety
- Content **about** Claude/Anthropic = **nominative fair use** (fine).
- **Do NOT** imply official Anthropic endorsement/partnership, misuse Anthropic logos, or brand the channel "Claude [X]". (This is exactly why the name is "AI Unpacked," not a Claude-name.)
- "Claude" / "Claude Code" / "Anthropic" live in **titles, descriptions, tags** (fair-use discovery), never the channel identity.
- Add a light **"Not affiliated with Anthropic — just sharing what works"** line in the channel + descriptions.

## 3. The host — "Sol" (fully synthetic)
- **Sol** = a named, consistent **AI guide**: a trusted **senior operator, not a hype-man**. Measured, credible, quietly enthusiastic — the person a busy pro trusts to have already tested the thing.
- **Not a real person.** One locked look (wardrobe / lighting / framing) reused across every video so identity never drifts. Generated + locked with a fixed seed (`assets/character/`), later turned into a **HeyGen Photo Avatar** for lip-synced cutaways.
- **Role:** appears in **~1–2s cutaways** (2–4 per Short) plus the hook and recap. Always paired with the **real-screen proof pane** to offset the AI-avatar trust penalty. The screen recording is the main content; Sol is the trust device.
- **Voice (LOCKED 2026-08-01):** ElevenLabs **"Hrithik — Charismatic Gen Z Male"**, `voice_id ZZ5OIPIzxVJswEhc0UXt`, **style 0.4** (was 0.5 in early drafts; playbook §17 locked this to 0.4 for sentence-break comprehension) — energetic Indian-English, Vaibhav-Sisinty-style delivery. Synthesize via `scripts/eleven_vo.py` `/with-timestamps` (real word-synced captions). Kokoro `am_michael` = free fallback only.
- **Upgrade path — Video Avatar (photo → video, when ready):** record **~2 min of natural talking footage** at the desk mic — good light, locked framing, hands in frame, keep talking and gesturing naturally the whole take. Requires the **HeyGen Creator plan** (do not buy until the POC earns it). Unlike the current still-photo avatar, a video avatar **inherits the real hand gestures and micro-movements** from the footage — the energetic talking-hands look of **@vaibhavsisinty** Shorts — which kills the static talking-photo tell in cutaways. Drop-in swap: `scripts/heygen_avatar.py` already renders via v3 avatar mode (`POST /v3/videos`), so replacing the cached photo-avatar id with the new video-avatar id upgrades every render with no pipeline changes.

## 4. Format (per Short — the signature)
1080×1920, **25–40s** (Shorts cap = 3 min), cold-open, **no intro sting**, three beats:
- **HOOK (0–1.5s):** full-frame bold problem/promise + the weak output already on screen. Value stated verbally AND on-screen in frame 1. No "hey guys."
- **BODY (proof pane):** Sol in the corner (1–2s cutaways, cut on motion) over a **real screen recording** of the exact steps producing a real result. ONE idea only. Pattern-interrupt every few seconds.
- **PAYOFF:** improved result on screen + one-line **"why it works"** insight (the anti-slop credential) + soft CTA → "link in my profile." Loop the closing line back to the hook for replays.
- **Captions:** word-by-word **karaoke**, ALL-CAPS heavy condensed sans (Anton/Bebas), thick dark stroke, 1–3 words at a time, active word flips white → **electric magenta**. Burned from ElevenLabs timestamps (character-level → grouped into words).

## 5. Content strategy & series
- **Mix (LOCKED, news-forward): ~35% Claude/desktop/token/model tips + ~20% new-capability + ~45% news.** _(Supersedes the earlier "70% tips + 30% news" line — that split predated the news-forward pivot logged in PRODUCTION-PLAYBOOK.md around Ep22–Ep25.)_ Tips = the reliable, batchable backbone; new-capability = day-one demos of just-shipped features; news = freshness + viral spikes (batched weekly via a "So What?" filter — one story → what it changes for your workflow + one action).
- **Recurring series (→ named playlists):**
  - **Prompt Teardown** (flagship): a weak prompt on screen, rebuilt live, visibly better output.
  - **60-Second Claude:** one power feature end-to-end (Projects, MCP, sub-agents, artifacts, Claude Code).
  - **Steal This Workflow:** a copy-paste system/automation — the newsletter opt-in engine.
  - **Built With Claude:** a real micro-build under a minute.
  - **So What? — AI News, decoded** (the 30%): anti-hype, batched weekly.
  - Occasional **Claude vs ChatGPT: one real task** (reach beyond the Claude audience).
- **Hook formulas:** problem-out-loud + weak output on screen · before/after result-flash · curiosity gap + number · contrarian ("Stop using ChatGPT for this") · "steal this."

## 6. Look & tone
- **Dark editorial base (deep ink) + ONE electric accent = MAGENTA** (deliberately NOT Anthropic clay/terracotta).
- Signature **"unpacking" motif:** a panel/terminal window that opens to reveal each tip.
- Locked visual system across ALL layers (screen caps, stills, stock, motion graphics): one LUT/grade, one font stack (Anton/Bebas display + clean mono for code), one device-frame style, one motion-timing spec. **Consistency is what defeats the slop perception.**
- Tone: confident, warm, anti-hype, concise. One idea per Short, always ends on "why it works."

## 7. Toolchain (Pipeline B — VERIFIED 2026-07-31)
Script (human/Claude, tested) → **ElevenLabs** VO via `/with-timestamps` (char-level → group to words) → **HeyGen** Photo-Avatar "Sol" rendered on a **solid green background** (custom avatars can NOT export alpha) → **FFmpeg chroma-key / RVM matte** per clip → composite over **real screen recordings** (Screen Studio/OBS) + Leonardo abstract stills + CC0 stock + kinetic magenta cards → **`scripts/assemble_short.py`** (1080×1920, ASS karaoke captions, ducked music) → **`yt_upload.py --channel claude-tricks`** with `status.containsSyntheticMedia=true` + not-MFK.

## 8. Compliance (both baked into publish)
- **Synthetic-content disclosure = MANDATORY** (photoreal AI human). Set `status.containsSyntheticMedia=true` on every upload via the Data API (confirmed settable). Lean INTO "made with AI" — the label does not suppress reach and builds trust.
- **Inauthentic-content rule (July 2025):** stay human-in-the-loop — original tip selection, a written POV, script variation, the real-screen proof pane, a spoken "why it works." No two Shorts read as the same template.
- **Made-for-Kids = NO.** Comments ON. Accurate claims only (every trick tested). "Not affiliated with Anthropic" note. FTC affiliate disclosure on any affiliate Short.

## 9. Monetization (the point — verified reality)
- **Affiliate-led, not ad-led.** Shorts ad RPM ~$0.03–0.07/1k → ads alone can't hit $200/mo; full ad revenue needs **1,000 subs + 10M Shorts views/90d** (fan funding at 500 subs + 3M/90d). So ads are a bonus.
- **Open to a 0-sub channel today:** **ElevenLabs** (22% recurring/12mo) + **Writesonic** (20% recurring/12mo, ~24h approval). Apply to these first.
- **Phase-2 (need an audience):** HeyGen (creator track wants ~5k followers), Descript (brand-fit review), Jasper (~5k monthly visits). **Notion = closed** to new affiliates in 2026.
- ⚠️ Approval ≠ revenue: with 0 traffic there are no clicks. Real affiliate income follows audience. **Route every Short to "link in profile"** (Shorts description/comment links barely click) → channel About tab + one owned hub (**newsletter** landing + linktree). Build the email list from day one.
- Layer: **$19–39 Gumroad product** (prompt pack / AI tools database) early; sponsorships + newsletter ad inventory later. **$200/mo is a Phase-2 target, realistically months out.**

## 10. Costs
- **Now = $0** (free proof-of-concept first, per user).
- When approved: **ElevenLabs Creator ~$22/mo** + **HeyGen PAYG ~$5–15/mo** (custom-twin cutaways at ~$0.017–0.05/sec, $5 min top-up). Optional one-time: Screen Studio ~$89, Rotato ~$59. Leonardo/stock/music effectively free. **~$22–45/mo core, well under $200.**
