import { useMemo, useState } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import Toast, { useToast } from '../components/Toast'
import { fmtDayHeading } from '../format'
import { istToday } from '../triage'
import { parsePaste, freshViewsFor, namedWithoutNumber } from '../paste'

/* =============================================================================
   SCOREBOARD — hit, flop, or too early to tell.

   The rule this screen exists to enforce: THE VERDICT IS EARNED. A video is
   judged against its own channel's distribution, on a clock chosen by where its
   views actually came from, and the words "hit" and "flop" are UNRENDERABLE
   before that clock allows them — the too-early state is a finished screen that
   offers no actions, not a greyed-out one.

   Why it is built this way, from this network's own numbers:
     · Age counts from PUBLIC-SINCE (first day the video appears in stats), not
       publish_at — many videos sat private or unlisted first, which would make
       them look like week-two miracles.
     · The clock follows the traffic mix: a Shorts-fed video is settled in about
       a week; a search/suggested video keeps accruing for months (one long-form
       here went 7 → 198 views over 17 days, its biggest day the most recent).
     · A flop must say WHICH flop. Retention is unavailable on low-view videos
       (14 of 24 here have no hold_15s at all), so "the feed never showed it" is
       the common case and gets the plain reading; "they left at Xs" is only
       claimed when the data exists.
     · Verdicts only ever UPGRADE. A late resurgence turns a flop into a
       sleeper; nothing ever turns a hit back into a flop.
   ========================================================================== */

const pct = (sorted, p) => {
  if (!sorted.length) return 0
  const i = Math.min(sorted.length - 1, Math.max(0, Math.round((p / 100) * (sorted.length - 1))))
  return sorted[i]
}
const daysBetween = (a, b) => Math.max(0, Math.round((b - a) / 86400000))

/** Shorts settle in about a week; search/suggested keeps earning for months.

    The mix only means something once there IS traffic: a video with 4 views has
    no meaningful "traffic mix", and reading one put every dud on a 90-day clock
    where it could not be called for a month — burying the flops this screen
    exists to surface. Below that floor we fall back to what the channel actually
    publishes, which for a Shorts channel is the 7-day clock. */
const MIX_FLOOR = 20
function clockFor(v, views) {
  const SHORTS = { days: 7, name: 'Shorts', callableAt: 3 }
  const SLOW = { days: 90, name: 'Search & suggested', callableAt: 30 }
  if ((views || 0) < MIX_FLOOR) return SHORTS
  const mix = v.traffic_mix || {}
  const total = Object.values(mix).reduce((s, n) => s + (Number(n) || 0), 0)
  // No mix data at all is not evidence of search traffic. Without this, a video
  // with views but no stats row -- which is exactly what a pasted number gives
  // you -- computed shorts=0/1 and got the 90-day search clock, so a day-old
  // Short read as "day 1 of 90". Absence of evidence is not evidence; fall back
  // to the channel's format clock, the same rule MIX_FLOOR applies below.
  if (v.shorts_pct == null && total === 0) return SHORTS
  const shorts = total ? (Number(mix.SHORTS) || 0) / total : 0
  const shortsPct = v.shorts_pct != null ? Number(v.shorts_pct) / 100 : shorts
  return shortsPct >= 0.5 ? SHORTS : SLOW
}

function trajectory(trend) {
  const t = (trend || []).filter((n) => typeof n === 'number')
  if (t.length < 3) return null
  const last = t.slice(-3)
  const rising = last[2] > last[1] && last[1] >= last[0]
  const falling = last[2] < last[1] && last[1] <= last[0]
  return rising ? 'climbing' : falling ? 'settling' : 'flat'
}

