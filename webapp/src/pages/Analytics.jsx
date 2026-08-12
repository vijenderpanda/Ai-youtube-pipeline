import { useMemo, useRef, useState } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import Chips, { ChipsGroup } from '../components/Chips'
import SyncAnalyticsButton from '../components/SyncAnalyticsButton'
import NewJobModal from '../components/NewJobModal'
import Toast, { useToast } from '../components/Toast'
import { toISODate, timeAgo, syncWindow } from '../format'
import {
  PerfSections,
  VideoTableFull,
  FallbackBanner,
  Sparkline,
  fmtNum,
  fmtPct,
} from '../components/VideoPerf'
import { enrichVideos, deltaIndex, networkRollup, daysSince } from '../analytics'

/**
 * Insights — replacement for the 544-number analytics wall (UX declutter).
 * Three layers, read top-down like a briefing:
 *   L1 "Since you last looked" — 3-5 plain-English insight cards, ONE primary
 *   L2 "Where things stand"    — 5 tiles that say what good looks like
 *   L3 "Explore all the numbers" — every chart/table behind one disclosure
 * L1/L2 are pinned to the whole network at 30 days; L3 has its own filters
 * (a deliberately separate fetch, so exploring never rewrites the briefing).
 */

const WINDOW_OPTIONS = [
  { value: '7', label: '7 days' },
  { value: '30', label: '30 days' },
  { value: '90', label: '90 days' },
]

function nowTiles(videos) {
  let views = 0, likes = 0, comments = 0, subs = 0, wpct = 0, wv = 0
  for (const v of videos) {
    views += v.totalViews || 0
    likes += Number(v.likes) || 0
    comments += Number(v.comments) || 0
    if (v.subs_gained != null) subs += Number(v.subs_gained) || 0
    if (v.retentionPct != null) {
      wpct += v.retentionPct * (v.totalViews || 0)
      wv += v.totalViews || 0
    }
  }
  return { views, avgRet: wv > 0 ? wpct / wv : null, eng: views > 0 ? ((likes + comments) / views) * 100 : null, subs }
}

/** New Job prefills for do-next actions (kept from the old Recommendations flow). */
function prefillFor(v, kind) {
  const title = v.title || v.video_id || 'this video'
  const ch = v.channel_key
  const map = {
    series: {
      title: `Follow-up to “${title}”`,
      prompt:
        `Make the next episode in the exact format of the winning video “${title}” (channel ${ch}). ` +
        `Keep the same hook and structure that worked; change only the topic. Goal: ride the momentum and start a series.`,
    },
    remake_hook: {
      title: `Re-hook “${title}”`,
      prompt:
        `Remake “${title}” (channel ${ch}) with a much stronger first ~3 seconds. ` +
        `Keep the topic; rewrite the opening hook and first shot to stop the scroll.`,
    },
    repackage: {
      title: `Repackage “${title}”`,
      prompt:
        `Repackage “${title}” (channel ${ch}) for discovery: new title + thumbnail, and consider a Shorts recut. ` +
        `Don't change the content — fix the packaging and re-promote.`,
    },
  }
  const m = map[kind] || map.series
  return { channel_key: ch, title: m.title, prompt: m.prompt, model: 'opus', effort: 'high' }
}

