# research.md — ep_amazon_perplexity (AI Unpacked / claude-tricks)

**Asset:** `research_peg_verification` v1 · production-time truth pass
**Status:** ✅ **Q1 PINNED TO PRIMARY SOURCE.** The episode may proceed.
**verified_at:** `2026-08-06T13:59:14Z` (2026-08-06 19:29 IST)
**Tools used:** `scripts/news_radar.py`, `scripts/news_radar.py --peg-check`, WebSearch (7 queries), WebFetch (2), direct read of the Ninth Circuit slip opinion PDF.

> **The one thing that matters:** this is a **vacatur of a preliminary injunction**, not a final judgment. Amazon **lost this round**; Amazon **has not lost the case**. The case is remanded and continues in N.D. Cal. Any line in the script that implies finality is false.

---

## 0. Peg freshness gate

`scripts/news_radar.py` — ran. Output: `feed fail https://www.anthropic.com/news/rss.xml: HTTP Error 404: Not Found` → **`radar: 0 new hits`**. (The Anthropic RSS endpoint is dead; unrelated to this peg, but worth a separate fix ticket.)

`scripts/news_radar.py --peg-check` — **the flag exists** (confirmed via `--help`; signature is `--peg-check PEG [--air-date] [--max-age-days] [--json]`). Ran with the peg string and `--air-date 2026-08-06`:

| field | value |
|---|---|
| `first_seen` | 2026-08-05 |
| `age_days` | 1 |
| `max_age_days` | 4 |
| `verdict` | **FRESH** |
| `fresher_same_story` | *(empty)* |

**Correction to the brief:** the spec lists the peg as "llm-stats.com, Aug 5 2026". That is the *aggregation* date. The opinion was **filed August 4, 2026**, and first-wave reporting (Engadget, Reuters, US News) is dated Aug 4. True peg age on air date is **2 days**, not 1. Still inside the 4-day gate → **FRESH, cleared to air.**

---

## 1. The primary source

**Amazon.com Services, LLC v. Perplexity AI, Inc.**, No. 26-1444 (9th Cir. Aug. 4, 2026) — **FOR PUBLICATION**.

- District court below: N.D. Cal., D.C. No. 3:25-cv-09514-MMC, **Judge Maxine M. Chesney**
- Panel: **Milan D. Smith, Jr.** and **Eric C. Tung**, Circuit Judges, and **John Charles Hinderaker**, District Judge (D. Ariz., sitting by designation)
- Opinion by **Judge Milan D. Smith, Jr.**
- Argued & submitted June 11, 2026, Seattle
- Slip opinion PDF: https://cdn.ca9.uscourts.gov/datastore/opinions/2026/08/04/26-1444.pdf
- Docket/mirror: https://law.justia.com/cases/federal/appellate-courts/ca9/26-1444/26-1444-2026-08-04.html

Every quote below is transcribed from that PDF. **We did not rely on press paraphrase for the holding.**

---

## Q1 — SCOPE: what exactly did the court hold?

### `final_vs_preliminary` → **PRELIMINARY. The case continues.**

Verbatim disposition (slip op. p.21, "CONCLUSION"):

> "Because Amazon is unlikely to succeed on the merits of the 'access' prong of the CFAA and CDAFA analysis and the equitable factors do not otherwise strongly favor an injunction, we **VACATE** the preliminary injunction granted by the district court and **REMAND** for further proceedings consistent with this opinion."

The standard of review was **abuse of discretion** over a preliminary injunction (slip op. p.9), and the merits test applied was *likelihood* of success under *Winter* — not a merits determination.

### `ruling_scope_beginner` (one sentence, beginner-safe)

> "A US appeals court just threw out the order that had blocked Perplexity's AI shopping assistant from Amazon — so Amazon lost this round, but the lawsuit itself is still running."

### `ruling_scope_precise` (one sentence a lawyer would not object to)

> "On August 4, 2026, a Ninth Circuit panel held that Amazon was unlikely to succeed on the 'access' element of its CFAA and CDAFA claims, vacated the district court's preliminary injunction as an abuse of discretion, and remanded for further proceedings — expressly without deciding the merits."

### Procedural history (from the opinion, p.8) — corrects two widely-repeated press errors

