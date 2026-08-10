import { useState, useEffect, useRef } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import { typeLabel, MODEL_OPTIONS, EFFORTS } from '../jobMeta'

function OverridePanel({ override, globalPaused, onChanged }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const enabled = !!(override && override.enabled)
  const model = (override && override.model) || 'opus'
  const effort = (override && override.effort) || 'high'

  const post = async (body) => {
    setBusy(true); setErr('')
    try { await api.post(body); onChanged() }
    catch (e) { setErr(e.message || 'update failed') }
    finally { setBusy(false) }
  }

  return (
    <div className="card panel" style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <strong style={{ fontSize: 14 }}>Global model / effort override</strong>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={enabled}
            disabled={busy}
            onChange={(e) => post({ action: 'set_override', enabled: e.target.checked, model, effort })}
          />
          <span>{enabled ? 'ON' : 'off'}</span>
        </label>
        <select value={model} disabled={busy || !enabled}
          onChange={(e) => post({ action: 'set_override', enabled: true, model: e.target.value, effort })}>
          {MODEL_OPTIONS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
        </select>
        <select value={effort} disabled={busy || !enabled}
          onChange={(e) => post({ action: 'set_override', enabled: true, model, effort: e.target.value })}>
          {EFFORTS.map((x) => <option key={x} value={x}>{x}</option>)}
        </select>

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto', cursor: 'pointer' }}
          title="Stops EVERY worker from claiming jobs">
          <input
            type="checkbox"
            checked={!!globalPaused}
            disabled={busy}
            onChange={(e) => post({ action: 'global_pause', paused: e.target.checked })}
          />
          <span style={{ color: globalPaused ? '#f59e0b' : 'inherit' }}>
            {globalPaused ? 'ALL workers paused' : 'Pause all workers'}
          </span>
        </label>
      </div>
      <p className="dim" style={{ fontSize: 12, margin: 0 }}>
        {enabled
          ? <>Override <strong>ON</strong> — every job on every worker runs at <strong>{model} / {effort}</strong>, ignoring the model &amp; effort it was queued with.</>
          : <>Off — each job uses its own queued model &amp; effort. Turn on to force one model/effort across the whole network (e.g. cheap <em>haiku / low</em> for a test run, or <em>fable / max</em> for a quality pass).</>}
      </p>
      {err && <div className="error-bar">{err}</div>}
    </div>
  )
}

function osGlyph(os) {
  const o = (os || '').toLowerCase()
  if (o.includes('darwin') || o.includes('mac')) return '' // Apple
  if (o.includes('windows')) return '⊞'
  if (o.includes('linux')) return '\u{1F427}'
  return '⚙'
}

function timeAgo(iso) {
  if (!iso) return 'never'
  const s = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000))
  if (s < 60) return s + 's ago'
  if (s < 3600) return Math.floor(s / 60) + 'm ago'
  if (s < 86400) return Math.floor(s / 3600) + 'h ago'
  return Math.floor(s / 86400) + 'd ago'
}

const LEVEL_COLOR = { error: '#ef4444', warn: '#f59e0b', info: 'var(--dim, #888)' }

