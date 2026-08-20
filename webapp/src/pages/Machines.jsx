import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import Toast, { useToast } from '../components/Toast'

/* =============================================================================
   MACHINES — the boxes that do the work, and the two things that actually stop
   them.

   Built from what this factory's failure history really contains, not from what
   a machine page usually shows:

     · WORKER RESTARTS ORPHAN RUNNING WORK. Roughly three dozen failures across
       two weeks are one sentence — "orphaned: worker restarted mid-job". That
       is a machine event, not a content failure, so it belongs here and not on
       a piece.
     · THE AI BUDGET IS PER ACCOUNT, NOT PER MACHINE. On 18 Aug a staged produce
       fanned out 31 asset jobs in six seconds across both boxes; every one died
       on the account cap. More machines cannot fix that — only fewer concurrent
       jobs or a later start can — so the budget is shown once, at the top,
       across the whole factory.

   Everything here is a control the API already has: pause/resume a box, cap its
   parallel slots, restrict which job types it accepts, and pause the factory.
   ========================================================================== */

const fmtAgo = (iso) => {
  if (!iso) return 'never'
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return m + 'm ago'
  const h = Math.round(m / 60)
  return h < 48 ? h + 'h ago' : Math.round(h / 24) + 'd ago'
}
const istTime = (iso) =>
  iso ? new Date(iso).toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }) : null

const JOB_TYPES = ['produce_preview', 'shell_script', 'generate_asset', 'plan_content', 'analyze_and_suggest', 'analytics_sync']
/* shell_script runs committed scripts directly — no `claude -p`, so its failures
   can never be the AI cap. Only these types spend the account quota. */
const AI_TYPES = new Set(['produce_preview', 'generate_asset', 'plan_content', 'analyze_and_suggest', 'produce_short', 'custom', 'channel_intake'])

/* Maintenance the app can run on a box. Mirrors the server's allow-list — the
   client sends an id, never a script path. `os` keeps PowerShell off the Mac. */
// Mirrors the server-side allow-list in factory-api. `os` lists the machines a
// switch has a script for — the browser never names a path, it names an action,
// and the edge function picks the PowerShell or the bash twin from the OS.
const MAINTENANCE = [
  { id: 'disk_report', label: 'Disk report', hint: 'reads only — shows what is eating the disk', os: ['Windows', 'Darwin'] },
  { id: 'disk_clean', label: 'Free up disk', hint: 'drops package and tool caches it can rebuild', os: ['Windows', 'Darwin'], destructive: true },
  { id: 'disk_deep', label: 'Deep clean', hint: 'also drops browser and Playwright caches', os: ['Darwin'], destructive: true },
  { id: 'docker_reclaim', label: 'Reclaim Docker disk', hint: 'removes unused images — the biggest single win on this Mac', os: ['Darwin'], destructive: true },
  { id: 'keep_awake', label: 'Stop it sleeping', hint: 'holds the machine awake so jobs finish', os: ['Windows', 'Darwin'] },
  { id: 'schedule_maint', label: 'Weekly auto-cleanup', hint: 'registers the recurring cleanup', os: ['Windows', 'Darwin'] },
]

