# Build Plan — "Rumble Trucks" (Vehicles)

> Pipeline **A (kids music video)**, Made-for-Kids = YES. Inherits the network doctrine (`README.md`) + hybrid motion (~$1.35/video). This doc = the deltas for a high-energy vehicle channel.
> Uploader key: `vehicles` → `secrets/token_vehicles.json` (`python3 scripts/yt_upload.py --channel vehicles --auth`).

## 1. ⚠️ Blocker
Visual generation (Rev + cast + Rumble Town) is on **Leonardo, which is out of tokens**. Everything below that isn't image-gen (naming, brand, songs, SEO, lyrics) can proceed now; **top up Leonardo to generate the trucks.**

## 2. Content strategy — the discovery engine
Two pillars, front-load the searchable one:
1. **Single-vehicle hero songs (discovery):** each targets a huge evergreen query — **excavator, garbage truck, fire truck, monster truck, dump truck, digger, police car, tow truck, cement mixer, school bus.** These are the search magnets.
2. **Cast / Rumble Town adventures (brand):** the trucks team up, race, help the town — builds the returning-audience moat.
> Ratio early on: ~70% single-vehicle hero songs, ~30% cast songs. Every video still stars the branded cast (Rev & friends), so even a "garbage truck song" is *our* garbage truck (Dot's friend), not a stock truck.

## 3. SEO (kids-vehicle specifics)
- **Title = vehicle keyword FIRST + energy + brand:** e.g.
  `Monster Truck Song 🚗💨 Rev's Big Jump! | Rumble Trucks` ·
  `Excavator Song 🚜 Dig Dig Dig! for Kids | Rumble Trucks`
- Vehicle sound-words in titles/tags (vroom, beep, dig, honk) — toddlers/parents search them.
- Compilations (30–60 min "Truck Songs for Kids") = the watch-time/RPM driver. Playlists per vehicle type = autoplay engine.

## 4. Money math
Kids RPM ~$0.30–1 (COPPA). Levers: **compilations + playlists + 24/7 potential**, and **multi-language dub fan-out** later (vehicle sounds are universal → easy localization). Same ~$1.35/video hybrid-motion cost.

## 5. Flagship + first songs
1. **Ep1 — "Rev the Monster Truck"** (`songs/01-rev-the-monster-truck.md`) — establishes the star + the high-energy sound; monster trucks are both on-brief *and* high-search.
2. Ep2 — Excavator (Digs) · Ep3 — Fire Truck (Bo) · Ep4 — Garbage/Dump (Dot) — the high-search work vehicles.

## 6. First 30 days
- **Week 1:** lock name/handle (@RumbleTrucks) + this brand core. **Top up Leonardo** → generate **Rev** (lock master + seed) → then Dot/Digs/Bo/Zip + Rumble Town scenes.
- **Week 2:** build Ep1 (Rev) — song (Suno Pro) → scenes → hybrid motion → thumbnail → QC. Create the YouTube channel (via Chrome) + authorize (`--channel vehicles --auth`).
- **Week 3–4:** batch Ep2–Ep4 (excavator/fire/garbage), first compilation, playlists; publish on a fixed cadence.

## 7. QC gate additions
- [ ] No windshield-eyes / no *Cars* resemblance (front-face only)
- [ ] Character on-model (color + silhouette) across all shots
- [ ] Energetic but **not** scary (no violent crashes); audio spikes safe
- [ ] Made-for-Kids ON