- Amazon filed its **Complaint in November 2025**, alleging CFAA and CDAFA violations, and moved for a preliminary injunction at the same time.
- The district court granted the injunction in **March 2026**, after a hearing at which it called the question "a close call."
- ⚠️ Multiple outlets (TNW, Reuters-derived wires, PYMNTS) say **"Amazon sued in March 2026."** That is **wrong** — March 2026 is when the *injunction issued*. Do not repeat it.
- ⚠️ One outlet (tftc.io) says **trademark claims survive**. The opinion states the complaint alleged **CFAA and CDAFA** and does not mention trademark claims. **Unverified — the script may not say it.**

---

## Q2 — REASONING: is "it's the USER, not the startup" the actual holding?

### ✅ **YES. It is the opinion's own reasoning, in the opinion body — not a commentator's paraphrase.**

`holding_quote` — the closest sourced wording (slip op. p.15, opinion body, Judge M. Smith):

> "Our focus is thus to ask whether Perplexity uses a tool (the Assistant) to 'access' Amazon's computers. **On the facts before us, we answer no. It is the user who 'accesses' Amazon's computers, with the help of the Assistant to carry out specific acts on Amazon.com.** To be sure, Perplexity may receive screenshots of the user's browser and may communicate instructions to the Assistant. But those activities, by themselves, do not mean that Perplexity has 'accessed' (gained entry) to Amazon's servers."

Supporting, same page:

> "The CFAA contemplates access by a person. **However advanced the Assistant currently is, it is a tool, not a person for statutory purposes.**"

Same conclusion for the state-law claim (p.18):

> "…we arrive at the same conclusion: the user (not Perplexity) accesses Amazon using the Assistant as an AI tool, and thus Amazon is unlikely to succeed on the merits of its CDAFA claim."

### 🚨 Three limiting passages the script MUST respect

These are the difference between an honest episode and a viral-but-wrong one.

**(a) The court explicitly disclaimed making agentic-AI law (p.17):**

> "Because agentic AI is an emerging technology, **we reiterate what this opinion is not. We do not establish a new legal regime governing agentic AI.** We do not address whether in other contexts, including tort claims, Perplexity can avoid liability for the Assistant's actions. Our holding here is limited to 'access' as contemplated by the CFAA and as applied to the Assistant's interactions with Amazon.com on the record before us, not the broader legal landscape surrounding agentic AI."

**(b) Amazon can still block agents — just not with a hacking statute (footnote 5, p.21):**

> "**This outcome does not impair Amazon's ability to regulate access to Amazon.com via private terms of service for its users.** On the facts before us, Amazon is simply unlikely to succeed in its attempt to regulate access by invoking the CFAA and the CDAFA."

**(c) The flip side — the court warned Amazon's theory would have put *users* at risk (p.16):**

> "Amazon's approach, if accepted, **could expose users themselves to criminal liability** (under a conspiracy or aiding-and-abetting theory) for facilitating Perplexity's purported unauthorized access to Amazon's servers."

Also load-bearing: the court applied the **rule of lenity**, construing CFAA ambiguity against liability (p.13 n.3, p.16), and noted (p.12) there is "little to no existing caselaw directly dealing with how to ascribe responsibility for AI agents like the Assistant."

**How the mechanism actually works** (p.7, and the EFF/Mozilla amicus quoted approvingly at p.14) — useful for the explainer beat:
the Assistant screenshots the browser view *on the user's machine*, sends those screenshots to Perplexity's servers, and receives instructions back. "**Perplexity's servers never directly access Amazon's servers.**" And (p.7): "the Assistant cannot operate wholly independently; it relies on direction from the user and instructions from Perplexity's servers."

---

## Q3 — APPEAL STATUS

`appeal_status`: **Amazon has publicly disagreed and is "evaluating next steps." No en banc petition and no cert petition is reported as filed as of 2026-08-06.**

Amazon spokesperson, quoted Aug 4 2026:

> "We respectfully disagree with today's decision on the preliminary injunction. We remain confident in our case and are evaluating our next steps."

— https://www.engadget.com/2230471/perplexity-has-successfully-overturned-amazon-injunction-on-its-ai-shopping-bot/ (2026-08-04)

Perplexity spokesperson:

> "Perplexity will continue to fight for the right of internet users to choose whatever AI they want."

— https://www.pymnts.com/amazon/2026/appeals-court-overturns-ban-on-perplexity-ai-shopping-agents-on-amazon/ (2026-08-05)

