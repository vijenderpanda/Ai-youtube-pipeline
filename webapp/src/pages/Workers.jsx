import { useState, useEffect, useRef } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import { typeLabel, isAiType, MODEL_OPTIONS, EFFORTS } from '../jobMeta'

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

function fmtTokens(n) {
  if (n == null) return '—'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k'
  return String(n)
}

// Progress through the current 5-hour window, from meta.usage. reset_at (from a
// real cap-hit) is exact; reset_est (window_start + 5h) is the pre-cap estimate.
// The subscription's true quota % is NOT machine-readable, so this bar shows
// elapsed TIME through the window, not a fake used/total. Returns null when no
// Claude activity is anchoring a window yet.
function fmtWindow(u) {
  const startMs = u.window_start ? new Date(u.window_start).getTime() : null
  const resetIso = u.reset_at || u.reset_est
  const resetMs = resetIso ? new Date(resetIso).getTime() : null
  if (!startMs || !resetMs || resetMs <= startMs) return null
  const now = Date.now()
  const pct = Math.min(100, Math.max(0, Math.round(((now - startMs) / (resetMs - startMs)) * 100)))
  const mins = Math.max(0, Math.round((resetMs - now) / 60000))
  const rel = mins <= 0 ? 'now' : mins < 60 ? `${mins}m` : `${Math.floor(mins / 60)}h ${mins % 60}m`
  const clock = new Date(resetMs).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  return { pct, rel, clock, exact: !!u.reset_at, resetIso }
}

/**
 * v17: the worker-side usage rollup (factory_workers.meta.usage) — real Claude
 * spend + token totals summed over this worker's jobs inside the subscription's
 * rolling window, plus a rate_limited tripwire. This is what separates "the
 * factory is broken" from "the Claude budget ran out": AI jobs stall on the
 * cap, native jobs (analytics_sync / shell_script) never do.
 */
function UsageStrip({ meta }) {
  const u = meta && meta.usage
  if (!u) {
    return (
      <div style={{ fontSize: 12, color: 'var(--dim, #888)' }}>
        🧠 Claude usage: <em>no data yet — starts reporting after the worker runs a Claude job</em>
      </div>
    )
  }
  const w = fmtWindow(u)
  const limited = !!u.rate_limited
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12,
      background: 'var(--bg-inset, #1113)', borderRadius: 6, padding: '8px 10px',
    }}>
      {/* row 1 — used so far this window + health */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span title={`Claude spend across this worker's jobs in the current ${u.window_h}h window`}>
          🧠 <strong>used ({u.window_h}h):</strong> <strong>${(u.cost_usd ?? 0).toFixed(2)}</strong>
        </span>
        <span className="dim">{u.jobs ?? 0} job{u.jobs === 1 ? '' : 's'}</span>
        <span className="dim" title="input / output tokens in the window">
          {fmtTokens(u.input_tokens)} in / {fmtTokens(u.output_tokens)} out
        </span>
        {limited ? (
          <span className="chip" title="A job hit the Claude usage cap — AI jobs stall until it resets; native jobs (stats, scripts) keep running"
            style={{ background: '#ef444422', color: '#ef4444', fontWeight: 700 }}>RATE LIMITED</span>
        ) : (
          <span className="chip" style={{ background: '#22c55e18', color: '#22c55e' }}>ok</span>
        )}
        {u.at && <span className="dim" style={{ marginLeft: 'auto' }}>as of {timeAgo(u.at)}</span>}
      </div>

      {/* row 2 — time through the 5h window + reset countdown */}
      {w ? (
        <div title={`Resets ${new Date(w.resetIso).toLocaleString()}${w.exact ? '' : ' (estimated — the exact reset is only known once a cap is actually hit)'}`}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
            <span className="dim">{limited ? 'AI jobs resume' : `${u.window_h}h window`}</span>
            <span style={{ color: limited ? '#f59e0b' : 'var(--dim, #888)', fontWeight: limited ? 600 : 400 }}>
              {limited
                ? <>🟠 in ~{w.rel} (~{w.clock})</>
                : <>resets in ~{w.rel} (~{w.clock}){w.exact ? '' : ' · est'}</>}
            </span>
          </div>
          <div style={{ height: 6, background: '#8882', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{
              width: `${w.pct}%`, height: '100%', borderRadius: 3,
              background: limited ? '#ef4444' : '#6366f1', transition: 'width .3s',
            }} />
          </div>
        </div>
      ) : (
        <span className="dim">no Claude usage in the last {u.window_h}h — nothing counting against the limit</span>
      )}
    </div>
  )
}

function WorkerLogs({ workerId }) {
  // v16: default OPEN so a fresh Workers page shows live streaming logs
  // without an extra click. Users can still collapse per-card.
  const [open, setOpen] = useState(true)
  const [logs, setLogs] = useState(null)
  const [err, setErr] = useState('')
  const logBoxRef = useRef(null)
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

  // Keep the log tail in view by scrolling ONLY the log box — never the page.
  // scrollIntoView() walks every scrollable ancestor (incl. the window), so each
  // 6s refresh was yanking the whole Machines page down. Setting scrollTop on the
  // box itself can't move the page. Guard on near-bottom so a user who scrolled up
  // to read history isn't dragged back down mid-read.
  useEffect(() => {
    const el = logBoxRef.current
    if (!open || !el) return
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    if (nearBottom) el.scrollTop = el.scrollHeight
  }, [logs, open])

  return (
    <div>
      <button className="btn btn-ghost btn-xs" onClick={() => setOpen(!open)}
        style={{ fontSize: 12 }}>
        {open ? '▾ hide logs' : '▸ logs'}
      </button>
      {open && (
        <div ref={logBoxRef} style={{
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

      <UsageStrip meta={worker.meta} />

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
            const ai = isAiType(t)
            return (
              <button
                key={t}
                className="chip"
                disabled={busy}
                onClick={() => toggleType(t)}
                title={(ai
                  ? 'runs a Claude session — counts against the subscription limit. '
                  : 'native — no AI usage, keeps working even when the Claude cap is hit. ')
                  + (on ? 'Click to stop pulling this type.' : 'Click to pull this type.')}
                style={{
                  cursor: 'pointer',
                  opacity: on ? 1 : 0.4,
                  border: on ? '1px solid #6366f1' : '1px solid transparent',
                  background: on ? '#6366f122' : '#8881',
                }}
              >
                {ai && <span style={{ opacity: 0.75, marginRight: 3 }}>🧠</span>}
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
          <h1>Machines</h1>
          <p className="sub">The computers doing the factory’s work.</p>
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
        Types marked 🧠 run a Claude session and count against the subscription's rolling limit;
        unmarked types are native and keep working even when the AI budget is exhausted — if the
        usage strip shows <strong>RATE LIMITED</strong>, that's why AI jobs are stalling while
        stats keep updating.
      </p>
    </div>
  )
}
