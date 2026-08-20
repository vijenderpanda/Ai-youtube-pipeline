import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { countsFromAssets, resolveStage } from '../pipeline'

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
const istToday = () => new Date().toLocaleDateString('en-CA', { timeZone: IST })
const istTime = (iso) =>
  new Date(iso).toLocaleTimeString('en-GB', { timeZone: IST, hour: '2-digit', minute: '2-digit' })

export default function Today() {
  const stagedQ = usePoll(() => api.get('?r=staged'), 10000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const workersQ = usePoll(() => api.get('?r=workers'), 30000)
  const postsQ = usePoll(() => api.get('?r=posts&status=scheduled'), 30000)
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

  /* ── the triage stack ────────────────────────────────────────────────── */
  /* Today is what needs a human NOW, not every unfinished thing ever made. A cut
     that has sat unarmed for weeks is backlog: real, but not today's decision —
     and 23 cards is not a queue that can reach zero, which is the whole promise
     of this screen. So cuts are only surfaced while they are still live work
     (planned within the last week, or still ahead), and the stack is capped;
     the rest is counted honestly on one line instead of being hidden. */
  const RECENT_DAYS = 7
  const MAX_CARDS = 6
  const cards = useMemo(() => {
    const out = []
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - RECENT_DAYS)
    const cutoffStr = cutoff.toLocaleDateString('en-CA', { timeZone: IST })
    const isLiveWork = (it) => !it.planned_date || it.planned_date >= cutoffStr
    const liveJobFor = (id) =>
      jobs.find(
        (j) =>
          j.meta &&
          j.meta.calendar_id === id &&
          j.type === 'produce_preview' &&
          (j.status === 'queued' || j.status === 'running')
      )

    for (const it of items) {
      if (it.status === 'published' || it.status === 'skipped' || it.status === 'superseded') continue
      const counts = countsById[it.id] || countsFromAssets([])
      const producing = !!liveJobFor(it.id)
      const { stage } = resolveStage(it, counts, { producing })

      if (producing) continue // the factory is working — nothing for a human
      if ((stage === 'qc' || (stage === 'arm' && it.preview_path)) && isLiveWork(it)) {
        out.push({
          k: 'cut',
          rank: 0,
          when: it.planned_date || '',
          icon: '▶',
          title: `${it.title || '(untitled)'} — a cut is waiting`,
          sub: `${it.channel_key}${it.preview_path ? ' · ' + String(it.preview_path).split('/').pop() : ''}`,
          to: '/piece/' + it.id,
          verb: 'Review it',
        })
      } else if (counts.failed > 0) {
        out.push({
          k: 'fail',
          rank: -1,
          icon: '⚠',
          title: `${it.title || '(untitled)'} — ${counts.failed} part${counts.failed === 1 ? '' : 's'} failed`,
          sub: `${it.channel_key} · this has to be fixed before it ships`,
          to: '/piece/' + it.id,
          verb: 'Open it',
        })
      }
    }

    // Channels with nothing planned ahead — a FACT, not a nag. No proposal is
    // attached because nothing plans overnight; asking is one agent run.
    const today = istToday()
    for (const c of channels) {
      if (c.lifecycle === 'incubating' || c.status === 'paused') continue
      const ahead = items.filter(
        (it) =>
          it.channel_key === c.key &&
          it.planned_date &&
          it.planned_date >= today &&
          !['skipped', 'superseded', 'published'].includes(it.status)
      )
      if (ahead.length === 0) {
        out.push({
          k: 'empty',
          rank: 2,
          icon: '○',
          title: `${c.name || c.key} has nothing planned`,
          sub: 'Nothing is proposed — asking costs one agent run',
          to: '/make/' + c.key,
          verb: '✦ Make something',
        })
      }
    }
    // failures first, then newest live work, then the empty-slot facts
    return out.sort((a, b) => a.rank - b.rank || String(b.when || '').localeCompare(String(a.when || '')))
  }, [items, countsById, jobs, channels])

  /* Everything that is real work but not today's decision. Counted, never hidden. */
  const backlog = useMemo(() => {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - RECENT_DAYS)
    const cutoffStr = cutoff.toLocaleDateString('en-CA', { timeZone: IST })
    return items.filter(
      (it) =>
        it.preview_path &&
        it.planned_date &&
        it.planned_date < cutoffStr &&
        !['published', 'skipped', 'superseded', 'armed'].includes(it.status)
    ).length
  }, [items])

  const shown = cards.slice(0, MAX_CARDS)
  const overflow = cards.length - shown.length

  /* ── ships today ─────────────────────────────────────────────────────── */
  const shipsToday = useMemo(() => {
    const t = istToday()
    return posts
      .filter((p) => p.publish_at && new Date(p.publish_at).toLocaleDateString('en-CA', { timeZone: IST }) === t)
      .sort((a, b) => String(a.publish_at).localeCompare(String(b.publish_at)))
  }, [posts])

  /* ── one health row ──────────────────────────────────────────────────── */
  const health = useMemo(() => {
    const now = Date.now()
    const alive = workers.filter((w) => w.last_seen && now - new Date(w.last_seen).getTime() < 15 * 60 * 1000)
    const usage = workers.map((w) => (w.meta || {}).usage).filter(Boolean)
    const limited = usage.some((u) => u.rate_limited)
    const reset = usage.map((u) => u.reset_est).filter(Boolean).sort()[0]
    return {
      ok: alive.length === workers.length && workers.length > 0 && !limited,
      text:
        workers.length === 0
          ? 'No machines have checked in'
          : `${alive.length} of ${workers.length} machine${workers.length === 1 ? '' : 's'} awake` +
            (limited ? ' · AI budget spent' : '') +
            (reset ? ` · budget resets ${istTime(reset)}` : ''),
    }
  }, [workers])

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
            The factory keeps running without you. Next honest read: <b>tomorrow 07:33</b>, when the
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

      {(overflow > 0 || backlog > 0) && (
        <div className="today-backlog">
          {overflow > 0 && <>{overflow} more need{overflow === 1 ? 's' : ''} you. </>}
          {backlog > 0 && (
            <>
              {backlog} older cut{backlog === 1 ? '' : 's'} are still unfinished —{' '}
              <Link className="link" to="/studio">that's backlog, not today</Link>.
            </>
          )}
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
        <Link className="link" to="/workers" style={{ marginLeft: 'auto' }}>
          machines →
        </Link>
      </div>
    </div>
  )
}
