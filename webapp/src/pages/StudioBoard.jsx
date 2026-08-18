import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { resolveAccents, accentFor } from '../channelColor'
import { resolveStage, countsFromAssets } from '../pipeline'
import StepSpine, { stepForStage } from '../components/StepSpine'
import { RENDERS_BASE } from '../config'
import { mediaKind, fileExt } from '../mediaKind'
import AssetInspector, {
  AssetStatusChip,
  AutoApprovedBadge,
  isAutoApproved,
} from '../components/AssetInspector'
import TextPreview from '../components/TextPreview'
import Lightbox from '../components/Lightbox'
import StatusChip from '../components/StatusChip'
import ConfirmDialog from '../components/ConfirmDialog'
import EmptyState from '../components/EmptyState'
import Toast, { useToast } from '../components/Toast'
import { fmtDayHeading, timeAgo, fmtDate } from '../format'

const assetFilename = (a) => a.filename || (a.storage_path || '').split('/').pop() || a.asset_key
const posOf = (a) => (a.position == null ? Number.MAX_SAFE_INTEGER : Number(a.position))
const stepNum = (i) => String(i + 1).padStart(2, '0')
const statusOf = (a) => String(a.status || 'queued').toLowerCase()

// Factory-QC'd text internals (plans, scripts, prompts) live in the docs
// rail, not the filmstrip: stored kind 'text', or an unrecognized kind with
// a text-y extension. Non-text 'other' files stay visual.
const TEXT_EXTS = new Set(['md', 'markdown', 'txt', 'json', 'yml', 'yaml', 'csv', 'srt', 'vtt'])
const isDoc = (a) => {
  if (String(a.kind || '').toLowerCase() === 'text') return true
  const name = assetFilename(a)
  return mediaKind(a.kind, name) === 'other' && TEXT_EXTS.has(fileExt(name))
}

/** frames jsonb (array of storage paths) — may arrive as array, string, or nothing. */
function framesOf(a) {
  let f = a && a.frames
  if (typeof f === 'string') {
    try {
      f = JSON.parse(f)
    } catch {
      f = []
    }
  }
  return Array.isArray(f) ? f.filter((p) => typeof p === 'string' && p) : []
}

const frameLabel = (i, n) => (n === 3 ? ['start', 'mid', 'end'][i] : `f${i + 1}`)

function glyphFor(kind, filename) {
  if (kind === 'video') return '▶'
  if (kind === 'audio') return '♪'
  if (kind === 'image') return '▣'
  const e = fileExt(filename)
  return e ? '.' + e.toUpperCase() : 'TXT'
}

function thumbSrcFor(a) {
  const kind = mediaKind(a.kind, assetFilename(a))
  if (kind === 'image' && a.storage_path) return RENDERS_BASE + a.storage_path
  if (kind === 'video') {
    if (a.poster_path) return RENDERS_BASE + a.poster_path
    const fr = framesOf(a)
    if (fr.length) return RENDERS_BASE + fr[0]
  }
  return null
}

/** Small still for filmstrip chips + bin tiles: real thumb when we have one, kind glyph otherwise. */
function Thumb({ a, className }) {
  const src = thumbSrcFor(a)
  const filename = assetFilename(a)
  return (
    <span className={className}>
      {src ? (
        <img src={src} alt="" loading="lazy" />
      ) : (
        <span className="fs-glyph">{glyphFor(mediaKind(a.kind, filename), filename)}</span>
      )}
    </span>
  )
}

/**
 * Studio board for one staged episode (see docs/STAGED-PIPELINE.md §5),
 * laid out like a video editor: draft-preview program monitor, numbered
 * filmstrip of the visual/audio production steps, a big stage for the
 * selected asset, an inspector with review actions + version history, a
 * bin of all visual steps, and a collapsed rail of factory-QC'd text docs.
 * Review is exception-based: v1 assets arrive auto-approved by factory QC;
 * only revisions (v2+) land in 'review'. All UI state is keyed by
 * asset_key so the 8s poll never resets it.
 */
