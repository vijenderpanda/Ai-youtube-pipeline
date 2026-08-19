/**
 * Pipeline model — the single source of truth for "where is this episode, and
 * what's the one next action?" (see the workflow-first redesign).
 *
 * Every episode moves along a fixed rail:  PLAN → PRODUCE → QC → ARM → LIVE.
 * Both the per-episode rail (StudioBoard) and the guided "Do next" queue
 * (Overview) derive their state from here, so they can never disagree.
 */

export const STAGES = [
  { key: 'plan', label: 'Plan' },
  { key: 'produce', label: 'Produce' },
  { key: 'qc', label: 'QC' },
  { key: 'arm', label: 'Arm' },
  { key: 'live', label: 'Live' },
]

const STAGE_INDEX = STAGES.reduce((m, s, i) => ((m[s.key] = i), m), {})
export const stageIndex = (key) => STAGE_INDEX[key] ?? 0

/** Tally an assets array the way the API does: latest version per asset_key. */
export function countsFromAssets(assets = []) {
  const latest = new Map()
  for (const a of assets) {
    const k = a.asset_key
    const cur = latest.get(k)
    if (!cur || (a.version || 0) > (cur.version || 0)) latest.set(k, a)
  }
  const c = { total: 0, queued: 0, generating: 0, review: 0, approved: 0, skipped: 0, failed: 0 }
  for (const a of latest.values()) {
    c.total += 1
    if (a.status in c) c[a.status] += 1
  }
  return c
}

/**
 * Resolve an episode's current stage + its single next action.
 * `item` is a factory_calendar row; `counts` is per-status asset counts.
 * `opts.producing` is a caller-supplied liveness flag: true when a DIRECT-mode
 * monolithic produce_preview job is still running for this piece (see below).
 * Returns { stage, label, action } where action is null (nothing for the
 * creator to do — the factory is working) or { kind, label } with
 *   kind: 'review' | 'arm' | 'fix'   (all route to the episode board).
 */
export function resolveStage(item, counts = {}, opts = {}) {
  const status = item?.status
  const producing = !!opts.producing
  const total = counts.total || 0
  const done = (counts.approved || 0) + (counts.skipped || 0)
  const failed = counts.failed || 0
  const review = counts.review || 0
  const generating = counts.generating || 0

  // Already out the door.
  if (status === 'published') return mk('live', 'Published', null)
  if (status === 'armed') return mk('live', 'Scheduled — waiting to go live', null)

  // A failed asset blocks the QC gate — surface it first, always.
  if (failed > 0) return mk('qc', `${failed} asset${failed > 1 ? 's' : ''} failed`, action('fix', `Fix ${failed} failed`))

  // In production.
  if (total === 0) return mk('produce', 'Planning assets…', null)
  if (generating > 0) return mk('produce', `Producing · ${generating} generating`, null)
  if (review > 0) return mk('qc', `${review} to review`, action('review', `Review ${review}`))
  // done>=total normally means "every part approved → ready to arm". But a
  // DIRECT-mode monolithic produce pushes its assets ALREADY-APPROVED and
  // incrementally, so mid-run "4 of 4 approved" is NOT finished — the run only
  // stamps preview_path at the very end. While that produce_preview job is live
  // the caller sets opts.producing, and we hold the piece at 'produce' (never
  // advancing to 'arm' or offering "Finalize & schedule") so the rail can't lie.
  if (total > 0 && done >= total) {
    if (producing) return mk('produce', 'Producing…', null)
    return mk('arm', 'Ready to schedule', action('arm', 'Finalize & schedule'))
  }
  return mk('produce', 'In production', null)
}

function mk(stage, label, act) {
  return { stage, label, action: act }
}
function action(kind, label) {
  return { kind, label }
}
