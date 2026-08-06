import { useMemo } from 'react'
import EmptyState from './EmptyState'
import { fmtNum } from './VideoPerf'

/**
 * "What to do next" — ranked, actionable recommendations built from the enriched
 * video list (see analytics.js `recommend`). Each actionable row has a one-click
 * button that opens the New Job modal pre-filled via `onAction(video, action)`.
 */

const CAT = {
  double_down: { label: 'Double down', tone: 'good', w: 6 },
  make_series: { label: 'Make series', tone: 'good', w: 5 },
  fix_hook: { label: 'Fix hook', tone: 'bad', w: 4 },
  fix_discovery: { label: 'Fix discovery', tone: 'warn', w: 3 },
  low_reach_investigate: { label: 'Low reach', tone: 'info', w: 2 },
  emerging_watch: { label: 'Emerging', tone: 'info', w: 1 },
  retire: { label: 'Retire', tone: 'bad', w: 0 },
  steady: { label: 'Steady', tone: 'info', w: -1 },
}

const ACTION_LABEL = {
  series: 'Make a sequel',
  remake_hook: 'Remake · new hook',
  repackage: 'New title + thumb',
}

export default function Recommendations({ videos, accents = {}, onAction, limit = 6 }) {
  const items = useMemo(() => {
    return (videos || [])
      .filter((v) => v.recommendation && v.recommendation.action)
      .map((v) => ({ v, rec: v.recommendation, meta: CAT[v.recommendation.category] || CAT.steady }))
      .sort((a, b) => b.meta.w - a.meta.w || (b.v.totalViews || 0) - (a.v.totalViews || 0))
      .slice(0, limit)
  }, [videos, limit])

  return (
    <section>
      <div className="gen-section">
        <span className="gen-section-label">What to do next</span>
        <span className="gen-section-count">{items.length}</span>
        <span className="gen-section-line" />
      </div>
      {items.length === 0 ? (
        <EmptyState
          message="No standout actions right now"
          hint="Recommendations appear as videos accumulate views and retention signal."
        />
      ) : (
        <div className="rec-list">
          {items.map(({ v, rec, meta }) => (
            <div className="card rec-row" key={v.video_id}>
              <div className="rec-main">
                <div className="rec-head">
                  <span
                    className="accent-dot accent-dot-sm"
                    style={{ background: accents[v.channel_key] || '#E91E63' }}
                    title={v.channel_key || ''}
                  />
                  <a
                    className="perf-title"
                    href={`https://youtu.be/${encodeURIComponent(v.video_id || '')}`}
                    target="_blank"
                    rel="noreferrer"
                    title={v.title || v.video_id}
                  >
                    {v.title || v.video_id || '(untitled)'}
                  </a>
                  <span className={`tag rec-${meta.tone}`}>{meta.label}</span>
                  <span className="rec-score" title="viral score (0–100)">
                    VS {v.viralScore}
                  </span>
                </div>
                <div className="rec-text">{rec.text}</div>
                <div className="rec-facts dim small">
                  {fmtNum(v.totalViews)} views · {v.retentionTier.replace('_', ' ')}
                  {v.velocity != null && ` · ${fmtNum(Math.round(v.velocity))}/day`}
                </div>
              </div>
              {rec.action && (
                <button className="btn btn-primary btn-sm" onClick={() => onAction(v, rec)}>
                  {ACTION_LABEL[rec.action.kind] || 'Create job'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
