import { useMemo, useState } from 'react'
import { api } from '../api'
import { resolveAccents, accentFor, channelEmoji } from '../channelColor'
import { planContentDefaults, createCalendarItem } from './PlanContentModal'

/**
 * Studio launcher — Step 1 of the Studio redesign (Phase C).
 *
 * An always-visible inline card that is the primary create path of the /studio
 * page: pick a channel, name the piece, add an optional brief, and hit start.
 *
 * On submit it reuses the EXACT same handoff the old "+ New project" modal ran:
 *   1. `create_calendar_item` (same payload shape as PlanContentModal, via the
 *      shared planContentDefaults/createCalendarItem helpers)
 *   2. `stage_calendar_item` (queues plan_assets so the board is a real staged
 *      episode — matches Studio's old onCreated at pages/Studio.jsx line ~109)
 *   3. `onCreated(id)` so the parent can navigate to /studio/:id
 *
 * It invents no new endpoint. The channel/title/brief fields mirror the modal's;
 * the produce type/model/effort defaults ride along from planContentDefaults().
 */
export default function StudioLauncher({ channels = [], onCreated }) {
  const accents = useMemo(() => resolveAccents(channels), [channels])
  const [channelKey, setChannelKey] = useState('')
  const [title, setTitle] = useState('')
  const [brief, setBrief] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  // Fall back to the first channel until the user picks one explicitly.
  const activeKey = channelKey || (channels[0] ? channels[0].key : '')
  const canStart = !busy && !!activeKey && !!title.trim()

  const submit = async (e) => {
    e.preventDefault()
    if (!canStart) return
    setBusy(true)
    setError('')
    try {
      const form = {
        ...planContentDefaults(channels),
        channel_key: activeKey,
        title: title.trim(),
        brief,
      }
      const item = await createCalendarItem(form)
      if (!item || !item.id) {
        throw new Error('Created but no id was returned — open it on the Calendar.')
      }
      // Stage immediately so the user lands on a live board with plan_assets
      // already queued (same step the old modal handoff ran).
      await api.post({ action: 'stage_calendar_item', id: item.id })
      onCreated(item.id)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <form className="card studio-launcher" onSubmit={submit}>
      <div className="studio-launcher-head">
        <span className="studio-launcher-step">Step 1</span>
        <h2>What are we making?</h2>
        <p className="sub">Pick a channel, name the piece, and the factory starts building.</p>
      </div>

      <div
        className="studio-filter-row studio-launcher-chans"
        role="radiogroup"
        aria-label="Channel"
      >
        {channels.length === 0 && <span className="dim small">Loading channels…</span>}
        {channels.map((c) => {
          const on = activeKey === c.key
          return (
            <button
              type="button"
              key={c.key}
              className={'chan-filter' + (on ? ' on' : '')}
              style={{ '--ch': accentFor(c.key, accents) }}
              onClick={() => setChannelKey(c.key)}
              role="radio"
              aria-checked={on}
              title={c.key}
            >
              <span className="chan-filter-dot" />
              {channelEmoji(c.key) && <span className="chan-filter-emoji">{channelEmoji(c.key)}</span>}
              {c.name || c.key}
            </button>
          )
        })}
      </div>

      <label className="field">
        <span className="field-label">Title</span>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What should get produced?"
        />
      </label>

      <label className="field">
        <span className="field-label">
          Brief <span className="field-opt">optional</span>
        </span>
        <textarea
          rows={3}
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
          placeholder="Anything the pipeline should know when this gets queued…"
        />
      </label>

      {error && <div className="form-error">{error}</div>}

      <div className="studio-launcher-actions">
        <button type="submit" className="btn btn-primary" disabled={!canStart}>
          {busy ? 'Starting…' : 'Start a piece →'}
        </button>
      </div>
    </form>
  )
}
