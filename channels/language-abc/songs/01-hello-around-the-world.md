# Episode 1 — "Hello Around the World"

> Flagship / hero video. It states the whole channel promise in one shareable piece: **say hello in 5 languages** with Poly. Teaches greetings in EN · ES · FR · DE · HI.
> Format: Pipeline A. English sung bed (Suno Pro) + **verified spoken greetings (ElevenLabs)** layered in. ~2:15–2:45.

## Target keywords
`hello song for kids`, `say hello in different languages`, `hello in spanish/french/german/hindi for kids`, `greetings song`, `hola bonjour hallo namaste`, `multilingual songs for children`.

---

## Lyrics (original)

**[Spoken intro — Poly, warm]**
> "Hi friends! I'm Poly the Parrot. Today we're going to say **HELLO**… all around the world! Ready? Let's fly!"

**[Chorus]**
Hello, hello, hello!
So many ways to say hello!
Up in my balloon we go —
Let's learn a way to say hello!

**[Verse 1 — English 👋]**
Here at home we smile and say… **"Hello!"** *(hello!)*
Give a great big wave today — **"Hello!"** *(hello!)*

**[Verse 2 — Spanish 🇪🇸]** *(balloon lands in a sunny plaza)*
> *(spoken)* "In Spanish, we say… **¡Hola!**  Can you say it? … **¡Hola!**"
*(sung)* Hola, hola, wave and say — **Hola** means hello today!

**[Verse 3 — French 🇫🇷]** *(a cozy café street)*
> *(spoken)* "In French, we say… **Bonjour!**  Your turn! … **Bonjour!**"
*(sung)* Bonjour, bonjour, off we go — **Bonjour** is the French hello!

**[Verse 4 — German 🇩🇪]** *(a green hillside)*
> *(spoken)* "In German, we say… **Hallo!**  Say it with me… **Hallo!**"
*(sung)* Hallo, hallo, wave hello — **Hallo** is the German hello!

**[Verse 5 — Hindi 🇮🇳]** *(a warm, bright marketplace; Poly presses wings together)*
> *(spoken)* "In Hindi, we say… **Namaste** — and we put our hands together, like this. Try it… **Namaste!**"
*(sung)* Namaste, hands together so — **Namaste** is a kind hello!

**[Bridge — recap, brighter]**
Hello! ¡Hola! Bonjour!
Hallo! Namaste — say some more!
Five ways now, you're in the know —
So many ways to say hello!

**[Chorus out]**
Hello, hello, hello!
Now YOU know how to say hello!
Wave goodbye, but don't be slow —
Come back soon and say… hello!

**[Spoken outro]**
> "Great job, friends! You said hello in **five** languages! Which one is your favorite? See you next time — bye bye! Adiós! Au revoir! Tschüss! Namaste!"

---

## Pronunciation table (verify every row before publish — QC gate)
| Word | Language | Romanization | Notes / TTS |
|---|---|---|---|
| ¡Hola! | Spanish | **OH-lah** | silent H · ElevenLabs ES |
| Bonjour | French | **bon-ZHOOR** | nasal "on", soft "j" · ElevenLabs FR |
| Hallo | German | **HAH-loh** | ElevenLabs DE |
| Namaste / नमस्ते | Hindi | **nuh-muh-STAY** | ElevenLabs HI **+ native check** |

**Production note:** the four spoken greetings are generated as separate ElevenLabs clips (one fixed Poly voice), then muxed into the Suno English bed at the marked spots. This guarantees the *taught* word is always pronounced correctly.

---

## Suno prompt (English bed only)
> Upbeat warm children's sing-along, ~110 BPM, ukulele and light hand percussion with claps, cheerful friendly female lead vocal, playful and bright but not frantic, call-and-response, wholesome and clean. Lyrics: [paste chorus + Verse 1 + bridge + chorus-out; leave gaps where the spoken foreign greetings will be inserted].

Save the Pro track as `channels/language-abc/songs/song01_bed.mp3`; after muxing the TTS greetings, export the final as `channels/language-abc/songs/song01.mp3`.

---

## Shot map (16:9; reuse locked Poly + a few simple locales)
| id | scene | on-screen text |
|---|---|---|
| s00 | Poly waving in balloon, Rainbow Treehouse behind | "Hello Around the World 🌍" (title) |
| s01 | Poly waving, home | **Hello** 👋 |
| s02 | sunny plaza | **¡Hola!** / OH-lah 🇪🇸 |
| s03 | café street | **Bonjour!** / bon-ZHOOR 🇫🇷 |
| s04 | green hillside | **Hallo!** / HAH-loh 🇩🇪 |
| s05 | bright marketplace, hands-together pose | **नमस्ते / Namaste** / nuh-muh-STAY 🇮🇳 |
| s06 | Poly + 5 little flags / rainbow montage | all five words |
| s07 | Poly waving goodbye from balloon | "Bye! 👋" |

Write these into `channels/language-abc/songs/01_shots.json` (same schema as Pip: `{"img":"…","dur":…,"motion":"zoom_in|zoom_out|pan_left|pan_right"}`) once scenes are generated. Keep motion gentle-bouncy.

---

## SEO block
**Title:** `Hello Around the World 🌍 Say Hello in 5 Languages! 👋 | Poly the Parrot (Spanish, French, German, Hindi for Kids)`

**Description (skeleton):**
> Fly around the world with Poly the Parrot and learn to say **hello in 5 languages**! 👋 Perfect first-words fun for toddlers and preschoolers — English, Spanish (¡Hola!), French (Bonjour!), German (Hallo!) and Hindi (Namaste!).
>
> ⭐ Chapters:
> 0:00 Hello! (English)
> 0:xx ¡Hola! (Spanish)
> 0:xx Bonjour! (French)
> 0:xx Hallo! (German)
> 0:xx Namaste! (Hindi)
> 0:xx Say them all!
>
> 👶 A gentle, premium learning song — bright and joyful, never overstimulating.
> 🔔 Subscribe for more first-words songs, the ABCs, counting, colors & more with Poly.
> *(pinned parent comment: "Which language is your little one's favorite? 💛")*

**Tags:** hello song, say hello in different languages, hello in spanish for kids, hola, bonjour, hallo, namaste, greetings song, learn languages for kids, spanish for kids, french for kids, multilingual kids songs, poly the parrot, toddler learning songs, preschool songs.

---

## QC gate (Pip's 7 points + language additions)
- [ ] Poly identical to locked model sheet (no drift)
- [ ] Palette on-brand; no oversaturation
- [ ] No uncanny motion; gentle-bouncy only
- [ ] Song original + on-brand tempo; audio levels safe (no spikes)
- [ ] Thumbnail readable at phone size, one clear emotion, word HUGE
- [ ] **Made for Kids = ON**
- [ ] **Every foreign word matches native pronunciation (checked)**
- [ ] **Romanization correct; Hindi नमस्ते spelled correctly**
- [ ] Framing is "your first words / say hello" (no fluency overclaim)
