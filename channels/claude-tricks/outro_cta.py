#!/usr/bin/env python3
"""Spoken series-CTA for the outro card (subscriber-conversion experiment,
2026-08-13). The Ep11 question-card outro is TEXT-ONLY; the channel converts at
0.34 subs/100 top-shelf views. This adds Sol SPEAKING a series CTA over the
card, teasing the NEXT planned episode when the factory calendar has one:

    "Tomorrow: <next episode tease> — follow so it finds you."

falling back to the series promise when the calendar is empty/unreachable:

    "One thirty-second Claude trick, every day — follow so the next one finds you."

RULES (locked by the brief):
  - Payoff first: this line exists ONLY in the outro segment, never earlier.
  - The tease names the next PLANNED/QUEUED factory_calendar item for this
    channel (kind=content), excluding the episode being built itself.
  - Loudness: the returned gain_db puts the VO's integrated loudness on the
    channel's -14 LUFS spine so the whole delivered file stays within the
    finalize QC band (-14 ±0.5, see scripts/finalize_episode.py).

Activation is per-episode via `outro_cta` in the spec (see build_ep_v2.py) —
ABSENT by default, so the locked Ep11/Ep12 templates are untouched until VJ
approves the treatment.

CLI (dry-run the composed line without spending TTS credits):
  python3 channels/claude-tricks/outro_cta.py --dry [--exclude-title "..."]
  python3 channels/claude-tricks/outro_cta.py --ep 33   # compose + synth
"""
import argparse, datetime, json, os, re, subprocess, sys

CH = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(CH))
sys.path.insert(0, os.path.join(REPO, "scripts"))

CHANNEL_KEY = "claude-tricks"
TEASE_TMPL = "Tomorrow: {tease} — follow so it finds you."
FALLBACK_LINE = ("One thirty-second Claude trick, every day — "
                 "follow so the next one finds you.")
# Friday = the learning-and-building series slot (VJ directive 2026-08-13):
# no daily Short on Fridays; the Thursday episode's outro hands off to the
# series instead. Named variant when a Friday chapter is already planned.
FRIDAY_TMPL = ("Tomorrow is Friday — we build: {tease}. "
               "Meet me there — follow so you don't miss it.")
FRIDAY_LINE = ("Tomorrow is Friday — we learn and build something from scratch, "
               "together. Meet me there — follow so you don't miss it.")
VO_TARGET_LUFS = -14.0   # channel spine (PLAYBOOK §Audio, finalize QC gate)
MAX_TEASE_CHARS = 80     # keeps the outro segment ≤ ~8s of speech


def _norm(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())


_MONTHS = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
           "Jun": "June", "Jul": "July", "Aug": "August", "Sep": "September",
           "Sept": "September", "Oct": "October", "Nov": "November", "Dec": "December"}


def clean_title(title):
    """YT title -> speakable tease: drop emojis/hashtags, keep spoken punctuation,
    fix the bits TTS reads badly ('--' pause-dashes, 'Aug 19' month abbrevs)."""
    t = re.sub(r"#\w+", "", title or "")
    t = "".join(c for c in t if c.isascii() or c in "—–’‘“”")
    t = t.replace("--", "—")
    t = re.sub(r"\b(" + "|".join(_MONTHS) + r")\.?(?=\s+\d)",
               lambda m: _MONTHS[m.group(1)], t)
    # trailing "(Ranked)" / "(Here's Your Rule)" parentheticals are YT packaging,
    # not speech — drop them from the spoken tease
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)
    t = re.sub(r"\s+", " ", t).strip(" -—–·|").strip()
    if len(t) > MAX_TEASE_CHARS:
        cut = max(t.rfind(m, 0, MAX_TEASE_CHARS) for m in ("—", ":", ","))
        if cut < 20:
            cut = t.rfind(" ", 0, MAX_TEASE_CHARS)
        t = t[:cut].strip(" -—–:,")
    return t


def _supa():
    from factory_worker import Supa, load_env
    env = load_env()
    return Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])


def _upcoming(supa, from_date, exclude_id=None, exclude_title=None, on_date=None):
    """Teasable content rows from `from_date` on — or exactly ON `on_date` —
    excluding this episode's own row. Teasable = planned/queued/produced
    (produced = already armed on YouTube, the most certain of all). NEVER
    `suggested`: an unapproved topic must not be promised on-air."""
    date_filter = (f"planned_date=eq.{on_date}" if on_date
                   else f"planned_date=gte.{from_date}")
    rows = supa.select("factory_calendar", (
        f"channel_key=eq.{CHANNEL_KEY}"
        "&status=in.(planned,queued,produced)"
        f"&{date_filter}"
        "&or=(kind.eq.content,kind.is.null)"
        "&order=planned_date.asc&limit=6"
        "&select=id,title,planned_date,status,kind,type"))
    out = []
    for r in rows or []:
        if exclude_id and str(r.get("id")) == str(exclude_id):
            continue
        if exclude_title and _norm(r.get("title")) == _norm(exclude_title):
            continue
        # internal production items (footage tapes etc.) are calendar rows but
        # never viewer-facing episodes — teasing one would be nonsense on air
        if (r.get("type") or "") in ("record_demo", "shell_script"):
            continue
        if clean_title(r.get("title")):
            out.append(r)
    return out


