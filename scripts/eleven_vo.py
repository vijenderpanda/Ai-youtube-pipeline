#!/usr/bin/env python3
"""
ElevenLabs voiceover for the AI Unpacked pipeline.

- Uses /v1/text-to-speech/{voice_id}/with-timestamps: one call returns audio +
  CHARACTER-level timings, which we group into WORD timings for the karaoke captions.
- Reads ELEVENLABS_API_KEY from repo .env.

Usage:
  # list available voices (name, id, labels) to pick Sol's signature voice
  python3 scripts/eleven_vo.py --list

  # synthesize: text (or --text-file) -> out.wav + out.words.json
  python3 scripts/eleven_vo.py --voice <voice_id> --text "Stop letting Claude Code..." \
      --out channels/claude-tricks/renders/vo_test.wav [--speed 1.08]

words JSON: [{"w":"STOP","start":0.0,"end":0.28}, ...]  (same schema the assembler eats)
"""
import argparse, json, os, subprocess, sys, tempfile
import requests

BASE = "https://api.elevenlabs.io/v1"

def load_key():
    here = os.path.dirname(os.path.abspath(__file__))
    for line in open(os.path.join(here, "..", ".env")):
        if line.strip().startswith("ELEVENLABS_API_KEY="):
            return line.strip().split("=", 1)[1]
    sys.exit("ELEVENLABS_API_KEY not found in .env")

def list_voices(key):
    r = requests.get(f"{BASE}/voices", headers={"xi-api-key": key})
    r.raise_for_status()
    for v in r.json()["voices"]:
        lab = v.get("labels", {}) or {}
        tags = " ".join(f"{k}={val}" for k, val in lab.items())
        print(f"{v['voice_id']}  {v['name']:<22} {tags}")

def synth(key, voice_id, text, out_wav, speed=1.0, model="eleven_multilingual_v2",
          stability=0.5, similarity=0.75, style=0.35):
    body = {
        "text": text, "model_id": model,
        "voice_settings": {"stability": stability, "similarity_boost": similarity,
                           "style": style, "use_speaker_boost": True},
    }
    r = requests.post(f"{BASE}/text-to-speech/{voice_id}/with-timestamps",
                      headers={"xi-api-key": key, "Content-Type": "application/json"},
                      json=body)
    if r.status_code >= 400:
        sys.exit(f"!! TTS {r.status_code}: {r.text[:400]}")
    d = r.json()
    import base64
    mp3 = base64.b64decode(d["audio_base64"])
    tmp = tempfile.mktemp(suffix=".mp3"); open(tmp, "wb").write(mp3)

    # char-level -> word-level grouping
    al = d["alignment"]
    chars, starts, ends = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    words, cur, w_start = [], "", None
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append({"w": cur.upper().strip(".,!?"), "start": round(w_start / speed, 2),
                              "end": round(prev_e / speed, 2)})
                cur = ""
            continue
        if not cur:
            w_start = s
        cur += ch; prev_e = e
    if cur:
        words.append({"w": cur.upper().strip(".,!?"), "start": round(w_start / speed, 2),
                      "end": round(prev_e / speed, 2)})

    af = f"atempo={speed}," if speed != 1.0 else ""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp,
                    "-filter:a", f"{af}anull", "-ar", "44100", "-ac", "1",
                    "-c:a", "pcm_s16le", out_wav], check=True)
    wj = out_wav.rsplit(".", 1)[0] + ".words.json"
    json.dump(words, open(wj, "w"), indent=1)
    dur = words[-1]["end"] if words else 0
    print(f">> {out_wav} (~{dur:.1f}s) + {wj} ({len(words)} words)")
    return out_wav, wj

def _norm(w):
    return "".join(c for c in w.upper() if c.isalnum())

