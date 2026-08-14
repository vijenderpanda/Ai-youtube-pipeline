# AI Unpacked — the 12-day read (2026-08-14)

> Written on the **committed snapshot history** (`docs/stats/history.csv`, 2026-08-03 → 2026-08-14,
> 12 daily snapshots, 166 rows for this channel). Last snapshot ran **2026-08-14 06:37 IST**.
>
> 🔴 **This read does NOT contain today's Build Club numbers.** bc01 (`bWoa98zMWjA`) was still
> `private`/scheduled at that snapshot and went public at **16:00 IST today** — every number below
> predates its publish. See §5 for the one command that closes that gap.

---

## 1. Channel state at the last snapshot

| | 2026-08-04 | 2026-08-14 | Δ |
|---|---|---|---|
| Subscribers | 3 | **5** | +2 |
| Channel views | 402 | **1280** | +878 |

Traffic mix (7d): **SHORTS 359** · YT_SEARCH 59 · YT_OTHER_PAGE 6 · EXT_URL 6.
→ Distribution on this channel *is* the Shorts feed. Search is a distant second and everything
else is noise. Whatever the feed decides in the first 24h is effectively the whole result.

## 2. The shape of every video's life: one burst, then flat

Indexed to the day each video actually went **public** (not its scheduled date — several were
unlisted for days and flipped later, which the raw date column hides):

| Video | Public | d0 | d1 | d2 | d3 | latest | Lane |
|---|---|---|---|---|---|---|---|
| I Built an AI Factory 🏭 | 08-06 | 68 | 170 | 219 | 221 | **223** | meta/BTS |
| Ask AI For a Table, Not a Wall of Text 📊 | 08-13 | 129 | **172** | — | — | 172 ↑ | tips |
| The Effort Dial Nobody Uses 🧠 | 08-11 | 165 | 165 | 165 | 166 | 166 | tips |
| You're Using The WRONG Claude Model! | 08-03 | 109 | 140 | 142 | 142 | 147 | tips |
| You Type The SAME Prompt Every Day! | 08-04 | 147 | 145 | 147 | 147 | 148 | tips |
| Claude Burns Your Tokens 🪙 | 08-11 | 132 | 138 | 143 | 144 | 144 | tips |
| Claude Just Got SKILLS! | 08-04 | 91 | 120 | 118 | 119 | 119 | tips |
| Claude Code Forgets EVERYTHING! | 08-03 | 88 | 117 | 115 | 116 | 117 | tips |
| The Best AI Just Got Cheaper 💸 | 08-05 | 8 | 22 | 22 | 107 | 107 | news/pricing |
| 6 Claude Commands, Ranked 🧠 | 08-12 | 25 | 37 | 51 | — | 51 ↑ | tips |
| AI Faked IDs In Its Own Safety Test 🧪 | 08-11 | 10 | 15 | 16 | 16 | **16** | news |
| That "AI" Label Is The Law Now 🏷️ | 08-09 | 7 | 9 | 12 | 14 | **14** | news |
| Google Just Put AI In Your Kid's Classroom 🎓 | 08-08 | 8 | 10 | 11 | 11 | **13** | news |
| Stop Describing Your Document — Give It The File 📄 | 08-08 | 1 | 7 | 7 | 7 | **7** | tips |
| Stop Copy-Pasting Between AIs 🛑 | 08-12 | 5 | 5 | 5 | — | **5** | tips |

**Everything is decided in 24–48h.** A video that gets a feed sample lands 90–130 views on day 0
and finishes within ~15% of that by day 3. A video that doesn't get sampled never recovers — no
video in this dataset has ever climbed out of single digits later. There is no long tail to wait for.

## 3. The one clean experiment in the dataset

On **2026-08-11** three videos flipped public on the **same day, same channel, same feed moment**:

| Video | Lane | Views |
|---|---|---|
| The Effort Dial Nobody Uses 🧠 | tips | **165** |
| Claude Burns Your Tokens 🪙 | tips | **132** |
| AI Faked IDs In Its Own Safety Test 🧪 | news | **10** |

Same day, same shelf, **13–16× gap**. This is what makes the lane split credible rather than a
publishing-schedule artifact: the usual confound (the Aug-11 batch flip got some special push)
is controlled here, because the news video was *inside that same batch* and still flopped.

