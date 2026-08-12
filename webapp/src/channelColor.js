/**
 * Channel color identity (v7 calendar design language).
 *
 * Source of truth is factory_channels.accent (hex, set via update_channel).
 * When a channel has no valid hex accent we fall back to a fixed, tasteful
 * palette for the known channels, then to a stable hashed palette for
 * anything new — so every channel always has a distinguishable color.
 */

export const CHANNEL_PALETTE = {
  lulla: '#7C9CF5', // moonlit blue
  'claude-tricks': '#E91E63', // magenta
  vehicles: '#F59E0B', // amber-orange
  aashiqana: '#F472B6', // rose
  'language-abc': '#34D399', // mint
  'already-happening': '#22D3EE', // electric teal
  _network: '#94A3B8', // factory-wide items — neutral steel
}

const HASH_PALETTE = [
  '#7C9CF5',
  '#F472B6',
  '#34D399',
  '#F59E0B',
  '#38BDF8',
  '#C084FC',
  '#FB7185',
  '#A3E635',
]

const isHex = (s) => /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(String(s || '').trim())

export function hashColor(key) {
  const s = String(key || '')
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return HASH_PALETTE[h % HASH_PALETTE.length]
}

/** channels (from ?r=channels) -> { channel_key: '#hex' } */
export function resolveAccents(channels) {
  const m = { ...CHANNEL_PALETTE }
  for (const c of channels || []) {
    if (isHex(c.accent)) m[c.key] = c.accent.trim()
    else if (!m[c.key]) m[c.key] = hashColor(c.key)
  }
  return m
}

export function accentFor(key, accents) {
  return (accents && accents[key]) || CHANNEL_PALETTE[key] || hashColor(key)
}
