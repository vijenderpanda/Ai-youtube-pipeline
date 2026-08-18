/**
 * Template-library helpers (Studio redesign, Phase A) — pure, no React.
 *
 * The factory_templates registry is "every production pipeline as data". These
 * helpers answer the three questions the Template Library UI asks of a row:
 *   1. which channel actually produces with it? (templateForChannel)
 *   2. can it arm an episode yet, or is it still a starter? (armable)
 *   3. for a given brand asset_type, is it truly rendered, merely locked, or
 *      just tracked for reference? (wiringOf)
 * plus a human label map shared by the list + quick-look (assetLabel).
 */

/** The channel row whose `.template` names this template key (or null). */
export function templateForChannel(channels, templateKey) {
  if (!templateKey) return null
  for (const c of channels || []) {
    if (c && c.template === templateKey) return c
  }
  return null
}

/** A template can arm an episode only once it has a finalize_script wired. */
export function armable(tpl) {
  return !!(tpl && tpl.finalize_script)
}

/**
 * Wiring of a brand asset_type in build_ep_v2:
 *   'live'      — actually rendered into every episode today
 *   'locked'    — a version is locked, but the renderer doesn't consume it yet
 *   'reference' — tracked for visibility only (components, per-episode gens)
 */
const WIRING = {
  outro_sting: 'live',
  host_outfit: 'live',
  music_bed: 'locked',
  remotion_comp: 'locked',
}
export function wiringOf(asset_type) {
  return WIRING[asset_type] || 'reference'
}

// Human labels for known asset types; unknown kinds titleize their key so new
// asset types still read cleanly without a code change.
const ASSET_LABELS = {
  host_outfit: 'Host — Sol',
  outro_sting: 'Outro sting',
  outro_card_gen: 'Outro card',
  music_bed: 'Music bed',
  step_chip_style: 'Step chips',
  remotion_comp: 'Remotion composition',
  component_statbars: 'StatBars',
  component_outrocard: 'OutroCard',
  component_buildclub: 'BuildClub',
}
const titleize = (s) =>
  String(s || '').replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
export function assetLabel(asset_type) {
  return ASSET_LABELS[asset_type] || titleize(asset_type)
}