export default function Machines() {
  const { toast, show } = useToast()
  const [busy, setBusy] = useState('')
  const [openTypes, setOpenTypes] = useState(null)

  const workersQ = usePoll(() => api.get('?r=workers'), 15000)
  const jobsQ = usePoll(() => api.get('?r=jobs&limit=200'), 20000)
  const workers = (workersQ.data && workersQ.data.workers) || []
  const jobs = (jobsQ.data && jobsQ.data.jobs) || []

  const act = async (body, tag, ok) => {
    setBusy(tag)
    try {
      const d = await api.post(body)
      if (d && d.error) throw new Error(d.error)
      show(ok, 'ok')
      workersQ.refresh(); jobsQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setBusy('')
  }

  /* The budget is one number for the whole factory, because the quota is one
     account. Take the worker that has spent the most in the current window. */
  const budget = useMemo(() => {
    const us = workers.map((w) => (w.meta || {}).usage).filter(Boolean)
    if (!us.length) return null
    const spend = us.reduce((s, u) => s + (Number(u.cost_usd) || 0), 0)
    const limited = us.some((u) => u.rate_limited)
    const reset = us.map((u) => u.reset_est).filter(Boolean).sort()[0]
    const jobsRun = us.reduce((s, u) => s + (Number(u.jobs) || 0), 0)
    return { spend, limited, reset, jobsRun, windowH: us[0].window_h }
  }, [workers])

  /* Failures, split by what actually caused them — because the fix differs. */
  const failures = useMemo(() => {
    const failed = jobs.filter((j) => j.status === 'failed')
    const orphaned = failed.filter((j) => String(j.error || '').startsWith('orphaned'))
    const rest = failed.filter((j) => !String(j.error || '').startsWith('orphaned'))
    // A burst = many failures of one type within a couple of minutes: the
    // signature of a fan-out hitting the account cap, not N separate problems.
    const byDay = new Map()
    for (const j of rest) {
      const k = String(j.created_at).slice(0, 10) + '|' + j.type
      byDay.set(k, (byDay.get(k) || 0) + 1)
    }
    const bursts = [...byDay.entries()]
      .filter(([, n]) => n >= 5)
      .map(([k, n]) => ({ day: k.split('|')[0], type: k.split('|')[1], n, ai: AI_TYPES.has(k.split('|')[1]) }))
      .sort((a, b) => b.n - a.n)
    const burstCount = bursts.reduce((s, b) => s + b.n, 0)
    return { total: failed.length, orphaned, rest, bursts, singles: rest.length - burstCount }
  }, [jobs])

  const running = jobs.filter((j) => j.status === 'running' || j.status === 'queued')

  return (
    <div className="piece machines">
      <div className="piece-head">
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="crumb">Machines</div>
          <h1 className="piece-title">The boxes that do the work</h1>
          <div className="piece-sub">
            {workers.length} machine{workers.length === 1 ? '' : 's'} · {running.length} job
            {running.length === 1 ? '' : 's'} in flight
          </div>
        </div>
        <div className="piece-chips">
          <button
            className="btn btn-ghost"
            disabled={!!busy}
            onClick={() => act({ action: 'global_pause', paused: true }, 'pauseall', 'All machines paused')}
          >
            Pause everything
          </button>
          <button
            className="btn btn-ghost"
            disabled={!!busy}
            onClick={() => act({ action: 'global_pause', paused: false }, 'resumeall', 'All machines resumed')}
          >
            Resume
          </button>
        </div>
      </div>

      {/* ── the budget, once, for the whole factory ─────────────────────── */}
      {budget && (
        <section className={'mach-budget' + (budget.limited ? ' spent' : '')}>
          <div>
            <div className="pc-eyebrow" style={{ margin: 0 }}>AI budget · one account, all machines</div>
            <div className="amt">
              ${budget.spend.toFixed(2)}
              <span className="sub">
                {' '}spent in this {budget.windowH || 5}h window · {budget.jobsRun} job
                {budget.jobsRun === 1 ? '' : 's'}
                {budget.reset ? ` · resets ${istTime(budget.reset)} IST` : ''}
              </span>
            </div>
          </div>
          <div className="note">
            {budget.limited
              ? 'Capped right now — more machines cannot help, the quota is per account.'
              : 'Adding a machine does not add quota. Concurrency is what spends it.'}
          </div>
        </section>
      )}

      {/* ── machines ────────────────────────────────────────────────────── */}
      <div className="mach-grid">
        {workers.map((w) => {
          const id = w.worker_id || w.name
          const awake = w.last_seen && Date.now() - new Date(w.last_seen).getTime() < 15 * 60 * 1000
          const res = (w.meta || {}).resources || {}
          const mine = jobs.filter((j) => j.assigned_worker === id)
          const live = mine.filter((j) => j.status === 'running' || j.status === 'queued').length
          const accepts = Array.isArray(w.accept_types) && w.accept_types.length ? w.accept_types : null
          return (
            <section key={id} className={'mach' + (w.paused ? ' paused' : awake ? '' : ' asleep')}>
              <div className="top">
                <span className="dot" />
                <div style={{ minWidth: 0 }}>
                  <div className="nm">{w.name}</div>
                  <div className="sub">
                    {w.os}
                    {w.gpu ? ' · ' + w.gpu : ''} · seen {fmtAgo(w.last_seen)}
                  </div>
                </div>
                <span className="state">{w.paused ? 'paused' : awake ? 'awake' : 'asleep'}</span>
              </div>

              <div className="stats">
                {res.cpu && <span><b>{Math.round(res.cpu.pct)}%</b> cpu</span>}
                {res.ram && <span><b>{res.ram.used_gb}</b>/{res.ram.total_gb} GB</span>}
                {res.disk && (
                  <span className={res.disk.used_gb / res.disk.total_gb >= 0.85 ? 'risk' : undefined}>
                    <b>{Math.round((res.disk.used_gb / res.disk.total_gb) * 100)}%</b> disk
                  </span>
                )}
                {res.gpu && <span><b>{res.gpu.util_pct}%</b> gpu · {res.gpu.temp_c}°C</span>}
              </div>

              {res.disk && res.disk.used_gb / res.disk.total_gb >= 0.85 && (
                <div className="mach-warn">
                  Only {Math.round(res.disk.total_gb - res.disk.used_gb)} GB free — renders write
                  gigabytes per episode, and this box stops mid-produce when it runs out.
                </div>
              )}
              <div className="piece-kv"><span>In flight</span><b>{live} of {w.max_parallel}</b></div>
              <div className="piece-kv">
                <span>Takes</span>
                <b>
                  <button className="link-btn link" onClick={() => setOpenTypes(openTypes === id ? null : id)}>
                    {accepts ? accepts.join(', ') : 'any job'}
                  </button>
                </b>
              </div>

              {openTypes === id && (
                <div className="mach-types">
                  <div className="pc-eyebrow" style={{ margin: '0 0 8px' }}>Which work this box takes</div>
                  <button
                    className={'ty' + (!accepts ? ' on' : '')}
                    disabled={!!busy}
                    onClick={() => act({ action: 'update_worker', worker_id: id, accept_types: [] }, 'ty:' + id, 'Takes any job now')}
                  >
                    any job
                  </button>
                  {JOB_TYPES.map((t) => {
                    const on = accepts && accepts.includes(t)
                    const next = on ? accepts.filter((x) => x !== t) : [...(accepts || []), t]
                    return (
                      <button
                        key={t}
                        className={'ty' + (on ? ' on' : '')}
                        disabled={!!busy}
                        onClick={() => act({ action: 'update_worker', worker_id: id, accept_types: next }, 'ty:' + id, 'Updated what this box takes')}
                      >
                        {t}
                      </button>
                    )
                  })}
                  <div className="dim small" style={{ marginTop: 8 }}>
                    This is how work is split between boxes — the GPU box can take renders while the
                    Mac takes the agent work.
                  </div>
                </div>
              )}

              {(() => {
                const mine2 = MAINTENANCE.filter((m) => !m.os || m.os.includes(w.os))
                if (!mine2.length) {
                  return (
                    <div className="dim small" style={{ marginTop: 10 }}>
                      No maintenance scripts for {w.os} yet.
                    </div>
                  )
                }
                return (
                  <div className="mach-maint">
                    <div className="pc-eyebrow" style={{ margin: '0 0 8px' }}>Run on this box</div>
                    {mine2.map((m) => {
                      const last = jobs.find((j) => j.meta && j.meta.maintenance === m.id && j.assigned_worker === id)
                      const live = last && (last.status === 'queued' || last.status === 'running')
                      return (
                        <div key={m.id} className="mrow">
                          <div style={{ minWidth: 0 }}>
                            <div className="ml">{m.label}</div>
                            <div className="mh">{m.hint}</div>
                          </div>
                          {last && !live && <span className={'mst ' + last.status}>{last.status} {fmtAgo(last.finished_at || last.created_at)}</span>}
                          <button
                            className={'btn ' + (m.destructive ? 'btn-ghost' : 'btn-ghost')}
                            disabled={!!busy || live}
                            title={!awake ? 'This box is asleep — it picks the job up when it wakes' : undefined}
                            onClick={() => {
                              if (m.destructive && !window.confirm(`${m.label} on ${w.name}?\n\nThis ${m.hint}. It cannot be undone.`)) return
                              act({ action: 'run_maintenance', worker_id: id, maintenance: m.id }, 'mt:' + m.id, `${m.label} queued on ${w.name}`)
                            }}
                          >
                            {live ? 'running…' : busy === 'mt:' + m.id ? 'queuing…' : awake ? 'Run' : 'Queue'}
                          </button>
                        </div>
                      )
                    })}
                    {!awake && (
                      <div className="dim small" style={{ marginTop: 6 }}>
                        Asleep — anything you queue runs when it next checks in.
                      </div>
                    )}
                  </div>
                )
              })()}

              <div className="piece-foot" style={{ marginTop: 12, paddingTop: 11 }}>
                <button
                  className="btn btn-ghost"
                  disabled={!!busy}
                  onClick={() => act({ action: 'update_worker', worker_id: id, paused: !w.paused }, 'p:' + id, w.paused ? 'Resumed' : 'Paused')}
                >
                  {w.paused ? 'Resume this box' : 'Pause this box'}
                </button>
                <button
                  className="btn btn-ghost"
                  disabled={!!busy}
                  onClick={() =>
                    act(
                      { action: 'update_worker', worker_id: id, max_parallel: Math.max(1, (w.max_parallel || 1) - 1) },
                      'mp:' + id,
                      'Fewer jobs at once — less quota burned per minute'
                    )
                  }
                >
                  − slot
                </button>
                <button
                  className="btn btn-ghost"
                  disabled={!!busy}
                  onClick={() =>
                    act({ action: 'update_worker', worker_id: id, max_parallel: (w.max_parallel || 1) + 1 }, 'mp:' + id, 'One more job at a time')
                  }
                >
                  + slot
                </button>
              </div>
            </section>
          )
        })}
      </div>

      {/* ── what has been failing, by cause ─────────────────────────────── */}
      <section className="pc-card" style={{ marginTop: 14 }}>
        <span className="pc-eyebrow">What has been failing · {failures.total} in the last 200 jobs</span>

        <div className="mach-cause">
          <div className="n">{failures.orphaned.length}</div>
          <div>
            <div className="h">Killed by a restart</div>
            <div className="d">
              “orphaned: worker restarted mid-job”. Not a content failure — the box went down while
              the job was running. Restarting during a produce is what costs the most, since the
              work is redone from the start.
            </div>
          </div>
        </div>

        {failures.bursts.map((b) => (
          <div className="mach-cause" key={b.day + b.type}>
            <div className="n warn">{b.n}</div>
            <div>
              <div className="h">
                {b.n} × {b.type} died together on {b.day}
              </div>
              <div className="d">
                {b.ai ? (
                  <>
                    A fan-out hitting the AI cap: many jobs started within seconds and the quota is
                    per account, so they failed as one event. The fix is fewer parallel slots or a
                    smaller fan-out — not another machine.
                  </>
                ) : (
                  <>
                    One bad run, counted many times — these run committed scripts directly, with no
                    AI quota involved, so a cluster this tight is the same script failing repeatedly.{' '}
                    <Link className="link" to="/jobs">Read the log →</Link>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}

        {failures.singles > 0 && (
          <div className="mach-cause">
            <div className="n">{failures.singles}</div>
            <div>
              <div className="h">One-off errors</div>
              <div className="d">
                Individual jobs that failed on their own reason. <Link className="link" to="/jobs">Open the log →</Link>
              </div>
            </div>
          </div>
        )}
      </section>

      <Toast toast={toast} />
    </div>
  )
}
