import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import CalendarStatusChip from './CalendarStatusChip'
import ChallengeBlock from './ChallengeBlock'
import UltracodeToggle from './UltracodeToggle'
import { JOB_TYPES, MODEL_OPTIONS, EFFORTS, typeLabel, modelLabel } from '../jobMeta'
import { fmtDate } from '../format'

export default function CalendarDrawer({
  item,
  challenger = null,
  onRunImproved,
  onKeepOriginal,
  challengeBusy = '',
  onClose,
  onChanged,
  onToast = null,
}) {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    planned_date: (item.planned_date || '').slice(0, 10),
    title: item.title || '',
    brief: item.brief || '',
    type: item.type || 'produce_short',
    model: item.model || 'opus',
    effort: item.effort || 'high',
    ultracode: !!item.ultracode,
  })
  const [status, setStatus] = useState(item.status || 'planned')
  const [jobId, setJobId] = useState(item.job_id || null)
  const [busy, setBusy] = useState('') // '' | 'save' | 'run' | 'status' | 'stage'
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [justQueued, setJustQueued] = useState(false)

  const locked = status === 'queued' || status === 'produced' || status === 'superseded'
  const suggested = status === 'suggested'
  const set = (k) => (e) => {
    setSaved(false)
    setForm((f) => ({ ...f, [k]: e.target.value }))
  }

  const save = async () => {
    if (busy) return
    setBusy('save')
    setError('')
    try {
      const d = await api.post({ action: 'update_calendar_item', id: item.id, patch: form })
      if (d.item) setStatus(d.item.status || status)
      setSaved(true)
      onChanged()
    } catch (e) {
      setError(e.message)
    }
    setBusy('')
  }

  const run = async () => {
    if (busy) return
    setBusy('run')
    setError('')
    try {
      const d = await api.post({ action: 'queue_calendar_item', id: item.id })
      setStatus((d.item && d.item.status) || 'queued')
      setJobId((d.job && d.job.id) || (d.item && d.item.job_id) || null)
      setJustQueued(true)
      onChanged()
    } catch (e) {
      setError(e.message)
    }
    setBusy('')
  }

  const setStatusTo = async (s) => {
    if (busy) return
    setBusy('status')
    setError('')
    try {
      const d = await api.post({ action: 'update_calendar_item', id: item.id, patch: { status: s } })
      setStatus((d.item && d.item.status) || s)
      onChanged()
    } catch (e) {
      setError(e.message)
    }
    setBusy('')
  }

  const viewJob = () => {
    onClose()
    navigate('/jobs', { state: { openJob: jobId } })
  }

  // Staged production: plan the asset list, then review fragments in the Studio.
  const stage = async () => {
    if (busy) return
    setBusy('stage')
    setError('')
    try {
      await api.post({ action: 'stage_calendar_item', id: item.id })
      if (onToast) onToast('Staged — the factory is planning the asset list', 'ok')
      onChanged()
      navigate('/studio/' + item.id)
      return
    } catch (e) {
      setError(e.message)
    }
    setBusy('')
  }

  // Locked items (queued/produced) keep an editable planned date — the
  // inverse of the DayPanel "Show on today instead" one-tap. Saves on change.
  const savePlannedDate = async (v) => {
    setForm((f) => ({ ...f, planned_date: v }))
    if (!v || busy) return
    setBusy('save')
    setError('')
    try {
      await api.post({
        action: 'update_calendar_item',
        id: item.id,
        patch: { planned_date: v },
      })
      onChanged()
    } catch (e) {
      setError(e.message)
    }
    setBusy('')
  }

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer">
        <div className="drawer-head">
          <div>
            <h3 className="drawer-title">{form.title || '(untitled)'}</h3>
            <div className="drawer-chips">
              <CalendarStatusChip status={status} />
              {item.origin === 'ai_suggestion' && (
                <span className="ai-badge" title={item.suggestion_reason || 'AI suggestion'}>
                  AI
                </span>
              )}
              {item.production_mode === 'staged' && (
                <button
                  type="button"
                  className="tag staged-tag"
                  onClick={() => navigate('/studio/' + item.id)}
                  title="Staged production — review assets in the Studio"
                >
                  staged →
                </button>
              )}
              <span className="tag">{item.channel_key}</span>
              <span className="tag dim-tag">{typeLabel(form.type)}</span>
              {form.ultracode && (
                <span className="tag ultra-chip" title="Ultracode — multi-agent orchestration">
                  ⚡
                </span>
              )}
            </div>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {error && <div className="error-bar">{error}</div>}

        <div className="drawer-body">
          {status === 'superseded' && (
            <div className="superseded-note">
              This plan was superseded — an improved AI version replaced it.
            </div>
          )}

          {item.suggestion_reason && (
            <div className="drawer-section">
              <span className="field-label">Why the AI suggests this</span>
              <div className="reason-box">{item.suggestion_reason}</div>
            </div>
          )}

          {item.why_not && (
            <div className="drawer-section">
              <span className="field-label">Why the AI challenges the original</span>
              <div className="reason-box amber">{item.why_not}</div>
            </div>
          )}

          {challenger && (
            <div className="drawer-section">
              <ChallengeBlock
                original={{ ...item, title: form.title, brief: form.brief }}
                challenger={challenger}
                onRunImproved={onRunImproved}
                onKeepOriginal={onKeepOriginal}
                busy={challengeBusy}
              />
            </div>
          )}

          {justQueued && (
            <div className="queued-banner">
              Job queued.{' '}
              {jobId && (
                <button className="link link-btn" onClick={viewJob}>
                  View job →
                </button>
              )}
            </div>
          )}

          {locked ? (
            <>
              <div className="meta-grid">
                <div>
                  <span className="field-label">Planned date</span>
                  {status === 'superseded' ? (
                    <div>{form.planned_date}</div>
                  ) : (
                    <input
                      type="date"
                      className="locked-date"
                      value={form.planned_date}
                      onChange={(e) => savePlannedDate(e.target.value)}
                      title="Move this item to another day (display follows the YouTube publish time once scheduled)"
                    />
                  )}
                </div>
                <div>
                  <span className="field-label">Model / effort</span>
                  <div title={form.model}>
                    {modelLabel(form.model)} · {form.effort}
                  </div>
                </div>
                <div className="meta-wide">
                  <span className="field-label">Created</span>
                  <div>{fmtDate(item.created_at)}</div>
                </div>
              </div>
              {form.brief && (
                <div className="drawer-section">
                  <span className="field-label">Brief</span>
                  <pre className="prompt-box">{form.brief}</pre>
                </div>
              )}
              <div className="drawer-actions">
                {/* backfill items carry a synthetic job_id (calendar↔post join
                    only) — there is no factory_jobs row to open */}
                {jobId && !justQueued && item.origin !== 'backfill' && (
                  <button className="btn btn-ghost" onClick={viewJob}>
                    View job →
                  </button>
                )}
                <button className="btn btn-ghost" onClick={onClose}>
                  Close
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="form-row">
                <label className="field">
                  <span className="field-label">Date</span>
                  <input type="date" value={form.planned_date} onChange={set('planned_date')} />
                </label>
                <label className="field">
                  <span className="field-label">Type</span>
                  <select value={form.type} onChange={set('type')}>
                    {JOB_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label className="field">
                <span className="field-label">Title</span>
                <input value={form.title} onChange={set('title')} required />
              </label>
              <label className="field">
                <span className="field-label">Brief</span>
                <textarea rows={5} value={form.brief} onChange={set('brief')} />
              </label>
              <div className="form-row">
                <label className="field">
                  <span className="field-label">Model</span>
                  <select value={form.model} onChange={set('model')}>
                    {/* models may arrive as full ids (claude-opus-5 etc.) — keep them selectable */}
                    {!MODEL_OPTIONS.some((m) => m.value === form.model) && form.model && (
                      <option value={form.model}>{form.model}</option>
                    )}
                    {MODEL_OPTIONS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">Effort</span>
                  <select value={form.effort} onChange={set('effort')}>
                    {EFFORTS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <UltracodeToggle
                checked={form.ultracode}
                onChange={(v) => {
                  setSaved(false)
                  setForm((f) => ({ ...f, ultracode: v }))
                }}
              />

              <div className="drawer-actions cal-actions">
                {saved && <span className="saved-msg">Saved ✓</span>}
                {suggested && (
                  <button
                    className="btn btn-ghost"
                    onClick={() => setStatusTo('skipped')}
                    disabled={!!busy}
                  >
                    Skip
                  </button>
                )}
                {status === 'skipped' && (
                  <button
                    className="btn btn-ghost"
                    onClick={() => setStatusTo('planned')}
                    disabled={!!busy}
                  >
                    Restore
                  </button>
                )}
                <button className="btn btn-ghost" onClick={save} disabled={!!busy}>
                  {busy === 'save' ? 'Saving…' : 'Save changes'}
                </button>
                <button
                  className="btn btn-primary"
                  onClick={stage}
                  disabled={!!busy || !form.title.trim() || locked}
                  title="Plan the asset list, then review each fragment in the Studio before assembly"
                >
                  {busy === 'stage' ? 'Staging…' : '▶ Produce in stages'}
                </button>
              </div>
            </>
          )}
        </div>
      </aside>
    </>
  )
}
