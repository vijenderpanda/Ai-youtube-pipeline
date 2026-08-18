#!/usr/bin/env python3
"""suggest_next.py -- Lane A of "suggest the next piece": a DETERMINISTIC, no-model
suggestion generator.

It reads the network's own research files, QUOTES them, and writes
`factory_calendar` rows with `status='suggested'`, `origin='ai_suggestion'` and a
full `evidence` trail (migration 022). It structurally cannot hallucinate: every
`cites[]` entry carries a real path + line number, and the quote is read off that
line at runtime -- never typed by hand, never paraphrased.

The governing rule is the GROUNDING LADDER: a channel may only emit suggestions at
the highest tier its research actually supports. A channel with no research shows
its blocker or its chore, NOT a generated idea.

  T1  decided slate       claude-tricks     (PIVOT-DECISION.md §4 scored slate)
  T2  scheduled cadence   aashiqana, lulla  (named next unit + its constraint)
  T4  format wedge        vehicles, language-abc   -> chore cards only (Lane B does topics)
  T5  recipe only         already-happening        -> chore card only
  T0  blocked             calm-ai                  -> blocker card only, never an idea

Lane B (model-backed topic generation for T4/T5) is deliberately NOT here.

Usage:
    python3 scripts/suggest_next.py --dry-run                # all channels, write nothing
    python3 scripts/suggest_next.py --channel claude-tricks --dry-run
    python3 scripts/suggest_next.py                          # reconcile + insert
    python3 scripts/suggest_next.py --limit 2
    python3 scripts/suggest_next.py --reconcile-all          # also reconcile FOREIGN
                                                             # (analyze_and_suggest) rows
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
os.chdir(REPO)

import factory_worker as fw  # noqa: E402  (Supa / load_env / suggestion_row)

CHANNELS_DIR = REPO / "channels"
GENERATED_BY = "suggest_next.py"

# ---------------------------------------------------------------- hard rules

# docs/stats/RETENTION-NEW.md reports this video at 539% / 504% / 461% -- a loop
# artefact, and RETENTION.md disagrees with retention_new.json on the same id.
# NEVER cite it, never let it into a computed stat. (spec §1.4 hard filter)
RETENTION_BLACKLIST = {"xwgEF4W5Qzc"}
# ...and its title, so the card can never name it either.
RETENTION_BLACKLIST_TEXT = {"xwgEF4W5Qzc", "Claude Burns Your Tokens"}

# The pivot (PIVOT-DECISION.md §2, VJ 2026-08-18) killed the serialized Build Club
# Short. NEEDS-ATTENTION.md still names bc06 / bcs1f as fillers and CONTENT-CALENDAR.csv
# still carries the bc03-bc06 tail: both are STALE. Dates from those files are usable;
# their topics are not. (spec §5 never-do #5)
CLAUDE_TRICKS_EP_DENYLIST = {"bc03", "bc04", "bc05", "bc06", "bcs1f"}

QUOTE_MAX = 260


class SourceDrift(RuntimeError):
    """A cited line is not where/what we expected -> emit NOTHING for this row."""


# ---------------------------------------------------------------- file helpers

_LINE_CACHE = {}


def rel(path):
    p = Path(path)
    try:
        return str(p.resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def lines_of(path):
    """1-indexed line list for `path` (index 0 is a placeholder)."""
    p = (REPO / path) if not str(path).startswith("/") else Path(path)
    key = str(p)
    if key not in _LINE_CACHE:
        if not p.exists():
            raise SourceDrift(f"missing source file: {rel(p)}")
        _LINE_CACHE[key] = [""] + p.read_text(encoding="utf-8").splitlines()
    return _LINE_CACHE[key]


def _clip(s):
    s = " ".join(s.split())
    return s if len(s) <= QUOTE_MAX else s[: QUOTE_MAX - 1] + "…"


def cite(label, path, *, needle=None, line=None, url=None, when=None, note=None):
    """Build one evidence citation. The quote is READ OFF THE FILE -- either the
    first line containing `needle`, or the given 1-indexed `line`. If the needle
    is gone the source has drifted and we raise rather than invent."""
    rows = lines_of(path)
    if needle is not None:
        hit = next((i for i in range(1, len(rows)) if needle in rows[i]), None)
        if hit is None:
            raise SourceDrift(f"{rel(path)}: needle not found: {needle!r}")
        line = hit
    if not line or line >= len(rows):
        raise SourceDrift(f"{rel(path)}: no line {line}")
    c = {"label": label, "path": rel(path), "line": line, "quote": _clip(rows[line])}
    if url:
        c["url"] = url
    if when:
        c["date"] = when
    if note:
        c["note"] = note
    return c


def cite_file(label, path, *, note=None):
    """A path-only citation (no line): used to point at an artifact whose existence
    -- or absence -- is itself the evidence."""
    c = {"label": label, "path": rel(path)}
    if note:
        c["note"] = note
    return c


def source_sha(cites):
    """sha1 over exactly the cited lines. reconcile() recomputes it from the files
    on disk; a mismatch means the research moved under a live suggestion."""
    h = hashlib.sha1()
    for c in cites:
        h.update(f"{c.get('path')}:{c.get('line')}:{c.get('quote','')}\n".encode())
    return h.hexdigest()[:16]


def current_sha(cites):
    """Recompute source_sha from what the files say RIGHT NOW."""
    fresh = []
    for c in cites:
        if not c.get("line"):
            fresh.append(c)
            continue
        rows = lines_of(c["path"])
        ln = int(c["line"])
        quote = _clip(rows[ln]) if ln < len(rows) else ""
        fresh.append({"path": c["path"], "line": ln, "quote": quote})
    return source_sha(fresh)


# ---------------------------------------------------------------- channels

def resolve_channels():
    """dir -> key via channel.json. NEVER infer the key from the directory name:
    `channels/pip-moonlit-garden/` has key `lulla`."""
    out = {}
    for d in sorted(CHANNELS_DIR.iterdir()):
        cj = d / "channel.json"
        if not d.is_dir() or not cj.exists():
            continue
        cfg = json.loads(cj.read_text())
        key = cfg.get("key")
        if not key:
            continue
        out[key] = {"key": key, "dir": d.name, "path": d, "cfg": cfg}
    return out


# ---------------------------------------------------------------- parsers

_PIVOT_ROW = re.compile(r"^\|\s*\*{0,2}(\d{1,2})\*{0,2}\s*\|(.+)$")


def parse_pivot_decision(path):
    """`## 4. The full candidate slate` -> the 12 scored candidates.
    Defensive: on zero rows the caller emits NOTHING (never a generic fallback)."""
    rows = lines_of(path)
    start = next((i for i in range(1, len(rows)) if rows[i].startswith("## 4.")), None)
    if start is None:
        raise SourceDrift(f"{rel(path)}: no '## 4.' candidate-slate section")
    out = []
    for i in range(start + 1, len(rows)):
        if rows[i].startswith("## "):
            break
        m = _PIVOT_ROW.match(rows[i].strip())
        if not m:
            continue
        cells = [c.strip() for c in rows[i].strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        raw_title = cells[1]
        # strip markdown bold and the trailing *(parenthetical)* note
        note = ""
        pm = re.search(r"\*\((.+?)\)\*", raw_title)
        if pm:
            note = pm.group(1)
            raw_title = raw_title[: pm.start()]
        title = raw_title.replace("**", "").strip()
        score = cells[3].replace("**", "").strip()
        out.append({
            "n": int(m.group(1)),
            "title": title,
            "note": note,
            "cluster": cells[2],
            "score": score,
            "why": cells[4].strip(),
            "line": i,
            "winner": "WINNER" in cells[3].upper(),
        })
    return out


_NA_SLOTS = re.compile(r"Empty guarded publish slots:\s*\*\*(.+?)\*\*")
_NA_HEAD = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+—\s+(.+?)\s*$")
_NA_FIELD = re.compile(r"^-\s+\*\*(.+?)\*\*:\s*(.*)$")


def parse_needs_attention(path):
    """-> {'slots': [YYYY-MM-DD...], 'slots_line': int, 'entries': [{date,title,line,fields}]}
    The slot list is the ONLY thing this file may contribute for claude-tricks
    (its named fillers are stale); for aashiqana it is the whole answer."""
    rows = lines_of(path)
    slots, slots_line, entries = [], None, []
    for i in range(1, len(rows)):
        if slots_line is None:
            m = _NA_SLOTS.search(rows[i])
            if m:
                slots_line = i
                slots = re.findall(r"\d{4}-\d{2}-\d{2}", m.group(1))
        h = _NA_HEAD.match(rows[i])
        if h:
            e = {"date": h.group(1), "title": h.group(2).strip(), "line": i, "fields": {}}
            for j in range(i + 1, len(rows)):
                if rows[j].startswith("#") or (not rows[j].strip() and e["fields"]):
                    break
                f = _NA_FIELD.match(rows[j].strip())
                if f:
                    e["fields"][f.group(1)] = f.group(2).strip()
                    e.setdefault("field_lines", {})[f.group(1)] = j
            entries.append(e)
    return {"slots": slots, "slots_line": slots_line, "entries": entries}


# a calendar row is CLOSED once it carries a real video (daily_check.py:50)
CLOSED_RE = re.compile(r"youtu\.be/|^\s*SHIPPED\b", re.I)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_calendar_csv(path):
    """-> {'rows': [...], 'closed_titles': [...], 'forward': [...]}
    For claude-tricks this is a NEGATIVE source: dedup corpus only, never ideas."""
    p = (REPO / path) if not str(path).startswith("/") else Path(path)
    if not p.exists():
        return {"rows": [], "closed_titles": [], "forward": [], "line_of": {}}
    text = p.read_text(encoding="utf-8")
    rdr = csv.DictReader(text.splitlines())
    rows, closed, forward, line_of = [], [], [], {}
    for n, r in enumerate(rdr, start=2):  # line 1 = header
        r["_line"] = n
        rows.append(r)
        title = (r.get("working_title") or r.get("title") or "").strip()
        if title:
            line_of[title] = n
        pd = (r.get("planned_date") or "").strip()
        if CLOSED_RE.search(pd):
            closed.append(title)
        elif DATE_RE.match(pd):
            forward.append(r)
    return {"rows": rows, "closed_titles": closed, "forward": forward, "line_of": line_of}


def parse_news_radar(md_path, cache_path):
    """Unchecked `- [ ]` radar items joined to .news_cache.json for a real URL+date.
    A peg is ONLY ever attached from here -- and only behind --peg, because none of
    the T1 candidates is news-derived and an invented peg is the worst failure mode."""
    out = []
    p = (REPO / md_path)
    if not p.exists():
        return out
    cache = {}
    cp = REPO / cache_path
    if cp.exists():
        try:
            cache = json.loads(cp.read_text())
        except (json.JSONDecodeError, OSError):
            cache = {}
        by_title = {(v.get("title") or "").strip().lower(): v for v in cache.values()}
    else:
        by_title = {}
    rows = lines_of(md_path)
    cur_date = None
    for i in range(1, len(rows)):
        h = re.match(r"^##\s+.*?(\d{4}-\d{2}-\d{2})", rows[i])
        if h:
            cur_date = h.group(1)
        m = re.match(r"^- \[ \]\s+(.+)$", rows[i].strip())
        if not m:
            continue
        title = m.group(1).strip()
        url = None
        um = re.search(r"https?://\S+", rows[i]) or (
            re.search(r"https?://\S+", rows[i + 1]) if i + 1 < len(rows) else None)
        if um:
            url = um.group(0).rstrip(")>,.")
        hit = by_title.get(title.lower())
        if hit and not url:
            url = hit.get("link")
        if url:
            out.append({"title": title, "url": url, "date": cur_date,
                        "source": "NEWS-RADAR.md", "line": i})
    return out


# ---------------------------------------------------------------- retention

def retention_constraints():
    """docs/stats/retention_new.json -> the CONSTRAINTS stapled to every
    claude-tricks brief. Never a suggestion. The loop-artefact video is excluded
    from every statistic and from every citation."""
    jp = REPO / "docs/stats/retention_new.json"
    data = json.loads(jp.read_text())
    vids = [v for v in data.get("videos", [])
            if v.get("status") == "ok" and v.get("video_id") not in RETENTION_BLACKLIST]
    if not vids:
        raise SourceDrift("retention_new.json: no usable videos after blacklist")
    ranked = sorted(vids, key=lambda v: (v.get("hook_hold") or {}).get("at_15s") or 0)
    worst, best = ranked[0], ranked[-1]
    best15 = (best["hook_hold"]["at_15s"])
    worst15 = (worst["hook_hold"]["at_15s"])
    best_end = best.get("end_watch_ratio") or 0
    worst_end = worst.get("end_watch_ratio") or 0
    ratio = (best_end / worst_end) if worst_end else 0

    steepest = [v["drop_points"][0]["at_sec"] for v in vids if v.get("drop_points")]
    lo, hi = (min(steepest), max(steepest)) if steepest else (0, 0)
    band = [s for s in steepest if 4.5 <= s <= 7.5]

    constraints = [
        "The 15s hold decides the ending: the best-holding short in the catalog "
        f"ends {ratio:.1f}x higher than the worst ({len(vids)} measurable videos, "
        "loop-artefact excluded). Rank order, not the absolute %, is the signal.",
        f"Get a changing screen on by ~4.5s (PIVOT-DECISION critic fix #1): "
        f"{len(band)} of {len(vids)} measurable videos take their steepest drop "
        f"inside 4.5-7.5s; across all {len(vids)} it lands between {lo}s and {hi}s.",
        "Target ~34s (retention-verified 2026-08-17; the old 22-28s target is dead).",
    ]
    cites = [
        cite("Best 15s hold in the catalog", "docs/stats/RETENTION-NEW.md",
             needle=best["title"][:34]),
        cite("Worst 15s hold in the catalog", "docs/stats/RETENTION-NEW.md",
             needle=worst["title"][:34]),
        cite("Critic fix #1 - kill the front-load",
             "channels/claude-tricks/PIVOT-DECISION.md",
             needle="get a real changing screen on by"),
        cite("LOCKED length + beat count", "channels/claude-tricks/PIVOT-DECISION.md",
             needle="7/7 beats, ~34s"),
        cite_file("Source data", "docs/stats/retention_new.json",
                  note="one video is blacklisted from every statistic and every citation "
                       "in this card: it reports 539-715% (a loop artefact) and the two "
                       "retention pulls disagree about it"),
    ]
    return {"constraints": constraints, "cites": cites,
            "best": best, "worst": worst}


# ---------------------------------------------------------------- normalisation

_NORM_STRIP = re.compile(r"[^a-z0-9 ]+")


def norm_title(t):
    t = (t or "").lower()
    t = t.replace("—", " ").replace("–", " ").replace("’", "'")
    t = _NORM_STRIP.sub(" ", t)
    return " ".join(t.split())


def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_free_date(chan, calendar, today):
    """spec §5 never-do #2: when there is no real empty guarded slot, fall back to
    the channel.json cadence_days formula and stamp confidence='date_inferred'.
    planned_date is NOT NULL, so the honesty lives in the confidence flag, not in
    a fabricated-looking date."""
    cad = int(chan["cfg"].get("cadence_days") or 7)
    dates = []
    for r in calendar.get("rows", []):
        pd = (r.get("planned_date") or "").strip()
        if DATE_RE.match(pd):
            dates.append(datetime.strptime(pd, "%Y-%m-%d").date())
    base = max(dates) if dates else today
    cand = base + timedelta(days=cad)
    return max(cand, today + timedelta(days=1)).isoformat()


def chore_date(chan, today):
    """A chore/blocker card is not an episode, so the cadence formula is the wrong
    shape for it. Park it one cadence (min 1 week) out so it is near-term but does
    not get retired by reconcile()'s 'slot passed' rule the next morning. Always
    confidence='date_inferred' -> the UI prints "no date yet"."""
    cad = max(int(chan["cfg"].get("cadence_days") or 7), 7)
    return (today + timedelta(days=cad)).isoformat()


# ---------------------------------------------------------------- evidence

def evidence_of(tier, source, cites, *, peg=None, constraints=None, blockers=None):
    cites = [c for c in cites if c]
    return {
        "tier": tier,
        "source": source,
        "generated_by": GENERATED_BY,
        "generated_at": iso_now(),
        "source_sha": source_sha(cites),
        "cites": cites,
        "peg": peg,
        "constraints": constraints or [],
        "blockers": blockers or [],
    }


def assert_evidence(row):
    """spec §5 never-do #4: NEVER write a row with empty cites. Dropped + logged,
    not inserted. Also enforces the retention blacklist across the whole card."""
    ev = row.get("evidence")
    if not isinstance(ev, dict):
        return "evidence missing"
    cites = ev.get("cites")
    if not isinstance(cites, list) or not cites:
        return "empty cites[]"
    for c in cites:
        if not c.get("label") or not c.get("path"):
            return f"citation without label/path: {c!r}"
    blob = json.dumps(row, ensure_ascii=False)
    for bad in RETENTION_BLACKLIST_TEXT:
        if bad in blob:
            return f"blacklisted retention video ({bad!r}) leaked into the card"
    if not ev.get("source_sha") or not ev.get("tier"):
        return "evidence missing tier/source_sha"
    return None


def mkrow(chan, planned_date, title, *, brief, reason, evidence, source,
          confidence, type_="produce_short"):
    row = fw.suggestion_row(
        chan["key"], planned_date, title,
        brief=brief, kind="content", type_=type_,
        reason=reason, evidence=evidence,
        suggestion_source=source, suggestion_confidence=confidence,
    )
    return row


# ---------------------------------------------------------------- T1 claude-tricks

# Research-named strongest un-shipped candidates (spec §1, from the judge phase).
CT_RESEARCH_TOP = [4, 8]
# PIVOT-DECISION §4 itself flags these as overlapping; keep the first, drop the second.
CT_DEDUP_PAIRS = [(9, 12), (10, 11)]


def build_claude_tricks(chan, today, limit, log):
    base = chan["path"]
    pivot = base / "PIVOT-DECISION.md"
    na_path = base / "NEEDS-ATTENTION.md"
    cands = parse_pivot_decision(pivot)
    if not cands:
        log("claude-tricks: PIVOT-DECISION §4 yielded ZERO candidates -> emitting nothing")
        return []

    winner = next((c for c in cands if c["winner"]), None)
    dropped = {b for _, b in CT_DEDUP_PAIRS}
    pool = [c for c in cands if not c["winner"] and c["n"] not in dropped]
    order = {n: i for i, n in enumerate(CT_RESEARCH_TOP)}
    pool.sort(key=lambda c: (order.get(c["n"], 99), c["n"]))
    log(f"claude-tricks: {len(cands)} candidates parsed; winner=#{winner['n'] if winner else '?'} "
        f"(shipped, excluded); dedup dropped #{', #'.join(str(b) for _, b in CT_DEDUP_PAIRS)}; "
        f"{len(pool)} un-shipped remain")

    # spec §5 never-do #5: the pivot killed the serialized Build Club Short, but
    # NEEDS-ATTENTION.md and CONTENT-CALENDAR.csv still name bc06 / bcs1f. Their
    # titles are on a hard denylist; only their DATES are usable.
    cal = parse_calendar_csv(base / "CONTENT-CALENDAR.csv")
    denied = {norm_title(r.get("working_title"))
              for r in cal["rows"]
              if (r.get("ep") or "").strip() in CLAUDE_TRICKS_EP_DENYLIST}
    denied.discard("")

    na = parse_needs_attention(na_path)
    denied |= {norm_title(e["title"]) for e in na["entries"]
               if (e["fields"].get("ep") or "").strip() in CLAUDE_TRICKS_EP_DENYLIST}
    denied.discard("")
    pool = [c for c in pool if norm_title(c["title"]) not in denied]
    log(f"claude-tricks: denylist (pivot-killed Build Club eps "
        f"{sorted(CLAUDE_TRICKS_EP_DENYLIST)}) holds {len(denied)} title(s)")

    slots = [s for s in na["slots"] if s >= today.isoformat()]
    if not slots:
        log("claude-tricks: no forward empty guarded slot in NEEDS-ATTENTION -> emitting nothing "
            "(never invent a date)")
        return []
    log(f"claude-tricks: empty guarded slots {slots} "
        f"(named fillers bc06/bcs1f IGNORED - the pivot killed them)")

    ret = retention_constraints()
    pivot_cite = cite("Pivot: the daily Shorts slot carries standalone tips", pivot,
                      needle="The **daily Shorts slot carries standalone tips**")
    slot_cite_line = na["slots_line"]

    rows = []
    for cand, slot in zip(pool, slots[:limit]):
        cites = [
            cite(f"Scored-slate candidate #{cand['n']} ({cand['cluster']})", pivot,
                 line=cand["line"],
                 note="rank INFERRED - only the winner's 77/90 survived transcript recovery"),
            cite("Recovery limitation - the losing 11 scores did not survive", pivot,
                 needle="did NOT survive"),
            pivot_cite,
            cite(f"Empty guarded slot {slot}", na_path, line=slot_cite_line),
        ] + ret["cites"]
        ev = evidence_of("T1", "pivot-decision", cites,
                         peg=None,  # no news peg: none of these candidates is news-derived
                         constraints=ret["constraints"], blockers=[])
        brief_lines = [
            f"Standalone tip Short from the locked 12-candidate slate "
            f"(PIVOT-DECISION.md §4, candidate #{cand['n']}, cluster: {cand['cluster']}).",
            f"Judge score: {cand['score']} - only the winner's 77/90 survived transcript "
            f"recovery, so this row's RANK IS INFERRED, not scored.",
            f"Slate note on this candidate: {cand['why']}",
            "",
            "MUST OBEY (from this channel's own retention pull):",
        ] + [f"  - {c}" for c in ev["constraints"]] + [
            "",
            "FORMAT: standalone tip, 7 beats / 7 lines, host-bookended demo shape. "
            "Drop every 'Ch. N' / Build Club framing - the pivot killed the serialized Short.",
            "",
            "TO DECIDE at kickoff: the single on-screen BEFORE state that lands by ~4.5s, "
            "and the one-frame muted payoff. Not fabricated here.",
        ]
        if cand["note"]:
            brief_lines.insert(1, f"Feature: {cand['note']}.")
        rows.append(mkrow(
            chan, slot, cand["title"],
            brief="\n".join(brief_lines),
            reason=(f"Un-shipped candidate #{cand['n']} from the locked pivot slate; "
                    f"fills the empty guarded slot {slot}. Rank inferred."),
            evidence=ev, source="pivot-decision", confidence="inferred_rank",
        ))
    return rows


# ---------------------------------------------------------------- T2 aashiqana

def build_aashiqana(chan, today, limit, log):
    base = chan["path"]
    na_path = base / "NEEDS-ATTENTION.md"
    ql_path = base / "QUALITY-LEDGER.md"
    na = parse_needs_attention(na_path)
    slots = set(na["slots"])
    entries = [e for e in na["entries"]
               if e["date"] in slots and e["date"] >= today.isoformat()]
    if not entries:
        log("aashiqana: no named+slotted chapter forward of today -> emitting nothing")
        return []
    log(f"aashiqana: {len(entries)} named+slotted chapter(s) {[e['date'] for e in entries]}")

    ql_cites = [
        cite("Current bar (QUALITY-LEDGER §1)", ql_path, needle="**Song #02"),
        cite("Track param floor", ql_path, needle="| Track |"),
        cite("Couple param floor", ql_path, needle="| Couple |"),
        cite("Karaoke sync param floor", ql_path, needle="| Lyrics on screen |"),
        cite("Bar rule", ql_path, needle="**Bar rule:**"),
    ]

    def _cell(quote):
        # QUALITY-LEDGER §1 is a 2-column markdown table -> "Component: param",
        # still verbatim, just lifted out of the pipes.
        parts = [p.strip() for p in quote.strip().strip("|").split("|")]
        return f"{parts[0]}: {parts[1]}" if len(parts) >= 2 else quote

    constraints = [_cell(c["quote"]) for c in ql_cites[1:4]]

    rows = []
    for e in entries[:limit]:
        fl = e.get("field_lines", {})
        cites = [
            cite(f"Named + slotted chapter {e['date']}", na_path, line=e["line"]),
            cite("Production note", na_path, line=fl.get("production_note", e["line"])),
            cite("Slot time", na_path, line=fl.get("slot_time_ist", e["line"])),
            cite("Empty guarded slot list", na_path, line=na["slots_line"]),
        ] + ql_cites
        ev = evidence_of("T2", "needs-attention", cites,
                         constraints=constraints, blockers=[])
        brief = "\n".join([
            f"{e['fields'].get('production_note', '')}",
            f"Slot: {e['date']} {e['fields'].get('slot_time_ist', '')} IST · "
            f"format: {e['fields'].get('format', 'short')} · ep {e['fields'].get('ep', '?')}",
            "",
            "PARAM FLOOR (QUALITY-LEDGER §1 - anything below this is a regression "
            "and blocks publish):",
        ] + [f"  - {c}" for c in constraints] + [
            "",
            "TO DECIDE at kickoff: which unused bar opens the Short word-first. "
            f"NEEDS-ATTENTION says \"{e['fields'].get('hook_promise', 'TBD')}\" - "
            "the suggester does not fabricate it.",
        ])
        rows.append(mkrow(
            chan, e["date"], e["title"],
            brief=brief,
            reason=(f"Standing serial: the next chapter is already named and slotted for "
                    f"{e['date']} in NEEDS-ATTENTION.md."),
            evidence=ev, source="needs-attention", confidence="scored",
        ))
    return rows


# ---------------------------------------------------------------- T2 lulla

def build_lulla(chan, today, limit, log):
    base = chan["path"]
    cal_path = base / "CONTENT-CALENDAR.csv"
    ql_path = base / "QUALITY-LEDGER.md"
    cal = parse_calendar_csv(cal_path)
    c1 = next((r for r in cal["rows"] if (r.get("ep") or "").strip().upper() == "C1"), None)
    if not c1:
        log("lulla: no C1 compilation row in CONTENT-CALENDAR.csv -> emitting nothing")
        return []
    note = c1.get("production_note") or ""
    blockers = []
    if "Leonardo" in note:
        blockers.append("Leonardo API tokens topped up for the 21 interlude stills "
                        "(account action - comp/README.md)")
    if "Suno" in note:
        blockers.append("A Suno Pro Chrome session for the 9 instrumental reprises "
                        "(account action - comp/README.md)")
    if not blockers:
        log("lulla: C1 no longer names its two account blockers -> source drifted")
        raise SourceDrift("lulla C1 production_note lost its blockers")

    when = next_free_date(chan, cal, today)
    na = parse_needs_attention(base / "NEEDS-ATTENTION.md")
    fwd_slots = [s for s in na["slots"] if s >= today.isoformat()]
    log(f"lulla: C1 is spec-complete + tooling-validated but BLOCKED on 2 account actions; "
        f"NEEDS-ATTENTION forward slots={fwd_slots or 'none'} -> planned_date {when} "
        f"is cadence-inferred ({chan['cfg'].get('cadence_days')}d)")

    cites = [
        cite("C1 compilation spec + its two account blockers", cal_path, line=c1["_line"]),
        cite_file("Validated compilation spec (3601.04s / 15 segments)",
                  base / "comp/60min_calm.json"),
        cite("QUALITY-LEDGER is STALE - says next = #6, calendar says #08 is next",
             ql_path, needle="Next NEW episode",
             note="2 episodes stale: #6 and #7 have since shipped/been planned. "
                  "Treat its params as a floor, not as the schedule."),
        cite("Pipeline param floor", ql_path, needle="**Pipeline v1 (Pipeline A):**"),
    ]
    if na["slots_line"]:
        cites.append(cite("NEEDS-ATTENTION slot list (Song #08 is a bare TBD - "
                          "ranked BELOW C1, and not suggested: its topic would have to be invented)",
                          base / "NEEDS-ATTENTION.md", line=na["slots_line"]))
    ev = evidence_of("T2", "calendar-csv", cites,
                     constraints=[_clip(c1.get("production_note", ""))],
                     blockers=blockers)
    brief = "\n".join([
        "READY EXCEPT FOR TWO ACCOUNT ACTIONS. Spec + tooling are DONE and validated "
        "end-to-end; nothing here needs writing.",
        f"Spec: {c1.get('assets', '')}",
        "",
        "BLOCKED ON:",
    ] + [f"  - {b}" for b in blockers] + [
        "",
        f"Calendar note: {_clip(note)}",
        "",
        "Best effort-to-output ratio on the network: 6 shipped songs -> one 1-hour "
        "compilation, no new lyrics, no new characters.",
        "",
        "NOTE: QUALITY-LEDGER.md is 2 episodes stale (it still says the next new "
        "episode is #6). Use it for params only, never for the schedule.",
    ])
    return [mkrow(
        chan, when, (c1.get("working_title") or "").strip(),
        brief=brief,
        reason=("C1 1-hour compilation: spec written, comp/60min_calm.json validated at "
                "3601.04s, tooling tested. Blocked only on 2 account top-ups."),
        evidence=ev, source="calendar-csv", confidence="date_inferred",
    )][:limit]


# ---------------------------------------------------------------- T0 calm-ai

def build_calm_ai(chan, today, limit, log):
    base = chan["path"]
    na_path = base / "NEEDS-ATTENTION.md"
    cj = base / "channel.json"
    if (chan["cfg"].get("lifecycle") or "") != "incubating":
        log("calm-ai: lifecycle is no longer 'incubating' -> spec assumption drifted")
    cites = [
        cite("NEEDS-ATTENTION §0 - the blocking decision", na_path,
             needle="FIRST — does this channel still exist?"),
        cite("What happened to the Supabase row", na_path,
             needle="were all deleted** from the database"),
        cite("Option A - it was deliberate", na_path, needle="It was deliberate"),
        cite("Option B - it was accidental", na_path, needle="It was accidental"),
        cite("channel.json lifecycle gate (produce_channel hard-409s on 'incubating')",
             cj, needle='"lifecycle"'),
        cite("§7 still open - is this channel distinct from AI Unpacked?", na_path,
             needle="Is this channel actually distinct"),
    ]
    blockers = [
        "The factory_channels row, the wizard draft and the scaffold job row were all "
        "deleted mid-scaffold - the on-disk scaffold is orphaned.",
        "No YouTube channel, no OAuth token, no ElevenLabs voice picked.",
        "channel.json lifecycle='incubating' -> produce_channel hard-409s.",
    ]
    ev = evidence_of("T0", "chore", cites, constraints=[], blockers=blockers)
    brief = "\n".join([
        "calm-ai is NOT producible. This is a decision card, not an idea.",
        "",
        "Decide one of:",
        "  A. It was deliberate (wizard test) -> delete channels/calm-ai/, revert the "
        "calm-ai entries in scripts/factory_worker.py and docs/PRODUCTION-PLAYBOOK.md §14.",
        "  B. It was accidental -> re-run the channel wizard with the same answers "
        "(name \"Calm AI\", key calm-ai, accent #6366F1), then uncomment the calm-ai "
        "entry in CHANNEL_SEED.",
        "",
        "Still open in §7: is this channel actually distinct from AI Unpacked? If a "
        "viewer couldn't tell them apart in 3 seconds, fold it in.",
        "",
        "No content suggestion will ever be emitted for this channel until the decision "
        "lands - its CONTENT-CALENDAR.csv is the best-designed research artifact in the "
        "repo and it is unrunnable.",
    ])
    return [mkrow(
        chan, chore_date(chan, today),
        "BLOCKED — decide whether calm-ai still exists",
        brief=brief,
        reason=("calm-ai's Supabase channel row was deleted mid-scaffold and "
                "lifecycle is 'incubating'. Blocker card only - never ideas."),
        evidence=ev, source="chore", confidence="date_inferred", type_="custom",
    )][:limit]


# ---------------------------------------------------------------- T4/T5 chores

def build_vehicles(chan, today, limit, log):
    base = chan["path"]
    cal_path = base / "CONTENT-CALENDAR.csv"
    na_path = base / "NEEDS-ATTENTION.md"
    cal = parse_calendar_csv(cal_path)
    ep01 = next((r for r in cal["rows"] if (r.get("ep") or "").strip() == "01"), None)
    if not ep01 or "avatar" not in (ep01.get("production_note") or ""):
        log("vehicles: ep01 row no longer names the pending avatar -> emitting nothing")
        return []
    cites = [
        cite("Channel avatar still pending (no API - Studio UI only)", cal_path,
             line=ep01["_line"]),
        cite("NEEDS-ATTENTION has not regenerated since 2026-08-10", na_path, line=1),
        cite("ep02 is a bare TBD - nothing built", na_path, needle="Nothing built yet"),
    ]
    ev = evidence_of("T4", "chore", cites, constraints=[],
                     blockers=["Channel avatar upload has no API path - YouTube Studio UI only."])
    brief = "\n".join([
        "CHORE, not a content idea. vehicles is T4 (format wedge): its only topic "
        "generator is BRAND-BIBLE §1's Rumble Town cast, which needs a model -> Lane B. "
        "This suggester will not invent a truck.",
        "",
        "Do this: upload the Rumble Trucks channel avatar in YouTube Studio "
        "(thumb A + banner were already set via API; the avatar has no API path).",
        "",
        "Also true and worth seeing: ep02 is a bare TBD with nothing built, and "
        "NEEDS-ATTENTION.md has not regenerated since 2026-08-10.",
    ])
    return [mkrow(
        chan, chore_date(chan, today),
        "CHORE — Upload the Rumble Trucks channel avatar (YouTube Studio, no API path)",
        brief=brief,
        reason=("Blocking chore surfaced from the channel's own calendar: the avatar is "
                "still pending and cannot be set via the API."),
        evidence=ev, source="chore", confidence="date_inferred", type_="custom",
    )][:limit]


def build_language_abc(chan, today, limit, log):
    base = chan["path"]
    cal_path = base / "CONTENT-CALENDAR.csv"
    cal = parse_calendar_csv(cal_path)
    ep02 = next((r for r in cal["rows"] if (r.get("ep") or "").strip() == "02"), None)
    if not ep02 or "duplicates" not in (ep02.get("production_note") or ""):
        log("language-abc: ep02 row no longer names the duplicate uploads -> emitting nothing")
        return []
    cites = [
        cite("Duplicate unlisted/private ep02 uploads block verify_uploads.py",
             cal_path, line=ep02["_line"]),
        cite("ep03 is a bare TBD - nothing built", base / "NEEDS-ATTENTION.md",
             needle="Nothing built yet"),
    ]
    ev = evidence_of("T4", "chore", cites, constraints=[],
                     blockers=["verify_uploads.py keeps failing until the duplicates are retired."])
    brief = "\n".join([
        "CHORE, not a content idea. language-abc is T4 (format wedge): its only topic "
        "generator is BRAND-BIBLE §1's multilingual wedge, which needs a model -> Lane B. "
        "This suggester will not invent an episode.",
        "",
        "Do this: two extra copies of \"Count to 5 in Spanish!\" sit unlisted + private on "
        "the channel. Mark them '🗑️ DELETE — ' and retire them with yt_cleanup.py "
        "(or verify_uploads.py keeps flagging them as duplicates).",
        "",
        "This is the blocking chore: it must clear before the next episode's upload "
        "verification can pass.",
    ])
    return [mkrow(
        chan, chore_date(chan, today),
        "CHORE — Retire the duplicate ep02 uploads (yt_cleanup.py) so verify_uploads.py passes",
        brief=brief,
        reason=("Blocking chore from the channel's own calendar: duplicate unlisted/private "
                "ep02 uploads make verify_uploads.py fail."),
        evidence=ev, source="chore", confidence="date_inferred", type_="custom",
    )][:limit]


def build_already_happening(chan, today, limit, log):
    base = chan["path"]
    bp = base / "PRODUCTION-BLUEPRINT.md"
    cal_path = base / "CONTENT-CALENDAR.csv"
    if cal_path.exists():
        log("already-happening: CONTENT-CALENDAR.csv now EXISTS -> chore is done, "
            "emitting nothing (topics are Lane B)")
        return []
    cites = [
        cite("§2 tells you HOW, and nothing about WHAT", bp,
             needle="## 2. Per-episode variables"),
        cite("Topic + script is a per-episode variable with no queue behind it", bp,
             needle="**Topic + script**"),
        cite("The fast path starts with \"lock topic\" - but nothing holds the topics", bp,
             needle="Lock topic + title"),
        cite_file("CONTENT-CALENDAR.csv DOES NOT EXIST", cal_path,
                  note="verified absent at generation time; every sibling channel has one"),
        cite_file("channel.json has no `calendar` key (siblings do)", base / "channel.json"),
    ]
    ev = evidence_of("T5", "chore", cites, constraints=[],
                     blockers=["No topic queue exists anywhere on disk for this channel."])
    brief = "\n".join([
        "CHORE, not a content idea. already-happening is T5 (recipe only): "
        "PRODUCTION-BLUEPRINT.md §2 tells you exactly HOW to make an episode "
        "(copy build_ep01_v3.py, edit 4 spots, alternate wonder<->provocation vs ep01) "
        "and NOTHING about what. Zero planning research exists.",
        "",
        "Do this: create channels/already-happening/CONTENT-CALENDAR.csv with the same "
        "header as its siblings "
        "(ep,planned_date,slot_time_ist,working_title,format,hook_promise,production_note,assets).",
        "",
        "Once it exists, NEWS-RADAR.md's untriaged headlines are exactly the \"TODAY "
        "anchor\" beat the 6-beat spine needs - and Lane B (plan_content) can fill the rows.",
        "",
        "No content suggestion will be emitted for this channel until the calendar exists.",
    ])
    return [mkrow(
        chan, chore_date(chan, today),
        "Create channels/already-happening/CONTENT-CALENDAR.csv",
        brief=brief,
        reason=("T5: the blueprint is a recipe with zero topic queue. The calendar file "
                "does not exist, so there is nothing honest to suggest until it does."),
        evidence=ev, source="chore", confidence="date_inferred", type_="custom",
    )][:limit]


BUILDERS = {
    "claude-tricks": build_claude_tricks,
    "aashiqana": build_aashiqana,
    "lulla": build_lulla,
    "calm-ai": build_calm_ai,
    "vehicles": build_vehicles,
    "language-abc": build_language_abc,
    "already-happening": build_already_happening,
}


# ---------------------------------------------------------------- dedup corpus

def dedup_corpus(supa, chan, today):
    """spec §5 never-do #3. Returns 4 sets:
      closed_norms    -- titles already planned/queued/produced in factory_calendar,
                         already SHIPPED in CONTENT-CALENDAR.csv, or already posted
      csv_forward     -- titles of OPEN (un-shipped, dated) CONTENT-CALENDAR.csv rows
      suggested_norms -- titles already sitting as a live suggestion (don't pile up)
      suggested_keys  -- (date, normtitle) of live suggestions (the unique-index key)

    `csv_forward` is split out on purpose. For claude-tricks the CSV is a NEGATIVE
    source and every CSV title blocks a suggestion. For the T2 channels the open CSV
    row IS the research the suggestion is made of (that is the whole point of "the
    next unit is already named"), so a row derived from needs-attention/calendar-csv
    is exempt from `csv_forward` -- but never from `closed_norms`.
    """
    lo = (today - timedelta(days=30)).isoformat()
    hi = (today + timedelta(days=30)).isoformat()
    planned, suggested_norms, suggested_keys = set(), set(), set()
    rows = supa.select(
        "factory_calendar",
        f"channel_key=eq.{chan['key']}&planned_date=gte.{lo}&planned_date=lte.{hi}"
        "&select=id,title,status,origin,planned_date")
    for r in rows:
        n = norm_title(r.get("title"))
        if not n:
            continue
        if r.get("status") == "skipped":
            continue
        if r.get("status") == "suggested":
            suggested_norms.add(n)
            suggested_keys.add((r.get("planned_date"), n))
        else:
            planned.add(n)
    cal = parse_calendar_csv(chan["path"] / "CONTENT-CALENDAR.csv")
    csv_forward = set()
    for n in (norm_title(t) for t in cal["closed_titles"]):
        if n:
            planned.add(n)
    for r in cal["forward"]:
        n = norm_title(r.get("working_title") or r.get("title"))
        if n:
            csv_forward.add(n)
    posts = supa.select(
        "factory_posts",
        f"channel_key=eq.{chan['key']}&select=yt_title&order=created_at.desc&limit=30")
    for p in posts:
        n = norm_title(p.get("yt_title"))
        if n:
            planned.add(n)
    return planned, csv_forward, suggested_norms, suggested_keys


# a row whose evidence IS the open calendar row may not be deduped against it
CSV_DERIVED_SOURCES = {"needs-attention", "calendar-csv"}


# ---------------------------------------------------------------- reconcile

def reconcile(supa, today, *, dry, include_foreign, log):
    """Runs FIRST, every tick (spec §5).
      1. planned_date < today, unaccepted        -> skipped / 'slot passed'
      2. slot now filled (queued/produced/post)  -> skipped / 'slot filled'
      3. cited lines moved (source_sha mismatch) -> skipped / 'source changed - re-derive'
      4. otherwise leave it alone. The shelf must not churn under the user.

    SAFETY: by default this only touches rows THIS script wrote
    (evidence.generated_by == 'suggest_next.py'). Rows written by
    analyze_and_suggest are counted and reported but left alone unless
    --reconcile-all is passed."""
    rows = supa.select(
        "factory_calendar",
        "status=eq.suggested&origin=eq.ai_suggestion"
        "&select=id,channel_key,planned_date,title,evidence,suggestion_source")
    filled = {}
    changes, foreign_would = [], 0
    for r in rows:
        ev = r.get("evidence") or {}
        ours = isinstance(ev, dict) and ev.get("generated_by") == GENERATED_BY
        why = None
        if r["planned_date"] < today.isoformat():
            why = "slot passed"
        else:
            ck = r["channel_key"]
            if ck not in filled:
                busy = supa.select(
                    "factory_calendar",
                    f"channel_key=eq.{ck}&status=in.(queued,produced)&select=planned_date")
                filled[ck] = {b["planned_date"] for b in busy}
            if r["planned_date"] in filled[ck]:
                why = "slot filled"
            elif ours and ev.get("cites"):
                try:
                    if current_sha(ev["cites"]) != ev.get("source_sha"):
                        why = "source changed - re-derive"
                except SourceDrift:
                    why = "source changed - re-derive"
        if not why:
            continue
        if not ours and not include_foreign:
            foreign_would += 1
            continue
        changes.append((r, why))

    for r, why in changes:
        log(f"  reconcile: {r['channel_key']} {r['planned_date']} "
            f"\"{r['title'][:52]}\" -> skipped ({why})")
        if not dry:
            supa.patch("factory_calendar", f"id=eq.{r['id']}",
                       {"status": "skipped", "why_not": why})
    if foreign_would:
        log(f"  reconcile: {foreign_would} FOREIGN ai_suggestion row(s) would also be "
            f"retired - left untouched (pass --reconcile-all to include them)")
    return len(changes), foreign_would


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Lane A deterministic suggestion generator")
    ap.add_argument("--channel", default=None, help="channel KEY (not directory)")
    ap.add_argument("--dry-run", action="store_true", help="print rows, write nothing")
    ap.add_argument("--limit", type=int, default=3, help="max rows per channel (default 3)")
    ap.add_argument("--no-reconcile", action="store_true")
    ap.add_argument("--reconcile-all", action="store_true",
                    help="also reconcile ai_suggestion rows this script did not write")
    ap.add_argument("--peg", action="store_true",
                    help="allow attaching a NEWS-RADAR peg (off: no candidate is news-derived)")
    a = ap.parse_args()

    def log(m):
        print(m, flush=True)

    today = date.today()
    env = fw.load_env()
    supa = fw.Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])

    chans = resolve_channels()
    log(f"[suggest_next] {today} · resolved {len(chans)} channel(s) via channel.json:")
    for k, c in chans.items():
        flag = "  <-- key != directory" if k != c["dir"] else ""
        log(f"   {c['dir']:24s} -> {k}{flag}")
    log("")

    if a.channel and a.channel not in chans:
        sys.exit(f"unknown channel key {a.channel!r}; known: {', '.join(sorted(chans))}")

    if not a.no_reconcile:
        log("[reconcile]")
        n, nf = reconcile(supa, today, dry=a.dry_run,
                          include_foreign=a.reconcile_all, log=log)
        log(f"  {n} row(s) retired{' (dry-run)' if a.dry_run else ''}\n")

    if a.peg:
        pegs = parse_news_radar("channels/claude-tricks/NEWS-RADAR.md",
                                "channels/claude-tricks/.news_cache.json")
        log(f"[peg] {len(pegs)} unchecked radar item(s) carry a real URL "
            f"(still unused: no T1 candidate is news-derived)\n")

    total_ins, total_skip = 0, 0
    for key in ([a.channel] if a.channel else list(BUILDERS)):
        chan = chans.get(key)
        if not chan:
            continue
        log(f"=== {key}  (dir: {chan['dir']}) ===")
        try:
            rows = BUILDERS[key](chan, today, a.limit, lambda m: log("  " + m))
        except SourceDrift as e:
            log(f"  SOURCE DRIFT -> emitting NOTHING: {e}\n")
            continue
        if not rows:
            log("")
            continue

        planned, csv_forward, sugg_norms, sugg_keys = dedup_corpus(supa, chan, today)
        keep = []
        for r in rows:
            bad = assert_evidence(r)
            if bad:
                log(f"  DROPPED (evidence guard): \"{r['title'][:56]}\" -- {bad}")
                total_skip += 1
                continue
            n = norm_title(r["title"])
            if (r["planned_date"], n) in sugg_keys:
                log(f"  already suggested (same date+title): \"{r['title'][:56]}\"")
                total_skip += 1
                continue
            if n in sugg_norms:
                log(f"  already suggested on another date: \"{r['title'][:56]}\"")
                total_skip += 1
                continue
            if n in planned:
                log(f"  already planned/queued/shipped: \"{r['title'][:56]}\"")
                total_skip += 1
                continue
            if n in csv_forward and r["suggestion_source"] not in CSV_DERIVED_SOURCES:
                log(f"  already an open calendar row: \"{r['title'][:56]}\"")
                total_skip += 1
                continue
            keep.append(r)

        for r in keep:
            ev = r["evidence"]
            log("")
            log(f"  [{ev['tier']}] {r['planned_date']}  {r['title']}")
            log(f"        source={r['suggestion_source']} confidence={r['suggestion_confidence']} "
                f"type={r['type']} sha={ev['source_sha']}")
            log(f"        why: {r['suggestion_reason']}")
            for c in ev["cites"]:
                loc = f"{c['path']}:{c['line']}" if c.get("line") else c["path"]
                log(f"        · {c['label']}")
                log(f"            {loc}")
                if c.get("quote"):
                    log(f"            “{c['quote']}”")
                if c.get("note"):
                    log(f"            ⚠ {c['note']}")
            for c in ev["constraints"]:
                log(f"        MUST OBEY: {c}")
            for b in ev["blockers"]:
                log(f"        BLOCKER:   {b}")
        log("")

        if keep and not a.dry_run:
            # every row carries identical keys (fw.suggestion_row) -> no PGRST102
            assert len({tuple(sorted(r)) for r in keep}) == 1, "heterogeneous row keys"
            assert all(r["evidence"]["cites"] for r in keep), "empty cites reached insert"
            supa.insert("factory_calendar", keep)
            log(f"  INSERTED {len(keep)} row(s)\n")
        total_ins += len(keep)

    log(f"[suggest_next] {'would insert' if a.dry_run else 'inserted'} {total_ins} row(s); "
        f"{total_skip} skipped by the dedup/evidence guards")


if __name__ == "__main__":
    main()