/** Build the ranked L1 insight cards from data already in memory. */
function buildInsights({ videos, channels, rollup, isFirst }) {
  const cands = []
  const chName = (k) => (channels.find((c) => c.key === k) || {}).name || k

  for (const v of videos) {
    const cat = v.recommendation && v.recommendation.category
    if (cat === 'double_down' || cat === 'make_series') {
      cands.push({
        kind: 'breakout', score: 100, tone: 'success', video: v,
        text: <>
          <b>{v.title}</b> is a proven winner — <b>{fmtNum(v.totalViews)}</b> views and people watch it through.
        </>,
        doNext: { label: 'Plan the follow-up', action: 'plan', prefill: prefillFor(v, 'series') },
      })
    } else if (cat === 'fix_hook') {
      cands.push({
        kind: 'hook_problem', score: 70, tone: 'warn', video: v,
        text: <>
          People find <b>{v.title}</b> but leave in the first seconds — only <b>{v.retentionPct == null ? '—' : Math.round(v.retentionPct) + '%'}</b> stay.
        </>,
        doNext: { label: 'Remake the opening', action: 'plan', prefill: prefillFor(v, 'remake_hook') },
      })
    } else if (cat === 'fix_discovery' || cat === 'low_reach_investigate') {
      cands.push({
        kind: 'hidden_gem', score: 60, tone: 'info', video: v,
        text: <>
          <b>{v.title}</b> keeps the viewers it gets — it just isn’t being found.
        </>,
        doNext: { label: 'Give it a new title + cover', action: 'plan', prefill: prefillFor(v, 'repackage') },
      })
    }
  }

  // Fastest mover since the last check.
  if (!isFirst && rollup.topGainer && (Number(rollup.topGainer.d_views) || 0) >= 5) {
    const tg = rollup.topGainer
    const v = videos.find((x) => x.video_id === tg.video_id)
    cands.push({
      kind: 'fastest_mover', score: 90, tone: 'success', video: v || { video_id: tg.video_id, channel_key: tg.channel_key, title: tg.title },
      text: <>
        <b>{tg.title || 'One video'}</b> is your fastest mover — <b>+{fmtNum(tg.d_views)}</b> views since you last looked.
      </>,
      doNext: v ? { label: 'Plan the follow-up', action: 'plan', prefill: prefillFor(v, 'series') } : null,
    })
  }

  // Quiet channels: absent from the 30-day summary entirely, or silent ≥8 days.
  const seen = new Map() // channel_key -> min daysSince(last_date)
  for (const v of videos) {
    const d = daysSince(v.last_date || v.first_date)
    const cur = seen.get(v.channel_key)
    if (d != null && (cur == null || d < cur)) seen.set(v.channel_key, d)
  }
  const quiet = []
  for (const c of channels) {
    if (c.status && c.status !== 'active') continue
    if (!seen.has(c.key)) quiet.push({ key: c.key, name: chName(c.key), days: null })
    else if (seen.get(c.key) >= 8) quiet.push({ key: c.key, name: chName(c.key), days: seen.get(c.key) })
  }
  quiet.sort((a, b) => (b.days == null ? 99 : b.days) - (a.days == null ? 99 : a.days))
  for (const qc of quiet.slice(0, 2)) {
    cands.push({
      kind: 'quiet_channel', score: 50, tone: 'danger', channelKey: qc.key,
      text: qc.days == null
        ? <><b>{qc.name}</b> has no videos tracked in the last 30 days.</>
        : <><b>{qc.name}</b> hasn’t published in <b>{qc.days}</b> days.</>,
      doNext: { label: 'Plan something for this channel', action: 'modal', channelKey: qc.key },
    })
  }

  if (!isFirst && rollup.newCount > 0) {
    cands.push({
      kind: 'new_videos', score: 40, tone: 'neutral',
      text: <><b>{rollup.newCount}</b> new video{rollup.newCount > 1 ? 's' : ''} started being tracked since your last check.</>,
      doNext: { label: 'See how they’re doing', action: 'explore' },
    })
  }

  // Dedupe by video, cap 2 per kind, rank, top 5, pad to ≥3.
  const byVideo = new Set()
  const byKind = {}
  const picked = []
  cands.sort((a, b) => b.score - a.score || ((b.video && b.video.totalViews) || 0) - ((a.video && a.video.totalViews) || 0))
  for (const c of cands) {
    const vid = c.video && c.video.video_id
    if (vid && byVideo.has(vid)) continue
    if ((byKind[c.kind] || 0) >= 2) continue
    if (vid) byVideo.add(vid)
    byKind[c.kind] = (byKind[c.kind] || 0) + 1
    picked.push(c)
    if (picked.length >= 5) break
  }
  while (picked.length < 3) {
    picked.push(
      isFirst
        ? { kind: 'baseline', score: 10, tone: 'neutral', text: <>First measurement captured — change since last check appears after the next refresh.</>, doNext: null }
        : { kind: 'steady_state', score: 10, tone: 'neutral', text: <>Everything is moving normally — <b>{fmtNum(rollup.dViews)}</b> views gained across <b>{rollup.tracked}</b> tracked videos.</>, doNext: null }
    )
    if (picked.length >= 3) break
  }
  return picked
}