export default function Scoreboard() {
  const { toast, show } = useToast()
  const [channel, setChannel] = useState('claude-tricks')
  const [paste, setPaste] = useState('')
  const [pasteOpen, setPasteOpen] = useState(false)

  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const vidsQ = usePoll(
    () => api.get(`?r=video_summary&channel=${encodeURIComponent(channel)}&days=90`),
    60000,
    [channel]
  )
  // first_date is the first day a video appears in STATS, which for anything
  // backfilled is when tracking started, not when it went public — that made
  // three-week-old videos with 2 views read as "too early to tell". The post
  // carries the real publish time, so age uses whichever is earlier.
  const postsQ = usePoll(() => api.get('?r=posts&limit=200'), 0)
  const channels = (chansQ.data && chansQ.data.channels) || []
  const chanName = (channels.find((c) => c.key === channel) || {}).name || channel
  const videos = (vidsQ.data && vidsQ.data.videos) || []
  const publishedAt = useMemo(() => {
    const m = new Map()
    for (const p of (postsQ.data && postsQ.data.posts) || []) {
      if (p.video_id && p.publish_at) m.set(p.video_id, new Date(p.publish_at).getTime())
    }
    return m
  }, [postsQ.data])

  /* Pasted numbers outrank stored stats for the videos they name — the API
     finalizes ~48h late and the newest Shorts have no rows at all. The parser
     is shared with Make (src/paste.js) so the same paste reads the same way on
     both screens; they used to have separate ones and drifted. */
  const pasted = useMemo(() => parsePaste(paste), [paste])
  const freshViews = (v) => freshViewsFor(pasted, v)
  const namedNoNumber = (v) => namedWithoutNumber(pasted, v)

  /* Videos that are LIVE but have no analytics row yet.
     The board is built from ?r=video_summary, which reads the stats table, and
     YouTube's analytics run about two days behind — so the two most recent
     Shorts simply vanished from the page. Absence reads as "it never went out",
     which is worse than "too early to tell", and it hides exactly the work you
     most want to look at. The posts prove they are public, so they appear with
     no numbers rather than not at all. */
  const livePosts = useMemo(() => {
    const known = new Set(videos.map((v) => v.video_id))
    const now = Date.now()
    return ((postsQ.data && postsQ.data.posts) || [])
      .filter((p) => p.channel_key === channel && p.video_id && !known.has(p.video_id))
      .filter((p) => ['published', 'armed', 'scheduled', 'uploading'].includes(String(p.status || '').toLowerCase()))
      .filter((p) => p.publish_at && new Date(p.publish_at).getTime() <= now)
      .map((p) => ({
        pending: true,
        v: { video_id: p.video_id, title: p.yt_title || '(untitled)' },
        publish_at: p.publish_at,
        day: new Date(p.publish_at).toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' }),
        age: daysBetween(new Date(p.publish_at).getTime(), now),
      }))
  }, [videos, postsQ.data, channel])

  /* A live video the stats table has not reached yet, but which the paste DID
     give a number for, is not "too early" any more — it has a real figure from
     a real source. It joins the measured set and gets judged like the rest,
     which is the entire point of pasting. The ones still without a number stay
     as pending cards. */
  const promoted = useMemo(
    () => livePosts
      .filter((p) => freshViews(p.v) != null)
      .map((p) => ({
        video_id: p.v.video_id,
        title: p.v.title,
        first_date: String(p.publish_at).slice(0, 10),
        total_views: freshViews(p.v),
      })),
    [livePosts, pasted] // eslint-disable-line react-hooks/exhaustive-deps
  )
  const pending = useMemo(
    () => livePosts.filter((p) => freshViews(p.v) == null),
    [livePosts, pasted] // eslint-disable-line react-hooks/exhaustive-deps
  )
  const measured = useMemo(() => [...videos, ...promoted], [videos, promoted])

  const cards = useMemo(() => {
    const now = Date.now()
    const viewsOf = (v) => freshViews(v) ?? (v.total_views || 0)
    const dist = measured.map(viewsOf).sort((a, b) => a - b)
    const p25 = pct(dist, 25)
    const p50 = pct(dist, 50)
    const p75 = pct(dist, 75)

    return measured
      .map((v) => {
        const views = viewsOf(v)
        // public-since = the earliest evidence it was live: its publish time, or
        // the first day stats saw it, whichever came first.
        const statFirst = v.first_date ? new Date(v.first_date + 'T00:00:00Z').getTime() : null
        const pub = publishedAt.get(v.video_id) || null
        const first = pub && statFirst ? Math.min(pub, statFirst) : (pub || statFirst)
        const age = first ? daysBetween(first, now) : null
        const clock = clockFor(v, views)
        const maturity = age == null ? 0 : Math.min(1, age / clock.days)
        const callable = age != null && age >= clock.callableAt
        const traj = trajectory(v.trend)

        let verdict = 'early'
        if (callable) {
          if (views >= p75 && p75 > 0) verdict = 'hit'
          else if (views <= p25) verdict = 'flop'
          else verdict = 'normal'
          // Verdicts only upgrade: something still climbing is never called a flop.
          if (verdict === 'flop' && traj === 'climbing') verdict = 'normal'
        }

        const hold = v.hold_15s != null ? Number(v.hold_15s) : null
        const looping = v.avg_view_pct != null && Number(v.avg_view_pct) > 100
        const diagnosis =
          verdict !== 'flop'
            ? null
            : hold == null
              ? 'the feed never showed it — not enough views to even measure retention'
              : `the feed showed it and they left early (15s hold ${Math.round(hold)}%)`

        const day = first ? new Date(first).toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' }) : ''
        return { v, views, age, day, clock, maturity, callable, verdict, traj, hold, looping, diagnosis, p25, p50, p75, fresh: freshViews(v) != null }
      })
      // Newest first, by the day it went public. The board used to lead with
      // every flop regardless of age, which is a ranking you cannot relate to
      // what you actually shipped this week — and the verdicts are already
      // colour-coded, so severity does not need the running order too.
      .sort((a, b) => String(b.day || '').localeCompare(String(a.day || '')) || (a.age ?? 999) - (b.age ?? 999))
  }, [measured, pasted, publishedAt]) // eslint-disable-line react-hooks/exhaustive-deps

  const dist = cards.length ? { p25: cards[0].p25, p50: cards[0].p50, p75: cards[0].p75 } : null
  const byDay = useMemo(() => {
    const m = new Map()
    const all = [...pending, ...cards].sort(
      (a, b) => String(b.day || '').localeCompare(String(a.day || '')) || (a.age ?? 999) - (b.age ?? 999)
    )
    for (const c of all) {
      const k = c.day || 'unknown'
      if (!m.has(k)) m.set(k, [])
      m.get(k).push(c)
    }
    return [...m.entries()]
  }, [cards, pending])

  return (
    <div className="piece scoreboard">
      <div className="piece-head">
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="crumb">Scoreboard</div>
          <h1 className="piece-title">Did it work — yet?</h1>
          {/* p25/median/p75 is statistician vocabulary on the one screen read for
              a verdict, where everything else says "Too early" and "the feed never
              showed it". Same numbers, said the way the rest of the page talks —
              and carrying the unit and the window, which they never did. */}
          <div className="piece-sub">
            {dist
              ? `${chanName} · typical video here gets ${dist.p50} views · the top quarter starts at ${dist.p75}`
              : chanName}
          </div>
        </div>
        <div className="piece-chips">
          <select className="make-select" value={channel} onChange={(e) => setChannel(e.target.value)}>
            {channels.map((c) => (
              <option key={c.key} value={c.key}>{c.name || c.key}</option>
            ))}
          </select>
          <button className="btn btn-ghost" onClick={() => setPasteOpen((v) => !v)}>
            {pasteOpen ? 'Hide paste' : '✦ Paste fresh numbers'}
          </button>
        </div>
      </div>

      {pasteOpen && (
        <section className="pc-card" style={{ marginBottom: 14 }}>
          <span className="pc-eyebrow">Numbers this app can’t see yet</span>
          <p style={{ margin: '0 0 9px', fontSize: 13, color: 'var(--text-2)' }}>
            The API finalizes ~48h late and the newest Shorts have no rows at all. Paste the
            Studio table, or any write-up that links the videos — a Studio link carries the
            video&rsquo;s id, which matches exactly instead of by title. Whatever matches is used
            instead of the stored figure.
          </p>
          <textarea
            className="make-paste"
            spellCheck={false}
            value={paste}
            onChange={(e) => setPaste(e.target.value)}
            placeholder={
              'I Built A Habit Tracker By Typing One…   1,204   18,900   6.1%\n\n' +
              '…or prose: “[I Built A Habit Tracker](https://studio.youtube.com/video/Ag9tBHbyrbo/analytics) ' +
              'is your top performer with 225 views.”'
            }
          />
          {pasted.size > 0 && (() => {
            // Unlike Make, this page HAS the video list, so it can report what
            // actually matched rather than how many lines it parsed. A row whose
            // title matches nothing silently falls back to the stored number, so
            // saying it matched would hide exactly the case worth seeing.
            // dedupe: a promoted video appears in BOTH measured and livePosts,
            // so counting the concatenation reported it twice.
            const seen = new Set()
            const all = [...measured, ...livePosts.map((p) => p.v)].filter((v) => {
              if (!v.video_id || seen.has(v.video_id)) return false
              seen.add(v.video_id); return true
            })
            const hits = all.filter((v) => freshViews(v) != null).length
            // A link the app recognised but that carried no view count. Worth
            // its own line: the video WAS found, the paste just did not say how
            // many views — "matched nothing" would be the wrong story.
            const named = all.filter((v) => namedNoNumber(v)).length
            const missed = Math.max(0, pasted.size - hits - named)
            return (
              <div className="make-parsed">
                <span className="lb">READ BACK ✓</span>
                <span className={'chip ' + (hits ? 'ok-chip' : '')}>
                  {hits} video{hits === 1 ? '' : 's'} got a fresh view count
                </span>
                {named > 0 && (
                  <span className="chip">
                    {named} recognised by link, but no view count in the text
                  </span>
                )}
                {missed > 0 && (
                  <span className="chip warn-chip">
                    {missed} matched nothing — those keep the stored numbers
                  </span>
                )}
                {hits > 0 && <span className="chip">used instead of the stored numbers</span>}
              </div>
            )
          })()}
        </section>
      )}

      {vidsQ.loading && !vidsQ.data && <p className="dim">Loading…</p>}

      {byDay.map(([day, group]) => (
        <div key={day} className="score-day">
          <div className="pd-head">
            {day === 'unknown' ? 'No publish date on record' : fmtDayHeading(day)}
            {day === istToday() && <span className="pd-today">today</span>}
          </div>
          <div className="score-grid">
        {group.map((c) => {
          // Live, but YouTube has not reported a single number for it yet. It
          // gets a card so it is not missing, and states exactly that — no
          // verdict, no bar, no percentile it could not have been measured against.
          if (c.pending) {
            return (
              <article key={c.v.video_id} className="score early pending">
                <div className="st">{c.v.title}</div>
                <div className="sm">live · day {c.age} — no numbers yet</div>
                <div className="vrow">
                  <svg width="46" height="46" viewBox="0 0 46 46" aria-hidden="true">
                    <circle cx="23" cy="23" r="19" fill="none" stroke="var(--border)" strokeWidth="5" />
                  </svg>
                  <div>
                    <div className="word">Too early</div>
                    <div className="sub">nothing measured yet</div>
                  </div>
                </div>
                <div className="nx">
                  It is out, but YouTube&rsquo;s numbers run about two days behind, so there is
                  nothing to judge it on. Paste fresher numbers above if you want them sooner.
                </div>
              </article>
            )
          }
          const dotPos =
            c.p75 > 0 ? Math.max(2, Math.min(98, (c.views / Math.max(c.p75 * 1.3, 1)) * 100)) : 2
          return (
            <article key={c.v.video_id} className={'score ' + c.verdict}>
              <div className="st">{c.v.title || '(untitled)'}</div>
              <div className="sm">
                {c.clock.name} clock · day {c.age ?? '?'} of {c.clock.days}
                {c.fresh && <span className="fresh"> · pasted</span>}
              </div>

              <div className="vrow">
                <svg width="46" height="46" viewBox="0 0 46 46" aria-hidden="true">
                  <circle cx="23" cy="23" r="19" fill="none" stroke="var(--border)" strokeWidth="5" />
                  <circle
                    cx="23" cy="23" r="19" fill="none" strokeWidth="5" strokeLinecap="round"
                    stroke="currentColor"
                    strokeDasharray={2 * Math.PI * 19}
                    strokeDashoffset={2 * Math.PI * 19 * (1 - c.maturity)}
                    transform="rotate(-90 23 23)"
                  />
                </svg>
                <div>
                  <div className="word">
                    {c.verdict === 'early' ? 'Too early' : c.verdict === 'hit' ? 'Hit' : c.verdict === 'flop' ? 'Flop' : 'Normal'}
                  </div>
                  <div className="sub">
                    {c.verdict === 'early'
                      ? `we've seen ${Math.round(c.maturity * 100)}% of its life`
                      : `${c.views} views${c.age != null && c.age > 90 ? ' in the last 90 days' : ''}${c.traj ? ' · ' + c.traj : ''}`}
                  </div>
                </div>
              </div>

              <div className="dist">
                <div className="bar">
                  <span className="me" style={{ left: dotPos + '%' }} />
                </div>
                <div className="sc">
                  <span><i>bottom quarter</i><b>{c.p25}</b></span>
                  <span><i>typical</i><b>{c.p50}</b></span>
                  <span><i>top quarter</i><b>{c.p75}</b></span>
                </div>
                <div className="scu">views, among this channel's own videos</div>
              </div>

              <div className="nx">
                {c.verdict === 'early' ? (
                  <>The numbers refresh once a day, <b>around 07:00</b>, and only while this Mac is awake. Paste fresher ones above if you have them.</>
                ) : c.verdict === 'flop' ? (
                  <>{c.diagnosis}</>
                ) : c.verdict === 'hit' ? (
                  <>More views than three out of four videos on this channel{c.traj === 'climbing' ? ', and still climbing' : ''} — the angle repeats.</>
                ) : (
                  <>Inside the normal band for this channel.</>
                )}
                {c.looping && <div className="loop">avg view &gt;100% — that’s looping, not retention.</div>}
                {c.hold == null && c.verdict !== 'early' && (
                  <div className="loop">Retention locked — too few views to measure.</div>
                )}
              </div>
            </article>
          )
        })}
          </div>
        </div>
      ))}

      <Toast toast={toast} />
    </div>
  )
}
