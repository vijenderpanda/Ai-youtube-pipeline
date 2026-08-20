import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { lifecycleOf } from '../lifecycle'
import { fmtDayHeading, toISODate } from '../format'
import Toast, { useToast } from '../components/Toast'

/* =============================================================================
   PLAN — "What is going out, and when?"

   Replaces the month-grid calendar. The rebuild exists because that page was the
   last old surface inside the frozen nav, but it could not simply be deleted:
   it held one signal that lives nowhere else in the app. `?r=staged` — which
   Today and the old board read — is restricted to status queued|produced, so a
   piece created in Make and not produced immediately is invisible on every
   other screen. An index of committed-but-unproduced work is the thing this
   page owes the rest of the app.

   Why this is a line-up and not a grid: of 144 calendar rows in the window,
   21 are committed and only 5 sit today-or-later. A month grid spends the whole
   screen drawing empty squares around five pieces. The honest shape of "what is
   going out" is a short list with the gap at the end of it — a cadence hole is
   the most actionable thing this page can tell you, and a grid hides it among
   the blanks.

   The 118 AI suggestions are NOT "going out" and never lead. They sit folded
   per channel, opened on purpose. Dumping them is how the old app got cluttered.

   RETIRED HERE (owner decision, 2026-08-20): the AI challenger loop — rows that
   proposed replacing an already-planned piece, shown as a decision within 72h of
   publish. Retired at the source too: the strategist prompt no longer asks for a
   challenge pass and the worker refuses a stray one, so nothing keeps writing
   rows that nothing renders. The 25 that were live were resolved as "keep the
   original". replaces_id rows are filtered out below in case any survive.
   ========================================================================== */

const COMMITTED = ['planned', 'queued', 'produced']

/** What a piece in the line-up is actually waiting for, in the gate rail's words. */
function stateOf(item, post) {
  const lc = lifecycleOf(item, post)
  if (lc === 'published') return { k: 'live', label: 'Live', tone: 'ok' }
  if (lc === 'armed') return { k: 'armed', label: 'Scheduled on YouTube', tone: 'ok' }
  if (lc === 'produced') return { k: 'produced', label: 'Cut ready — needs your eyes', tone: 'warn' }
  if (lc === 'queued') return { k: 'queued', label: 'Producing', tone: 'info' }
  return { k: 'planned', label: 'Not started', tone: 'dim' }
}

const dayKey = (item, post) => {
  if (post && post.publish_at) {
    const d = new Date(post.publish_at)
    if (!isNaN(d.getTime())) return toISODate(d)
  }
  return String(item.planned_date || '').slice(0, 10)
}