export default function Analytics() {
  const { toast, show } = useToast()
  const [modal, setModal] = useState(null)
  const [exploreOpen, setExploreOpen] = useState(() => sessionStorage.getItem('insights_explore') === '1')
  const [channel, setChannel] = useState('')
  const [days, setDays] = useState('30')
  const exploreRef = useRef(null)

  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  // L1/L2: pinned to the whole network at 30 days.
  const netQ = usePoll(() => api.get('?r=video_summary&days=30'), 0)
  const deltasQ = usePoll(() => api.get('?r=video_deltas'), 0)
  // L3: its own filtered fetches — exploring never rewrites the briefing.
  const scope = channel ? `&channel=${encodeURIComponent(channel)}` : ''
  const exQ = usePoll(() => api.get(`?r=video_summary&days=${days}${scope}`), 0, [channel, days])
  const statsQ = usePoll(() => api.get(`?r=video_stats&days=${days}${scope}`), 0, [channel, days])

  const channels = (chansQ.data && chansQ.data.channels) || []
  const deltas = deltasQ.data || null
  const rollup = useMemo(() => networkRollup(deltas), [deltas])
  const accents = {}
  for (const c of channels) accents[c.key] = c.accent

  const dIdx = useMemo(() => deltaIndex(deltas), [deltas])
  const merge = (raw, d) =>
    enrichVideos(raw, Number(d)).map((v) => {
      const x = dIdx.get(v.video_id)
      return x ? { ...v, d_views: x.d_views, d_likes: x.d_likes, d_comments: x.d_comments, rank_change: x.rank_change, is_new: x.is_new } : v
    })

  const netVideos = useMemo(() => merge((netQ.data && netQ.data.videos) || [], 30), [netQ.data, dIdx])
  const exVideos = useMemo(() => merge((exQ.data && exQ.data.videos) || [], Number(days)), [exQ.data, dIdx, days])
  const statsRows = (statsQ.data && statsQ.data.rows) || []

  const now = useMemo(() => nowTiles(netVideos), [netVideos])
  const insights = useMemo(
    () => buildInsights({ videos: netVideos, channels, rollup, isFirst: rollup.isFirst }),
    [netVideos, channels, rollup]
  )
  // The primary attaches to the highest-ranked card that HAS a do-next.
  const primaryIdx = insights.findIndex((i) => i.doNext)

  const runDoNext = async (ins) => {
    const dn = ins.doNext
    if (!dn) return
    if (dn.action === 'modal') {
      setModal({ channel_key: dn.channelKey })
      return
    }
    if (dn.action === 'explore') {
      sessionStorage.setItem('insights_explore', '1')
      setExploreOpen(true)
      setTimeout(() => exploreRef.current && exploreRef.current.scrollIntoView({ behavior: 'smooth' }), 60)
      return
    }
    try {
      const res = await api.post({
        action: 'create_calendar_item',
        channel_key: dn.prefill.channel_key,
        planned_date: toISODate(new Date()),
        title: dn.prefill.title,
        brief: dn.prefill.prompt,
        model: dn.prefill.model,
        effort: dn.prefill.effort,
      })
      await api.post({ action: 'stage_calendar_item', id: res.item.id })
      show('Sent to Studio — the factory is planning it now.', 'ok')
    } catch (e) {
      show(e.message, 'error')
    }
  }

  const eyebrow = rollup.isFirst
    ? 'First measurement'
    : rollup.prevSyncAt && rollup.curSyncAt
      ? `Since you last looked · over ${syncWindow(rollup.prevSyncAt, rollup.curSyncAt)}`
      : 'Since you last looked'

  const tiles = [
    {
      label: 'Views · last 30 days', value: fmtNum(now.views),
      sub: !rollup.isFirst && rollup.dViews ? `+${fmtNum(rollup.dViews)} since last check` : null,
      bench: 'Growing week over week is the goal — flat for 7+ days means ship something new.',
    },
    {
      label: 'Watch-through', value: now.avgRet == null ? '—' : fmtPct(now.avgRet),
      bench: 'Above 45% is strong. Under 35% means openings are losing people.',
    },
    {
      label: 'Reactions per view', value: now.eng == null ? '—' : fmtPct(now.eng),
      sub: !rollup.isFirst && rollup.dEng ? `+${fmtNum(rollup.dEng)} reactions since last check` : null,
      bench: 'Around 5% — one in twenty viewers reacting — is healthy for Shorts.',
    },
    {
      label: 'New subscribers', value: fmtNum(now.subs),
      bench: 'Subs follow series — the follow-up video usually earns more than the first.',
    },
    {
      label: 'Videos tracked', value: String(netVideos.length),
      bench: 'Everything the factory is measuring across your channels.',
    },
  ]

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Insights</h1>
          <p className="sub">See how your videos are doing — and what to make more of.</p>
        </div>
        <div className="head-actions">
          <SyncAnalyticsButton onToast={show} />
        </div>
      </header>

      {netQ.error && <div className="error-bar">{netQ.error.message}</div>}
      <FallbackBanner statsRows={statsRows} />

      {/* L1 — the briefing */}
      <section className="ins-l1">
        <div className="lib-eyebrow">{eyebrow}</div>
        {netQ.loading && netQ.data == null ? (
          <div className="act-skeletons">
            {[0, 1, 2].map((i) => <div key={i} className="act-card act-skeleton" />)}
          </div>
        ) : (
          <div className="ins-cards">
            {insights.map((ins, i) => {
              const v = ins.video
              const accent = (v && accents[v.channel_key]) || (ins.channelKey && accents[ins.channelKey]) || 'var(--neutral)'
              const chKey = (v && v.channel_key) || ins.channelKey
              const chDisplay = chKey ? ((channels.find((c) => c.key === chKey) || {}).name || chKey) : null
              return (
                <div key={i} className={`ins-card tone-${ins.tone}`}>
                  <div className="ins-card-main">
                    <p className="ins-text">{ins.text}</p>
                    <div className="ins-meta">
                      {chDisplay && (
                        <span className="act-chan">
                          <span className="act-chan-dot" style={{ background: accent }} />
                          {chDisplay}
                        </span>
                      )}
                      {v && Array.isArray(v.trend) && v.trend.length > 1 && (
                        <Sparkline data={v.trend} color={accent} />
                      )}
                    </div>
                  </div>
                  {ins.doNext && (
                    i === primaryIdx ? (
                      <button className="btn btn-primary" onClick={() => runDoNext(ins)}>{ins.doNext.label}</button>
                    ) : (
                      <button className="link ins-link" onClick={() => runDoNext(ins)}>{ins.doNext.label} →</button>
                    )
                  )}
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* L2 — where things stand */}
      <section>
        <div className="gen-section">
          <span className="gen-section-label">Where things stand</span>
          <span className="gen-section-line" />
        </div>
        <div className="ins-tiles">
          {tiles.map((t) => (
            <div className="card stat ins-tile" key={t.label}>
              <div className="stat-value">{t.value}</div>
              <div className="stat-label">{t.label}</div>
              {t.sub && <div className="ins-tile-sub tone-green">{t.sub}</div>}
              <div className="ins-tile-bench">{t.bench}</div>
            </div>
          ))}
        </div>
      </section>

      {/* L3 — everything else, behind one disclosure */}
      <section ref={exploreRef} className="ins-explore">
        <button
          className="ins-explore-toggle"
          onClick={() => {
            const next = !exploreOpen
            setExploreOpen(next)
            sessionStorage.setItem('insights_explore', next ? '1' : '0')
          }}
          aria-expanded={exploreOpen}
        >
          <span className={'act-chevron' + (exploreOpen ? ' open' : '')} aria-hidden="true">▸</span>
          Explore all the numbers
          <span className="dim small">every video, chart and table</span>
        </button>
        {exploreOpen && (
          <div className="ins-explore-body">
            <div className="chips-bar">
              <ChipsGroup label="Channel">
                <Chips
                  options={[{ value: '', label: 'All channels' }, ...channels.map((c) => ({ value: c.key, label: c.name || c.key }))]}
                  value={channel} onChange={setChannel} ariaLabel="Channel"
                />
              </ChipsGroup>
              <ChipsGroup label="Window">
                <Chips options={WINDOW_OPTIONS} value={days} onChange={setDays} ariaLabel="Window" />
              </ChipsGroup>
            </div>
            <p className="ins-caption">
              Sparklines show daily views across the window — a rising line means the video is still finding people.
            </p>
            <PerfSections videos={exVideos} accents={accents} loading={exQ.loading && exQ.data == null} />
            <p className="ins-caption">
              Every tracked video, ranked. “Watch-through” is how much of the video people stay for; “Since last check” is what changed after the latest refresh.
            </p>
            <VideoTableFull videos={exVideos} accents={accents} />
          </div>
        )}
      </section>

      <Toast toast={toast} />
      {modal && (
        <NewJobModal
          channels={channels}
          initial={modal}
          onClose={() => setModal(null)}
          onCreated={(job) => {
            setModal(null)
            show(`Queued “${job && job.title ? job.title : 'task'}”`, 'ok')
          }}
        />
      )}
    </div>
  )
}
