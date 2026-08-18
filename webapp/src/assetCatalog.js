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
  outro_sting:         { label: 'Outro sting',          kind: 'video', wiring: 'live',      group: 'Bookends' },
  outro_card_gen:      { label: 'Outro card',           kind: 'video', wiring: 'reference', group: 'Bookends', perEpisode: true },
  intro_sting:         { label: 'Intro sting (legacy)', kind: 'video', wiring: 'reference', group: 'Bookends' },
  hook_image:          { label: 'Hook art',             kind: 'image', wiring: 'reference', group: 'Opener', perEpisode: true },
  music_bed:           { label: 'Music bed',            kind: 'audio', wiring: 'locked',    group: 'Sound' },
  endcard:             { label: 'End card',             kind: 'image', wiring: 'reference', group: 'Bookends' },
  brand_watermark:     { label: 'Watermark',            kind: 'image', wiring: 'reference', group: 'Brand marks' },
  brand_logo_pop:      { label: 'Logo pop',             kind: 'image', wiring: 'reference', group: 'Brand marks' },
  brand_sol_badge:     { label: 'Sol badge',            kind: 'image', wiring: 'reference', group: 'Brand marks' },
  channel_avatar:      { label: 'Channel avatar',       kind: 'image', wiring: 'reference', group: 'Channel art' },
  channel_banner:      { label: 'Channel banner',       kind: 'image', wiring: 'reference', group: 'Channel art' },
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
