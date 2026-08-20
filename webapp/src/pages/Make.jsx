import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { parsePaste, freshViewsFor, namedWithoutNumber } from '../paste'
import Toast, { useToast } from '../components/Toast'

/* =============================================================================
   MAKE — the on-demand proposer. One run, when you ask, for one channel.

   There is deliberately NO overnight proposer: `claude -p` quota is per ACCOUNT
   (all three workers capped within 4s on 2026-08-18), so speculatively planning
   seven channels every night spends the day's quota on ideas nobody asked for.
   Asking at the moment you want to produce also means the reasoning argues from
   the NEWEST numbers rather than something written before yesterday's numbers
   landed.

   PASTE-FIRST: the app's own analytics finalize with a ~48h lag and a 1-3 day
   old Short has no API rows at all — but you can read the real figures in
   YouTube Studio right now. So the paste box sits ABOVE the button, is parsed
   forgivingly, and is READ BACK to you before anything argues from it.
   ========================================================================== */

const ANGLE_LABEL = {
  analytics: 'from your analytics',
  vaibhav: 'competitor DNA',
  news: 'news peg',
  event: 'upcoming event',
  wildcard: 'wildcard',
}

export default function Make() {
  const { channelKey } = useParams()
  const navigate = useNavigate()
  const { toast, show } = useToast()

  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const workersQ = usePoll(() => api.get('?r=workers'), 0)
  const channels = (chansQ.data && chansQ.data.channels) || []
  const workers = (workersQ.data && workersQ.data.workers) || []

  const [channel, setChannel] = useState(channelKey || '')
  const [paste, setPaste] = useState('')
  const [worker, setWorker] = useState('')      // '' = any free machine
  const [phase, setPhase] = useState('idle')     // idle | running | ideas
  const [ideas, setIdeas] = useState([])
  const [picked, setPicked] = useState(-1)
  const [busy, setBusy] = useState('')

  const ch = channels.find((c) => c.key === channel) || channels[0]
  const chKey = (ch && ch.key) || ''
  const parsed = useMemo(() => (paste.trim() ? parsePaste(paste) : null), [paste])

  /* Make can now MATCH, so its read-back can stop being vague. It used to hold
     no video list at all, which is why it could only honestly report "N rows
     read" — it had nothing to match against. The channel is already chosen
     right here, so its videos are one cheap call away, and a Studio link in the
     paste resolves to an exact video. */
  const vidsQ = usePoll(
    () => (chKey ? api.get(`?r=video_summary&channel=${encodeURIComponent(chKey)}&days=90`) : Promise.resolve(null)),
    0,
    [chKey]
  )
  /* Stats AND posts. Matching only against ?r=video_summary means matching only
     against the stats table — and the video with the freshest number is exactly
     the one the stats table cannot see yet, since analytics lag ~48h. So the
     paste that matters most reported as matching nothing. The posts carry
     video_id + title for everything that has shipped. */
  const postsQ = usePoll(() => api.get('?r=posts'), 0)
  const chanVideos = useMemo(() => {
    const out = (vidsQ.data && vidsQ.data.videos) || []
    const known = new Set(out.map((v) => v.video_id))
    const extra = ((postsQ.data && postsQ.data.posts) || [])
      .filter((p) => p.channel_key === chKey && p.video_id && !known.has(p.video_id))
      .map((p) => ({ video_id: p.video_id, title: p.yt_title || '' }))
    return [...out, ...extra]
  }, [vidsQ.data, postsQ.data, chKey])
  /* The library's answer to each planned beat, worked out HERE so the proposal
     is visible before anything is approved or spent. Same pickCookbook the
     sequence designer and auto_compose use — one ranker, not a second opinion. */
  const [picks, setPicks] = useState({})
  useEffect(() => {
    let dead = false
    const withBeats = ideas.filter((i) => Array.isArray(i.beats) && i.beats.length)
    if (!withBeats.length) { setPicks({}); return }
    import('@remotion-src/cookbook/registry').then(({ pickCookbook }) => {
      if (dead) return
      const out = {}
      ideas.forEach((idea, ix) => {
        if (!Array.isArray(idea.beats)) return
        out[ix] = idea.beats.map((b) => {
          const [top] = pickCookbook(
            { beat: b.beat, needs: b.needs, keywords: b.keywords || [] }, 1
          ) || []
          return top
            ? { id: top.entry.id, label: top.entry.title, score: top.score, why: top.why || [] }
            : null   // nothing scored — that is the build-a-component signal
        })
      })
      setPicks(out)
    }).catch(() => setPicks({}))
    return () => { dead = true }
  }, [ideas])

  const readBack = useMemo(() => {
    if (!parsed) return null
    const matched = chanVideos.filter((v) => freshViewsFor(parsed, v) != null).length
    const named = chanVideos.filter((v) => namedWithoutNumber(parsed, v)).length
    return { matched, named, unmatched: Math.max(0, parsed.size - matched - named), ...parsed }
  }, [parsed, chanVideos])

  /* Ask for ideas. Same job the channel page has always used — now carrying the
     paste and, optionally, a machine to run on. */
  const run = async () => {
    if (!chKey || busy) return
    setBusy('run'); setPhase('running'); setIdeas([]); setPicked(-1)
    try {
      const d = await api.post({
        action: 'plan_content',
        channel_key: chKey,
        fresh_numbers: paste.trim() || undefined,
        target_worker: worker || undefined,
      })
      const jobId = d.job && d.job.id
      if (!jobId) throw new Error('no job came back')
      // poll — planning takes a few minutes
      for (let i = 0; i < 150; i += 1) {
        await new Promise((r) => setTimeout(r, 4000))
        const j = (await api.get(`?r=job&id=${encodeURIComponent(jobId)}`)).job
        if (!j) continue
        if (j.status === 'failed') throw new Error(j.error || 'planning failed')
        if (j.status === 'done') {
          const list = Array.isArray(j.result && j.result.ideas) ? j.result.ideas : []
          if (!list.length) throw new Error('planning returned no ideas')
          setIdeas(list.sort((a, b) => (a.rank || 99) - (b.rank || 99)))
          setPhase('ideas')
          setBusy('')
          return
        }
      }
      throw new Error('planning timed out')
    } catch (e) {
      show(e.message, 'error')
      setPhase('idle')
      setBusy('')
    }
  }

  /* Turn the chosen idea into a Piece and go straight to its Plan gate. */
  const usePick = async () => {
    if (picked < 0 || busy) return
    const idea = ideas[picked]
    setBusy('create')
    try {
      const today = new Date()
      today.setDate(today.getDate() + 1)
      const planned = today.toISOString().slice(0, 10)
      const d = await api.post({
        action: 'create_calendar_item',
        channel_key: chKey,
        planned_date: planned,
        title: idea.title,
        brief: idea.brief || idea.why_viral || '',
        type: 'produce_short',
        model: 'opus',
        effort: 'high',
      })
      const id = d.item && d.item.id
      if (!id) throw new Error('the piece was not created')
      navigate('/piece/' + id)
    } catch (e) {
      show(e.message, 'error')
      setBusy('')
    }
  }

  return (
    <div className="piece make">
      <div className="piece-head">
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="crumb">Make</div>
          <h1 className="piece-title">What should we make next?</h1>
          <div className="piece-sub">
            One run, when you ask — nothing plans overnight.
          </div>
        </div>
      </div>

      {phase === 'idle' && (
        <>
          <div className="piece-cols">
            <section className="pc-card">
              <span className="pc-eyebrow">Numbers this app can’t see yet</span>
              <p style={{ margin: '0 0 9px', fontSize: 13, color: 'var(--text-2)' }}>
                Your newest Shorts have no API data, and the daily sync lags ~48h. Paste the rows
                straight out of YouTube Studio, or any write-up that links the videos — a Studio
                link carries the video&rsquo;s id, so it matches exactly rather than by title. Messy
                paste is fine.
              </p>
              <textarea
                className="make-paste"
                spellCheck={false}
                value={paste}
                onChange={(e) => setPaste(e.target.value)}
                placeholder={
                  'I Built A Habit Tracker By Typing One…   1,204   18,900   6.1%   0:19\n' +
                  'I Built A Working App By Typing One L…      31      910   2.8%   0:11\n\n' +
                  '…or prose: “[I Built A Habit Tracker](https://studio.youtube.com/video/Ag9tBHbyrbo/analytics) ' +
                  'is your top performer with 225 views.”'
                }
              />
              {parsed && readBack && (
                <div className="make-parsed">
                  <span className="lb">READ BACK ✓</span>
                  {/* This page now holds the channel's videos, so the read-back can
                      report what actually matched instead of how many lines it
                      parsed. Whatever matched nothing still goes to the planner —
                      the whole paste does — it just is not claimed as understood. */}
                  <span className={'chip ' + (readBack.matched ? 'ok-chip' : '')}>
                    {readBack.matched} video{readBack.matched === 1 ? '' : 's'} matched with a view count
                  </span>
                  {readBack.named > 0 && (
                    <span className="chip">{readBack.named} recognised by link, no view count in the text</span>
                  )}
                  {readBack.unmatched > 0 && (
                    <span className="chip warn-chip">{readBack.unmatched} named nothing on this channel</span>
                  )}
                  {parsed.ignored > 0 && <span className="chip">{parsed.ignored} line{parsed.ignored === 1 ? '' : 's'} ignored</span>}
                  <span className="chip">the whole paste goes to the planner either way</span>
                </div>
              )}
            </section>

            <section className="pc-card">
              <span className="pc-eyebrow">Where it runs</span>
              <div className="piece-kv">
                <span>Channel</span>
                <b>
                  <select value={chKey} onChange={(e) => setChannel(e.target.value)} className="make-select">
                    {channels.map((c) => (
                      <option key={c.key} value={c.key}>{c.name || c.key}</option>
                    ))}
                  </select>
                </b>
              </div>
              <div className="piece-kv">
                <span>Machine</span>
                <b>
                  <select value={worker} onChange={(e) => setWorker(e.target.value)} className="make-select">
                    <option value="">Any free machine</option>
                    {workers.map((w) => (
                      <option key={w.worker_id || w.name} value={w.worker_id || w.name} disabled={w.paused}>
                        {w.name}{w.gpu ? ' · GPU' : ''}{w.paused ? ' (paused)' : ''}
                      </option>
                    ))}
                  </select>
                </b>
              </div>
              {/* This used to assert "the Windows box currently accepts shell
                  scripts only" as a hardcoded string, while never reading
                  accept_types — so it kept claiming a configuration long after
                  it was changed on Machines. It is read now, or not claimed. */}
              <div className="dim small" style={{ marginTop: 9 }}>
                Pinning is per job. Which machine takes which <em>kind</em> of work is set on the
                machine itself.
                {(() => {
                  const limited = workers.filter((w) => Array.isArray(w.accept_types) && w.accept_types.length)
                  if (!limited.length) return ' Every machine here takes any job.'
                  return ' ' + limited.map((w) => `${w.name} takes only ${w.accept_types.length} kind${w.accept_types.length === 1 ? '' : 's'} of work`).join('; ') + '.'
                })()}
              </div>
            </section>
          </div>

          <div className="piece-foot">
            <button className="btn btn-primary" onClick={run} disabled={!chKey || !!busy}>
              ✦ Make something for {(ch && (ch.name || ch.key)) || '…'}
            </button>
            <span className="piece-why">
              One agent run. Nothing is planned or spent until you pick an idea.
            </span>
          </div>
        </>
      )}

      {phase === 'running' && (
        <section className="pc-card">
          <span className="pc-eyebrow">Reading before it says anything</span>
          <div className="make-reading">
            {[
              paste.trim()
                ? `Your paste · ${readBack ? readBack.matched : 0} matched · freshest source`
                : null,
              'This channel’s last shorts + their numbers',
              'What actually held retention (curriculum vs news)',
              'Competitor DNA + this week’s AI news',
              'The calendar, for anything timely',
            ].filter(Boolean).map((l) => (
              <div key={l} className="rl"><span className="sp" />{l}</div>
            ))}
          </div>
          <div className="dim small" style={{ marginTop: 11 }}>
            A few minutes. You can leave this page — the run keeps going.
          </div>
        </section>
      )}

      {phase === 'ideas' && (
        <>
          <span className="pc-eyebrow" style={{ marginBottom: 10 }}>
            {ideas.length} proposals · ranked by what your own numbers say
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
            {ideas.map((idea, i) => (
              <button
                key={i}
                type="button"
                className="make-idea"
                aria-selected={picked === i}
                onClick={() => setPicked(i)}
              >
                <span className="rk">{i === 0 ? 'BEST FIT' : 'OPTION ' + (i + 1)}</span>
                <div className="ttl">{idea.title}</div>
                {idea.hook && <div className="hk">“{idea.hook}”</div>}
                {idea.why_viral && (
                  <div className="why">
                    <span className="lb">WHY</span>
                    <span>{idea.why_viral}</span>
                  </div>
                )}
                {idea.angle && <span className="chip" style={{ marginTop: 8 }}>{ANGLE_LABEL[idea.angle] || idea.angle}</span>}

                {/* The shot list, and what the library would put on screen for each
                    beat — visible BEFORE the money gate, which is the whole point of
                    keeping a component library. A beat nothing scores for is not a
                    failure: it is the signal that this idea needs a component built. */}
                {Array.isArray(idea.beats) && idea.beats.length > 0 && (
                  <div className="mk-beats">
                    <span className="lb">THE CUT IT WOULD MAKE</span>
                    {idea.beats.map((b, bi) => {
                      const p = (picks[i] || [])[bi]
                      return (
                        <div key={bi} className="mk-beat">
                          <span className="bk">{b.beat}</span>
                          <span className="bs">{b.shows}</span>
                          {p ? (
                            <span className="bp" title={(p.why || []).join(' · ')}>{p.label}</span>
                          ) : (
                            <span className="bp none">needs a new component</span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </button>
            ))}
          </div>
          <div className="piece-foot">
            <button className="btn btn-primary" onClick={usePick} disabled={picked < 0 || !!busy}>
              {busy === 'create' ? 'Creating…' : 'Use this one →'}
            </button>
            <button className="btn btn-ghost" onClick={run} disabled={!!busy}>Propose again</button>
            <span className="piece-why">Picking creates the piece at its Plan gate. Still nothing spent.</span>
          </div>
        </>
      )}

      <Toast toast={toast} />
    </div>
  )
}
