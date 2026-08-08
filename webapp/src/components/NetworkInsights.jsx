/**
 * NetworkInsights — derives actionable production signals from enriched video
 * data (output of enrichVideos()) and surfaces them as scannable insight cards.
 *
 * Each insight is one of:
 *   momentum  — something is accelerating; make more of it NOW
 *   hook      — reach is there but retention is weak; fix the opening
 *   gap       — a channel has gone quiet; re-engage before the algo forgets it
 *   series    — a strong performer has no follow-up yet
 *   dormant   — a good video that slipped below radar; worth re-promoting
 */

import { retentionTier } from '../analytics'

const ICON = {
  momentum: '🚀',
  hook:     '🪝',
  gap:      '📭',
  series:   '🎬',
  dormant:  '💤',
}

const LABEL = {
  momentum: 'Ride the wave',
  hook:     'Fix the hook',
  gap:      'Gap alert',
  series:   'Start a series',
  dormant:  'Re-promote',
}

const WHY = {
  momentum: (v) =>
    `"${v.title || v.video_id}" is accelerating — ${Math.round(v.viralScore)} viral score, ` +
    (v.retentionPct != null ? `${Math.round(v.retentionPct)}% avg retention. ` : '') +
    `Post a follow-up in the same format within 72 h while the algo is still distributing this one.`,
  hook: (v) =>
    `"${v.title || v.video_id}" has reach but ${Math.round(v.retentionPct ?? 0)}% avg retention. ` +
    `Viewers leave in the first ~4 s. Remake just the opening hook — same topic, stronger first frame.`,
  gap: (ch, daysSince) =>
    `${ch} hasn't published in ${daysSince} day${daysSince !== 1 ? 's' : ''}. ` +
    `Channels that go quiet >7 days lose algorithmic momentum. Queue at least one short this week.`,
  series: (v) =>
    `"${v.title || v.video_id}" is your top performer on ${v.channel_key} (viral score ${Math.round(v.viralScore)}) ` +
    `but has no follow-up yet. A second episode in the same format compounds the distribution already earned.`,
  dormant: (v) =>
    `"${v.title || v.video_id}" earned ${Math.round(v.retentionPct ?? 0)}% retention when it was active ` +
    `but hasn't gained views recently. A new thumbnail + pinned comment can restart the distribution cycle.`,
}

function daysSinceDate(dateStr) {
  if (!dateStr) return null
  const d = new Date(String(dateStr).slice(0, 10) + 'T00:00:00')
  if (isNaN(d)) return null
  return Math.floor((Date.now() - d.getTime()) / 86400000)
}

/**
 * Derive up to `maxPerType` insights of each type from the enriched video list.
 * Returns an array sorted: momentum > series > hook > dormant > gap.
 */
