# publish_metadata v1 — `ep_amazon_perplexity` (AI Unpacked / `claude-tricks`)

**Depends on:** `research.json` v1 (verified 2026-08-06T13:59:14Z) · `script.md` v1 (locked) · `vo_master` v1 (29.37s speech / 29.72s file)
**Written:** 2026-08-06 · **Preflight run live against the API this session** (`verify_uploads.py`, `videos.list`)
**Deliverables:** this file + `publish.json` (machine-readable, same content) → both copied to `channels/claude-tricks/assets/ep_amazon_perplexity/`

---

## 1. TITLE

```
Amazon Just Lost This Round Over AI In Your Cart 🛒 (Court: You're The Shopper)
```

**78 characters** (≤100 ✅) · front-loaded ("Amazon Just Lost This Round" is the claim, first 27 chars) · **one emoji** 🛒.

### Scope check — why not "lost the case"

`research.json → q1_scope.final_vs_preliminary = "PRELIMINARY"`, `case_continues = true`. The brief's own
example headline ("Amazon Just Lost The Fight…") reads final; the disposition is a **vacatur of a preliminary
injunction plus remand**. `banned_phrasings[0]`: *"Amazon lost the case" → use "Amazon lost this round."*
The title therefore says **"this round"**, which is also the exact wording of VO line 1 and of the cover
(`AMAZON JUST / LOST THIS ROUND`) — three surfaces, one scope.

