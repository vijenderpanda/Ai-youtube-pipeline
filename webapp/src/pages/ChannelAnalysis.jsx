import { useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import EmptyState from '../components/EmptyState'
import SyncAnalyticsButton from '../components/SyncAnalyticsButton'
import CalendarStatusChip from '../components/CalendarStatusChip'
import Toast, { useToast } from '../components/Toast'
import { PerfSections, FallbackBanner } from '../components/VideoPerf'
import { timeAgo, fmtDate } from '../format'
import { typeLabel } from '../jobMeta'

const VIEWS_COLOR = '#ff5c93'
const SUBS_COLOR = '#7dd3fc'

function fmtNum(n) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M'
  if (v >= 1e4) return Math.round(v / 1e3) + 'K'
  if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K'
  return String(v)
}

/** SVG line chart: views + subs over time, each normalized to its own max. */
function StatsChart({ points }) {
  const W = 660
  const H = 210
  const PAD = { l: 46, r: 46, t: 12, b: 26 }
  const iw = W - PAD.l - PAD.r
  const ih = H - PAD.t - PAD.b
  const views = points.map((p) => Math.max(0, Number(p.views) || 0))
  const subs = points.map((p) => Math.max(0, Number(p.subs) || 0))
  const vMax = Math.max(1, ...views)
  const sMax = Math.max(1, ...subs)
  const x = (i) => PAD.l + (points.length === 1 ? iw / 2 : (i / (points.length - 1)) * iw)
  const y = (v, max) => PAD.t + ih - (v / max) * ih
  const line = (arr, max) =>
    arr.map((v, i) => `${x(i).toFixed(1)},${y(v, max).toFixed(1)}`).join(' ')
  const grid = [0.25, 0.5, 0.75]

  return (
    <>
      <svg
        className="stats-chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Views and subscribers over time"
      >
        <line x1={PAD.l} y1={PAD.t + ih} x2={PAD.l + iw} y2={PAD.t + ih} stroke="#26262c" />
        {grid.map((g) => (
          <line
            key={g}
            x1={PAD.l}
            y1={PAD.t + ih * (1 - g)}
            x2={PAD.l + iw}
            y2={PAD.t + ih * (1 - g)}
            stroke="#1d1d23"
          />
        ))}
        {/* y labels: views left, subs right */}
        <text x={PAD.l - 6} y={PAD.t + 8} textAnchor="end" className="chart-tick" fill={VIEWS_COLOR}>
          {fmtNum(vMax)}
        </text>
        <text x={PAD.l - 6} y={PAD.t + ih} textAnchor="end" className="chart-tick" fill="#63636b">
          0
        </text>
        <text x={PAD.l + iw + 6} y={PAD.t + 8} textAnchor="start" className="chart-tick" fill={SUBS_COLOR}>
          {fmtNum(sMax)}
        </text>
        {/* x labels */}
        <text x={PAD.l} y={H - 8} textAnchor="start" className="chart-tick" fill="#63636b">
          {points[0].date}
        </text>
        <text x={PAD.l + iw} y={H - 8} textAnchor="end" className="chart-tick" fill="#63636b">
          {points[points.length - 1].date}
        </text>

        <polyline points={line(subs, sMax)} fill="none" stroke={SUBS_COLOR} strokeWidth="1.6" strokeLinejoin="round" opacity="0.9" />
        <polyline points={line(views, vMax)} fill="none" stroke={VIEWS_COLOR} strokeWidth="2" strokeLinejoin="round" />
        {points.map((p, i) => (
          <circle key={i} cx={x(i)} cy={y(views[i], vMax)} r="2.6" fill={VIEWS_COLOR}>
            <title>{`${p.date} · ${fmtNum(views[i])} views · ${fmtNum(subs[i])} subs`}</title>
          </circle>
        ))}
      </svg>
      <div className="chart-legend">
        <span>
          <span className="legend-dot" style={{ background: VIEWS_COLOR }} />
          Views (latest {fmtNum(views[views.length - 1])})
        </span>
        <span>
          <span className="legend-dot" style={{ background: SUBS_COLOR }} />
          Subscribers (latest {fmtNum(subs[subs.length - 1])})
        </span>
      </div>
    </>
  )
}

