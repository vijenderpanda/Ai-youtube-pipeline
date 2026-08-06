import { LIFECYCLE_LABELS } from '../lifecycle'
import { ClockCheckGlyph, PlayGlyph } from './glyphs'

/**
 * v7 — chip for a calendar item's lifecycle state. `status` accepts both raw
 * calendar statuses and the joined lifecycle states 'armed' / 'published'.
 */
export default function CalendarStatusChip({ status }) {
  const s = String(status || 'planned').toLowerCase()
  return (
    <span className={`chip cal-${s}`}>
      {s === 'armed' ? (
        ClockCheckGlyph
      ) : s === 'published' ? (
        PlayGlyph
      ) : (
        <span className="chip-dot" />
      )}
      {LIFECYCLE_LABELS[s] || s}
    </span>
  )
}
