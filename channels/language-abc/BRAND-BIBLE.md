# Brand Bible — "Learn with Poly" (Language / ABC channel)

> **Channel name (locked): "Learn with Poly"** · handle target **@LearnWithPoly** · **Mascot: Poly the Parrot**.
> ("Learn" = high-intent SEO keyword; mascot carries the brand.)

> **Working name — confirm before launch** (check YouTube handle + a light trademark search, same as we did for Pip).
> Positioning in one line: **the warm, premium early-learning channel where a friendly parrot teaches the ABCs, numbers, and colors — and your child's *first words* in Spanish, French, German & Hindi — through original singable songs.**

---

## 1. The wedge (why this beats the flooded "ABC song" market)
The alphabet/phonics niche is enormous but generic and English-only. Two moves make us un-templated:
1. **Multilingual from day one.** Almost no premium kids channel teaches *first words in several languages* well. This is a real, under-served parental demand (bilingual-curious families, immigrant families, "expose them early" parents).
2. **Warm, not frantic.** We carry Pip's premium DNA into an *upbeat* register: bright and bouncy, but never the strobe-cut "crack-cartoon" look. Parents who reject Cocomelon overstimulation but still want *learning* have nowhere premium to go. That's us.

The multilingual angle is also our **built-in scale lever** — the same production fans out into 5 language markets (see BUILD-PLAN §3).

---

## 2. Mascot — **Poly the Parrot**
**Why a parrot:** parrots *mimic speech* — the perfect metaphor for "hear it, repeat it, learn it." Colorful = thumbnail pop. Simple round shape = easy AI consistency. Merch-friendly.
**Why "Poly":** triple hook — **Polly** (classic parrot name) + **poly**glot (many languages) + works phonetically in ES/FR/DE/HI. Ownable and self-explaining.

**Design spec (lock this for AI consistency):**
- Small, **round** body; **big friendly eyes**; short curved beak; tiny feet.
- **Signature crest = 3 rainbow feathers** on the head → strong silhouette, reads at thumbnail size, ties to the "Rainbow Treehouse" world.
- **Storybook 2D illustration** — soft shading, thick clean outlines, gentle gradients. **Not** 3D/Pixar, not photoreal.
- Fixed proportions: head ≈ 40% of body, oversized eyes, small wings that read as "hands" for waving/pointing.
- Always cheerful, gentle, encouraging — never manic.

**Supporting cast (recurring, keeps it feeling like a *show*):**
- **Alba** — a soft-grey baby owl, Poly's shy student (the "learner" kids identify with).
- **Mango** — a round orange kitten, the playful one.
Keep the cast tiny (consistency cost). Introduce only after Poly is locked.

---

## 3. World — **Poly's Rainbow Treehouse**
Home base = a cozy treehouse with a rainbow-striped roof. For multilingual episodes, Poly travels in a **little hot-air balloon** to simple, warm, stylized locales (a sunny plaza, a café street, a green hillside, a bright marketplace). Travel = a natural, kid-legible reason each language appears. Keep locales few and reusable.

---

