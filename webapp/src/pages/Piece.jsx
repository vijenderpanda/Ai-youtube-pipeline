import { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { RENDERS_BASE } from '../config'
import { countsFromAssets, resolveStage } from '../pipeline'
import Toast, { useToast } from '../components/Toast'
import { fmtDayHeading } from '../format'

/* =============================================================================
   PIECE — one video's own page, from approved idea to scheduled.

   This is slice 1 of the "One Desk" redesign: it replaces the produce board
   (/studio/:id) and the Publish page for a single piece. The rules it encodes:

     · ONE gate rail — PLAN → PRODUCE → REVIEW → SCHEDULE → VERDICT — with
       exactly ONE primary button visible, always the next gate. Cheap
       reversible steps flow; the two expensive/irreversible ones stop hard.
     · The PLAN gate is the only screen that spends money, and it says what it
       will spend in ENGINE CATEGORIES (never invented dollars — no cost oracle
       exists, and a wrong number at the money gate gets ignored forever).
     · ONE current cut, its render tag printed. The SCHEDULE gate shows exactly
       what YouTube will receive — the answer to a short that once went live
       titled "ep_habit_v2_outro.mp4".

   It lives beside the old board rather than replacing it, so production keeps
   running while this is proven on real pieces.
   ========================================================================== */

const GATES = [
  { key: 'plan', label: 'Plan' },
  { key: 'produce', label: 'Produce' },
  { key: 'review', label: 'Review' },
  { key: 'schedule', label: 'Schedule' },
  { key: 'verdict', label: 'Verdict' },
]
const GATE_IX = GATES.reduce((m, g, i) => ((m[g.key] = i), m), {})

/** pipeline stage (plan|produce|qc|arm|live) → this page's gate. */
function gateFor(item, counts, producing) {
  if (!item) return 'plan'
  const { stage } = resolveStage(item, counts, { producing })
  if (producing) return 'produce'
  if (stage === 'produce') return (counts.total || 0) === 0 ? 'plan' : 'produce'
  if (stage === 'qc') return 'review'
  if (stage === 'arm') return 'schedule'
  if (stage === 'live') return 'verdict'
  return 'plan'
}

const fmtClock = (ms) => {
  const s = Math.max(0, Math.round(ms / 1000))
  return `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`
}

/* ── gate rail ─────────────────────────────────────────────────────────── */
function Rail({ gate }) {
  const at = GATE_IX[gate] ?? 0
  return (
    <div className="piece-rail" role="list" aria-label="Progress">
      {GATES.map((g, i) => (
        <span key={g.key} role="listitem" className={'pg ' + (i < at ? 'done' : i === at ? 'now' : 'next')}>
          {i < at ? '✓ ' : i === at ? '◆ ' : ''}
          {g.label}
        </span>
      ))}
    </div>
  )
}

/* ── the cut a locked composition will make ────────────────────────────── */
function SceneList({ blocks }) {
  if (!blocks.length) {
    return (
      <div className="dim small" style={{ padding: '10px 0' }}>
        This look has no designed scenes — the produce will use the channel's classic beats.
      </div>
    )
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {blocks.map((b, i) => {
        const cfg = b.config || {}
        const cb = (cfg.cookbook || cfg.broll || {}).id
        const conf = typeof cfg.confidence === 'number' ? cfg.confidence : null
        return (
          <div key={b.position ?? i} className="piece-scene">
            <span className="ix">{String(i).padStart(2, '0')}</span>
            <span className="thumb" aria-hidden="true" />
            <span style={{ minWidth: 0 }}>
              <span className="nm">{cb || b.block_type}</span>
              {cfg.line && <span className="ln">“{cfg.line}”</span>}
            </span>
            {conf != null && (
              <span className={'fit' + (conf < 0.5 ? ' low' : '')}>
                {Math.round(conf * 100)}%{conf < 0.5 ? ' · check' : ''}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function Piece() {
  const { calendarId } = useParams()
  const { toast, show } = useToast()
  const [busy, setBusy] = useState('')
  const [schedule, setSchedule] = useState('')
  const [cutApproved, setCutApproved] = useState(false)

  const boardQ = usePoll(
    () => api.get(`?r=episode_assets&calendar_id=${encodeURIComponent(calendarId)}`),
    8000,
    [calendarId]
  )
  const chansQ = usePoll(() => api.get('?r=channels'), 0)

  const item = boardQ.data && boardQ.data.item
  const assets = (boardQ.data && boardQ.data.assets) || []
  const jobs = (boardQ.data && boardQ.data.jobs) || []
  const manifest = (boardQ.data && boardQ.data.manifest) || null

  const channels = (chansQ.data && chansQ.data.channels) || []
  const chan = channels.find((c) => c.key === (item && item.channel_key))
  const tplKey = chan && chan.template ? chan.template : null

  // The locked composition this piece runs through — its blocks ARE the cut the
  // produce will make, so the plan gate can show it before anything is spent.
  const tvQ = usePoll(
    () => (tplKey ? api.get(`?r=template_versions&template_key=${encodeURIComponent(tplKey)}&include_retired=1`) : Promise.resolve(null)),
    0,
    [tplKey]
  )
  const versions = (tvQ.data && tvQ.data.versions) || []
  const allBlocks = (tvQ.data && tvQ.data.blocks) || []
  const boundId = (item && item.template_version_id) || null
  const boundVersion = versions.find((v) => v.id === boundId) || null
  const blocks = useMemo(() => {
    if (!boundId) return []
    const rows = allBlocks.filter((b) => b.template_version_id === boundId)
    if (rows.length) return [...rows].sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
    const frozen = (boundVersion && boundVersion.composition && boundVersion.composition._sequence) || []
    return [...frozen].sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
  }, [allBlocks, boundId, boundVersion])

  const counts = useMemo(() => countsFromAssets(assets), [assets])
  const newestOf = (type) =>
    jobs.filter((j) => j.type === type).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))[0] || null
  const produceJob = newestOf('produce_preview')
  const finalizeJob = newestOf('shell_script')
  const producing = !!produceJob && (produceJob.status === 'queued' || produceJob.status === 'running')

  const rawGate = gateFor(item, counts, producing)
  // REVIEW is a human gate: the piece waits there until the cut is approved,
  // even though the backend auto-approves the assets a direct produce pushes.
  const gate = rawGate === 'schedule' && !cutApproved && item && item.preview_path ? 'review' : rawGate

  // Default the publish time from the planned date (09:00), never in the past.
  useEffect(() => {
    if (!item || schedule) return
    const pad = (n) => String(n).padStart(2, '0')
    const now = new Date()
    let d = item.planned_date ? new Date(item.planned_date + 'T09:00') : null
    if (!d || isNaN(d.getTime()) || d.getTime() < now.getTime()) {
      d = new Date(now)
      d.setDate(d.getDate() + 1)
      d.setHours(9, 0, 0, 0)
    }
    setSchedule(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`)
  }, [item, schedule])

  /* ── actions ───────────────────────────────────────────────────────── */
  const doProduce = async () => {
    if (busy) return
    setBusy('produce')
    try {
      await api.post({ action: 'produce_preview', calendar_id: calendarId })
      show('Producing — this page will show it being made', 'ok')
      boardQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setBusy('')
  }

  const doSchedule = async () => {
    if (busy) return
    if (!schedule) return show('Pick a publish time first', 'error')
    setBusy('schedule')
    try {
      await api.post({ action: 'finalize_episode', calendar_id: calendarId, schedule: new Date(schedule).toISOString() })
      show('Scheduling — finishing the final cut and setting the YouTube time', 'ok')
      boardQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setBusy('')
  }

  /* ── derived display bits ──────────────────────────────────────────── */
  const previewSrc = item && item.preview_path ? RENDERS_BASE + item.preview_path : null
  const cutName = item && item.preview_path ? String(item.preview_path).split('/').pop() : null
  const title = (item && item.title) || ''
  const titleLen = title.length

  // What this produce will use — CATEGORIES, never invented dollars.
  const spend = useMemo(() => {
    const out = []
    const hasHost = blocks.some((b) => b.block_type === 'host' || ((b.config || {}).host && ((b.config || {}).host.id || (b.config || {}).host.label)))
    const freeScenes = blocks.filter((b) => ((b.config || {}).cookbook || (b.config || {}).broll || {}).id).length
    out.push({ label: 'Voice track', cost: 'paid', detail: 'ElevenLabs' })
    if (hasHost) out.push({ label: 'Host clips', cost: 'paid', detail: 'HeyGen' })
    if (freeScenes) out.push({ label: `${freeScenes} scene${freeScenes === 1 ? '' : 's'}`, cost: 'free', detail: 'rendered locally' })
    return out
  }, [blocks])

  const elapsed =
    produceJob && produceJob.started_at ? Date.now() - new Date(produceJob.started_at).getTime() : null

  if (boardQ.loading && !boardQ.data) return <p className="dim">Loading…</p>
  if (!item) return <p className="dim">That piece doesn’t exist.</p>

  return (
    <div className="piece">
      <div className="piece-head">
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="crumb">
            <Link className="link" to="/studio">Studio</Link> / piece
          </div>
          <h1 className="piece-title">{title || '(untitled)'}</h1>
          <div className="piece-sub">
            {item.channel_key}
            {item.planned_date ? ' · ' + fmtDayHeading(String(item.planned_date).slice(0, 10)) : ''}
            {boundVersion ? ` · runs through v${boundVersion.version}` : ' · channel default look'}
          </div>
        </div>
        <div className="piece-chips">
          {titleLen > 0 && (
            <span className={'chip' + (titleLen > 60 ? ' warn-chip' : '')}>{titleLen} chars</span>
          )}
          {item.auto_mode && <span className="chip">auto-mode</span>}
          <Link className="btn btn-ghost" to={'/studio/' + calendarId}>Old board →</Link>
        </div>
      </div>

      <Rail gate={gate} />

      {/* ── PLAN ─────────────────────────────────────────────────────── */}
      {gate === 'plan' && (
        <div className="piece-cols">
          <section className="card">
            <div className="field-label">The cut it will make</div>
            <SceneList blocks={blocks} />
            <div className="piece-money">
              <div className="mt">What this will use</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {spend.map((s) => (
                  <span key={s.label} className={'chip ' + (s.cost === 'paid' ? 'warn-chip' : 'ok-chip')}>
                    {s.label} · {s.detail}
                  </span>
                ))}
              </div>
              <div className="dim small" style={{ marginTop: 8 }}>
                Engine categories, not a price — the factory has no cost meter, and a wrong number here
                would be worse than none.
              </div>
            </div>
          </section>

          <section className="card">
            <div className="field-label">Checked before it burns</div>
            <div className="piece-kv"><span>Look</span><b>{boundVersion ? `v${boundVersion.version}${boundVersion.label ? ' · ' + boundVersion.label : ''}` : 'channel default'}</b></div>
            <div className="piece-kv"><span>Scenes</span><b>{blocks.length || '—'}</b></div>
            <div className="piece-kv"><span>Title length</span><b>{titleLen} chars</b></div>
            <div className="piece-kv"><span>Slot</span><b>{item.planned_date || 'unscheduled'}</b></div>
            <div className="piece-kv"><span>Brief</span><b>{item.brief ? 'present' : <span className="dim">none</span>}</b></div>
          </section>
        </div>
      )}

      {/* ── PRODUCE ──────────────────────────────────────────────────── */}
      {gate === 'produce' && (
        <div className="piece-cols">
          <section className="card">
            <div className="field-label">Being made {elapsed != null && <span className="dim small">· {fmtClock(elapsed)} elapsed</span>}</div>
            <div className="dim small" style={{ marginBottom: 10 }}>
              {produceJob && produceJob.status === 'queued'
                ? 'Queued — waiting for a free machine.'
                : 'Running. You can close this page; it keeps going.'}
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {assets.slice(0, 12).map((a) => (
                <span key={a.id} className="piece-frame" title={a.asset_key} />
              ))}
              {assets.length === 0 && <span className="dim small">No parts made yet.</span>}
            </div>
          </section>
          <section className="card">
            <div className="field-label">Latest activity</div>
            <div className="piece-log">
              {(produceJob && produceJob.logs ? String(produceJob.logs).trim().split('\n').slice(-6) : ['starting…']).map((l, i) => (
                <div key={i}>{l}</div>
              ))}
            </div>
          </section>
        </div>
      )}

      {/* ── REVIEW ───────────────────────────────────────────────────── */}
      {gate === 'review' && (
        <div className="piece-cols">
          <section className="card">
            <div className="field-label">
              Current cut {cutName && <span className="dim small">· {cutName}</span>}
            </div>
            {previewSrc ? (
              <video className="piece-player" controls preload="metadata" src={previewSrc} />
            ) : (
              <div className="dim small">The cut isn’t on disk yet.</div>
            )}
          </section>
          <section className="card">
            <div className="field-label">What it made</div>
            {manifest && Array.isArray(manifest.assets) ? (
              <div className="piece-ledger">
                {manifest.assets.slice(0, 10).map((a, i) => (
                  <div key={i} className="lrow">
                    <span>{a.type}{a.id ? ' · ' + a.id : ''}</span>
                    {a.scene != null && <span className="dim small">scene {a.scene}</span>}
                    <span className={a.cost === 'paid' ? 'warn-txt' : 'dim small'}>{a.cost}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="dim small">
                No manifest on this piece — it was produced before the manifest existed. The cut is still reviewable.
              </div>
            )}
          </section>
        </div>
      )}

      {/* ── SCHEDULE ─────────────────────────────────────────────────── */}
      {gate === 'schedule' && (
        <div className="piece-cols">
          <section className="card">
            <div className="field-label">What YouTube will receive</div>
            <div className="piece-kv"><span>Title</span><b>{title}</b></div>
            <div className="piece-kv"><span>Channel</span><b>{item.channel_key}</b></div>
            <div className="piece-kv"><span>Cut</span><b>{cutName || <span className="dim">none</span>}</b></div>
            <div className="piece-kv"><span>Look</span><b>{boundVersion ? `v${boundVersion.version}` : 'channel default'}</b></div>
            <label className="field" style={{ marginTop: 12 }}>
              <span className="field-label">Publish time</span>
              <input type="datetime-local" value={schedule} onChange={(e) => setSchedule(e.target.value)} />
            </label>
          </section>
          <section className="card">
            <div className="field-label">How it will be judged</div>
            <div className="piece-kv"><span>Clock</span><b>Shorts · 7 days</b></div>
            <div className="piece-kv"><span>No verdict</span><b>before day 3</b></div>
            <div className="dim small" style={{ marginTop: 10 }}>
              Setting the expectation now is what stops a day-zero panic later.
            </div>
          </section>
        </div>
      )}

      {/* ── VERDICT ──────────────────────────────────────────────────── */}
      {gate === 'verdict' && (
        <section className="card">
          <div className="field-label">{item.status === 'published' ? 'Published' : 'Scheduled'}</div>
          <p className="dim small" style={{ margin: 0 }}>
            {item.status === 'published'
              ? 'This piece is out. Its verdict lands on the Scoreboard once the clock allows one.'
              : 'Scheduled and waiting to go live — nothing left to do here.'}
          </p>
          {previewSrc && <video className="piece-player" controls preload="metadata" src={previewSrc} style={{ marginTop: 12 }} />}
        </section>
      )}

      {/* ── the ONE next gate ────────────────────────────────────────── */}
      <div className="piece-foot">
        {gate === 'plan' && (
          <>
            <button className="btn btn-primary" onClick={doProduce} disabled={!!busy}>
              {busy === 'produce' ? 'Starting…' : 'Approve plan & produce →'}
            </button>
            <span className="piece-why">This is the only screen that spends money.</span>
          </>
        )}
        {gate === 'produce' && (
          <span className="piece-why" style={{ marginLeft: 0 }}>
            Nothing to approve until there’s a cut.
          </span>
        )}
        {gate === 'review' && (
          <>
            <button className="btn btn-primary" onClick={() => setCutApproved(true)} disabled={!previewSrc}>
              Approve cut →
            </button>
            <button className="btn btn-ghost" onClick={doProduce} disabled={!!busy}>Rebuild it</button>
            <span className="piece-why">A failed take fails again — rebuilding costs real credits.</span>
          </>
        )}
        {gate === 'schedule' && (
          <>
            <button className="btn btn-primary" onClick={doSchedule} disabled={!!busy || !schedule}>
              {busy === 'schedule' ? 'Scheduling…' : 'Upload to YouTube →'}
            </button>
            <button className="btn btn-ghost" onClick={() => setCutApproved(false)}>Back to the cut</button>
            <span className="piece-why">The only irreversible action in the product.</span>
          </>
        )}
        {finalizeJob && finalizeJob.status === 'failed' && (
          <span className="warn-txt small">The final cut failed — see the old board for the log.</span>
        )}
      </div>

      <Toast toast={toast} />
    </div>
  )
}
