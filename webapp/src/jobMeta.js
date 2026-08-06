// Shared job/calendar metadata (models, efforts, type labels)

export const JOB_TYPES = [
  { value: 'produce_short', label: 'Produce Short' },
  { value: 'record_demo', label: 'Record Demo' },
  { value: 'custom', label: 'Custom' },
  { value: 'new_channel_scaffold', label: 'New Channel Scaffold' },
]

export const TYPE_LABELS = {
  produce_short: 'Produce Short',
  record_demo: 'Record Demo',
  custom: 'Custom',
  new_channel_scaffold: 'New Channel Scaffold',
  analytics_sync: 'Analytics Sync',
  analyze_and_suggest: 'AI Analysis',
  suggest_brief: 'Brief Suggestion',
  plan_assets: 'Plan assets',
  generate_asset: 'Generate asset',
  assemble_episode: 'Assemble episode',
}

export function typeLabel(t) {
  return TYPE_LABELS[t] || t
}

export const MODEL_OPTIONS = [
  { value: 'fable', label: 'Fable 5 — deepest' },
  { value: 'opus', label: 'opus' },
  { value: 'sonnet', label: 'sonnet' },
  { value: 'haiku', label: 'haiku' },
]

/**
 * v4: job model values may arrive as aliases ('opus') OR full ids
 * ('claude-opus-5', 'us.anthropic.claude-fable-5') — shorten for display.
 */
export function modelLabel(m) {
  if (!m) return ''
  const s = String(m)
  if (s.length <= 8) return s
  const match = s.match(/claude[-.]([a-z]+)[-.]?\d*/i)
  return match ? match[1] : s
}

export const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']

/** Worker heartbeat older than this on a running job = probably dead. */
export const STALE_HEARTBEAT_MS = 3 * 60 * 1000

/**
 * True when a running job's worker heartbeat is >3 min old.
 * Legacy rows without heartbeat_at are never flagged.
 */
export function isStaleRunning(job) {
  if (!job || job.status !== 'running' || !job.heartbeat_at) return false
  const t = new Date(job.heartbeat_at).getTime()
  if (isNaN(t)) return false
  return Date.now() - t > STALE_HEARTBEAT_MS
}