/** Pull a chartable [{date, views, subs}] series out of insight.details, if any. */
function seriesFromInsights(insights) {
  for (const ins of insights) {
    const d = ins && ins.details
    if (!d || typeof d !== 'object') continue
    for (const key of ['series', 'history', 'stats', 'daily']) {
      const arr = d[key]
      if (Array.isArray(arr) && arr.length > 0 && arr[0] && arr[0].date != null) {
        return arr
          .filter((p) => p && p.date != null)
          .map((p) => ({ date: String(p.date).slice(0, 10), views: p.views ?? 0, subs: p.subs ?? 0 }))
      }
    }
  }
  return null
}

/** Pull a per-video table out of insight.details, if any. */
function videosFromInsights(insights) {
  for (const ins of insights) {
    const d = ins && ins.details
    if (!d || typeof d !== 'object') continue
    const arr = d.videos || d.per_video || d.top_videos
    if (Array.isArray(arr) && arr.length > 0) return arr
  }
  return null
}

function asList(v) {
  if (Array.isArray(v)) return v.map(String)
  if (typeof v === 'string' && v.trim()) return [v]
  return []
}

function InsightCard({ insight }) {
  const d = (insight.details && typeof insight.details === 'object' && insight.details) || {}
  const cols = [
    ['Wins', asList(d.wins)],
    ['Risks', asList(d.risks)],
    ['Next', asList(d.next)],
  ].filter(([, items]) => items.length > 0)

  return (
    <div className="card insight-card">
      <div className="insight-head">
        <span className="insight-time" title={fmtDate(insight.ts)}>
          {timeAgo(insight.ts)}
        </span>
      </div>
      {insight.summary && <p className="insight-summary">{insight.summary}</p>}
      {cols.length > 0 && (
        <div className="insight-cols">
          {cols.map(([label, items]) => (
            <div className="gen-io-col" key={label}>
              <h4>{label}</h4>
              <ul>
                {items.map((it, i) => (
                  <li key={i}>{it}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const WrenchIcon = (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
  </svg>
)

function VideoTable({ videos }) {
  const pick = (v, keys) => {
    for (const k of keys) if (v[k] != null) return v[k]
    return null
  }
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Video</th>
            <th>Views</th>
            <th>Likes</th>
            <th>Published</th>
          </tr>
        </thead>
        <tbody>
          {videos.map((v, i) => (
            <tr key={i}>
              <td className="cell-title">{String(pick(v, ['title', 'video', 'name']) ?? '—')}</td>
              <td className="dim">{fmtNum(pick(v, ['views', 'view_count']))}</td>
              <td className="dim">{fmtNum(pick(v, ['likes', 'like_count']))}</td>
              <td className="dim">{String(pick(v, ['published', 'published_at', 'date']) ?? '—')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function ChannelAnalysis() {
  const { channelKey } = useParams()
  const { toast, show } = useToast()
  const [runBusy, setRunBusy] = useState(null)

  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const statsQ = usePoll(
    () => api.get(`?r=stats&channel=${encodeURIComponent(channelKey)}&days=90`),
    0,
    [channelKey]
  )
  const insightsQ = usePoll(
    () => api.get(`?r=insights&channel=${encodeURIComponent(channelKey)}&limit=10`),
    0,
    [channelKey]
  )
  const calQ = usePoll(
    () => api.get(`?r=calendar&channel=${encodeURIComponent(channelKey)}`),
    15000,
    [channelKey]
  )
  const videoSummaryQ = usePoll(
    () => api.get(`?r=video_summary&channel=${encodeURIComponent(channelKey)}&days=30`),
    0,
    [channelKey]
  )
  const videoStatsQ = usePoll(
    () => api.get(`?r=video_stats&channel=${encodeURIComponent(channelKey)}&days=30`),
    0,
    [channelKey]
  )

  const channels = (chansQ.data && chansQ.data.channels) || []
  const channel = channels.find((c) => c.key === channelKey)
  const insights = (insightsQ.data && insightsQ.data.insights) || []
  const perfVideos = (videoSummaryQ.data && videoSummaryQ.data.videos) || []
  const perfStatsRows = (videoStatsQ.data && videoStatsQ.data.rows) || []
  const accents = {}
  for (const c of channels) accents[c.key] = c.accent

  // Chart data: factory_stats first; else a series buried in insights.details.
  const points = useMemo(() => {
    const stats = (statsQ.data && statsQ.data.stats) || []
    if (stats.length > 0) {
      return stats.map((s) => ({
        date: String(s.date).slice(0, 10),
        views: s.views,
        subs: s.subs,
      }))
    }
    return seriesFromInsights(insights) || []
  }, [statsQ.data, insights])

  const videos = useMemo(
    () => (points.length === 0 ? videosFromInsights(insights) : null),
    [points, insights]
  )

  const suggestions = ((calQ.data && calQ.data.items) || []).filter(
    (i) => i.status === 'suggested'
  )

  const runSuggestion = async (item) => {
    if (runBusy) return
    setRunBusy(item.id)
    try {
      await api.post({ action: 'queue_calendar_item', id: item.id })
      show(`'${item.title}' queued as a job`, 'ok')
      calQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setRunBusy(null)
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="crumbs">
            <Link className="link" to="/channels">
              Channels
            </Link>{' '}
            <span className="dim">/</span>{' '}
            <Link className="link" to={`/channels/${encodeURIComponent(channelKey)}`}>
              <span className="mono">{channelKey}</span>
            </Link>{' '}
            <span className="dim">/</span> analysis
          </div>
          <h1 className="with-dot">
            <span
              className="accent-dot"
              style={{ background: (channel && channel.accent) || '#94A3B8' }}
            />
            {channel ? `${channel.name || channel.key} — Analysis` : `${channelKey} — Analysis`}
          </h1>
          <p className="sub">Performance, AI insights and suggested next moves</p>
        </div>
        <div className="head-actions">
          <SyncAnalyticsButton onToast={show} />
        </div>
      </header>

      {(statsQ.error || insightsQ.error) && (
        <div className="error-bar">{(statsQ.error || insightsQ.error).message}</div>
      )}

      <section className="card panel">
        <div className="panel-head">
          <h2>Views &amp; subscribers</h2>
          <span className="dim small">last 90 days</span>
        </div>
        {statsQ.loading && statsQ.data == null ? (
          <p className="dim">Loading…</p>
        ) : points.length > 0 ? (
          <StatsChart points={points} />
        ) : videos ? (
          <>
            <p className="dim small" style={{ marginBottom: 10 }}>
              No daily stats series yet — showing per-video numbers from the latest insight.
            </p>
            <VideoTable videos={videos} />
          </>
        ) : (
          <EmptyState
            message="No stats yet"
            hint="Run a Sync Analytics — the worker fills the daily series and it charts here."
          />
        )}
      </section>

      <FallbackBanner statsRows={perfStatsRows} />

      <PerfSections
        videos={perfVideos}
        accents={accents}
        loading={videoSummaryQ.loading && videoSummaryQ.data == null}
      />

      <section>
        <div className="gen-section">
          <span className="gen-section-label">Latest insights</span>
          <span className="gen-section-count">{insights.length}</span>
          <span className="gen-section-line" />
        </div>
        {insightsQ.loading && insightsQ.data == null ? (
          <p className="dim">Loading…</p>
        ) : insights.length === 0 ? (
          <EmptyState
            message="No insights yet"
            hint="Each analytics sync writes an AI insight for this channel."
          />
        ) : (
          insights.map((ins) => <InsightCard key={ins.id} insight={ins} />)
        )}
      </section>

      <section>
        <div className="gen-section">
          <span className="gen-section-label">Suggestions for this channel</span>
          <span className="gen-section-count">{suggestions.length}</span>
          <span className="gen-section-line" />
        </div>
        {suggestions.length === 0 ? (
          <EmptyState
            message="No open suggestions"
            hint="AI suggestions land in the calendar after each analytics sync."
          />
        ) : (
          <div className="cal-list">
            {suggestions.map((it) => (
              <div className="card suggestion-row" key={it.id}>
                <div className="cal-item-main">
                  <div className="cal-item-title">{it.title || '(untitled)'}</div>
                  <div className="cal-item-chips">
                    <CalendarStatusChip status={it.status} />
                    {it.kind === 'factory' ? (
                      <span className="tag factory-tag" title="Improvement of the factory itself">
                        {WrenchIcon} factory
                      </span>
                    ) : (
                      <span className="tag dim-tag">{typeLabel(it.type)}</span>
                    )}
                    <span className="tag dim-tag">{String(it.planned_date || '').slice(0, 10)}</span>
                  </div>
                  {it.suggestion_reason && (
                    <div className="cal-item-reason" title={it.suggestion_reason}>
                      {it.suggestion_reason}
                    </div>
                  )}
                </div>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => runSuggestion(it)}
                  disabled={runBusy === it.id}
                >
                  {runBusy === it.id ? 'Queuing…' : '▶ Run'}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <Toast toast={toast} />
    </div>
  )
}