The parenthetical is the holding, near-verbatim to slip op. p.15 ("It is the user who 'accesses' Amazon's
computers"). It is **not** "the court ruled AI agents are legal" (banned #2) and **not** "AI agents have
rights" (banned #6).

### Surface de-duplication (all three hook on different beats)

| surface | copy |
|---|---|
| cover (frame zero) | AMAZON JUST / LOST THIS ROUND |
| 16:9 thumbnail | AMAZON v. PERPLEXITY · YOU ARE / THE SHOPPER |
| **title** | Amazon Just Lost This Round Over AI In Your Cart 🛒 (Court: You're The Shopper) |

The title is the only surface carrying the *cart* — the concrete consumer stake — so the three do not repeat.

---

## 2. DESCRIPTION

Paste verbatim into `channels/claude-tricks/docs/desc_ep_amazon_perplexity.txt` and pass with
`--desc-file`. Sections are in the brief's mandated order (summary → sources → what it can do → multi-entity
disclaimer → affiliate disclosure → CTA).

```text
A US appeals court threw out the order that had blocked Perplexity's AI shopping assistant from Amazon — Amazon lost this round, but the lawsuit itself is still running.
Precisely: on August 4, 2026 a three-judge Ninth Circuit panel held that Amazon was unlikely to succeed on the "access" element of its CFAA and CDAFA claims, vacated the district court's preliminary injunction as an abuse of discretion, and remanded for further proceedings — expressly without deciding the merits.

SOURCES & DATES
• Amazon.com Services, LLC v. Perplexity AI, Inc., No. 26-1444 (9th Cir., filed Aug 4, 2026) — the opinion itself, FOR PUBLICATION. Vacatur + remand; the "access" holding; "the CFAA contemplates access by a person… it is a tool, not a person for statutory purposes"; the same reasoning defeating the California CDAFA claim; the court's express statement that it does NOT establish a new legal regime for agentic AI; footnote 5 preserving Amazon's ability to restrict agents via its own Terms of Service; the warning that Amazon's theory could have exposed users themselves to criminal liability; and the mechanics — Perplexity's servers never directly access Amazon's servers. Panel: Judges Milan D. Smith Jr. and Eric C. Tung, with District Judge John Charles Hinderaker. Complaint filed Nov 2025; injunction granted Mar 2026.
  https://cdn.ca9.uscourts.gov/datastore/opinions/2026/08/04/26-1444.pdf (Aug 4, 2026)
• Amazon's response — "We respectfully disagree with today's decision on the preliminary injunction. We remain confident in our case and are evaluating our next steps."
  https://www.engadget.com/2230471/perplexity-has-successfully-overturned-amazon-injunction-on-its-ai-shopping-bot/ (Aug 4, 2026)
• Perplexity's response, and the framing of this as the first federal appellate ruling on whether AI agents acting for users can access online platforms.
  https://www.pymnts.com/amazon/2026/appeals-court-overturns-ban-on-perplexity-ai-shopping-agents-on-amazon/ (Aug 5, 2026)
• Comet availability and tiers.
  https://www.perplexity.ai/comet (checked Aug 6, 2026) · https://www.eesel.ai/blog/perplexity-comet-pricing (checked Aug 6, 2026) · https://ecommerceguide.com/agents/comet-2/ (checked Aug 6, 2026)

APPEAL STATUS: No reported appeal signal as of 2026-08-06: Amazon has publicly disagreed and says it is evaluating next steps, but no en banc or Supreme Court filing is reported. Amazon's lack of a filing is not acceptance — it stated on the record that it disagrees.

WHAT THE AGENT ACTUALLY DOES TODAY — AND WHAT IT DOESN'T
Perplexity's Comet browser and its Assistant are available to consumers, free, on Windows 10/11, macOS 13+, iOS and Android; paid Pro/Max tiers raise browser-agent query limits, and Max adds background assistants (checked Aug 6, 2026). It browses, compares and fills a cart. On consumer tiers the payment step is gated behind human confirmation — the agent does the legwork and hands back at checkout. Three honest limits: (1) how autonomous the Assistant really is was disputed by the parties and the court did not resolve it; (2) the Assistant works at your direction — it cannot operate wholly independently; (3) a vacated injunction is not a restored feature. The court removed a legal bar; it did not order Amazon to admit anyone, and footnote 5 leaves Amazon free to block agents through its Terms of Service. We have not confirmed the Assistant operating on Amazon.com for a consumer today, and we are not claiming it does. This is reporting, not legal advice.

⚠️ Not affiliated with Amazon or Perplexity. Neither company sponsored, reviewed or approved this video, and neither is a source for anything here beyond its own public statement quoted above. No Amazon or Perplexity logo, screenshot or interface appears in this video: the shopping-assistant chat and the delegation card are our own neutral in-house mock-ups, labelled illustrative. Made with AI, checked by a human — the presenter is an AI-animated version of me, built with the tools we teach.

🎙️ The AI voice tool we use: https://try.elevenlabs.io/4wscoc0bm5zl
(Affiliate link — we earn a commission if you subscribe, at no extra cost to you. ElevenLabs is deliberately named here and NOT in the non-affiliation line above, because we do have a commercial relationship with it and that claim would be false. B-roll via Pexels, licensed, no attribution required. Music is our own generated instrumental.)

🎯 One AI story unpacked every single day — follow so you don't miss one
📚 "Claude Zero to Pro" — the beginner series
📬 Free AI tools cheat sheet + every link we mention: the About tab on this channel

#AIAgents #AIShopping #AgenticAI #AINews #Shorts
```

**Description compliance notes**

- **Not legal advice** — required by `compliance.not_legal_advice_required: true`; carried by the last
  sentence of the capability section, and mirrored on screen by the mandated chip.
- **`no reported appeal signal as of <date>` is verbatim** from `q3_appeal.status_line`, plus the
  `do_not_infer` sentence, so the absence is never read as acquiescence.
- **Every claim in the description is dated.** C1–C19 in `research.json` are all covered; the four
  `rejected_claims` appear nowhere (in particular, *not* "Amazon sued in March 2026" — the complaint was
  **November 2025**, and the description says so).
- **Cross-cluster rule honoured, absolutely.** No link to Lulla, Rumble Trucks, Poly/language-abc or any
  other kids channel. The only CTA destination is this channel's own About tab.
- **CTA is the About tab, not an in-description URL** — Shorts descriptions barely click
  (PLAYBOOK line 226); the About tab holds 14 link slots and is the channel's link hub.

---

## 3. MULTI-ENTITY DISCLAIMER — the enumeration, shown as work

The rule (`compliance.multi_entity_rule`, and QUALITY-LEDGER §5): *the "Not affiliated with X" line must list
**every** named entity, not just the channel's boilerplate one.* Missing one is the exact defect the rule
exists for. So the list is derived from **two independent passes** and then unioned.

**Pass 1 — `research.json → entities_named[]`**

| entity | `required` | in final VO? | in disclaimer? |
|---|---|---|---|
| Amazon (Amazon.com Services, LLC) | **true** | yes — lines 1, 7 | **YES** |
| Perplexity (Perplexity AI, Inc.) | **true** | yes — line 3 | **YES** |
| Apple | false — *only if the Safari analogy beat survives* | **NO** — beat cut | no, correctly |
| Google | false — *only if the Maps agentic-commerce segue survives* | **NO** — beat cut | no, correctly |
| Meta | false — *only if the Muse Code segue survives* | **NO** — beat cut | no, correctly |

**Pass 2 — everything named on screen, read off the delivered fragments** (this is the #25 method: enumerate
from the *footage*, not only from the script)

| surface | brand names present? |
|---|---|
| `host_hook_clip` / `host_payoff_clip` | none — founder photo, own studio background, no corner badge |
| `chat_mock_agent_cart` (in-house) | none — neutral dark chat, generic "AI ASSISTANT" label, ILLUSTRATIVE footer, no retailer marks |
| `glyph_delegation_clip` (in-house) | none |
| `broll_*` (Pexels) | none — checked as clean at fetch |
| `step_chips` S1–S3 + compliance chip | none |
| `emphasis_overlays` | none |
| `cover_frame_zero` | "AMAZON" (title copy) — already listed |
| `thumbnail` | "AMAZON v. PERPLEXITY" (pill) — both already listed |
| `outro_bookend` | channel branding only |

**Union = {Amazon, Perplexity}.** Matches `compliance.multi_entity_disclaimer_must_list` exactly. The
disclaimer reads **"Not affiliated with Amazon or Perplexity."**

**The ElevenLabs carve-out (the #25 precedent).** ElevenLabs is named in the description — but in the
*affiliate disclosure*, never in the non-affiliation line. We **are** affiliated with it. A blanket "not
affiliated with anyone named here" would be a false statement, which is a worse compliance failure than the
omission the rule guards against. Same logic for Pexels (a licence, not a sponsorship) — named as a source,
not as a non-affiliate. This asymmetry is stated in the description itself so a reader can see it is
deliberate.

---

## 4. TAGS

10 tags (band 8–11 ✅) — 6 story terms + 4 channel evergreen:

```
ai news, ai agents, ai shopping, agentic ai, amazon, perplexity, ai law, ai for beginners, ai tips, claude ai tips
```

`ninth circuit` was the 11th candidate and was **dropped**: it is a search term for lawyers, and this
channel's audience is general beginners (memory: *AI Unpacked — Audience Pivot*). `ai law` carries the same
territory in language the audience actually types. Tag casing follows the live channel convention
(all-lowercase, verified on `xZirrXHzM4Q`).

---

## 5. FLAGS

| field | value | source of truth |
|---|---|---|
| `containsSyntheticMedia` | **`true`** → `yt_upload.py --synthetic` | a photoreal AI human + a cloned voice requires it; `UPLOAD_DEFAULTS["claude-tricks"].synthetic = True` |
| `selfDeclaredMadeForKids` | **`false`** → `--audience general` | `channel.json.made_for_kids = false`; `UPLOAD_DEFAULTS` audience `notForKids` |
| `categoryId` | **`28`** (Science & Technology) | **brief-specified — see the flag below** |
| `privacyStatus` | `private` + `publishAt` (scheduling forces private until the slot) | `yt_upload.py --publish-at` |
| `--thumbnail` | `renders_out/staged/de372dd8-…/thumbnail/v1/thumb.jpg` | thumbnail fragment v1 |
| `--playlist` | none | no series playlist for news items |

> ⚠️ **Category is a deliberate divergence, flag it at review.** The brief specifies Science & Technology
> (**28**). Every one of this channel's 11 live public+scheduled videos is **27 (Education)** — confirmed live
> this session on `xZirrXHzM4Q`, and 27 is `yt_upload.py`'s default. 28 is defensible for a legal/agentic-AI
> news item and it is what the spec says, so **28 is what this package sets**. If the reviewer prefers
> catalogue consistency over the spec, it is a one-token change (`--category 27`) and nothing else moves.

### Publish slot — 🔴 **the Aug-7 daily slot is NOT vacant. Read this before arming.**

The brief's premise is that item `dcf956d5` was superseded and left the Aug-7 daily slot empty. **That was
true when the suggestion was written and is no longer true.** Verified live this session:

```
videos.list part=status id=xZirrXHzM4Q
  → privacyStatus: private, publishAt: "2026-08-07T10:30:00Z"
  → "Google Just Put AI In Your Kid's Classroom 🎓 (Parents, Check This)"
```

`CONTENT-CALENDAR.csv` row **08** agrees: `SCHEDULED 2026-08-07 10:30 UTC · youtu.be/xZirrXHzM4Q`.
`channel.json` `slot_time_ist: "16:00"` = **10:30 UTC** — so 10:30 UTC *is* the daily slot, and build 08
already holds Aug-7's.

Applying the preflight collision rule (PLAYBOOK line 140: *nothing else on this channel within ±6h*), the
window **2026-08-07T04:30Z → 16:30Z is blocked**.

**Slot set by this package:**

```
publish_at = 2026-08-07T17:00:00Z          (22:30 IST · 1:00 pm ET)
```

- **6h30m after** build 08 — clears ±6h with 30 minutes of margin.
- **Same day Aug 7**, as the brief intends, so the peg is **3 days old** (opinion filed Aug 4) — inside
  `--max-age-days 4`. Deferring to Aug-8 10:30Z would put it at 4 days, at the ceiling, on a story whose
  whole value is that it is fresh.
- Touches nothing already armed. Moving build 08 would require an unschedule, which the playbook says is
  **never implicit** (line 135) — not something this package does on its own authority.
- **Fallback if the reviewer wants strict one-video-per-day cadence:** `2026-08-08T10:30:00Z`. Calendar row
  10 for Aug-8 is unproduced and unscheduled, so it is free — but re-run the collision check at arm time,
  because build 24 is still unpublished and has been eyeing Aug-8/Aug-12.

### Preflight — run live this session, both halves ✅

`python3 scripts/verify_uploads.py --channel claude-tricks --json /tmp/vu.json` →
**`TOTAL DISCREPANCIES: 0`**, 11 public+scheduled / 14 fetched.

| check | result |
|---|---|
| **±6h collision on `factory_posts`** | calendar shows no other claude-tricks item near 2026-08-07T17:00Z (rows 07/09/22 shipped, row 10 is Aug-8) — **clear** |
| **±6h collision on the LIVE uploads list** | only Aug-7 item is `xZirrXHzM4Q` @ 10:30Z; Δ = 6h30m — **clear** |
| **near-duplicate title vs live list** | 11 live titles carry no "Amazon", "Perplexity", "cart" or "shopper"; `near_duplicate_pairs: []` — **clear** |
| **near-duplicate title vs `factory_posts`** | no calendar/working title in the file uses this story — **clear** |
| **double-booked slot** | `double_booked_slots: []` — **clear** |

⚠️ This preflight is **timestamped 2026-08-06 15:24 UTC**. It is a snapshot, not a licence. **Re-run it
immediately before arming** — build 24 and builds 27/29/30 are all produced-but-unscheduled and any of them
landing on Aug 7 would change the answer.

---

## 6. UPLOAD COMMAND

```bash
python3 scripts/yt_upload.py \
  --channel claude-tricks \
  --video    channels/claude-tricks/renders/ep_amazon_perplexity_v2_outro.mp4 \
  --title    "Amazon Just Lost This Round Over AI In Your Cart 🛒 (Court: You're The Shopper)" \
  --desc-file channels/claude-tricks/docs/desc_ep_amazon_perplexity.txt \
  --tags     "ai news,ai agents,ai shopping,agentic ai,amazon,perplexity,ai law,ai for beginners,ai tips,claude ai tips" \
  --category 28 \
  --audience general \
  --synthetic \
  --publish-at 2026-08-07T17:00:00Z \
  --thumbnail renders_out/staged/de372dd8-264e-4e52-9296-e6ae664e23e4/thumbnail/v1/thumb.jpg
```

**Read the output, not the exit code.** Post-upload steps (thumbnail set, playlist append) are **non-fatal
warnings** — a thumbnail failure does not mean the upload failed. **The video id printed in the upload output
is the truth.** If a step warns, re-run with `--video-id <id>` to set the thumbnail alone; never re-upload,
or you have created the duplicate `verify_uploads` exists to catch.

**Before arming, assert the file is the newest approved cut** (PLAYBOOK line 249 — the Ep25 loss). Every
craft fix in this build is worthless if an older assembly is what gets armed. A published Short's file can
never be swapped.

---

## 7. 🔴 MANDATORY LAST STEP — the acceptance gate

**The job is not done when the upload returns. It is done when this exits zero.**

```bash
# 1. the gate — exit non-zero means the job is NOT done
python3 scripts/verify_uploads.py --channel claude-tricks

# 2. re-assert AND LOG the synthetic-media flag
python3 scripts/verify_uploads.py --channel claude-tricks --assert-disclosure --yes
```

Expected after both: `TOTAL DISCREPANCIES: 0`, and this episode's video id present in
`channels/claude-tricks/disclosure_ledger.json`. **That file does not exist yet** — verified this session.
This episode creates it, so its first write is the one to eyeball.

### Why the disclosure step is a *write*, not a read — and why reading it is a guaranteed false positive

**`videos.list` NEVER returns `status.containsSyntheticMedia`.** The Data API accepts it on
`videos.insert` / `videos.update` and simply does not echo it back. Confirmed live this session — the full
`status` resource for `xZirrXHzM4Q` came back as `uploadStatus, privacyStatus, publishAt, license,
embeddable, publicStatsViewable, madeForKids, selfDeclaredMadeForKids`. **No `containsSyntheticMedia` field
at all**, on a video this repo uploaded with `--synthetic`.

So **an absent field means "not returned", never "not disclosed."** Auditing disclosure by reading the API
returns a false positive on **every single video** — 11/11 on this channel — which is exactly the bug an
earlier build of `verify_uploads.py` shipped. Hence: synthetic disclosure is **ADVISORY**, never a
discrepancy (unless someone passes `--strict-disclosure`, which re-introduces the false positive on purpose),
and the only way to make it verifiable is to **re-assert it and write it down**. `--assert-disclosure`
round-trips the full status resource and re-reads each video afterwards, aborting if `privacyStatus` or
`publishAt` moved by a hair — because `videos.update` **replaces** the whole part you send, and one missing
key is an accidental unschedule. Ledger entries are only ever written for videos we actually asserted:
never inferred, never backfilled.

`madeForKids` **is** readable, so the kids/notForKids check is real. Disclosure is not. Do not conflate them.

### `videos.list` is read-after-write stale — how to read a confirmation

The **`videos.insert` / `videos.update` response is the authority.** The re-read is a *confirmation*, and it
can legitimately lag the write by seconds. So:

- A confirming re-read that comes back stale or empty is **not** evidence the write failed. Retry briefly
  (a few seconds, 2–3 attempts) before concluding anything.
- **The video id in the upload output is the truth, not the exit code.** If you have an id, the video
  exists — go verify and repair from that id. If you have no id, and only then, has nothing been created.
- Never respond to a stale read by re-uploading. That is how the duplicate gets made.

### Post-publish hygiene

Update `CONTENT-CALENDAR.csv` `planned_date` to `SCHEDULED 2026-08-07 17:00 UTC · youtu.be/<id>`. A calendar
row is closed by a **video link**, not by a word (PLAYBOOK line 157) — a bare "SCHEDULED" with no link stays
guarded by `daily_check.py` and will keep raising.

---

## 8. QUALITY-LEDGER ROW — draft for `channels/claude-tricks/QUALITY-LEDGER.md` §4

Append after row 08. Claimed: **B, D, H** beaten. Held: **A, C, E, F, G, I, J**.

```markdown
| ep_amazon_perplexity | Amazon Just Lost This Round Over AI In Your Cart 🛒 (Court: You're The Shopper) | **B** (the deepest freshness pass this channel has run: `news_radar.py` + `--peg-check` returned FRESH with `fresher_same_story: []`, then — instead of trusting press paraphrase — the actual Ninth Circuit slip opinion was pulled and read, *Amazon.com Services, LLC v. Perplexity AI, Inc.*, No. 26-1444, filed Aug 4 2026, so Q1/Q2 are pinned to verbatim primary-source quotes with page cites. That read caught a wire error the coverage repeats — "Amazon sued in March 2026"; the complaint was **Nov 2025**, March is when the injunction issued — and it fixed the episode's scope: this is a **vacatur of a preliminary injunction + remand**, merits undecided, so every surface says "lost this round", never "lost the case". Appeal status disclosed *as an absence with its date* — "no reported appeal signal as of 2026-08-06" — plus Amazon's on-record disagreement, so the absence can't be misread as acceptance. All 19 claims dated with URLs in the description; peg 3 days old at the Aug-7 slot, inside the 4-day ceiling) + **D** (news visual grammar with **ZERO vendor UI on a story about two named companies**, where a screenshot of the Comet assistant or an Amazon cart was the lazy path and the obvious one: the hero is an **in-house neutral agent-chat mock** (`make_chat_mock_agent_cart.py` — generic "AI ASSISTANT" label, ILLUSTRATIVE footer, no retailer marks) frozen in the top pane on **frame 1** via the `newsSplit` grammar while the lip-synced host speaks in the bottom pane — both literally on frame 1, no beat spent, vs 4.950s for the rejected host-then-cut alternative — plus an in-house **delegation glyph** carrying the "you're the one shopping" beat, and licensed Pexels b-roll. This extends #08's "the real dated source as proof" in the opposite direction: when the entity IS the story, showing its UI is the risk, so the explainer beats are authored) + **H** (multi-entity disclaimer enumerated **twice and unioned** — from `research.json entities_named[]` AND from every delivered fragment read for on-screen brand names — giving {Amazon, Perplexity}, both in the line. Apple/Google/Meta were conditional on beats that were cut, and are correctly absent. ElevenLabs is deliberately **excluded** from the non-affiliation line and covered by the affiliate disclosure instead, because we are affiliated with it and the claim would be false — the #25 carve-out, and the asymmetry is stated in the description so it reads as deliberate) | **A** (Hrithik `ZZ5OIPIzxVJswEhc0UXt` @ style 0.4 / 0.4s breaks, `host_canonical.jpg` byte-verified against the HeyGen avatar, and **both** host clips lipsync-measured independently — hook +23.0 ms / corr 0.9971, payoff +23.0 ms / corr 0.9969, the payoff's offset re-measured rather than inherited — corrected in the files so the beat map places at `@0.00`), **C** (**29.37s speech / 29.72s file**, inside the 26–30s band and 0.28s under the ceiling; the syllable model predicted 28.96s, +1.4% error. **This is the explicit correction of #08's 33.8s regression** — the one soft step back that build wrote down. Nothing may be appended downstream: re-render instead), **E** (all 3 chip corners scored on the **shipped** clips over the **exact line-quantised cut windows** — S1 4.95→8.29 / 3.34s, S2 13.39→15.75 / 2.36s, S3 15.75→19.34 / 3.59s, every hold ≥1.5s. Key finding: `probe_frames.py corner` scores in *frame* coordinates, but a `\|split` beat cover-fits its source into the 1080×1056 top pane, so the raw command scores pixels the episode never shows; decisions came from rebuilt `Short.tsx`-geometry composites, which flipped S1 and S2), **F** (`music_gain_db` **+3.6** derived from a transfer curve measured on *this* episode's VO (0.476 LU/dB, steeper than the 0.4 rule of thumb) → predicted body master **−18.2 LUFS** vs the last **shipped** master #26 (`BlQ-gDzw1aE`) at −18.2 body / −18.4 published — **0.0–0.2 LU**, inside the ±0.3 LU bar. #26's +1.9 dB could NOT be reused: this VO is 1.9 LU hotter and ducks the bed 2.3 LU harder), **G** (Poster Duotone cover, `until: 3.0` derived from the hook — the cover clears before the mock's reply beat; type QC'd on the PNG at 42px/31px margins, legible at 320px), **I** (existing branded `outro_sub_comment.mp4` reused verbatim — 3.800s, no re-render — and pickup verified by **running the builder's actual concat filtergraph**, not by reading it), **J** (dated sources + 10 tags + flags complete; live preflight run, 0 discrepancies). **Three trades written down, not hidden:** (1) **The Aug-7 daily slot was NOT vacant** — the premise that `dcf956d5`'s supersession left it empty expired; build 08 holds 2026-08-07T10:30:00Z (confirmed live). Slotted **17:00:00Z**, +6h30m, clearing the ±6h rule with 30 min margin rather than unscheduling an armed video. Cost: two AI Unpacked videos publish on Aug 7. (2) **`categoryId` 28** per spec, against 11/11 live videos at 27 — a deliberate divergence, flagged for the reviewer, reversible with one flag. (3) **Chip corner scores are partly proxied** — chips 1+2 land in the host pane and `v2_host.mp4` isn't rendered yet, so those numbers come from `host_hook.mp4` + `host_payoff.mp4`, two real renders from the same shoot agreeing to 0.0003; re-probe after the body master exists. | *(pending upload)* | *(pending — slot 2026-08-07T17:00:00Z)* |
```

---

## 9. Pre-arm checklist

- [ ] Armed render is the **newest approved** cut for this episode (PLAYBOOK line 249 / the Ep25 loss)
- [ ] `verify_uploads.py --channel claude-tricks` **re-run** (the 2026-08-06 15:24 UTC preflight is a snapshot)
- [ ] `2026-08-07T17:00:00Z` still ±6h-clear — check builds 24, 27, 29, 30 haven't been slotted onto Aug 7
- [ ] Description pasted to `channels/claude-tricks/docs/desc_ep_amazon_perplexity.txt` — disclaimer line intact
- [ ] Category decision made: **28** (spec) or **27** (catalogue consistency)
- [ ] `--synthetic` present on the upload command
- [ ] 🔴 `verify_uploads.py --channel claude-tricks` exits **0**
- [ ] 🔴 `verify_uploads.py --channel claude-tricks --assert-disclosure --yes` run; video id present in `disclosure_ledger.json`
- [ ] `CONTENT-CALENDAR.csv` closed with the **video link**, not the word "SCHEDULED"
- [ ] QUALITY-LEDGER §4 row appended
