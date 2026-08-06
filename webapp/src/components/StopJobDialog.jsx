import { useState } from 'react'
import { api } from '../api'
import ConfirmDialog from './ConfirmDialog'

/** Square stop glyph used on every stop control. */
export function StopIcon({ size = 10 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 10 10"
      aria-hidden="true"
      focusable="false"
    >
      <rect width="10" height="10" rx="2" fill="currentColor" />
    </svg>
  )
}

/**
 * Confirmation for stopping a *running* job.
 * POSTs stop_job; the worker notices control='stop' within ~4s and marks the
 * job cancelled — callers keep polling until that lands.
 */
export default function StopJobDialog({ job, onClose, onStopped }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const confirm = async () => {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const d = await api.post({ action: 'stop_job', id: job.id })
      if (onStopped) onStopped(d)
      onClose()
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <ConfirmDialog
      title="Stop this job?"
      confirmLabel="Stop job"
      danger
      busy={busy}
      onConfirm={confirm}
      onCancel={onClose}
    >
      <p>
        Stop <b>{job.title || 'this job'}</b>? Progress is lost.
      </p>
      {error && <div className="error-bar">{error}</div>}
    </ConfirmDialog>
  )
}
