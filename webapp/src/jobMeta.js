// Shared job/calendar metadata (models, efforts, type labels)

export const JOB_TYPES = [
  { value: 'produce_short', label: 'Produce Short' },
  { value: 'record_demo', label: 'Record Demo' },
  { value: 'custom', label: 'Custom' },
  { value: 'new_channel_scaffold', label: 'New Channel Scaffold' },
]

// Types offerable for a NEW create_job. produce_short is EXCLUDED (2026-08-07):
// production is staged-only — content is produced via Plan Content → Produce in stages.
export const NEW_JOB_TYPES = JOB_TYPES.filter((t) => t.value !== 'produce_short')

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
  preview_episode: 'Draft preview',
  produce_preview: 'Produce preview',
  shell_script: 'Finalize / script',
}

export function typeLabel(t) {
  return TYPE_LABELS[t] || t
}

/**
 * Plain-creator-language phrase for a job, used as the Activity card eyebrow.
 * tense: 'now' (present continuous) | 'past'. Never shows the raw type.
 */
const ACTIVITY_PHRASES = {
  produce_preview: ['Making a preview cut', 'Made a preview cut'],
  preview_episode: ['Making a preview cut', 'Made a preview cut'],
  generate_asset: ['Making a piece of the video', 'Made a piece of the video'],
  plan_assets: ['Planning the shots', 'Planned the shots'],
  assemble_episode: ['Putting the video together', 'Put the video together'],
  produce_short: ['Making a Short', 'Made a Short'],
  record_demo: ['Recording a screen demo', 'Recorded a screen demo'],
  analytics_sync: ['Updating your stats', 'Updated your stats'],
  analyze_and_suggest: ['Looking for ideas in your numbers', 'Looked for ideas in your numbers'],
  suggest_brief: ['Drafting an idea brief', 'Drafted an idea brief'],
  plan_content: ['Coming up with content ideas', 'Came up with content ideas'],
  channel_intake: ['Thinking through your channel idea', 'Thought through your channel idea'],
  new_channel_scaffold: ['Setting up a new channel', 'Set up a new channel'],
  shell_script: ['Running housekeeping', 'Ran housekeeping'],
  custom: ['Working on a task', 'Finished a task'],
}
export function activityPhrase(type, tense = 'now') {
  const p = ACTIVITY_PHRASES[type]
  if (!p) return tense === 'now' ? 'Working on a task' : 'Finished a task'
  return tense === 'now' ? p[0] : p[1]
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
