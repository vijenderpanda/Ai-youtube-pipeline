import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import JobTable from '../components/JobTable'
import JobDrawer from '../components/JobDrawer'
import NewJobModal from '../components/NewJobModal'
import RenderCard from '../components/RenderCard'
import EmptyState from '../components/EmptyState'

export default function ChannelDetail() {
  const { channelKey } = useParams()
  const navigate = useNavigate()
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
  // v17: channel-page produce (locked Ep11/Ep12 template, auto ep-sequencing)
  const [pTitle, setPTitle] = useState('')
  const [pBrief, setPBrief] = useState('')
  const [producing, setProducing] = useState(false)
  const [pErr, setPErr] = useState('')
  // v17: idea engine (ranked 4-signal ideas)
  const [planning, setPlanning] = useState(false)
  const [ideas, setIdeas] = useState([])
  const [planErr, setPlanErr] = useState('')

  const ANGLE = {
    analytics: { icon: '📊', label: 'Analytics' },
    vaibhav: { icon: '🏆', label: 'Vaibhav-DNA' },
    news: { icon: '📰', label: 'News' },
    event: { icon: '📅', label: 'Event' },
    domain: { icon: '🌐', label: 'Domain' },
    wildcard: { icon: '🎲', label: 'Wildcard' },
  }

  // v17: channels that can produce a full episode from this page. Each has a
  // locked craft template; the produce pipeline + copy differ per channel.
  const PRODUCE_CFG = {
    'claude-tricks': {
      templateTag: '🔒 Ep11/Ep12 template',
      templateTitle: 'Locked craft template — every produce follows Ep11/Ep12',
      titlePh: 'e.g. Ask AI For a Table, Not a Wall of Text 📊',
      briefPh: "The tip, the on-screen demo, why it'll go viral, and any facts to verify first…",
    },
    'already-happening': {
      templateTag: '🔒 Cinematic blueprint',
      templateTitle: 'Locked cinematic blueprint — every produce follows Ep01',
      titlePh: "e.g. You're the last generation that will ever drive a car",
      briefPh:
        'The topic, the verified TODAY anchor (dated primary source), the +5yr leap, and 6 shot ideas…',
    },
    'aashiqana': {
      templateTag: '🔒 Sensual-motion Shorts template',
      templateTitle: 'Locked recipe — fresh couple → keyframes → Hailuo motion → premium brand',
      titlePh: 'e.g. Aadhi Raat — 2am situationship, neon rooftop',
      briefPh:
        'Song concept + mood, couple vibe, the SETTING to rotate to (not the last short), Suno style tags, the hook line…',
    },
  }
  const pcfg = PRODUCE_CFG[channelKey]

  const doPlanContent = async () => {
    if (planning) return
    setPlanning(true)
    setPlanErr('')
    try {
      const d = await api.post({ action: 'plan_content', channel_key: channelKey })
      const jobId = d.job && d.job.id
      if (!jobId) throw new Error('planning job did not start')
      const start = Date.now()
      let job = null
      while (Date.now() - start < 240000) {
        await new Promise((r) => setTimeout(r, 3000))
        const jr = await api.get(`?r=job&id=${jobId}`)
        job = jr.job || jr
        if (job.status === 'done') break
        if (job.status === 'failed' || job.status === 'cancelled')
          throw new Error(job.error || 'planning failed — is the worker running?')
      }
      const result = (job && job.result) || {}
      const list = Array.isArray(result.ideas) ? result.ideas : []
      if (!list.length) throw new Error('planning timed out or returned no ideas')
      setIdeas(list)
    } catch (e) {
      setPlanErr(e.message)
    }
    setPlanning(false)
  }

  const useIdea = (idea) => {
    setPTitle(idea.title || '')
    setPBrief(idea.brief || '')
    setIdeas([])
    setPErr('')
  }

  const doProduce = async () => {
    if (producing) return
    setProducing(true)
    setPErr('')
    try {
      const d = await api.post({
        action: 'produce_channel', channel_key: channelKey,
        title: pTitle.trim(), brief: pBrief.trim(),
      })
      if (!d || !d.calendar_id) {
        // surface a bad/empty response instead of routing to /studio/undefined;
        // keep the title/brief so the user can retry without retyping.
        throw new Error('produce started but no project id came back — check the Jobs list, the episode may still be queued')
      }
      setPTitle(''); setPBrief('')
      navigate('/studio/' + d.calendar_id)
    } catch (e) {
      setPErr(e.message)
    }
    setProducing(false)
  }

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
              style={{ background: (channel && channel.accent) || '#94A3B8' }}
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

      {pcfg && (
        <section className="card panel">
          <div className="panel-head">
            <h2>Produce new episode</h2>
            <div className="panel-actions">
              <span className="tag" title={pcfg.templateTitle}>
                {pcfg.templateTag}
              </span>
              <button className="btn btn-ghost btn-sm" onClick={doPlanContent} disabled={planning}>
                {planning ? 'Thinking… (~1–2 min)' : '✨ Plan content'}
              </button>
            </div>
          </div>
          {channelKey === 'already-happening' ? (
            <p className="dim small" style={{ marginTop: 0 }}>
              <strong>Plan content</strong> for grounded-speculation ideas from analytics · breaking
              AI news · a new life domain · upcoming events — or write your own below. Produces the
              script + VO + an <strong>animatic preview</strong> and the 6 Wan&nbsp;2.6 motion prompts →
              review in Studio → generate the 6 clips in Chrome (they replace the placeholders) →
              <strong> Finalize &amp; Arm</strong>. The <strong>episode number is auto-assigned</strong>{' '}
              when you arm. No calendar needed.
            </p>
          ) : (
            <p className="dim small" style={{ marginTop: 0 }}>
              <strong>Plan content</strong> for ranked ideas from analytics · Vaibhav-DNA · recent news ·
              upcoming events — or write your own below. Produces on the locked template → review in
              Studio → Finalize &amp; Arm; the <strong>episode number is auto-assigned</strong> when you
              arm. No calendar needed.
            </p>
          )}
          {planErr && <div className="error-bar">{planErr}</div>}
          {ideas.length > 0 && (
            <div className="idea-list" style={{ display: 'grid', gap: 10, marginBottom: 16 }}>
              {ideas.map((idea, i) => {
                const a = ANGLE[idea.angle] || { icon: '💡', label: idea.angle || 'idea' }
                return (
                  <div
                    key={i}
                    className="card"
                    style={{ padding: 14, display: 'flex', gap: 12, alignItems: 'flex-start' }}
                  >
                    <div className="mono dim" style={{ fontSize: 22, fontWeight: 800, minWidth: 30 }}>
                      #{idea.rank ?? i + 1}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                        <span className="tag" title={a.label}>{a.icon} {a.label}</span>
                        <strong>{idea.title}</strong>
                      </div>
                      {idea.hook && (
                        <div className="dim small" style={{ marginTop: 4 }}>🎙️ {idea.hook}</div>
                      )}
                      {idea.why_viral && (
                        <div className="small" style={{ marginTop: 4 }}>{idea.why_viral}</div>
                      )}
                    </div>
                    <button className="btn btn-primary btn-sm" onClick={() => useIdea(idea)}>
                      Use this
                    </button>
                  </div>
                )
              })}
            </div>
          )}
          <label className="field">
            <span className="field-label">Title</span>
            <input
              value={pTitle}
              onChange={(e) => setPTitle(e.target.value)}
              placeholder={pcfg.titlePh}
            />
          </label>
          <label className="field">
            <span className="field-label">Brief / idea</span>
            <textarea
              rows={5}
              value={pBrief}
              onChange={(e) => setPBrief(e.target.value)}
              placeholder={pcfg.briefPh}
            />
          </label>
          <div className="drawer-actions cal-actions">
            {pErr && <span className="saved-msg" style={{ color: '#f87171' }}>{pErr}</span>}
            <button
              className="btn btn-primary"
              onClick={doProduce}
              disabled={producing || !pTitle.trim() || !pBrief.trim()}
            >
              {producing ? 'Queuing…' : '▶ Produce next episode'}
            </button>
          </div>
        </section>
      )}

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
