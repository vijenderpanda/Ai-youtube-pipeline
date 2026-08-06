import { Link } from 'react-router-dom'
import CalendarStatusChip from './CalendarStatusChip'
import ChallengeBlock from './ChallengeBlock'
import { typeLabel, modelLabel } from '../jobMeta'
import { lifecycleOf } from '../lifecycle'
import { EarlyGlyph } from './glyphs'

export const WrenchIcon = (
  <svg
    width="12"
    height="12"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
  </svg>
)

function excerpt(s, n = 140) {
  const t = String(s || '').trim()
  return t.length > n ? t.slice(0, n).trimEnd() + '…' : t
}

/**
 * Full calendar item card — used by the Agenda list and the Day panel.
 * v7: speaks the same language as the month pills — channel color as the
 * left edge (--ch), lifecycle as the fill treatment (lc-* classes, joined
 * post via `post`). When a live AI challenger targets this item, the
 * challenge renders INSIDE this card as an attached ChallengeBlock.
 */
export default function CalItem({
  item,
  accent,
  post = null,
  disp = null,
  onClick,
  detail = false,
  challenger = null,
  onMoveToToday = null,
  onRunImproved,
  onKeepOriginal,
  challengeBusy = '',
}) {
  const lc = lifecycleOf(item, post)
  const early = !!(disp && disp.early)
  const suggested = lc === 'suggested'
  const struck = lc === 'skipped' || lc === 'superseded'
  const factory = item.kind === 'factory'
  return (
    <div
      className={
        'card cal-item lc-' +
        lc +
        (factory ? ' factory' : '') +
        (challenger ? ' challenged' : '')
      }
      style={{ '--ch': accent }}
      onClick={onClick}
    >
      <div className="cal-item-main">
        <div className={'cal-item-title' + (struck ? ' struck' : '')}>
          {item.title || '(untitled)'}
        </div>
        <div className="cal-item-chips">
          <CalendarStatusChip status={lc} />
          {item.production_mode === 'staged' && (
            <Link
              className="tag staged-tag"
              to={`/studio/${item.id}`}
              onClick={(e) => e.stopPropagation()}
              title="Staged production — open the Studio board"
            >
              staged
            </Link>
          )}
          {early && (
            <span className="tag early-tag" title={disp.earlyTip}>
              {EarlyGlyph} early
            </span>
          )}
          {factory && (
            <span className="tag factory-tag" title="Improvement of the factory itself">
              {WrenchIcon} factory
            </span>
          )}
          {challenger && (
            <span className="tag challenged-tag" title="The AI challenges this plan">
              ⚠ challenged
            </span>
          )}
          <span className="tag chan-tag">
            <span className="chan-tag-dot" style={{ background: accent }} />
            {item.channel_key}
          </span>
          <span className="tag dim-tag">{typeLabel(item.type)}</span>
          <span className="tag dim-tag">{modelLabel(item.model)}</span>
          <span className="tag dim-tag">{item.effort}</span>
          {item.ultracode && (
            <span className="tag ultra-chip" title="Ultracode — multi-agent orchestration">
              ⚡
            </span>
          )}
        </div>
        {detail && item.brief && <div className="cal-item-brief">{excerpt(item.brief)}</div>}
        {detail && early && disp.movable && onMoveToToday && (
          <div className="cal-item-early-row">
            <span className="cal-item-early-note">{disp.earlyTip}</span>
            <button
              type="button"
              className="btn btn-ghost btn-sm early-move"
              title="Set planned date to today so this shows on today's slot"
              onClick={(e) => {
                e.stopPropagation()
                onMoveToToday(item)
              }}
            >
              {EarlyGlyph} Show on today instead
            </button>
          </div>
        )}
        {suggested && item.suggestion_reason && (
          <div className="cal-item-reason" title={item.suggestion_reason}>
            {item.suggestion_reason}
          </div>
        )}
        {challenger && (
          <ChallengeBlock
            original={item}
            challenger={challenger}
            onRunImproved={onRunImproved}
            onKeepOriginal={onKeepOriginal}
            busy={challengeBusy}
          />
        )}
      </div>
    </div>
  )
}
