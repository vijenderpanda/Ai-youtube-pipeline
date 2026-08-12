import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { RENDERS_BASE } from '../config'
import { usePoll } from '../hooks'
import {
  resolveAccents,
  accentFor,
  channelEmoji,
  channelMonogram,
} from '../channelColor'
import CalendarStatusChip from '../components/CalendarStatusChip'
import EmptyState from '../components/EmptyState'
import PlanContentModal from '../components/PlanContentModal'
import Toast, { useToast } from '../components/Toast'
import { fmtDayHeading } from '../format'

/**
 * Studio — staged fragment production (see docs/STAGED-PIPELINE.md §5).
 * One card per in-flight episode; click through to its asset board.
 *
 * v17 polish: each card leads with the episode's real cover art (falling back to
 * a branded gradient + channel glyph when no servable image exists yet), names
 * the channel explicitly, and the grid gains search + channel + status filters
 * so a specific post is easy to find at a glance.
 */

// Which status "lane" a card belongs to, for the filter + sort.
function laneOf(it, c) {
  if (it.status === 'produced') return 'produced'
  if ((c.failed || 0) > 0) return 'attention'
  if ((c.review || 0) > 0) return 'review'
  if ((c.generating || 0) > 0 || (c.total || 0) === 0) return 'producing'
  return 'ready'
}

const STATUS_TABS = [
  { key: 'all', label: 'All' },
  { key: 'producing', label: 'Producing' },
  { key: 'review', label: 'In review' },
  { key: 'ready', label: 'Ready' },
  { key: 'produced', label: 'Produced' },
  { key: 'attention', label: 'Needs attention' },
]

export default function Studio() {
  const stagedQ = usePoll(() => api.get('?r=staged'), 15000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const navigate = useNavigate()
  const [modalOpen, setModalOpen] = useState(false)
  const [q, setQ] = useState('')
  const [chanFilter, setChanFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const { toast, show } = useToast()

  const items = (stagedQ.data && stagedQ.data.items) || []
  const counts = (stagedQ.data && stagedQ.data.counts) || {}
  const covers = (stagedQ.data && stagedQ.data.covers) || {}
  const channels = (chansQ.data && chansQ.data.channels) || []
  const accents = useMemo(() => resolveAccents(channels), [channels])
  const chanName = useMemo(() => {
    const m = {}
    for (const c of channels) m[c.key] = c.name || c.key
    return m
  }, [channels])

  // Channels present in the current staged set, for the filter row.
  const chanChips = useMemo(() => {
    const seen = new Map()
    for (const it of items) seen.set(it.channel_key, (seen.get(it.channel_key) || 0) + 1)
    return [...seen.entries()]
      .map(([key, n]) => ({ key, n, name: chanName[key] || key }))
      .sort((a, b) => b.n - a.n || a.name.localeCompare(b.name))
  }, [items, chanName])

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return items
      .map((it) => ({ it, c: counts[it.id] || {}, lane: laneOf(it, counts[it.id] || {}) }))
      .filter(({ it, lane }) => {
        if (chanFilter !== 'all' && it.channel_key !== chanFilter) return false
        if (statusFilter !== 'all' && lane !== statusFilter) return false
        if (needle) {
          const hay = `${it.title || ''} ${it.channel_key} ${chanName[it.channel_key] || ''}`.toLowerCase()
          if (!hay.includes(needle)) return false
        }
        return true
      })
  }, [items, counts, q, chanFilter, statusFilter, chanName])

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

  const nothingStaged = !stagedQ.loading && items.length === 0
  const noMatches = items.length > 0 && filtered.length === 0

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

      {items.length > 0 && (
        <div className="studio-toolbar">
          <div className="studio-search">
            <span className="studio-search-icon" aria-hidden="true">⌕</span>
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search episodes…"
              aria-label="Search episodes"
            />
            {q && (
              <button className="studio-search-clear" onClick={() => setQ('')} aria-label="Clear search">
                ×
              </button>
            )}
          </div>

          {chanChips.length > 1 && (
            <div className="studio-filter-row" role="tablist" aria-label="Filter by channel">
              <button
                className={'chan-filter' + (chanFilter === 'all' ? ' on' : '')}
                onClick={() => setChanFilter('all')}
              >
                All channels
              </button>
              {chanChips.map((c) => (
                <button
                  key={c.key}
                  className={'chan-filter' + (chanFilter === c.key ? ' on' : '')}
                  style={{ '--ch': accentFor(c.key, accents) }}
                  onClick={() => setChanFilter((f) => (f === c.key ? 'all' : c.key))}
                  title={c.key}
                >
                  <span className="chan-filter-dot" />
                  {channelEmoji(c.key) && <span className="chan-filter-emoji">{channelEmoji(c.key)}</span>}
                  {c.name}
                  <span className="chan-filter-n">{c.n}</span>
                </button>
              ))}
            </div>
          )}

          <div className="studio-status-tabs" role="tablist" aria-label="Filter by status">
            {STATUS_TABS.map((t) => (
              <button
                key={t.key}
                className={'status-tab' + (statusFilter === t.key ? ' on' : '')}
                onClick={() => setStatusFilter(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {stagedQ.loading && stagedQ.data == null ? (
        <p className="dim">Loading…</p>
      ) : nothingStaged ? (
        <EmptyState
          message="Nothing staged yet"
          hint="Open a planned item on the Calendar and choose “Produce in stages” — the factory plans the asset list, generates each fragment as its own job, and you review them all here before the final assembly."
        />
      ) : noMatches ? (
        <EmptyState
          message="No episodes match"
          hint="Try a different search term or clear the channel / status filters."
        />
      ) : (
        <div className="studio-grid">
          {filtered.map(({ it, c }) => {
            const accent = accentFor(it.channel_key, accents)
            const total = c.total || 0
            const done = (c.approved || 0) + (c.skipped || 0)
            const pct = total ? Math.round((done / total) * 100) : 0
            const coverPath = covers[it.id]
            const coverUrl = coverPath ? RENDERS_BASE + coverPath : null
            const emoji = channelEmoji(it.channel_key)
            const name = chanName[it.channel_key] || it.channel_key
            return (
              <Link
                key={it.id}
                className="card studio-card"
                to={`/studio/${it.id}`}
                style={{ '--ch': accent }}
              >
                <div className={'studio-cover' + (coverUrl ? '' : ' studio-cover-fallback')}>
                  {coverUrl ? (
                    <img src={coverUrl} alt="" loading="lazy" />
                  ) : (
                    <span className="studio-cover-glyph" aria-hidden="true">
                      {emoji || channelMonogram(name)}
                    </span>
                  )}
                  <span className="studio-cover-chan">
                    <span className="studio-cover-dot" />
                    {name}
                  </span>
                  {(c.generating || 0) > 0 && (
                    <span className="studio-cover-live">
                      <span className="live-dot" /> live
                    </span>
                  )}
                </div>

                <div className="studio-card-body">
                  <div className="studio-card-title">{it.title || '(untitled)'}</div>
                  <div className="studio-card-sub">
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
                </div>
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
