import { fmtNum } from './VideoPerf'
import { networkRollup, fmtSigned, toneOf } from '../analytics'
import { timeAgo } from '../format'

/**
 * "Since last sync" KPI strip — diffs the two most recent network snapshots
 * (?r=video_deltas). Until a second snapshot exists it shows a baseline notice
 * rather than a fabricated number (snapshot deltas need two syncs).
 */
export default function SyncDelta({ deltas, loading = false }) {
  const r = networkRollup(deltas)

  const head = (
    <div className="gen-section">
      <span className="gen-section-label">Since last sync</span>
      {!r.isFirst && r.prevSyncAt && (
        <span className="gen-section-count" title={r.prevSyncAt}>
          vs {timeAgo(r.prevSyncAt)}
        </span>
      )}
      <span className="gen-section-line" />
    </div>
  )

  if (loading && !deltas) {
    return (
      <section>
        {head}
        <p className="dim">Loading…</p>
      </section>
    )
  }

  if (!r.curSyncAt || r.isFirst) {
    return (
      <section>
        {head}
        <div className="card baseline-note">
          <b>Baseline captured.</b> Change vs last sync — view gains, rank moves, new
          videos — appears here after the next <span className="mono">Sync Analytics</span>.
        </div>
      </section>
    )
  }

  const tiles = [
    { label: 'views gained', value: fmtSigned(r.dViews, fmtNum), tone: toneOf(r.dViews) },
    { label: 'likes + comments', value: fmtSigned(r.dEng, fmtNum), tone: toneOf(r.dEng) },
    { label: 'movers', value: fmtNum(r.movers), tone: '' },
    { label: 'new videos', value: fmtNum(r.newCount), tone: '' },
    { label: 'videos tracked', value: fmtNum(r.tracked), tone: '' },
  ]

  return (
    <section>
      {head}
      <div className="stat-grid">
        {tiles.map((t) => (
          <div className="card stat" key={t.label}>
            <div className={'stat-value' + (t.tone ? ` tone-${t.tone}` : '')}>{t.value}</div>
            <div className="stat-label">{t.label}</div>
          </div>
        ))}
      </div>
      {r.topGainer && (Number(r.topGainer.d_views) || 0) > 0 && (
        <p className="dim small mover-lead">
          Biggest gainer:{' '}
          <a
            className="perf-title"
            href={`https://youtu.be/${encodeURIComponent(r.topGainer.video_id || '')}`}
            target="_blank"
            rel="noreferrer"
          >
            {r.topGainer.title || r.topGainer.video_id}
          </a>{' '}
          <span className="tone-green">{fmtSigned(r.topGainer.d_views, fmtNum)} views</span>
          {Number(r.topGainer.rank_change) > 0 && (
            <span className="tone-green"> · ▲{r.topGainer.rank_change} rank</span>
          )}
        </p>
      )}
    </section>
  )
}
