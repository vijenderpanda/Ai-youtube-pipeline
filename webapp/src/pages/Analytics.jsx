import { useMemo, useState } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import Chips, { ChipsGroup } from '../components/Chips'
import SyncAnalyticsButton from '../components/SyncAnalyticsButton'
import SyncDelta from '../components/SyncDelta'
import Recommendations from '../components/Recommendations'
import NewJobModal from '../components/NewJobModal'
import Toast, { useToast } from '../components/Toast'
import { toISODate } from '../format'
import {
  PerfSections,
  VideoTableFull,
  VideoCard,
  FallbackBanner,
  fmtNum,
  fmtPct,
} from '../components/VideoPerf'
import { enrichVideos, deltaIndex } from '../analytics'

const WINDOW_OPTIONS = [
  { value: '7', label: '7 days' },
  { value: '30', label: '30 days' },
  { value: '90', label: '90 days' },
]

/** Network roll-up tiles ("what it is now") from the enriched video list. */
function nowTiles(videos) {
  let views = 0, likes = 0, comments = 0, subs = 0, wpct = 0, wv = 0, best = 0
  for (const v of videos) {
    views += v.totalViews || 0
    likes += Number(v.likes) || 0
    comments += Number(v.comments) || 0
    if (v.subs_gained != null) subs += Number(v.subs_gained) || 0
    if (v.retentionPct != null) {
      wpct += v.retentionPct * (v.totalViews || 0)
      wv += v.totalViews || 0
    }
    if (Number.isFinite(v.viralScore)) best = Math.max(best, v.viralScore)
  }
  return {
    views,
    avgRet: wv > 0 ? wpct / wv : null,
    eng: views > 0 ? ((likes + comments) / views) * 100 : null,
    subs,
    best,
  }
}

/** Turn a recommendation into a pre-filled New Job. */
function jobInitial(v, rec) {
  const title = v.title || v.video_id || 'this video'
  const ch = v.channel_key
  const views = fmtNum(v.totalViews)
  const map = {
    series: {
      title: `Follow-up to “${title}”`,
      prompt:
        `Make the next episode in the exact format of the winning video “${title}” (channel ${ch}). ` +
        `It is performing well (viral score ${v.viralScore}, ${v.retentionTier} retention, ${views} views in-window). ` +
        `Keep the same hook and structure that worked; change only the topic. Goal: ride the momentum and start a series.`,
    },
    remake_hook: {
      title: `Re-hook “${title}”`,
      prompt:
        `Remake “${title}” (channel ${ch}) with a much stronger first ~3 seconds. ` +
        `Reach is there but retention is weak (avg view ${v.retentionPct == null ? '—' : Math.round(v.retentionPct) + '%'}). ` +
        `Keep the topic; rewrite the opening hook and first shot to stop the scroll.`,
    },
    repackage: {
      title: `Repackage “${title}”`,
      prompt:
        `Repackage “${title}” (channel ${ch}) for discovery: new title + thumbnail, and consider a Shorts recut. ` +
        `Watch-through is solid but few people arrive. Don't change the content — fix the packaging and re-promote.`,
    },
  }
  const m = map[rec.action.kind] || map.series
  return { channel_key: ch, type: 'produce_short', title: m.title, prompt: m.prompt, model: 'opus', effort: 'high' }
}

