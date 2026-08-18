import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RENDERS_BASE } from '../config'
import { resolveStage } from '../pipeline'
import { assetLabel } from '../templates'
import PipelineRail from './PipelineRail'
import { fmtDayHeading } from '../format'

/**
 * StepSpine — the "conductor" over the Studio production board (Phase B).
 *
 * It is PURELY PRESENTATIONAL: it owns no pipeline logic and mutates nothing.
 * It reads `resolveStage(item, counts)` (the single existing stage machine),
 * maps that stage to one of five steps, and renders:
 *   1. the channel-colored PLAN → PRODUCE → QC → ARM → LIVE rail
 *   2. a `.step-panel` for the active step — its own card for plan/arm/live,
 *      or the review/monitor body the board passes as `children` for
 *      produce/qc (kept in StudioBoard so its refs + selection state stay put)
 *   3. a `.step-foot` with exactly one `.btn-primary` (secondary verbs ghost)
 *
 * Every handler + every gate boolean is computed in StudioBoard and passed in
 * unchanged; StepSpine only decides WHICH button renders in WHICH step.
 */

// resolveStage never emits 'plan' (it collapses total===0 into 'produce'); the
// spine splits that back out so the pre-production "confirm the format" panel
// gets its own step. Every other stage maps straight through.
export function stepForStage(stage, total) {
  if (stage === 'produce' && (total || 0) === 0) return 'plan'
  return stage // 'produce' | 'qc' | 'arm' | 'live'
}

const STEP_TAG = {
  plan: 'Step 1 · Confirm the format',
  produce: 'Step 2 · Producing',
  qc: 'Step 3 · Review + QC',
  arm: 'Step 4 · Arm',
  live: 'Live',
}

// The three locked brand frames the recipe bakes into every episode.
const FRAME_TYPES = ['host_outfit', 'outro_sting', 'music_bed']

/** Resolve each locked frame's thumb for a channel from ?r=assets ({versions, locks}). */
function lockedFrames(assets, channelKey) {
  const versions = (assets && assets.versions) || []
  const locks = (assets && assets.locks) || []
  const lockByType = {}
  for (const l of locks) if (l.channel_key === channelKey) lockByType[l.asset_type] = l
  const versByType = {}
  for (const v of versions) {
    if (v.channel_key !== channelKey) continue
    ;(versByType[v.asset_type] || (versByType[v.asset_type] = [])).push(v)
  }
  return FRAME_TYPES.map((type) => {
    const vers = versByType[type] || []
    const byId = {}
    for (const v of vers) byId[v.id] = v
    const lock = lockByType[type]
    const locked =
      (lock && lock.locked_version_id && byId[lock.locked_version_id]) ||
      vers.find((v) => v.status === 'locked') ||
      null
    const coverPath = locked && (locked.thumb_path || locked.storage_path)
    return {
      type,
      label: assetLabel(type),
      coverUrl: coverPath ? RENDERS_BASE + coverPath : null,
      version: locked ? locked.version : null,
    }
  })
}

