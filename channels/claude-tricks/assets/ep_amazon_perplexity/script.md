# ep_amazon_perplexity — LOCKED SCRIPT (v1)

**Channel:** AI Unpacked (`claude-tricks`) · **Air:** 2026-08-06 · **Depends on:** `research.json` v1 (verified 2026-08-06T13:59:14Z)
**Voice:** ElevenLabs Hrithik `ZZ5OIPIzxVJswEhc0UXt`, style 0.4, `<break time="0.4s" />` between lines
**Cold open:** planned hook KEPT — `q5_movement.cold_open_changed = false`, `fresher_same_story = []`. Line 1 is the peg itself.

---

## (a) The numbered lines, exactly as spoken

1. Amazon just lost this round. It had an A I agent banned from its site.
2. That agent browses, compares, and fills your cart.
3. The Ninth Circuit threw out the ban on Perplexity.
4. The case is not over.
5. The court said you are the one shopping.
6. Let agents do the legwork. You keep the pay click.
7. Amazon can still block agents in its terms.
8. Agents do the work, humans approve. This video too.
9. I unpack one A I story every single day.

**81 words · 108 syllables · 9 lines · 3 line-internal sentence stops.**

### Predicted duration (the C-axis gate)

Model calibrated on this exact chain (Hrithik / style 0.4 / 0.4s breaks) from the last three shipped VOs:

| ep | measured VO | lines | syllables | derived s/syllable |
|----|------------|-------|-----------|--------------------|
| #27 | 39.06s | 10 | 147 | **0.233** |
| #28 | 30.46s | 8 | 117 | **0.233** |
| #29 | 33.25s | 9 | 144 | 0.202 (outlier — number-heavy monosyllables) |

`dur = 0.233·syllables + 0.4·(lines−1) + 0.2·(internal sentence stops)`

→ **0.233 × 108 + 3.2 + 0.6 = 28.96s.** In band `[26, 30]`, under the 29s target.
Lower bound at the #29 fast rate: 25.4s. Two of three data points agree at 0.233, so 29.0s is the working number — but **the gate is the measured `vo_v2.wav`, not this estimate.** If it lands >30s, cut line 4 to nothing and fold "not over" into the on-screen chip (it is already mandated there); if <26s, restore "of service" to line 7 and "shopping" to line 2.

### Predicted beat clock (same model)

| # | start | end | note |
|---|-------|-----|------|
| 1 | 0.00 | 4.63 | **claim head "Amazon just lost this round" completes at 1.63s** |
| 2 | 5.03 | 7.59 | |
| 3 | 7.99 | 11.02 | |
| 4 | 11.42 | 12.82 | |
| 5 | **12.98** | **15.32** | **SECONDARY HOOK lands at 15.3s** ✅ target ~15.0 |
| 6 | 15.72 | 18.52 | |
| 7 | 18.92 | 21.48 | |
| 8 | 21.88 | 25.14 | |
| 9 | 25.54 | 28.57 | |

---

## (b) `lines` — paste-ready for `build_ep_v2.py`

```python
    "lines": [
      "Amazon just lost this round. It had an A I agent banned from its site.",
      "That agent browses, compares, and fills your cart.",
      "The Ninth Circuit threw out the ban on Perplexity.",
      "The case is not over.",
      "The court said you are the one shopping.",
      "Let agents do the legwork. You keep the pay click.",
      "Amazon can still block agents in its terms.",
      "Agents do the work, humans approve. This video too.",
      "I unpack one A I story every single day.",
    ],
```

> `A I` is spelled with a space on purpose — the pinned voice reads "AI" as a word otherwise (house convention, every prior episode).

## (c) `hot_words` — 35 punch words

```python
    "hot_words": ["AMAZON", "JUST", "LOST", "ROUND", "BANNED", "SITE",
                  "BROWSES", "COMPARES", "FILLS", "CART",
                  "NINTH", "CIRCUIT", "BAN", "PERPLEXITY",
                  "CASE", "OVER",
                  "COURT", "YOU", "SHOPPING",
                  "AGENTS", "LEGWORK", "PAY", "CLICK",
                  "STILL", "BLOCK", "TERMS",
                  "WORK", "HUMANS", "APPROVE", "VIDEO",
                  "UNPACK", "ONE", "STORY", "EVERY", "DAY"],
```

Per-line hot density (the renderer matches the set globally, so density is checked per line — no line is a fully-hot clause):

| line | hot / words | % |
|------|-------------|---|
| 1 | 6 / 14 | 43% |
| 2 | 4 / 8 | 50% (a three-verb list, not a clause) |
| 3 | 4 / 9 | 44% |
| 4 | 2 / 5 | 40% |
| 5 | 3 / 8 | 38% |
| 6 | 4 / 10 | 40% |
| 7 | 4 / 8 | 50% |
| 8 | 4 / 9 | 44% |
| 9 | 4 / 9 | 44% |

House norm for reference: #29 ran 39 hot / 92 words = 42%.

## (d) Cover hook

```python
    "cover": {"title1": "AMAZON LOST", "title2": "THE CART FIGHT",
              "sub": "ninth circuit · aug 4 · case continues", "emojis": "🛒⚖️",
              "until": 3.0},
```

