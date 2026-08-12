import { Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import DoNext from '../components/DoNext'
import { timeAgo } from '../format'

/**
 * Today — the home screen (UX declutter redesign). One idea: what needs you
 * right now, in order. The DoNext queue IS the page; totals collapse into a
 * single sentence; the machine room shrinks to a one-line health strip.
 */
export default function Overview() {
  const { data, error } = usePoll(() => api.get('?r=overview'), 8000)
  const jobsQ = usePoll(() => api.get('?r=jobs&limit=100'), 30000)

  const totals = (data && data.totals) || {}
  const events = (data && data.recent_events) || []
  const jobs = (jobsQ.data && jobsQ.data.jobs) || []
  const failed = jobs.filter((j) => j.status === 'failed').length
  const running = jobs.filter((j) => j.status === 'running').length
  const lastEvent = events[0]

  const bits = []
  if (totals.channels) bits.push(`${totals.channels} channels`)
  if (totals.jobs_done) bits.push(`${totals.jobs_done} tasks finished`)
  if (totals.renders) bits.push(`${totals.renders} finished pieces in the Library`)
  const summary = bits.join(' · ')

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Today</h1>
          <p className="sub">What needs you right now, in the order it should happen.</p>
        </div>
      </header>

      {error && <div className="error-bar">{error.message}</div>}

      <DoNext hero />

      {summary && <p className="today-summary dim">{summary}</p>}

      <Link to="/jobs" className={'today-strip' + (failed > 0 ? ' is-failing' : '')}>
        {failed > 0 ? (
          <>
            <span className="today-strip-dot bad" />
            {failed} task{failed > 1 ? 's' : ''} failed — see what happened →
          </>
        ) : (
          <>
            <span className="today-strip-dot ok" />
            Behind the scenes: all healthy
            {running > 0 && ` · ${running} task${running > 1 ? 's' : ''} running`}
            {lastEvent && lastEvent.created_at && ` · last activity ${timeAgo(lastEvent.created_at)}`} →
          </>
        )}
      </Link>
    </div>
  )
}
