/**
 * analytics.js — pure derived-metric helpers for the Analytics page (no React).
 *
 * Inputs come from two endpoints:
 *   ?r=video_summary  → per-video window aggregates (total_views, watch_minutes,
 *                       avg_view_pct, subs_gained, likes, comments, shares,
 *                       first_date, last_date, trend[], channel_key)
 *   ?r=video_deltas   → per-video diff of the two most recent snapshots
 *                       (d_views, d_likes, d_comments, rank_now, rank_prev,
 *                        rank_change, is_new)
 *
 * Design notes (from the metrics review):
 *  - viral score uses MEDIAN-RELATIVE SATURATION sat(x,m)=x/(x+m), not
 *    percentile-within-set. A percentile moves a video's score when a *sibling*
 *    changes, which would defeat "what changed since last sync". The median is a
 *    stable set statistic, so a score of 40→68 across syncs is meaningful.
 *  - Signals absent on the data_api_fallback path (retention, subs, shares,
 *    acceleration) are DROPPED from the score and the weights renormalized over
 *    the available ones — never coerced to 0 (that would punish every fallback
 *    channel structurally).
 *  - Recommendations that depend on retention are gated behind !isFallback and
 *    are labelled hypotheses — we have no impressions/CTR/retention-curve data.
 */

const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x))

function median(nums) {
  const a = nums.filter((n) => Number.isFinite(n)).sort((x, y) => x - y)
  if (a.length === 0) return null
  const m = Math.floor(a.length / 2)
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2
}

const mean = (a) => (a.length ? a.reduce((s, x) => s + x, 0) / a.length : 0)

/** Saturating normalizer: 0.5 at the set median m, →1 for x≫m, →0 for x≪m. */
function sat(x, m) {
  if (!Number.isFinite(x) || x <= 0) return 0
  if (!Number.isFinite(m) || m <= 0) return x > 0 ? 1 : 0
  return x / (x + m)
}

function daysBetween(a, b) {
  const d0 = new Date(String(a).slice(0, 10) + 'T00:00:00')
  const d1 = new Date(String(b).slice(0, 10) + 'T00:00:00')
  if (isNaN(d0) || isNaN(d1)) return null
  return Math.round((d1 - d0) / 86400000)
}

export function daysSince(dateStr) {
  if (!dateStr) return null
  const d = new Date(String(dateStr).slice(0, 10) + 'T00:00:00')
  if (isNaN(d)) return null
  return Math.floor((Date.now() - d.getTime()) / 86400000)
}

/** Scale-free trend acceleration on the active-day tail; null when not enough
 *  signal (short trend or retention-less fallback video). Range ≈ [-1, 2]. */
function acceleration(trend, hasRetention) {
  if (!hasRetention || !Array.isArray(trend) || trend.length < 4) return null
  const t = trend.map((n) => Math.max(0, Number(n) || 0))
  const k = Math.min(3, Math.floor(t.length / 2))
  const recent = mean(t.slice(-k))
  const before = mean(t.slice(-2 * k, -k))
  if (before <= 0 && recent <= 0) return null
  return clamp((recent - before) / Math.max(1, before), -1, 2)
}

export function retentionTier(pct) {
  if (pct == null || !Number.isFinite(Number(pct))) return 'unknown'
  const p = Number(pct)
  if (p >= 60) return 'elite'
  if (p >= 45) return 'strong'
  if (p >= 35) return 'ok'
  return 'weak'
}

export const RETENTION_TIER_LABEL = {
  elite: 'Elite retention',
  strong: 'Strong retention',
  ok: 'OK retention',
  weak: 'Weak retention',
  unknown: 'Retention n/a',
}

/**
 * Enrich a video_summary list with derived metrics + a 0–100 viral score +
 * a recommendation. `windowDays` is the selected window (7/30/90). Returns a new
 * array (originals untouched) sorted by viral score desc.
 */
export function enrichVideos(videos, windowDays = 30) {
  const base = (videos || []).map((v) => {
    const totalViews = Number(v.total_views) || 0
    const trend = Array.isArray(v.trend) ? v.trend.map((n) => Math.max(0, Number(n) || 0)) : []
    const span = daysBetween(v.first_date, v.last_date)
    const daysActive = clamp((span == null ? windowDays : span) + 1, 1, windowDays)
    const velocity = totalViews / daysActive
    const recentVelocity = trend.length ? mean(trend.slice(-3)) : velocity
    const vel = Math.max(velocity, recentVelocity) // fast-growth: reward the tail

    const retentionPct = v.avg_view_pct == null ? null : Number(v.avg_view_pct)
    const isFallback = retentionPct == null
    const likes = Number(v.likes) || 0
    const comments = Number(v.comments) || 0
    // low-view guard: a 5-view video with 1 comment must not read as 20% engagement
    const engagementRate = totalViews >= 50 ? (likes + 3 * comments) / totalViews : null
    const subsPer1k = v.subs_gained == null ? null : (Number(v.subs_gained) / Math.max(totalViews, 1)) * 1000
    const sharesPer1k = v.shares == null ? null : (Number(v.shares) / Math.max(totalViews, 1)) * 1000
    const accel = acceleration(trend, !isFallback)

    return {
      ...v,
      totalViews,
      velocity: vel,
      engagementRate,
      subsPer1k,
      sharesPer1k,
      retentionPct,
      isFallback,
      accel,
      retentionTier: retentionTier(retentionPct),
      ageDays: daysSince(v.first_date),
    }
  })

  // set medians (robust references) over the videos that qualify
  const medVel = median(base.filter((v) => v.totalViews >= 50).map((v) => v.velocity)) ?? median(base.map((v) => v.velocity))
  const medEng = median(base.map((v) => v.engagementRate).filter((x) => x != null))
  const medSubs = median(base.map((v) => v.subsPer1k).filter((x) => x != null))
  const medShares = median(base.map((v) => v.sharesPer1k).filter((x) => x != null))

  const W = { velocity: 0.32, retention: 0.22, shares: 0.16, engagement: 0.12, subs: 0.1, accel: 0.08 }

  return base
    .map((v) => {
      const parts = []
      parts.push([W.velocity, sat(v.velocity, medVel)])
      if (v.retentionPct != null) parts.push([W.retention, clamp((v.retentionPct - 20) / 50, 0, 1)])
      if (v.sharesPer1k != null) parts.push([W.shares, sat(v.sharesPer1k, medShares)])
      if (v.engagementRate != null) parts.push([W.engagement, sat(v.engagementRate, medEng)])
      if (v.subsPer1k != null) parts.push([W.subs, sat(v.subsPer1k, medSubs)])
      if (v.accel != null) parts.push([W.accel, clamp((v.accel + 1) / 3, 0, 1)])
      const wsum = parts.reduce((s, [w]) => s + w, 0)
      const score = wsum > 0 ? parts.reduce((s, [w, n]) => s + w * n, 0) / wsum : 0
      const viralScore = Math.round(100 * score)
      return { ...v, viralScore, velocityMedian: medVel, recommendation: recommend(v, viralScore, medVel) }
    })
    .sort((a, b) => b.viralScore - a.viralScore)
}

