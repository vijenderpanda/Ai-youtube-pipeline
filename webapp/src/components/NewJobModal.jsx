import { useState, useEffect } from 'react'
import { api } from '../api'
import Modal from './Modal'
import UltracodeToggle from './UltracodeToggle'
import SuggestButton from './SuggestButton'
import Toast, { useToast } from './Toast'
import { NEW_JOB_TYPES as TYPES, MODEL_OPTIONS, EFFORTS } from '../jobMeta'

export default function NewJobModal({ channels = [], initial = {}, onClose, onCreated }) {
  const [form, setForm] = useState({
    channel_key: initial.channel_key || (channels[0] ? channels[0].key : ''),
    type: initial.type && initial.type !== 'produce_short' ? initial.type : 'record_demo',
    title: initial.title || '',
    prompt: initial.prompt || '',
    model: initial.model || 'opus',
    effort: initial.effort || 'high',
    ultracode: !!initial.ultracode,
    target_worker: initial.target_worker || '',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [workers, setWorkers] = useState([])
  const { toast, show } = useToast()

  // v14: offer to pin the job to a specific machine ("Run on"). Best-effort —
  // if the workers endpoint fails we just omit the picker.
  useEffect(() => {
    let alive = true
    api.get('?r=workers')
      .then((r) => { if (alive) setWorkers(r.workers || []) })
      .catch(() => {})
    return () => { alive = false }
  }, [])

  // If channels arrive after mount (e.g. deep-linked from Generators), pick the first one.
  useEffect(() => {
    if (!form.channel_key && channels.length > 0) {
      setForm((f) => (f.channel_key ? f : { ...f, channel_key: channels[0].key }))
    }
  }, [channels]) // eslint-disable-line react-hooks/exhaustive-deps

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const payload = { action: 'create_job', ...form }
      if (!payload.target_worker) delete payload.target_worker  // '' = any worker
      const res = await api.post(payload)
      onCreated(res.job)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Modal title="New Job" onClose={onClose} width={560}>
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
            <span className="field-label">Type</span>
            <select value={form.type} onChange={set('type')}>
              {TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
        </div>
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
                  prompt: r.brief || f.prompt,
                }))
              }
              onError={(msg) => show(msg, 'error')}
            />
          </div>
          <input
            value={form.title}
            onChange={set('title')}
            placeholder="What should this job produce?"
            required
          />
        </label>
        <label className="field">
          <span className="field-label">Prompt / instructions</span>
          <textarea
            rows={6}
            value={form.prompt}
            onChange={set('prompt')}
            placeholder="Detailed instructions for the pipeline…"
          />
        </label>
        <div className="form-row">
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
        {workers.length > 0 && (
          <label className="field">
            <span className="field-label">Run on</span>
            <select value={form.target_worker} onChange={set('target_worker')}>
              <option value="">Any worker</option>
              {workers.map((w) => (
                <option key={w.worker_id} value={w.worker_id}>
                  {(w.name || w.worker_id) + (w.online ? '' : ' (offline)') +
                    (w.gpu ? ' · GPU' : '')}
                </option>
              ))}
            </select>
          </label>
        )}
        <UltracodeToggle
          checked={form.ultracode}
          onChange={(v) => setForm((f) => ({ ...f, ultracode: v }))}
        />
        {error && <div className="form-error">{error}</div>}
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={busy || !form.channel_key || !form.title.trim()}
          >
            {busy ? 'Queuing…' : 'Queue Job'}
          </button>
        </div>
      </form>
      <Toast toast={toast} />
    </Modal>
  )
}
