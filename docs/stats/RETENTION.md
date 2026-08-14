
### Retention — claude-tricks (2026-08-13 22:26 IST)
_Analytics lag ~48h; low-sample videos are withheld by YouTube._

- **I Built an AI Factory That Makes My Videos 🏭 (It Made This O** (32s) — 3s hold 116%, 15s hold 39%, ends 22%. steepest drops: 6.7s (−14pp), 6.4s (−10pp), 5.1s (−8pp)
- **You Type The SAME Prompt Every Day! (Save It As A Command) 🛑** (33s) — 3s hold 106%, 15s hold 56%, ends 17%. steepest drops: 5.3s (−11pp), 6.3s (−6pp), 8.6s (−6pp)
- **Claude Burns Your Tokens — Do THIS Instead 🪙 (Save Money + S** (36s) — 3s hold 715%, 15s hold 680%, ends 640%. steepest drops: 1.4s (−20pp), 4.7s (−10pp), 24.8s (−10pp)

### bc01 (`bWoa98zMWjA`) — pulled 2026-08-15 02:27 IST from the Mac

The 2026-08-15 attempt on `DESKTOP-DEIR7RS` (Windows worker) failed with
`FileNotFoundError: secrets/client_secret.json` — that channel has never been authed on that box.
Re-run from the Mac session, which has `secrets/token_claude-tricks.json`:

`python3 scripts/yt_retention.py --channel claude-tricks --video bWoa98zMWjA --summary --md docs/stats/RETENTION.md`
succeeded and returned **`insufficient_data`** — YouTube withholds the retention curve until the
video has more sample, so there is no drop-off shape to read yet.

- **Your Idea Goes LIVE Tonight — From Your Phone (FREE) 🚀 — Bui** — _insufficient_data_

**bc01 read against the pre-committed thresholds ([AI-UNPACKED-READ-2026-08-14.md §4](AI-UNPACKED-READ-2026-08-14.md#4-the-friday-question--there-is-no-friday-signal-yet)):**
`docs/stats/history.csv` shows **4 views** at the 2026-08-15 snapshot (~9.5h after the 2026-08-14
20:30 IST publish), public since 2026-08-15. That's **well under the <20 "format question" band** —
bc01 is not clearing the 20–90 hold-and-fix-hook band, let alone the ≥90 keep band. With no
retention curve to diagnose the hook, the immediate signal is impressions/sampling, not on-video
drop-off. `yt_engage.py --count-keyword SHIPPED --days 7` found **0 comments** matching "SHIPPED"
(0 unique authors) — no homework-CTA signal yet, consistent with the low view count.
