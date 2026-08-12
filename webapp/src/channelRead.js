/**
 * channelRead — the per-channel analysis engine (UX declutter follow-up).
 *
 * Encodes the distribution model learned from the network's own data:
 *  - Shorts run an AUDITION (seed batch → scored → push or stop) that resolves
 *    within ~3 days, then DECAY to a tail.
 *  - Some videos (music/full songs, search-intent content) are STEADY
 *    compounders instead: a daily trickle that never expires.
 * Everything here is computed client-side from ?r=video_summary + ?r=video_deltas.
 */

/** Classify one daily-views trend. */
export function analyzeTrend(trend) {
  const d = (Array.isArray(trend) ? trend : []).map((v) => Math.max(0, Number(v) || 0))
  if (d.length < 2) return { shape: 'quiet', pushDay: null, pushSize: 0, tailRate: 0 }
  const peak = Math.max(...d)
  const peakI = d.indexOf(peak)
  const rest = d.filter((_, i) => i !== peakI)
  const restMean = rest.length ? rest.reduce((a, b) => a + b, 0) / rest.length : 0
  const after = d.slice(peakI + 1)
  const tailRate = after.length ? after.reduce((a, b) => a + b, 0) / after.length : restMean
  // push: one dominant day well above the rest
  if (peak >= 20 && peak >= 4 * Math.max(1, restMean)) {
    return { shape: 'push', pushDay: peakI + 1, pushSize: peak, tailRate }
  }
  // steady: meaningful daily flow without a dominant spike
  const mean = d.reduce((a, b) => a + b, 0) / d.length
  if (d.length >= 4 && mean >= 3 && peak < 3 * Math.max(1, mean)) {
    return { shape: 'steady', pushDay: null, pushSize: peak, tailRate: mean }
  }
  return { shape: 'quiet', pushDay: null, pushSize: peak, tailRate }
}

const dayMs = 86400000
export function ageDays(dateStr) {
  if (!dateStr) return null
  const t = new Date(String(dateStr).slice(0, 10) + 'T12:00').getTime()
  if (isNaN(t)) return null
  return Math.max(0, Math.round((Date.now() - t) / dayMs))
}

/**
 * Full channel read. `videos` = ?r=video_summary rows (30d window),
 * `deltas` = ?r=video_deltas payload. Returns everything the Analysis page renders.
 */
export function channelRead(videos = [], deltas = null) {
  const dRows = (deltas && deltas.videos) || []
  const dIdx = new Map(dRows.map((x) => [x.video_id, x]))

  const vids = videos.map((v) => {
    const t = analyzeTrend(v.trend)
    const d = dIdx.get(v.video_id) || {}
    return {
      ...v,
      ...t,
      views: Number(v.total_views) || 0,
      ret: v.avg_view_pct == null ? null : Number(v.avg_view_pct),
      dViews: Number(d.d_views) || 0,
      viewsNow: d.views_now != null ? Number(d.views_now) : null,
      age: ageDays(v.first_date),
    }
  })

  // Snapshot-only rows: present in sync snapshots but absent from the analytics
  // window. Since analytics rows lag ~2 days, absence itself means the video is
  // ≤~2 days old (or scheduled at 0 views) — i.e. in or near its audition window.
  const summaryIds = new Set(videos.map((v) => v.video_id))
  const freshOnly = dRows
    .filter((x) => !summaryIds.has(x.video_id) && !String(x.title || '').includes('DELETE'))
    .map((x) => ({
      video_id: x.video_id,
      title: x.title,
      views: Number(x.views_now) || 0,
      viewsNow: Number(x.views_now) || 0,
      dViews: Number(x.d_views) || 0,
      ret: null,
      shape: 'quiet',
      age: x.is_new ? 0 : 1,
      snapshotOnly: true,
    }))

  // Auditioning: anything ≤3 days old (or snapshot-new). Scheduled = 0 views.
  const auditions = [...vids, ...freshOnly].filter(
    (v) => v.age != null && v.age <= 3
  )

  const movers = [...vids, ...freshOnly]
    .filter((v) => v.dViews !== 0)
    .sort((a, b) => b.dViews - a.dViews)

  // Outcome stats over settled videos (old enough for their audition to be over).
  const settled = vids.filter((v) => v.age != null && v.age >= 4 && v.views > 0)
  const hits = settled.filter((v) => v.shape === 'push' || v.views >= 50)
  const steady = vids.filter((v) => v.shape === 'steady')
  const hitRate = settled.length ? hits.length / settled.length : null
  const hitSizes = hits.map((v) => v.views).sort((a, b) => a - b)
  const medHit = hitSizes.length ? hitSizes[Math.floor(hitSizes.length / 2)] : 0
  const maxHit = hitSizes.length ? hitSizes[hitSizes.length - 1] : 0
  const misses = settled.filter((v) => !hits.includes(v))
  const avgMiss = misses.length
    ? Math.round(misses.reduce((a, v) => a + v.views, 0) / misses.length)
    : 5

  // Conversion + totals across the window.
  let views = 0, likes = 0, comments = 0, subs = 0
  for (const v of vids) {
    views += v.views
    likes += Number(v.likes) || 0
    comments += Number(v.comments) || 0
    subs += Number(v.subs_gained) || 0
  }
  const conversion = views > 0 ? (subs / views) * 100 : null // subs per 100 views

  // Cadence: uploads whose first tracked day is inside the window.
  const uploads30 = vids.filter((v) => v.age != null && v.age <= 30).length

  // The compounding floor: steady videos' combined daily trickle.
  const steadyPerDay = Math.round(steady.reduce((a, v) => a + v.tailRate, 0))

  // Forward model (same math as the growth-model artifact, from THIS channel's numbers).
  const perUpload = hitRate == null ? null : hitRate * (medHit || 100) + (1 - hitRate) * avgMiss
  const viewsPerMonth = perUpload == null ? null : Math.round(uploads30 * perUpload + steadyPerDay * 30)
  const subsPerMonth = viewsPerMonth != null && conversion != null ? (viewsPerMonth * conversion) / 100 : null
  const monthsTo = (target, rate) => (rate && rate > 0 ? Math.ceil(target / rate) : null)

  return {
    vids: vids.sort((a, b) => b.views - a.views),
    auditions,
    movers,
    steady,
    hitRate,
    medHit,
    maxHit,
    avgMiss,
    conversion,
    uploads30,
    steadyPerDay,
    totals: { views, likes, comments, subs },
    forecast: {
      nextVideo: { lo: avgMiss, mid: medHit, hi: maxHit },
      viewsPerMonth,
      subsPerMonth,
      to500: monthsTo(500, subsPerMonth),
      to1k: monthsTo(1000, subsPerMonth),
      // conversion fixed to 1/100 — the spoken-CTA scenario
      to500Fixed: viewsPerMonth != null ? monthsTo(500, viewsPerMonth / 100) : null,
      to1kFixed: viewsPerMonth != null ? monthsTo(1000, viewsPerMonth / 100) : null,
    },
    syncAt: deltas ? deltas.cur_sync_at : null,
    isFirstSync: deltas ? !!deltas.is_first : true,
  }
}

/** Plain-language month count: "≈ 14 months" / "years — not a path". */
export function fmtMonths(m) {
  if (m == null) return '—'
  if (m > 120) return 'years — not a path'
  if (m > 24) return `≈ ${Math.round(m / 12)} years`
  return `≈ ${m} month${m === 1 ? '' : 's'}`
}
