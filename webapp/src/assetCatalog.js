/**
 * assetCatalog — the single registry of brand-asset SLOTS.
 *
 * An `asset_type` is a SLOT: one thing chosen per render. Its VERSIONS are
 * interchangeable revisions of that slot (12 host outfits = 12 versions of
 * `host_outfit`, not 12 types) — that is what makes mix-and-match possible.
 *
 * asset_type is the join key across ingest / factory_asset_versions /
 * factory_asset_locks / build_ep_v2._LOCK_CFG_KEY, so these strings must not
 * drift. Collapses what used to be duplicated in Assets.jsx + templates.js +
 * TemplateDetail.jsx (labels, lineage walk, wiring map).
 */
import { mediaKind } from './mediaKind'

// kind drives the VISUAL treatment (not the file extension):
//   image|video|audio → cover band · code|id|style → body-only + mono chip
// wiring is the truth about the renderer:
//   live = build_ep_v2 resolves it · locked = lock exists, not yet wired · reference = catalogue only
export const SLOTS = {
  host_outfit:         { label: 'Host — Sol',           kind: 'image', wiring: 'live',      group: 'Host' },
  outro_sting:         { label: 'Outro sting',          kind: 'video', wiring: 'live',      group: 'Bookends', buildKey: 'outro_src' },
  outro_card_gen:      { label: 'Outro card',           kind: 'video', wiring: 'reference', group: 'Bookends', perEpisode: true, buildKey: 'outro_src' },
  intro_sting:         { label: 'Intro sting (legacy)', kind: 'video', wiring: 'reference', group: 'Bookends' },
  hook_image:          { label: 'Hook art',             kind: 'image', wiring: 'reference', group: 'Opener', perEpisode: true },
  music_bed:           { label: 'Music bed',            kind: 'audio', wiring: 'locked',    group: 'Sound' },
  endcard:             { label: 'End card',             kind: 'image', wiring: 'reference', group: 'Bookends' },
  brand_watermark:     { label: 'Watermark',            kind: 'image', wiring: 'reference', group: 'Brand marks' },
  brand_logo_pop:      { label: 'Logo pop',             kind: 'image', wiring: 'reference', group: 'Brand marks' },
  brand_sol_badge:     { label: 'Sol badge',            kind: 'image', wiring: 'reference', group: 'Brand marks' },
  channel_avatar:      { label: 'Channel avatar',       kind: 'image', wiring: 'reference', group: 'Channel art' },
  channel_banner:      { label: 'Channel banner',       kind: 'image', wiring: 'reference', group: 'Channel art' },
  demo_clip:           { label: 'Demo footage',          kind: 'video', wiring: 'reference', group: 'Footage', multi: true },
  broll_clip:          { label: 'B-roll bank',          kind: 'video', wiring: 'reference', group: 'Footage', multi: true },
  remotion_comp:       { label: 'Remotion composition', kind: 'id',    wiring: 'locked',    group: 'Code' },
  step_chip_style:     { label: 'Step chips',           kind: 'style', wiring: 'reference', group: 'Code' },
  component_statbars:  { label: 'StatBars',             kind: 'code',  wiring: 'reference', group: 'Code' },
  component_outrocard: { label: 'OutroCard',            kind: 'code',  wiring: 'reference', group: 'Code' },
  component_buildclub: { label: 'BuildClub',            kind: 'code',  wiring: 'reference', group: 'Code' },
}

const titleize = (s) =>
  String(s || '').replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

export const assetLabel = (t) => (SLOTS[t] && SLOTS[t].label) || titleize(t)
export const wiringOf = (t) => (SLOTS[t] && SLOTS[t].wiring) || 'reference'
export const slotGroup = (t) => (SLOTS[t] && SLOTS[t].group) || 'Other'

/** Visual kind for a card: declared non-media kind wins; media falls back to the extension. */
export function kindOf(asset_type, v) {
  const declared = SLOTS[asset_type] && SLOTS[asset_type].kind
  if (declared === 'code' || declared === 'id' || declared === 'style') return declared
  const path = (v && (v.thumb_path || v.storage_path)) || ''
  const k = mediaKind('', path)
  return k !== 'other' ? k : declared || 'other'
}

/** Only these kinds get a 16:9 cover band; the rest render body-only. */
export const hasCover = (k) => k === 'image' || k === 'video' || k === 'audio'

/** True only for a path an <img> can actually decode (an .mp3 cannot). */
export const isImagePath = (p) => !!p && mediaKind('', p) === 'image'

/**
 * HeyGen liveness of a revision (host_outfit today).
 *
 * A photo-avatar id can be FREED server-side — the account caps the pool at 3,
 * so registering a new face evicts an old one. The row keeps the id string, but
 * a render against it fails. meta.heygen records this as, e.g.
 *   { pip, wide, pip_state: "freed", pool_live: [<ids still registered>] }        // v11
 *   { rest, closeup, rest_state: "not_in_pool", closeup_state: "not_in_pool",     // v12
 *     pool_live: [<someone else's id>] }
 * So: every non-`_state`, non-`pool_live` string value is an avatar id, its
 * health is `<key>_state` (plus membership of a declared, non-empty pool_live),
 * and a revision is DEAD only when *every* id it declares is dead — v11 renders
 * fine off its wide avatar even though its pip id was freed.
 *
 * Returns { dead, reason, warn }. dead ⇒ never offer it as a pick.
 */
