import { Fragment, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RENDERS_BASE } from '../config'
import { assetLabel, isImagePath, kindOf, requiredShotRoles } from '../assetCatalog'
import { mediaKind, fileExt } from '../mediaKind'
import { resolveStage } from '../pipeline'
import PipelineRail from './PipelineRail'
import CastReconciliation from './CastReconciliation'
import SequenceReconciliation from './SequenceReconciliation'
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

/**
 * A cast's human name. `label` is optional and often empty, so fall back to
 * something that still distinguishes one cast from another (the host frame it
 * freezes) rather than rendering a bare blank next to the version number.
 */
function castName(v) {
  if (!v) return ''
  const base = `v${v.version}`
  const label = String(v.label || '').trim()
  if (label) return `${base} · ${label}`
  const host = (v.composition && v.composition.host_outfit) || null
  const ref = host && host.build_ref
  if (ref) {
    const leaf = String(ref).split('/').filter(Boolean).pop()
    if (leaf) return `${base} · ${leaf}`
  }
  return base
}

/** Why a cast cannot be produced with — mirrors the API's own 409 wording. */
function castBlockReason(v) {
  if (!v) return ''
  if (v.status === 'draft') return 'draft — lock it first'
  if (v.status === 'retired') return 'retired — branch a new cast instead'
  return `${v.status} — only a locked cast can be produced with`
}

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
    const imgPath =
      (isImagePath(locked && locked.thumb_path) && locked.thumb_path) ||
      (isImagePath(locked && locked.storage_path) && locked.storage_path) ||
      null
    return {
      type,
      label: assetLabel(type),
      coverUrl: imgPath ? RENDERS_BASE + imgPath : null,
      kind: locked ? kindOf(type, locked) : null,
      version: locked ? locked.version : null,
      from: 'lock',
    }
  })
}

/**
 * The frames a BOUND cast will actually render with.
 *
 * build_ep_v2.resolve_locked() is per-slot: the cast's frozen `composition`
 * wins, and any slot the cast does not compose still falls through to the
 * channel lock. So this overlays the composition onto the lock frames rather
 * than replacing them wholesale — the strip then matches the build slot by slot.
 */
function castFrames(cast, lockFrames) {
  const comp = (cast && cast.composition) || {}
  return lockFrames.map((f) => {
    const slot = comp[f.type]
    if (!slot || !slot.build_ref) return f // not in this cast → the lock still runs
    const imgPath =
      (isImagePath(slot.thumb_path) && slot.thumb_path) ||
      (isImagePath(slot.storage_path) && slot.storage_path) ||
      null
    return {
      type: f.type,
      label: f.label,
      coverUrl: imgPath ? RENDERS_BASE + imgPath : null,
      kind: kindOf(f.type, slot),
      version: slot.version || null,
      from: 'cast',
    }
  })
}

// ── LIVE PRODUCE PANEL ────────────────────────────────────────────────────
// While a DIRECT monolithic produce_preview job runs, this is what the produce
// step shows instead of the empty "Producing the final cut…" spinner: elapsed
// time, a heartbeat pulse, the assets landed so far, the current activity line,
// and a phase stepper. It is deliberately HONEST — no fake %/denominator/ETA
// (a monolithic produce has no fixed total), only what we can actually observe.

const PHASES = [
  { key: 'script', label: 'Script' },
  { key: 'visuals', label: 'Visuals' },
  { key: 'render', label: 'Render' },
  { key: 'master', label: 'Master' },
]

const liveFilename = (a) =>
  a.filename || String(a.storage_path || '').split('/').pop() || a.asset_key || ''

/** frames jsonb (array | JSON string | nothing) — first frame is a servable still. */
function firstFrame(a) {
  let f = a && a.frames
  if (typeof f === 'string') {
    try {
      f = JSON.parse(f)
    } catch {
      f = null
    }
  }
  return Array.isArray(f) && typeof f[0] === 'string' && f[0] ? f[0] : null
}

/** A small servable still for a pushed asset, or null → glyph cell. */
function liveThumbSrc(a) {
  const name = liveFilename(a)
  const kind = mediaKind(a.kind, name)
  if (kind === 'image' && a.storage_path) return RENDERS_BASE + a.storage_path
  if (isImagePath(a.thumb_path)) return RENDERS_BASE + a.thumb_path
  if (a.poster_path) return RENDERS_BASE + a.poster_path
  const fr = firstFrame(a)
  if (fr) return RENDERS_BASE + fr
  return null
}

