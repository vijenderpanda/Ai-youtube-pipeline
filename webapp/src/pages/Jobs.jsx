import { useState, useEffect, useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { typeLabel } from '../jobMeta'
import Chips, { ChipsGroup } from '../components/Chips'
import JobTable from '../components/JobTable'
import JobDrawer from '../components/JobDrawer'
import NewJobModal from '../components/NewJobModal'

const STATUS_ORDER = ['queued', 'running', 'done', 'failed', 'cancelled']
const STATUS_LABELS = {
  queued: 'Queued',
  running: 'Running',
  done: 'Done',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

export default function Jobs() {
  const jobsQ = usePoll(() => api.get('?r=jobs&limit=100'), 8000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const [selected, setSelected] = useState(null)
  const [modal, setModal] = useState(null) // null | {initial values}
  const [status, setStatus] = useState('')
  const [type, setType] = useState('')
  const [channel, setChannel] = useState('')
  const location = useLocation()
  const navigate = useNavigate()

  // Deep links: state.newJob pre-fills the modal (Generators),
  // state.openJob opens a job drawer (Calendar "View job").
  useEffect(() => {
    const st = location.state
    if (st && st.newJob) {
      setSelected(null) // recap "Fix & re-run" / "Run" arrive with a drawer open
      setModal(st.newJob)
      navigate('/jobs', { replace: true })
    } else if (st && st.openJob) {
      setSelected(st.openJob)
      navigate('/jobs', { replace: true })
    }
  }, [location.state]) // eslint-disable-line react-hooks/exhaustive-deps

  const jobs = (jobsQ.data && jobsQ.data.jobs) || []
  const channels = (chansQ.data && chansQ.data.channels) || []

  const filtered = jobs.filter(
    (j) =>
      (!status || j.status === status) &&
      (!type || j.type === type) &&
      (!channel || j.channel_key === channel)
  )

  const statusOptions = [
    { value: '', label: 'All', count: jobs.length },
    ...STATUS_ORDER.map((s) => ({
      value: s,
      label: STATUS_LABELS[s],
      count: jobs.filter((j) => j.status === s).length,
    })).filter((o) => o.count > 0),
  ]

  const typeOptions = useMemo(() => {
    const present = [...new Set(jobs.map((j) => j.type).filter(Boolean))]
    return [
      { value: '', label: 'All types' },
      ...present.map((t) => ({
        value: t,
        label: typeLabel(t),
        count: jobs.filter((j) => j.type === t).length,
      })),
    ]
  }, [jobs])

  const channelOptions = [
    { value: '', label: 'All channels' },
    ...channels.map((c) => ({
      value: c.key,
      label: c.name || c.key,
      count: jobs.filter((j) => j.channel_key === c.key).length,
    })),
  ]

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Jobs</h1>
          <p className="sub">Production queue · refreshes every 8s</p>
        </div>
        <button className="btn btn-primary" onClick={() => setModal({})}>
          + New Job
        </button>
      </header>

      {jobsQ.error && <div className="error-bar">{jobsQ.error.message}</div>}

      <div className="chips-bar">
        <ChipsGroup label="Status">
          <Chips options={statusOptions} value={status} onChange={setStatus} ariaLabel="Status" />
        </ChipsGroup>
        <ChipsGroup label="Type">
          <Chips options={typeOptions} value={type} onChange={setType} ariaLabel="Type" />
        </ChipsGroup>
        <ChipsGroup label="Channel">
          <Chips
            options={channelOptions}
            value={channel}
            onChange={setChannel}
            ariaLabel="Channel"
          />
        </ChipsGroup>
      </div>

      {jobsQ.loading && jobsQ.data == null ? (
        <p className="dim">Loading…</p>
      ) : (
        <div className="card panel">
          <JobTable
            jobs={filtered}
            onSelect={(j) => setSelected(j.id)}
            onChanged={jobsQ.refresh}
          />
        </div>
      )}

      {selected && (
        <JobDrawer id={selected} onClose={() => setSelected(null)} onChanged={jobsQ.refresh} />
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
