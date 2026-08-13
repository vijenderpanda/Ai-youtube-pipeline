# Calm AI — Channel Setup & Launch Kit
_Scaffolded 2026-08-12. Global English audience, not India-restricted. Everything in §1–§3 is a **human step on youtube.com** — the factory cannot do it via API._

## 0. Reality check — read before spending a rupee
1. **This is our third AI channel.** The wedge (de-escalation, parent-relevant "so what", no host) is real but thin. If the first five episodes don't feel obviously different from AI Unpacked in the first 3 seconds, kill or merge the channel rather than diluting the network.
2. **The lane is crowded.** "Calm, explainer, faceless" is a common Shorts format. We win on hook quality + the fact-check wedge, not on the look.
3. **We are the July-2025 inauthentic-content profile.** Vary genuinely per episode (BRAND-BIBLE §6) or get throttled.
4. **Assume a 60–90 day ramp.** Judge on rolling 10–20 uploads, never per-video.
5. **"Calm" is a retention risk.** Low energy can read as low stakes and get swiped. The tension has to come from the *fear being named in the first line*, not from pace. Watch the 15s hold on Ep01–03 (`scripts/yt_retention.py --channel calm-ai`) and treat any >6pp cliff before 11s as a hook failure, not a pacing preference.

## 1. Name & handle — LOCK THESE FIRST (human)
- **Name: Calm AI.**
- **Handle: `@calmai`** — almost certainly taken; check and take the first free option in order, then claim the same string on TikTok + Instagram + X the same day:
  1. `@calmai`
  2. `@calm.ai`
  3. `@thecalmai`
  4. `@calmaidaily`
  5. `@calmaishorts`
- Reinforce the brand verbally by closing every episode on **"That's it. You're caught up."**

## 2. Channel description (About) — paste-ready
> Calm AI — AI news, minus the panic.
>
> Every Short takes one real thing that happened in AI this week and answers the only question that matters: do you actually need to do anything about it? No hype, no doom, no jargon. Just what happened, what the scary version got wrong, what it means for your week, and one calm thing to do — which is often nothing.
>
> Made for busy adults who don't have time to keep up and are tired of being told to panic. Every claim is sourced and dated.
>
> New Shorts Monday, Wednesday and Friday.
>
> #Shorts #AI #AINews

## 3. Channel keywords (Settings → Channel → Keywords)
`Calm AI, AI news explained, AI without the hype, AI for beginners, what AI means for me, AI explained simply, AI news for parents, is AI safe, AI jargon explained, artificial intelligence explained, no hype AI, AI weekly, should I worry about AI`

## 4. Posting schedule
- **Days: Monday · Wednesday · Friday** — deliberately offset from `already-happening` (Tue/Wed/Thu) so the two AI channels don't compete for the same feed slot, and so the week opens and closes on a calm note.
- **Time: 12:00 PM US Eastern** = 16:00 UTC (EDT) = **9:30 PM IST**. Hits the US lunch break, UK ~5 PM, EU ~6 PM — the "catch me up on my break" moment, which is the brand's use case. (US winter/EST → 17:00 UTC / 10:30 PM IST.)
- Anchor to US-Eastern **local** time so it survives DST. **Hold it fixed for the first month**; timing barely moves a cold channel — over-optimise hooks instead.

## 5. Per-Short SEO
**Title formula:** `[plain-language subject in the first 3 words] + [the reassurance or the correction]`, 40–55 chars, sentence case.
- Good: `AI in schools: what actually changed this week`
- Good: `No, AI isn't reading your emails — here's what is`
- Bad: `INSANE new AI update SHOCKS everyone 🤯` (wrong channel, wrong brand)
- Ship mostly correction titles; ~1 in 3 a question title for search capture.

**Description template:**
```
<one-sentence plain summary of what happened, with the date>

What the panic version got wrong: <one line>
What it means for you: <one line>

Sources:
- <publisher>, <YYYY-MM-DD>: <url>
- <publisher>, <YYYY-MM-DD>: <url>

Calm AI — AI news, minus the panic. New Shorts Mon / Wed / Fri.
This video uses AI-generated visuals and voice.

#Shorts #AI #AINews
```
3–5 hashtags, led by `#Shorts`. Sources are **not optional** — they are the wedge.

## 6. Publish path
- Draft in `factory_posts` → arm on the dashboard → worker uploads via `scripts/yt_upload.py`.
- Flags: `--audience general --synthetic` (AI footage + AI voice → disclosure required).
- Wired in `scripts/factory_worker.py` (`UPLOAD_DEFAULTS` / `CHANNEL_SEED` / `DISPLAY_MAP`).
- **Token file `secrets/token_calm-ai.json` does not exist yet** — a human OAuth step, see `NEEDS-ATTENTION.md`. Do it *before* Ep01 finishes rendering, and include the `force-ssl` scope in the same consent so comments/pinning work later (the `yt-engage-scope-and-pin-limits` lesson).

## 7. Brand assets
- Generated in-house by `channels/calm-ai/gen_brand.py` → `assets/brand/icon.png` (800×800), `assets/brand/icon_circle160.png` (32px legibility proof), `assets/brand/banner.png` (2560×1440).
- Upload: icon → Studio → Customisation → Branding; banner → same page. Both are human steps (no API).
- Re-run `python3 channels/calm-ai/gen_brand.py` after any identity change; it is deterministic.
