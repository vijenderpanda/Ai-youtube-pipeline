import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import JobTable from '../components/JobTable'
import JobDrawer from '../components/JobDrawer'
import NewJobModal from '../components/NewJobModal'
import RenderCard from '../components/RenderCard'
import EmptyState from '../components/EmptyState'

export default function ChannelDetail() {
  const { channelKey } = useParams()
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const jobsQ = usePoll(
    () => api.get(`?r=jobs&channel=${encodeURIComponent(channelKey)}&limit=25`),
    8000,
    [channelKey]
  )
  const rendersQ = usePoll(
    () => api.get(`?r=renders&channel=${encodeURIComponent(channelKey)}`),
    0,
    [channelKey]
  )

  const channels = (chansQ.data && chansQ.data.channels) || []
  const channel = channels.find((c) => c.key === channelKey)
  const jobs = (jobsQ.data && jobsQ.data.jobs) || []
  const renders = (rendersQ.data && rendersQ.data.renders) || []

  const [draft, setDraft] = useState(null) // null = untouched
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [saveErr, setSaveErr] = useState('')
  const [selectedJob, setSelectedJob] = useState(null)
  const [showNewJob, setShowNewJob] = useState(false)
  const [statusBusy, setStatusBusy] = useState(false)

  const guidelines = draft != null ? draft : (channel && channel.guidelines) || ''
  const dirty = draft != null && draft !== ((channel && channel.guidelines) || '')

  const saveGuidelines = async () => {
    if (saving) return
    setSaving(true)
    setSaveErr('')
    setSaveMsg('')
    try {
      await api.post({ action: 'update_channel', key: channelKey, patch: { guidelines } })
      setSaveMsg('Saved')
      setTimeout(() => setSaveMsg(''), 2500)
      chansQ.refresh()
    } catch (e) {
      setSaveErr(e.message)
    }
    setSaving(false)
  }

  const toggleStatus = async () => {
    if (!channel || statusBusy) return
    setStatusBusy(true)
    setSaveErr('')
    try {
      const next = channel.status === 'active' ? 'paused' : 'active'
      await api.post({ action: 'update_channel', key: channelKey, patch: { status: next } })
      chansQ.refresh()
    } catch (e) {
      setSaveErr(e.message)
    }
    setStatusBusy(false)
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="crumbs">
            <Link className="link" to="/channels">
              Channels
            </Link>{' '}
            <span className="dim">/</span> <span className="mono">{channelKey}</span>
          </div>
          <h1 className="with-dot">
            <span
              className="accent-dot"
              style={{ background: (channel && channel.accent) || '#E91E63' }}
            />
            {channel ? channel.name || channel.key : channelKey}
          </h1>
          <p className="sub">{(channel && channel.niche) || ''}</p>
        </div>
        <div className="head-actions">
          <Link
            className="btn btn-ghost"
            to={`/channels/${encodeURIComponent(channelKey)}/analysis`}
          >
            Analysis
          </Link>
          {channel && (
            <button className="btn btn-ghost" onClick={toggleStatus} disabled={statusBusy}>
              {channel.status === 'active' ? 'Pause channel' : 'Activate channel'}
            </button>
          )}
          <button className="btn btn-primary" onClick={() => setShowNewJob(true)}>
            + New Job
          </button>
        </div>
      </header>

      {(chansQ.error || jobsQ.error) && (
        <div className="error-bar">{(chansQ.error || jobsQ.error).message}</div>
      )}
      {saveErr && <div className="error-bar">{saveErr}</div>}

      <section className="card panel">
        <div className="panel-head">
          <h2>Guidelines</h2>
          <div className="panel-actions">
            {saveMsg && <span className="saved-msg">{saveMsg}</span>}
            <button
              className="btn btn-primary btn-sm"
              onClick={saveGuidelines}
              disabled={saving || !dirty}
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
        <textarea
          className="guidelines-box"
          rows={8}
          value={guidelines}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Voice, style, do's and don'ts for this channel…"
        />
      </section>

      <section className="card panel">
        <div className="panel-head">
          <h2>Jobs</h2>
          <span className="dim small">{jobs.length} shown · refreshes every 8s</span>
        </div>
        <JobTable
          jobs={jobs}
          showChannel={false}
          onSelect={(j) => setSelectedJob(j.id)}
          onChanged={jobsQ.refresh}
        />
      </section>

      <section className="card panel">
        <div className="panel-head">
          <h2>Renders</h2>
        </div>
        {renders.length === 0 ? (
          <EmptyState message="No renders yet — run your first job" />
        ) : (
          <div className="render-grid">
            {renders.map((r) => (
              <RenderCard key={r.id || r.storage_path} render={r} />
            ))}
          </div>
        )}
      </section>

      {selectedJob && (
        <JobDrawer
          id={selectedJob}
          onClose={() => setSelectedJob(null)}
          onChanged={jobsQ.refresh}
        />
      )}
      {showNewJob && (
        <NewJobModal
          channels={channels}
          initial={{ channel_key: channelKey }}
          onClose={() => setShowNewJob(false)}
          onCreated={() => {
            setShowNewJob(false)
            jobsQ.refresh()
          }}
        />
      )}
    </div>
  )
}
