#!/usr/bin/env python3
"""
AI Unpacked news radar. Runs every 3h via launchd.

Checks AI news feeds for big stories (Claude/Anthropic/OpenAI launches etc.).
New + big => macOS notification + appends a draft row to NEWS-RADAR.md so a
bonus short can be produced same-day.

Also hosts the PEG FRESHNESS GATE (`--peg-check`), which every produce_short
job must run as step zero before scripting a NEWS episode:

    python scripts/news_radar.py --peg-check "GPT-5.6 price cut" \
        --air-date 2026-08-07 --max-age-days 4 [--json]

It answers one question — "how old is the story this cold open fronts, on the
day it actually airs?" — from local history (NEWS-RADAR.md + the titled RSS
cache) and refuses to pass anything it cannot date.

Two incidents this gate exists to prevent:
  * dcf956d5 — "The Smartest AI Just Changed (Again)". Hook claimed the
    leaderboard "just changed" while its pegs (Claude Opus 5 Jul 24, GPT-5.6
    price cuts Jul 30) were 8-14 days old on the Aug-7 air date. Challenged by
    hand; the ba79ded0 replacement reframed it from "just happened" to
    verified consumer impact.
  * 14d5fed6 — "AI Models Tried to Hack Back During Safety Tests". Fronted the
    Aug-4 "19 instances" finding on an Aug-10 air date (6 days stale) while
    fresher developments in the *same* story stream (fake identities and
    social-engineering attempts, Aug 5) were sitting right there unused.

Both were caught by a reviewer. A recurring mechanical failure belongs in a
gate, so: stale peg => exit 2, undatable peg => exit 3. An unknown age is not
a fresh peg. Every check is appended to NEWS-RADAR.md so the QUALITY-LEDGER
can audit peg age per episode.
"""
import argparse, hashlib, html, json, os, re, subprocess, sys, urllib.request
from datetime import datetime, timedelta

CH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "channels", "claude-tricks")
SEEN = os.path.join(CH, ".news_seen.json")
CACHE = os.path.join(CH, ".news_cache.json")
OUT = os.path.join(CH, "NEWS-RADAR.md")

FEEDS = [
    "https://www.anthropic.com/news/rss.xml",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
]
HOT = re.compile(r"claude|anthropic|openai|gpt|gemini|launch|releases?|announc|new model|update", re.I)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")

def items(xml):
    for m in re.finditer(r"<item>(.*?)</item>|<entry>(.*?)</entry>", xml, re.S):
        chunk = m.group(1) or m.group(2)
        t = re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", chunk, re.S)
        l = re.search(r"<link[^>]*?(?:href=\"([^\"]+)\"|>([^<]+)</link>)", chunk, re.S)
        if t:
            title = re.sub(r"\s+", " ", t.group(1)).strip()
            link = (l.group(1) or l.group(2) or "").strip() if l else ""
            yield title, link

def notify(msg):
    subprocess.run(["osascript", "-e",
                    f'display notification "{msg}" with title "AI Unpacked — News Radar" sound name "Glass"'])

# ---------------------------------------------------------------- peg check

# Section headers in NEWS-RADAR.md carry the date every headline under them
# inherits: "## Radar 2026-08-05 03:51", "## Backfill 2026-07-30".
SECTION_RE = re.compile(r"^##\s+\w+\s+(\d{4}-\d{2}-\d{2})")
HEADLINE_RE = re.compile(r"^-\s+(?:\[[ xX]\]\s*)?(.+?)\s*$")
STOPWORDS = {"the", "a", "an", "of", "for", "and", "to", "in", "on", "at", "by",
             "is", "are", "was", "were", "its", "it", "as", "that", "this",
             "with", "from", "just", "has", "have", "had", "but", "not"}
# Tokens too generic to establish that two headlines are the same story —
# "launch"/"new"/"model" relate half the feed to the other half.
GENERIC = {"launch", "launches", "launched", "new", "update", "updates", "ai",
           "model", "models", "announce", "announces", "announced", "release",
           "releases", "released", "says", "report", "reports", "tool", "tools",
           "company", "companies", "startup", "startups", "team", "day", "days"}
# A peg is "found" when this share of its significant tokens appear in one
# history entry. 2-of-3 / 3-of-4 — loose enough for phrasing drift, tight
# enough that "Amazon ruling" doesn't match every Amazon headline.
MATCH_THRESHOLD = 0.67

def norm(text):
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()

