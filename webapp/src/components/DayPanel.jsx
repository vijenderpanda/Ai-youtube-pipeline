import CalItem from './CalItem'
import EmptyState from './EmptyState'
import { fmtDayHeading } from '../format'

/**
 * v7 — a day's full cards. Side drawer on desktop, bottom sheet on phones.
 * Challenges render inside the challenged original's card (via CalItem →
 * ChallengeBlock), never standalone.
 */
export default function DayPanel({
  date,
  items,
  accents,
  postByJob,
  dispById = new Map(),
  challengerByTarget,
  onClose,
  onOpenItem,
  onMoveToToday,
  onRunImproved,
  onKeepOriginal,
  challengeBusy,
}) {
  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer day-panel">
        <div className="sheet-handle" aria-hidden="true" />
        <div className="drawer-head">
          <div>
            <h3 className="drawer-title">{fmtDayHeading(date)}</h3>
            <div className="drawer-chips">
              <span className="tag dim-tag">
                {items.length} {items.length === 1 ? 'item' : 'items'}
              </span>
            </div>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="drawer-body">
          {items.length === 0 ? (
            <EmptyState
              message="Nothing on this day"
              hint="Plan content with “+ Plan content”, or let the AI suggest the slate."
            />
          ) : (
            <div className="cal-list">
              {items.map((it) => (
                <CalItem
                  key={it.id}
                  item={it}
                  accent={accents[it.channel_key] || '#E91E63'}
                  post={it.job_id ? postByJob.get(it.job_id) : null}
                  disp={dispById.get(it.id)}
                  detail
                  challenger={challengerByTarget.get(it.id) || null}
                  onClick={() => onOpenItem(it.id)}
                  onMoveToToday={onMoveToToday}
                  onRunImproved={onRunImproved}
                  onKeepOriginal={onKeepOriginal}
                  challengeBusy={challengeBusy}
                />
              ))}
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
