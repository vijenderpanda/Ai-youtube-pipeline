import { useMemo, useState } from 'react'
import { ChipSearch } from './Chips'
import EmptyState from './EmptyState'
import { fmtSigned, toneOf } from '../analytics'

/**
 * v5 — shared "what's working" building blocks, driven by ?r=video_summary
 * rows: { video_id, title, channel_key?, total_views, watch_minutes,
 *         avg_view_pct, subs_gained, likes, comments, first_date, last_date,
 *         trend: [daily views] }
 * Used by the network Analytics page and the per-channel Analysis page.
 */

export function fmtNum(n) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  const a = Math.abs(v)
  if (a >= 1e6) return (v / 1e6).toFixed(1) + 'M'
  if (a >= 1e4) return Math.round(v / 1e3) + 'K'
  if (a >= 1e3) return (v / 1e3).toFixed(1) + 'K'
  return String(Math.round(v))
}

export function fmtPct(n) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  return (v >= 10 ? Math.round(v) : v.toFixed(1)) + '%'
}

function daysSince(dateStr) {
  if (!dateStr) return null
  const d = new Date(String(dateStr).slice(0, 10) + 'T00:00:00')
  if (isNaN(d.getTime())) return null
  return Math.floor((Date.now() - d.getTime()) / 86400000)
}

/** First seen more than 3 days ago — old enough to judge. */
function isMature(v) {
  const age = daysSince(v.first_date)
  return age != null && age > 3
}

/**
 * Simple momentum score: recency-weighted daily views (latest day weighs
 * most) times a retention bonus (1 + avg_view_pct/100).
 */
export function momentumScore(v) {
  const trend = Array.isArray(v.trend)
    ? v.trend.map((n) => Math.max(0, Number(n) || 0))
    : []
  let recent = 0
  if (trend.length > 0) {
    for (let i = 0; i < trend.length; i++) {
      recent += trend[i] * ((i + 1) / trend.length)
    }
  } else {
    recent = Number(v.total_views) || 0
  }
  const pct = Number(v.avg_view_pct)
  const bonus = Number.isFinite(pct) ? 1 + Math.min(Math.max(pct, 0), 100) / 100 : 1
  return recent * bonus
}

/** Which metric is dragging a weak video down: 'pct' (retention) or 'views'. */
function weakMetric(v) {
  const pct = Number(v.avg_view_pct)
  if (Number.isFinite(pct) && pct < 35) return 'pct'
  return 'views'
}

export function Sparkline({ data, color = '#ff5c93' }) {
  const arr = (Array.isArray(data) ? data : []).map((n) => Math.max(0, Number(n) || 0))
  if (arr.length < 2) return <div className="spark spark-empty" />
  const W = 120
  const H = 30
  const max = Math.max(1, ...arr)
  const pts = arr
    .map(
      (v, i) =>
        `${((i / (arr.length - 1)) * W).toFixed(1)},${(H - 2 - (v / max) * (H - 4)).toFixed(1)}`
    )
    .join(' ')
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}

export function PctBar({ pct, bad = false }) {
  const p = Math.max(0, Math.min(100, Number(pct) || 0))
  return (
    <span className={'pct-bar' + (bad ? ' bad' : '')}>
      <span style={{ width: `${p}%` }} />
    </span>
  )
}

/** Since-last-sync chips (rank move + view gain). Reads enriched fields off the
 *  video; renders nothing when the video wasn't merged with a delta. */
function DeltaChips({ v }) {
  const dv = v.d_views
  const rc = Number(v.rank_change)
  const hasRank = Number.isFinite(rc) && rc !== 0
  const hasViews = dv != null && Number(dv) !== 0
  if (v.is_new) return <span className="perf-delta"><span className="delta-chip new">NEW</span></span>
  if (!hasRank && !hasViews) return null
  return (
    <span className="perf-delta">
      {hasRank && (
        <span className={'delta-chip ' + (rc > 0 ? 'up' : 'down')}>
          {rc > 0 ? `▲${rc}` : `▼${Math.abs(rc)}`} rank
        </span>
      )}
      {hasViews && (
        <span className={'delta-chip ' + toneOf(dv)}>{fmtSigned(dv, fmtNum)} views</span>
      )}
    </span>
  )
}