def synth_lines(key, voice_id, lines, out_mp3, brk="0.4s",
                model="eleven_multilingual_v2", stability=0.5, similarity=0.75, style=0.4):
    """Render numbered script lines joined by <break/> tags -> mp3 + word timings +
    per-line boundaries. Writes the raw ElevenLabs mp3 (no re-encode, no normalize:
    the master chain in PLAYBOOK sec.3 expects the quiet TTS level)."""
    import base64
    text = f'<break time="{brk}"/>'.join(lines)
    body = {"text": text, "model_id": model,
            "voice_settings": {"stability": stability, "similarity_boost": similarity,
                               "style": style, "use_speaker_boost": True}}
    r = requests.post(f"{BASE}/text-to-speech/{voice_id}/with-timestamps",
                      headers={"xi-api-key": key, "Content-Type": "application/json"}, json=body)
    if r.status_code >= 400:
        sys.exit(f"!! TTS {r.status_code}: {r.text[:400]}")
    d = r.json()
    open(out_mp3, "wb").write(base64.b64decode(d["audio_base64"]))

    al = d["alignment"]
    json.dump(al, open(out_mp3.rsplit(".", 1)[0] + ".alignment.json", "w"))
    chars, starts, ends = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    # char -> word, skipping any <break .../> tag chars the API echoes back into the alignment.
    # A word ENDS at its last SPOKEN char: a trailing '.'/',' carries the pause after the word,
    # so ending on it holds the caption ~0.5s into the break and mis-places the line-out beat.
    words, cur, w_start, last_e, i, n = [], "", None, None, 0, len(chars)

    def flush():
        nonlocal cur
        w = cur.upper().strip(".,!?;:\"'")
        if w:
            words.append({"w": w, "start": round(w_start, 2), "end": round(last_e, 2)})
        cur = ""

    while i < n:
        ch = chars[i]
        if ch == "<":
            j = i
            while j < n and chars[j] != ">":
                j += 1
            flush(); i = j + 1; continue
        if ch.isspace():
            flush(); i += 1; continue
        if not cur:
            w_start = starts[i]; last_e = ends[i]
        cur += ch
        if ch.isalnum() or ch in "'-":
            last_e = ends[i]
        i += 1
    flush()

    # assign words to lines by sequential token match (independent of tag echo)
    bounds, k = [], 0
    for li, line in enumerate(lines):
        toks = [t for t in line.split() if _norm(t)]
        got = words[k:k + len(toks)]
        ok = len(got) == len(toks) and all(_norm(g["w"]) == _norm(t) for g, t in zip(got, toks))
        bounds.append({"line": li + 1, "text": line, "start": got[0]["start"] if got else None,
                       "end": got[-1]["end"] if got else None, "words": len(got), "match": ok})
        k += len(toks)
    dur = words[-1]["end"] if words else 0.0
    wj = out_mp3.rsplit(".", 1)[0] + ".words.json"
    json.dump(words, open(wj, "w"), indent=1)
    return {"duration_s": dur, "words": words, "line_boundaries": bounds,
            "unassigned_words": words[k:], "audio": out_mp3, "words_json": wj}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--voice")
    ap.add_argument("--text"); ap.add_argument("--text-file")
    ap.add_argument("--out")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--style", type=float, default=0.35)
    ap.add_argument("--lines-file", help="JSON array of spoken lines -> mp3 joined by <break/>")
    ap.add_argument("--break-time", default="0.4s")
    a = ap.parse_args()
    key = load_key()
    if a.list:
        list_voices(key); sys.exit(0)
    if a.lines_file:
        if not (a.voice and a.out):
            sys.exit("need --voice and --out with --lines-file")
        res = synth_lines(key, a.voice, json.load(open(a.lines_file)), a.out,
                          brk=a.break_time, style=a.style)
        print(json.dumps({k: v for k, v in res.items() if k != "words"}, indent=1))
        sys.exit(0)
    text = a.text or (open(a.text_file).read() if a.text_file else None)
    if not (a.voice and text and a.out):
        sys.exit("need --voice, --text/--text-file, --out (or --list)")
    synth(key, a.voice, text, a.out, speed=a.speed, style=a.style)
