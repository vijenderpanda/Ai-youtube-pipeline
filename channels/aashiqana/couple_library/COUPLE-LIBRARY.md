# Aashiqana — Couple Library

> A casting library of **original AI couples**, one couple per folder, each locked to a
> distinct **vibe**. When a new song is written, you read its mood/theme and **pick the
> couple folder whose tags match** — instead of re-generating a couple from scratch every
> time. Faces are **consistent within a folder**; the folder's vibe = its setting, palette,
> wardrobe and grade.
>
> Primary use: **long-form music videos**. Every shot is framed so it can be **re-cut into a
> Short** (9:16-safe composition, hook-worthy face in frame). The **heroine ("girl") shots
> are the hook** — they are the frames that stop the scroll and make someone play the Short.

---

## 1. Engine (locked 2026-08-06)

**Leonardo.ai → Nano Banana 2** (Google's latest image model), driven in Chrome on the free
web-token pool (~31.7K tokens; **80 tokens / image** at Small 848×1264).

- **Why not the old Kino XL + charref:** Kino XL renders read generic/late-20s and drift
  (mustache/hair rerolls logged in QUALITY-LEDGER). Nano Banana 2 is dramatically more
  photoreal for "hot" faces **and** carries identity across shots via **Image Ref** (image
  guidance) instead of a fragile controlnet.
- **Consistency method:** cast ONE anchor two-shot → lock it → attach the anchor (plus a
  hero face-crop and a heroine face-crop) as **Image Ref** on every subsequent shot. Same
  faces, new pose/framing/setting.
- **Compliance spine (unchanged):** original AI couple, **no celebrity likeness**, fair &
  unmistakably Indian, synthetic-media disclosure ON at upload. See BRAND-BIBLE §2.
- Prompt Enhance = **Off** (exact prompt control). Private Mode = **On**.

Fallback engine if the pool runs dry or NB2 is gated: Kino XL + Character Reference @ Mid
(the old recipe, still in `songs/02-aaja-ve/characters/`).

---

## 2. The 5 vibes (folder = couple = vibe)

Each couple is a different pair of faces, cast to suit that vibe. Pick by matching a song's
mood to the **`best_for` tags**.

| Folder | Codename | Palette / world | Emotional register | Cast to fit songs about… |
|---|---|---|---|---|
| `couple_01_monsoon` | **Monsoon** | rain, wet night street, teal-blue + warm amber | longing, intense, aching | rain first-love, separation, "come back", obsessive love, sad ballad |
| `couple_02_goldenhour` | **Golden Hour** | fields / hilltop / dusk, warm amber haze | hopeful, tender, yearning | new love, "aaja ve", waiting, soft happy love |
| `couple_03_midnight` | **Midnight** | rooftop / city neon, moody low-key, bokeh | modern, sensual, Gen-Z intense | Saiyaara-energy, night drives, desire, toxic-but-can't-leave |
| `couple_04_cafe` | **Café** | cozy indoor, fairy lights, rain on window | cute, warm, playful intimacy | crush, first date, comfort love, "you're home" |
| `couple_05_seaside` | **Seaside** | beach / sea at golden dusk, breezy, airy | free, joyful, dreamy | travel love, freedom, wedding-teaser joy, escape-together |

> Rule of thumb: **1** = heartbreak/rain, **2** = warm yearning, **3** = night/desire,
> **4** = cute/cozy, **5** = joyful/free. Between them they cover ~every Aashiqana song mood.

Status (2026-08-06): **ALL 5 COUPLES LOCKED.** couple_01 Monsoon = stills + 3 motion clips;
couples 02 Golden Hour, 03 Midnight, 04 Café, 05 Seaside = 12-shot stills sets each (heroine
hooks + couple + hero) + anchor + face refs + couple.meta.json. Every couple is a distinct
fair, mid-20s, unmistakably-Indian pair. Anchors 02–05 were auto-picked (user may swap any).
Total spend ≈ 8K of the free web-token pool.

**Two-tier policy (user, 2026-08-06):**
1. **Base library (now):** each couple folder holds the locked anchor + a small consistent
   stills set (heroine-weighted hooks + couple + hero). This is the casting pool.
2. **Per-song extras (later, at production):** when a specific song's Short/long-form goes
   into production, read the lyrics and generate **2–3 new stills + motion** for the chosen
   couple, tailored to that song's beats. Motion is generated per-song, not stocked up front
   (couple_01's 3 clips were the workflow proof).

---

## 3. Metadata schema (`couple.meta.json` per folder)

Every couple folder carries a `couple.meta.json`. The **`tags`** block is what you grep/scan
to pick a couple for a song. Keep tag vocabulary consistent across folders.

```jsonc
{
  "id": "couple_01",
  "codename": "Monsoon",
  "status": "locked | wip",
  "engine": "leonardo/nano-banana-2",
  "created": "2026-08-06",
  "refs": {                      // the identity lock — attach these as Image Ref
    "anchor": "faces/couple_anchor.jpg",
    "hero_face": "faces/hero_face.jpg",
    "heroine_face": "faces/heroine_face.jpg"
  },
  "look": {
    "heroine": "verbatim attribute string reused in every heroine prompt",
    "hero": "verbatim attribute string reused in every hero prompt",
    "world": "palette + grade + lens line appended to every prompt"
  },
  "tags": {
    "vibe": ["monsoon","rainy-night","longing"],
    "mood": ["heartbreak","yearning","intense","romantic-tension"],
    "palette": ["teal-blue","amber","low-key","moody"],
    "time_of_day": "night",
    "season": "monsoon",
    "location": ["rain street","under umbrella","cafe window","balcony"],
    "tempo_fit": ["slow","mid"],
    "energy": "melancholic-intense",
    "wardrobe": ["dark","layered","wet-look"],
    "best_for": ["rain first-love","separation","obsessive love","sad ballad","come-back"]
  },
  "shots": [ /* filled from the shot-set recipe, §4 */ ],
  "compliance": "original AI, fair & unmistakably Indian, no celebrity likeness, synthetic disclosure ON"
}
```

---

## 4. Standard shot-set recipe (every couple folder gets this)

Girl-forward (the **hook** frames — heroine is the scroll-stopper). Portrait 2:3 → crops to 9:16.

| Code | Shot | Frame | Motion-ready? |
|---|---|---|---|
| `G1` | Heroine hero close-up, eyes to camera/lost in thought | 2:3 | ✅ hair, breath, slow push-in |
| `G2` | Heroine 3/4 turn, hair in motion | 2:3 | ✅ hair/wind |
| `G3` | Heroine looking back over shoulder | 2:3 | ✅ turn |
| `G4` | Heroine environmental / wide in the vibe | 2:3 or 16:9 | ✅ ambient (rain, walk) |

Couple:

| Code | Shot | Frame | Motion-ready? |
|---|---|---|---|
| `C1` | Couple anchor two-shot (foreheads / embrace) | 2:3 **+** 16:9 | ✅ subtle push-in |
| `C2` | Couple walking / holding hands | 16:9 or 2:3 | ✅ walk |
| `C3` | Couple face-to-face, almost-kiss | 2:3 | ✅ lean-in |
| `C4` | Hero solo (for balance / cutaways) | 2:3 | ✅ |

- **`faces/`** = the identity lock (anchor + hero_face + heroine_face crops).
- **`shots/`** = the stills above (final, on-model).
- **`motion/`** = image→video clips generated from the ✅ stills (Leonardo Video / Hailuo;
  subtle motion only — brand rule). These feed both long-form and Shorts cuts.

Naming: `01_G1_heroine_closeup.jpg`, `05_C1_anchor_twoshot_16x9.jpg`, etc. Keep the code in
the filename so the editor can grab "all G shots" or "all motion clips" fast.

---

## 5. How to pick a couple for a new song (30-second ritual)

1. Read the song's hook + theme; name its **mood** in one word (heartbreak? yearning? desire? cute? free?).
2. Match to §2's rule-of-thumb → open that folder's `couple.meta.json`, confirm `best_for`.
3. That couple's `refs/` are your Image Refs; that folder's `look.world` is your grade line.
4. Generate any missing song-specific shots on-model from the refs; assemble.
5. If two songs reuse the same couple, that's fine — it becomes "their story continues"
   (BRAND-BIBLE §4), as long as §4b anti-templating (re-grade/re-frame reused frames) holds.

---

## 6. Cost & cadence

- Casting a couple ≈ 4 anchor candidates (320 tok) + ~10 locked shots (≈800 tok) ≈ **~1.1K tokens/couple**.
- All 5 couples ≈ **~6K tokens** — comfortably inside the free web pool.
- Motion clips are the expensive part (Leonardo Video) — generate on demand per song, not up front.
