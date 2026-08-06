import { useState, useEffect, useRef } from 'react'
import { api } from '../api'
import StatusChip, { StaleHint } from './StatusChip'
import StopJobDialog, { StopIcon } from './StopJobDialog'
import JobRecap, { getRecap, RecapIssues } from './JobRecap'
import { fmtDate } from '../format'
import { typeLabel, modelLabel, isStaleRunning } from '../jobMeta'

export default function JobDrawer({ id, onClose, onChanged }) {
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')
  const [cancelling, setCancelling] = useState(false)
  const [confirmStop, setConfirmStop] = useState(false)
  const [renders, setRenders] = useState([])
  const [showLogs, setShowLogs] = useState(false)
  const logRef = useRef(null)

  useEffect(() => {
    let alive = true
    let timer = null
    async function load() {
      if (document.hidden) {
        timer = setTimeout(load, 4000)
        return
      }
      try {
        const d = await api.get(`?r=job&id=${encodeURIComponent(id)}`)
        if (!alive) return
        setJob(d.job)
        setError('')
        const st = d.job && d.job.status
        if (st === 'running' || st === 'queued') timer = setTimeout(load, 4000)
      } catch (e) {
        if (!alive) return
        setError(e.message)
      }
    }
    load()
    setShowLogs(false)
    return () => {
      alive = false
      if (timer) clearTimeout(timer)
    }
  }, [id])

  const recap = getRecap(job)
  const hasOutputs = !!(recap && recap.outputs.length)
  const channelKey = job ? job.channel_key : ''

  // Recap output chips link to their render's public URL — fetch the channel's
  // recent renders once so chips can match by job_id (or filename fallback).
  useEffect(() => {
    if (!hasOutputs) return
    let alive = true
    const q =
      '?r=renders' + (channelKey ? `&channel=${encodeURIComponent(channelKey)}` : '')
    api
      .get(q)
      .then((d) => {
        if (alive) setRenders((d && d.renders) || [])
      })
      .catch(() => {}) // chips degrade to plain text without links
    return () => {
      alive = false
    }
  }, [id, hasOutputs, channelKey])

  const logs = job
    ? Array.isArray(job.logs)
      ? job.logs.join('\n')
      : job.logs || ''
    : ''

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logs])

  const cancel = async () => {
    if (cancelling) return
    setCancelling(true)
    try {
      const d = await api.post({ action: 'cancel_job', id })
      setJob(d.job)
      if (onChanged) onChanged()
    } catch (e) {
      setError(e.message)
    }
    setCancelling(false)
  }

  const live = job && (job.status === 'running' || job.status === 'queued')

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer">
        <div className="drawer-head">
          <div>
            <h3 className="drawer-title">{job ? job.title || '(untitled job)' : 'Loading…'}</h3>
            {job && (
              <div className="drawer-chips">
                <StatusChip status={job.status} />
                {isStaleRunning(job) && <StaleHint />}
                <span className="tag">{job.channel_key}</span>
                <span className="tag dim-tag">{typeLabel(job.type)}</span>
                <span className="tag dim-tag" title={job.model}>
                  {modelLabel(job.model)}
                </span>
                <span className="tag dim-tag">{job.effort}</span>
                {job.ultracode && (
                  <span
                    className="tag ultra-chip"
                    title="Ultracode — multi-agent orchestration"
                  >
                    ⚡ ultracode
                  </span>
                )}
              </div>
            )}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {error && <div className="error-bar">{error}</div>}

        {job && (
          <div className="drawer-body">
            <div className="meta-grid">
              <div>
                <span className="field-label">Created</span>
                <div>{fmtDate(job.created_at)}</div>
              </div>
              {job.updated_at && (
                <div>
                  <span className="field-label">Updated</span>
                  <div>{fmtDate(job.updated_at)}</div>
                </div>
              )}
              <div className="meta-wide">
                <span className="field-label">Job ID</span>
                <div className="mono small">{job.id}</div>
              </div>
            </div>

            {job.prompt && (
              <div className="drawer-section">
                <span className="field-label">Prompt</span>
                <pre className="prompt-box">{job.prompt}</pre>
              </div>
            )}

            {recap && (
              <JobRecap
                recap={recap}
                renders={renders}
                jobId={job.id}
                job={job}
                showIssues={job.status !== 'failed'}
              />
            )}

            {job.status === 'failed' && recap && recap.issues.length > 0 && (
              <RecapIssues issues={recap.issues} prominent job={job} />
            )}

            {job.error && (
              <div className="drawer-section">
                <span className="field-label">Error</span>
                <pre className="prompt-box error-text">{String(job.error)}</pre>
              </div>
            )}

            {recap && (
              <button
                type="button"
                className="btn btn-ghost btn-sm details-toggle"
                onClick={() => setShowLogs((v) => !v)}
              >
                {showLogs ? 'Hide details' : 'Show details'}
              </button>
            )}

            {(!recap || showLogs) && (
              <div className="drawer-section grow">
                <span className="field-label">
                  Logs{' '}
                  {job.status === 'running' && <span className="live-pill">live · 4s</span>}
                </span>
                <pre className="logbox" ref={logRef}>
                  {logs || (live ? 'Waiting for output…' : 'No logs recorded.')}
                </pre>
              </div>
            )}

            <div className="drawer-actions">
              {job.status === 'queued' && (
                <button className="btn btn-danger" onClick={cancel} disabled={cancelling}>
                  {cancelling ? 'Cancelling…' : 'Cancel job'}
                </button>
              )}
              {job.status === 'running' && (
                <button
                  className="btn btn-danger"
                  onClick={() => setConfirmStop(true)}
                  disabled={job.control === 'stop'}
                >
                  <StopIcon />
                  {job.control === 'stop' ? 'Stopping…' : 'Stop job'}
                </button>
              )}
              <button className="btn btn-ghost" onClick={onClose}>
                Close
              </button>
            </div>
          </div>
        )}
      </aside>

      {confirmStop && job && (
        <StopJobDialog
          job={job}
          onClose={() => setConfirmStop(false)}
          onStopped={(d) => {
            // Optimistic: show "Stopping…" immediately; the live 4s poll keeps
            // running (status is still 'running') until the worker flips the
            // job to cancelled.
            setJob((prev) =>
              d && d.job ? d.job : prev ? { ...prev, control: 'stop' } : prev
            )
            if (onChanged) onChanged()
          }}
        />
      )}
    </>
  )
}