**Explicit non-inference statement for the script:** *no reported en banc or Supreme Court filing as of 2026-08-06.* Amazon's silence is **not** acceptance — it said the opposite. Available paths (rehearing, en banc, cert) were noted by outlets as *options*, not as filings.

Also unresolved and **not** to be asserted: whether Amazon has changed its Terms of Service in response. Amazon's ToS already required AI agents to identify themselves (e.g. via user-agent string) and limited agents to public parts of the site — that predates the ruling; **no post-ruling ToS change is reported.**

---

## Q4 — WHAT ACTUALLY SHIPPED ON A CONSUMER TIER TODAY

`consumer_tier_capability`:

| question | answer | confidence |
|---|---|---|
| Is Comet available to a normal person? | **Yes — free, worldwide** | HIGH |
| Platforms | **Windows 10/11 (64-bit), macOS 13+, iOS, Android** | HIGH |
| Free tier includes the agentic Assistant? | **Yes** — agentic search, page summarisation, shopping assistance, Deep Research | MEDIUM-HIGH |
| Paid difference (Pro / Max $200/mo) | Stronger models, **higher browser-agent query limits**, and Max-only **Background Assistants** that run unattended | MEDIUM |
| Browse + compare + add to cart | **Yes**, at user direction | MEDIUM-HIGH |
| **Completes checkout autonomously?** | **NO — treat as "hands back to the human."** Consumer deployments gate consequential actions (payment) behind human confirmation | **MEDIUM — must be hedged on air** |
| **Does it work on Amazon.com right now?** | **UNVERIFIED — see below** | **LOW** |

**Record evidence on checkout, from the opinion itself** (better than any review): Perplexity's own analogy in briefing (p.11) was to "an Apple user accessing Amazon.com via the Safari web browser, even if 'the Safari software automatically fills in the user's address and payment information at checkout on the user's behalf.'" That is **autofill-assisted checkout**, not autonomous purchasing. Amazon's counter-characterisation is that the Assistant "proceeds autonomously" and "behaves like an efficient human shopper" (p.11) — i.e. **the two parties actively dispute how autonomous it is.** The script must not settle a dispute the court declined to settle.

### 🚨 The limit that MUST appear in the script

**A vacated injunction is not a restored feature.** The court removed a *legal* bar. It did not order Amazon to let Comet in, and footnote 5 preserves Amazon's right to block agents via its own Terms of Service and technical measures. **We found no source confirming that Comet's Assistant successfully operates on Amazon.com for a consumer today.** The script may say the ban was lifted; it may **not** say "it works on Amazon now."

Sources: https://www.perplexity.ai/comet · https://comet-help.perplexity.ai/en/articles/11734730-operating-system-requirements · https://www.eesel.ai/blog/perplexity-comet-pricing (2026) · https://ecommerceguide.com/agents/comet-2/

---

## Q5 — MOVEMENT / FRESHER DEVELOPMENT

`fresher_development_check`: **`cold_open_changed: false`** — the peg holds the cold open.

- `--peg-check` returned `fresher_same_story: []`. No Aug-6 development on Amazon v. Perplexity.
- Same-day (2026-08-06) AI stories from the radar, all **smaller** than the first federal appellate ruling on AI-agent access: rogue AI agents creating fake online identities in a hacking attempt; Meta launching Muse Code; Hark previewing a browser-use agent; **Google Maps adding agentic features including food ordering and hotel bookings.**
- Judgment call: **keep the court ruling as cold open.** The Google Maps item is not a replacement peg but is the **best B-roll segue** — it makes the ruling concrete ("this is not hypothetical; agents are booking your hotel this week"). Recommended as beat 4, not as the hook.

---

## `claims[]` — the only sentences the script may assert

Anything not on this list may not be spoken.

