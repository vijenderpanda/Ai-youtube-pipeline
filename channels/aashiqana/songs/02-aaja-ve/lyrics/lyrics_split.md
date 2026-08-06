# Aaja Ve — phrase-split alignment source (derivative cuts only)

Same lyric as `lyrics.md`, but every comma-bearing verse/bridge line is split into its two
sung phrases so stable-ts times each phrase independently (playbook §15: a single
`wiperight` sweep across a wrapped 2-line block fills both lines at once and reads wrong).
Romanized and Devanagari are 1:1 line-for-line AND word-count-for-word-count, which is what
`align_karaoke.py`'s chunk-back-by-word-count step requires.

Chorus hook lines are NOT split — "Aaja ve, aaja ve, aaja ve, aaja" is one chant.
`(parenthesised)` female-echo lines are aligned but not displayed; they act as the sink.

## Lyrics (romanized)
[Chorus]
Aaja ve, aaja ve, aaja ve, aaja
Tere bina ye shaam adhoori
Aaja ve, aaja ve, aaja ve, aaja
Mit jaaye bas ye thodi doori
(aaja... aaja...)
Aaja ve, aaja ve, aaja ve, aaja

[Verse]
Sunehri si shaam hai,
par tu yahan nahi
Ye vaadi, ye hawa,
sab hai, bas tu hi nahi
Wine ke do glass rakh ke,
raah teri dekhun
Tu kab aayegi,
main raste hi dekhun

[Chorus]
Aaja ve, aaja ve, aaja ve, aaja
Tere bina ye shaam adhoori
Aaja ve, aaja ve, aaja ve, aaja
Mit jaaye bas ye thodi doori
(aaja... aaja...)
Aaja ve, aaja ve, aaja ve, aaja

[Verse]
Wo shaam yaad hai,
tu laal dress mein thi
Aasmaan se zyada,
tu hi roshan thi
Gulaab tere haathon mein,
main tera ho gaya
Ab door hoon to lagta,
adhoora reh gaya

[Bridge]
Saansein le rahi hain bas tera naam
Tu aa jaaye to poori ho ye shaam

[Chorus]
Aaja ve, aaja ve, aaja ve, aaja
Tere bina ye shaam adhoori
Aaja ve, aaja ve, aaja ve, aaja
Mit jaaye bas ye thodi doori
(aaja... aaja...)
Aaja ve, aaja ve, aaja ve, aaja

[Outro]
Aaja ve, aaja ve, aaja ve, aaja
(aaja... aaja...)
Aaja ve... aaja...

## Lyrics (Devanagari)
[Chorus]
आजा वे, आजा वे, आजा वे, आजा
तेरे बिना ये शाम अधूरी
आजा वे, आजा वे, आजा वे, आजा
मिट जाए बस ये थोड़ी दूरी
(आजा... आजा...)
आजा वे, आजा वे, आजा वे, आजा

[Verse]
सुनहरी सी शाम है,
पर तू यहाँ नहीं
ये वादी, ये हवा,
सब है, बस तू ही नहीं
वाइन के दो ग्लास रख के,
राह तेरी देखूँ
तू कब आएगी,
मैं रस्ते ही देखूँ

[Chorus]
आजा वे, आजा वे, आजा वे, आजा
तेरे बिना ये शाम अधूरी
आजा वे, आजा वे, आजा वे, आजा
मिट जाए बस ये थोड़ी दूरी
(आजा... आजा...)
आजा वे, आजा वे, आजा वे, आजा

[Verse]
वो शाम याद है,
तू लाल ड्रेस में थी
आसमान से ज़्यादा,
तू ही रोशन थी
गुलाब तेरे हाथों में,
मैं तेरा हो गया
अब दूर हूँ तो लगता,
अधूरा रह गया

[Bridge]
साँसें ले रही हैं बस तेरा नाम
तू आ जाए तो पूरी हो ये शाम

[Chorus]
आजा वे, आजा वे, आजा वे, आजा
तेरे बिना ये शाम अधूरी
आजा वे, आजा वे, आजा वे, आजा
मिट जाए बस ये थोड़ी दूरी
(आजा... आजा...)
आजा वे, आजा वे, आजा वे, आजा

[Outro]
आजा वे, आजा वे, आजा वे, आजा
(आजा... आजा...)
आजा वे... आजा...
