import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import Modal from '../components/Modal'
import EmptyState from '../components/EmptyState'

function NewChannelModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    key: '',
    name: '',
    niche: '',
    accent: '#E91E63',
    guidelines: '',
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
      await api.post({ action: 'create_channel', ...form })
      onCreated()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Modal title="New Channel" onClose={onClose} width={560}>
      <form className="form" onSubmit={submit}>
        <div className="form-row">
          <label className="field">
            <span className="field-label">Key</span>
            <input
              value={form.key}
              onChange={set('key')}
              placeholder="e.g. lulla-bedtime"
              pattern="[a-z0-9_-]+"
              title="lowercase letters, digits, dashes, underscores"
              required
            />
          </label>
          <label className="field">
            <span className="field-label">Accent</span>
            <input type="color" className="color-input" value={form.accent} onChange={set('accent')} />
          </label>
        </div>
        <label className="field">
          <span className="field-label">Name</span>
          <input value={form.name} onChange={set('name')} placeholder="Channel name" required />
        </label>
        <label className="field">
          <span className="field-label">Niche</span>
          <input value={form.niche} onChange={set('niche')} placeholder="e.g. calm bedtime songs for toddlers" />
        </label>
        <label className="field">
          <span className="field-label">Guidelines</span>
          <textarea
            rows={6}
            value={form.guidelines}
            onChange={set('guidelines')}
            placeholder="Voice, style, do's and don'ts for this channel…"
          />
        </label>
        {error && <div className="form-error">{error}</div>}
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy || !form.key || !form.name}>
            {busy ? 'Creating…' : 'Create Channel'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default function Channels() {
  const { data, error, loading, refresh } = usePoll(() => api.get('?r=channels'), 0)
  const [showNew, setShowNew] = useState(false)
  const navigate = useNavigate()
  const channels = (data && data.channels) || []

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Channels</h1>
          <p className="sub">Every channel the factory produces for</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowNew(true)}>
          + New Channel
        </button>
      </header>

      {error && <div className="error-bar">{error.message}</div>}

      {loading && data == null ? (
        <p className="dim">Loading…</p>
      ) : channels.length === 0 ? (
        <EmptyState message="No channels yet" hint="Create your first channel to start producing." />
      ) : (
        <div className="channel-grid">
          {channels.map((c) => (
            <div
              key={c.key}
              className="card channel-card"
              onClick={() => navigate(`/channels/${encodeURIComponent(c.key)}`)}
            >
              <div className="channel-top">
                <span className="accent-dot" style={{ background: c.accent || '#E91E63' }} />
                <span className={'status-pill' + (c.status === 'active' ? ' on' : '')}>
                  {c.status || 'active'}
                </span>
              </div>
              <div className="channel-name">{c.name || c.key}</div>
              <div className="channel-niche">{c.niche || '—'}</div>
              <div className="channel-foot">
                <span className="channel-key mono">{c.key}</span>
                <button
                  className="btn btn-ghost btn-xs"
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(`/channels/${encodeURIComponent(c.key)}/analysis`)
                  }}
                >
                  Analysis
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showNew && (
        <NewChannelModal
          onClose={() => setShowNew(false)}
          onCreated={() => {
            setShowNew(false)
            refresh()
          }}
        />
      )}
    </div>
  )
}