export default function Plan() {
  const { toast, show } = useToast()
  const [busy, setBusy] = useState('')
  const [openChannel, setOpenChannel] = useState(null)
  const [showShipped, setShowShipped] = useState(false)
  const [creating, setCreating] = useState(false)

  const calQ = usePoll(() => api.get('?r=calendar'), 20000)
  const postsQ = usePoll(() => api.get('?r=posts'), 60000)
  const chanQ = usePoll(() => api.get('?r=channels'), 300000)

  const items = (calQ.data && calQ.data.items) || []
  const posts = (postsQ.data && postsQ.data.posts) || []
  const channels = (chanQ.data && (chanQ.data.channels || chanQ.data.items)) || []

  const nameOf = useMemo(() => {
    const m = {}
    channels.forEach((c) => { m[c.key] = c.name || c.key })
    return (k) => m[k] || k
  }, [channels])

  const postFor = useMemo(() => {
    const byCal = {}
    posts.forEach((p) => { if (p.calendar_id) byCal[p.calendar_id] = p })
    return (it) => byCal[it.id] || null
  }, [posts])

  const today = toISODate(new Date())

  const { lineup, shipped, ideas, factory, nextGap } = useMemo(() => {
    // A challenger never renders as its own piece. The loop is retired, but a
    // historical row must not suddenly appear as a standalone idea.
    const live = items.filter((it) => !it.replaces_id)

    const committed = live
      .filter((it) => COMMITTED.includes(it.status) && it.kind !== 'factory')
      .map((it) => ({ it, post: postFor(it), day: dayKey(it, postFor(it)) }))

    const lineup = committed.filter((r) => r.day >= today).sort((a, b) => a.day.localeCompare(b.day))
    const shipped = committed.filter((r) => r.day < today).sort((a, b) => b.day.localeCompare(a.day))

    const byChannel = {}
    live
      .filter((it) => it.status === 'suggested' && it.kind !== 'factory')
      .forEach((it) => { (byChannel[it.channel_key] ||= []).push(it) })
    const ideas = Object.entries(byChannel)
      .map(([key, list]) => ({ key, list: list.sort((a, b) => String(a.planned_date).localeCompare(String(b.planned_date))) }))
      .sort((a, b) => b.list.length - a.list.length)

    const factory = live.filter((it) => it.kind === 'factory' && it.status !== 'skipped')

    // The gap is the point of the page: the first day after the last committed
    // piece. Saying "nothing after Sat 23" beats drawing 8 empty squares.
    const lastDay = lineup.length ? lineup[lineup.length - 1].day : null
    return { lineup, shipped, ideas, factory, nextGap: lastDay }
  }, [items, postFor, today])

  const days = useMemo(() => {
    const m = new Map()
    lineup.forEach((r) => { if (!m.has(r.day)) m.set(r.day, []); m.get(r.day).push(r) })
    return [...m.entries()]
  }, [lineup])

  const post = async (body, tag, okMsg) => {
    setBusy(tag)
    try {
      const r = await api.post(body)
      if (r && r.error) show(r.error, 'err')
      else { show(okMsg); calQ.refresh() }
    } catch (e) {
      show(String((e && e.message) || e), 'err')
    } finally { setBusy('') }
  }

  const patch = (id, p, tag, msg) => post({ action: 'update_calendar_item', id, patch: p }, tag, msg)

  if (calQ.error) return <div className="piece plan"><div className="dim">Could not load the plan: {String(calQ.error.message || calQ.error)}</div></div>
  if (!calQ.data) return <div className="piece plan"><div className="dim">Loading…</div></div>

  const ideaCount = ideas.reduce((n, g) => n + g.list.length, 0)

  return (
    <div className="piece plan">
      <Toast toast={toast} />

      <div className="piece-head">
        <div style={{ flex: 1, minWidth: 260 }}>
          <div className="pc-eyebrow" style={{ margin: 0 }}>Plan</div>
          <h1 className="plan-h1">What’s going out, and when</h1>
          <div className="piece-sub">
            {lineup.length} piece{lineup.length === 1 ? '' : 's'} {lineup.length === 1 ? 'has' : 'have'} a slot
            {nextGap ? ` · nothing after ${fmtDayHeading(nextGap)}` : ' · nothing is planned'}
          </div>
        </div>
        {/* One primary per screen: while the form is open the primary is its
            own submit, so this demotes itself to a plain Close. */}
        <button className={'btn ' + (creating ? 'btn-ghost' : 'btn-primary')} onClick={() => setCreating((v) => !v)}>
          {creating ? 'Close' : 'Plan something →'}
        </button>
      </div>

      {creating && (
        <PlanSomething
          channels={channels}
          busy={busy}
          onCancel={() => setCreating(false)}
          onCreate={async (body) => {
            await post({ action: 'create_calendar_item', ...body }, 'create', 'Planned')
            setCreating(false)
          }}
        />
      )}

      {/* ── the line-up ─────────────────────────────────────────────────── */}
      <section className="pc-card">
        <div className="pc-eyebrow">The line-up</div>
        {!days.length && (
          <div className="dim small">
            Nothing has a slot from today onward. Plan something, or open a channel’s
            ideas below and give one a day.
          </div>
        )}
        {days.map(([day, rows]) => (
          <div key={day} className="plan-day">
            <div className="pd-head">
              {fmtDayHeading(day)}
              {day === today && <span className="pd-today">today</span>}
            </div>
            {rows.map(({ it, post: p }) => {
              const st = stateOf(it, p)
              return (
                <div key={it.id} className="plan-row">
                  <div className="pr-main">
                    <Link className="pr-title" to={`/piece/${it.id}`}>{it.title}</Link>
                    <div className="pr-sub">
                      {nameOf(it.channel_key)}
                      {it.format === 'longform' ? ' · long-form' : ''}
                      {p && p.publish_at ? ` · ${new Date(p.publish_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })} IST` : ''}
                    </div>
                  </div>
                  <span className={'pr-state ' + st.tone}>{st.label}</span>
                  <div className="pr-acts">
                    {/* planned_date is the only thing the outro's "Tomorrow:" tease
                        reads, so moving a day has to be possible from here — it was
                        only ever editable in the old calendar drawer. */}
                    <input
                      type="date"
                      className="pr-date"
                      value={it.planned_date ? String(it.planned_date).slice(0, 10) : ''}
                      disabled={!!busy || st.k === 'armed' || st.k === 'live'}
                      title={st.k === 'armed' || st.k === 'live' ? 'YouTube has the schedule now' : 'Move it to another day'}
                      onChange={(e) => patch(it.id, { planned_date: e.target.value }, 'd:' + it.id, 'Moved')}
                    />
                    {st.k === 'planned' && (
                      <button
                        className="btn btn-ghost btn-sm"
                        disabled={!!busy}
                        onClick={() => patch(it.id, { status: 'skipped' }, 's:' + it.id, 'Parked')}
                      >
                        Park
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        ))}
        {nextGap && (
          <div className="plan-gap">
            Nothing is planned after <b>{fmtDayHeading(nextGap)}</b>.
          </div>
        )}
      </section>

      {/* ── ideas ───────────────────────────────────────────────────────── */}
      <section className="pc-card">
        <div className="pc-eyebrow">
          Ideas waiting <span className="soft">· {ideaCount} across {ideas.length} channel{ideas.length === 1 ? '' : 's'}</span>
        </div>
        <div className="dim small" style={{ marginBottom: 10 }}>
          Written by the strategist. None of these is going out — giving one a day is what commits it.
        </div>
        {!ideas.length && <div className="dim small">No ideas waiting.</div>}
        {ideas.map((g) => (
          <div key={g.key} className="plan-chan">
            <button
              className="pc-row"
              onClick={() => setOpenChannel(openChannel === g.key ? null : g.key)}
            >
              <span className="pc-name">{nameOf(g.key)}</span>
              <span className="pc-n">{g.list.length}</span>
              <span className="pc-caret">{openChannel === g.key ? '▾' : '▸'}</span>
            </button>
            {openChannel === g.key && (
              <div className="plan-ideas">
                {g.list.map((it) => (
                  <div key={it.id} className="plan-idea">
                    <div style={{ minWidth: 0 }}>
                      <div className="pi-title">{it.title}</div>
                      {it.suggestion_reason && <div className="pi-why">{it.suggestion_reason}</div>}
                    </div>
                    <div className="pi-acts">
                      <button
                        className="btn btn-ghost btn-sm"
                        disabled={!!busy}
                        title="Give it today’s slot — it moves into the line-up"
                        onClick={() => patch(it.id, { status: 'planned', planned_date: today }, 'p:' + it.id, 'Moved into the line-up')}
                      >
                        Give it a day
                      </button>
                      <button
                        className="btn btn-ghost btn-sm"
                        disabled={!!busy}
                        onClick={() => patch(it.id, { status: 'skipped' }, 'x:' + it.id, 'Parked')}
                      >
                        Not this
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </section>

      {/* ── the factory's own backlog ───────────────────────────────────── */}
      {!!factory.length && (
        <section className="pc-card">
          <div className="pc-eyebrow">What the strategist thinks the factory needs</div>
          {factory.map((it) => (
            <div key={it.id} className="plan-idea">
              <div style={{ minWidth: 0 }}>
                <div className="pi-title">{it.title}</div>
                {it.suggestion_reason && <div className="pi-why">{it.suggestion_reason}</div>}
              </div>
              <button
                className="btn btn-ghost btn-sm"
                disabled={!!busy}
                onClick={() => patch(it.id, { status: 'skipped' }, 'f:' + it.id, 'Parked')}
              >
                Not this
              </button>
            </div>
          ))}
        </section>
      )}

      {/* ── what already went ───────────────────────────────────────────── */}
      <section className="pc-card">
        <button className="plan-more" onClick={() => setShowShipped((v) => !v)}>
          {showShipped ? '▾' : '▸'} {shipped.length} piece{shipped.length === 1 ? '' : 's'} in the last week
        </button>
        {showShipped && (
          <div style={{ marginTop: 10 }}>
            {shipped.map(({ it, post: p }) => {
              const st = stateOf(it, p)
              return (
                <div key={it.id} className="plan-row past">
                  <div className="pr-main">
                    <Link className="pr-title" to={`/piece/${it.id}`}>{it.title}</Link>
                    <div className="pr-sub">{fmtDayHeading(dayKey(it, p))} · {nameOf(it.channel_key)}</div>
                  </div>
                  <span className={'pr-state ' + st.tone}>{st.label}</span>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}

/* ── plan something ────────────────────────────────────────────────────────
   The old Plan Content modal carried nine fields. This asks for the four that
   decide what gets made; model/effort/type keep their defaults, which is what
   they had in practice anyway. */
function PlanSomething({ channels, busy, onCreate, onCancel }) {
  const [channel, setChannel] = useState(channels[0] ? channels[0].key : '')
  const [when, setWhen] = useState(toISODate(new Date()))
  const [title, setTitle] = useState('')
  const [brief, setBrief] = useState('')
  const [format, setFormat] = useState('short')
  const ready = channel && when && title.trim()

  return (
    <section className="pc-card plan-new">
      <div className="pc-eyebrow">Plan something</div>
      <div className="pn-grid">
        <label className="pn-f">
          <span>Channel</span>
          <select value={channel} onChange={(e) => setChannel(e.target.value)}>
            {channels.map((c) => <option key={c.key} value={c.key}>{c.name || c.key}</option>)}
          </select>
        </label>
        <label className="pn-f">
          <span>Day</span>
          <input type="date" value={when} onChange={(e) => setWhen(e.target.value)} />
        </label>
        <label className="pn-f">
          <span>Length</span>
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="short">Short</option>
            <option value="longform">Long-form</option>
          </select>
        </label>
      </div>
      <label className="pn-f wide">
        <span>Title</span>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="I Built A ___ By Typing One Line" />
      </label>
      <label className="pn-f wide">
        <span>What it should be</span>
        <textarea rows={3} value={brief} onChange={(e) => setBrief(e.target.value)}
          placeholder="The idea, the proof on screen, and the one thing the viewer walks away with." />
      </label>
      <div className="pn-acts">
        <button className="btn btn-ghost" onClick={onCancel} disabled={!!busy}>Cancel</button>
        <button
          className="btn btn-primary"
          disabled={!ready || !!busy}
          onClick={() => onCreate({ channel_key: channel, planned_date: when, title: title.trim(), brief, format })}
        >
          {busy === 'create' ? 'Planning…' : 'Add it to the line-up'}
        </button>
      </div>
    </section>
  )
}
