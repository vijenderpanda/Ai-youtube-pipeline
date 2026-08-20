# _upi production gate — RESULT (2026-08-21 03:45 IST)

`locked_numbers.json` -> `provenance.production_gate_NOT_run` said:

> Nobody has yet confirmed that Claude, given these screenshots via claude.ai on
> a phone with the real prompt, returns a GROUPED per-merchant breakdown rather
> than prose. Until that is filmed there is no proof beat.

It has now been filmed, on the real Claude Android app (`com.anthropic.claude`,
Opus 5 Thinking), with all 18 sampled frames and the verified prompt.

## The capability gate PASSED
Grouped by category, collapsed People to ONE unnamed line (the failure mode of
the first 50-word prompt), excluded the failed top-ups, and named a merchant as
the shock. It also volunteered two limits nobody asked for: the failed wallet
top-ups, and "One Blinkit entry (Rs 1,843) was cut off at a screenshot edge".

## The NUMBERS gate FAILED
| | film says | tape says |
|---|---|---|
| Blinkit | **Rs 7,339 / 8 orders / Rs 917 a tap** | **Rs 3,762 / 4 orders** |
| DMart | 5,931 | 5,931 OK |
| Zepto | 1,560 | 1,560 OK |
| Amazon | 1,414 | 1,414 OK |
| Maestro | 491.50 | 491.50 OK |
| Box8 / Bistro / Liquor | 372 / 113 / 1,000 | same OK |
| Snabbit | 1,612.50 (6) | 1,092 (4) |
| Licious | 274 | 1,231 |
| denominator | 25,136 merchant-only | 85,882.50 incl. Amex 45,000 + PayRupik 18,726 |

3,762 = 710 + 649 + 560 + 1,843 — the four August 16-18 orders. The film's other
four (923, 1215 on 03 Aug; 841, 598 on 02 Aug) are in the recording but did not
survive the model's own dedup across these 18 frames.

**Consequence:** beat 4 (12.02s) frames this reply on screen; beat 6 (18.07s)
speaks "Seven thousand, three hundred and thirty nine"; beat 7 speaks "nearly a
third" (7,339/25,136 = 29.2%). A viewer who pauses sees the film disputing
itself. NOT ARMED.

## The honest re-cut
Take the tape as the source of truth: **Rs 3,762 across four orders = Rs 941 a
tap**. The thesis survives intact — "the ones I call small are Rs 941 a tap" is
the same film and a rounder number. Costs: new lines 5-8, VO re-synth (the sig
changes), fresh host clips, full re-render, and locked_numbers.json rebuilt FROM
the reply rather than from my frame sampling.

## Still outstanding whichever way it goes
- The attached thumbnails in ask.mp4 show real payees by name (Rajan Ram RITU,
  MANOJ KUMAR CHAUHAN, RANJANA, Abhishek Sarswat, Majalom Mansuri, PRINCE
  JAISWAL, ANNU, Kamal Sain). The *reply* is clean — the prompt did its job —
  but the INPUT is not. Solid drawbox plates per `redaction.technique`.
- "Alcohol - Rs 1,000: The Liquor Fort" appears as its own category line. VJ
  ruled: mask it. It stays counted in the denominator.
