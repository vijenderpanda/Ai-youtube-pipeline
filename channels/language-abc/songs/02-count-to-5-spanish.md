# Episode 2 — "Count to 5 in Spanish!" (Uno Dos Tres)

> Tier-1 bilingual video (Build Plan §3): English counting anchor + first Spanish numbers.
> Format: Pipeline A. Suno sung bed; Spanish numbers sung + echoed (QC gate: verify pronunciation; fallback = overlay macOS `say` Spanish voice). ~1:30–2:00.

## Target keywords
`counting song for kids`, `count to 5`, `numbers in spanish for kids`, `uno dos tres song`, `spanish numbers for toddlers`, `learn to count`, `bilingual counting song`.

---

## Lyrics (original)

**[Spoken intro — Poly, warm]**
> "Hi friends! I'm Poly the Parrot. Today we're counting to FIVE — in English AND in Spanish! Ready? Let's count!"

**[Chorus]**
One, two, three, four, five!
Counting makes me feel alive!
Uno, dos, tres — sing it too —
Counting's fun for me and you!

**[Verse 1 — English count, objects appear]**
ONE little balloon floating by the tree,
TWO bright butterflies dancing just for me,
THREE red apples sitting in a row,
FOUR little flowers — watch them grow!
FIVE shiny stars — now count with me: 1! 2! 3! 4! 5!

**[Verse 2 — Spanish 🇪🇸]**
> *(spoken)* "Now let's count in Spanish! Say it with me…"
**UNO!** *(uno!)* — that means one!
**DOS!** *(dos!)* — counting's fun!
**TRES!** *(tres!)* — you're doing great!
**CUATRO!** *(cuatro!)* — can't be late!
**CINCO!** *(cinco!)* — give a cheer — you counted all the way to five!

**[Bridge — both together, brighter]**
One is uno, two is dos,
Three is tres — away we go!
Four is cuatro, five is cinco —
Count in Spanish, now you know!

**[Chorus out]**
One, two, three, four, five!
Uno, dos, tres, cuatro, cinco!
Count them high and count them low —
Come back soon and count some more!

**[Spoken outro]**
> "Great counting, friends! You counted to five in TWO languages! See you next time — bye bye! ¡Adiós!"

---

## Pronunciation table (verify every row before publish — QC gate)
| Word | Language | Romanization | Notes |
|---|---|---|---|
| Uno | Spanish | **OO-noh** | pure vowels, no "yoo" |
| Dos | Spanish | **DOHS** | one syllable |
| Tres | Spanish | **TREHS** | rolled/tapped r ok, soft e |
| Cuatro | Spanish | **KWAH-troh** | "kwa" not "kua-tro" flat |
| Cinco | Spanish | **SEEN-koh** | Latin-Am "s" (not "th") |

Fallback if Suno mispronounces: overlay macOS `say -v` Spanish voice (Paulina/Mónica) clip at that moment.

---

## Suno prompt (style line)
> Upbeat warm children's sing-along, ~110 BPM, ukulele and light hand percussion with claps, cheerful friendly female lead vocal, playful and bright but not frantic, call-and-response, wholesome and clean, bilingual English Spanish kids counting song.

Save Pro track as `channels/language-abc/songs/song02.mp3`.

---

## Shot map (16:9; locked seed 1664045002, flat style, feature-lock string)
| id | scene | on-screen text |
|---|---|---|
| s00 | reuse `s00_treehouse_v2_0.jpg` — title | "Count to 5 in Spanish! 🔢" |
| s10 | Poly pointing at ONE red balloon by treehouse | **1 · Uno** / OO-noh |
| s11 | Poly with TWO butterflies, sunny meadow | **2 · Dos** / DOHS |
| s12 | Poly with THREE red apples in a row | **3 · Tres** / TREHS |
| s13 | Poly with FOUR flowers on hillside | **4 · Cuatro** / KWAH-troh |
| s14 | Poly with FIVE stars, evening sky (warm, not dark) | **5 · Cinco** / SEEN-koh |
| s15 | Poly cheering, numbers 1-5 confetti recap | all five |
| s06 | reuse goodbye scene | "¡Adiós! 👋" |

Shots → `songs/02_shots.json`; motion clips via `leo_motion.py` like EP01.

---

## SEO block
**Title:** `Count to 5 in Spanish! 🔢 Uno Dos Tres Counting Song for Kids | Poly the Parrot`

**Tags:** counting song, count to 5, numbers in spanish for kids, uno dos tres, spanish numbers song, learn to count, counting for toddlers, bilingual kids songs, spanish for kids, numbers song, poly the parrot, toddler learning songs, preschool songs, first words in spanish.

**Chapters:** 0:00 Let's count! · English 1–5 · Spanish uno–cinco · Count together · ¡Adiós!

---

## QC gate
- [ ] Poly identical to locked master (no drift)
- [ ] Palette on-brand; flat 2D look holds
- [ ] Gentle-bouncy motion only
- [ ] Audio levels safe
- [ ] Thumbnail: word/number HUGE, readable phone-size
- [ ] Made for Kids = ON
- [ ] All 5 Spanish numbers pronounced correctly (verified)
- [ ] Romanization correct
- [ ] "First numbers" framing, no fluency overclaim
