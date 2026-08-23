#!/usr/bin/env python3
"""score_packaging.py — advisory CTR/virality score for a Short's PACKAGING
(title · description · tags · hook line), checked against THIS channel's own
data-derived rules. Not a promise of virality — no gate can be — but it flags
packaging that misses the patterns our winners share.

Rules come from docs/SHORTS-METHOD-AND-APP-GATES.md, the retention-truth memo,
and WEB-TOUR-TEMPLATE.md:
  - Title CTR band ~40–50 chars (the 4.6%-CTR winners cluster near 44), exactly
    ONE emoji, at least one hot/curiosity word, and a specific noun/number.
  - The searched noun must live in title AND tags (search tail), not just VO.
  - Tags: 8–15, include the primary noun, no dupes.
  - Description line-1 is a DIFFERENT hook from the title, carries the GIVE
    (a URL / pinned prompt), and the "Not affiliated" disclosure.
  - Hook VO line ≤ ~12 words with a tension/curiosity trigger.

Usage:
  python3 scripts/score_packaging.py --ep academy            # reads the spec + builds desc
  python3 scripts/score_packaging.py --ep academy --json
  python3 scripts/score_packaging.py --title "..." --tags "a,b,c" --desc-file d.txt
Exit code: 0 if score >= FLOOR, 1 if below (so CI / a hook can block on it).
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CH = os.path.join(REPO, "channels", "claude-tricks")

FLOOR = 62          # below this, packaging is "not ready" (exit 1 / gate issue)
STRONG = 80         # at/above this, "strong"
YT_TITLE_MAX = 100

# Hot / curiosity / power words our CTR winners lean on (title-cased match is
# case-insensitive). Kept deliberately tight — presence of ANY earns the point.
HOT_WORDS = {
    "free", "you", "your", "this", "how", "why", "stop", "nobody", "just", "now",
    "secret", "actually", "wrong", "before", "never", "everyone", "gives", "opened",
    "real", "watch", "look", "no", "without", "catch", "hidden", "instantly",
    "badge", "cheaper", "forever", "1", "one",
}
# Curiosity/tension triggers for the spoken hook line
HOOK_TRIGGERS = {
    "nobody", "no one", "you", "your", "how", "why", "just", "actually", "free",
    "watch", "look", "without", "secret", "before", "catch", "opened", "gives",
    "stop", "never", "everyone", "wrong",
}
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⌀-⏿]"
)


def _emoji_count(s):
    return len(EMOJI_RE.findall(s or ""))


def _words(s):
    return re.findall(r"[a-z0-9']+", (s or "").lower())


def _title_len_no_emoji(title):
    # count the readable characters (emoji excluded) — the CTR band is about text
    return len(EMOJI_RE.sub("", title or "").strip())


def score(title, tags, desc, hook_line=None, noun=None):
    """Return (score:int, checks:list[dict{name,status,detail,pts,max}])."""
    checks = []

    def add(name, ok, warn, detail, pts, mx):
        status = "PASS" if ok else ("WARN" if warn else "FAIL")
        got = mx if ok else (round(mx * 0.5) if warn else 0)
        checks.append({"name": name, "status": status, "detail": detail,
                       "pts": got, "max": mx})

    title = title or ""
    tags = tags or ""
    desc = desc or ""
    taglist = [t.strip() for t in tags.split(",") if t.strip()]
    tlen = _title_len_no_emoji(title)

    # 1. Title length band (25 pts) — ideal 40–50, ok 34–56, else warn/fail
    if 40 <= tlen <= 50:
        add("title-length", True, False, f"{tlen} chars (ideal 40–50)", 25, 25)
    elif 34 <= tlen <= 56:
        add("title-length", False, True, f"{tlen} chars (ok; aim 40–50)", 25, 25)
    elif len(title) > YT_TITLE_MAX:
        add("title-length", False, False, f"{len(title)} chars — OVER YouTube {YT_TITLE_MAX}", 25, 25)
    else:
        add("title-length", False, True, f"{tlen} chars (off-band; aim 40–50)", 25, 25)

    # 2. Exactly one emoji (10 pts)
    ec = _emoji_count(title)
    add("title-emoji", ec == 1, ec in (0, 2), f"{ec} emoji (want exactly 1)", 10, 10)

    # 3. Hot / curiosity word in title (20 pts)
    tw = set(_words(title))
    hits = sorted(tw & HOT_WORDS)
    add("title-hotword", bool(hits), False,
        f"hot words: {hits}" if hits else "no hot/curiosity word — flat title", 20, 20)

    # 4. Specificity: a number OR a proper/product noun in title (10 pts)
    has_num = bool(re.search(r"\d", title))
    has_caps = bool(re.search(r"\b[A-Z][a-zA-Z]{2,}\b", title))
    add("title-specific", has_num or has_caps, False,
        ("has number" if has_num else "") + (" +named-thing" if has_caps else "")
        or "no number or named thing — vague", 10, 10)

    # 5. Searched noun in title AND tags (15 pts) — the search tail
    if noun:
        n = noun.lower()
        in_title = n in title.lower()
        in_tags = n in tags.lower()
        add("noun-searchable", in_title and in_tags, in_title or in_tags,
            f"'{noun}' in title={in_title} tags={in_tags}", 15, 15)
    else:
        add("noun-searchable", None is None and True, False,
            "no noun supplied — skipped", 0, 0)

    # 6. Tags count + include primary token (10 pts)
    ntags = len(taglist)
    dupes = len(taglist) != len(set(t.lower() for t in taglist))
    ok_tags = 8 <= ntags <= 15 and not dupes
    add("tags", ok_tags, 5 <= ntags <= 20 and not dupes,
        f"{ntags} tags{' (DUPES)' if dupes else ''} (want 8–15)", 10, 10)

    # 7. Description line-1 is a different hook + has GIVE + disclosure (10 pts)
    d1 = next((ln.strip() for ln in desc.splitlines() if ln.strip()), "")
    diff_hook = d1 and d1.lower().rstrip(" .!?") != title.lower().rstrip(" .!?")
    has_give = bool(re.search(r"https?://|pinned|copy|prompt|exact line|link", desc, re.I))
    has_disc = "not affiliated" in desc.lower()
    d_ok = diff_hook and has_give and has_disc
    add("description", d_ok, (diff_hook and has_disc) or (has_give and has_disc),
        f"line1≠title={bool(diff_hook)} give={has_give} disclosure={has_disc}", 10, 10)

    # 8. Hook VO line: short + a curiosity trigger (bonus, does not lower a good score)
    if hook_line is not None:
        hw = _words(hook_line)
        short = len(hw) <= 13
        trig = bool(set(hw) & {w for t in HOOK_TRIGGERS for w in t.split()})
        add("hook-line", short and trig, short or trig,
            f"{len(hw)} words, trigger={trig}", 10, 10)

    total = sum(c["pts"] for c in checks)
    mx = sum(c["max"] for c in checks) or 1
    return round(100 * total / mx), checks


def _load_from_ep(ep):
    spec_path = os.path.join(CH, "episodes", f"{ep}.v2.json")
    spec = json.load(open(spec_path))
    title = spec.get("title", "")
    tags = spec.get("tags", "")
    lines = spec.get("lines") or []
    hook = lines[0] if lines else None
    # primary searched noun: first multi-char token of the first tag
    noun = None
    if tags:
        first = tags.split(",")[0].strip()
        noun = first or None
    # build the real description via finalize's builder
    desc = ""
    try:
        sys.path.insert(0, HERE)
        import tempfile
        from finalize_episode import build_description
        with tempfile.TemporaryDirectory() as td:
            desc = open(build_description(spec, os.path.join(td, "p"))).read()
    except Exception as e:
        print(f"!! could not build description ({e}); scoring title/tags only", file=sys.stderr)
    return title, tags, desc, hook, noun


def run(title, tags, desc, hook, noun):
    sc, checks = score(title, tags, desc, hook_line=hook, noun=noun)
    verdict = "STRONG" if sc >= STRONG else ("OK" if sc >= FLOOR else "NOT READY")
    return sc, verdict, checks


def _fmt(sc, verdict, checks):
    out = [f"packaging score: {sc}/100 — {verdict}  (floor {FLOOR}, strong {STRONG})", "-" * 64]
    for c in checks:
        if c["max"] == 0:
            continue
        mark = {"PASS": "✓", "WARN": "~", "FAIL": "✗"}[c["status"]]
        out.append(f"  {mark} {c['name']:<16} {c['pts']:>2}/{c['max']:<2}  {c['detail']}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Advisory CTR/virality score for Short packaging")
    ap.add_argument("--ep", help="episode key — reads episodes/<ep>.v2.json + builds desc")
    ap.add_argument("--title")
    ap.add_argument("--tags", help="comma-separated")
    ap.add_argument("--desc-file")
    ap.add_argument("--hook", help="the spoken hook line (else lines[0] from the spec)")
    ap.add_argument("--noun", help="primary searched noun (else first tag)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.ep:
        title, tags, desc, hook, noun = _load_from_ep(a.ep)
    else:
        title, tags = a.title or "", a.tags or ""
        desc = open(a.desc_file).read() if a.desc_file else ""
        hook, noun = a.hook, a.noun
    if a.hook:
        hook = a.hook
    if a.noun:
        noun = a.noun

    sc, verdict, checks = run(title, tags, desc, hook, noun)
    if a.json:
        print(json.dumps({"score": sc, "verdict": verdict, "floor": FLOOR,
                          "checks": checks, "title": title}, indent=1))
    else:
        print(_fmt(sc, verdict, checks))
    sys.exit(0 if sc >= FLOOR else 1)


if __name__ == "__main__":
    main()