export default function StepSpine({
  item,
  counts = {},
  channel,
  templates = [],
  assets,
  accent,
  isDirect = false,
  incubating = false,
  busy = '',
  schedule = '',
  onSchedule,
  planning = false,
  planFailed = false,
  canAssemble = false,
  assembleTitle,
  assembleActive = false,
  canFinalize = false,
  finalizeTitle,
  finalizeActive = false,
  previewDisabled = false,
  previewTitle,
  onProduce,
  onRebuildDraft,
  onFinalize,
  onAssemble,
  children,
}) {
  const { stage } = resolveStage(item, counts)
  const step = stepForStage(stage, counts.total || 0)

  // Local view-navigation only (no pipeline state): a direct-mode reviewer can
  // jump the QC step forward to the Arm confirm without waiting for a re-poll.
  const [peek, setPeek] = useState(null)
  useEffect(() => {
    setPeek(null)
  }, [step])
  const effStep = peek || step

  const style = accent ? { '--ch': accent } : undefined

  // ── Incubation: the existing incubation panel (rendered by StudioBoard) is
  // the action surface; the spine just frames it with the rail + the draft to
  // watch. No footer here — Lock/Revise live in that unchanged panel.
  if (incubating) {
    return (
      <div className="step-spine" style={style}>
        <PipelineRail current={stage} accent={accent} />
        <div className="step-panel">
          <div className="step-tag">● Incubating · refine Episode 1</div>
          {children}
        </div>
      </div>
    )
  }

  const templateKey = channel && channel.template
  const tpl = templateKey ? templates.find((t) => t.key === templateKey) : null
  const channelKey = (channel && channel.key) || (item && item.channel_key) || null
  const frames = lockedFrames(assets, channelKey)
  const hasFrames = frames.some((f) => f.coverUrl)

  const previewSrc = item && item.preview_path ? RENDERS_BASE + item.preview_path : null

  // ── The active step's panel ────────────────────────────────────────
  let panel = null
  if (effStep === 'plan') {
    panel = (
      <>
        <div className="step-tag">{STEP_TAG.plan}</div>
        <div className="card format-card">
          <div className="format-card-head">
            <div className="format-card-title">
              {tpl ? tpl.name || tpl.key : channel ? channel.name || channelKey : channelKey}
            </div>
            {tpl ? (
              <span className="dim small">
                {tpl.aspect} · {tpl.runtime_s}s
              </span>
            ) : (
              <span className="dim small">Built-in recipe</span>
            )}
          </div>
          {tpl && tpl.description && <p className="dim small format-card-desc">{tpl.description}</p>}
          {hasFrames && (
            <div className="frames-strip" aria-label="Locked frames">
              {frames.map((f) => (
                <div key={f.type} className="frame-cell" title={f.label}>
                  <span className={'frame-cell-thumb' + (f.coverUrl ? '' : ' is-empty')}>
                    {f.coverUrl ? (
                      <img src={f.coverUrl} alt="" loading="lazy" />
                    ) : (
                      <span className="fs-glyph">{f.label.slice(0, 1)}</span>
                    )}
                  </span>
                  <span className="frame-cell-label">
                    {f.label}
                    {f.version ? ` · v${f.version}` : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
          <p className="dim small format-card-note">
            This is the locked recipe. Preview generates with these exact frames.
          </p>
          {planFailed ? (
            <p className="error-text small">Planning failed — check the Jobs page, then stage again.</p>
          ) : planning ? (
            <p className="dim small format-card-note">
              <span className="asset-pulse" /> Writing the asset list…
            </p>
          ) : null}
        </div>
      </>
    )
  } else if (effStep === 'arm') {
    panel = (
      <>
        <div className="step-tag">{STEP_TAG.arm}</div>
        <div className="card arm-card">
          <div className="arm-card-title">{(item && item.title) || '(untitled)'}</div>
          {item && item.planned_date && (
            <div className="dim small">{fmtDayHeading(String(item.planned_date).slice(0, 10))}</div>
          )}
          <div className="arm-card-media">
            {previewSrc ? (
              <video
                key={`${item.preview_path}|${item.preview_at || ''}`}
                className="pm-video"
                controls
                preload="metadata"
                src={previewSrc}
              />
            ) : (
              <div className="stage-pending">
                <span className="asset-pulse pulse-queued" />
                <span>Producing the final cut…</span>
              </div>
            )}
          </div>
          {isDirect ? (
            <label className="arm-when-field">
              <span className="field-label">Publish time</span>
              <input
                type="datetime-local"
                className="finalize-when"
                value={schedule}
                onChange={(e) => onSchedule && onSchedule(e.target.value)}
                title="Local publish time — YouTube flips public at this moment"
              />
            </label>
          ) : (
            <p className="dim small">
              Every part is approved. Assemble the final cut, then arm it on Publish.
            </p>
          )}
          <p className="dim small arm-card-note">
            {isDirect
              ? 'The draft above is the final cut — set the time and schedule it on YouTube.'
              : 'Assembly stitches the approved parts into the final video and drafts the post.'}
          </p>
        </div>
      </>
    )
  } else if (effStep === 'live') {
    const published = item && item.status === 'published'
    panel = (
      <>
        <div className="step-tag">{published ? 'Published' : 'Scheduled'}</div>
        <div className="card arm-card">
          <div className="arm-card-title">{(item && item.title) || '(untitled)'}</div>
          <p className="dim small">
            {published
              ? 'This episode is published — nothing left to do here.'
              : 'Scheduled and waiting to go live — nothing left to do here.'}
          </p>
        </div>
      </>
    )
  } else {
    // produce / qc: the board's own monitor + review body, passed as children.
    panel = (
      <>
        <div className="step-tag">{STEP_TAG[effStep]}</div>
        {children}
      </>
    )
  }

  // ── The single primary + ghost secondaries for the active step ─────
  let foot = null
  if (effStep === 'plan') {
    foot = (
      <>
        <button
          className="btn btn-primary"
          onClick={onProduce}
          disabled={previewDisabled || !!busy}
          title={previewTitle}
        >
          {busy === 'preview' ? 'Producing…' : 'Use this template & produce →'}
        </button>
        {tpl && (
          <Link className="btn btn-ghost" to={`/studio/templates/${tpl.key}`}>
            See everything this template uses →
          </Link>
        )}
      </>
    )
  } else if (effStep === 'produce') {
    // No primary while the factory works. The monitor's own "Rebuild draft"
    // button (in children, verbatim) is the single ghost — not duplicated here.
    foot = null
  } else if (effStep === 'qc') {
    foot = (
      <>
        {isDirect && (
          <button
            className="btn btn-primary"
            onClick={() => setPeek('arm')}
            title="Jump to scheduling — the draft above is the final cut"
          >
            Looks good — schedule →
          </button>
        )}
        {item && item.preview_path && (
          <button
            className="btn btn-ghost"
            onClick={onRebuildDraft}
            disabled={previewDisabled || !!busy}
            title={previewTitle}
          >
            Rebuild draft
          </button>
        )}
      </>
    )
  } else if (effStep === 'arm') {
    foot = (
      <>
        {isDirect ? (
          <button
            className="btn btn-primary"
            onClick={onFinalize}
            disabled={!canFinalize || !!busy || !schedule}
            title={finalizeTitle}
          >
            {busy === 'finalize' ? 'Scheduling…' : 'Approve & schedule →'}
          </button>
        ) : (
          <>
            <button
              className="btn btn-primary"
              onClick={onAssemble}
              disabled={!canAssemble || !!busy}
              title={assembleTitle}
            >
              Approve & assemble →
            </button>
            <span className="dim small">then arm on Publish</span>
          </>
        )}
        {(isDirect ? finalizeActive : assembleActive) && (
          <span className="dim small">{isDirect ? 'Scheduling…' : 'Assembling…'}</span>
        )}
        {peek === 'arm' && (
          <button className="btn btn-ghost" onClick={() => setPeek(null)}>
            ← Back to review
          </button>
        )}
      </>
    )
  }

  return (
    <div className="step-spine" style={style}>
      <PipelineRail current={stage} accent={accent} />
      <div className="step-panel">{panel}</div>
      {foot && <div className="step-foot">{foot}</div>}
    </div>
  )
}
