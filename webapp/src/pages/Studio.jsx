import { Fragment, useMemo, useState } from 'react'
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
import StudioLauncher from '../components/StudioLauncher'
import { fmtDayHeading } from '../format'
import { STAGES, stageIndex, resolveStage } from '../pipeline'

// Card stage badge: one word for "where is this piece?", coloured per stage.
const STAGE_BADGE = {
  plan: { label: 'PLANNING', tone: 'plan' },
  produce: { label: 'PRODUCING', tone: 'produce' },
  qc: { label: 'REVIEW', tone: 'qc' },
  arm: { label: 'READY', tone: 'arm' },
  live: { label: 'SCHEDULED', tone: 'live' },
}

/**
 * Studio — staged fragment production (see docs/STAGED-PIPELINE.md §5).
 * One card per in-flight episode; click through to its asset board.
 *
 * v17 polish: each card leads with the episode's real cover art (falling back to
 * a branded gradient + channel glyph when no servable image exists yet), names
 * the channel explicitly, and the grid gains search + channel + status filters
 * so a specific post is easy to find at a glance.
 */

// A DIRECT monolithic produce stamps preview_path only when it FINISHES, so a
// direct item that has none yet is still producing — even when every pushed
// asset already reads "approved". Used to keep the card's badge/rail/lane from
// flipping to READY mid-run. (The board is authoritative via the live job; this
// grid infers from the calendar row it already has.)
const isProducing = (it) => it.production_mode === 'direct' && !it.preview_path

// Which status "lane" a card belongs to, for the filter + sort.
function laneOf(it, c) {
  if (it.status === 'produced') return 'produced'
  if ((c.failed || 0) > 0) return 'attention'
  if ((c.review || 0) > 0) return 'review'
  if (isProducing(it) || (c.generating || 0) > 0 || (c.total || 0) === 0) return 'producing'
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

const FORMAT_TABS = [
  { key: 'all', label: 'All formats' },
  { key: 'short', label: 'Shorts' },
  { key: 'longform', label: 'Long-form' },
]
const formatOf = (it) => it.format || 'short' // pre-migration rows are Shorts

export default function Studio() {
  const stagedQ = usePoll(() => api.get('?r=staged'), 15000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [chanFilter, setChanFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [formatFilter, setFormatFilter] = useState('all')

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
        if (formatFilter !== 'all' && formatOf(it) !== formatFilter) return false
        if (needle) {
          const hay = `${it.title || ''} ${it.channel_key} ${chanName[it.channel_key] || ''}`.toLowerCase()
          if (!hay.includes(needle)) return false
        }
        return true
      })
  }, [items, counts, q, chanFilter, statusFilter, formatFilter, chanName])

  const nothingStaged = !stagedQ.loading && items.length === 0
  const noMatches = items.length > 0 && filtered.length === 0

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Studio</h1>
          <p className="sub">Start a piece, watch drafts, and approve what’s ready.</p>
        </div>
        <div className="head-actions">
          <Link className="studio-templates-link" to="/studio/templates">
            Templates ↗
          </Link>
        </div>
      </header>

      {stagedQ.error && <div className="error-bar">{stagedQ.error.message}</div>}

      <StudioLauncher channels={channels} onCreated={(id) => navigate('/studio/' + id)} />

      <h2 className="studio-section-head">Pieces in progress</h2>

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

          <div className="studio-status-tabs" role="tablist" aria-label="Filter by format">
            {FORMAT_TABS.map((t) => {
              const n =
                t.key === 'all'
                  ? items.length
                  : items.filter((it) => formatOf(it) === t.key).length
              return (
                <button
                  key={t.key}
                  className={'status-tab' + (formatFilter === t.key ? ' on' : '')}
                  onClick={() => setFormatFilter(t.key)}
                >
                  {t.label}
                  <span className="chan-filter-n">{n}</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {stagedQ.loading && stagedQ.data == null ? (
        <p className="dim">Loading…</p>
      ) : nothingStaged ? (
        <EmptyState
          message="Nothing staged yet"
          hint="Open a planned item on the Calendar and hit “Produce” — the factory builds each part as its own job, and you review them all here before the final cut."
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
            // Same state machine the board + rail use, so a card can never disagree.
            const producing = isProducing(it)
            const pipe = resolveStage(it, c, { producing })
            const stageAt = stageIndex(pipe.stage)
            const badge = STAGE_BADGE[pipe.stage] || STAGE_BADGE.plan
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
                  <span className={'studio-cover-stage sc-tone-' + badge.tone}>
                    {((c.generating || 0) > 0 || producing) && <span className="live-dot" />}
                    {badge.label}
                  </span>
                  {formatOf(it) === 'longform' && (
                    <span className="studio-cover-format" title="Long-form (16:9)">
                      ▭ long-form
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

                  {/* Mini pipeline rail — the same PLAN→PRODUCE→QC→ARM→LIVE spine
                      the board shows, so the grid reads at a glance. */}
                  <div className={'sc-rail sc-tone-' + badge.tone}>
                    {STAGES.map((s, i) => (
                      <Fragment key={s.key}>
                        {i > 0 && <span className={'sc-seg' + (i <= stageAt ? ' done' : '')} />}
                        <span
                          className={
                            'sc-node' +
                            (i < stageAt ? ' done' : '') +
                            (i === stageAt ? ' at' : '')
                          }
                          title={s.label}
                        >
                          {i < stageAt ? '✓' : i + 1}
                        </span>
                      </Fragment>
                    ))}
                  </div>
                  <div className={'sc-status sc-tone-' + badge.tone}>
                    {pipe.label}
                    {total > 0 && pipe.stage !== 'live' && (
                      <span className="sc-count">
                        {done}/{total}
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
