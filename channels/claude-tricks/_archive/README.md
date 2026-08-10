# Archived — AI Unpacked (`claude-tricks`)

Anything here is **out of the channel's active context**. Do not read from this dir during planning, brief writing, analytics rollups, or brand-bible reconciliation unless the operator names it explicitly ("read the archived Ep28 spec").

## Why archive

Between 2026-08-05 and 2026-08-09 the pipeline shipped four episodes (Ep27–30) as **draft posts** — the manifest contract turned the delivered video into a `factory_posts` draft row so the operator could arm them for scheduled publish. None were armed within the peg window. Ep28 in particular went stale (peg dated 2026-08-10, expired). Rather than let stale drafts pollute the analytics + planning surface, they move here.

Ep11–Ep30 as public episode numbers were **never claimed** — the channel's live catalogue publishes as Ep1–Ep8 (Effort Dial is the last live) plus Ep25 "AI Factory" as a one-off breakout. The next public episode is **Ep 9**, coming 2026-08-11.

## What's here

### `episodes/`
- `27.v2.json` — "Free Google AI Notebook" (unshipped)
- `28.v2.json` — "AI Faked IDs" (unshipped, peg stale)
- `29.v2.json` — "AI Label Is Law" (unshipped)
- `30.v2.json` — "Give It The File" (unshipped)

### `assets/ep{27,28,29,30}/`
Per-episode asset bundles: host outfit pin (`host_outfit.txt`), VO word timings (`vo_v2.words.json`), broll manifest (`broll/manifest.json` where present), plus every mock / still / clip generated during the build. Large media files (mp4/png/jpg) are gitignored per repo policy — they may or may not still be on disk locally.

### `renders/`
Per-episode raw + polished + outro MP4s (`ep{27,28,29,30}_v2*.mp4`). Gitignored — moved locally, not tracked.

## External inventory — not local

The unlisted YouTube video `cv1nzSC7mMY` "Google Just Put AI In Your Kid's Classroom 🎓" is functionally archived (11 views, no plan to revive) but has no local files here — the archive is on YouTube itself. Flip its `privacyStatus` from `unlisted` → `private` via `scripts/yt_cleanup.py` (or a one-off privacy flip) when the operator is ready.

## Recall

If ever needed: `git log --oneline channels/claude-tricks/_archive/` shows when each was moved and why. `grep -r "<ep_key>" channels/claude-tricks/QUALITY-LEDGER.md` still surfaces the build lessons — they stayed in the ledger's `# Archived` section, not deleted.
