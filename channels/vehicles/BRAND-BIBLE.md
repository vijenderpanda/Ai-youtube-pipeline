# Brand Bible — "Rumble Trucks" (Vehicles channel)

> **Working name (confirm handle @RumbleTrucks + light trademark check).** Audience: **kids (Made-for-Kids)**. Mascot-forward, high-energy.
> One line: **the high-energy vehicle-friends music show** — a cast of truck characters in **Rumble Town** singing big, catchy, rock-powered songs about diggers, fire trucks, monster trucks & more.

---

## 1. The wedge
Vehicle content is one of the **biggest** toddler niches (excavator / garbage-truck / fire-truck / monster-truck searches are enormous). But most of it is **generic** — stock 3D trucks, no characters, no brand. Our wedge:
- A **branded CAST** of vehicle characters with personalities + a **world (Rumble Town)** + **original high-energy songs**. The un-templated core = *the characters + the world + the sound* (same doctrine as Pip/Poly).
- **Energy is the point.** This is the hyper-active lane (opposite of Pip's calm) — but kept **premium** via consistent characters, catchy original songs, and a cohesive look. Bright, punchy, fun — energetic, not frantic-ugly.
- **Bonus:** vehicles are **rigid shapes** → *easier for AI to keep consistent and animate* than organic characters. This lane actually plays to the toolchain's strengths.

## 2. ⚠️ IP SAFETY (non-negotiable)
- **Original characters only.** NO Pixar *Cars* characters, names, or trade dress.
- **Face design = round headlight-EYES + friendly grille/bumper-MOUTH on the FRONT of the vehicle.** Do **NOT** put eyes on the windshield — windshield-eyes is Pixar *Cars*' signature trade dress. Front-face (headlight eyes) is the classic, safe, distinct look.
- **No Disney/Pixar music** — all songs original (Suno Pro, commercial license).
- Generic vehicle *types* (monster truck, excavator, fire truck) are fine; real-world brands/logos are not.

## 3. Mascot + cast — "the Rumble Trucks"
Keep to 4–5 for consistency. Each = one bold hero color + one clear personality + strong silhouette.
- **Rev** ⭐ — a cheerful **RED monster truck**, big chunky wheels, the energetic leader. ("Let's rumble!")
- **Dot** — a friendly **YELLOW dump truck**, helpful and sweet.
- **Digs** — an **ORANGE excavator**, curious/playful (loves to dig).
- **Bo** — a brave **RED-&-WHITE fire truck** (ladder, siren).
- **Zip** — a small **GREEN race car**, fast and cheeky.

**Design spec (AI consistency):** bold simple shapes, **thick clean outlines, flat 2D + soft shading**, **big round headlight-eyes**, smiley grille-mouth, one signature color each, consistent proportions (chunky, toy-like, huggable). Lead prompts with FLAT tokens + fixed seed (network standard).

## 4. World — **Rumble Town**
A sunny, bright town with recurring settings so every video feels like the same show: a **construction site** (dirt hills, cones, ramps), **roads/streets**, a **fire station**, a **garage/clubhouse**, a **race track**.

## 5. Look & palette
Bright, **curated-saturated** (energetic, not garish): each truck a bold hero color; warm sunny sky; blue-grey roads; earthy construction browns; safety orange/yellow accents. Thick outlines, flat 2D but punchy. *(Lock hex when we generate the cast.)*

## 6. Motion / energy rule
**HIGH energy** — bouncy, fast-but-readable, engine bobs, wheel spins, dust puffs, beat-synced jumps. Snappier cuts than Pip/Poly. Still premium: **no frantic strobe, no scary crashes**. Hybrid motion (Motion 2.0 heroes + Ken Burns), ~$1.35/video.

## 7. Song style
**High-energy kids rock/pop:** driving drums, electric-guitar riffs, big singalong choruses, engine/horn SFX, **~120–140 BPM**. Fun, powerful, "feel the rumble." Repetition + call-and-response + vehicle sounds (vroom, beep, *dig dig dig*). Suno **Pro** (commercial). This is the "Cars-movie truck energy" the channel is built on.

## 8. Thumbnails
Bright, **one big hero truck** (Rev, or the episode's star) mid-action, dust/motion, ≤3 huge words, high contrast. Action energy at phone size.

## 9. Compliance
**Made-for-Kids = ON.** Positive & safe — friendly trucks, no violence/scary wrecks, no sudden loud spikes.

## 10. Locked recipe
- **Image model:** Leonardo **Lucid Origin** (network standard) — lead **FLAT** prompts + **fixed seed** for consistency (rigid vehicle shapes make this easier).
- ⚠️ **BLOCKED: Leonardo API tokens EXHAUSTED** — top up before generating Rev + the cast + Rumble Town scenes.
- **Rev canonical master = LOCKED:** `assets/character/canonical/rev_master.jpg` (from `rev_v1_1`). **Seed `1946430917`**, Lucid Origin, 1024². Front headlight-eyes + grille-mouth (IP-safe, no windshield-face). Reuse seed + flat tokens for the rest of the cast + scenes.
- **Negative (draft):** `windshield eyes, eyes on windshield, pixar cars, realistic, 3d render, photoreal, scary, broken, crash, neon, text, watermark`.

*Living document — lock name/handle + generate Rev first, then batch.*
