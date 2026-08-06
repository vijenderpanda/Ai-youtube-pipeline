#!/usr/bin/env python3
"""Generate the 12 'Aaja Ve' scene stills, charref-locked to the approved couple anchor.

Reads SHOTLIST.md still prompts, injects the look-bible couple DNA + negative list,
and runs scripts/leo_ref_gen.py (charref 133/High) per shot, N candidates each.
"""
import re, subprocess, sys, pathlib

HERE = pathlib.Path(__file__).parent
SONG = HERE.parent
ROOT = SONG.parent.parent.parent.parent  # repo root
MODEL = "aa77f04e-3eec-4034-9c07-d0f619684628"  # Kino XL
ANCHOR = SONG / "characters" / "couple_anchor_v2a_1.jpg"
OUT = HERE / "stills"
N_PER_SHOT = 2

# Couple DNA injected into every prompt (guards drift; charref locks the faces)
DNA_MAN = ("the man in his late 20s with a strong defined jawline, short neatly styled swept-back hair "
           "with short sides, clean jawline with the faintest light stubble, no mustache, "
           "very fair North Indian complexion, glowing fair skin, tall athletic build; ")
DNA_WOMAN = ("the woman in her late 20s with a soft oval face, big expressive brown eyes, "
             "very fair luminous Indian complexion, subtle natural glam makeup with soft nude-rose lips, "
             "long dark wavy hair; ")
SOLO_WOMAN = {"S07"}  # her hero shot — never mention the man
SOLO_MAN = {"S02"}    # his close-up profile — never mention the woman
# man-drift negatives (safe: phrased so they don't hit her long hair)
NEG_MAN_DRIFT = ", mustache, handlebar mustache, mullet, shoulder-length hair on a man, 90s hairstyle, long flowing mane on a man"

bible = (SONG / "characters" / "COUPLE-LOOK-BIBLE.md").read_text()
NEG = re.search(r"## Negative prompt\n```\n(.*?)\n```", bible, re.S).group(1).strip()

shots = re.findall(r"### (S\d+) — .*?\n\*\*Framing:\*\* .*?\n\*\*Use:\*\* .*?\n\*\*Still prompt:\*\* (.*?)\n\*\*Motion prompt:\*\*",
                   (HERE / "SHOTLIST.md").read_text(), re.S)
assert len(shots) == 12, f"expected 12 shots, got {len(shots)}"

only = sys.argv[1:]  # optional: pass shot ids (e.g. S07 S10) to regenerate a subset
OUT.mkdir(exist_ok=True)
for sid, prompt in shots:
    if only and sid not in only:
        continue
    if sid in SOLO_WOMAN:
        dna, ref, neg = DNA_WOMAN, SONG / "characters" / "heroine_face_crop.jpg", NEG
    elif sid in SOLO_MAN:
        dna, ref, neg = DNA_MAN, SONG / "characters" / "hero_face_crop.jpg", NEG + NEG_MAN_DRIFT
    else:
        dna, ref, neg = DNA_MAN + DNA_WOMAN, ANCHOR, NEG + NEG_MAN_DRIFT
    full = (dna + prompt.strip())[:1490]  # Leonardo prompt cap safety
    print(f"== {sid} ==", flush=True)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "leo_ref_gen.py"),
                        "--ref", str(ref), "--prompt", full, "--negative", neg,
                        "--model", MODEL, "--num", str(N_PER_SHOT),
                        "--width", "1344", "--height", "768",
                        "--mode", "charref", "--strengthType", "High",
                        "--out", str(OUT), "--label", sid.lower()])
    if r.returncode != 0:
        print(f"!! {sid} FAILED", flush=True)
print("ALL DONE", flush=True)