export function deriveInsights(videos, channels = [], maxTotal = 6) {
  const insights = []

  // ── momentum: high viral score + positive acceleration ───────────────
  const momentum = videos
    .filter((v) => v.viralScore >= 45 && v.accel != null && v.accel > 0.15)
    .sort((a, b) => b.viralScore - a.viralScore)
    .slice(0, 2)
  for (const v of momentum)
    insights.push({ kind: 'momentum', video: v, channelKey: v.channel_key })

  // ── series: top video per channel with no recent follow-up (published >7d ago, no newer sibling) ──
  const byChannel = {}
  for (const v of videos) {
    if (!byChannel[v.channel_key] || v.viralScore > byChannel[v.channel_key].viralScore)
      byChannel[v.channel_key] = v
  }
  const recentByChannel = {}
  for (const v of videos) {
    const ds = daysSinceDate(v.last_date)
    if (ds != null && (!recentByChannel[v.channel_key] || ds < recentByChannel[v.channel_key]))
      recentByChannel[v.channel_key] = ds
  }
  for (const [ch, top] of Object.entries(byChannel)) {
    const daysSinceTop = daysSinceDate(top.last_date)
    if (
      top.viralScore >= 35 &&
      daysSinceTop != null && daysSinceTop >= 7 &&
      !momentum.find((m) => m.video_id === top.video_id)
    ) {
      insights.push({ kind: 'series', video: top, channelKey: ch })
    }
  }

  // ── hook: decent views but weak retention ─────────────────────────────
  const hookCandidates = videos
    .filter((v) => !v.isFallback && v.totalViews >= 100 && v.retentionPct != null && v.retentionPct < 38 && v.viralScore >= 20)
    .sort((a, b) => b.totalViews - a.totalViews)
    .slice(0, 2)
  for (const v of hookCandidates)
    insights.push({ kind: 'hook', video: v, channelKey: v.channel_key })

  // ── dormant: strong retention but no recent views ─────────────────────
  const dormant = videos
    .filter((v) => !v.isFallback && v.retentionPct != null && v.retentionPct >= 50 && v.velocity < 2 && daysSinceDate(v.last_date) > 14)
    .sort((a, b) => b.retentionPct - a.retentionPct)
    .slice(0, 1)
  for (const v of dormant)
    insights.push({ kind: 'dormant', video: v, channelKey: v.channel_key })

  // ── gap: channels that went quiet ─────────────────────────────────────
  for (const c of channels) {
    const chVids = videos.filter((v) => v.channel_key === c.key)
    if (!chVids.length) continue
    const mostRecent = Math.min(...chVids.map((v) => daysSinceDate(v.last_date)).filter((d) => d != null))
    if (mostRecent >= 8)
      insights.push({ kind: 'gap', channelKey: c.key, channelName: c.name || c.key, daysSince: mostRecent })
  }

  // deduplicate video-level insights by video_id (keep first / highest-priority)
  const seen = new Set()
  const deduped = []
  for (const ins of insights) {
    const key = ins.video ? ins.video.video_id : `gap:${ins.channelKey}`
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(ins)
  }

  // sort by priority order
  const ORDER = { momentum: 0, series: 1, hook: 2, dormant: 3, gap: 4 }
  return deduped.sort((a, b) => (ORDER[a.kind] ?? 9) - (ORDER[b.kind] ?? 9)).slice(0, maxTotal)
}

function InsightCard({ ins, accent }) {
  const v = ins.video
  const kindColor = {
    momentum: '#34d399',
    hook:     '#fb923c',
    gap:      '#f87171',
    series:   '#a78bfa',
    dormant:  '#60a5fa',
  }[ins.kind] || '#8b8b95'

  const why =
    ins.kind === 'gap'
      ? WHY.gap(ins.channelName || ins.channelKey, ins.daysSince)
      : WHY[ins.kind]?.(v) ?? ''

  const href = v ? `https://youtu.be/${encodeURIComponent(v.video_id || '')}` : null

  return (
    <div className="card insight-card" style={{ borderLeft: `3px solid ${kindColor}` }}>
      <div className="insight-header">
        <span className="insight-icon">{ICON[ins.kind]}</span>
        <span className="insight-kind-label" style={{ color: kindColor }}>{LABEL[ins.kind]}</span>
        {ins.channelKey && (
          <span
            className="insight-channel-chip"
            style={{ background: accent ? accent + '22' : undefined, color: accent || undefined }}
          >
            {ins.channelKey}
          </span>
        )}
      </div>

      {v && (
        <div className="insight-video-title">
          {href
            ? <a href={href} target="_blank" rel="noreferrer" className="perf-title">{v.title || v.video_id}</a>
            : <span>{v.title || v.video_id}</span>
          }
          {v.viralScore != null && (
            <span className="insight-score">viral {Math.round(v.viralScore)}</span>
          )}
          {v.retentionPct != null && (
            <span className={`insight-ret ret-${retentionTier(v.retentionPct)}`}>
              {Math.round(v.retentionPct)}% ret
            </span>
          )}
        </div>
      )}

      <p className="insight-why">{why}</p>
    </div>
  )
}

export default function NetworkInsights({ videos, channels, accents = {} }) {
  if (!videos || videos.length === 0) return null

  const insights = deriveInsights(videos, channels)
  if (!insights.length) return null

  return (
    <section>
      <div className="gen-section">
        <span className="gen-section-label">Production signals</span>
        <span className="gen-section-count">{insights.length}</span>
        <span className="gen-section-line" />
      </div>
      <p className="dim small" style={{ marginBottom: 14 }}>
        Derived from your retention &amp; engagement data — what to plan next and why.
      </p>
      <div className="insight-grid">
        {insights.map((ins, i) => (
          <InsightCard
            key={ins.video ? ins.video.video_id : `gap:${ins.channelKey}:${i}`}
            ins={ins}
            accent={accents[ins.channelKey]}
          />
        ))}
      </div>
    </section>
  )
}
