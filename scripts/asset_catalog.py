#!/usr/bin/env python3
"""asset_catalog — the registry of brand-asset SLOTS, python side.

Machine-readable twin of `webapp/src/assetCatalog.js`. The `asset_type` strings here
MUST stay byte-identical to the ones there, because asset_type is the join key across:

    scripts/ingest_asset_library.py  ->  factory_asset_versions
                                     ->  factory_asset_locks
                                     ->  build_ep_v2._LOCK_CFG_KEY (build_ep_v2.py:1289)
                                     ->  factory_template_assets (Phase 4)

VOCABULARY (the whole design rests on this):
  * an `asset_type` is a **SLOT** — one thing chosen per render.
  * its **versions** are interchangeable **revisions** of that slot. 12 host outfits are
    12 versions of `host_outfit`, not 12 asset types.
  * **candidates are not versions.** The 134 outfit candidates + 41 upscaled_4k files ride
    on their outfit's version row as `meta.variants[]` / `meta.candidates`.

Each slot carries a `discover` rule so any channel's ingest can be driven from this one
file. Globs are relative to the slot's root:
    root="assets"   ->  channels/<ch>/assets/
    root="channel"  ->  channels/<ch>/
resolved against BOTH the repo working tree and the T5 media backup
(/Volumes/Samsung_T5/Ai-youtube-pipeline-media-backup/...).

Never duplicate the label map a fourth time — import from here.
"""

# --------------------------------------------------------------------------------------
# file-kind helpers (mirror of webapp/src/mediaKind.js)
# --------------------------------------------------------------------------------------
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_EXTS = (".mp4", ".mov", ".webm", ".m4v")
AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac")


def media_kind(path):
    p = (path or "").lower()
    if p.endswith(IMAGE_EXTS):
        return "image"
    if p.endswith(VIDEO_EXTS):
        return "video"
    if p.endswith(AUDIO_EXTS):
        return "audio"
    return "other"


# --------------------------------------------------------------------------------------
# canonical variant-role vocabulary
# --------------------------------------------------------------------------------------
# Three host generations named the same shots three different ways. `meta.variants[].role`
# is where that normalizes. ONLY `center` and `three_quarter` exist across all three —
# do not assume more.
CANONICAL_ROLES = (
    "center", "three_quarter", "wide", "pip", "corner_l", "corner_r", "broll", "hands",
    "keyframe_closeup", "keyframe_rest", "keyframe_wide", "poster", "other",
)

ROLE_BY_FILENAME = {
    # o01-o10 (Leonardo Kino XL batch, 2026-08-06)
    "center.jpg": "center",
    "three_quarter.jpg": "three_quarter",
    "left_corner.jpg": "corner_l",
    "right_corner.jpg": "corner_r",
    "profile_broll.jpg": "broll",
    # o11 (Sol magenta; note the typo'd filename is load-bearing on disk)
    "wide.jpg": "wide",
    "cropeed_center_final.jpeg": "pip",
    # o12 (Nano-Banana image-EDIT chain, see its RECIPE.md)
    "keyframe_closeup.jpg": "keyframe_closeup",
    "keyframe_rest.jpg": "keyframe_rest",
    "keyframe_wide.jpg": "keyframe_wide",
    "hands_locked.jpg": "hands",
}


def role_for(filename):
    return ROLE_BY_FILENAME.get(filename.lower(), "other")


