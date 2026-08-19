import { useState, useEffect } from 'react'
import { api } from '../api'
import Modal from './Modal'
import UltracodeToggle from './UltracodeToggle'
import SuggestButton from './SuggestButton'
import Toast, { useToast } from './Toast'
import { JOB_TYPES, MODEL_OPTIONS, EFFORTS } from '../jobMeta'
import { toISODate } from '../format'

/**
 * Default "plan content" form payload. Shared with StudioLauncher so both the
 * modal and the inline Studio launcher POST the exact same shape to
 * `create_calendar_item` (channel + title + brief up front; the produce
 * type/model/effort defaults ride along invisibly).
 */
export function planContentDefaults(channels = []) {
  return {
    channel_key: channels[0] ? channels[0].key : '',
    planned_date: toISODate(new Date()),
    title: '',
    brief: '',
    type: 'produce_short',
    model: 'opus',
    effort: 'high',
    ultracode: false,
  }
}

/** Fire the create action the modal uses and return the fresh calendar item. */
export async function createCalendarItem(form) {
  const res = await api.post({ action: 'create_calendar_item', ...form })
  return res.item
}

export default function PlanContentModal({ channels = [], onClose, onCreated }) {
  const [form, setForm] = useState(() => planContentDefaults(channels))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const { toast, show } = useToast()
  // S5: pick which locked composition this piece runs through, at plan time.
  const [compPin, setCompPin] = useState('')
  const [comps, setComps] = useState([])
  const chan = channels.find((c) => c.key === form.channel_key)
  const tplKey = chan && chan.template ? chan.template : null

  useEffect(() => {
    if (!form.channel_key && channels.length > 0) {
      setForm((f) => (f.channel_key ? f : { ...f, channel_key: channels[0].key }))
    }
  }, [channels]) // eslint-disable-line react-hooks/exhaustive-deps

  // load the selected channel's LOCKED composition library; reset when the
  // channel changes (compositions are channel-specific).
  useEffect(() => {
    setCompPin('')
    setComps([])
    if (!tplKey) return
    let ok = true
    api
      .get(`?r=template_versions&template_key=${encodeURIComponent(tplKey)}&include_retired=1`)
      .then((d) => { if (ok) setComps((d.versions || []).filter((v) => v.status === 'locked')) })
      .catch(() => {})
    return () => { ok = false }
  }, [tplKey]) // eslint-disable-line react-hooks/exhaustive-deps

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const item = await createCalendarItem(form)
      // create_calendar_item doesn't take template_version_id; pin the chosen
      // composition in a follow-up (same action the plan drawer uses). Non-fatal.
      if (compPin && item && item.id) {
        try {
          await api.post({ action: 'set_calendar_template_version', calendar_id: item.id, template_version_id: compPin })
        } catch { /* leave on channel default */ }
      }
      onCreated(item)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Modal title="Plan Content" onClose={onClose} width={560}>
      <form className="form" onSubmit={submit}>
        <div className="form-row">
          <label className="field">
            <span className="field-label">Channel</span>
            <select value={form.channel_key} onChange={set('channel_key')} required>
              {channels.length === 0 && <option value="">Loading channels…</option>}
              {channels.map((c) => (
                <option key={c.key} value={c.key}>
                  {c.name || c.key}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field-label">Date</span>
            <input
              type="date"
              value={form.planned_date}
              onChange={set('planned_date')}
              required
            />
          </label>
        </div>
        {tplKey && (
          <label className="field">
            <span className="field-label">Composition</span>
            <select value={compPin} onChange={(e) => setCompPin(e.target.value)}>
              <option value="">— channel default —</option>
              {comps.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version}
                  {v.label ? ' · ' + v.label : ''}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="field">
          <div className="field-label-row">
            <span className="field-label">Title</span>
            <SuggestButton
              channelKey={form.channel_key}
              seed={form.title}
              onResult={(r) =>
                setForm((f) => ({
                  ...f,
                  title: r.title || f.title,
                  brief: r.brief || f.brief,
                }))
              }
              onError={(msg) => show(msg, 'error')}
            />
          </div>
          <input
            value={form.title}
            onChange={set('title')}
            placeholder="The video's title — e.g. I Built An App By Typing One Line"
            required
          />
        </label>
        <label className="field">
          <span className="field-label">Brief</span>
          <textarea
            rows={5}
            value={form.brief}
            onChange={set('brief')}
            placeholder="Instructions for the pipeline when this gets queued…"
          />
        </label>
        <div className="form-row">
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
          <label className="field">
            <span className="field-label">Model</span>
            <select value={form.model} onChange={set('model')}>
              {MODEL_OPTIONS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-row">
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
          <div className="field">
            <span className="field-label">Orchestration</span>
            <UltracodeToggle
              checked={form.ultracode}
              onChange={(v) => setForm((f) => ({ ...f, ultracode: v }))}
            />
          </div>
        </div>
        {error && <div className="form-error">{error}</div>}
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={busy || !form.channel_key || !form.title.trim() || !form.planned_date}
          >
            {busy ? 'Planning…' : 'Plan Content'}
          </button>
        </div>
      </form>
      <Toast toast={toast} />
    </Modal>
  )
}