/** Rule-based next action. Top-down, first match wins. Returns
 *  {category, text, action, confidence}. `action.kind` maps to a New Job prefill. */
export function recommend(v, viralScore, medVel) {
  const relVel = sat(v.velocity, medVel) // 0.5 at median
  const strong = v.retentionTier === 'elite' || v.retentionTier === 'strong'
  const age = v.ageDays == null ? 999 : v.ageDays
  const eng = v.engagementRate

  if (age <= 3 && relVel >= 0.6)
    return { category: 'emerging_watch', confidence: 'med', action: null,
      text: 'Too new to judge but climbing — leave it, check again next sync.' }

  if (viralScore >= 70 && strong && v.accel != null && v.accel > 0.2)
    return { category: 'double_down', confidence: 'high', action: { kind: 'series' },
      text: '🔥 Winner and still rising — reuse this hook now, ship a sequel this week.' }

  if (viralScore >= 70 && strong)
    return { category: 'make_series', confidence: 'high', action: { kind: 'series' },
      text: 'Proven format — spin it into a series while it has momentum.' }

  if (!v.isFallback && v.retentionPct < 35 && relVel >= 0.5)
    return { category: 'fix_hook', confidence: 'med', action: { kind: 'remake_hook' },
      text: 'Reach is there but they bounce — rework the first ~3s hook (hypothesis).' }

  if (!v.isFallback && v.retentionPct >= 35 && relVel < 0.4 && age > 5)
    return { category: 'fix_discovery', confidence: 'med', action: { kind: 'repackage' },
      text: 'People who watch, stay — but few arrive. New title/thumbnail or recut as a Short (hypothesis).' }

  if (v.isFallback && relVel < 0.4 && age > 5)
    return { category: 'low_reach_investigate', confidence: 'low', action: { kind: 'repackage' },
      text: 'Low reach; retention unknown on this channel (re-auth needed). Refresh title/thumb and watch.' }

  if (!v.isFallback && age > 14 && relVel < 0.3 && v.retentionPct < 35 &&
      (eng == null || eng < 0.01) && (v.accel == null || v.accel <= 0))
    return { category: 'retire', confidence: 'high', action: null,
      text: 'Weak on every axis — stop reinvesting in this format.' }

  return { category: 'steady', confidence: 'low', action: null, text: 'Performing normally — no action needed.' }
}

/* ── Deltas (?r=video_deltas) ─────────────────────────────────────────── */

/** Index the deltas array by video_id for merging into enriched videos. */
export function deltaIndex(deltas) {
  const m = new Map()
  for (const d of (deltas && deltas.videos) || []) m.set(d.video_id, d)
  return m
}

/** A video is a "mover" if it jumped ≥3 ranks or gained a meaningful chunk of views. */
export function isMover(d, viewThreshold = 100) {
  if (!d || d.is_new) return false
  return Math.abs(Number(d.rank_change) || 0) >= 3 || Math.abs(Number(d.d_views) || 0) >= viewThreshold
}

/** Network rollup for the "Since last sync" strip. New videos are excluded from
 *  the view sum (a first-seen video would otherwise dump its whole lifetime in). */
export function networkRollup(deltas) {
  const vids = (deltas && deltas.videos) || []
  let dViews = 0, dEng = 0, movers = 0, newCount = 0
  let topGainer = null
  for (const d of vids) {
    if (d.is_new) { newCount++; continue }
    const dv = Number(d.d_views) || 0
    dViews += dv
    dEng += (Number(d.d_likes) || 0) + (Number(d.d_comments) || 0)
    if (isMover(d)) movers++
    if (!topGainer || dv > (Number(topGainer.d_views) || 0)) topGainer = d
  }
  return {
    curSyncAt: deltas ? deltas.cur_sync_at : null,
    prevSyncAt: deltas ? deltas.prev_sync_at : null,
    isFirst: deltas ? deltas.is_first : true,
    dViews, dEng, movers, newCount, topGainer,
    tracked: vids.length,
  }
}

/* ── formatting ──────────────────────────────────────────────────────── */

export function fmtSigned(n, fmt = (x) => String(x)) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  return (v > 0 ? '+' : v < 0 ? '−' : '') + fmt(Math.abs(v))
}

export function toneOf(n) {
  const v = Number(n)
  if (!Number.isFinite(v) || v === 0) return ''
  return v > 0 ? 'green' : 'red'
}
