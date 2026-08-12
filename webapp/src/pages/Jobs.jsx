import { useState, useEffect, useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { activityPhrase, isStaleRunning } from '../jobMeta'
import { resolveAccents, accentFor } from '../channelColor'
import { getRecap } from '../components/JobRecap'
import JobDrawer from '../components/JobDrawer'
import NewJobModal from '../components/NewJobModal'
import StopJobDialog, { StopIcon } from '../components/StopJobDialog'
import ConfirmDialog from '../components/ConfirmDialog'
import EmptyState from '../components/EmptyState'
import { timeAgo } from '../format'

/**
 * Activity — replacement for the raw jobs table (UX declutter redesign).
 * Three intent lanes instead of 101 rows: fix what broke, watch what's
 * running, skim what finished. Plain creator language everywhere; IDs, models,
 * effort and raw types live only in the JobDrawer.
 */

const dayKey = (iso) => (iso ? String(iso).slice(0, 10) : '')

function dayLabel(key) {
  const today = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const todayKey = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`
  const y = new Date(today)
  y.setDate(y.getDate() - 1)
  const yKey = `${y.getFullYear()}-${pad(y.getMonth() + 1)}-${pad(y.getDate())}`
  if (key === todayKey) return 'Today'
  if (key === yKey) return 'Yesterday'
  const d = new Date(key + 'T12:00')
  return isNaN(d.getTime())
    ? key
    : d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })
}

/** Minutes-in sentence for a running task. */
function elapsedLine(j) {
  const start = j.started_at || j.created_at
  if (!start) return ''
  const mins = Math.max(0, Math.round((Date.now() - new Date(start).getTime()) / 60000))
  const t = new Date(start)
  const clock = t.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  return mins < 1 ? `just started — ${clock}` : `${mins} min in — started ${clock}`
}

/** Duration sentence for a finished task. */
function tookLine(j) {
  if (!j.started_at || !j.finished_at) return ''
  const mins = Math.round((new Date(j.finished_at) - new Date(j.started_at)) / 60000)
  if (mins < 1) return 'took under a minute'
  if (mins < 60) return `took ${mins} min`
  return `took ${Math.round(mins / 60 * 10) / 10} h`
}

/** Prefill for "Try again" — same shape the recap Fix & re-run uses. */
function retryPrefill(j) {
  return {
    channel_key: j.channel_key,
    type: j.type === 'produce_short' ? 'custom' : j.type,
    title: j.title || '',
    prompt: j.prompt || '',
    model: j.model,
    effort: j.effort,
    ultracode: !!j.ultracode,
  }
}

function ChanDot({ accent, name }) {
  return (
    <span className="act-chan">
      <span className="act-chan-dot" style={{ background: accent }} />
      {name}
    </span>
  )
}

export default function Jobs() {
  const jobsQ = usePoll(() => api.get('?r=jobs&limit=100'), 8000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const [selected, setSelected] = useState(null)
  const [modal, setModal] = useState(null)
  const [channel, setChannel] = useState('')
  const [stopTarget, setStopTarget] = useState(null)
  const [cancelTarget, setCancelTarget] = useState(null)
  const [cancelBusy, setCancelBusy] = useState(false)
  const [queueOpen, setQueueOpen] = useState(false)
  const [openDays, setOpenDays] = useState({}) // dayKey -> bool (Today defaults open)
  const [showAllDays, setShowAllDays] = useState({}) // dayKey -> bool (uncap group)
  const location = useLocation()
  const navigate = useNavigate()

  // Deep links preserved: state.newJob pre-fills the modal, state.openJob opens a drawer.
  useEffect(() => {
    const st = location.state
    if (st && st.newJob) {
      setSelected(null)
      setModal(st.newJob)
      navigate('/jobs', { replace: true })
    } else if (st && st.openJob) {
      setSelected(st.openJob)
      navigate('/jobs', { replace: true })
    }
  }, [location.state]) // eslint-disable-line react-hooks/exhaustive-deps

  const jobs = (jobsQ.data && jobsQ.data.jobs) || []
  const channels = (chansQ.data && chansQ.data.channels) || []
  const accents = useMemo(() => resolveAccents(channels), [channels])
  const chanName = useMemo(() => {
    const m = { _network: 'The whole network' }
    for (const c of channels) m[c.key] = c.name || c.key
    return m
  }, [channels])

  const visible = channel ? jobs.filter((j) => j.channel_key === channel) : jobs

  const lanes = useMemo(() => {
    const failed = []
    const stale = []
    const running = []
    const queued = []
    const doneByDay = new Map()
    for (const j of visible) {
      if (j.status === 'failed') failed.push(j)
      else if (j.status === 'running' && isStaleRunning(j)) stale.push(j)
      else if (j.status === 'running') running.push(j)
      else if (j.status === 'queued') queued.push(j)
      else if (j.status === 'done' || j.status === 'cancelled') {
        const k = dayKey(j.finished_at || j.created_at)
        if (!doneByDay.has(k)) doneByDay.set(k, [])
        doneByDay.get(k).push(j)
      }
    }
    const days = [...doneByDay.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1)).slice(0, 7)
    return { failed, stale, running, queued, days }
  }, [visible])

  // Status sentence — carries every count; reflects the channel filter (critique R4).
  const sentence = useMemo(() => {
    const scope = channel ? (chanName[channel] || channel) + ': ' : ''
    const nAttn = lanes.failed.length + lanes.stale.length
    if (nAttn > 0)
      return { tone: 'bad', text: `${scope}${nAttn} task${nAttn > 1 ? 's' : ''} hit a problem — start there.` }
    if (lanes.running.length > 0)
      return {
        tone: '',
        text: `${scope}${lanes.running.length} task${lanes.running.length > 1 ? 's' : ''} running${lanes.queued.length ? `, ${lanes.queued.length} waiting` : ''} — nothing needs you.`,
      }
    if (lanes.queued.length > 0)
      return { tone: '', text: `${scope}${lanes.queued.length} task${lanes.queued.length > 1 ? 's' : ''} waiting to start.` }
    const today = lanes.days.find(([k]) => dayLabel(k) === 'Today')
    if (today) return { tone: '', text: `${scope}All quiet — ${today[1].length} task${today[1].length > 1 ? 's' : ''} finished today.` }
    return { tone: '', text: `${scope}All quiet.` }
  }, [lanes, channel, chanName])

  const doCancel = async () => {
    if (!cancelTarget || cancelBusy) return
    setCancelBusy(true)
    try {
      await api.post({ action: 'cancel_job', id: cancelTarget.id })
      jobsQ.refresh()
    } catch (e) {
      /* the list poll will re-show it; drawer has full error surface */
    }
    setCancelBusy(false)
    setCancelTarget(null)
  }

  const loading = jobsQ.loading && jobsQ.data == null
  const allQuiet =
    !loading && lanes.failed.length === 0 && lanes.stale.length === 0 &&
    lanes.running.length === 0 && lanes.queued.length === 0 && lanes.days.length === 0

  const card = (j, kind) => {
    const accent = accentFor(j.channel_key, accents)
    const recap = getRecap(j)
    const reason =
      kind === 'failed'
        ? (recap && recap.issues && recap.issues[0]) ||
          (j.error ? 'It stopped because: ' + String(j.error).split('\n')[0].slice(0, 140) : 'It stopped with a problem.')
        : null
    return (
      <div key={j.id} className={'act-card' + (kind === 'failed' ? ' is-failed' : kind === 'stale' ? ' is-stale' : '')}>
        <div className="act-card-top">
          <ChanDot accent={accent} name={chanName[j.channel_key] || j.channel_key} />
          <span className="act-eyebrow">{activityPhrase(j.type, kind === 'running' ? 'now' : 'past')}</span>
        </div>
        <div className="act-title">{j.title || '(untitled)'}</div>
        {kind === 'running' && (
          <div className="act-line dim">
            <span className="act-pulse" aria-hidden="true" /> {elapsedLine(j)}
          </div>
        )}
        {kind === 'stale' && (
          <div className="act-line warn">The machine went quiet on this one — worth a look.</div>
        )}
        {reason && <div className="act-line dim">{reason}</div>}
        <div className="act-foot">
          <span className="dim small">{timeAgo(j.finished_at || j.started_at || j.created_at)}</span>
          <span className="act-actions">
            {kind === 'failed' && (
              <>
                <button className="btn btn-ghost btn-sm" onClick={() => setModal(retryPrefill(j))}>
                  Try again
                </button>
                <button className="btn btn-ghost btn-sm" onClick={() => setSelected(j.id)}>
                  See what happened
                </button>
              </>
            )}
            {kind === 'stale' && (
              <>
                <button className="btn btn-ghost btn-sm" onClick={() => setSelected(j.id)}>
                  Check on it
                </button>
                <button
                  className="icon-btn act-stop"
                  title={j.control === 'stop' ? 'Stopping…' : 'Stop this task'}
                  disabled={j.control === 'stop'}
                  onClick={() => setStopTarget(j)}
                >
                  <StopIcon />
                </button>
              </>
            )}
            {kind === 'running' && (
              <>
                <button className="btn btn-ghost btn-sm" onClick={() => setSelected(j.id)}>
                  Watch
                </button>
                <button
                  className="icon-btn act-stop"
                  title={j.control === 'stop' ? 'Stopping…' : 'Stop this task'}
                  disabled={j.control === 'stop'}
                  onClick={() => setStopTarget(j)}
                >
                  <StopIcon />
                </button>
              </>
            )}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Activity</h1>
          <p className={'sub' + (sentence.tone === 'bad' ? ' tone-red' : '')}>{sentence.text}</p>
          <p className="dim small" style={{ margin: '2px 0 0' }}>Updates itself every few seconds.</p>
        </div>
        <div className="head-actions">
          <select
            className="act-chan-select"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            aria-label="Filter by channel"
          >
            <option value="">All channels</option>
            {channels.map((c) => (
              <option key={c.key} value={c.key}>{c.name || c.key}</option>
            ))}
          </select>
          <button className="btn btn-primary" onClick={() => setModal({})}>
            + New task
          </button>
        </div>
      </header>

      {jobsQ.error && <div className="error-bar">{jobsQ.error.message}</div>}

      {loading ? (
        <div className="act-skeletons">
          {[0, 1, 2].map((i) => <div key={i} className="act-card act-skeleton" />)}
        </div>
      ) : allQuiet ? (
        <EmptyState message="All quiet." hint="The factory has nothing on its plate — give it a task." />
      ) : (
        <>
          {(lanes.failed.length > 0 || lanes.stale.length > 0) && (
            <section className="act-lane">
              <div className="act-lane-head">
                <span className="act-lane-label">Needs your attention</span>
                <span className="dim small">
                  {lanes.failed.length > 0 && `${lanes.failed.length} task${lanes.failed.length > 1 ? 's' : ''} stopped with a problem`}
                  {lanes.failed.length > 0 && lanes.stale.length > 0 && ' · '}
                  {lanes.stale.length > 0 && `${lanes.stale.length} gone quiet`}
                </span>
              </div>
              <div className="act-stack">
                {lanes.failed.map((j) => card(j, 'failed'))}
                {lanes.stale.map((j) => card(j, 'stale'))}
              </div>
            </section>
          )}

          <section className="act-lane">
            <div className="act-lane-head">
              <span className="act-lane-label">Happening now</span>
            </div>
            {lanes.running.length === 0 && lanes.queued.length === 0 ? (
              <p className="dim" style={{ padding: '2px 2px 6px' }}>Nothing running right now.</p>
            ) : (
              <>
                <div className="act-stack">{lanes.running.map((j) => card(j, 'running'))}</div>
                {lanes.queued.length > 0 && (
                  <div className="act-queue">
                    <button className="act-queue-toggle" onClick={() => setQueueOpen((v) => !v)} aria-expanded={queueOpen}>
                      <span className={'act-chevron' + (queueOpen ? ' open' : '')} aria-hidden="true">▸</span>
                      Up next: {lanes.queued.length} task{lanes.queued.length > 1 ? 's' : ''} waiting
                    </button>
                    {queueOpen && (
                      <ul className="act-queue-list">
                        {lanes.queued.map((j) => (
                          <li key={j.id} className="act-row">
                            <span className="act-chan-dot" style={{ background: accentFor(j.channel_key, accents) }} />
                            <span className="act-eyebrow">{activityPhrase(j.type, 'now')}</span>
                            <button className="act-row-title" onClick={() => setSelected(j.id)}>{j.title || '(untitled)'}</button>
                            <span className="dim small">{timeAgo(j.created_at)}</span>
                            <button className="btn btn-ghost btn-sm" onClick={() => setCancelTarget(j)}>Cancel</button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </>
            )}
          </section>

          {lanes.days.length > 0 && (
            <section className="act-lane">
              <div className="act-lane-head">
                <span className="act-lane-label">Finished</span>
              </div>
              {lanes.days.map(([k, list], di) => {
                const label = dayLabel(k)
                const open = openDays[k] ?? (di === 0)
                const done = list.filter((j) => j.status === 'done').length
                const cancelled = list.length - done
                const capped = !(showAllDays[k]) && list.length > 10
                const shown = capped ? list.slice(0, 10) : list
                return (
                  <div key={k} className="act-day">
                    <button className="act-day-head" onClick={() => setOpenDays((s) => ({ ...s, [k]: !open }))} aria-expanded={open}>
                      <span className={'act-chevron' + (open ? ' open' : '')} aria-hidden="true">▸</span>
                      <span className="act-day-label">{label}</span>
                      <span className="dim small">
                        {done} finished{cancelled > 0 ? `, ${cancelled} cancelled` : ''}
                      </span>
                    </button>
                    {open && (
                      <ul className="act-done-list">
                        {shown.map((j) => {
                          const recap = getRecap(j)
                          const sub = (recap && recap.headline) || tookLine(j)
                          const notes = j.status === 'done' && recap && recap.issues && recap.issues.length > 0
                          return (
                            <li key={j.id}>
                              <button className="act-row act-row-btn" onClick={() => setSelected(j.id)}>
                                <span className={'act-glyph' + (j.status === 'done' ? ' ok' : ' off')} aria-hidden="true">
                                  {j.status === 'done' ? '✓' : '○'}
                                </span>
                                <span className="act-chan-dot" style={{ background: accentFor(j.channel_key, accents) }} />
                                <span className="act-row-main">
                                  <span className="act-row-line1">
                                    <span className="act-eyebrow">{activityPhrase(j.type, 'past')}</span>
                                    <span className="act-row-title-text">{j.title || '(untitled)'}</span>
                                    {notes && <span className="act-notes" title={recap.issues.join(' · ')}>finished with notes</span>}
                                  </span>
                                  {sub && <span className="act-row-sub" title={sub}>{sub}</span>}
                                </span>
                                <span className="dim small">{timeAgo(j.finished_at || j.created_at)}</span>
                              </button>
                            </li>
                          )
                        })}
                        {capped && (
                          <li>
                            <button className="act-showall" onClick={() => setShowAllDays((s) => ({ ...s, [k]: true }))}>
                              Show all {list.length} from {label.toLowerCase()}
                            </button>
                          </li>
                        )}
                      </ul>
                    )}
                  </div>
                )
              })}
              <p className="dim small" style={{ marginTop: 8 }}>Older activity isn’t shown here.</p>
            </section>
          )}
        </>
      )}

      {selected && <JobDrawer id={selected} onClose={() => setSelected(null)} onChanged={jobsQ.refresh} />}
      {stopTarget && (
        <StopJobDialog job={stopTarget} onClose={() => setStopTarget(null)} onStopped={jobsQ.refresh} />
      )}
      {cancelTarget && (
        <ConfirmDialog
          title="Cancel this task?"
          confirmLabel="Cancel it"
          danger
          busy={cancelBusy}
          onConfirm={doCancel}
          onCancel={() => setCancelTarget(null)}
        >
          <p>
            Cancel <b>{cancelTarget.title || 'this task'}</b>? It hasn’t started yet.
          </p>
        </ConfirmDialog>
      )}
      {modal && (
        <NewJobModal
          channels={channels}
          initial={modal}
          onClose={() => setModal(null)}
          onCreated={(job) => {
            setModal(null)
            jobsQ.refresh()
            if (job && job.id) setSelected(job.id)
          }}
        />
      )}
    </div>
  )
}