export default function StudioBoard() {
  const { calendarId } = useParams()
  const boardQ = usePoll(
    () => api.get(`?r=episode_assets&calendar_id=${encodeURIComponent(calendarId)}`),
    8000,
    [calendarId]
  )
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const { toast, show } = useToast()
  const [confirmAssemble, setConfirmAssemble] = useState(false)
  const [busy, setBusy] = useState('') // '' | 'assemble' | 'preview' | 'finalize' | 'revise' | 'lock'
  const [schedule, setSchedule] = useState('') // datetime-local for scheduling
  const [feedback, setFeedback] = useState('') // v18: incubation revision note
  const [confirmLock, setConfirmLock] = useState(false)
  const [selectedKey, setSelectedKey] = useState(null)
  const [pinned, setPinned] = useState({}) // asset_key -> version number displayed (absent = latest)
  const [docsOpen, setDocsOpen] = useState(false)
  const [zoom, setZoom] = useState(null)
  const stripRef = useRef(null)
  const stageRef = useRef(null)

  const item = (boardQ.data && boardQ.data.item) || null
  const assets = (boardQ.data && boardQ.data.assets) || []
  const jobs = (boardQ.data && boardQ.data.jobs) || []

  // Phase B — the step-spine PLAN panel shows the channel's resolved template
  // card + its locked brand frames. Templates are the whole registry; brand
  // assets are re-fetched once we learn this item's channel.
  const channelKey = item ? item.channel_key : ''
  const tplQ = usePoll(() => api.get('?r=templates'), 0)
  const brandAssetsQ = usePoll(
    () => api.get(`?r=assets${channelKey ? `&channel=${encodeURIComponent(channelKey)}` : ''}`),
    0,
    [channelKey]
  )
  const templates = (tplQ.data && tplQ.data.templates) || []
  const brandAssets = brandAssetsQ.data || { versions: [], locks: [] }

  // Pre-fill a sensible publish time so the creator confirms one, never invents
  // one from a blank field: the planned date at 09:00 local, or tomorrow 09:00
  // if that's already past. They can still change it before scheduling.
  useEffect(() => {
    if (!item || schedule) return
    const pad = (n) => String(n).padStart(2, '0')
    const now = new Date()
    let d = item.planned_date ? new Date(item.planned_date + 'T09:00') : null
    if (!d || isNaN(d.getTime()) || d.getTime() < now.getTime()) {
      d = new Date(now)
      d.setDate(d.getDate() + 1)
      d.setHours(9, 0, 0, 0)
    }
    setSchedule(
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
    )
  }, [item, schedule])
  const channels = (chansQ.data && chansQ.data.channels) || []
  const accents = useMemo(() => resolveAccents(channels), [channels])
  const accent = item ? accentFor(item.channel_key, accents) : '#8f9bb3'
  // v18: while the channel is incubating, this board refines the Ep01 TEMP
  // (Revise ⇄ Lock) instead of scheduling to YouTube.
  const channel = item ? channels.find((c) => c.key === item.channel_key) : null
  const incubating = !!channel && channel.lifecycle === 'incubating'

  // Latest version per asset_key — the only rows whose status matters.
  const latestByKey = useMemo(() => {
    const m = new Map()
    for (const a of assets) {
      const cur = m.get(a.asset_key)
      if (!cur || (a.version || 1) > (cur.version || 1)) m.set(a.asset_key, a)
    }
    return m
  }, [assets])

  // Older (superseded) versions per asset_key, newest first.
  const olderByKey = useMemo(() => {
    const m = new Map()
    for (const a of assets) {
      const latest = latestByKey.get(a.asset_key)
      if (latest && a.id !== latest.id) {
        if (!m.has(a.asset_key)) m.set(a.asset_key, [])
        m.get(a.asset_key).push(a)
      }
    }
    for (const list of m.values()) list.sort((x, y) => (y.version || 1) - (x.version || 1))
    return m
  }, [assets, latestByKey])

  // First-seen time per asset_key (v1's created_at) — keeps step numbers
  // stable when a revision replaces the latest row.
  const firstSeen = useMemo(() => {
    const m = new Map()
    for (const a of assets) {
      const t = String(a.created_at || '')
      const cur = m.get(a.asset_key)
      if (cur == null || t < cur) m.set(a.asset_key, t)
    }
    return m
  }, [assets])

  // Full production order: position asc (older rows without one go last),
  // tiebreak first created_at asc, then asset_key. Step numbers come from
  // THIS list so they match the plan even though docs render elsewhere.
  const ordered = useMemo(() => {
    const list = [...latestByKey.values()]
    list.sort(
      (x, y) =>
        posOf(x) - posOf(y) ||
        String(firstSeen.get(x.asset_key) || '').localeCompare(
          String(firstSeen.get(y.asset_key) || '')
        ) ||
        String(x.asset_key).localeCompare(String(y.asset_key))
    )
    return list
  }, [latestByKey, firstSeen])

  // Visual/audio steps drive the filmstrip + bin; text docs get the quiet rail.
  const visuals = useMemo(() => ordered.filter((a) => !isDoc(a)), [ordered])
  const docs = useMemo(() => ordered.filter(isDoc), [ordered])
  const stepNoByKey = useMemo(() => {
    const m = new Map()
    ordered.forEach((a, i) => m.set(a.asset_key, i))
    return m
  }, [ordered])

  const total = ordered.length
  const done = ordered.filter((a) => a.status === 'approved' || a.status === 'skipped').length
  const approvedCount = ordered.filter((a) => a.status === 'approved').length
  const pct = total ? Math.round((done / total) * 100) : 0

  // Single stage machine (unchanged) drives both the rail and which step panel
  // the spine shows. resolveStage never emits 'plan'; stepForStage splits the
  // pre-production total===0 case back out into the "confirm the format" step.
  const counts = useMemo(() => countsFromAssets(assets), [assets])
  const pipeStage = item ? resolveStage(item, counts).stage : 'plan'
  const step = stepForStage(pipeStage, counts.total || 0)

  // First load: land on what needs the human — a pending revision, then a
  // failure, then the first visual step. Never reset later (poll refreshes
  // must not steal the selection).
  useEffect(() => {
    if (ordered.length === 0) return
    if (selectedKey && latestByKey.has(selectedKey)) return
    const pick =
      ordered.find((a) => a.status === 'review') ||
      ordered.find((a) => a.status === 'failed') ||
      visuals[0] ||
      ordered[0]
    setSelectedKey(pick.asset_key)
  }, [ordered, visuals, selectedKey, latestByKey])

  // Arrow keys walk the filmstrip (ignored while typing or driving a player).
  const visualsRef = useRef(visuals)
  visualsRef.current = visuals
  const selectedRef = useRef(selectedKey)
  selectedRef.current = selectedKey
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
      const t = e.target
      const tag = t && t.tagName
      if (
        tag === 'INPUT' ||
        tag === 'TEXTAREA' ||
        tag === 'SELECT' ||
        tag === 'VIDEO' ||
        tag === 'AUDIO' ||
        (t && t.isContentEditable)
      )
        return
      const list = visualsRef.current
      if (!list.length) return
      e.preventDefault()
      const cur = list.findIndex((a) => a.asset_key === selectedRef.current)
      const next =
        e.key === 'ArrowLeft'
          ? Math.max(0, cur <= 0 ? 0 : cur - 1)
          : Math.min(list.length - 1, cur < 0 ? 0 : cur + 1)
      setSelectedKey(list[next].asset_key)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // Keep the selected chip visible in the strip.
  useEffect(() => {
    if (!stripRef.current || !selectedKey) return
    const el = stripRef.current.querySelector(`[data-key="${CSS.escape(selectedKey)}"]`)
    if (el) el.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }, [selectedKey])

  const genActive = jobs.filter(
    (j) => j.type === 'generate_asset' && (j.status === 'queued' || j.status === 'running')
  ).length

  const newestOf = (type) =>
    jobs
      .filter((j) => j.type === type)
      .sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))[0] ||
    null
  const planJob = newestOf('plan_assets')
  const assembleJob = newestOf('assemble_episode')
  const assembleActive =
    !!assembleJob && (assembleJob.status === 'queued' || assembleJob.status === 'running')
  const previewJob = newestOf('preview_episode')
  const previewActive =
    !!previewJob && (previewJob.status === 'queued' || previewJob.status === 'running')

  const canAssemble = total > 0 && done === total && approvedCount > 0 && !assembleActive
  const assembleTitle = canAssemble
    ? 'Queue the final assembly job'
    : total === 0
      ? 'No assets yet — the plan is still being written'
      : assembleActive
        ? 'An assembly job is already queued or running'
        : approvedCount === 0
          ? 'At least one asset must be approved'
          : 'Every asset must be approved or skipped first'

  const doAssemble = async () => {
    if (busy) return
    setBusy('assemble')
    try {
      await api.post({ action: 'queue_assembly', calendar_id: calendarId })
      show('Assembly queued — the worker will build the episode', 'ok')
      setConfirmAssemble(false)
      boardQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setBusy('')
  }

  // Draft preview (low-res stitch). The server 409s with a human message
  // when assets are still generating/failed or a preview is in flight —
  // surfaced as a toast, never a crash.
  const previewDisabled = !!busy || genActive > 0 || previewActive
  const previewTitle = previewActive
    ? 'A draft preview is already queued or running'
    : genActive > 0
      ? 'Wait for the generation queue to drain first'
      : item && item.preview_path
        ? 'Rebuild the low-res draft with the latest assets'
        : 'Queue a low-res draft stitch of the whole episode'

  const doPreview = async () => {
    if (busy) return
    setBusy('preview')
    try {
      await api.post({ action: 'queue_preview', calendar_id: calendarId })
      show('Draft preview queued — a low-res stitch will render', 'ok')
      boardQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setBusy('')
  }

  // v16: direct-mode (produce_preview) items don't ASSEMBLE — they FINALIZE:
  // master + LUFS QC + arm YouTube via scripts/finalize_episode.py (a
  // shell_script job). The preview MP4 in the program monitor above is the QC
  // gate. finalize_episode.py writes the scheduled post + flips this item to
  // produced, so the app reflects the arm with no manual DB write.
  const isDirect = !!item && item.production_mode === 'direct'
  const finalizeJob = newestOf('shell_script')
  const finalizeActive =
    !!finalizeJob && (finalizeJob.status === 'queued' || finalizeJob.status === 'running')
  const canFinalize = isDirect && !!item?.preview_path && !finalizeActive
  const finalizeTitle = !isDirect
    ? 'Only preview-style episodes are scheduled from here'
    : !item?.preview_path
      ? 'Produce the episode first — you review it before scheduling'
      : finalizeActive
        ? 'Already scheduling…'
        : !schedule
          ? 'Pick a publish date and time first'
          : 'Finish the final cut and schedule it on YouTube for this time'

  const doFinalize = async () => {
    if (busy) return
    if (!schedule) {
      show('Pick a publish date/time first', 'error')
      return
    }
    const iso = new Date(schedule).toISOString() // local datetime-local → UTC
    setBusy('finalize')
    try {
      await api.post({ action: 'finalize_episode', calendar_id: calendarId, schedule: iso })
      show('Scheduling — finishing the final cut and setting the YouTube time', 'ok')
      boardQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setBusy('')
  }

  // ── v18: incubation loop — this preview IS Ep01 TEMP ───────────────
  // The newest produce_preview job carries the running revision number.
  const previewJobDirect = newestOf('produce_preview')
  const iteration = Number((previewJobDirect && previewJobDirect.meta && previewJobDirect.meta.iteration) || 1)
  const previewBusy =
    !!previewJobDirect &&
    (previewJobDirect.status === 'queued' || previewJobDirect.status === 'running')
  const canRefine = incubating && !!item?.preview_path && !previewBusy

  // Plan-step ("confirm the format") status note: direct items are "planning"
  // while their monolithic produce_preview runs; staged items while plan_assets
  // writes the fragment list.
  const planning = isDirect
    ? previewBusy
    : !!(planJob && (planJob.status === 'queued' || planJob.status === 'running'))
  const planFailed = isDirect
    ? !!(previewJobDirect && previewJobDirect.status === 'failed')
    : !!(planJob && planJob.status === 'failed')

  const doRevise = async () => {
    if (busy) return
    const note = feedback.trim()
    if (!note) {
      show('Write what to change first', 'error')
      return
    }
    setBusy('revise')
    try {
      const d = await api.post({ action: 'revise_preview', calendar_id: calendarId, feedback: note })
      show(`Revision ${d.iteration || iteration + 1} queued — re-producing Episode 1`, 'ok')
      setFeedback('')
      boardQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setBusy('')
  }

  const doLock = async () => {
    if (busy || !item) return
    setBusy('lock')
    try {
      await api.post({ action: 'lock_baseline', channel_key: item.channel_key, calendar_id: calendarId })
      show('Baseline locked — the channel is now active', 'ok')
      setConfirmLock(false)
      boardQ.refresh()
      chansQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setBusy('')
  }

  // ── Selection → displayed version ──────────────────────────────────
  const selected = selectedKey ? latestByKey.get(selectedKey) || null : null
  const history = selected ? olderByKey.get(selected.asset_key) || [] : []
  const pin = selected ? pinned[selected.asset_key] : undefined
  const displayed = useMemo(() => {
    if (!selected) return null
    if (pin == null || pin === (selected.version || 1)) return selected
    return history.find((h) => (h.version || 1) === pin) || selected
  }, [selected, history, pin])

  const showVersion = (v) => {
    if (!selected) return
    setPinned((m) => {
      const next = { ...m }
      if (v === (selected.version || 1)) delete next[selected.asset_key]
      else next[selected.asset_key] = v
      return next
    })
  }

  const pickAndShow = (key) => {
    setSelectedKey(key)
    if (stageRef.current) stageRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  // ── Stage (preview monitor) for the displayed version ──────────────
  let stage = null
  if (displayed) {
    const dSrc = displayed.storage_path ? RENDERS_BASE + displayed.storage_path : null
    const dName = assetFilename(displayed)
    const dKind = mediaKind(displayed.kind, dName)
    const dStatus = statusOf(displayed)
    const dTitle = `${displayed.title || displayed.asset_key} · v${displayed.version || 1}`
    const dFrames = dKind === 'video' ? framesOf(displayed) : []

    let media
    if (!dSrc) {
      media = (
        <div className="stage-pending">
          {dStatus === 'generating' ? (
            <>
              <span className="asset-pulse" />
              <span>Generating…</span>
            </>
          ) : dStatus === 'failed' ? (
            <>
              <span className="asset-pulse pulse-failed" />
              <span className="error-text">Generation failed</span>
            </>
          ) : (
            <>
              <span className="asset-pulse pulse-queued" />
              <span>Waiting in queue…</span>
            </>
          )}
        </div>
      )
    } else if (dKind === 'image') {
      media = (
        <button
          type="button"
          className="stage-img-btn"
          onClick={() => setZoom({ src: dSrc, kind: 'image', title: dTitle })}
          title="Open full size"
        >
          <img className="stage-img" src={dSrc} alt={dTitle} />
        </button>
      )
    } else if (dKind === 'video') {
      media = (
        <>
          <video
            key={displayed.id}
            className="stage-video"
            controls
            preload="metadata"
            src={dSrc}
            poster={displayed.poster_path ? RENDERS_BASE + displayed.poster_path : undefined}
          />
          {dFrames.length > 0 && (
            <div className="frame-strip">
              {dFrames.map((p, i) => (
                <button
                  key={`${p}-${i}`}
                  type="button"
                  className="frame-thumb"
                  onClick={() =>
                    setZoom({
                      src: RENDERS_BASE + p,
                      kind: 'image',
                      title: `${dTitle} · ${frameLabel(i, dFrames.length)}`,
                    })
                  }
                  title={`${frameLabel(i, dFrames.length)} — open full size`}
                >
                  <img src={RENDERS_BASE + p} alt={frameLabel(i, dFrames.length)} loading="lazy" />
                  <span className="frame-tag">{frameLabel(i, dFrames.length)}</span>
                </button>
              ))}
            </div>
          )}
        </>
      )
    } else if (dKind === 'audio') {
      media = (
        <div className="stage-audio">
          <audio key={displayed.id} controls preload="none" src={dSrc} />
        </div>
      )
    } else {
      media = (
        <TextPreview
          key={displayed.id}
          asset={displayed}
          reviewNote={displayed.review_note || (selected && selected.review_note)}
        />
      )
    }

    stage = (
      <div className="stage">
        {selected && displayed.id !== selected.id && (
          <div className="stage-superseded">
            <span>Superseded v{displayed.version || 1}</span>
            <button type="button" className="link" onClick={() => showVersion(selected.version || 1)}>
              Back to latest v{selected.version || 1}
            </button>
          </div>
        )}
        <div className="stage-media">{media}</div>
        {dSrc && (
          <div className="stage-bar">
            <span className="stage-file">{dName}</span>
            <a className="link" href={dSrc} target="_blank" rel="noreferrer">
              Open ↗
            </a>
          </div>
        )}
      </div>
    )
  }

  // review_note for media assets shows in the inspector; anything the stage
  // renders through TextPreview (kind 'other') gets the callout there instead.
  const selKind = selected ? mediaKind(selected.kind, assetFilename(selected)) : null
  const inspectorNote = selected && selKind !== 'other' ? selected.review_note : null

  // ── Board body pieces (unchanged markup) — composed per step into the spine
  // panel. The draft monitor, progress, filmstrip, review stage, bin and docs
  // rail all keep their exact JSX + refs; only WHEN they render changes.
  const previewMonitorEl = (
    <div className="preview-monitor">
      <div className="pm-head">
        <span className="pm-label">Draft preview</span>
        {item && item.preview_path && item.preview_at && (
          <span className="pm-time" title={fmtDate(item.preview_at)}>
            {timeAgo(item.preview_at)}
          </span>
        )}
        {previewActive && (
          <span className="pm-status">
            <StatusChip status={previewJob.status} />
            <span className="dim small">Draft rendering…</span>
          </span>
        )}
        <button
          className="btn btn-ghost btn-sm pm-btn"
          onClick={doPreview}
          disabled={previewDisabled}
          title={previewTitle}
        >
          {busy === 'preview'
            ? 'Queuing…'
            : item && item.preview_path
              ? 'Rebuild draft'
              : 'Build draft preview'}
        </button>
      </div>
      {item && item.preview_path && (
        <video
          key={`${item.preview_path}|${item.preview_at || ''}`}
          className="pm-video"
          controls
          preload="metadata"
          src={RENDERS_BASE + item.preview_path}
        />
      )}
      <div className="pm-caption">
        Low-res draft — judge beats, overlays and timing before assembling.
      </div>
    </div>
  )

  const progressBarEl = total > 0 && (
    <div className="board-bar">
      <div className="progress">
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <span className="progress-label">
          {done}/{total} approved or skipped
        </span>
      </div>
      {genActive > 0 && (
        <span className="chip queue-hint">
          {genActive} part{genActive === 1 ? '' : 's'} still being produced
        </span>
      )}
    </div>
  )

  const filmstripEl = visuals.length > 0 && (
    <div className="filmstrip" ref={stripRef} role="listbox" aria-label="Production steps">
      {visuals.map((a) => {
        const st = statusOf(a)
        const isSel = a.asset_key === selectedKey
        const num = stepNum(stepNoByKey.get(a.asset_key))
        return (
          <button
            key={a.asset_key}
            type="button"
            data-key={a.asset_key}
            role="option"
            aria-selected={isSel}
            className={`fs-chip fs-${st}` + (isSel ? ' selected' : '')}
            onClick={() => setSelectedKey(a.asset_key)}
            title={`${num} · ${a.title || a.asset_key} — ${st}`}
          >
            <Thumb a={a} className="fs-thumb" />
            <span className="fs-meta">
              <span className="fs-num">{num}</span>
              <span className="fs-title">{a.title || a.asset_key}</span>
            </span>
          </button>
        )
      })}
    </div>
  )

  const stageRowEl = (
    <div className="stage-row" ref={stageRef}>
      {stage}
      {selected && (
        <AssetInspector
          key={selected.asset_key}
          asset={selected}
          history={history}
          displayed={displayed}
          onShowVersion={showVersion}
          reviewNote={inspectorNote}
          onToast={show}
          refresh={boardQ.refresh}
        />
      )}
    </div>
  )

  const binEl = visuals.length > 0 && (
    <section className="bin-section">
      <div className="asset-section-head">
        Bin <span className="asset-section-count">{visuals.length}</span>
      </div>
      <div className="bin">
        {visuals.map((a) => {
          const st = statusOf(a)
          const isSel = a.asset_key === selectedKey
          return (
            <button
              key={a.asset_key}
              type="button"
              className={`bin-tile fs-${st}` + (isSel ? ' selected' : '')}
              onClick={() => pickAndShow(a.asset_key)}
              title={`${a.title || a.asset_key} — ${st}`}
            >
              <span className="bin-num">{stepNum(stepNoByKey.get(a.asset_key))}</span>
              <Thumb a={a} className="bin-thumb" />
              <span className="bin-name">{a.title || a.asset_key}</span>
              {a.group_key && <span className="bin-group">{a.group_key}</span>}
              <span className="bin-dot" />
            </button>
          )
        })}
      </div>
    </section>
  )

  const docsEl = docs.length > 0 && (
    <section className="docs-rail">
      <button
        type="button"
        className="docs-toggle"
        onClick={() => setDocsOpen((v) => !v)}
        aria-expanded={docsOpen}
      >
        <span className={'docs-caret' + (docsOpen ? ' open' : '')}>▸</span>
        Factory docs ({docs.length})
        <span className="docs-hint">QC&apos;d internals — plans, scripts, prompts</span>
      </button>
      {docsOpen && (
        <div className="docs-list">
          {docs.map((a) => {
            const isSel = a.asset_key === selectedKey
            return (
              <button
                key={a.asset_key}
                type="button"
                className={'doc-row' + (isSel ? ' selected' : '')}
                onClick={() => pickAndShow(a.asset_key)}
                title={a.asset_key}
              >
                <span className="doc-title">{a.title || a.asset_key}</span>
                <AssetStatusChip status={a.status} />
                {isAutoApproved(a) && <AutoApprovedBadge />}
                <span className="doc-time" title={fmtDate(a.created_at)}>
                  {timeAgo(a.created_at)}
                </span>
              </button>
            )
          })}
        </div>
      )}
    </section>
  )

  // PRODUCE shows the monitor + progress + live filmstrip; QC (and incubation,
  // which keeps its full body so nothing is lost) adds the review stage, bin
  // and docs. PLAN/ARM/LIVE render their own panels inside the spine.
  const producingBody = (
    <>
      {previewMonitorEl}
      {progressBarEl}
      {filmstripEl}
    </>
  )
  const reviewBody = (
    <>
      {previewMonitorEl}
      {progressBarEl}
      {filmstripEl}
      {stageRowEl}
      {binEl}
      {docsEl}
    </>
  )
  let spineBody = null
  if (incubating) spineBody = reviewBody
  else if (step === 'produce') spineBody = producingBody
  else if (step === 'qc') spineBody = reviewBody

  return (
    <div className="page studio-board" style={{ '--ch': accent }}>
      <header className="page-head">
        <div>
          <div className="crumbs">
            <Link className="link" to="/studio">
              Studio
            </Link>{' '}
            <span className="dim">/</span>{' '}
            <span className="mono">{item ? item.channel_key : '…'}</span>
          </div>
          <h1>{item ? item.title || '(untitled)' : 'Loading…'}</h1>
          {item && (
            <div className="board-chips">
              <span className="tag chan-tag">
                <span className="chan-tag-dot" style={{ background: accent }} />
                {item.channel_key}
              </span>
              {item.planned_date && (
                <span className="dim small">
                  {fmtDayHeading(String(item.planned_date).slice(0, 10))}
                </span>
              )}
            </div>
          )}
        </div>
      </header>

      {incubating && (
        <section className="card panel incubation-panel">
          <div className="panel-head">
            <h2>
              <span className="incubating-pill">● Incubating</span> Refine Episode 1, then lock it
            </h2>
            <span className="dim small">Revision {iteration}</span>
          </div>
          <p className="dim small" style={{ marginTop: 0 }}>
            This is Episode 1 as a <strong>temp</strong>. Watch the preview above, then either send
            it back with notes or lock it — locking freezes this look/sound as the channel’s{' '}
            <strong>baseline recipe</strong> and flips the channel to active. Nothing publishes to
            YouTube until you lock.
          </p>
          <label className="field">
            <span className="field-label">What should change?</span>
            <textarea
              rows={3}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="e.g. hook is too slow, cut the intro card; make the captions bigger; warmer grade…"
              disabled={!!busy}
            />
          </label>
          <div className="drawer-actions cal-actions">
            <button
              className="btn btn-ghost"
              onClick={doRevise}
              disabled={!canRefine || !!busy || !feedback.trim()}
              title={
                !item?.preview_path
                  ? 'Produce Episode 1 first'
                  : previewBusy
                    ? 'A revision is still producing…'
                    : 'Re-produce Episode 1 with this feedback'
              }
            >
              {busy === 'revise' ? 'Queuing…' : '↻ Revise with feedback'}
            </button>
            <button
              className="btn btn-primary"
              onClick={() => setConfirmLock(true)}
              disabled={!canRefine || !!busy}
              title={
                !item?.preview_path
                  ? 'Produce Episode 1 first — you review it before locking'
                  : previewBusy
                    ? 'A revision is still producing…'
                    : 'Freeze this as the baseline recipe — the channel goes active'
              }
            >
              🔒 Lock as baseline
            </button>
          </div>
        </section>
      )}

      {boardQ.error && <div className="error-bar">{boardQ.error.message}</div>}

      {boardQ.loading && boardQ.data == null ? (
        <p className="dim">Loading…</p>
      ) : !item ? (
        <EmptyState
          message="Not a staged episode"
          hint="This item hasn’t been produced yet. Open it on the Calendar and hit “Produce”."
        />
      ) : (
        <>
          <StepSpine
            item={item}
            counts={counts}
            channel={channel}
            templates={templates}
            assets={brandAssets}
            accent={accent}
            isDirect={isDirect}
            incubating={incubating}
            busy={busy}
            schedule={schedule}
            onSchedule={setSchedule}
            planning={planning}
            planFailed={planFailed}
            canAssemble={canAssemble}
            assembleTitle={assembleTitle}
            assembleActive={assembleActive}
            canFinalize={canFinalize}
            finalizeTitle={finalizeTitle}
            finalizeActive={finalizeActive}
            previewDisabled={previewDisabled}
            previewTitle={previewTitle}
            onProduce={doPreview}
            onRebuildDraft={doPreview}
            onFinalize={doFinalize}
            onAssemble={() => setConfirmAssemble(true)}
          >
            {spineBody}
          </StepSpine>
        </>
      )}

      {confirmAssemble && (
        <ConfirmDialog
          title="Assemble the episode?"
          confirmLabel="Queue assembly"
          busy={busy === 'assemble'}
          onConfirm={doAssemble}
          onCancel={() => setConfirmAssemble(false)}
        >
          <p>
            This queues one <b>assemble_episode</b> job that stitches the {approvedCount}{' '}
            approved asset{approvedCount === 1 ? '' : 's'} into the final video and drafts the
            post. Skipped assets are left out.
          </p>
        </ConfirmDialog>
      )}

      {confirmLock && (
        <ConfirmDialog
          title="Lock this as the baseline?"
          confirmLabel="Lock baseline"
          busy={busy === 'lock'}
          onConfirm={doLock}
          onCancel={() => setConfirmLock(false)}
        >
          <p>
            This freezes Episode 1’s look and sound as{' '}
            <b>{channel ? channel.name : item?.channel_key}</b>’s canonical recipe — every future
            episode follows it. The channel flips from <b>incubating</b> to <b>active</b>, and
            producing/scheduling to YouTube unlocks.
          </p>
          <p className="dim small">
            You can still edit the blueprint later, but the incubation loop ends here.
          </p>
        </ConfirmDialog>
      )}

      {zoom && <Lightbox item={zoom} onClose={() => setZoom(null)} />}

      <Toast toast={toast} />
    </div>
  )
}
