
### Retention — claude-tricks (2026-08-13 22:26 IST)
_Analytics lag ~48h; low-sample videos are withheld by YouTube._

- **I Built an AI Factory That Makes My Videos 🏭 (It Made This O** (32s) — 3s hold 116%, 15s hold 39%, ends 22%. steepest drops: 6.7s (−14pp), 6.4s (−10pp), 5.1s (−8pp)
- **You Type The SAME Prompt Every Day! (Save It As A Command) 🛑** (33s) — 3s hold 106%, 15s hold 56%, ends 17%. steepest drops: 5.3s (−11pp), 6.3s (−6pp), 8.6s (−6pp)
- **Claude Burns Your Tokens — Do THIS Instead 🪙 (Save Money + S** (36s) — 3s hold 715%, 15s hold 680%, ends 640%. steepest drops: 1.4s (−20pp), 4.7s (−10pp), 24.8s (−10pp)

### bc01 (`bWoa98zMWjA`) — pull attempted 2026-08-15, blocked

`python scripts/yt_retention.py --channel claude-tricks --video bWoa98zMWjA --summary --md docs/stats/RETENTION.md`
and the matching `yt_engage.py --count-keyword SHIPPED` pull both failed on this worker
(`DESKTOP-DEIR7RS`) with `FileNotFoundError: secrets/client_secret.json`. Per
`docs/stats/AI-UNPACKED-READ-2026-08-14.md` §5, this channel has never been authed on this box —
`secrets/token_claude-tricks.json` does not exist here either, and `secrets/` on this host only
holds `factory.env`. No d0 view count or retention curve could be pulled, so bc01 cannot yet be
placed in the §4 band (≥90 keep / 20–90 hold+fix hook / <20 format question).

**Unblock:** run `python scripts/yt_upload.py --channel claude-tricks` (or the equivalent
one-time interactive auth path in `yt_upload.py`) on this box to complete the OAuth consent flow
and write `secrets/token_claude-tricks.json`, then re-run the retention/engagement pulls above.