| # | claim | source | date | conf |
|---|---|---|---|---|
| C1 | On August 4, 2026, the US Court of Appeals for the Ninth Circuit vacated the preliminary injunction that had barred Perplexity's Comet AI assistant from Amazon.com. | ca9 slip op. 26-1444 p.21 | 2026-08-04 | HIGH |
| C2 | The case is not over — the panel remanded it for further proceedings in the Northern District of California. | slip op. p.21 | 2026-08-04 | HIGH |
| C3 | The panel held only that Amazon was *unlikely to succeed* on the "access" element; it did not decide the merits. | slip op. p.9, p.21 | 2026-08-04 | HIGH |
| C4 | The court's reasoning: "It is the user who 'accesses' Amazon's computers, with the help of the Assistant to carry out specific acts on Amazon.com." | slip op. p.15 | 2026-08-04 | HIGH |
| C5 | The court reasoned the CFAA contemplates access by a person, and "however advanced the Assistant currently is, it is a tool, not a person for statutory purposes." | slip op. p.15 | 2026-08-04 | HIGH |
| C6 | The same reasoning defeated Amazon's California state-law CDAFA claim. | slip op. p.18 | 2026-08-04 | HIGH |
| C7 | The court expressly said it was **not** establishing a new legal regime governing agentic AI. | slip op. p.17 | 2026-08-04 | HIGH |
| C8 | The ruling does not stop Amazon from restricting AI agents through its own Terms of Service. | slip op. p.21 n.5 | 2026-08-04 | HIGH |
| C9 | The court warned that Amazon's theory could have exposed *users* to criminal liability under conspiracy or aiding-and-abetting theories. | slip op. p.16 | 2026-08-04 | HIGH |
| C10 | Amazon said: "We respectfully disagree with today's decision on the preliminary injunction. We remain confident in our case and are evaluating our next steps." | Engadget | 2026-08-04 | HIGH |
| C11 | As of August 6, 2026 there is no reported en banc petition or Supreme Court filing by Amazon. | absence across 7 searches | 2026-08-06 | MEDIUM |
| C12 | Amazon filed its complaint in November 2025; the district court granted the injunction in March 2026. | slip op. p.8 | 2026-08-04 | HIGH |
| C13 | Mechanically, the Assistant screenshots the page on the user's own machine and sends those to Perplexity's servers — "Perplexity's servers never directly access Amazon's servers." | slip op. p.14 (EFF et al. amicus, quoted approvingly) | 2026-08-04 | HIGH |
| C14 | The Assistant cannot operate wholly independently; it relies on direction from the user. | slip op. p.7 | 2026-08-04 | HIGH |
| C15 | Comet is available free, worldwide, on Windows, macOS, iOS and Android. | perplexity.ai/comet; Comet help centre | 2026 | MEDIUM-HIGH |
| C16 | Paid tiers (Pro/Max) raise browser-agent query limits and add Max-only Background Assistants. | eesel/Perplexity help centre | 2026 | MEDIUM |
| C17 | For purchases, consumer AI browsers gate the payment step behind human confirmation — the agent does the legwork and hands back at checkout. | ecommerceguide.com; Perplexity's own Safari-autofill analogy at slip op. p.11 | 2026 | **MEDIUM — hedge on air** |
| C18 | Panel: Judges Milan D. Smith Jr., Eric C. Tung, and District Judge John Charles Hinderaker; opinion by Judge M. Smith. | slip op. p.1–2 | 2026-08-04 | HIGH |
| C19 | This is the first federal appeals court ruling to address whether AI agents acting for users can legally access online platforms. | PYMNTS / Reuters-derived | 2026-08-05 | MEDIUM |

### Rejected — sourced but NOT usable
- ❌ "Amazon sued Perplexity in March 2026" — contradicted by the opinion (complaint Nov 2025).
- ❌ "Amazon's trademark claims survive" — the opinion describes only CFAA and CDAFA claims; unverified.
- ❌ "Amazon will appeal / plans to appeal" — Amazon said it is *evaluating* next steps.
- ❌ "Comet's shopping assistant is working on Amazon again today" — no source confirms restored operation.

---

## `banned_phrasings[]`

Never say any of these:

1. ❌ "Amazon lost the case" / "Amazon lost" → ✅ "Amazon lost **this round**."
2. ❌ "The court ruled AI agents are legal." → ✅ "The court ruled the **hacking statute** doesn't reach this."
3. ❌ "It's now legal everywhere." → ✅ Ninth Circuit only; other circuits are unbound.
4. ❌ "Agents can now buy anything for you." → ✅ the agent works at your direction, and you confirm the purchase.
5. ❌ "Amazon can't stop it anymore." → ✅ Amazon can still block agents via its Terms of Service (footnote 5).
6. ❌ "The court said AI agents have rights / are like users."
7. ❌ "This settles the law on AI agents." → the opinion says the opposite in terms (p.17).
8. ❌ "Perplexity won the lawsuit." → ✅ Perplexity won the appeal of an injunction.
9. ❌ "You can now let AI shop Amazon for you." → unverified that it works today.
10. ❌ "Amazon accepted the ruling" / "Amazon didn't respond." → it disagreed on the record.
11. ❌ "The judge said…" (singular) → it was a **three-judge panel**.
12. ❌ Any "this means you're safe to scrape/automate any site" generalisation — the court warned the *user* is the one who may carry the liability.