# --------------------------------------------------------------------------------------
# the slots
# --------------------------------------------------------------------------------------
# discover.unit:
#   "dir"  -> one revision per matched DIRECTORY; the canonical still is the revision's
#             bytes, every other file in the dir becomes a meta.variants[] entry.
#   "file" -> one revision per matched FILE (deduped by sha1 across local + T5).
# upload: "always" (any tier) | "full" (only --tier full) | "none" (storage_path stays null)
# thumb:  "downscale" (640px jpg) | "poster" (ffmpeg frame) | "companion" (sibling .jpg,
#         else poster) | "none"
SLOTS = {
    "host_outfit": {
        "label": "Host — Sol", "kind": "image", "wiring": "live", "group": "Host",
        "multi": False, "per_episode": False,
        "generator": "Leonardo Kino XL (o01-o11) / Nano Banana image-EDIT (o12)",
        "upload": "always", "thumb": "downscale",
        "discover": {
            "root": "assets", "unit": "dir", "order_by": "mtime",
            "globs": ["character/host_library/outfit_*"],
            # first existing name wins
            "canonical": ["wide.jpg", "keyframe_wide.jpg", "center.jpg"],
            # o12's wide.jpg is a byte-identical copy of hands_locked.jpg (verified on
            # disk 2026-08-18); shot_map.json says the establishing frame is keyframe_wide.
            "canonical_override": {"outfit_12_longform_olive": "keyframe_wide.jpg"},
            "variant_exclude_dirs": ["_candidates", "upscaled_4k", "raw", "raw_edit",
                                     "raw_hands", "raw_keyframes", "raw_rest",
                                     "raw_bodyref", "avatar_compare"],
            "count_dirs": {"candidates": "_candidates", "upscaled_4k": "upscaled_4k"},
        },
    },
    "outro_sting": {
        "label": "Outro sting", "kind": "video", "wiring": "live", "group": "Bookends",
        "multi": False, "per_episode": False, "generator": None,
        "upload": "always", "thumb": "poster",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["outro/*.mp4", "outro/*.png"],
            "exclude": ["outro/*.poster.jpg"],
        },
    },
    "outro_card_gen": {
        "label": "Outro card", "kind": "video", "wiring": "reference", "group": "Bookends",
        "multi": False, "per_episode": True, "generator": "gen_outro_card.py",
        "upload": "always", "thumb": "companion",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["*/outro_card.mp4"],
        },
    },
    "intro_sting": {
        "label": "Intro sting (legacy)", "kind": "video", "wiring": "reference",
        "group": "Bookends", "multi": False, "per_episode": False, "generator": None,
        "upload": "always", "thumb": "poster",
        "discover": {
            "root": "channel", "unit": "file", "order_by": "mtime",
            "globs": ["bookends/intro.mp4"],
        },
    },
    "hook_image": {
        "label": "Hook art", "kind": "image", "wiring": "reference", "group": "Opener",
        "multi": False, "per_episode": True, "generator": None,
        "upload": "always", "thumb": "downscale",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["*/hook_art/*", "*/hook.png", "*/hook_*.png", "*/hook_*.jpg",
                      "*/hook_art.png"],
            "exts": IMAGE_EXTS,
        },
    },
    "music_bed": {
        "label": "Music bed", "kind": "audio", "wiring": "locked", "group": "Sound",
        "multi": False, "per_episode": False, "generator": "Suno",
        # 21 MB of mp3 — only shipped at --tier full; waveform is synthesized client-side.
        "upload": "full", "thumb": "none",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["music/*.mp3"],
        },
    },
    "endcard": {
        "label": "End card", "kind": "image", "wiring": "reference", "group": "Bookends",
        "multi": False, "per_episode": False, "generator": None,
        "upload": "always", "thumb": "downscale",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["*/endcard*.png", "*/endcard*.jpg", "endcard*.png"],
            "exts": IMAGE_EXTS,
        },
    },
    "brand_watermark": {
        "label": "Watermark", "kind": "image", "wiring": "reference",
        "group": "Brand marks", "multi": False, "per_episode": False, "generator": None,
        "upload": "always", "thumb": "downscale",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["watermark*.png", "*/watermark*.png"],
        },
    },
    "brand_logo_pop": {
        "label": "Logo pop", "kind": "image", "wiring": "reference",
        "group": "Brand marks", "multi": False, "per_episode": False, "generator": None,
        "upload": "always", "thumb": "downscale",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["logo_pop*.png", "*/logo_pop*.png"],
        },
    },
    "brand_sol_badge": {
        "label": "Sol badge", "kind": "image", "wiring": "reference",
        "group": "Brand marks", "multi": False, "per_episode": False, "generator": None,
        "upload": "always", "thumb": "downscale",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["sol_badge*.png", "*/sol_badge*.png"],
        },
    },
    "channel_avatar": {
        "label": "Channel avatar", "kind": "image", "wiring": "reference",
        "group": "Channel art", "multi": False, "per_episode": False, "generator": None,
        "upload": "always", "thumb": "downscale",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["channel/avatar*.jpg", "channel/avatar*.png"],
        },
    },
    "channel_banner": {
        "label": "Channel banner", "kind": "image", "wiring": "reference",
        "group": "Channel art", "multi": False, "per_episode": False, "generator": None,
        "upload": "always", "thumb": "downscale",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["channel/banner*.jpg", "channel/banner*.png"],
        },
    },
    "broll_clip": {
        "label": "B-roll bank", "kind": "video", "wiring": "reference", "group": "Footage",
        "multi": True, "per_episode": False, "generator": None,
        # 20.9 MB of mp4 — bytes only at --tier full, but the poster is always cheap.
        "upload": "full", "thumb": "poster",
        "discover": {
            "root": "assets", "unit": "file", "order_by": "mtime",
            "globs": ["footage_bank/*.mp4"],
        },
    },
    # ---- ids / rules / code: nothing on disk to upload, storage_path stays null --------
    "remotion_comp": {
        "label": "Remotion composition", "kind": "id", "wiring": "locked", "group": "Code",
        "multi": False, "per_episode": False, "generator": None,
        "upload": "none", "thumb": "none", "discover": None,
        "static": [{"build_ref": "Short", "label": "Remotion composition id"}],
    },
    "step_chip_style": {
        "label": "Step chips", "kind": "style", "wiring": "reference", "group": "Code",
        "multi": False, "per_episode": False, "generator": None,
        "upload": "none", "thumb": "none", "discover": None,
        "static": [{"build_ref": "chip", "label": "STEP n/N glass chip + #NN hashtag card",
                    "note": "Short.tsx StepChip; corner in the 4th steps tuple"}],
    },
    "component_statbars": {
        "label": "StatBars", "kind": "code", "wiring": "reference", "group": "Code",
        "multi": False, "per_episode": False, "generator": None,
        "upload": "none", "thumb": "none", "discover": None,
        "static": [{"build_ref": "StatBars.tsx", "label": "StatBars chart component"}],
    },
    "component_outrocard": {
        "label": "OutroCard", "kind": "code", "wiring": "reference", "group": "Code",
        "multi": False, "per_episode": False, "generator": None,
        "upload": "none", "thumb": "none", "discover": None,
        "static": [{"build_ref": "OutroCard.tsx",
                    "label": "Premium OutroCard component (v16.2)"}],
    },
    "component_buildclub": {
        "label": "BuildClub", "kind": "code", "wiring": "reference", "group": "Code",
        "multi": False, "per_episode": False, "generator": None,
        "upload": "none", "thumb": "none", "discover": None,
        "static": [{"build_ref": "BuildClub.tsx", "label": "Build-Club kit component"}],
    },
}

