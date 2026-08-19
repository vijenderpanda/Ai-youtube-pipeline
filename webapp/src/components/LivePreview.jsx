import { useMemo } from 'react'
import { Player } from '@remotion/player'
// The REAL production composition, imported unchanged via the vite alias so the
// preview renders exactly what build_ep_v2 → npx remotion render will produce.
// (Kept in a lazy-loaded chunk by the importer, so remotion only loads on demand.)
import { Short, totalDuration } from '@remotion-src/Short'

// Root.tsx registers Short at 1080×1920, 30fps — match it exactly.
const FPS = 30
const W = 1080
const H = 1920
const DEFAULT_DUR = 4 // placeholder seconds for a block with no config.dur (VO sets the real timing at produce)

/**
 * blockToSegment — the browser twin of build_ep_v2._seq_segment(). Converts one
 * DRAFT sequence block ({block_type, layout, config}) into a Short `Seg`, using
 * the EXACT Short.tsx contract field names. Returns null for a block that carries
 * nothing renderable here (hook/statbars/outro with no cookbook payload), mirroring
 * _seq_segment so the structural preview matches the eventual render.
 *
 * STRUCTURAL preview: no generated assets exist in the app, so a slot's host.src
 * is intentionally dropped (SlotScene shows its host placeholder); the cookbook
 * b-roll — the designable part — renders fully (cookbook components are pure TS,
 * no external files). VO/captions/host clips fill in at produce time.
 */
function blockToSegment(b) {
  const conf = (b && b.config) || {}
  const dur = typeof conf.dur === 'number' && conf.dur > 0 ? conf.dur : DEFAULT_DUR
  if (b.block_type === 'slot') {
    const hostIn = conf.host || {}
    const brollIn = conf.broll || {}
    const slot = { layout: conf.layout || b.layout }
    const label = hostIn.label || hostIn.id
    if (label) slot.host = { label } // host.src dropped — no asset in the app
    if (brollIn && brollIn.id) {
      slot.broll = { kind: 'cookbook', id: brollIn.id, props: brollIn.props || {} }
    }
    if (conf.tag) slot.tag = conf.tag
    return { kind: 'slot', dur, slot }
  }
  const cb = conf.cookbook
  if (cb && typeof cb.id === 'string' && cb.id) {
    const seg = { kind: 'cookbook', dur, cookbook: { id: cb.id, props: cb.props || {} } }
    if ('transparent' in cb) seg.cookbook.transparent = cb.transparent
    return seg
  }
  return null
}

/**
 * LivePreview — client-side, zero-API-cost structural preview of a composition
 * sequence. Feeds the draft blocks through the real Short composition in an
 * embedded @remotion/player. Lazy-loaded by SequenceEditor so remotion is not in
 * the main bundle.
 */
export default function LivePreview({ blocks = [], style = 'classic' }) {
  const props = useMemo(() => {
    const segments = [...blocks]
      .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
      .map(blockToSegment)
      .filter(Boolean)
    return { segments, captions: [], vo: '', style } // vo:'' is the Root.tsx fallback — safe in the Player
  }, [blocks, style])

  const durationInFrames = Math.max(1, Math.round(totalDuration(props) * FPS))
  const renderable = props.segments.length

  return (
    <div style={{ marginTop: 4, marginBottom: 12 }}>
      <div
        style={{
          width: 240,
          maxWidth: '100%',
          margin: '0 auto',
          borderRadius: 12,
          overflow: 'hidden',
          border: '1px solid var(--border)',
          background: '#000',
          aspectRatio: '9 / 16',
        }}
      >
        <Player
          component={Short}
          inputProps={props}
          durationInFrames={durationInFrames}
          fps={FPS}
          compositionWidth={W}
          compositionHeight={H}
          style={{ width: '100%', height: '100%' }}
          controls
          loop
          acknowledgeRemotionLicense
        />
      </div>
      <div className="dim small" style={{ textAlign: 'center', marginTop: 8 }}>
        {renderable
          ? `Structural preview — ${renderable} block${renderable === 1 ? '' : 's'}. VO, captions, and host clips fill in at produce; block durations are placeholders.`
          : 'No renderable blocks yet — add a b-roll/slot block with a cookbook component to preview it.'}
      </div>
    </div>
  )
}
