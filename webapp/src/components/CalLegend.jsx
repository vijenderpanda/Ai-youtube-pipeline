import { LIFECYCLE_LABELS } from '../lifecycle'
import { ClockCheckGlyph, PlayGlyph } from './glyphs'

/**
 * v7 — compact strip that teaches the calendar language: fill treatment =
 * lifecycle. Swatches use a neutral slate so no channel color is implied
 * (channel colors live on the filter chips and the pills themselves).
 */
const NEUTRAL = '#8f9bb3'
const STATES = ['planned', 'suggested', 'queued', 'produced', 'armed', 'published', 'skipped']

export default function CalLegend() {
  return (
    <div className="cal-legend" aria-label="Calendar legend">
      {STATES.map((s) => (
        <span key={s} className={'mpill leg-pill lc-' + s} style={{ '--ch': NEUTRAL }}>
          <span className="mpill-title">{LIFECYCLE_LABELS[s]}</span>
          {s === 'suggested' && <span className="mpill-ai">AI</span>}
          {s === 'armed' && <span className="mpill-glyph glyph-armed">{ClockCheckGlyph}</span>}
          {s === 'published' && (
            <span className="mpill-glyph glyph-published">{PlayGlyph}</span>
          )}
        </span>
      ))}
      <span className="leg-extra">
        <span className="leg-warn" /> challenged
      </span>
    </div>
  )
}