---

## `entities_named[]` → input to the multi-entity disclaimer

Companies/organisations the script will name:

1. **Amazon** (Amazon.com Services, LLC)
2. **Perplexity AI, Inc.**
3. **Apple** — only if the Safari analogy beat survives *(optional; drop to shorten the disclaimer)*
4. **Google** — only if the Google Maps agentic-commerce segue survives *(optional)*
5. **Meta** — only if the Muse Code segue survives *(optional; also appears in cited caselaw)*

**Required, per PRODUCTION-PLAYBOOK §multi-entity compliance:** the "Not affiliated with…" disclaimer must list **every** entity actually named in the final VO — at minimum **Amazon and Perplexity**. Non-negotiable additions for this episode, given it is a legal story:

- ✅ **"Not legal advice."** on screen and in VO — the episode describes a court ruling.
- ✅ Name the court and date on screen: *Ninth Circuit · Aug 4, 2026 · No. 26-1444*.
- ✅ On-screen chip when the ruling is described: **"Preliminary injunction vacated — case continues"** (per [[step-chips-never-cover-content]], place in dead space, never over the quote).

---

## Recommended cold open (unchanged peg)

> "A US appeals court just told Amazon it can't use a hacking law to keep an AI shopping agent off its site — because legally, it isn't the AI visiting Amazon. It's you."

Follows C1 + C4, avoids all 12 banned phrasings, and sets up the twist in C9 (the liability lands on the user, not the startup) — which is the genuinely under-covered angle and the strongest reason this episode is worth making.

---

## Sources

- [Slip opinion, Amazon.com Services, LLC v. Perplexity AI, Inc., No. 26-1444 (9th Cir. Aug. 4, 2026)](https://cdn.ca9.uscourts.gov/datastore/opinions/2026/08/04/26-1444.pdf) — **primary**
- [Justia docket entry](https://law.justia.com/cases/federal/appellate-courts/ca9/26-1444/26-1444-2026-08-04.html)
- [Engadget — Perplexity has successfully overturned Amazon's injunction (Aug 4, 2026)](https://www.engadget.com/2230471/perplexity-has-successfully-overturned-amazon-injunction-on-its-ai-shopping-bot/)
- [PYMNTS — Appeals Court Overturns Ban on Perplexity AI Shopping Agents (Aug 5, 2026)](https://www.pymnts.com/amazon/2026/appeals-court-overturns-ban-on-perplexity-ai-shopping-agents-on-amazon/)
- [TFTC — Ninth Circuit Vacates Amazon's CFAA Injunction (Aug 4, 2026)](https://www.tftc.io/ninth-circuit-cfaa-amazon-perplexity-comet-browser-ruling)
- [Techdirt — Your AI Agent Can't Violate Hacking Law. But You Might. (Aug 5, 2026)](https://www.techdirt.com/2026/08/05/ninth-circuit-your-ai-agent-cant-violate-hacking-law-but-you-might/)
- [The Decoder — US appeals court allows Perplexity's AI shopping agent back on Amazon](https://the-decoder.com/us-appeals-court-allows-perplexitys-ai-shopping-agent-back-on-amazon/)
- [Law.com — 9th Circuit Allows Use of Perplexity AI Agent on Amazon (Aug 5, 2026)](https://www.law.com/nationallawjournal/2026/08/05/9th-circuit-allows-use-of-perplexity-ai-agent-on-amazon/)
- [Perplexity — Comet](https://www.perplexity.ai/comet) · [Comet OS requirements](https://comet-help.perplexity.ai/en/articles/11734730-operating-system-requirements)
- [eesel — Perplexity Comet pricing in 2026](https://www.eesel.ai/blog/perplexity-comet-pricing)
- [Knight First Amendment Institute — Amazon v. Perplexity AI case page](https://knightcolumbia.org/cases/amazon-v-perplexity-ai)