def compose_line(cfg_title=None, calendar_id=None, ref_date=None):
    """-> (spoken_line, source_note). DAY-AWARE relative to the episode's own
    PUBLISH date (its calendar row's planned_date via calendar_id, or
    `ref_date`, else today — finalize runs before publish, and 'tomorrow' must
    be the VIEWER'S tomorrow):
      - tomorrow is FRIDAY  -> the learning-and-building series handoff
        (names the Friday chapter when one is planned, generic line otherwise)
      - next planned item IS tomorrow -> "Tomorrow: <tease>"
      - next planned item is later / none -> series promise (never claim a
        'tomorrow' the calendar can't back)
    Best-effort: any lookup failure degrades to the calendar-free lines."""
    supa = None
    try:
        supa = _supa()
    except Exception as e:  # noqa: BLE001
        print(f">> outro_cta: no calendar access ({e}) — composing without it")

    ref = None
    if ref_date:
        ref = datetime.date.fromisoformat(str(ref_date))
    elif calendar_id and supa:
        try:
            own = supa.select("factory_calendar",
                              f"id=eq.{calendar_id}&select=planned_date")
            if own:
                ref = datetime.date.fromisoformat(own[0]["planned_date"])
        except Exception:  # noqa: BLE001
            pass
    ref = ref or datetime.date.today()
    tomorrow = ref + datetime.timedelta(days=1)

    if tomorrow.weekday() == 4:  # Friday -> series handoff, never a daily tease
        if supa:
            try:
                rows = _upcoming(supa, None, exclude_id=calendar_id,
                                 exclude_title=cfg_title,
                                 on_date=tomorrow.isoformat())
                if rows:
                    return (FRIDAY_TMPL.format(tease=clean_title(rows[0]["title"])),
                            f"friday-series:{tomorrow.isoformat()}")
            except Exception as e:  # noqa: BLE001
                print(f">> outro_cta: friday lookup failed ({e}) — generic series line")
        return FRIDAY_LINE, "friday-series"

    if supa:
        try:
            rows = _upcoming(supa, tomorrow.isoformat(), exclude_id=calendar_id,
                             exclude_title=cfg_title)
            if rows and rows[0]["planned_date"] == tomorrow.isoformat():
                return (TEASE_TMPL.format(tease=clean_title(rows[0]["title"])),
                        f"tease:{rows[0]['planned_date']}")
        except Exception as e:  # noqa: BLE001
            print(f">> outro_cta: calendar lookup failed ({e}) — using series promise")
    return FALLBACK_LINE, "series-promise"


def measure_lufs(path):
    """Integrated loudness via ebur128 Summary block (same parse as
    finalize_episode.measure_lufs). None on failure."""
    r = subprocess.run(
        ["ffmpeg", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True)
    tail = r.stderr.rsplit("Summary:", 1)[-1] if "Summary:" in r.stderr else r.stderr
    m = re.findall(r"I:\s*(-?[\d.]+)\s+LUFS", tail)
    return float(m[-1]) if m else None


def probe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def prepare_cta(cfg, assets_dir, voice, style=0.4, calendar_id=None):
    """Compose + synth + level the outro CTA. Returns
    {text, note, wav, dur_s, gain_db}. Raises on TTS failure — a spec that
    asks for a spoken CTA must not silently ship without one (§ Ep25 lesson:
    silent regressions, not failures, are what actually hurt).

    cfg["outro_cta"]: True/"auto" -> compose from the calendar; any other
    string -> that exact line is spoken verbatim (VJ-authored)."""
    spec = cfg.get("outro_cta")
    if isinstance(spec, str) and spec.strip().lower() not in ("auto", "true"):
        text, note = spec.strip(), "verbatim"
    else:
        text, note = compose_line(cfg_title=cfg.get("title"), calendar_id=calendar_id)

    wav = os.path.join(assets_dir, "outro_cta.wav")
    txt = os.path.join(assets_dir, "outro_cta.txt")
    cached = (os.path.exists(wav) and os.path.exists(txt)
              and open(txt, encoding="utf-8").read().strip() == text)
    if not cached:
        from eleven_vo import load_key, synth
        synth(load_key(), voice, text, wav, speed=1.0, style=style)
        with open(txt, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    dur = probe_dur(wav)
    lufs = measure_lufs(wav)
    if lufs is None:
        raise RuntimeError(f"outro_cta: could not measure LUFS of {wav}")
    gain = round(VO_TARGET_LUFS - lufs, 2)
    gain = max(-20.0, min(30.0, gain))
    print(f">> outro_cta [{note}] {dur:.2f}s, {lufs:.1f} LUFS -> gain "
          f"{gain:+.1f} dB{' (cached)' if cached else ''}: {text!r}")
    return {"text": text, "note": note, "wav": wav, "dur_s": dur, "gain_db": gain}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="compose only, no TTS spend")
    ap.add_argument("--ep", help="synth into assets/ep<EP>/outro_cta.wav")
    ap.add_argument("--exclude-title", help="this episode's own title (skip in tease)")
    ap.add_argument("--calendar-id", help="this episode's calendar row id (skip in tease)")
    ap.add_argument("--text", help="verbatim line instead of auto-compose")
    ap.add_argument("--ref-date", help="simulate the episode's publish date "
                    "(YYYY-MM-DD) — 'tomorrow' is computed from this")
    a = ap.parse_args()
    if a.dry:
        line, note = ((a.text, "verbatim") if a.text else
                      compose_line(cfg_title=a.exclude_title, calendar_id=a.calendar_id,
                                   ref_date=a.ref_date))
        print(json.dumps({"line": line, "source": note}, indent=1))
        sys.exit(0)
    if not a.ep:
        sys.exit("need --ep (or --dry)")
    from build_ep_v2 import ELEVEN_VOICE, STYLE  # locked voice + style
    A = os.path.join(CH, "assets", f"ep{a.ep}")
    os.makedirs(A, exist_ok=True)
    cfg = {"outro_cta": a.text or "auto", "title": a.exclude_title or ""}
    res = prepare_cta(cfg, A, ELEVEN_VOICE, style=STYLE, calendar_id=a.calendar_id)
    print(json.dumps(res, indent=1))