`sub` carries the mandated on-screen citation *and* defuses the finality that "LOST THE CART FIGHT" would otherwise imply in type. `until: 3.0` follows §13 (title overlay is a beat, 2.5–4s) and costs the first ~3 hot words of the hook caption — accepted, because the poster states the same claim in type.

Mandated chip (from `compliance.required_chip`), dead space only, never over the quoted holding:

```
Preliminary injunction vacated — case continues
```

---

## (e) Per-line claim map

| # | line | backing | notes |
|---|------|---------|-------|
| 1 | Amazon just lost this round. It had an A I agent banned from its site. | **C1**, **C12** | "this round" is the mandated substitute for the banned "Amazon lost the case". "an A I agent" (indefinite) — not *all* AI, only the assistant the injunction named. |
| 2 | That agent browses, compares, and fills your cart. | **C14**, **C13**, `q4.can_browse_compare`, `q4.can_add_to_cart` | Stops at the cart on purpose. Never says it buys. |
| 3 | The Ninth Circuit threw out the ban on Perplexity. | **C1**, **C18** | Names the court and its level. "threw out" = vacated, beginner gloss. |
| 4 | The case is not over. | **C2**, **C3** | The honest-scope line. Merits undecided; remanded to N.D. Cal. |
| 5 | The court said you are the one shopping. | **C4**, **C5** | Standalone, pinnable, near-verbatim to the holding at slip op. p.15. |
| 6 | Let agents do the legwork. You keep the pay click. | **C14**, **C17** (+ `q4.checkout_behaviour`) | Framed as *advice*, not as a fact about the product — see judgment call 2. |
| 7 | Amazon can still block agents in its terms. | **C8** | Slip op. p.21 n.5. Directly forecloses the banned "Amazon can't stop it anymore". |
| 8 | Agents do the work, humans approve. This video too. | — | Doctrine + this channel's own disclosure. Non-factual; asserts nothing about a third party. |
| 9 | I unpack one A I story every single day. | — | CTA. |

### Entities named in the VO

`Amazon`, `Perplexity` — both `required: true`. **No other company is spoken.** Apple / Google / Meta (the optional Safari, Maps and Muse Code beats) are all cut, so no extra disclaimer line is owed.

Disclaimer must therefore read: *Not affiliated with Amazon or Perplexity.* (`compliance.multi_entity_disclaimer_must_list`)

### Banned-phrasing audit — every entry checked against the final 9 lines

| banned | status |
|--------|--------|
| "Amazon lost the case" | ✅ line 1 says "lost this round" |
| "The court ruled AI agents are legal" | ✅ never said; line 5 is the access holding, line 7 is the counterweight |
| "It's legal everywhere now" | ✅ line 3 names the Ninth Circuit specifically |
| "Agents can now buy anything for you" | ✅ line 2 stops at the cart; line 6 keeps the pay click human |
| "Amazon can't stop it anymore" | ✅ line 7 says the exact opposite |
| "The court said AI agents have rights / are like users" | ✅ line 5 says the *user* is the one shopping |
| "This settles the law on AI agents" | ✅ line 4 |
| "Perplexity won the lawsuit" | ✅ line 3 is the ban, not the lawsuit; line 4 |
| "You can now let AI shop Amazon for you" | ✅ line 6 is a general rule; line 7 immediately scopes it back |
| "Amazon accepted the ruling / didn't respond" | ✅ never said |
| "The judge said…" | ✅ line 5 says "the court" |
| "This means you're safe to automate any site" | ✅ never said |

### Deliberately NOT in the VO

- **"It works on Amazon today."** `q4.mandatory_script_limit` — a vacated injunction is not a restored feature, and no source confirms operation. Nothing in the script implies present-tense operation on Amazon.com.
- **C7** (no new legal regime) and **C3** in full — no line budget at 29s. Both are carried by the on-screen chip + the description. If the reviewer wants C7 spoken, it costs line 4 its slot.
- **C10** (Amazon's "we respectfully disagree" statement) — cut for length. It belongs in the description. Nothing in the VO implies Amazon accepted the result.
- **C9** (users could have faced criminal exposure under Amazon's theory) — strong beat, no room; description.
- **"Not legal advice"** — `compliance.not_legal_advice_required: true`. **Owed on screen and in the description**; it is not in the VO.

### Judgment calls (flagged for review)

1. **Hook wording.** The brief's line — "Amazon just lost the fight to keep AI out of your shopping cart" — reads as final, and Q1 says this was a **preliminary** injunction with the case remanded. Kept the energy, changed the tense of the loss: *"Amazon just lost this round."* The claim head completes at ~1.63s (est.), marginally over the 1.5s spec. If the measured `vo_v2.words.json` puts "round" past 1.5s, drop "just" (−0.23s) rather than re-cutting the line.
2. **The consumer-tier limit is stated as a rule, not a fact.** Q4 marks the checkout behaviour `MEDIUM` confidence and `disputed: true` — the parties fight over it and the court did not resolve it. So line 6 says *"You keep the pay click"* (advice the viewer controls) instead of *"it hands you the checkout"* (a contested claim about the product). This satisfies the brief's intent without the script settling a dispute the research forbids settling.
3. **Line-1 → line-3 referent.** Line 1 establishes the ban so line 3 can say "the ban" without a second gloss. That is what bought the syllables for line 7 (the Terms-of-Service counterweight), which is the single most important honesty line in the episode.