## 4. Look & palette (warm-premium, not garish)
Slightly-desaturated, warm versions of bright colors. Avoid a wall of saturated primaries (that's the "crack" look).

| Role | Hex |
|---|---|
| Poly body (teal) | `#2FB6A8` |
| Poly belly (sunny yellow) | `#FFD24C` |
| Coral accent | `#FF7A5A` |
| Cream background | `#FFF4E0` |
| Soft sky | `#BFE3E0` |
| Sage (treehouse) | `#9CC7A6` |
| Ink (text/outlines) | `#2B3A42` |
| Rainbow crest | red→orange→yellow→green→blue, gentle tones |

**Motion / energy rule:** *bright and bouncy, never frantic.* Gentle-forward Ken Burns, soft bounces on beat, crossfades — **no** rapid strobe cuts, **no** hyper-zoom. (This is why the existing `assemble_video.py` works as-is for this channel — no engine change needed, unlike Vehicles.)

**Typography:** big, round, friendly sans (Fredoka / Baloo / Quicksand family). Huge target word, generous spacing.

---

## 5. Song style guide
- Upbeat warm children's sing-along, **~100–115 BPM**.
- Ukulele + light hand percussion + claps; cheerful, clear, friendly **lead vocal**.
- Heavy **repetition + call-and-response** ("Can you say it? ... ").
- Singable 4-line hooks. Bright but wholesome — **not** EDM, not frantic.
- **One consistent Poly voice** across the channel (part of the brand — see §7).

---

## 6. The multilingual system (our differentiator — get this right)
**Languages:** English (anchor) · Spanish · French · German · Hindi.

**Teaching method — *Hear → See → Repeat → Sing*:**
1. **Hear:** Poly *says* the target word clearly (spoken, pronunciation-verified — see §7).
2. **See:** on-screen the word appears **large + romanization + a small picture/flag**.
3. **Repeat:** a short pause / echo ("Your turn!") for the child to say it.
4. **Sing:** the word folds into the song's hook.

**On-screen text rules:**
- Target word is the biggest thing on screen; always show **romanization** underneath (for parents).
- **Hindi shows both scripts:** `नमस्ते / Namaste`.
- A small flag / place motif for color only — no geography lesson, no politics.
- Early videos teach **1–3 target words max** — don't overload toddlers.

**Don't-overreach rule:** we teach *first words and joyful exposure*, not fluency. Framing everywhere: "your first words in…", "say hello in 5 languages!" — never "become fluent."

---

## 7. Pronunciation QC — **the one non-negotiable gate**
A language channel that mispronounces its own lesson is dead on arrival with parents. Rules:
- **Every non-English word is verified against a native reference before publish.**
- **Lean tooling:** the *taught foreign word* is delivered as a **spoken TTS clip** (ElevenLabs multilingual free tier for ES/FR/DE), layered into the song — so we never gamble the exact teaching moment on Suno's singing pronunciation.
- **Hindi:** verify natively (you can likely QC this yourself) and/or ElevenLabs Hindi.
- Suno sings the **English connective tissue + chorus**; foreign greetings are **spoken + echoed**, not sung, in early episodes.
- **Poly's spoken voice = one fixed ElevenLabs voice** (warm, clear, friendly). Consistency = brand.

**QC checklist addition (on top of Pip's 7-point gate):**
- [ ] Every foreign word matches native pronunciation (checked against reference)
- [ ] Romanization spelled correctly; Hindi Devanagari correct
- [ ] "First words / say hello"-style framing (no fluency overclaim)

---

## 8. Thumbnails
Bright warm background · one big happy Poly · the **target word or letter HUGE** · ≤3 words · a small flag/emoji cue on language videos. Test 2 variants (A/B).

## 9. Compliance
**Made-for-Kids = ON** (disables comments + personalized ads — mandatory). Educational, safe, gentle. No scary imagery, no sudden loud audio.

---

## 10. The locked recipe (fill the seed once Poly is generated)
- **Image model:** Leonardo **Lucid Origin** — `7b592283-e8a7-4c5a-9ba6-d18c31f258b9` (same as Pip; consistency via **prompt + fixed seed**, since Lucid Origin has no img2img/char-ref).
- **Character portrait:** 1024×1024. **Scenes:** 16:9 (e.g. 1536×864 or upscale to 1920×1080).
- **Seed:** `1664045002` (generation-level, from the first Poly batch `poly_v1_*` — reproducible; reuse as `leo_generate.sh` 9th arg).
- **Canonical master = LOCKED:** `assets/character/canonical/poly_master.jpg` (from `poly_v1_2.jpg`). Front-facing, teal body / yellow belly / coral cheeks / short yellow beak / big black eyes / 3 rainbow feathers. Anchor every scene to this.
- **Base style tokens (LOCKED — the FLAT look is what holds consistency):** `flat 2D children's book illustration, bold flat color fills, thick uniform dark outlines, minimal flat shading, no gradients, clean vector look, warm palette, cheerful, wholesome`. ⚠️ Lead every prompt with FLAT — "soft shading / gradients" drifts Lucid Origin into a painterly 3D look and breaks the character.
- **Poly feature lock (repeat in every prompt):** `teal body, big yellow oval belly, two round coral cheeks, short yellow curved beak, big simple round black eyes, a crest of exactly three rainbow feathers red yellow and blue`.
- **Negative (LOCKED):** `3d render, pixar, photoreal, realistic, painterly, soft gradient shading, glossy, volumetric lighting, neon, oversaturated, scary, deformed beak, extra limbs, blurry, eyelashes, many feathers, extra feathers, text, watermark`.
- **Scene workflow:** generate **2 per shot** at **1344×768**, seed **1664045002**, keep the on-model one (QC vs master). Proven establishing shot: `assets/scenes/s00_treehouse_v2_0.jpg`.
- **Palette:** §4 hex values.

*Living document — lock the working name + seed first, then batch content.*