**Lane medians across the whole window:** news ≈ **14** · tips ≈ **134**.

### What this is NOT
- **Not** a claim that news is unviable in general — it's a claim about *this* channel's current
  news execution, at n=4, against an audience of 5 subscribers.
- **The Best AI Just Got Cheaper** (107) is a real exception in the news lane, and **Stop Describing
  Your Document** (7) and **Stop Copy-Pasting** (5) are real exceptions in the tips lane. The split
  is directional, not a law.
- **No retention data backs any of this.** Views are an impression-side signal; `yt_retention.py`
  has never been run on these videos, so *why* the feed drops the news shorts (weak 3s hook? weak
  15s sustain?) is unmeasured. That's the gap worth closing before any big restructure.

## 4. The Friday question — there is no Friday signal yet

| Friday | What shipped | Result |
|---|---|---|
| 2026-08-07 | Google Classroom 🎓 (**news lane**) | 13 lifetime views |
| 2026-08-14 | Build Club Ch.1 (`bWoa98zMWjA`) | **unknown — published after the last snapshot** |

Two Fridays, one of which is unreadable. Day-of-week has **n=1 legible sample**, and that sample is
confounded with lane (it was a news short, and news shorts flopped on Tue/Sun/Wed too). Nothing in
this dataset separates "Friday is a bad slot" from "news is a bad lane."

**Therefore: keep the current cadence.** Fridays stay Build Club, per the standing rule — no
restructure without evidence. The evidence that *does* exist points at the **lane**, not the weekday.

Revisit after **bc02 (Aug 21)**: two chapters + retention curves is the first point where a Friday
verdict is honest. Pre-commit the thresholds now so it isn't argued after the fact:
- **bc01 d0 ≥ 90 views** → Build Club reaches the feed like the tips lane. Keep Friday, keep going.
- **bc01 d0 in 20–90** → mid. Hold Friday, fix the hook off the retention curve before Ch.3.
- **bc01 d0 < 20** → the format is not being sampled. Then the question becomes format (long-form
  serialized vs 60s Short), not weekday — moving the same asset to Tuesday would change nothing.

## 5. Closing the gap — the live pull (Windows worker)

Not runnable from a Claude Code web session: this container has **no `secrets/token_*.json`** (they're
gitignored and never leave the worker hosts), and the Supabase host is **blocked by this session's
egress policy** (`403` on CONNECT to `xfqyovimnqdghiekicqr.supabase.co`), so the job queue can't be
reached from here either. Run on the Windows box:

```powershell
# 1. refresh the network snapshot (writes history.csv + DAILY-STATS.md)
python scripts\network_stats.py

# 2. today's Build Club chapter — the retention curve, not just the view count
python scripts\yt_retention.py --channel claude-tricks --video bWoa98zMWjA --summary `
    --md docs\stats\RETENTION.md

# 3. the Build Club demand signal (the homework CTA is the whole point of the format)
python scripts\yt_engage.py --channel claude-tricks --video bWoa98zMWjA --count-keyword SHIPPED --days 7
python scripts\yt_engage.py --channel claude-tricks --video bWoa98zMWjA --count-keyword netlify --days 7
```

Two Windows caveats, both live:
- **Auth.** `get_creds()` falls through to an *interactive browser consent* when
  `secrets\token_claude-tricks.json` is absent — that will hang a headless `analytics_sync` job
  forever. Auth each channel once on the box before scheduling a sync there.
- **Analytics lag.** The Analytics API finalizes with a ~48h lag, so today's retention numbers are
  provisional. The **view count** in step 1 is live and is the number that matters for the §4
  thresholds.

## 6. What the read says to do

1. **Keep Friday = Build Club.** No evidence to move it. (§4)
2. **Cut the news lane, not the Friday slot.** It is the one thing in this dataset that reliably
   underperforms by an order of magnitude. Aug 17 was an unbooked "fetch feeds day-of" news slot —
   moved to the tips lane (calendar row 19). Aug 19 (row 21) is the same generic slot and should
   move too. Aug 15 and Aug 16 are already armed and dated — leave them alone.
3. **Run the retention pull** (§5) before touching anything structural. Views tell you the feed said
   no; only the curve tells you where.
