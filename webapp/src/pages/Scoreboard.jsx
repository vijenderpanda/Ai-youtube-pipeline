import { useMemo, useState } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import Toast, { useToast } from '../components/Toast'

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
  const total = Object.values(mix).reduce((s, n) => s + (Number(n) || 0), 0) || 1
  const shorts = (Number(mix.SHORTS) || 0) / total
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

  /* Pasted Studio rows outrank stored stats for the videos they name — the API
     lags ~48h and the newest Shorts have no rows at all. Matched on title. */
  const pasted = useMemo(() => {
    const map = new Map()
    for (const line of String(paste || '').split('\n')) {
      const nums = line.match(/[\d][\d,.]*%?/g) || []
      const title = line.split(/\s{2,}|\t/)[0].trim()
      if (!title || !nums.length || /^video\b/i.test(title)) continue
      const plain = nums.filter((n) => !n.includes('%'))
      if (!plain.length) continue
      map.set(title.replace(/[…\.]+$/, '').toLowerCase(), Number(plain[0].replace(/[^\d]/g, '')))
    }
    return map
  }, [paste])

  const freshViews = (v) => {
    const t = String(v.title || '').toLowerCase()
    for (const [k, views] of pasted) {
      if (k.length > 12 && (t.startsWith(k.slice(0, 24)) || k.startsWith(t.slice(0, 24)))) return views
    }
    return null
  }

  const cards = useMemo(() => {
    const now = Date.now()
    const viewsOf = (v) => freshViews(v) ?? (v.total_views || 0)
    const dist = videos.map(viewsOf).sort((a, b) => a - b)
    const p25 = pct(dist, 25)
    const p50 = pct(dist, 50)
    const p75 = pct(dist, 75)

    return videos
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

        return { v, views, age, clock, maturity, callable, verdict, traj, hold, looping, diagnosis, p25, p50, p75, fresh: freshViews(v) != null }
      })
      .sort((a, b) => {
        // "needs a decision" first: flops, then hits, then everything else newest-first
        const rank = (c) => (c.verdict === 'flop' ? 0 : c.verdict === 'hit' ? 1 : c.verdict === 'early' ? 2 : 3)
        return rank(a) - rank(b) || (a.age ?? 999) - (b.age ?? 999)
      })
  }, [videos, pasted, publishedAt]) // eslint-disable-line react-hooks/exhaustive-deps

  const dist = cards.length ? { p25: cards[0].p25, p50: cards[0].p50, p75: cards[0].p75 } : null

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
            The API finalizes ~48h late and the newest Shorts have no rows at all. Paste from
            YouTube Studio — matched by title, and used instead of the stored figure.
          </p>
          <textarea
            className="make-paste"
            spellCheck={false}
            value={paste}
            onChange={(e) => setPaste(e.target.value)}
            placeholder={'I Built A Habit Tracker By Typing One…   1,204   18,900   6.1%'}
          />
          {pasted.size > 0 && (() => {
            // Unlike Make, this page HAS the video list, so it can report what
            // actually matched rather than how many lines it parsed. A row whose
            // title matches nothing silently falls back to the stored number, so
            // saying it matched would hide exactly the case worth seeing.
            const hits = videos.filter((v) => freshViews(v) != null).length
            const missed = pasted.size - hits
            return (
              <div className="make-parsed">
                <span className="lb">READ BACK ✓</span>
                <span className={'chip ' + (hits ? 'ok-chip' : '')}>
                  {hits} of {pasted.size} row{pasted.size === 1 ? '' : 's'} matched a video
                </span>
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

      <div className="score-grid">
        {cards.map((c) => {
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

      <Toast toast={toast} />
    </div>
  )
}
