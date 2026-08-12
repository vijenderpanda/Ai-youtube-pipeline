import { useMemo } from 'react'
import { toISODate } from '../format'
import { lifecycleOf, LIFECYCLE_LABELS } from '../lifecycle'
import { ClockCheckGlyph, PlayGlyph, EarlyGlyph } from './glyphs'

const WrenchSm = (
  <svg
    width="10"
    height="10"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
  </svg>
)

const DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const MAX_PILLS = 3

function Pill({ item, accent, lc, challenged, urgent, disp }) {
  const factory = item.kind === 'factory'
  const early = !!(disp && disp.early)
  const bits = [item.title || '(untitled)', LIFECYCLE_LABELS[lc] || lc]
  if (early) bits.push('early — ' + disp.earlyTip)
  if (challenged) bits.push('AI challenges this plan')
  if (urgent) bits.push('urgent — decide before publish')
  return (
    <div
      className={
        'mpill lc-' + lc +
        (factory ? ' kind-factory' : '') +
        (challenged ? ' challenged' : '') +
        (urgent ? ' urgent' : '')
      }
      style={{ '--ch': accent }}
      title={bits.join(' — ')}
    >
      {factory && <span className="mpill-wrench">{WrenchSm}</span>}
      <span className="mpill-title">{item.title || '(untitled)'}</span>
      {lc === 'suggested' && <span className="mpill-ai">AI</span>}
      {early && <span className="mpill-glyph glyph-early">{EarlyGlyph}</span>}
      {lc === 'armed' && <span className="mpill-glyph glyph-armed">{ClockCheckGlyph}</span>}
      {lc === 'published' && <span className="mpill-glyph glyph-published">{PlayGlyph}</span>}
      {challenged && <span className="mpill-warn" />}
    </div>
  )
}

/**
 * v7 — Month grid (Mon-start). Pills speak the calendar language: channel
 * color = left edge + tint, lifecycle = fill treatment (see CalLegend).
 * On phones pills collapse to colored bars and the day shows a count badge.
 */
export default function MonthGrid({
  cursor,
  items,
  accents,
  postByJob,
  dispById = new Map(),
  challengedIds,
  urgentIds = new Set(),
  onDayClick,
}) {
  const month = cursor.getMonth()

  const days = useMemo(() => {
    const y = cursor.getFullYear()
    const m = cursor.getMonth()
    const offset = (new Date(y, m, 1).getDay() + 6) % 7 // Mon = 0
    const daysInMonth = new Date(y, m + 1, 0).getDate()
    const total = Math.ceil((offset + daysInMonth) / 7) * 7 // 5–6 weeks
    const out = []
    for (let i = 0; i < total; i++) out.push(new Date(y, m, 1 - offset + i))
    return out
  }, [cursor])

  const byDate = useMemo(() => {
    const map = new Map()
    for (const it of items) {
      // Smart date: publish_at wins over planned_date (see calDisplay).
      const d =
        (dispById.get(it.id) || {}).displayDate ||
        String(it.planned_date || '').slice(0, 10)
      if (!d) continue
      if (!map.has(d)) map.set(d, [])
      map.get(d).push(it)
    }
    return map
  }, [items, dispById])

  const todayStr = toISODate(new Date())

  return (
    <div className="card mgrid">
      <div className="mgrid-head">
        {DOW.map((d) => (
          <span key={d} className="mgrid-hcell">
            {d}
          </span>
        ))}
      </div>
      <div className="mgrid-body">
        {days.map((d) => {
          const ds = toISODate(d)
          const dayItems = byDate.get(ds) || []
          const shown = dayItems.slice(0, MAX_PILLS)
          const extra = dayItems.length - shown.length
          return (
            <div
              key={ds}
              className={
                'mday' +
                (d.getMonth() !== month ? ' out' : '') +
                (ds === todayStr ? ' today' : '')
              }
              role="button"
              tabIndex={0}
              aria-label={ds}
              onClick={() => onDayClick(ds)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onDayClick(ds)
                }
              }}
            >
              <div className="mday-num">
                {dayItems.length > 0 && (
                  <span className="mday-count">{dayItems.length}</span>
                )}
                <span className="mday-date">{d.getDate()}</span>
              </div>
              <div className="mday-pills">
                {shown.map((it) => (
                  <Pill
                    key={it.id}
                    item={it}
                    accent={accents[it.channel_key] || '#94A3B8'}
                    lc={lifecycleOf(it, it.job_id ? postByJob.get(it.job_id) : null)}
                    challenged={challengedIds.has(it.id)}
                    urgent={urgentIds.has(it.id)}
                    disp={dispById.get(it.id)}
                  />
                ))}
                {extra > 0 && <div className="mday-more">+{extra} more</div>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
