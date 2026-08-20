import { countsFromAssets, resolveStage } from './pipeline'

/* =============================================================================
   TRIAGE — the single answer to "what needs a human right now".

   This exists because Today and the sidebar badge each computed their own, with
   different windows, different job pages and different filters, so they were
   structurally guaranteed to disagree: measured 2026-08-20, the badge said 19,
   the headline said 20, six cards were drawn and the rest were named with no
   way to reach them. Both now call this.

   THE STRUCTURAL BUG THIS FIXES. `?r=staged` selects factory_calendar rows with
   status queued|produced, and finalize_episode.py's terminal write is
   status='produced' (finalize_episode.py:503). So a piece that is armed and
   live on YouTube keeps the exact status the triage feed selects for, forever,
   and nothing ever leaves the set. resolveStage guards on status 'published' /
   'armed' (pipeline.js:56-57) but factory_calendar's enum is
   planned|suggested|queued|produced|skipped (002_calendar_analytics.sql:11) —
   it can hold neither, so that guard has never once fired.

   The proof a piece shipped is its POST, not its calendar status. finalize
   writes factory_posts.calendar_id (finalize_episode.py:490) and older rows
   carry job_id, so a piece is resolved through either link. What we cannot
   prove, we do not claim: pieces with no post at all are reported separately
   and never counted as "needs you".
   ========================================================================== */

const IST = 'Asia/Kolkata'
export const istToday = () => new Date().toLocaleDateString('en-CA', { timeZone: IST })

/** A post in any of these states proves the video is on YouTube already. */
const SHIPPED = ['published', 'armed', 'scheduled', 'uploading']

export const RECENT_DAYS = 7
export const MAX_CARDS = 6

/** calendar row -> its post, via either link finalize has used over time. */
export function postIndex(posts) {
  const byCal = {}
  const byJob = {}
  for (const p of posts || []) {
    if (p.calendar_id) byCal[p.calendar_id] = p
    if (p.job_id) byJob[p.job_id] = p
  }
  return (it) => byCal[it.id] || (it.job_id ? byJob[it.job_id] : null) || null
}

/**
 * @param items       ?r=staged items
 * @param countsById  ?r=staged counts
 * @param jobs        ?r=jobs
 * @param posts       ?r=posts (ALL of them — a scheduled-only page cannot prove
 *                    a piece already published)
 * @param channels    ?r=channels
 * @param planned     ?r=calendar items — needed because ?r=staged excludes
 *                    status planned|suggested entirely, so without this the
 *                    page cannot see that a channel HAS upcoming work and will
 *                    say it has none.
 */
export function buildTriage({ items = [], countsById = {}, jobs = [], posts = [], channels = [], planned = [] }) {
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - RECENT_DAYS)
  const cutoffStr = cutoff.toLocaleDateString('en-CA', { timeZone: IST })
  const today = istToday()

  const postFor = postIndex(posts)
  const isLiveWork = (it) => !it.planned_date || it.planned_date >= cutoffStr
  const producingIds = new Set(
    jobs
      .filter((j) => j.type === 'produce_preview' && (j.status === 'queued' || j.status === 'running'))
      .map((j) => j.meta && j.meta.calendar_id)
      .filter(Boolean)
  )

  const cards = []
  let shipped = 0
  let unlinked = 0
  let stalled = 0

  for (const it of items) {
    if (['published', 'skipped', 'superseded'].includes(it.status)) continue

    // Its post is the only thing that can prove the piece is done.
    const p = postFor(it)
    if (p && SHIPPED.includes(String(p.status || '').toLowerCase())) { shipped++; continue }

    const counts = countsById[it.id] || countsFromAssets([])
    if (producingIds.has(it.id)) continue // the factory is working — not a decision

    const { stage } = resolveStage(it, counts, { producing: false })

    // Failures FIRST. resolveStage returns 'qc' whenever failed > 0, so testing
    // the cut branch first made every fresh failure render as "a cut is
    // waiting" and the ⚠ branch below was only ever reachable for pieces
    // already classified as something else.
    if (counts.failed > 0) {
      cards.push({
        k: 'fail', rank: -1, when: it.planned_date || '', icon: '⚠',
        title: `${it.title || '(untitled)'} — ${counts.failed} part${counts.failed === 1 ? '' : 's'} failed`,
        sub: `${it.channel_key} · this has to be fixed before it ships`,
        to: '/piece/' + it.id, verb: 'Open it',
      })
    } else if ((stage === 'qc' || (stage === 'arm' && it.preview_path)) && isLiveWork(it)) {
      cards.push({
        k: 'cut', rank: 0, when: it.planned_date || '', icon: '▶',
        title: `${it.title || '(untitled)'} — a cut is waiting`,
        sub: it.channel_key,
        to: '/piece/' + it.id, verb: 'Review it',
      })
    } else if (it.preview_path) {
      // A cut exists, it is past its slot, and no post references it. It may
      // well have shipped before finalize started writing the backlink, so this
      // is reported, not counted, and never called "needs you".
      unlinked++
    } else {
      // No cut on disk and no post: this one was never made. A different fact
      // from the above, and it used to fall through every branch and be counted
      // nowhere at all -- present in the badge, absent from the page.
      stalled++
    }
  }

  // A channel with nothing ahead is a fact worth acting on. It has to be read
  // from the calendar: ?r=staged cannot see 'planned' or 'suggested' at all, so
  // reading it from `items` told five of six channels they had nothing planned
  // while they held 3-17 upcoming rows.
  const aheadByChannel = {}
  for (const it of planned) {
    if (!it.planned_date || it.planned_date < today) continue
    if (['skipped', 'superseded'].includes(it.status)) continue
    if (it.replaces_id) continue
    aheadByChannel[it.channel_key] = (aheadByChannel[it.channel_key] || 0) + 1
  }
  for (const c of channels) {
    if (c.lifecycle === 'incubating' || c.status === 'paused') continue
    if (!aheadByChannel[c.key]) {
      cards.push({
        k: 'empty', rank: 2, when: '', icon: '○',
        title: `${c.name || c.key} has nothing planned`,
        sub: 'Nothing is proposed — asking costs one agent run',
        to: '/make/' + c.key, verb: '✦ Make something',
      })
    }
  }

  cards.sort((a, b) => a.rank - b.rank || String(b.when || '').localeCompare(String(a.when || '')))
  // Every item lands in exactly one bucket: a card, shipped, producing,
  // unlinked or stalled. If that stops being true, something is invisible.
  return { cards, shipped, unlinked, stalled }
}
