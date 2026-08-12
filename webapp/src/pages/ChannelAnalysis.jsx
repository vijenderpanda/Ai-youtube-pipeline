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
import { channelRead, fmtMonths } from '../channelRead'

/**
 * Channel Analysis — the living "channel read" (UX declutter follow-up).
 * Everything the network learned about distribution, rendered per channel from
 * its own data: the audition tracker, push-vs-steady shapes, decay tails,
 * working-vs-not, and forward predictions. Detail stays behind one disclosure.
 */

function fmtNum(n) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M'
  if (v >= 1e4) return Math.round(v / 1e3) + 'K'
  if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K'
  return String(v)
}

const SHAPE_LABEL = {
  push: 'one push, then tail',
  steady: 'steady compounder',
  quiet: 'no push yet',
}

/** Tiny daily-views trend with the push day dotted. */
function MiniTrend({ v, accent }) {
  const d = (Array.isArray(v.trend) ? v.trend : []).map((x) => Math.max(0, Number(x) || 0))
  if (d.length < 2) return <div className="cr-noline dim small">not enough days tracked yet</div>
  const W = 190, H = 56, pad = 5
  const maxY = Math.max(...d, 10)
  const x = (i) => pad + (i / (d.length - 1)) * (W - pad * 2)
  const y = (val) => H - pad - (val / maxY) * (H - pad * 2)
  const line = d.map((val, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(val).toFixed(1)}`).join(' ')
  const area = `${line} L${x(d.length - 1).toFixed(1)} ${H - pad} L${x(0).toFixed(1)} ${H - pad} Z`
  const peakI = d.indexOf(Math.max(...d))
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="cr-trend" aria-label={`Daily views for ${v.title}`}>
      <path d={area} fill={accent} opacity="0.12" />
      <path d={line} fill="none" stroke={accent} strokeWidth="2" strokeLinecap="round" />
      <circle cx={x(peakI)} cy={y(d[peakI])} r="3.5" fill={accent} stroke="var(--panel)" strokeWidth="2">
        <title>{`push day: ${d[peakI]} views`}</title>
      </circle>
    </svg>
  )
}

/** Horizontal watch-through bars, shape-coloured, 45% reference line. */
function RetBars({ vids, accent }) {
  const rows = vids.filter((v) => v.ret != null && v.views >= 5).slice(0, 8)
  if (rows.length === 0) return <p className="dim small">Watch-through arrives ~2 days after publish.</p>
  const W = 780, rowH = 36, left = 262, right = 88, top = 6
  const H = top + rows.length * rowH + 22
  const maxV = 80
  const x = (val) => left + (Math.min(val, maxV) / maxV) * (W - left - right)
  const color = (v) => (v.shape === 'steady' ? 'var(--info)' : accent)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="cr-bars" role="img" aria-label="Watch-through per video">
      {[0, 20, 40, 60, 80].map((g) => (
        <g key={g}>
          <line x1={x(g)} x2={x(g)} y1={top} y2={H - 20} stroke="var(--border-soft)" strokeWidth="1" />
          <text x={x(g)} y={H - 6} textAnchor="middle" fontSize="10.5" fill="var(--faint)">{g}%</text>
        </g>
      ))}
      <line x1={x(45)} x2={x(45)} y1={top} y2={H - 20} stroke="var(--border-strong)" strokeWidth="1.5" strokeDasharray="4 4" />
      <text x={x(45) + 4} y={top + 9} fontSize="10" fill="var(--faint)">45% = strong</text>
      {rows.map((v, i) => {
        const yy = top + i * rowH + 5
        return (
          <g key={v.video_id}>
            <text x={left - 8} y={yy + 14} textAnchor="end" fontSize="12" fill="var(--text)">
              {String(v.title || '').length > 34 ? String(v.title).slice(0, 33) + '…' : v.title}
            </text>
            <rect x={left} y={yy} width={Math.max(2, x(v.ret) - left)} height="18" rx="4" fill={color(v)}>
              <title>{`${v.title} — ${v.ret.toFixed(1)}% watch-through · ${v.views} views`}</title>
            </rect>
            <text x={x(v.ret) + 6} y={yy + 13} fontSize="11" fontWeight="700" fill="var(--text-2)">
              {Math.round(v.ret)}% · {fmtNum(v.views)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

/** Daily views+subs series (kept from the old page, re-tokenized). */
function StatsChart({ points, accent }) {
  const W = 660, H = 200
  const PAD = { l: 46, r: 46, t: 12, b: 24 }
  const iw = W - PAD.l - PAD.r
  const ih = H - PAD.t - PAD.b
  const views = points.map((p) => Math.max(0, Number(p.views) || 0))
  const subs = points.map((p) => Math.max(0, Number(p.subs) || 0))
  const vMax = Math.max(1, ...views)
  const sMax = Math.max(1, ...subs)
  const x = (i) => PAD.l + (points.length === 1 ? iw / 2 : (i / (points.length - 1)) * iw)
  const y = (v, max) => PAD.t + ih - (v / max) * ih
  const line = (arr, max) => arr.map((v, i) => `${x(i).toFixed(1)},${y(v, max).toFixed(1)}`).join(' ')
  return (
    <>
      <svg className="stats-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Views and subscribers over time">
        <line x1={PAD.l} y1={PAD.t + ih} x2={PAD.l + iw} y2={PAD.t + ih} stroke="var(--border)" />
        {[0.25, 0.5, 0.75].map((g) => (
          <line key={g} x1={PAD.l} y1={PAD.t + ih * (1 - g)} x2={PAD.l + iw} y2={PAD.t + ih * (1 - g)} stroke="var(--border-soft)" />
        ))}
        <text x={PAD.l - 6} y={PAD.t + 8} textAnchor="end" fontSize="10.5" fill={accent}>{fmtNum(vMax)}</text>
        <text x={PAD.l + iw + 6} y={PAD.t + 8} textAnchor="start" fontSize="10.5" fill="var(--info)">{fmtNum(sMax)}</text>
        <text x={PAD.l} y={H - 6} textAnchor="start" fontSize="10.5" fill="var(--faint)">{points[0].date}</text>
        <text x={PAD.l + iw} y={H - 6} textAnchor="end" fontSize="10.5" fill="var(--faint)">{points[points.length - 1].date}</text>
        <polyline points={line(subs, sMax)} fill="none" stroke="var(--info)" strokeWidth="1.6" strokeLinejoin="round" opacity="0.9" />
        <polyline points={line(views, vMax)} fill="none" stroke={accent} strokeWidth="2" strokeLinejoin="round" />
      </svg>
      <div className="chart-legend">
        <span><span className="legend-dot" style={{ background: accent }} />Views</span>
        <span><span className="legend-dot" style={{ background: 'var(--info)' }} />Subscribers</span>
      </div>
    </>
  )
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
        <span className="insight-time" title={fmtDate(insight.ts)}>{timeAgo(insight.ts)}</span>
      </div>
      {insight.summary && <p className="insight-summary">{insight.summary}</p>}
      {cols.length > 0 && (
        <div className="insight-cols">
          {cols.map(([label, items]) => (
            <div className="gen-io-col" key={label}>
              <h4>{label}</h4>
              <ul>{items.map((it, i) => <li key={i}>{it}</li>)}</ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ChannelAnalysis() {
  const { channelKey } = useParams()
  const { toast, show } = useToast()
  const [runBusy, setRunBusy] = useState(null)
  const [exploreOpen, setExploreOpen] = useState(false)

  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const summaryQ = usePoll(
    () => api.get(`?r=video_summary&channel=${encodeURIComponent(channelKey)}&days=30`), 0, [channelKey])
  const deltasQ = usePoll(
    () => api.get(`?r=video_deltas&channel=${encodeURIComponent(channelKey)}`), 0, [channelKey])
  const statsQ = usePoll(
    () => api.get(`?r=stats&channel=${encodeURIComponent(channelKey)}&days=90`), 0, [channelKey])
  const videoStatsQ = usePoll(
    () => api.get(`?r=video_stats&channel=${encodeURIComponent(channelKey)}&days=30`), 0, [channelKey])
  const insightsQ = usePoll(
    () => api.get(`?r=insights&channel=${encodeURIComponent(channelKey)}&limit=5`), 0, [channelKey])
  const calQ = usePoll(
    () => api.get(`?r=calendar&channel=${encodeURIComponent(channelKey)}`), 15000, [channelKey])

  const channels = (chansQ.data && chansQ.data.channels) || []
  const channel = channels.find((c) => c.key === channelKey)
  const accent = (channel && channel.accent) || '#94A3B8'
  const name = channel ? channel.name || channel.key : channelKey

  const read = useMemo(
    () => channelRead((summaryQ.data && summaryQ.data.videos) || [], deltasQ.data || null),
    [summaryQ.data, deltasQ.data]
  )
  const { forecast: fc } = read

  const points = useMemo(() => {
    const stats = (statsQ.data && statsQ.data.stats) || []
    return stats.map((s) => ({ date: String(s.date).slice(0, 10), views: s.views, subs: s.subs }))
  }, [statsQ.data])

  const insights = (insightsQ.data && insightsQ.data.insights) || []
  const perfStatsRows = (videoStatsQ.data && videoStatsQ.data.rows) || []
  const suggestions = ((calQ.data && calQ.data.items) || []).filter((i) => i.status === 'suggested')
  const accents = {}
  for (const c of channels) accents[c.key] = c.accent

  const loading = summaryQ.loading && summaryQ.data == null

  const runSuggestion = async (item) => {
    if (runBusy) return
    setRunBusy(item.id)
    try {
      await api.post({ action: 'queue_calendar_item', id: item.id })
      show(`'${item.title}' queued`, 'ok')
      calQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setRunBusy(null)
  }

  // Plain-language read bullets, computed
  const best = read.vids.find((v) => v.ret != null && v.views >= 20)
  const bestRet = read.vids.filter((v) => v.ret != null && v.views >= 20).sort((a, b) => b.ret - a.ret)[0]
  const worstRet = read.vids.filter((v) => v.ret != null && v.views >= 5).sort((a, b) => a.ret - b.ret)[0]

  return (
    <div className="page" style={{ '--ch': accent }}>
      <header className="page-head">
        <div>
          <div className="crumbs">
            <Link className="link" to="/channels">Channels</Link>{' '}
            <span className="dim">/</span>{' '}
            <Link className="link" to={`/channels/${encodeURIComponent(channelKey)}`}>
              <span className="mono">{channelKey}</span>
            </Link>{' '}
            <span className="dim">/</span> analysis
          </div>
          <h1 className="with-dot">
            <span className="accent-dot" style={{ background: accent }} />
            {name} — the read
          </h1>
          <p className="sub">How this channel is really doing — auditions, pushes, tails, and where it's heading.</p>
        </div>
        <div className="head-actions">
          <SyncAnalyticsButton onToast={show} />
        </div>
      </header>

      {(summaryQ.error || deltasQ.error) && (
        <div className="error-bar">{(summaryQ.error || deltasQ.error).message}</div>
      )}
      <FallbackBanner statsRows={perfStatsRows} />

      {loading ? (
        <div className="act-skeletons">{[0, 1, 2].map((i) => <div key={i} className="act-card act-skeleton" />)}</div>
      ) : read.vids.length === 0 && read.auditions.length === 0 ? (
        <EmptyState message="Nothing tracked yet" hint="Publish something and run a Sync — the read builds itself from the data." />
      ) : (
        <>
          {/* ── In the audition room ── */}
          <section className="act-lane">
            <div className="act-lane-head">
              <span className="act-lane-label">In the audition room</span>
              <span className="dim small">
                the feed decides in the first 1–3 days
                {read.syncAt && ` · numbers as of ${timeAgo(read.syncAt)}`}
              </span>
            </div>
            {read.auditions.length === 0 ? (
              <p className="dim" style={{ padding: '2px 2px 6px' }}>
                Nothing in its audition window right now — the next upload enters the lottery the moment it goes public.
              </p>
            ) : (
              <div className="cr-aud-row">
                {read.auditions.map((v) => {
                  const scheduled = (v.viewsNow ?? v.views) === 0
                  return (
                    <div key={v.video_id} className="card cr-aud">
                      <div className="cr-aud-day">
                        {scheduled ? 'scheduled' : v.snapshotOnly ? 'in audition' : v.age === 0 ? 'day 1' : `day ${v.age + 1} of 3`}
                      </div>
                      <div className="cr-aud-title">{v.title}</div>
                      <div className="cr-aud-num">
                        <b>{fmtNum(v.viewsNow ?? v.views)}</b> views
                        {v.dViews > 0 && <span className="tone-green"> · +{v.dViews} since last check</span>}
                      </div>
                      {!scheduled && fc.nextVideo.mid > 0 && (
                        <div className="dim small">
                          typical winner here: ~{fmtNum(fc.nextVideo.mid)} · best: {fmtNum(fc.nextVideo.hi)} · miss: ≤{fmtNum(fc.nextVideo.lo)}
                        </div>
                      )}
                      {scheduled && <div className="dim small">audition starts when it goes public</div>}
                    </div>
                  )
                })}
              </div>
            )}
          </section>

          {/* ── The read ── */}
          <section className="act-lane">
            <div className="act-lane-head"><span className="act-lane-label">The read</span></div>
            <ul className="cr-pts">
              {read.hitRate != null && (
                <li>
                  <b>{Math.round(read.hitRate * 100)}%</b> of settled videos got a feed push
                  {read.medHit > 0 && <> — a typical win lands <b>~{fmtNum(read.medHit)}</b> views, the best hit <b>{fmtNum(read.maxHit)}</b></>}
                  ; a miss stays around <b>{fmtNum(read.avgMiss)}</b>.
                </li>
              )}
              {read.steady.length > 0 && (
                <li>
                  <b>{read.steady.length}</b> steady compounder{read.steady.length > 1 ? 's' : ''} feed{read.steady.length > 1 ? '' : 's'} a floor of
                  <b> ~{read.steadyPerDay}/day</b> that never expires — this channel's tail is its asset.
                </li>
              )}
              {read.steady.length === 0 && read.vids.length > 2 && (
                <li>
                  Every win decays to a <b>1–2/day tail</b> after its push — growth here is <b>cadence</b>: more auditions, not older videos.
                </li>
              )}
              {bestRet && (
                <li><span className="tone-green">Strongest hold:</span> <b>{bestRet.title}</b> keeps <b>{Math.round(bestRet.ret)}%</b> of viewers — make more shaped like this.</li>
              )}
              {worstRet && bestRet && worstRet.video_id !== bestRet.video_id && worstRet.ret < 30 && (
                <li><span className="tone-red-inline">Weakest hold:</span> <b>{worstRet.title}</b> loses people at <b>{Math.round(worstRet.ret)}%</b> — the format signal, not bad luck.</li>
              )}
              {read.conversion != null && (
                <li>
                  Conversion: <b>{read.conversion.toFixed(1)} subs per 100 views</b>
                  {read.conversion < 0.8 && <> — the weak layer. A spoken series-CTA typically reaches ~1/100.</>}
                </li>
              )}
            </ul>
          </section>

          {/* ── Shapes ── */}
          {read.vids.filter((v) => Array.isArray(v.trend) && v.trend.length > 1).length > 0 && (
            <section className="act-lane">
              <div className="act-lane-head">
                <span className="act-lane-label">The shape of every video</span>
                <span className="dim small">dot = push day · flat lines after it are the tail</span>
              </div>
              <div className="cr-sm-grid">
                {read.vids.filter((v) => Array.isArray(v.trend) && v.trend.length > 1).slice(0, 6).map((v) => (
                  <div key={v.video_id} className="card cr-sm">
                    <div className="cr-sm-title">{v.title}</div>
                    <MiniTrend v={v} accent={accent} />
                    <div className="cr-sm-foot">
                      <span className={'cr-shape cr-shape-' + v.shape}>{SHAPE_LABEL[v.shape]}</span>
                      {v.shape === 'push' && <span className="dim small">tail ~{Math.max(1, Math.round(v.tailRate))}/day</span>}
                      {v.shape === 'steady' && <span className="dim small">~{Math.round(v.tailRate)}/day, ongoing</span>}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Working vs not ── */}
          <section className="act-lane">
            <div className="act-lane-head">
              <span className="act-lane-label">Working vs not</span>
              <span className="dim small">bar = how much of the video people actually watch</span>
            </div>
            <div className="card" style={{ padding: 'var(--s-4)', overflowX: 'auto' }}>
              <RetBars vids={read.vids} accent={accent} />
            </div>
          </section>

          {/* ── The road ahead ── */}
          <section className="act-lane">
            <div className="act-lane-head">
              <span className="act-lane-label">The road ahead</span>
              <span className="dim small">from this channel's own outcomes — not averages</span>
            </div>
            <div className="cr-road">
              <div className="card cr-road-tile">
                <div className="cr-road-v">{fc.viewsPerMonth != null ? fmtNum(fc.viewsPerMonth) : '—'}</div>
                <div className="cr-road-l">views/mo at current pace ({read.uploads30} uploads in 30d{read.steadyPerDay > 0 ? ` + ${read.steadyPerDay}/day floor` : ''})</div>
              </div>
              <div className="card cr-road-tile">
                <div className="cr-road-v">{fc.subsPerMonth != null ? Math.round(fc.subsPerMonth) : '—'}<small> /mo</small></div>
                <div className="cr-road-l">subs at current conversion → 1,000 {fmtMonths(fc.to1k)}</div>
              </div>
              <div className="card cr-road-tile">
                <div className="cr-road-v">{fc.to1kFixed != null ? fmtMonths(fc.to1kFixed).replace('≈ ', '') : '—'}</div>
                <div className="cr-road-l">to 1,000 subs if conversion is fixed to 1/100 (spoken series-CTA)</div>
              </div>
            </div>
            <p className="dim small" style={{ marginTop: 8 }}>
              Cadence is the multiplier: every upload is a fresh audition, and tickets stop earning after ~3 days.
              Breakouts (the lottery's fat tail) can collapse these timelines — they're not in the math above.
            </p>
          </section>

          {/* ── Explore ── */}
          <section className="ins-explore">
            <button className="ins-explore-toggle" onClick={() => setExploreOpen((v) => !v)} aria-expanded={exploreOpen}>
              <span className={'act-chevron' + (exploreOpen ? ' open' : '')} aria-hidden="true">▸</span>
              Explore the detail
              <span className="dim small">daily series · every video · AI notes · suggestions</span>
            </button>
            {exploreOpen && (
              <div className="ins-explore-body">
                {points.length > 0 && (
                  <div className="card panel" style={{ marginBottom: 'var(--s-4)' }}>
                    <div className="panel-head"><h2>Views &amp; subscribers</h2><span className="dim small">last 90 days</span></div>
                    <StatsChart points={points} accent={accent} />
                  </div>
                )}
                <PerfSections
                  videos={(summaryQ.data && summaryQ.data.videos) || []}
                  accents={accents}
                  loading={false}
                />
                {insights.length > 0 && (
                  <>
                    <div className="gen-section">
                      <span className="gen-section-label">AI notes from each sync</span>
                      <span className="gen-section-line" />
                    </div>
                    {insights.map((ins) => <InsightCard key={ins.id} insight={ins} />)}
                  </>
                )}
                {suggestions.length > 0 && (
                  <>
                    <div className="gen-section">
                      <span className="gen-section-label">Open suggestions</span>
                      <span className="gen-section-count">{suggestions.length}</span>
                      <span className="gen-section-line" />
                    </div>
                    <div className="cal-list">
                      {suggestions.map((it) => (
                        <div className="card suggestion-row" key={it.id}>
                          <div className="cal-item-main">
                            <div className="cal-item-title">{it.title || '(untitled)'}</div>
                            <div className="cal-item-chips">
                              <CalendarStatusChip status={it.status} />
                              <span className="tag dim-tag">{typeLabel(it.type)}</span>
                              <span className="tag dim-tag">{String(it.planned_date || '').slice(0, 10)}</span>
                            </div>
                            {it.suggestion_reason && (
                              <div className="cal-item-reason" title={it.suggestion_reason}>{it.suggestion_reason}</div>
                            )}
                          </div>
                          <button className="btn btn-ghost btn-sm" onClick={() => runSuggestion(it)} disabled={runBusy === it.id}>
                            {runBusy === it.id ? 'Queuing…' : '▶ Run'}
                          </button>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </section>
        </>
      )}

      <Toast toast={toast} />
    </div>
  )
}
