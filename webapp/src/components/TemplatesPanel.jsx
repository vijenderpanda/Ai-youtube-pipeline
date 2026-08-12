import { useState } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import Modal from './Modal'

/**
 * TemplatesPanel — the template registry, browsable + creatable (Formats page).
 * "+ New format" clones an existing template's pipeline wiring (produce/plan/
 * finalize routing + blueprint) and overrides the creative surface, so a new
 * format is immediately selectable on any channel's produce panel — no worker
 * dependency. Deeper flows (from-URL analysis, AI refinement) come later.
 */

function NewFormatModal({ templates, onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '',
    clone_from: templates[0] ? templates[0].key : '',
    description: '',
    runtime_s: '',
    tag: '',
    title_ph: '',
    brief_ph: '',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const body = {
        action: 'create_template',
        name: form.name.trim(),
        clone_from: form.clone_from,
      }
      if (form.description.trim()) body.description = form.description.trim()
      if (form.runtime_s.trim()) body.runtime_s = parseInt(form.runtime_s, 10)
      if (form.tag.trim() || form.title_ph.trim() || form.brief_ph.trim()) {
        body.produce_ui = {
          tag: form.tag.trim() || '🧪 ' + form.name.trim(),
          tag_title: form.description.trim(),
          title_ph: form.title_ph.trim() || 'Episode title…',
          brief_ph: form.brief_ph.trim() || 'The idea, the beats, and any facts to verify first…',
        }
      }
      const d = await api.post(body)
      onCreated(d.template)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Modal title="New format" onClose={onClose} width={560}>
      <form className="form" onSubmit={submit}>
        <label className="field">
          <span className="field-label">Name</span>
          <input value={form.name} onChange={set('name')} placeholder="e.g. Kinetic Countdown v2" required autoFocus />
        </label>
        <label className="field">
          <span className="field-label">Start from <span className="dim">(inherits its whole production pipeline)</span></span>
          <select value={form.clone_from} onChange={set('clone_from')}>
            {templates.map((t) => (
              <option key={t.key} value={t.key}>{t.name}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field-label">What's different <span className="dim">(one or two lines)</span></span>
          <textarea rows={3} value={form.description} onChange={set('description')}
            placeholder="e.g. Ranked countdown with kinetic serif ordinals, loop-seam ending, host only in the last 3s…" />
        </label>
        <div className="form-row">
          <label className="field">
            <span className="field-label">Target length (s)</span>
            <input value={form.runtime_s} onChange={set('runtime_s')} placeholder="30" inputMode="numeric" />
          </label>
          <label className="field">
            <span className="field-label">Panel tag <span className="dim">(shown on the produce panel)</span></span>
            <input value={form.tag} onChange={set('tag')} placeholder="🧪 Kinetic Countdown" />
          </label>
        </div>
        <label className="field">
          <span className="field-label">Title placeholder</span>
          <input value={form.title_ph} onChange={set('title_ph')} placeholder="e.g. Top 5 Claude Code ___ That ___" />
        </label>
        <label className="field">
          <span className="field-label">Brief placeholder</span>
          <input value={form.brief_ph} onChange={set('brief_ph')} placeholder="The 5 items, their one-number proofs, and the #1 payoff…" />
        </label>
        {error && <div className="form-error">{error}</div>}
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={busy || !form.name.trim() || !form.clone_from}>
            {busy ? 'Creating…' : 'Create format'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default function TemplatesPanel() {
  const tplsQ = usePoll(() => api.get('?r=templates'), 0)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const [showNew, setShowNew] = useState(false)
  const [justMade, setJustMade] = useState(null)

  const templates = (tplsQ.data && tplsQ.data.templates) || []
  const channels = (chansQ.data && chansQ.data.channels) || []
  const usedBy = (key) => channels.filter((c) => c.template === key).map((c) => c.name || c.key)

  return (
    <section className="act-lane">
      <div className="act-lane-head">
        <span className="act-lane-label">Templates</span>
        <span className="dim small">every production pipeline as data · pick one on a channel's produce panel</span>
        <button className="btn btn-primary btn-sm" style={{ marginLeft: 'auto' }} onClick={() => setShowNew(true)}>
          + New format
        </button>
      </div>

      {justMade && (
        <div className="queued-banner" style={{ marginBottom: 10 }}>
          Format “{justMade.name}” created — select it on a channel's produce panel to use it.
        </div>
      )}

      {tplsQ.loading && tplsQ.data == null ? (
        <p className="dim">Loading…</p>
      ) : (
        <div className="tpl-grid">
          {templates.map((t) => {
            const users = usedBy(t.key)
            const proposal = /proposal/i.test(t.name || '')
            return (
              <div key={t.key} className="card tpl-card">
                <div className="tpl-card-top">
                  <span className="tpl-badge">{proposal ? '🧪' : '🔒'}</span>
                  <span className="tpl-name">{t.name}</span>
                </div>
                {t.description && <p className="tpl-desc">{t.description}</p>}
                <div className="tpl-meta dim small">
                  {t.runtime_s ? `${t.runtime_s}s` : '—'} · {t.aspect || '9:16'} ·{' '}
                  {t.finalize_script ? 'full pipeline (can schedule)' : 'no arm pipeline yet'}
                </div>
                <div className="tpl-foot">
                  {users.length > 0 ? (
                    <span className="small tpl-used">used by {users.join(', ')}</span>
                  ) : (
                    <span className="small dim">not in use</span>
                  )}
                  {t.blueprint_source && (
                    <span className="mono small dim" title={t.blueprint_source}>blueprint ✓</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showNew && (
        <NewFormatModal
          templates={templates}
          onClose={() => setShowNew(false)}
          onCreated={(t) => {
            setShowNew(false)
            setJustMade(t)
            tplsQ.refresh()
          }}
        />
      )}
    </section>
  )
}