def tokens(text):
    """Significant lowercase tokens. Keeps version numbers intact: gpt-5.6."""
    raw = re.findall(r"[a-z0-9][a-z0-9.\-']*", norm(text).lower())
    out = []
    for t in raw:
        t = t.strip(".-'")
        if len(t) >= 3 and t not in STOPWORDS:
            out.append(t)
    return out

def hits(token, text):
    """Prefix match on a word boundary, so 'cut' matches 'cuts'."""
    return re.search(r"(?<![a-z0-9])" + re.escape(token), text.lower()) is not None

def score(peg_tokens, entry_text):
    if not peg_tokens:
        return 0.0
    return sum(1 for t in peg_tokens if hits(t, entry_text)) / len(peg_tokens)

def read_history():
    """Every dated headline the factory has locally: NEWS-RADAR.md + RSS cache.

    Peg-check log lines are skipped — a gate must never treat its own audit
    trail as evidence that a story existed.
    """
    entries, date = [], None
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            line = line.rstrip("\n")
            s = SECTION_RE.match(line)
            if s:
                date = s.group(1)
                continue
            if line.startswith("- PEG-CHECK") or line.startswith("## Peg Checks"):
                continue
            m = HEADLINE_RE.match(line)
            if m and date and not line.startswith("- http"):
                entries.append({"title": norm(m.group(1)), "date": date, "src": "NEWS-RADAR.md"})
    if os.path.exists(CACHE):
        try:
            for rec in json.load(open(CACHE)).values():
                if rec.get("title") and rec.get("first_seen"):
                    entries.append({"title": norm(rec["title"]),
                                    "date": rec["first_seen"][:10],
                                    "src": "rss-cache"})
        except Exception as e:
            print(f"warn: unreadable RSS cache ({e})", file=sys.stderr)
    return entries

def peg_check(peg, air_date, max_age_days, as_json=False):
    peg_tokens = tokens(peg)
    history = read_history()

    matches = [dict(e, score=round(score(peg_tokens, e["title"]), 2))
               for e in history]
    strong = [m for m in matches if m["score"] >= MATCH_THRESHOLD]

    # 48h window ending on the air date, for the re-peg suggestion.
    window_start = (air_date - timedelta(days=2)).strftime("%Y-%m-%d")
    air_s = air_date.strftime("%Y-%m-%d")
    first_seen = min((m["date"] for m in strong), default=None)
    specific = [t for t in peg_tokens if t not in GENERIC]

    def related(m, since):
        # Same story stream = shares a non-generic token, and is newer than
        # the peg itself.
        return (m["date"] <= air_s and m["date"] >= since
                and (first_seen is None or m["date"] > first_seen)
                and any(hits(t, m["title"]) for t in specific))

    def dedupe(ms):
        return sorted({m["title"]: m for m in ms}.values(),
                      key=lambda m: (m["date"], m["title"]), reverse=True)

    fresher = dedupe([m for m in matches if related(m, window_start)])
    # Anything newer than the peg, not only the last 48h — the 14d5fed6 fix
    # re-pegged a 10 Aug episode onto a 5 Aug development.
    since_peg = dedupe([m for m in matches
                        if related(m, first_seen or window_start)
                        and m["title"] not in {f["title"] for f in fresher}])

    result = {"peg": peg, "air_date": air_s, "max_age_days": max_age_days,
              "first_seen": first_seen, "age_days": None,
              "fresher_related": [f"{m['date']} — {m['title']}" for m in fresher[:5]],
              "fresher_same_story": [f"{m['date']} — {m['title']}" for m in since_peg[:5]],
              "verdict": None, "sources": sorted({m["src"] for m in strong})}

    if first_seen is None:
        result["verdict"] = "UNVERIFIED"
        code = 3
    else:
        result["age_days"] = (air_date - datetime.strptime(first_seen, "%Y-%m-%d")).days
        stale = result["age_days"] > max_age_days
        result["verdict"] = "STALE" if stale else "FRESH"
        code = 2 if stale else 0

    log_check(result)

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f'PEG      : "{peg}"')
        print(f"AIR DATE : {air_s}   (max age {max_age_days}d)")
        if result["verdict"] == "UNVERIFIED":
            print("FIRST SEEN: — not in local history —")
            print("\n" + "!" * 62)
            print("!!  UNVERIFIED — WebSearch required.")
            print("!!  This peg appears in NO local radar history (radar gap).")
            print("!!  An unknown age is NOT a fresh peg. Date the story with")
            print("!!  WebSearch, then re-run --peg-check, or pick a peg the")
            print("!!  radar has actually seen.")
            print("!" * 62)
        else:
            print(f"FIRST SEEN: {first_seen}  ({', '.join(result['sources'])})")
            print(f"AGE      : {result['age_days']} day(s)")
            print(f"VERDICT  : {result['verdict']}")
        if result["fresher_related"]:
            print("\nFRESHER RELATED (last 48h, same entities):")
            for h in result["fresher_related"]:
                print(f"  - {h}")
        if result["fresher_same_story"]:
            print("\nALSO NEWER THAN THE PEG (same story stream):")
            for h in result["fresher_same_story"]:
                print(f"  - {h}")
        if result["verdict"] == "STALE":
            print("\n" + "!" * 62)
            print(f"!!  STALE PEG — {result['age_days']}d old on air date (limit {max_age_days}d).")
            print("!!  Do ONE of these before scripting:")
            print("!!   (a) re-peg the cold open on a fresher related story above;")
            print("!!   (b) reframe from 'just happened' to verified-impact")
            print("!!       framing ('here is what it means for you now').")
            print("!!  See dcf956d5 / 14d5fed6 in this file's docstring.")
            print("!" * 62)
    return code

