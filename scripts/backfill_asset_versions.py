#!/usr/bin/env python3
"""backfill_asset_versions — register today's claude-tricks brand assets as v1 = LOCKED
in factory_asset_versions, and set the factory_asset_locks rows (docs/STUDIO-ASSET-VERSIONING.md
Phase 1). Idempotent (upsert on the unique keys), so safe to re-run.

Two namespaces per row (the whole design hinges on this):
  storage_path = BUCKET path  (<channel>/assets/...)  -> webapp preview
  meta.build_ref = the ASSETS-RELATIVE substitution string build_ep_v2 uses (or a bare id)
`asset_type` is the join key across backfill / lock table / build_ep_v2 _LOCK_CFG_KEY.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import factory_worker as fw

CH = "claude-tricks"

# (asset_type, label, storage_path|None, thumb_path|None, build_ref|None, extra_meta)
ASSETS = [
    # --- wired into build_ep_v2 via factory_asset_locks (Phase 2) ---
    ("outro_sting", "Subscribe/comment sting (shared default)",
     f"{CH}/assets/outro/outro_sub_comment.mp4", None, "outro/outro_sub_comment.mp4",
     {"note": "the exact asset the 2026-08-18 build silently fell back to; now deliberate + visible"}),
    ("host_outfit", "Sol — outfit 11 magenta (Shorts, pinned Ep11)",
     f"{CH}/assets/character/host_library/outfit_11_sol_magenta/wide.jpg",
     f"{CH}/assets/character/host_library/outfit_11_sol_magenta/wide.jpg",
     "character/host_library/outfit_11_sol_magenta",
     {"note": "dir lock; pip/wide/3q derive from it. HeyGen 3-face pool = Phase 3"}),
    ("music_bed", "bed_active (−8.3 LUFS, 0.35 mix)",
     f"{CH}/assets/music/bed_active.mp3", None, "music/bed_active.mp3", {}),
    ("remotion_comp", "Remotion composition id", None, None, "Short", {}),
    # --- visibility-only (board shows what's locked; not lock-resolved in Phase 2) ---
    ("outro_card_gen", "Outro question-CTA generator (premium, per-ep)",
     f"{CH}/assets/ep_artifacts/outro_card.mp4", f"{CH}/assets/ep_artifacts/outro_card.jpg",
     "gen_outro_card.py", {"note": "per-episode question-CTA card"}),
    ("step_chip_style", "STEP n/N glass chip + #NN hashtag card", None, None, "chip",
     {"note": "Short.tsx StepChip; corner in the 4th steps tuple"}),
    ("component_statbars", "StatBars chart component", None, None, "StatBars.tsx", {}),
    ("component_outrocard", "Premium OutroCard component (v16.2)", None, None, "OutroCard.tsx", {}),
    ("component_buildclub", "Build-Club kit component", None, None, "BuildClub.tsx", {}),
]
# only these get a factory_asset_locks row (the build-resolvable defaults)
LOCKED_TYPES = {"outro_sting", "host_outfit", "music_bed", "remotion_comp"}


def main():
    env = fw.load_env()
    supa = fw.Supa(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])

    rows = []
    for atype, label, sp, tp, bref, meta in ASSETS:
        m = dict(meta)
        if bref is not None:
            m["build_ref"] = bref
        rows.append({
            "channel_key": CH, "asset_type": atype, "version": 1, "label": label,
            "storage_path": sp, "thumb_path": tp, "source": "import",
            # only the build-resolvable slots get a lock row, so only they are "locked"
            "status": "locked" if atype in LOCKED_TYPES else "candidate",
            "meta": m,
        })
    supa.insert("factory_asset_versions", rows,
                on_conflict="channel_key,asset_type,version", resolution="merge-duplicates")
    print(f">> upserted {len(rows)} version row(s) (v1, locked)")

    # fetch ids back to build the lock rows
    got = supa.select("factory_asset_versions",
                      f"channel_key=eq.{CH}&version=eq.1&select=id,asset_type")
    id_by_type = {r["asset_type"]: r["id"] for r in got}
    locks = [{"channel_key": CH, "asset_type": t, "locked_version_id": id_by_type[t]}
             for t in LOCKED_TYPES if t in id_by_type]
    supa.insert("factory_asset_locks", locks,
                on_conflict="channel_key,asset_type", resolution="merge-duplicates")
    print(f">> set {len(locks)} lock row(s): {', '.join(sorted(l['asset_type'] for l in locks))}")
    print(">> DONE — Studio asset versions + locks registered for", CH)


if __name__ == "__main__":
    main()
