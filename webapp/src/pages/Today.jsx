import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { buildTriage, MAX_CARDS, istToday } from '../triage'

/* =============================================================================
   TODAY — only what needs a human, and nothing else.

   The old Overview showed a queue plus vanity totals ("412 tasks finished") and
   could offer "Finalize & schedule" on a video that did not exist yet, because
   it resolved the stage WITHOUT the producing flag. This one:

     · shows one card per thing that actually needs a decision, in the order the
       decision matters, and CAN REACH ZERO — the empty state is the feature;
     · never invents work: an empty slot is a fact you can act on, not a nag,
       and it carries no pre-written proposal because nothing plans overnight;
     · collapses infrastructure into ONE muted row. Seven channels failing on a
       single expired token is one problem, not seven alerts.
   ========================================================================== */

const IST = 'Asia/Kolkata'
const istTime = (iso) =>
  new Date(iso).toLocaleTimeString('en-GB', { timeZone: IST, hour: '2-digit', minute: '2-digit' })

export default function Today() {
  const stagedQ = usePoll(() => api.get('?r=staged'), 10000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const workersQ = usePoll(() => api.get('?r=workers'), 30000)
  // ALL posts, not just scheduled: a post is the only proof a piece already
  // shipped, and a published one proves it just as well as a scheduled one.
  const postsQ = usePoll(() => api.get('?r=posts'), 30000)
  // ?r=staged cannot see status planned|suggested, so without the calendar the
  // page cannot tell whether a channel has upcoming work.
  const planQ = usePoll(() => api.get('?r=calendar'), 60000)
  // ?r=staged carries items + counts + covers but NOT jobs, and without the live
  // job we cannot tell "producing" from "ready to review" — which is precisely
  // how the old Overview came to offer "Finalize & schedule" on a video that did
  // not exist yet. Fetch the jobs and pass the liveness flag in.
  const jobsQ = usePoll(() => api.get('?r=jobs&limit=60'), 10000)

  const items = (stagedQ.data && stagedQ.data.items) || []
  const countsById = (stagedQ.data && stagedQ.data.counts) || {}
  const jobs = (jobsQ.data && jobsQ.data.jobs) || []
  const channels = (chansQ.data && chansQ.data.channels) || []
  const workers = (workersQ.data && workersQ.data.workers) || []
  const posts = (postsQ.data && postsQ.data.posts) || []
  const planned = (planQ.data && planQ.data.items) || []

  /* ── the triage stack ────────────────────────────────────────────────── */
  /* One selector, shared with the sidebar badge — see triage.js for why the two
     used to disagree and why a shipped piece never left this list before. */
  const { cards, shipped, unlinked, stalled } = useMemo(
    () => buildTriage({ items, countsById, jobs, posts, channels, planned }),
    [items, countsById, jobs, posts, channels, planned]
  )

  const shown = cards.slice(0, MAX_CARDS)
  const overflow = cards.length - shown.length

  /* ── ships today ─────────────────────────────────────────────────────── */
  const shipsToday = useMemo(() => {
    const t = istToday()
    const live = ['scheduled', 'armed', 'uploading', 'published']
    return posts
      .filter((p) => live.includes(String(p.status || '').toLowerCase()))
      .filter((p) => p.publish_at && new Date(p.publish_at).toLocaleDateString('en-CA', { timeZone: IST }) === t)
      .sort((a, b) => String(a.publish_at).localeCompare(String(b.publish_at)))
  }, [posts])

  /* ── one health row ──────────────────────────────────────────────────── */
  const health = useMemo(() => {
    const now = Date.now()
    const alive = workers.filter((w) => w.last_seen && now - new Date(w.last_seen).getTime() < 15 * 60 * 1000)
    const failedJobs = jobs.filter((j) => j.status === 'failed').length
    const usage = workers.map((w) => (w.meta || {}).usage).filter(Boolean)
    const limited = usage.some((u) => u.rate_limited)
    const reset = usage.map((u) => u.reset_est).filter(Boolean).sort()[0]
    return {
      ok: alive.length === workers.length && workers.length > 0 && !limited && failedJobs === 0,
      failedJobs,
      text:
        workers.length === 0
          ? 'No machines have checked in'
          : `${alive.length} of ${workers.length} machine${workers.length === 1 ? '' : 's'} awake` +
            (limited ? ' · AI budget spent' : '') +
            (reset ? ` · budget resets ${istTime(reset)}` : '') +
            (failedJobs
              ? ` · ${failedJobs} of the last ${jobs.length} background tasks failed`
              : ''),
    }
  }, [workers, jobs])

  const loading = stagedQ.loading && !stagedQ.data

  return (
    <div className="piece today">
      <div className="piece-head">
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="crumb">Today</div>
          <h1 className="piece-title">
            {loading
              ? 'Looking…'
              : cards.length === 0
                ? 'Nothing needs you.'
                : `${cards.length} thing${cards.length === 1 ? '' : 's'} need${cards.length === 1 ? 's' : ''} you.`}
          </h1>
          <div className="piece-sub">
            {shipsToday.length > 0
              ? `${shipsToday.length} ship${shipsToday.length === 1 ? 's' : ''} today · ${shipsToday
                  .map((p) => istTime(p.publish_at))
                  .join(', ')} IST`
              : 'Nothing ships today.'}
          </div>
        </div>
      </div>

      {!loading && cards.length === 0 && (
        <section className="pc-card today-empty">
          <div className="big">The queue is empty.</div>
          <p>
            The factory keeps running without you. The numbers refresh once a day, <b>around 07:00</b>, and only while this Mac is awake — when the
            overnight numbers land.
          </p>
        </section>
      )}

      <div className="today-stack">
        {shown.map((c, i) => (
          <Link key={c.k + i} to={c.to} className={'today-card' + (i === 0 ? ' focus' : '')}>
            <span className={'ic ' + c.k}>{c.icon}</span>
            <span style={{ minWidth: 0 }}>
              <span className="t">{c.title}</span>
              <span className="s">{c.sub}</span>
            </span>
            <span className="verb">{c.verb} →</span>
          </Link>
        ))}
      </div>

      {(overflow > 0 || unlinked > 0 || stalled > 0 || shipped > 0) && (
        <div className="today-backlog">
          {overflow > 0 && (
            <>
              {overflow} more need{overflow === 1 ? 's' : ''} you —{' '}
              <Link className="link" to="/plan">see them all</Link>.{' '}
            </>
          )}
          {unlinked > 0 && (
            <>
              {unlinked} older cut{unlinked === 1 ? '' : 's'} have no record of going out. They may well
              have shipped before the app started linking a post back to its piece — it cannot tell.{' '}
            </>
          )}
          {stalled > 0 && (
            <>
              {stalled} older piece{stalled === 1 ? '' : 's'} stalled before a cut was ever made —{' '}
              <Link className="link" to="/plan">in the plan</Link>.{' '}
            </>
          )}
          {shipped > 0 && <>{shipped} already shipped and left this list.</>}
        </div>
      )}

      {shipsToday.length > 0 && (
        <section className="pc-card" style={{ marginTop: 14 }}>
          <span className="pc-eyebrow">Ships today</span>
          {shipsToday.map((p) => (
            <div key={p.id} className="piece-kv">
              <span>{istTime(p.publish_at)} IST</span>
              <b>{p.yt_title || p.title || '(untitled)'}</b>
            </div>
          ))}
        </section>
      )}

      <div className={'today-health' + (health.ok ? '' : ' warn')}>
        <span className="dot" aria-hidden="true" />
        {health.text}
        {/* Both used to leave the six destinations (/jobs, /workers). Machines
            carries the failure breakdown and the machine state now. */}
        <Link className="link" to="/machines" style={{ marginLeft: 'auto' }}>
          {health.failedJobs ? 'see what failed →' : 'machines →'}
        </Link>
      </div>
    </div>
  )
}