function WorkerLogs({ workerId }) {
  // v16: default OPEN so a fresh Workers page shows live streaming logs
  // without an extra click. Users can still collapse per-card.
  const [open, setOpen] = useState(true)
  const [logs, setLogs] = useState(null)
  const [err, setErr] = useState('')
  const bottomRef = useRef(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!open) { clearInterval(intervalRef.current); return }
    const load = () => {
      api.get(`?r=worker_logs&worker_id=${encodeURIComponent(workerId)}&limit=80`)
        .then((d) => { setLogs(d.logs || []); setErr('') })
        .catch((e) => setErr(e.message || 'failed'))
    }
    load()
    intervalRef.current = setInterval(load, 6000)
    return () => clearInterval(intervalRef.current)
  }, [open, workerId])

  useEffect(() => {
    if (open && bottomRef.current) bottomRef.current.scrollIntoView({ behavior: 'smooth' })
  }, [logs, open])

  return (
    <div>
      <button className="btn btn-ghost btn-xs" onClick={() => setOpen(!open)}
        style={{ fontSize: 12 }}>
        {open ? '▾ hide logs' : '▸ logs'}
      </button>
      {open && (
        <div style={{
          marginTop: 6, background: 'var(--bg-inset, #111)', borderRadius: 6,
          padding: '8px 10px', maxHeight: 260, overflowY: 'auto', fontSize: 11,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          lineHeight: 1.55,
        }}>
          {err && <div style={{ color: '#ef4444' }}>{err}</div>}
          {logs && logs.length === 0 && <span style={{ color: 'var(--dim, #888)' }}>no logs yet</span>}
          {logs && logs.map((l, i) => (
            <div key={i} style={{ color: LEVEL_COLOR[l.level] || LEVEL_COLOR.info }}>
              <span style={{ opacity: 0.5 }}>{l.ts?.slice(11, 19) || ''}</span>{' '}
              {l.level !== 'info' && <span style={{ fontWeight: 600 }}>[{l.level}] </span>}
              {l.message}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}

function WorkerCard({ worker, jobTypes, onChanged }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [editingName, setEditingName] = useState(false)
  const [nameVal, setNameVal] = useState(worker.name || worker.worker_id)

  // accept_types null/empty = ALL types
  const accepts = Array.isArray(worker.accept_types) && worker.accept_types.length
    ? worker.accept_types
    : null
  const acceptsAll = accepts === null

  const post = async (patch) => {
    setBusy(true)
    setErr('')
    try {
      await api.post({ action: 'update_worker', worker_id: worker.worker_id, ...patch })
      onChanged()
    } catch (e) {
      setErr(e.message || 'update failed')
    } finally {
      setBusy(false)
    }
  }

  const toggleType = (t) => {
    // Build the explicit allow-list, flip t, then send. Sending the full list
    // when "all" was on lets the user carve one type out.
    const current = acceptsAll ? [...jobTypes] : [...accepts]
    const next = current.includes(t) ? current.filter((x) => x !== t) : [...current, t]
    // all selected -> null (= all); none selected -> keep [] (worker pulls nothing)
    post({ accept_types: next.length === jobTypes.length ? null : next })
  }

  return (
    <div className="card panel" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span
          title={worker.online ? 'online' : 'offline'}
          style={{
            width: 10, height: 10, borderRadius: '50%', flex: '0 0 auto',
            background: worker.online ? '#22c55e' : '#71717a',
            boxShadow: worker.online ? '0 0 8px #22c55e' : 'none',
          }}
        />
        <span style={{ fontSize: 18 }}>{osGlyph(worker.os)}</span>
        {editingName ? (
          <input
            className="input"
            value={nameVal}
            autoFocus
            onChange={(e) => setNameVal(e.target.value)}
            onBlur={() => { setEditingName(false); if (nameVal !== worker.name) post({ name: nameVal }) }}
            onKeyDown={(e) => { if (e.key === 'Enter') e.target.blur() }}
            style={{ maxWidth: 200 }}
          />
        ) : (
          <strong style={{ fontSize: 15, cursor: 'pointer' }} onClick={() => setEditingName(true)}
            title="Click to rename">
            {worker.name || worker.worker_id}
          </strong>
        )}
        {worker.paused && <span className="chip" style={{ background: '#f59e0b22', color: '#f59e0b' }}>PAUSED</span>}
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--dim, #888)' }}>
          {worker.running}/{worker.max_parallel ?? '?'} running · seen {timeAgo(worker.last_seen)}
        </span>
      </div>

      <div style={{ fontSize: 12, color: 'var(--dim, #888)', display: 'flex', gap: 14, flexWrap: 'wrap' }}>
        <span>host: {worker.hostname || '—'}</span>
        <span>os: {worker.os || '—'}</span>
        <span>gpu: {worker.gpu || 'none'}</span>
        <span>id: {worker.worker_id}</span>
      </div>

      <div>
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
          Handles {acceptsAll ? 'all job types' : `${accepts.length} of ${jobTypes.length} types`}
          {!acceptsAll && (
            <button className="btn btn-ghost btn-xs" style={{ marginLeft: 8 }}
              disabled={busy} onClick={() => post({ accept_types: null })}>
              reset to all
            </button>
          )}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {jobTypes.map((t) => {
            const on = acceptsAll || accepts.includes(t)
            return (
              <button
                key={t}
                className="chip"
                disabled={busy}
                onClick={() => toggleType(t)}
                title={on ? 'click to stop pulling this type' : 'click to pull this type'}
                style={{
                  cursor: 'pointer',
                  opacity: on ? 1 : 0.4,
                  border: on ? '1px solid #6366f1' : '1px solid transparent',
                  background: on ? '#6366f122' : '#8881',
                }}
              >
                {typeLabel(t)}
              </button>
            )
          })}
        </div>
      </div>

      {err && <div className="error-bar">{err}</div>}

      <div style={{ display: 'flex', gap: 8 }}>
        <button
          className={'btn ' + (worker.paused ? 'btn-primary' : 'btn-ghost')}
          disabled={busy}
          onClick={() => post({ paused: !worker.paused })}
        >
          {worker.paused ? 'Resume' : 'Pause'}
        </button>
      </div>

      <WorkerLogs workerId={worker.worker_id} />
    </div>
  )
}

export default function Workers() {
  const q = usePoll(() => api.get('?r=workers'), 8000)
  const workers = (q.data && q.data.workers) || []
  const jobTypes = (q.data && q.data.job_types) || []
  const override = q.data && q.data.override
  const globalPaused = q.data && q.data.global_paused

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Workers</h1>
          <p className="sub">
            Machines running the local worker · refreshes every 8s · online = heartbeat within 90s
          </p>
        </div>
      </header>

      {q.error && <div className="error-bar">{q.error.message}</div>}

      {q.data != null && (
        <OverridePanel override={override} globalPaused={globalPaused} onChanged={q.refresh} />
      )}

      {q.loading && q.data == null ? (
        <p className="dim">Loading…</p>
      ) : workers.length === 0 ? (
        <div className="card panel">
          <p className="dim" style={{ margin: 0 }}>
            No workers have registered yet. Start the worker on a machine (Mac: launchd, Windows:
            the FactoryWorker task) and it will appear here within a few seconds.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 14, gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))' }}>
          {workers.map((w) => (
            <WorkerCard key={w.worker_id} worker={w} jobTypes={jobTypes} onChanged={q.refresh} />
          ))}
        </div>
      )}

      <p className="dim" style={{ fontSize: 12, marginTop: 16 }}>
        Pausing a worker stops it claiming new jobs (running jobs finish). Type toggles route work:
        e.g. let the GPU box pull <em>assemble / preview</em> and the Mac pull the rest. Changes
        apply live — no restart. A job can also be pinned to one machine from its job drawer.
      </p>
    </div>
  )
}
