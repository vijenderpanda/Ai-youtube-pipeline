# Aaja Ve — short_payoff hook bar

**Decision: cold-open at `67.61s`, run `29.61s` to `97.22s`.**
That is **chorus 2**, the spec's *fallback* — not the default 151.88.

`ffmpeg -ss 67.61 -t 29.61`

---

## Why not the default (151.88)

The 151.88 prior is not an onset. A 20 ms RMS + voiced-ratio envelope on the demucs
vocal stem shows **unbroken voiced energy from before 151.30 through 152.24** at
−17 to −21 dB with a voiced ratio of +12 to +16 dB. That is the held vowel of the
bridge's last line, *"Tu aa jaaye to poori ho ye shaam"* (ends 151.66), plus its
reverb tail. There is no step at 151.88 — the number is fiction, exactly the case
step 3 of the brief says to catch.

Re-scanning finely put the real chorus-3 attack at **152.36s**, 0.48 s later. That
does not rescue it:

- The only gap near it is the 80 ms notch at 152.28–152.34. A guard pre-roll in the
  mandated 0.10–0.20 s range **cannot fit**, so frame zero would land on the previous
  phrase's reverb tail no matter what.
- The mix has **no downbeat here at all**. It is a smooth bridge crescendo — −20 dB at
  151.64 rising continuously to −8.7 dB at 152.02. There is no transient to cut on.
- It is also **1.1 dB quieter** than 68.20 in the mix (−14.20 vs −13.10 mean).

The "lands straight off the bridge climax" appeal is genuine, but that climax is
precisely what makes frame zero un-cuttable.

## Why 68.20 wins

It is the loudest of the three qualifying chorus instances *and* the only one with a
clean frame zero:

| | mix mean | mix peak | vocal mean | true onset | prior error |
|---|---|---|---|---|---|
| 4.08 (excluded) | −14.80 | −3.80 | −15.00 | — | — |
| **68.20** | **−13.10** | **−2.60** | **−15.10** | 68.16 | −0.04 s |
| 151.88 | −14.20 | −3.00 | −16.10 | 152.36 | +0.48 s |

The onset structure at C2 is textbook:

| time | event | evidence |
|---|---|---|
| 67.42–67.74 | inter-phrase drop | stem −24…−33 dB; prior line ends 67.48 and is fully decayed |
| **67.61** | **frame zero** | mix −19.9 dB, stem −32 dB — no tail crosses it |
| 67.76 | **full band slams in** | **+10.87 dB** mix step in one 20 ms frame, to −6.5 dB |
| 67.78 | singer's breath | stem −29.7 → −21.2 dB in two frames; voiced ratio **negative** (HF noise) |
| 68.16 | voiced **"Aa-"** | voiced ratio flips −12.5 → +3.6 dB; syllable intact, unclipped |

This is the structure `PRODUCTION-PLAYBOOK` line 323 prescribes — *open on the
percussive transient, hook word lands immediately after, reads deliberate instead of
clipped*. The 0.15 s guard is placed to protect **the 67.76 downbeat**, not the vocal:
guarding the vocal instead would put frame zero at 67.96, mid-decay of the band hit,
which is the one genuinely bad place to cut.

It resolves through **"Tere bina ye shaam adhoori"** at 73.40s — 5.79 s in.

## Judgment calls

1. **Took the fallback over the default.** The default failed the non-negotiable ear
   check; the fallback passed cleanly. No §4b exception is needed and none is claimed —
   `exception: false`.
2. **Guard protects the band downbeat, not the vocal onset.** `chosen_start_s` is
   `67.76 − 0.15`, not `68.16 − 0.15`. Rationale above.
3. **Out-point 97.22** is the quietest frame (−23.4 dB) inside the allowed 29.5–30.0 s
   band, in a micro-gap right before a new phrase hits at 97.40. The 88.74–97.22
   stretch has no karaoke line but is **not** dead air — the stem averages −16.75 dB
   there (wordless ad-libs over a full band).
4. **`scripts/hook_finder.py` is still absent.** Per the brief I did not wait for it and
   did not build it; the Aug-5 Baarish `hook_scan.py` method was copied verbatim, then
   the ear check was escalated from the allowed 0.1 s fine hop to a 20 ms envelope with
   a voiced/unvoiced ratio, because RMS alone cannot tell a reverb tail from an attack —
   which is the whole reason 151.88 fell over.

## Handoff

Cut arrives at **−12.3 LUFS / −1.5 dBTP / LRA 1.6** → needs ≈ **−1.7 LU**, two-pass
`loudnorm` to −14 LUFS / −1.5 TP on the lossless wav before muxing.

§4b rule 1 is satisfied structurally: the live Short (`youtu.be/TMVJHHv7v4c`) opens at
3.6 s on the **opening** chorus; this cut opens at 67.61 s on **chorus 2**. Rules 2–4
(visual grammar, re-alignment, metadata) remain the downstream assets' burden.

Probes for re-listening: `short_payoff/probes/` — `c2_67.61_*` (chosen),
`c1_151.88_*` and `c1_onset_152.36_*` (rejected), mix and vocal stem for each.
