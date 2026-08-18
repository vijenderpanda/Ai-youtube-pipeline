import { useMemo, useState } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import { accentFor } from '../channelColor'
import { fmtDayHeading } from '../format'

/**
 * Suggestion shelf — "here's what to make next", grounded in each channel's own
 * research files (v19).
 *
 * Reads `?r=suggestions&channel=<key>` (edge: factory-api). Every row it shows
 * is an `origin='ai_suggestion'` calendar row written by scripts/suggest_next.py
 * with a non-empty `evidence.cites[]`; the edge drops anything that cannot show
 * its work, and so does this component. The whole point of the shelf is that it
 * is NOT a black box: no card renders without an expandable trail of real
 * file:line quotes behind it.
 *
 * Three shapes, deliberately NOT flattened into one:
 *   T1 / T2  → a content idea      (.sugg-idea)     — start it, or edit it first
 *   T4 / T5  → a chore             (.sugg-chore)    — the channel has no topic
 *              queue yet; the only honest suggestion is the file/task that
 *              would create one. Never dressed up as an idea.
 *   T0       → a blocker           (.sugg-blocked)  — the channel cannot produce
 *              at all. Warn tone, no start button, decision text only.
 *
 * A blocked channel has no factory_channels row, so it is missing from the
 * launcher's channel picker and can never be "selected". That is exactly why
 * the blocked strip is fed by its own network-wide read and is NEVER filtered
 * against the `channels` prop — otherwise the one card that most needs a human
 * would be the one card nobody could ever see.
 */

// Tier → what the tier actually means, in the owner's language.
const TIERS = {
  T0: {
    shape: 'blocked',
    label: 'Blocked',
    hint: 'Tier 0 — this channel cannot produce at all. A decision is owed before any idea is honest.',
  },
  T1: {
    shape: 'idea',
    label: 'Scored slate',
    hint: 'Tier 1 — drawn from a scored candidate slate in this channel’s own research.',
  },
  T2: {
    shape: 'idea',
    label: 'Named next unit',
    hint: 'Tier 2 — this channel’s research already names this as the next unit to make.',
  },
  T3: { shape: 'idea', label: 'Research-backed', hint: 'Tier 3 — research-backed suggestion.' },
  T4: {
    shape: 'chore',
    label: 'Chore',
    hint: 'Tier 4 — format wedge: this channel has no topic queue, so the only honest suggestion is a chore.',
  },
  T5: {
    shape: 'chore',
    label: 'Chore',
    hint: 'Tier 5 — recipe only: there is no topic queue yet. The chore is what would create one.',
  },
}

// suggestion_confidence, said plainly. Never hidden, never softened.
const CONFIDENCE = {
  scored: {
    label: 'scored',
    tone: 'ok',
    note: 'The underlying research scored this candidate directly.',
  },
  inferred_rank: {
    label: 'rank inferred',
    tone: 'warn',
    note: 'The research names this candidate but its score did not survive. The ranking is inferred, not measured.',
  },
  date_inferred: {
    label: 'date inferred',
    tone: 'warn',
    note: 'No empty guarded slot was free, so the date came from the channel’s cadence formula — treat it as “no date yet”.',
  },
  ai_generated: {
    label: 'AI-generated',
    tone: 'warn',
    note: 'A model wrote this suggestion. Check the citations before trusting it.',
  },
}

const CREATE_FILE_RE = /^(create|update)\s+[\w./-]+\/[\w.-]+\.\w+/i
const CHORE_TITLE_RE = /^chore\s*[—–-]/i

/** Which of the three card shapes a row is. Tier decides; title is the fallback. */
export function suggestionShape(s) {
  const tier = String((s.evidence && s.evidence.tier) || '').toUpperCase()
  if (TIERS[tier]) return TIERS[tier].shape
  const title = String(s.title || '')
  if (CHORE_TITLE_RE.test(title) || CREATE_FILE_RE.test(title)) return 'chore'
  return 'idea'
}

const citesOf = (s) =>
  (s.evidence && Array.isArray(s.evidence.cites) && s.evidence.cites) || []
const blockersOf = (s) =>
  (s.evidence && Array.isArray(s.evidence.blockers) && s.evidence.blockers.filter(Boolean)) || []
const constraintsOf = (s) =>
  (s.evidence && Array.isArray(s.evidence.constraints) && s.evidence.constraints.filter(Boolean)) ||
  []

/** `path:line`, the way it is quoted in the repo. */
const citeRef = (c) => String(c.path || '') + (c.line != null ? ':' + c.line : '')

