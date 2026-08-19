import { useMemo, useState } from 'react'
import { api } from '../api'
import { resolveAccents, accentFor, channelEmoji } from '../channelColor'
import { planContentDefaults, createCalendarItem } from './PlanContentModal'
import SuggestionShelf from './SuggestionShelf'

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
 *
 * v19 — the suggestion shelf sits between the channel picker and the Title
 * field, so the read order is "pick channel → here's what to make → title/brief
 * prefilled". "Use this" only PREFILLS (the owner still edits and submits);
 * "Start it" accepts a suggestion as stored. Either way the accepted row is the
 * suggestion itself: when `sourceId` is set, submit routes through
 * `accept_suggestion` (patch title/brief, then the identical stage path) instead
 * of `create_calendar_item`, so editing a prefilled suggestion can never mint a
 * duplicate row and orphan the original. With no `sourceId` the create + stage +
 * navigate flow below is byte-for-byte the one that shipped in Phase C.
 */
export default function StudioLauncher({ channels = [], onCreated }) {
  const accents = useMemo(() => resolveAccents(channels), [channels])
  const [channelKey, setChannelKey] = useState('')
  const [title, setTitle] = useState('')
  const [brief, setBrief] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  // Set only when the form was prefilled from a suggestion; cleared whenever the
  // channel changes so an edited suggestion can never be accepted against the
  // wrong channel.
  const [sourceId, setSourceId] = useState('')
  const [starting, setStarting] = useState('')

  // Fall back to the first channel until the user picks one explicitly.
  const activeKey = channelKey || (channels[0] ? channels[0].key : '')
  const activeChannel = channels.find((c) => c.key === activeKey)
  const canStart = !busy && !!activeKey && !!title.trim()

  const pickChannel = (key) => {
    setChannelKey(key)
    setSourceId('')
  }

  /** "Use this" — prefill only. Never creates anything. */
  const useSuggestion = (s) => {
    setChannelKey(s.channel_key)
    setTitle(s.title || '')
    setBrief(s.brief || '')
    setSourceId(s.id)
    setError('')
  }

  const startFresh = () => {
    setSourceId('')
    setTitle('')
    setBrief('')
    setError('')
  }

  /** "Start it" — accept the suggestion exactly as stored, then open its board. */
  const startSuggestion = async (s) => {
    if (starting) return
    setStarting(s.id)
    setError('')
    try {
      await api.post({ action: 'accept_suggestion', id: s.id })
      onCreated(s.id)
    } catch (err) {
      setError(err.message)
      setStarting('')
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!canStart) return
    setBusy(true)
    setError('')
    try {
      if (sourceId) {
        // Accepting an existing suggested row (title/brief patched server-side
        // if the owner edited them), then the identical stage path.
        await api.post({
          action: 'accept_suggestion',
          id: sourceId,
          title: title.trim(),
          brief,
        })
        onCreated(sourceId)
        return
      }
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
              onClick={() => pickChannel(c.key)}
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

      <SuggestionShelf
        channelKey={activeKey}
        channelName={(activeChannel && (activeChannel.name || activeChannel.key)) || activeKey}
        channels={channels}
        accents={accents}
        onUse={useSuggestion}
        onStart={startSuggestion}
        starting={starting}
      />

      {sourceId && (
        <div className="sugg-source-note">
          <span>
            Editing a research-backed suggestion — starting will accept that row, not create a
            new one.
          </span>
          <button type="button" className="btn btn-xs btn-ghost" onClick={startFresh}>
            Start fresh instead
          </button>
        </div>
      )}

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
          {busy ? 'Starting…' : sourceId ? 'Accept & start →' : 'Start a piece →'}
        </button>
      </div>
    </form>
  )
}
