import { toISODate } from './format'

/**
 * Calendar item lifecycle (v7 design language).
 *
 * A calendar item's visual state is its own status *refined by* the joined
 * post (calendar_item.job_id -> posts.job_id). A post that is armed /
 * uploading / scheduled proves the video is really sitting on YouTube with a
 * publish time; a published post proves it's live.
 */

export function lifecycleOf(item, post) {
  const ps = post ? String(post.status || '').toLowerCase() : ''
  if (ps === 'published') return 'published'
  if (ps === 'armed' || ps === 'uploading' || ps === 'scheduled') return 'armed'
  return String((item && item.status) || 'planned').toLowerCase()
}

/**
 * Where a calendar item should appear + "produced early" detection.
 *
 * Display date = the linked post's publish_at date when it has one (the
 * YouTube schedule is the truth once armed), else planned_date. An item
 * queued/produced/armed/published BEFORE its planned slot gets `early`
 * plus a tooltip so a pill sitting days ahead never reads as a mystery.
 * `movable` marks items whose display still follows planned_date, so a
 * one-tap "Show on today instead" (planned_date=today) makes sense.
 */
export function calDisplay(item, post, job) {
  const planned = String((item && item.planned_date) || '').slice(0, 10)
  const lc = lifecycleOf(item, post)
  const hasPublishAt = !!(post && post.publish_at)

  let displayDate = planned
  if (hasPublishAt) {
    const d = new Date(post.publish_at)
    if (!isNaN(d.getTime())) displayDate = toISODate(d)
  }

  const active =
    lc === 'queued' || lc === 'produced' || lc === 'armed' || lc === 'published'
  let producedDate = ''
  if (active) {
    const src =
      (post && (post.created_at || post.publish_at)) ||
      (job && (job.finished_at || job.created_at)) ||
      null
    if (src) {
      const d = new Date(src)
      if (!isNaN(d.getTime())) producedDate = toISODate(d)
    }
  }

  const early = !!(active && planned && producedDate && producedDate < planned)
  return {
    displayDate: displayDate || planned,
    planned,
    producedDate,
    early,
    earlyTip: early ? `produced ${producedDate}, planned ${planned}` : '',
    movable: early && !hasPublishAt && displayDate !== toISODate(new Date()),
  }
}

export const LIFECYCLE_LABELS = {
  planned: 'Planned',
  suggested: 'AI suggested',
  queued: 'Queued',
  produced: 'Produced',
  armed: 'Scheduled on YouTube',
  published: 'Published',
  skipped: 'Skipped',
  superseded: 'Superseded',
}
