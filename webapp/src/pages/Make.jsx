import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
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

/** Parse a YouTube Studio paste. Forgiving on purpose: any line with a title and
    at least one number counts; the first plain number is views, a % is CTR. */
function parsePaste(txt) {
  const lines = String(txt || '').split('\n').map((l) => l.trim()).filter(Boolean)
  const rows = []
  let ignored = 0
  for (const l of lines) {
    const nums = l.match(/[\d][\d,.]*%?/g) || []
    const title = l.split(/\s{2,}|\t/)[0].trim()
    if (!nums.length || !title || /^video\b/i.test(title)) { ignored += 1; continue }
    const pct = nums.find((n) => n.includes('%')) || null
    const plain = nums.filter((n) => !n.includes('%'))
    rows.push({ title, views: plain[0] ? plain[0].replace(/[^\d]/g, '') : null, ctr: pct })
  }
  return { rows, ignored }
}

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
                straight out of YouTube Studio — messy paste is fine.
              </p>
              <textarea
                className="make-paste"
                spellCheck={false}
                value={paste}
                onChange={(e) => setPaste(e.target.value)}
                placeholder={'I Built A Habit Tracker By Typing One…   1,204   18,900   6.1%   0:19\nI Built A Working App By Typing One L…      31      910   2.8%   0:11'}
              />
              {parsed && (
                <div className="make-parsed">
                  <span className="lb">READ BACK ✓</span>
                  <span className="chip ok-chip">{parsed.rows.length} video{parsed.rows.length === 1 ? '' : 's'} matched</span>
                  {parsed.ignored > 0 && <span className="chip">{parsed.ignored} line{parsed.ignored === 1 ? '' : 's'} ignored</span>}
                  <span className="chip">used before the app’s own data</span>
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
              <div className="dim small" style={{ marginTop: 9 }}>
                Pinning is per job. Which machine takes which <em>kind</em> of work is set on the
                machine itself — the Windows box currently accepts shell scripts only.
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
              paste.trim() ? `Your paste · ${parsed ? parsed.rows.length : 0} videos · freshest source` : null,
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