function liveGlyph(a) {
  const kind = mediaKind(a.kind, liveFilename(a))
  if (kind === 'video') return '▶'
  if (kind === 'audio') return '♪'
  if (kind === 'image') return '▣'
  const e = fileExt(liveFilename(a))
  return e ? '.' + e.toUpperCase() : 'TXT'
}

/**
 * The last human-meaningful line of the agent's live log. Strips the streaming
 * scaffolding — [thinking…], [system:*], [result…], [worker]… — and tool-call
 * lines ([tool:Bash] {…json…}); prefers the last plain assistant sentence. When
 * only tool lines remain, returns a friendly fallback derived from the tool.
 */
function currentActivity(logs) {
  if (!logs) return ''
  const text = Array.isArray(logs) ? logs.join('\n') : String(logs)
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
  const isScaffold = (l) => /^\[(thinking|system:|result|worker\])/i.test(l)
  const isTool = (l) => /^\[tool:/i.test(l)
  let lastTool = null
  for (let i = lines.length - 1; i >= 0; i--) {
    const l = lines[i]
    if (isScaffold(l)) continue
    if (isTool(l)) {
      if (!lastTool) lastTool = l
      continue
    }
    // A plain assistant sentence — the thing worth showing. Trim any trailing
    // tool JSON that got concatenated onto the same buffer line, just in case.
    return l.replace(/\s*\[tool:.*$/i, '').slice(0, 140)
  }
  if (lastTool) {
    const m = /^\[tool:([^\]]+)\]/i.exec(lastTool)
    const tool = (m && m[1]) || ''
    const verb = /bash/i.test(tool)
      ? 'running commands'
      : /read|grep|glob|ls/i.test(tool)
        ? 'reading files'
        : /write|edit/i.test(tool)
          ? 'writing files'
          : 'rendering'
    return `Working… (${verb})`
  }
  return ''
}

/**
 * Best-effort phase inference from what's observable — assets pushed + log
 * keywords. Later phases win. Returns null when we can't tell confidently
 * (earliest moment, nothing pushed, no keyword) so the stepper stays hidden
 * rather than guessing.
 */
function inferPhase(assets, logs) {
  const t = String(logs || '').toLowerCase()
  if (/master|lufs|loudnorm|mastering|final cut/.test(t)) return 'master'
  if (/render|remotion|stitch|ffmpeg|encod|assembl/.test(t)) return 'render'
  const hasVideo = assets.some((a) => mediaKind(a.kind, liveFilename(a)) === 'video')
  if (hasVideo) return 'render'
  if (assets.length > 0) return 'visuals'
  if (/script|writing|write the|outline|hook|plan/.test(t)) return 'script'
  return null
}

const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

function LiveProducePanel({ job, assets = [], accent }) {
  // Local 1s tick so elapsed reads live between the board's 8s polls.
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  const startedMs = job && job.started_at ? Date.parse(job.started_at) : NaN
  const elapsed = Number.isFinite(startedMs) ? Math.max(0, Math.floor((now - startedMs) / 1000)) : null
  const hbMs = job && job.heartbeat_at ? Date.parse(job.heartbeat_at) : NaN
  const hbAge = Number.isFinite(hbMs) ? Math.max(0, Math.floor((now - hbMs) / 1000)) : null
  const live = hbAge != null && hbAge <= 90

  const n = assets.length
  const activity = currentActivity(job && job.logs)
  const phase = inferPhase(assets, job && job.logs)
  const phaseAt = phase ? PHASES.findIndex((p) => p.key === phase) : -1

  const style = accent ? { '--ch': accent } : undefined

  return (
    <div className="live-produce" style={style} role="status" aria-live="polite">
      <div className="live-produce-head">
        <span
          className={'live-produce-dot' + (live ? ' on' : ' stale')}
          aria-hidden="true"
        />
        <span className="live-produce-title">
          Producing — {n} piece{n === 1 ? '' : 's'} done so far
        </span>
        {elapsed != null && (
          <span className="mono live-produce-elapsed" aria-hidden="true">
            {mmss(elapsed)}
          </span>
        )}
        <span className="dim small live-produce-liveness">
          {live ? 'live' : hbAge != null ? `no heartbeat for ${hbAge}s` : 'starting…'}
        </span>
      </div>

      {phase && (
        <div className="phase-steps" aria-hidden="true">
          {PHASES.map((p, i) => (
            <Fragment key={p.key}>
              {i > 0 && <span className={'phase-seg' + (i <= phaseAt ? ' done' : '')} />}
              <span
                className={
                  'phase-step' +
                  (i < phaseAt ? ' done' : '') +
                  (i === phaseAt ? ' at' : '')
                }
              >
                {p.label}
              </span>
            </Fragment>
          ))}
        </div>
      )}

      {n > 0 && (
        <div className="frames-strip live-filmstrip" aria-label="Assets produced so far">
          {assets.map((a) => {
            const src = liveThumbSrc(a)
            const st = String(a.status || 'queued').toLowerCase()
            return (
              <div
                key={a.asset_key}
                className={`frame-cell live-cell fs-${st}`}
                title={`${a.title || a.asset_key} — ${st}`}
              >
                <span className={'frame-cell-thumb' + (src ? '' : ' is-empty')}>
                  {src ? (
                    <img src={src} alt="" loading="lazy" />
                  ) : (
                    <span className="fs-glyph">{liveGlyph(a)}</span>
                  )}
                </span>
                <span className="frame-cell-label">{a.title || assetLabel(a.asset_key)}</span>
              </div>
            )
          })}
        </div>
      )}

      <div className="live-produce-activity dim small" title={activity || undefined}>
        {activity || 'Working…'}
      </div>
    </div>
  )
}

// S6 (Sprint 5): the pre-produce GENERATION MANIFEST — every asset the build will
// make, each linked to its scene(s), free|paid, low-confidence flagged. Populated
// by build_ep_v2 --manifest (persisted to factory_calendar.generation_manifest);
// null until a produce/manifest run has stamped it.
function ManifestPanel({ manifest }) {
  if (!manifest || !Array.isArray(manifest.assets)) return null
  const paid = manifest.paid_asset_count ?? manifest.assets.filter((a) => a.cost === 'paid').length
  const low = manifest.low_confidence_scenes || []
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <div className="step-tag">
        Generation manifest · {manifest.assets.length} assets · {paid} paid · {manifest.sequence_mode || 'augment'}
      </div>
      {low.length > 0 && (
        <div className="small" style={{ color: '#e0a84a', margin: '4px 0' }}>
          ⚠ {low.length} low-confidence scene{low.length === 1 ? '' : 's'} — review before producing
        </div>
      )}
      <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0', display: 'grid', gap: 4 }}>
        {manifest.assets.map((a, i) => (
          <li key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}>
            <span className="tag" style={{ minWidth: 78 }}>{a.type}</span>
            {a.id && <span style={{ fontWeight: 600 }}>{a.id}</span>}
            {a.scene != null && <span className="dim small">scene {a.scene}</span>}
            {a.confidence != null && (
              <span className="dim small" style={a.confidence < 0.5 ? { color: '#e0a84a' } : undefined}>
                {Math.round(a.confidence * 100)}%
              </span>
            )}
            <span
              className="tag"
              style={{ marginLeft: 'auto', color: a.cost === 'paid' ? 'var(--ch)' : 'var(--text-3)' }}
            >
              {a.cost}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function StepSpine({
  item,
  counts = {},
  channel,
  templates = [],
  assets,
  castVersions = [],
  castBusy = false,
  onSetCast,
  accent,
  isDirect = false,
  incubating = false,
  busy = '',
  schedule = '',
  onSchedule,
  producing = false,
  produceJob = null,
  producedAssets = [],
  builtRows = null,
  builtBlocks = null,
  planning = false,
  planFailed = false,
  planFailReason = '',
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
  const { stage } = resolveStage(item, counts, { producing })
  const step = stepForStage(stage, counts.total || 0)

  // Local view-navigation only (no pipeline state): a direct-mode reviewer can
  // jump the QC step forward to the Arm confirm without waiting for a re-poll.
  const [peek, setPeek] = useState(null)
  // S7 (Sprint 5): auto-mode toggle — produce all beats with minimal review.
  // View state (like peek); passed to onProduce, which sends it to produce_preview.
  const [autoMode, setAutoMode] = useState(!!(item && item.auto_mode))
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

  // ── Which CAST produces this piece ─────────────────────────────────
  // build_ep_v2._bind_template_version() precedence (the part this board can
  // see): factory_calendar.template_version_id → factory_templates.
  // active_version_id → nothing. An unbound piece therefore does NOT render off
  // the raw channel locks; it renders off the template's ACTIVE cast. And
  // _tpl_lookup() ignores any cast that is not `locked`, falling back to the
  // channel locks — so only a locked cast is ever "in force" here.
  const boundId = (item && item.template_version_id) || null
  const activeId = (tpl && tpl.active_version_id) || null
  const castById = {}
  for (const v of castVersions) castById[v.id] = v
  const boundCast = boundId ? castById[boundId] || null : null
  const activeCast = activeId ? castById[activeId] || null : null
  const pickedCast = boundId ? boundCast : activeCast
  const effCast = pickedCast && pickedCast.status === 'locked' ? pickedCast : null
  // A pinned cast the build will refuse (draft/retired/vanished) — the panel
  // must say so instead of showing frames that will not render.
  const deadPin = boundId && !effCast ? boundCast : null

  const lockFrames = lockedFrames(assets, channelKey)
  const frames = effCast ? castFrames(effCast, lockFrames) : lockFrames
  const hasFrames = frames.some((f) => f.coverUrl)

  // ── Cast reconciliation (EP15) — shown once produced, on the review steps.
  // Diffs what the piece is pinned to against what the build used; the only
  // ground truth for "used" is factory_episode_assets_used, which has no
  // per-episode read yet, so it renders the divergences provable now (a refused
  // cast, a host that can't render this format) and marks the Built column
  // honestly. `brandVersions` carries meta.heygen so the host's shotCoverage can
  // be checked from the pinned version_id.
  const reqRoles = requiredShotRoles(tpl)
  const reconEl =
    item && item.preview_path && (effStep === 'qc' || effStep === 'arm' || effStep === 'live') ? (
      <>
        <CastReconciliation
          item={item}
          pickedCast={pickedCast}
          effCast={effCast}
          deadPin={deadPin}
          boundId={boundId}
          brandVersions={(assets && assets.versions) || []}
          reqRoles={reqRoles}
          builtRows={builtRows}
        />
        {/* S4 — the SEQUENCE twin of the cast card: locked composition._sequence
            vs the blocks the build actually rendered (factory_episode_blocks_used). */}
        <SequenceReconciliation
          item={item}
          pickedCast={pickedCast}
          deadPin={deadPin}
          boundId={boundId}
          builtBlocks={builtBlocks}
        />
      </>
    ) : null

  // Only locked casts are offered. Drafts stay visible but disabled (you can
  // see the work in progress; you cannot ship it). Retired casts are noise
  // unless this piece is pinned to one, in which case it must be listed so the
  // <select> can show the real current value.
  const castOptions = castVersions.filter(
    (v) => v.status === 'locked' || v.status === 'draft' || v.id === boundId
  )
  const defaultCastLabel = activeCast
    ? `Use the channel's active cast (${castName(activeCast)})`
    : 'Channel default (asset locks)'

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
            <div className="frames-strip" aria-label="Frames this piece will render with">
              {frames.map((f) => (
                <div
                  key={f.type}
                  className="frame-cell"
                  title={
                    f.from === 'cast'
                      ? `${f.label} — from ${castName(effCast)}`
                      : effCast
                        ? `${f.label} — not in this cast, so the channel lock still runs`
                        : f.label
                  }
                >
                  <span className={'frame-cell-thumb' + (f.coverUrl ? '' : ' is-empty')}>
                    {f.coverUrl ? (
                      <img src={f.coverUrl} alt="" loading="lazy" />
                    ) : (
                      <span className="fs-glyph">{f.kind === 'audio' ? '♪' : f.kind === 'video' ? '▶' : f.label.slice(0, 1)}</span>
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

          {/* CAST switcher — the one thing this step could show but not change. */}
          <div className="cast-row">
            <label className="cast-row-label" htmlFor="plan-cast-select">
              Cast
            </label>
            <select
              id="plan-cast-select"
              className="cast-select"
              value={boundId || ''}
              disabled={castBusy || !!busy || !onSetCast}
              onChange={(e) => onSetCast && onSetCast(e.target.value || null)}
              title="Which locked cast this piece produces with"
            >
              <option value="">{defaultCastLabel}</option>
              {castOptions.map((v) => {
                const blocked = v.status !== 'locked'
                const why = castBlockReason(v)
                return (
                  <option
                    key={v.id}
                    value={v.id}
                    disabled={blocked}
                    title={blocked ? why : `Produce this piece with ${castName(v)}`}
                  >
                    {`${castName(v)}${v.id === activeId ? ' · ACTIVE' : ''}${blocked ? ` — ${why}` : ''}`}
                  </option>
                )
              })}
            </select>
            {castBusy && <span className="dim small">Switching…</span>}
            {tpl && (
              <Link className="link small cast-row-compose" to={`/studio/templates/${tpl.key}`}>
                Compose a new cast →
              </Link>
            )}
          </div>

          {deadPin ? (
            <p className="error-text small format-card-note">
              Pinned to {castName(deadPin)} — {castBlockReason(deadPin)}. The build ignores it and
              falls back to the channel&apos;s asset locks, shown above.
            </p>
          ) : boundId && !boundCast ? (
            <p className="error-text small format-card-note">
              Pinned to a cast that no longer exists. The build falls back to the channel&apos;s
              asset locks, shown above.
            </p>
          ) : null}

          <p className="dim small format-card-note">
            {effCast ? (
              <>
                Producing with <b>{castName(effCast)}</b>
                {effCast.id === activeId ? " — the template's active cast" : ''}
                {boundId ? ' — pinned to this piece.' : '.'} Preview generates with these exact
                frames.
              </>
            ) : (
              <>
                No locked cast is in force — this produces with the channel&apos;s asset locks,
                shown above.
              </>
            )}
          </p>
          {planFailed ? (
            <p className="error-text small">
              {/* Show WHY, not just "failed". The common case is an account cap
                  ("You've hit your session limit · resets …"), which is not a
                  pipeline fault and needs no fix — only a retry later. The old
                  copy said "Planning failed … stage again", which is neither the
                  right phase nor the right verb for a direct-mode piece. */}
              {planFailReason
                ? <>Last run stopped: <b>{planFailReason}</b>{' '}
                    {/rate|limit|quota|resets/i.test(planFailReason)
                      ? '— nothing to fix here, just run it again after that.'
                      : '— see the Jobs page for the full log.'}</>
                : <>The last run failed — see the Jobs page for the log, then try again.</>}
            </p>
          ) : planning ? (
            <p className="dim small format-card-note">
              <span className="asset-pulse" /> Writing the asset list…
            </p>
          ) : null}
        </div>
        {item && item.generation_manifest && <ManifestPanel manifest={item.generation_manifest} />}
        <label
          className="auto-mode-toggle"
          style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, fontSize: 13 }}
        >
          <input type="checkbox" checked={autoMode} onChange={(e) => setAutoMode(e.target.checked)} />
          <span>
            Auto-mode — produce all beats with minimal review{' '}
            <span className="dim">(still stops at the arm gate for your go)</span>
          </span>
        </label>
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
    // While a DIRECT monolithic produce is live, the produce step shows the
    // honest live-progress panel (elapsed + assets + activity + phase) instead
    // of the staged monitor body — this is where the old empty "Producing the
    // final cut…" spinner used to sit once the rail wrongly jumped to Arm.
    const showLive = effStep === 'produce' && isDirect && producing
    panel = (
      <>
        <div className="step-tag">{STEP_TAG[effStep]}</div>
        {showLive ? (
          <LiveProducePanel job={produceJob} assets={producedAssets} accent={accent} />
        ) : (
          children
        )}
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
          onClick={() => onProduce(autoMode)}
          disabled={previewDisabled || !!busy}
          title={previewTitle}
        >
          {busy === 'preview' ? 'Producing…' : autoMode ? 'Auto-produce →' : 'Use this template & produce →'}
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
      <div className="step-panel">
        {panel}
        {reconEl}
      </div>
      {foot && <div className="step-foot">{foot}</div>}
    </div>
  )
}
