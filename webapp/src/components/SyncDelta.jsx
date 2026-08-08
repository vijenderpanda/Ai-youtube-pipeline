import { fmtNum } from './VideoPerf'
import { networkRollup, fmtSigned, toneOf } from '../analytics'
import { timeAgo, syncWindow } from '../format'

/**
 * "Since last sync" KPI strip — diffs the two most recent network snapshots
 * (?r=video_deltas). Until a second snapshot exists it shows a baseline notice
 * rather than a fabricated number (snapshot deltas need two syncs).
 *
 * v13: "vs X ago" bug-fix — now shows the window between the two syncs
 * (e.g. "over 6h") not the age of the previous sync from now.
 * Tiles also show previous absolute value so the user sees e.g. "+42 (was 174)".
 */
export default function SyncDelta({ deltas, loading = false }) {
  const r = networkRollup(deltas)

  const head = (
    <div className="gen-section">
      <span className="gen-section-label">Since last sync</span>
      {!r.isFirst && r.prevSyncAt && r.curSyncAt && (
        <span className="gen-section-count" title={`${r.prevSyncAt} → ${r.curSyncAt}`}>
          over {syncWindow(r.prevSyncAt, r.curSyncAt)}
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

  // For delta tiles: when delta === 0 show the previous absolute figure
  // with an "unchanged" ribbon instead of a bare 0.
  function deltaTile(label, delta, prev, fmt = fmtNum) {
    const isZero = Number.isFinite(Number(delta)) && Number(delta) === 0
    if (isZero && prev != null) {
      return {
        label,
        value: fmt(prev),
        tone: '',
        badge: 'unchanged',
        prev: null,
      }
    }
    return {
      label,
      value: fmtSigned(delta, fmt),
      tone: toneOf(delta),
      badge: null,
      prev: prev != null ? `was ${fmt(prev)}` : null,
    }
  }

  const tiles = [
    deltaTile('views gained', r.dViews, r.prevViews),
    deltaTile('likes + comments', r.dEng, r.prevEng),
    { label: 'movers', value: fmtNum(r.movers), tone: '', badge: null },
    { label: 'new videos', value: fmtNum(r.newCount), tone: '', badge: null },
    { label: 'videos tracked', value: fmtNum(r.tracked), tone: '', badge: null },
  ]

  return (
    <section>
      {head}
      <div className="stat-grid">
        {tiles.map((t) => (
          <div className="card stat" key={t.label} style={{ position: 'relative' }}>
            {t.badge && <span className="sync-unchanged-badge">{t.badge}</span>}
            <div className={'stat-value' + (t.tone ? ` tone-${t.tone}` : '')}>{t.value}</div>
            <div className="stat-label">{t.label}</div>
            {t.prev && <div className="stat-prev">{t.prev}</div>}
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
