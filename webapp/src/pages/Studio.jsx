import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { resolveAccents, accentFor } from '../channelColor'
import CalendarStatusChip from '../components/CalendarStatusChip'
import EmptyState from '../components/EmptyState'
import { fmtDayHeading } from '../format'

/**
 * Studio — staged fragment production (see docs/STAGED-PIPELINE.md §5).
 * One card per staged episode; click through to its asset board.
 */
export default function Studio() {
  const stagedQ = usePoll(() => api.get('?r=staged'), 15000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)

  const items = (stagedQ.data && stagedQ.data.items) || []
  const counts = (stagedQ.data && stagedQ.data.counts) || {}
  const channels = (chansQ.data && chansQ.data.channels) || []
  const accents = useMemo(() => resolveAccents(channels), [channels])

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Studio</h1>
          <p className="sub">Staged production · review every asset before assembly</p>
        </div>
      </header>

      {stagedQ.error && <div className="error-bar">{stagedQ.error.message}</div>}

      {stagedQ.loading && stagedQ.data == null ? (
        <p className="dim">Loading…</p>
      ) : items.length === 0 ? (
        <EmptyState
          message="Nothing staged yet"
          hint="Open a planned item on the Calendar and choose “Produce in stages” — the factory plans the asset list, generates each fragment as its own job, and you review them all here before the final assembly."
        />
      ) : (
        <div className="studio-grid">
          {items.map((it) => {
            const accent = accentFor(it.channel_key, accents)
            const c = counts[it.id] || {}
            const total = c.total || 0
            const done = (c.approved || 0) + (c.skipped || 0)
            const pct = total ? Math.round((done / total) * 100) : 0
            // Tiny filmstrip motif: up to 12 frames, filled = share done
            const frames = Math.min(total, 12)
            const filled = total ? Math.round((done / total) * frames) : 0
            return (
              <Link
                key={it.id}
                className="card studio-card"
                to={`/studio/${it.id}`}
                style={{ '--ch': accent }}
              >
                <div className="studio-card-title">{it.title || '(untitled)'}</div>
                <div className="studio-card-sub">
                  <span className="tag chan-tag">
                    <span className="chan-tag-dot" style={{ background: accent }} />
                    {it.channel_key}
                  </span>
                  {it.planned_date && (
                    <span className="dim small">
                      {fmtDayHeading(String(it.planned_date).slice(0, 10))}
                    </span>
                  )}
                  {it.status === 'produced' && <CalendarStatusChip status="produced" />}
                </div>
                {total === 0 ? (
                  <div className="studio-card-planning">
                    <span className="asset-pulse" />
                    Planning assets…
                  </div>
                ) : (
                  <>
                    <div className="studio-mini-strip" aria-hidden="true">
                      {Array.from({ length: frames }).map((_, i) => (
                        <span key={i} className={'mini-cell' + (i < filled ? ' on' : '')} />
                      ))}
                      <span className="mini-count">
                        {total} step{total === 1 ? '' : 's'}
                      </span>
                    </div>
                    <div className="progress studio-card-progress">
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="progress-label">
                        {done}/{total} ready
                      </span>
                    </div>
                    <div className="studio-card-chips">
                      {(c.generating || 0) > 0 && (
                        <span className="chip chip-running">
                          <span className="chip-dot" />
                          {c.generating} generating
                        </span>
                      )}
                      {(c.review || 0) > 0 && (
                        <span className="chip asset-review">
                          <span className="chip-dot" />
                          {c.review} in review
                        </span>
                      )}
                      {(c.failed || 0) > 0 && (
                        <span className="chip chip-failed">
                          <span className="chip-dot" />
                          {c.failed} failed
                        </span>
                      )}
                    </div>
                  </>
                )}
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
