import { useState } from 'react'

function excerpt(s, n = 110) {
  const t = String(s || '').trim()
  return t.length > n ? t.slice(0, n).trimEnd() + '…' : t
}

/**
 * v6 — "AI challenge" block. Rendered INSIDE the original item's card when a
 * live suggested challenger points at it via replaces_id. Never a standalone card.
 *
 *   original      the challenged calendar item
 *   challenger    the suggested item carrying replaces_id + why_not
 *   onRunImproved(challenger)  -> supersede flow (confirm handled by caller)
 *   onKeepOriginal(challenger) -> dismiss_challenge
 *   busy          '' | 'supersede' | 'dismiss'
 */
export default function ChallengeBlock({
  original,
  challenger,
  onRunImproved,
  onKeepOriginal,
  busy,
}) {
  const [expanded, setExpanded] = useState(false)
  const [whyOpen, setWhyOpen] = useState(false)
  const longBrief = String(challenger.brief || '').trim().length > 110
  const longWhy = String(challenger.why_not || '').trim().length > 150

  return (
    <div className="challenge" onClick={(e) => e.stopPropagation()}>
      <div className="challenge-head">
        <span aria-hidden="true">⚠</span> AI challenge
      </div>

      {challenger.why_not && (
        <div className="challenge-why">
          {whyOpen ? challenger.why_not : excerpt(challenger.why_not, 150)}
          {longWhy && (
            <button
              type="button"
              className="link link-btn challenge-expand"
              onClick={() => setWhyOpen((v) => !v)}
            >
              {whyOpen ? 'less' : 'more'}
            </button>
          )}
        </div>
      )}

      <div className="challenge-compare">
        <div className="challenge-col">
          <span className="challenge-col-label">Current plan</span>
          <div className="challenge-col-title">{original.title || '(untitled)'}</div>
          {original.brief && (
            <div className="challenge-col-brief">{excerpt(original.brief)}</div>
          )}
        </div>
        <div className="challenge-arrow" aria-hidden="true">
          →
        </div>
        <div className="challenge-col improved">
          <span className="challenge-col-label">Improved</span>
          <div className="challenge-col-title">{challenger.title || '(untitled)'}</div>
          {challenger.brief && (
            <div className="challenge-col-brief">
              {expanded ? challenger.brief : excerpt(challenger.brief)}
              {longBrief && (
                <button
                  type="button"
                  className="link link-btn challenge-expand"
                  onClick={() => setExpanded((v) => !v)}
                >
                  {expanded ? 'less' : 'more'}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="challenge-actions">
        <button
          type="button"
          className="btn btn-sm btn-ghost"
          disabled={!!busy}
          onClick={() => onKeepOriginal(challenger)}
        >
          {busy === 'dismiss' ? 'Keeping…' : 'Keep original'}
        </button>
        <button
          type="button"
          className="btn btn-sm challenge-run"
          disabled={!!busy}
          onClick={() => onRunImproved(challenger)}
        >
          {busy === 'supersede' ? 'Queuing…' : '▶ Run improved instead'}
        </button>
      </div>
    </div>
  )
}
