const LABELS = {
  queued: 'Queued',
  running: 'Running',
  done: 'Done',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

export default function StatusChip({ status }) {
  const s = String(status || 'queued').toLowerCase()
  return (
    <span className={`chip chip-${s}`}>
      <span className="chip-dot" />
      {LABELS[s] || s}
    </span>
  )
}

/** Subtle amber hint for running jobs whose worker heartbeat went quiet. */
export function StaleHint() {
  return (
    <span
      className="stale-hint"
      title="No worker heartbeat for over 3 minutes — the job may be orphaned"
    >
      stale?
    </span>
  )
}