def log_check(r):
    """Append to NEWS-RADAR.md so QUALITY-LEDGER can audit peg age per episode."""
    try:
        body = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        with open(OUT, "a", encoding="utf-8") as f:
            if "## Peg Checks" not in body:
                f.write("\n## Peg Checks\n"
                        "<!-- appended by news_radar.py --peg-check; audit trail, "
                        "NOT radar history -->\n")
            f.write(f"- PEG-CHECK {datetime.now():%Y-%m-%d %H:%M} | peg=\"{r['peg']}\" | "
                    f"air={r['air_date']} | first_seen={r['first_seen'] or '?'} | "
                    f"age={r['age_days'] if r['age_days'] is not None else '?'}d | "
                    f"limit={r['max_age_days']}d | {r['verdict']}\n")
    except Exception as e:
        print(f"warn: could not log peg check ({e})", file=sys.stderr)

# ------------------------------------------------------------------- radar

def main():
    seen = set(json.load(open(SEEN))) if os.path.exists(SEEN) else set()
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    now = f"{datetime.now():%Y-%m-%d %H:%M}"
    hits_ = []
    for f in FEEDS:
        try:
            for title, link in list(items(fetch(f)))[:15]:
                h = hashlib.md5(title.encode()).hexdigest()
                # Titles are cached with their first-seen date even when they
                # aren't "hot" — --peg-check needs to date stories the radar
                # merely saw, not only the ones it flagged.
                cache.setdefault(h, {"title": norm(title), "link": link, "first_seen": now})
                if h in seen:
                    continue
                seen.add(h)
                if HOT.search(title):
                    hits_.append((title, link))
        except Exception as e:
            print(f"feed fail {f}: {e}")
    if hits_:
        with open(OUT, "a") as f:
            f.write(f"\n## Radar {now}\n")
            for t, l in hits_[:6]:
                f.write(f"- [ ] {t}\n  {l}\n")
        notify(f"{len(hits_)} new AI stories flagged — see NEWS-RADAR.md (bonus short?)")
    json.dump(sorted(seen)[-500:], open(SEEN, "w"))
    keep = sorted(cache.items(), key=lambda kv: kv[1]["first_seen"])[-1500:]
    json.dump(dict(keep), open(CACHE, "w"), indent=0)
    print(f"radar: {len(hits_)} new hits")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="AI Unpacked news radar + peg freshness gate")
    ap.add_argument("--peg-check", metavar="PEG",
                    help="check how old a news peg is on its air date (step zero for NEWS episodes)")
    ap.add_argument("--air-date", default=None, metavar="YYYY-MM-DD",
                    help="the date the episode airs (default: today)")
    ap.add_argument("--max-age-days", type=int, default=4,
                    help="max peg age tolerated on air date (default: 4)")
    ap.add_argument("--json", action="store_true", help="emit the result as JSON")
    a = ap.parse_args()
    if a.peg_check:
        air = datetime.strptime(a.air_date, "%Y-%m-%d") if a.air_date else datetime.now()
        sys.exit(peg_check(a.peg_check, air, a.max_age_days, a.json))
    main()