export default function Analytics() {
  const { toast, show } = useToast()
  const [channel, setChannel] = useState('')
  const [days, setDays] = useState('30')
  const [modal, setModal] = useState(null)

  const chansQ = usePoll(() => api.get('?r=channels'), 0)

  const scope = channel ? `&channel=${encodeURIComponent(channel)}` : ''
  const summaryQ = usePoll(() => api.get(`?r=video_summary&days=${days}${scope}`), 0, [channel, days])
  const statsQ = usePoll(() => api.get(`?r=video_stats&days=${days}${scope}`), 0, [channel, days])
  const deltasQ = usePoll(
    () => api.get(`?r=video_deltas${channel ? `&channel=${encodeURIComponent(channel)}` : ''}`),
    0,
    [channel]
  )

  const channels = (chansQ.data && chansQ.data.channels) || []
  const rawVideos = (summaryQ.data && summaryQ.data.videos) || []
  const statsRows = (statsQ.data && statsQ.data.rows) || []
  const deltas = deltasQ.data || null

  const accents = {}
  for (const c of channels) accents[c.key] = c.accent

  const dIdx = useMemo(() => deltaIndex(deltas), [deltas])
  const videos = useMemo(
    () =>
      enrichVideos(rawVideos, Number(days)).map((v) => {
        const d = dIdx.get(v.video_id)
        return d
          ? { ...v, d_views: d.d_views, d_likes: d.d_likes, d_comments: d.d_comments, rank_change: d.rank_change, rank_now: d.rank_now, is_new: d.is_new }
          : v
      }),
    [rawVideos, dIdx, days]
  )

  const now = useMemo(() => nowTiles(videos), [videos])

  const movers = useMemo(() => {
    if (!deltas || deltas.is_first) return []
    const withDelta = videos.filter((v) => !v.is_new && (v.d_views != null || Number.isFinite(v.rank_change)))
    return [...withDelta]
      .sort((a, b) => (Number(b.d_views) || 0) - (Number(a.d_views) || 0))
      .filter((v) => (Number(v.d_views) || 0) !== 0 || (Number(v.rank_change) || 0) !== 0)
      .slice(0, 6)
  }, [videos, deltas])

  const channelOptions = [
    { value: '', label: 'All channels' },
    ...channels.map((c) => ({ value: c.key, label: c.name || c.key })),
  ]

  const nowGrid = [
    { label: 'views · window', value: fmtNum(now.views) },
    { label: 'avg retention', value: now.avgRet == null ? '—' : fmtPct(now.avgRet) },
    { label: 'engagement', value: now.eng == null ? '—' : fmtPct(now.eng) },
    { label: 'subs · window', value: fmtNum(now.subs) },
    { label: 'top viral score', value: now.best ? String(now.best) : '—' },
  ]

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Analytics</h1>
          <p className="sub">What changed since last sync · what each video is · what to do next</p>
        </div>
        <div className="head-actions">
          <SyncAnalyticsButton onToast={show} />
        </div>
      </header>

      {summaryQ.error && <div className="error-bar">{summaryQ.error.message}</div>}

      <div className="chips-bar">
        <ChipsGroup label="Channel">
          <Chips options={channelOptions} value={channel} onChange={setChannel} ariaLabel="Channel" />
        </ChipsGroup>
        <ChipsGroup label="Window">
          <Chips options={WINDOW_OPTIONS} value={days} onChange={setDays} ariaLabel="Window" />
        </ChipsGroup>
      </div>

      <SyncDelta deltas={deltas} loading={deltasQ.loading && !deltas} />

      <section>
        <div className="gen-section">
          <span className="gen-section-label">Where things stand</span>
          <span className="gen-section-line" />
        </div>
        <div className="stat-grid">
          {nowGrid.map((t) => (
            <div className="card stat" key={t.label}>
              <div className="stat-value">{t.value}</div>
              <div className="stat-label">{t.label}</div>
            </div>
          ))}
        </div>
      </section>

      <FallbackBanner statsRows={statsRows} />

      <Recommendations
        videos={videos}
        accents={accents}
        onAction={async (v, rec) => {
          // staged-only (2026-08-07): a recommendation plans a calendar item and stages it
          // (Produce in stages), instead of the old direct produce_short job.
          const init = jobInitial(v, rec)
          try {
            const res = await api.post({
              action: 'create_calendar_item',
              channel_key: init.channel_key,
              planned_date: toISODate(new Date()),
              title: init.title,
              brief: init.prompt,
              model: init.model,
              effort: init.effort,
            })
            await api.post({ action: 'stage_calendar_item', id: res.item.id })
            show('Staged — the factory is planning the asset list in Studio', 'ok')
          } catch (e) {
            show(e.message, 'error')
          }
        }}
      />

      {movers.length > 0 && (
        <section>
          <div className="gen-section">
            <span className="gen-section-label">Movers since last sync</span>
            <span className="gen-section-count">{movers.length}</span>
            <span className="gen-section-line" />
          </div>
          <div className="perf-grid">
            {movers.map((v) => (
              <VideoCard key={v.video_id} v={v} accent={accents[v.channel_key]} />
            ))}
          </div>
        </section>
      )}

      <PerfSections videos={videos} accents={accents} loading={summaryQ.loading && summaryQ.data == null} />

      <VideoTableFull videos={videos} accents={accents} />

      <Toast toast={toast} />

      {modal && (
        <NewJobModal
          channels={channels}
          initial={modal}
          onClose={() => setModal(null)}
          onCreated={(job) => {
            setModal(null)
            show(`Queued “${job && job.title ? job.title : 'job'}”`, 'ok')
          }}
        />
      )}
    </div>
  )
}
