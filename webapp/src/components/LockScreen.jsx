import { useState } from 'react'
import { api, setToken, clearToken } from '../api'

export default function LockScreen({ initialError, onUnlock }) {
  const [value, setValue] = useState('')
  const [error, setError] = useState(initialError || '')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    const token = value.trim()
    if (!token || busy) return
    setBusy(true)
    setError('')
    setToken(token)
    try {
      await api.get('?r=overview')
      onUnlock()
    } catch (err) {
      clearToken()
      setError(err.status === 401 ? 'Invalid token — access denied' : err.message)
      setBusy(false)
    }
  }

  return (
    <div className="lock-wrap">
      <form className="lock-card" onSubmit={submit}>
        <div className="lock-brand">
          <span className="brand-dot big" />
          <div className="brand-name">THE FACTORY</div>
          <div className="brand-sub">control room access</div>
        </div>
        <label className="field">
          <span className="field-label">Factory token</span>
          <input
            type="password"
            autoFocus
            placeholder="Paste your token"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            spellCheck={false}
            autoComplete="off"
          />
        </label>
        {error && <div className="form-error">{error}</div>}
        <button className="btn btn-primary btn-block" type="submit" disabled={busy || !value.trim()}>
          {busy ? 'Verifying…' : 'Unlock'}
        </button>
        <p className="lock-hint">The token is stored only in this browser.</p>
      </form>
    </div>
  )
}
