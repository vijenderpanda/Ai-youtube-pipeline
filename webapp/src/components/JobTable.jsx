import { useState } from 'react'
import StatusChip, { StaleHint } from './StatusChip'
import EmptyState from './EmptyState'
import StopJobDialog, { StopIcon } from './StopJobDialog'
import { timeAgo, fmtDate } from '../format'
import { typeLabel, modelLabel, isStaleRunning } from '../jobMeta'

/** Recap headline shown as a secondary row line for finished jobs. */
function recapHeadline(j) {
  if (j.status !== 'done' && j.status !== 'failed') return ''
  const r = j.result && j.result.recap
  return r && typeof r.headline === 'string' ? r.headline.trim() : ''
}

export default function JobTable({ jobs = [], onSelect, onChanged, showChannel = true }) {
  const [stopTarget, setStopTarget] = useState(null) // job pending stop confirm

  if (!jobs.length) {
    return <EmptyState message="No jobs yet" hint="Queue your first job with “New Job”." />
  }
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Title</th>
            {showChannel && <th>Channel</th>}
            <th>Type</th>
            <th>Model</th>
            <th>Effort</th>
            <th>Created</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => {
            const headline = recapHeadline(j)
            return (
            <tr key={j.id} onClick={() => onSelect && onSelect(j)}>
              <td>
                <span className="status-cell">
                  <StatusChip status={j.status} />
                  {isStaleRunning(j) && <StaleHint />}
                </span>
              </td>
              <td className="cell-title">
                <div className="cell-title-main">{j.title || '(untitled)'}</div>
                {headline && (
                  <div className="cell-sub" title={headline}>
                    {headline}
                  </div>
                )}
              </td>
              {showChannel && (
                <td>
                  <span className="tag">{j.channel_key}</span>
                </td>
              )}
              <td className="dim">{typeLabel(j.type)}</td>
              <td className="dim" title={j.model}>
                {modelLabel(j.model)}
                {j.ultracode && (
                  <span
                    className="tag ultra-chip ultra-cell"
                    title="Ultracode — multi-agent orchestration"
                  >
                    ⚡
                  </span>
                )}
              </td>
              <td className="dim">{j.effort}</td>
              <td className="dim" title={fmtDate(j.created_at)}>
                {timeAgo(j.created_at)}
              </td>
              <td className="cell-actions">
                {j.status === 'running' && (
                  <button
                    type="button"
                    className="row-stop"
                    title={j.control === 'stop' ? 'Stop requested…' : 'Stop job'}
                    aria-label="Stop job"
                    disabled={j.control === 'stop'}
                    onClick={(e) => {
                      e.stopPropagation()
                      setStopTarget(j)
                    }}
                  >
                    <StopIcon />
                  </button>
                )}
              </td>
            </tr>
            )
          })}
        </tbody>
      </table>

      {stopTarget && (
        <StopJobDialog
          job={stopTarget}
          onClose={() => setStopTarget(null)}
          onStopped={() => {
            if (onChanged) onChanged()
          }}
        />
      )}
    </div>
  )
}