function fmtGeneratedAt(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return String(iso)
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * The anti-black-box control: a real <details> disclosure listing every citation
 * as `path:line` plus its quote, the constraints the piece must obey, and who
 * generated the card and when. Renders nothing at all when there are no cites.
 */
function EvidenceDisclosure({ suggestion, open, onToggle, labelledBy }) {
  const cites = citesOf(suggestion)
  if (cites.length === 0) return null
  const ev = suggestion.evidence || {}
  const constraints = constraintsOf(suggestion)
  const peg = ev.peg && typeof ev.peg === 'object' ? ev.peg : null

  return (
    <details
      className="sugg-evidence"
      open={open}
      onToggle={(e) => onToggle(e.currentTarget.open)}
    >
      <summary aria-describedby={labelledBy}>
        <span className="sugg-evidence-q">Why this?</span>
        <span className="dim small">
          {cites.length} source{cites.length === 1 ? '' : 's'}
        </span>
      </summary>

      <div className="sugg-evidence-body">
        {peg && (peg.url || peg.date) && (
          <p className="sugg-peg">
            <span className="sugg-evidence-head">News peg</span>{' '}
            {peg.url ? (
              <a href={peg.url} target="_blank" rel="noreferrer">
                {peg.title || peg.url}
              </a>
            ) : (
              <span>{peg.title || ''}</span>
            )}
            {peg.date && <span className="dim small"> · {peg.date}</span>}
          </p>
        )}

        <ul className="sugg-cites">
          {cites.map((c, i) => (
            <li key={i} className="sugg-cite">
              <div className="sugg-cite-label">{c.label || citeRef(c)}</div>
              <div className="sugg-cite-ref">
                <code>{citeRef(c)}</code>
                {c.url && (
                  <a href={c.url} target="_blank" rel="noreferrer" className="sugg-cite-link">
                    open ↗
                  </a>
                )}
                {c.date && <span className="dim small">{c.date}</span>}
              </div>
              {c.quote && <blockquote className="sugg-cite-quote">{c.quote}</blockquote>}
              {c.note && <p className="sugg-cite-note">⚠ {c.note}</p>}
            </li>
          ))}
        </ul>

        {constraints.length > 0 && (
          <>
            <p className="sugg-evidence-head">Must obey</p>
            <ul className="sugg-constraints">
              {constraints.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </>
        )}

        <p className="sugg-evidence-foot dim small">
          Generated by {ev.generated_by || 'unknown'}
          {ev.generated_at ? ' · ' + fmtGeneratedAt(ev.generated_at) : ''}
          {ev.source ? ' · source: ' + ev.source : ''}
        </p>
      </div>
    </details>
  )
}

function SuggestionCard({ suggestion: s, accent, onUse, onStart, starting }) {
  const [open, setOpen] = useState(false)
  const shape = suggestionShape(s)
  const tier = String((s.evidence && s.evidence.tier) || '').toUpperCase()
  const tierMeta = TIERS[tier]
  const conf = CONFIDENCE[s.suggestion_confidence] || {
    label: s.suggestion_confidence || 'unrated',
    tone: 'warn',
    note: 'No confidence was recorded for this suggestion.',
  }
  const blockers = blockersOf(s)
  const dateInferred = s.suggestion_confidence === 'date_inferred'
  const titleId = 'sugg-title-' + s.id
  const isBlocked = shape === 'blocked'
  const busy = starting === s.id

  return (
    <li
      className={'sugg-row sugg-' + shape}
      style={{ '--ch': accent }}
      aria-labelledby={titleId}
    >
      <div className="sugg-row-when">
        <span className={'sugg-row-date' + (dateInferred ? ' sugg-row-date-soft' : '')}>
          {dateInferred
            ? 'no date yet'
            : fmtDayHeading(String(s.planned_date || '').slice(0, 10)) || 'no date yet'}
        </span>
        <span className="sugg-row-chan">{s.channel_key}</span>
      </div>

      <div className="sugg-row-body">
        <h4 className="sugg-row-title" id={titleId}>
          {isBlocked && <span className="sugg-row-kind">Blocked · </span>}
          {shape === 'chore' && <span className="sugg-row-kind">Chore · </span>}
          {s.title || '(untitled)'}
        </h4>

        <div className="sugg-row-chips">
          {tierMeta && (
            <span className={'chip sugg-chip-' + shape} title={tierMeta.hint}>
              {tier} · {tierMeta.label}
            </span>
          )}
          <span className={'chip sugg-chip-conf sugg-conf-' + conf.tone} title={conf.note}>
            {conf.label}
          </span>
          {s.suggestion_source && (
            <span className="chip sugg-chip-src" title="Which research file this came from">
              {s.suggestion_source}
            </span>
          )}
        </div>

        {s.suggestion_reason && <div className="cal-item-reason">{s.suggestion_reason}</div>}

        {dateInferred && (
          <p className="sugg-caveat small">
            No free guarded slot — the date is a cadence estimate, not a booking.
          </p>
        )}

        {blockers.length > 0 && (
          <div className="sugg-blockers" role="note">
            <span className="sugg-blockers-head">
              ⚠ {blockers.length} blocker{blockers.length === 1 ? '' : 's'} before this can run
            </span>
            <ul>
              {blockers.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          </div>
        )}

        <EvidenceDisclosure
          suggestion={s}
          open={open}
          onToggle={setOpen}
          labelledBy={titleId}
        />
      </div>

      <div className="sugg-row-actions">
        {isBlocked ? (
          <>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              disabled
              title="This channel has no factory row and cannot produce — decide the blocker first."
            >
              Can’t start
            </button>
            <button
              type="button"
              className="btn btn-xs btn-ghost"
              onClick={() => setOpen(true)}
              aria-expanded={open}
            >
              Open blockers
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              onClick={() => onUse(s)}
              title="Fill the form above with this suggestion so you can edit it before starting"
            >
              Use this
            </button>
            {blockers.length > 0 ? (
              <button
                type="button"
                className="btn btn-xs btn-ghost"
                onClick={() => setOpen(true)}
                aria-expanded={open}
                title="Clear the blockers before starting this one"
              >
                Open blockers
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-xs btn-ghost"
                onClick={() => onStart(s)}
                disabled={busy}
                title="Accept as-is and open its Studio board"
              >
                {busy ? 'Starting…' : 'Start it'}
              </button>
            )}
          </>
        )}
      </div>
    </li>
  )
}

const VISIBLE = 3

export default function SuggestionShelf({
  channelKey,
  channelName,
  channels = [],
  accents = {},
  onUse,
  onStart,
  starting = '',
}) {
  const [showAll, setShowAll] = useState(false)

  // Per-channel read. Refetches whenever the launcher's channel changes.
  const suggQ = usePoll(
    () =>
      channelKey
        ? api.get('?r=suggestions&limit=24&channel=' + encodeURIComponent(channelKey))
        : Promise.resolve({ items: [] }),
    0,
    [channelKey],
  )

  // Network-wide read, used ONLY to surface blocked channels. A T0 channel has
  // no factory_channels row, so it never appears in the picker — filtering the
  // shelf by the `channels` prop would make its card unreachable forever.
  const blockedQ = usePoll(() => api.get('?r=suggestions&limit=24'), 0)

  const knownKeys = useMemo(() => new Set(channels.map((c) => c.key)), [channels])

  const items = (suggQ.data && suggQ.data.items) || []
  const blocked = useMemo(() => {
    const all = (blockedQ.data && blockedQ.data.items) || []
    // Only the ones the picker can never reach — no duplicates with `items`.
    return all.filter((s) => suggestionShape(s) === 'blocked' && !knownKeys.has(s.channel_key))
  }, [blockedQ.data, knownKeys])

  const shown = showAll ? items : items.slice(0, VISIBLE)
  const loading = suggQ.loading && suggQ.data == null

  if (!channelKey && blocked.length === 0) return null

  return (
    <section className="sugg-shelf" aria-label="Research-backed suggestions">
      <div className="sugg-shelf-head">
        <span className="studio-launcher-step">Or start from research</span>
        <span className="sugg-shelf-title">
          Suggested for {channelName || channelKey || 'the network'}
        </span>
        <span className="sugg-shelf-sub dim small">
          Grounded in this channel’s own files — never generic.
        </span>
      </div>

      {loading && <span className="dim small">Reading this channel’s research…</span>}

      {!loading && suggQ.error && (
        <span className="dim small">
          Couldn’t read the research ({suggQ.error.message}).
        </span>
      )}

      {!loading && !suggQ.error && items.length === 0 && (
        <p className="sugg-empty dim small">
          No research-backed suggestion for this channel yet — nothing in its files names a
          next piece. Name one above instead.
        </p>
      )}

      {shown.length > 0 && (
        <ul className="sugg-shelf-list">
          {shown.map((s) => (
            <SuggestionCard
              key={s.id}
              suggestion={s}
              accent={accentFor(s.channel_key, accents)}
              onUse={onUse}
              onStart={onStart}
              starting={starting}
            />
          ))}
        </ul>
      )}

      {!showAll && items.length > VISIBLE && (
        <button type="button" className="btn btn-xs btn-ghost" onClick={() => setShowAll(true)}>
          Show {items.length - VISIBLE} more
        </button>
      )}

      {blocked.length > 0 && (
        <>
          <p className="sugg-shelf-subhead dim small">
            Blocked elsewhere in the network — these channels can’t be picked above because
            they have no factory row.
          </p>
          <ul className="sugg-shelf-list">
            {blocked.map((s) => (
              <SuggestionCard
                key={s.id}
                suggestion={s}
                accent={accentFor(s.channel_key, accents)}
                onUse={onUse}
                onStart={onStart}
                starting={starting}
              />
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
