import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { resolveAccents, accentFor } from '../channelColor'
import CalendarStatusChip from '../components/CalendarStatusChip'
import EmptyState from '../components/EmptyState'
import PlanContentModal from '../components/PlanContentModal'
import Toast, { useToast } from '../components/Toast'
import { fmtDayHeading } from '../format'

/**
 * Studio — staged fragment production (see docs/STAGED-PIPELINE.md §5).
 * One card per staged episode; click through to its asset board.
 * "+ New project" (v16) creates the calendar row AND stages it in one flow, so
 * every asset generated for a post lives inside its Studio project from the
 * start — no local scaffolding, no post-hoc syncing.
 */
export default function Studio() {
  const stagedQ = usePoll(() => api.get('?r=staged'), 15000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const navigate = useNavigate()
  const [modalOpen, setModalOpen] = useState(false)
  const { toast, show } = useToast()

  const items = (stagedQ.data && stagedQ.data.items) || []
  const counts = (stagedQ.data && stagedQ.data.counts) || {}
  const channels = (chansQ.data && chansQ.data.channels) || []
  const accents = useMemo(() => resolveAccents(channels), [channels])

  // Plan modal returns the fresh calendar item; we stage it immediately so the
  // user lands on the Studio board with plan_assets already queued.
  const onCreated = async (item) => {
    if (!item || !item.id) {
      show('Created but no id returned — open the calendar to stage manually.', 'error')
      setModalOpen(false)
      return
    }
    try {
      await api.post({ action: 'stage_calendar_item', id: item.id })
    } catch (err) {
      show('Created but staging failed: ' + err.message + ' — open on the calendar and try again.', 'error')
      setModalOpen(false)
      return
    }
    setModalOpen(false)
    navigate('/studio/' + item.id)
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Studio</h1>
          <p className="sub">Staged production · review every asset before assembly</p>
        </div>
        <div className="head-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setModalOpen(true)}
            disabled={channels.length === 0}
            title={channels.length === 0 ? 'Loading channels…' : 'Create a new Studio project'}
          >
            + New project
          </button>
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

      {modalOpen && (
        <PlanContentModal
          channels={channels}
          onClose={() => setModalOpen(false)}
          onCreated={onCreated}
        />
      )}
      <Toast toast={toast} />
    </div>
  )
}