export function VideoCard({ v, accent, weak }) {
  const pct = Number(v.avg_view_pct)
  const subs = Number(v.subs_gained) || 0
  const title = v.title || v.video_id || '(untitled)'
  const rec = v.recommendation
  return (
    <div className={'card perf-card' + (weak ? ' perf-bad' : '')}>
      <div className="perf-top">
        <span
          className="accent-dot"
          style={{ background: accent || '#94A3B8' }}
          title={v.channel_key || ''}
        />
        <a
          className="perf-title"
          href={`https://youtu.be/${encodeURIComponent(v.video_id || '')}`}
          target="_blank"
          rel="noreferrer"
          title={title}
        >
          {title}
        </a>
        {Number.isFinite(v.viralScore) && (
          <span className="viral-badge" title="viral score (0–100)">
            {v.viralScore}
          </span>
        )}
      </div>
      <DeltaChips v={v} />
      <div className="perf-stats">
        <div className="perf-stat">
          <span className={'perf-val' + (weak === 'views' ? ' perf-weak' : '')}>
            {fmtNum(v.total_views)}
          </span>
          <span className="perf-lbl">views</span>
        </div>
        <div className="perf-stat">
          <span className="perf-val">
            {v.watch_minutes == null ? '—' : fmtNum(Math.round(v.watch_minutes))}
          </span>
          <span className="perf-lbl">watch min</span>
        </div>
        <div className="perf-stat">
          <span className={'perf-val' + (weak === 'pct' ? ' perf-weak' : '')}>
            {weak === 'pct' ? `avg view ${fmtPct(pct)}` : fmtPct(pct)}
          </span>
          <span className="perf-lbl">avg view</span>
          <PctBar pct={pct} bad={weak === 'pct'} />
        </div>
        <div className="perf-stat">
          <span className="perf-val">{subs > 0 ? `+${fmtNum(subs)}` : fmtNum(subs)}</span>
          <span className="perf-lbl">subs</span>
        </div>
      </div>
      <Sparkline data={v.trend} />
      {rec && rec.category !== 'steady' && (
        <div className={'perf-rec rec-' + (rec.category || '')} title={rec.text}>
          {rec.text}
        </div>
      )}
    </div>
  )
}

function SectionHead({ label, count, tone }) {
  return (
    <div className="gen-section">
      <span className={'gen-section-label' + (tone ? ` ${tone}` : '')}>{label}</span>
      <span className="gen-section-count">{count}</span>
      <span className="gen-section-line" />
    </div>
  )
}

/**
 * WORKING (top momentum) + NOT WORKING (mature, lowest momentum/retention)
 * sections. `accents` maps channel_key -> accent color.
 */
