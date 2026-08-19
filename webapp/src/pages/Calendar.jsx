import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { toISODate, fmtDayHeading } from '../format'
import Chips, { ChipsGroup } from '../components/Chips'
import EmptyState from '../components/EmptyState'
import CalItem, { WrenchIcon } from '../components/CalItem'
import MonthGrid from '../components/MonthGrid'
import CalLegend from '../components/CalLegend'
import DayPanel from '../components/DayPanel'
import { resolveAccents } from '../channelColor'
import { calDisplay } from '../lifecycle'
import CalendarDrawer from '../components/CalendarDrawer'
import PlanContentModal from '../components/PlanContentModal'
import SyncAnalyticsButton from '../components/SyncAnalyticsButton'
import ConfirmDialog from '../components/ConfirmDialog'
import Toast, { useToast } from '../components/Toast'

export default function Calendar() {
  const navigate = useNavigate()
  const [channel, setChannel] = useState('')
  const [kind, setKind] = useState('')
  const [format, setFormat] = useState('') // '' | 'short' | 'longform'
  const [view, setView] = useState('month') // 'month' | 'agenda'
  const [cursor, setCursor] = useState(() => {
    const t = new Date()
    return new Date(t.getFullYear(), t.getMonth(), 1)
  })
  const calQ = usePoll(() => api.get('?r=calendar'), 15000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const postsQ = usePoll(() => api.get('?r=posts'), 15000)
  // Jobs join: lets "produced early" show WHEN production actually happened.
  const jobsQ = usePoll(() => api.get('?r=jobs&limit=100'), 30000)
  const [selectedId, setSelectedId] = useState(null)
  const [dayOpen, setDayOpen] = useState(null) // 'YYYY-MM-DD' | null
  const [showPlan, setShowPlan] = useState(false)
  const [confirmChal, setConfirmChal] = useState(null) // challenger pending supersede confirm
  const [chalBusy, setChalBusy] = useState('') // '' | 'supersede' | 'dismiss'
  const { toast, show } = useToast()

  const allItems = (calQ.data && calQ.data.items) || []
  const channels = (chansQ.data && chansQ.data.channels) || []
  const posts = (postsQ.data && postsQ.data.posts) || []
  const accents = useMemo(() => resolveAccents(channels), [channels])

  // Lifecycle join: calendar item -> its post, via the shared job.
  const postByJob = useMemo(() => {
    const m = new Map()
    for (const p of posts) if (p.job_id) m.set(p.job_id, p)
    return m
  }, [posts])

  const jobById = useMemo(() => {
    const m = new Map()
    for (const j of (jobsQ.data && jobsQ.data.jobs) || []) m.set(j.id, j)
    return m
  }, [jobsQ.data])

  // Smart dates: item id -> { displayDate, planned, early, earlyTip, movable }.
  // Display date follows the post's publish_at when it has one, else planned.
  const dispById = useMemo(() => {
    const m = new Map()
    for (const it of allItems) {
      m.set(
        it.id,
        calDisplay(
          it,
          it.job_id ? postByJob.get(it.job_id) : null,
          it.job_id ? jobById.get(it.job_id) : null
        )
      )
    }
    return m
  }, [allItems, postByJob, jobById])

  const displayDateOf = (it) =>
    (dispById.get(it.id) || {}).displayDate || String(it.planned_date || '').slice(0, 10)

  const byId = useMemo(() => new Map(allItems.map((i) => [i.id, i])), [allItems])

  // Live challengers: suggested items pointing at an existing original via replaces_id.
  // They never render standalone — they attach to the original's card instead.
  const challengerByTarget = useMemo(() => {
    const m = new Map()
    for (const it of allItems) {
      if (it.replaces_id && it.status === 'suggested' && byId.has(it.replaces_id)) {
        m.set(it.replaces_id, it)
      }
    }
    return m
  }, [allItems, byId])

  const hiddenChallengerIds = useMemo(
    () => new Set([...challengerByTarget.values()].map((c) => c.id)),
    [challengerByTarget]
  )
  const challengedIds = useMemo(
    () => new Set(challengerByTarget.keys()),
    [challengerByTarget]
  )

  // Urgency-before-schedule: originals with a live challenger AND ≤72h from
  // their planned publish. Sorted soonest-first so the strip reads top-down
  // like a "fix these before they ship" list.
  const URGENT_HOURS = 72
  const urgentPairs = useMemo(() => {
    const now = Date.now()
    const out = []
    for (const [origId, challenger] of challengerByTarget) {
      const orig = byId.get(origId)
      if (!orig) continue
      const displayD = displayDateOf(orig)
      if (!displayD) continue
      // parse as local midnight; publish slot is 16:00 IST but we compare to
      // start-of-day tolerance since we care about a 72h window, not seconds.
      const t = new Date(displayD + 'T00:00:00').getTime()
      if (Number.isNaN(t)) continue
      const hoursTo = Math.round((t - now) / 3_600_000)
      if (hoursTo <= URGENT_HOURS && hoursTo > -24) {
        out.push({ original: orig, challenger, hoursTo })
      }
    }
    out.sort((a, b) => a.hoursTo - b.hoursTo)
    return out
  }, [challengerByTarget, byId, dispById]) // eslint-disable-line react-hooks/exhaustive-deps
  const urgentOriginalIds = useMemo(
    () => new Set(urgentPairs.map((p) => p.original.id)),
    [urgentPairs]
  )
  const fmtHours = (h) => {
    if (h <= 0) return 'past due'
    if (h < 24) return h + 'h'
    const d = Math.round(h / 24)
    return d + 'd'
  }

  const itemKind = (it) => it.kind || 'content'
  const itemFormat = (it) => it.format || 'short' // pre-migration rows are Shorts
  const items = allItems.filter(
    (it) =>
      !hiddenChallengerIds.has(it.id) &&
      (!channel || it.channel_key === channel) &&
      (!kind || itemKind(it) === kind) &&
      (!format || itemFormat(it) === format)
  )

  const suggestedCount = allItems.filter((it) => it.status === 'suggested').length

  const channelOptions = [
    { value: '', label: 'All channels' },
    ...channels.map((c) => ({
      value: c.key,
      label: c.name || c.key,
      icon: <span className="fchip-dot" style={{ background: accents[c.key] }} />,
      count: allItems.filter((it) => it.channel_key === c.key).length,
    })),
  ]

  const kindOptions = [
    { value: '', label: 'All', count: allItems.length },
    {
      value: 'content',
      label: 'Content',
      count: allItems.filter((it) => itemKind(it) === 'content').length,
    },
    {
      value: 'factory',
      label: 'Factory',
      icon: WrenchIcon,
      className: 'fchip-factory',
      count: allItems.filter((it) => itemKind(it) === 'factory').length,
    },
  ]

  const formatOptions = [
    { value: '', label: 'All', count: allItems.length },
    {
      value: 'short',
      label: 'Shorts',
      count: allItems.filter((it) => itemFormat(it) === 'short').length,
    },
    {
      value: 'longform',
      label: 'Long-form',
      count: allItems.filter((it) => itemFormat(it) === 'longform').length,
    },
  ]

  // ── Challenge actions ────────────────────────────────────────────────

  const runImproved = (challenger) => setConfirmChal(challenger)

  const doSupersede = async () => {
    if (chalBusy || !confirmChal) return
    setChalBusy('supersede')
    try {
      const d = await api.post({
        action: 'supersede_calendar_item',
        suggestion_id: confirmChal.id,
      })
      const jobId =
        (d && d.job && d.job.id) || (d && d.item && d.item.job_id) || null
      show(
        jobId ? (
          <span>
            Improved plan queued — original superseded.{' '}
            <button
              className="link link-btn"
              onClick={() => navigate('/jobs', { state: { openJob: jobId } })}
            >
              View job →
            </button>
          </span>
        ) : (
          'Improved plan queued — original superseded.'
        ),
        'ok'
      )
      setConfirmChal(null)
      setSelectedId(null)
      calQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setChalBusy('')
  }

  const keepOriginal = async (challenger) => {
    if (chalBusy) return
    setChalBusy('dismiss')
    try {
      await api.post({ action: 'dismiss_challenge', suggestion_id: challenger.id })
      show('Challenge dismissed — keeping the original plan.', 'ok')
      calQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setChalBusy('')
  }

  // ── Agenda grouping (upcoming first, recent past below) ──────────────

  const groups = useMemo(() => {
    const map = new Map()
    for (const it of items) {
      const d = displayDateOf(it)
      if (!map.has(d)) map.set(d, [])
      map.get(d).push(it)
    }
    const today = toISODate(new Date())
    const dates = [...map.keys()].sort()
    return {
      map,
      today,
      upcoming: dates.filter((d) => d >= today),
      past: dates.filter((d) => d < today).reverse(),
    }
  }, [items, dispById]) // eslint-disable-line react-hooks/exhaustive-deps

  const selectedItem = selectedId ? allItems.find((i) => i.id === selectedId) : null
  const dayItems = dayOpen ? items.filter((it) => displayDateOf(it) === dayOpen) : []

  // One tap on an early-produced item: surface it on today's slot instead.
  const moveToToday = async (item) => {
    try {
      await api.post({
        action: 'update_calendar_item',
        id: item.id,
        patch: { planned_date: toISODate(new Date()) },
      })
      show('Moved to today — planned date updated.', 'ok')
      calQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
  }

  const monthLabel = cursor.toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  })
  const shiftMonth = (n) =>
    setCursor((c) => new Date(c.getFullYear(), c.getMonth() + n, 1))
  const goToday = () => {
    const t = new Date()
    setCursor(new Date(t.getFullYear(), t.getMonth(), 1))
  }

  const renderAgendaDay = (date) => (
    <section key={date}>
      <div className={'cal-day' + (date === groups.today ? ' today' : '')}>
        <span className="cal-day-dot" />
        <span className="cal-day-label">{fmtDayHeading(date)}</span>
        <span className="cal-day-line" />
      </div>
      <div className="cal-list">
        {groups.map.get(date).map((it) => (
          <CalItem
            key={it.id}
            item={it}
            accent={accents[it.channel_key] || '#94A3B8'}
            post={it.job_id ? postByJob.get(it.job_id) : null}
            disp={dispById.get(it.id)}
            challenger={challengerByTarget.get(it.id) || null}
            onClick={() => setSelectedId(it.id)}
            onRunImproved={runImproved}
            onKeepOriginal={keepOriginal}
            challengeBusy={chalBusy}
          />
        ))}
      </div>
    </section>
  )

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Plan</h1>
          <p className="sub">Decide what each channel publishes next, and when.</p>
        </div>
        <div className="head-actions">
          <SyncAnalyticsButton onToast={show} />
          <button className="btn btn-primary" onClick={() => setShowPlan(true)}>
            + Plan content
          </button>
        </div>
      </header>

      {calQ.error && <div className="error-bar">{calQ.error.message}</div>}

      <div className="cal-toolbar">
        <div className="tabs view-toggle" role="tablist" aria-label="Calendar view">
          <button
            role="tab"
            aria-selected={view === 'month'}
            className={'tab' + (view === 'month' ? ' active' : '')}
            onClick={() => setView('month')}
          >
            Month
            {suggestedCount > 0 && (
              <span
                className="view-badge"
                title={`${suggestedCount} AI suggestion${suggestedCount === 1 ? '' : 's'}`}
              >
                {suggestedCount}
              </span>
            )}
          </button>
          <button
            role="tab"
            aria-selected={view === 'agenda'}
            className={'tab' + (view === 'agenda' ? ' active' : '')}
            onClick={() => setView('agenda')}
          >
            Agenda
          </button>
        </div>

        {view === 'month' && (
          <div className="mnav">
            <button
              className="icon-btn mnav-arrow"
              onClick={() => shiftMonth(-1)}
              aria-label="Previous month"
            >
              ‹
            </button>
            <span className="mnav-label">{monthLabel}</span>
            <button
              className="icon-btn mnav-arrow"
              onClick={() => shiftMonth(1)}
              aria-label="Next month"
            >
              ›
            </button>
            <button className="btn btn-ghost btn-sm" onClick={goToday}>
              Today
            </button>
          </div>
        )}
      </div>

      <div className="chips-bar">
        <ChipsGroup label="Kind">
          <Chips options={kindOptions} value={kind} onChange={setKind} ariaLabel="Kind" />
        </ChipsGroup>
        <ChipsGroup label="Format">
          <Chips options={formatOptions} value={format} onChange={setFormat} ariaLabel="Format" />
        </ChipsGroup>
        <ChipsGroup label="Channel">
          <Chips
            options={channelOptions}
            value={channel}
            onChange={setChannel}
            ariaLabel="Channel"
          />
        </ChipsGroup>
      </div>

      {urgentPairs.length > 0 && (
        <section className="urgent-strip" aria-label="Urgent revisions">
          <div className="urgent-strip-head">
            <span className="urgent-strip-icon" aria-hidden="true">⚠</span>
            <span className="urgent-strip-title">
              Urgent revisions <span className="dim">({urgentPairs.length})</span>
            </span>
            <span className="urgent-strip-sub dim small">
              Challenger AI suggestions within {URGENT_HOURS}h of publish — decide before they ship
            </span>
          </div>
          <ul className="urgent-strip-list">
            {urgentPairs.map(({ original, challenger, hoursTo }) => (
              <li key={original.id} className="urgent-row" style={{ '--ch': accents[original.channel_key] || '#94A3B8' }}>
                <div className="urgent-row-when">
                  <span className="urgent-row-eta">{fmtHours(hoursTo)}</span>
                  <span className="urgent-row-chan">{original.channel_key}</span>
                </div>
                <div className="urgent-row-body">
                  <button
                    type="button"
                    className="urgent-row-title link-btn"
                    onClick={() => setSelectedId(original.id)}
                    title="Open on the calendar"
                  >
                    {original.title || '(untitled)'}
                  </button>
                  {challenger.why_not && (
                    <div className="urgent-row-why">{challenger.why_not}</div>
                  )}
                </div>
                <div className="urgent-row-actions">
                  <button
                    type="button"
                    className="btn btn-sm btn-primary"
                    disabled={!!chalBusy}
                    onClick={() => runImproved(challenger)}
                  >
                    Run improved
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost"
                    disabled={!!chalBusy}
                    onClick={() => keepOriginal(challenger)}
                  >
                    Keep
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {calQ.loading && calQ.data == null ? (
        <p className="dim">Loading…</p>
      ) : view === 'month' ? (
        <>
          <MonthGrid
            cursor={cursor}
            items={items}
            accents={accents}
            postByJob={postByJob}
            dispById={dispById}
            challengedIds={challengedIds}
            urgentIds={urgentOriginalIds}
            onDayClick={(ds) => setDayOpen(ds)}
          />
          <CalLegend />
        </>
      ) : items.length === 0 ? (
        <EmptyState
          message="Nothing planned yet"
          hint="Plan content by hand, or run an analytics sync and let the AI suggest the slate."
        />
      ) : (
        <>
          {groups.upcoming.length === 0 && (
            <EmptyState
              message="Nothing upcoming"
              hint="Plan content with “+ Plan content”, or run an analytics sync."
            />
          )}
          {groups.upcoming.map(renderAgendaDay)}
          {groups.past.length > 0 && (
            <>
              <div className="cal-past-divider">Past 7 days</div>
              {groups.past.map(renderAgendaDay)}
            </>
          )}
          <CalLegend />
        </>
      )}

      {dayOpen && (
        <DayPanel
          date={dayOpen}
          items={dayItems}
          accents={accents}
          postByJob={postByJob}
          dispById={dispById}
          challengerByTarget={challengerByTarget}
          onClose={() => setDayOpen(null)}
          onOpenItem={(id) => setSelectedId(id)}
          onMoveToToday={moveToToday}
          onRunImproved={runImproved}
          onKeepOriginal={keepOriginal}
          challengeBusy={chalBusy}
        />
      )}

      {selectedItem && (
        <CalendarDrawer
          key={selectedItem.id}
          item={selectedItem}
          channels={channels}
          challenger={challengerByTarget.get(selectedItem.id) || null}
          onRunImproved={runImproved}
          onKeepOriginal={keepOriginal}
          challengeBusy={chalBusy}
          onClose={() => setSelectedId(null)}
          onChanged={calQ.refresh}
          onToast={show}
        />
      )}

      {showPlan && (
        <PlanContentModal
          channels={channels}
          onClose={() => setShowPlan(false)}
          onCreated={() => {
            setShowPlan(false)
            calQ.refresh()
          }}
        />
      )}

      {confirmChal && (
        <ConfirmDialog
          title="Run improved instead?"
          confirmLabel="Run improved"
          busy={chalBusy === 'supersede'}
          onConfirm={doSupersede}
          onCancel={() => setConfirmChal(null)}
        >
          <p>
            This queues <b>{confirmChal.title || 'the improved plan'}</b> and marks{' '}
            <b>
              {(byId.get(confirmChal.replaces_id) || {}).title || 'the original plan'}
            </b>{' '}
            as superseded.
          </p>
        </ConfirmDialog>
      )}

      <Toast toast={toast} />
    </div>
  )
}