const DEAD_HEYGEN_STATES = new Set(['freed', 'not_in_pool', 'deleted', 'expired'])

export function heygenHealth(v) {
  const h = v && v.meta && v.meta.heygen
  if (!h || typeof h !== 'object') return { dead: false, reason: '', warn: '' }
  const idKeys = Object.keys(h).filter(
    (k) => k !== 'pool_live' && !k.endsWith('_state') && typeof h[k] === 'string',
  )
  if (idKeys.length === 0) return { dead: false, reason: '', warn: '' }
  const pool = Array.isArray(h.pool_live) && h.pool_live.length ? h.pool_live : null
  const deadKeys = idKeys.filter((k) => {
    const st = h[k + '_state']
    if (typeof st === 'string' && DEAD_HEYGEN_STATES.has(st)) return true
    return !!(pool && !pool.includes(h[k]))
  })
  if (deadKeys.length === 0) return { dead: false, reason: '', warn: '' }
  if (deadKeys.length === idKeys.length) {
    return {
      dead: true,
      reason: 'HeyGen id freed — won’t render',
      warn: '',
    }
  }
  return {
    dead: false,
    reason: '',
    warn: `${deadKeys.join(' + ')} face freed — the rest still render`,
  }
}

/* ── Usage backlinks (Phase 3) ────────────────────────────────────────────
 * `?r=asset_backlinks` returns usage keyed by factory_asset_versions.id, built
 * from factory_episode_assets_used — what a build ACTUALLY resolved, not what
 * the locks say today.
 *
 * HONESTY RULE: provenance recording only began with migration 021. A revision
 * with no entry may still have shipped many times before that day, so absence
 * means NOT RECORDED — never "never used". Every helper below therefore returns
 * '' for absence, so no caller can accidentally render a "0".
 */

/** The usage entry for a revision, or null when nothing is recorded. */
export const usageOf = (usage, id) => (id && usage && usage[id]) || null

/** Rail badge: "3 eps" · '' when nothing is recorded (render nothing, not 0). */
export function usageBadge(u) {
  if (!u || !u.episodes) return ''
  return u.episodes + (u.episodes > 1 ? ' eps' : ' ep')
}

/** Card line: "shipped in 3 · in 1 cast" · '' when nothing is recorded. */
export function usageSummary(u) {
  if (!u) return ''
  const bits = []
  if (u.shipped > 0) bits.push('shipped in ' + u.shipped)
  else if (u.episodes > 0) bits.push('built into ' + u.episodes)
  if (u.casts > 0) bits.push('in ' + u.casts + (u.casts > 1 ? ' casts' : ' cast'))
  return bits.join(' · ')
}

/** Hover detail — names the episodes/casts. '' when nothing is recorded. */
export function usageTitle(u) {
  if (!u) return ''
  const lines = []
  if (u.episodes > 0) {
    lines.push(
      'Recorded in ' + u.episodes + (u.episodes > 1 ? ' episode builds' : ' episode build') +
        (u.shipped > 0 ? ' · ' + u.shipped + ' shipped' : ''),
    )
  }
  for (const v of u.videos || []) {
    lines.push(
      '• ' + (v.yt_title || v.video_id) +
        (v.publish_at ? ' — ' + String(v.publish_at).slice(0, 10) : ''),
    )
  }
  for (const t of u.template_versions || []) {
    lines.push('• cast ' + t.template_key + ' v' + t.version + (t.label ? ' — ' + t.label : ''))
  }
  return lines.join('\n')
}

/**
 * Slots feeding the SAME build key are interchangeable picks in a cast.
 *
 * outro_sting (shared subscribe/comment sting) and outro_card_gen (per-episode
 * question-CTA card) are both substituted into `outro_src` — the Artifacts short
 * shipped with the CARD, not the sting. Modelling them as separate, un-swappable
 * slots made the thing we actually published unchoosable in the composer.
 */
export function interchangeableWith(assetType) {
  const key = SLOTS[assetType] && SLOTS[assetType].buildKey
  if (!key) return [assetType]
  return Object.keys(SLOTS).filter((t) => (SLOTS[t] || {}).buildKey === key)
}

/** "v3 ← v2 ← v1"; '' for a single-version chain (nothing worth showing). */
export function lineageOf(v, byId) {
  const chain = []
  const seen = new Set()
  let cur = v
  while (cur && !seen.has(cur.id)) {
    seen.add(cur.id)
    chain.push('v' + cur.version)
    cur = cur.parent_version_id ? byId[cur.parent_version_id] : null
  }
  return chain.length > 1 ? chain.join(' ← ') : ''
}