export function PerfSections({ videos, accents = {}, loading = false }) {
  const { top, bottom } = useMemo(() => {
    const sorted = videos
      .map((v) => ({ v, score: Number.isFinite(v.viralScore) ? v.viralScore : momentumScore(v) }))
      .sort((a, b) => b.score - a.score)
    const top = sorted.filter((s) => (Number(s.v.total_views) || 0) > 0).slice(0, 6)
    const topIds = new Set(top.map((s) => s.v.video_id))
    const bottom = sorted
      .filter((s) => !topIds.has(s.v.video_id) && isMature(s.v))
      .reverse()
      .slice(0, 4)
    return { top, bottom }
  }, [videos])

  const accentOf = (v) => accents[v.channel_key] || undefined

  return (
    <>
      <section>
        <SectionHead label="Working" count={top.length} tone="ok" />
        {loading && videos.length === 0 ? (
          <p className="dim">Loading…</p>
        ) : top.length === 0 ? (
          <EmptyState
            message="No video stats yet"
            hint="Run a Sync Analytics — per-video daily stats land here."
          />
        ) : (
          <div className="perf-grid">
            {top.map(({ v }) => (
              <VideoCard key={v.video_id} v={v} accent={accentOf(v)} />
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHead label="Not working" count={bottom.length} tone="bad" />
        {loading && videos.length === 0 ? (
          <p className="dim">Loading…</p>
        ) : bottom.length === 0 ? (
          <EmptyState
            message="Nothing flagged"
            hint="Videos published more than 3 days ago with weak momentum or retention show up here."
          />
        ) : (
          <div className="perf-grid">
            {bottom.map(({ v }) => (
              <VideoCard key={v.video_id} v={v} accent={accentOf(v)} weak={weakMetric(v)} />
            ))}
          </div>
        )}
      </section>
    </>
  )
}

/**
 * Amber notice when some rows fell back to the Data API (no retention).
 * Pass raw ?r=video_stats rows — channels are detected via row.source.
 */
export function FallbackBanner({ statsRows }) {
  const chans = useMemo(
    () => [
      ...new Set(
        (statsRows || [])
          .filter((r) => r && r.source === 'data_api_fallback')
          .map((r) => r.channel_key)
          .filter(Boolean)
      ),
    ],
    [statsRows]
  )
  if (chans.length === 0) return null
  return (
    <div className="warn-bar">
      Retention metrics need a one-time re-auth for: <b>{chans.join(', ')}</b> — views/likes
      shown from Data API meanwhile.
    </div>
  )
}

/* ── Full sortable table ─────────────────────────────────────────────── */

const TIER_SHORT = { elite: 'Elite', strong: 'Strong', ok: 'OK', weak: 'Weak', unknown: 'n/a' }
const REC_SHORT = {
  double_down: 'Double down', make_series: 'Series', fix_hook: 'Fix hook',
  fix_discovery: 'Fix discovery', low_reach_investigate: 'Low reach',
  emerging_watch: 'Emerging', retire: 'Retire', steady: '—',
}

const num = (x) => (Number.isFinite(Number(x)) ? Number(x) : -Infinity)
const Signed = ({ n }) =>
  n == null || Number(n) === 0 ? (
    <span className="dim">{n == null ? '—' : '0'}</span>
  ) : (
    <span className={'tone-' + toneOf(n)}>{fmtSigned(n, fmtNum)}</span>
  )

// Config-driven columns: header + body render from one list so they can't drift.
// `enriched` cols only show when the videos carry derived metrics (Analytics page).
const COLS = [
  {
    key: 'title', label: 'Video', str: true, cellClass: 'cell-title',
    sortVal: (v) => (v.title || v.video_id || '').toLowerCase(),
    render: (v) => (
      <a className="perf-title" href={`https://youtu.be/${encodeURIComponent(v.video_id || '')}`}
        target="_blank" rel="noreferrer" title={v.title || v.video_id}>
        {v.title || v.video_id || '(untitled)'}
      </a>
    ),
  },
  {
    key: 'channel_key', label: 'Channel', str: true, channel: true,
    sortVal: (v) => v.channel_key || '',
    render: (v, accents) => (
      <>
        <span className="accent-dot accent-dot-sm" style={{ background: accents[v.channel_key] || '#94A3B8' }} />
        <span className="dim mono small">{v.channel_key || '—'}</span>
      </>
    ),
  },
  {
    key: 'viralScore', label: 'Viral', enriched: true,
    sortVal: (v) => num(v.viralScore),
    render: (v) => (Number.isFinite(v.viralScore) ? <span className="viral-cell">{v.viralScore}</span> : <span className="dim">—</span>),
  },
  {
    key: 'd_views', label: 'Δ last sync', enriched: true,
    sortVal: (v) => (v.d_views == null ? -Infinity : Number(v.d_views)),
    render: (v) => (v.is_new ? <span className="delta-chip new">NEW</span> : <Signed n={v.d_views} />),
  },
  {
    key: 'rank_change', label: 'Rank Δ', enriched: true,
    sortVal: (v) => (v.rank_change == null ? -Infinity : Number(v.rank_change)),
    render: (v) => {
      const rc = Number(v.rank_change)
      if (!Number.isFinite(rc) || rc === 0) return <span className="dim">—</span>
      return <span className={'tone-' + (rc > 0 ? 'green' : 'red')}>{rc > 0 ? `▲${rc}` : `▼${Math.abs(rc)}`}</span>
    },
  },
  {
    key: 'velocity', label: 'Views/day', enriched: true, cellClass: 'dim',
    sortVal: (v) => num(v.velocity),
    render: (v) => (v.velocity == null ? '—' : fmtNum(Math.round(v.velocity))),
  },
  { key: 'total_views', label: 'Views', sortVal: (v) => num(v.total_views), render: (v) => fmtNum(v.total_views) },
  { key: 'avg_view_pct', label: 'Avg view %', cellClass: 'dim', sortVal: (v) => num(v.avg_view_pct), render: (v) => fmtPct(v.avg_view_pct) },
  {
    key: 'hold15s', label: '15s hold', enriched: true, cellClass: 'dim',
    sortVal: (v) => num(v.hold15s),
    render: (v) => (v.hold15s == null ? '—' : Math.round(Number(v.hold15s) * 100) + '%'),
  },
  {
    key: 'shortsPct', label: 'Shorts feed', enriched: true, cellClass: 'dim',
    sortVal: (v) => num(v.shortsPct),
    render: (v) => (v.shortsPct == null ? '—' : fmtPct(v.shortsPct)),
  },
  {
    key: 'retentionTier', label: 'Retention', str: true, enriched: true, cellClass: 'dim',
    sortVal: (v) => v.retentionTier || '',
    render: (v) => (v.retentionTier ? <span className={'ret-' + v.retentionTier}>{TIER_SHORT[v.retentionTier]}</span> : '—'),
  },
  { key: 'subs_gained', label: 'Subs', cellClass: 'dim', sortVal: (v) => num(v.subs_gained), render: (v) => fmtNum(v.subs_gained) },
  { key: 'likes', label: 'Likes', cellClass: 'dim', sortVal: (v) => num(v.likes), render: (v) => fmtNum(v.likes) },
  { key: 'comments', label: 'Comments', cellClass: 'dim', sortVal: (v) => num(v.comments), render: (v) => fmtNum(v.comments) },
  { key: 'shares', label: 'Shares', cellClass: 'dim', sortVal: (v) => num(v.shares), render: (v) => (v.shares == null ? '—' : fmtNum(v.shares)) },
  { key: 'first_date', label: 'First seen', str: true, cellClass: 'dim', sortVal: (v) => String(v.first_date || ''), render: (v) => String(v.first_date || '—').slice(0, 10) },
  {
    key: 'rec', label: 'Next move', str: true, enriched: true,
    sortVal: (v) => (v.recommendation && v.recommendation.category) || '',
    render: (v) =>
      v.recommendation && v.recommendation.category !== 'steady' ? (
        <span className={'tag rec-tag rec-' + v.recommendation.category} title={v.recommendation.text}>
          {REC_SHORT[v.recommendation.category] || v.recommendation.category}
        </span>
      ) : (
        <span className="dim">—</span>
      ),
  },
]

export function VideoTableFull({ videos, accents = {}, showChannel = true, enriched = true }) {
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState({ key: enriched ? 'viralScore' : 'total_views', dir: 'desc' })

  const cols = COLS.filter((c) => (showChannel || !c.channel) && (enriched || !c.enriched))

  const clickSort = (col) => {
    setSort((s) =>
      s.key === col.key
        ? { key: col.key, dir: s.dir === 'desc' ? 'asc' : 'desc' }
        : { key: col.key, dir: col.str ? 'asc' : 'desc' }
    )
  }

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase()
    const filtered = q
      ? videos.filter((v) =>
          [v.title, v.video_id, v.channel_key].filter(Boolean).join(' ').toLowerCase().includes(q)
        )
      : videos
    const col = COLS.find((c) => c.key === sort.key) || COLS[0]
    const mul = sort.dir === 'desc' ? -1 : 1
    return [...filtered].sort((a, b) => {
      if (col.str) return mul * String(col.sortVal(a)).localeCompare(String(col.sortVal(b)))
      return mul * (col.sortVal(a) - col.sortVal(b))
    })
  }, [videos, search, sort])

  return (
    <section className="card panel">
      <div className="panel-head">
        <h2>All videos</h2>
        <ChipSearch value={search} onChange={setSearch} placeholder="Search videos…" />
      </div>
      {rows.length === 0 ? (
        <EmptyState message={search ? 'No videos match the search' : 'No videos yet'} />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                {cols.map((c) => (
                  <th
                    key={c.key}
                    className="th-sort"
                    onClick={() => clickSort(c)}
                    aria-sort={sort.key === c.key ? (sort.dir === 'desc' ? 'descending' : 'ascending') : undefined}
                  >
                    {c.label}
                    {sort.key === c.key && <span className="sort-arrow">{sort.dir === 'desc' ? '▼' : '▲'}</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((v) => (
                <tr key={v.video_id}>
                  {cols.map((c) => (
                    <td key={c.key} className={c.cellClass || undefined}>
                      {c.render(v, accents)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
