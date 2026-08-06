import { useState, useRef } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import { timeAgo } from '../format'

/**
 * v6 — Queues an analytics_sync job. Shows "last ran <relative>" from
 * overview.last_sync_at and disables (with spinner) while an analytics_sync
 * job is queued/running. `onToast(msg, tone)` reports the outcome.
 */
export default function SyncAnalyticsButton({ onToast }) {
  const [posting, setPosting] = useState(false)
  const queuedAtRef = useRef(0) // grace window so the button locks instantly after queueing
  const overviewQ = usePoll(() => api.get('?r=overview'), 30000)
  const jobsQ = usePoll(() => api.get('?r=jobs&limit=50'), 10000)

  const o = overviewQ.data || {}
  const lastSyncAt =
    o.last_sync_at ||
    (o.settings && o.settings.last_sync_at) ||
    (o.overview && o.overview.last_sync_at) ||
    null

  const jobs = (jobsQ.data && jobsQ.data.jobs) || []
  const syncing =
    jobs.some(
      (j) => j.type === 'analytics_sync' && (j.status === 'queued' || j.status === 'running')
    ) || Date.now() - queuedAtRef.current < 15000

  const run = async () => {
    if (posting || syncing) return
    setPosting(true)
    try {
      await api.post({ action: 'sync_analytics' })
      queuedAtRef.current = Date.now()
      onToast(
        'Analytics sync queued — suggestions will appear in the calendar when analysis completes',
        'ok'
      )
      jobsQ.refresh()
      overviewQ.refresh()
    } catch (e) {
      if (e.status === 409) {
        queuedAtRef.current = Date.now()
        onToast('A sync is already running', 'warn')
        jobsQ.refresh()
      } else {
        onToast(e.message, 'error')
      }
    }
    setPosting(false)
  }

  const spinning = posting || syncing
  const rel = lastSyncAt ? timeAgo(lastSyncAt) : 'never'

  return (
    <button
      className="btn btn-ghost sync-btn"
      onClick={run}
      disabled={posting || syncing}
      title={syncing ? 'An analytics sync is queued or running' : 'Queue an analytics sync'}
    >
      <svg
        className={spinning ? 'spin' : ''}
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M21 12a9 9 0 1 1-2.64-6.36" />
        <path d="M21 3v6h-6" />
      </svg>
      <span className="sync-btn-text">
        <span>{syncing ? 'Sync running…' : posting ? 'Queuing…' : 'Sync Analytics'}</span>
        <span className="sync-btn-sub">last ran {rel}</span>
      </span>
    </button>
  )
}