# Revisions that are explicitly DEAD — registered so the board can show what was killed and
# why, but flagged `retired` + `retired_at` so they never surface as a pickable candidate.
# Keys are rel_paths as produced by the discovery walk.
RETIRED = {
    "outro/outro_sub_comment.old.mp4":
        "superseded by outro_sub_comment.mp4 (2026-08-06)",
    "outro/outro_chk.png":
        "QC contact sheet, never a shipped sting",
    "bookends/intro.mp4":
        "claude-tricks ships --intro-none per channels/BOOKENDS.md",
    "channel/avatar_host_v3.rust.bak.jpg":
        "backup copy taken before the rust-crew avatar swap",
    "channel/banner_v2_sheet.jpg":
        "contact sheet of the A/B/C banner options, not a banner",
}

# --------------------------------------------------------------------------------------
# accessors (never re-derive these anywhere else)
# --------------------------------------------------------------------------------------
def _titleize(s):
    return " ".join(w.capitalize() for w in str(s or "").replace("-", " ").replace("_", " ").split())


def asset_label(t):
    return (SLOTS.get(t) or {}).get("label") or _titleize(t)


def wiring_of(t):
    return (SLOTS.get(t) or {}).get("wiring") or "reference"


def slot_group(t):
    return (SLOTS.get(t) or {}).get("group") or "Other"


def slot_kind(t):
    return (SLOTS.get(t) or {}).get("kind") or "other"


def discover_of(t):
    return (SLOTS.get(t) or {}).get("discover")


def has_cover(kind):
    return kind in ("image", "video", "audio")


def ordered_slots():
    """Deterministic slot order: grouped, then declaration order inside a group."""
    groups, out = [], []
    for t in SLOTS:
        g = slot_group(t)
        if g not in groups:
            groups.append(g)
    for g in groups:
        out += [t for t in SLOTS if slot_group(t) == g]
    return out


if __name__ == "__main__":  # tiny self-check: keep in sync with webapp/src/assetCatalog.js
    print(f"{len(SLOTS)} slots")
    for t in ordered_slots():
        d = discover_of(t)
        print(f"  {t:<20} {slot_group(t):<12} {slot_kind(t):<6} {wiring_of(t):<10} "
              f"{'disk:' + d['unit'] if d else 'static'}")
