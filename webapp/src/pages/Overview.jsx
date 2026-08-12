import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import StatusChip from '../components/StatusChip'
import EmptyState from '../components/EmptyState'
import DoNext from '../components/DoNext'
import SyncAnalyticsButton from '../components/SyncAnalyticsButton'
import Toast, { useToast } from '../components/Toast'
import { timeAgo } from '../format'

function eventText(ev) {
  return (
    ev.message || ev.detail || ev.description || ev.text || ev.event || ev.type || 'event'
  )
}

export default function Overview() {
  const { data, error, loading } = usePoll(() => api.get('?r=overview'), 8000)
  const histQ = usePoll(() => api.get('?r=renders&origin=historical'), 0)
  const navigate = useNavigate()
  const { toast, show } = useToast()
  const totals = (data && data.totals) || {}
  const jobs = (data && data.recent_jobs) || []
  const events = (data && data.recent_events) || []
  const histCount = histQ.data ? ((histQ.data.renders || []).length) : null

  const cards = [
    { label: 'Jobs done', value: totals.jobs_done, tone: 'green' },
    { label: 'Jobs failed', value: totals.jobs_failed, tone: 'red' },
    { label: 'Renders', value: totals.renders },
    { label: 'Historical renders', value: histCount, pending: histQ.data == null && histQ.loading },
    { label: 'Channels', value: totals.channels },
  ]

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Overview</h1>
          <p className="sub">The factory floor at a glance · refreshes every 8s</p>
        </div>
        <div className="head-actions">
          <SyncAnalyticsButton onToast={show} />
        </div>
      </header>

      {error && <div className="error-bar">{error.message}</div>}

      <DoNext />

      <div className="stat-grid">
        {cards.map((c) => (
          <div className="card stat" key={c.label}>
            <div className={'stat-value' + (c.tone ? ` tone-${c.tone}` : '')}>
              {(data == null && loading) || c.pending ? '—' : c.value != null ? c.value : 0}
            </div>
            <div className="stat-label">{c.label}</div>
          </div>
        ))}
      </div>

      <div className="two-col">
        <section className="card panel">
          <div className="panel-head">
            <h2>Recent jobs</h2>
            <Link className="link" to="/jobs">
              All jobs →
            </Link>
          </div>
          {jobs.length === 0 ? (
            <EmptyState message="No jobs yet" hint="Queue one from the Jobs page." />
          ) : (
            <ul className="row-list">
              {jobs.map((j) => (
                <li key={j.id} className="row-item" onClick={() => navigate('/jobs')}>
                  <StatusChip status={j.status} />
                  <span className="row-title">{j.title || '(untitled)'}</span>
                  <span className="tag">{j.channel_key}</span>
                  <span className="row-time">{timeAgo(j.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card panel">
          <div className="panel-head">
            <h2>Activity</h2>
          </div>
          {events.length === 0 ? (
            <EmptyState message="No activity yet" hint="Events appear as the factory works." />
          ) : (
            <ul className="feed">
              {events.map((ev, i) => (
                <li key={ev.id || i} className="feed-item">
                  <span className="feed-dot" />
                  <div className="feed-body">
                    <div className="feed-text">{eventText(ev)}</div>
                    <div className="feed-meta">
                      {[ev.type, ev.channel_key].filter(Boolean).join(' · ')}
                      {(ev.type || ev.channel_key) && ' · '}
                      {timeAgo(ev.created_at)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <Toast toast={toast} />
    </div>
  )
}
