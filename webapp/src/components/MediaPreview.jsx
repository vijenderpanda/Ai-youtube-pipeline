import { useCallback, useEffect, useRef, useState } from 'react'
import { RENDERS_BASE } from '../config'
import { SLOTS, isImagePath } from '../assetCatalog'
import { mediaKind } from '../mediaKind'

/**
 * MediaPreview — the one place a brand-asset revision becomes AUDIBLE / WATCHABLE.
 *
 * The composer used to show a still thumbnail and ask you to pick. You cannot
 * hear a music bed from a waveform glyph, and you cannot judge an outro sting
 * from its poster frame. So every slot row, every swap-picker tile and every
 * library card now carries a real player.
 *
 * Source resolution (deliberately keyed off the REAL file, not the declared
 * SLOT kind — an outro_sting's thumb_path is a .png poster, which would make a
 * naive kind lookup call the whole slot an image):
 *
 *   storage_path ends .mp3/.wav/… → 'audio'   play/pause + waveform
 *   storage_path ends .mp4/.mov/… → 'video'   poster + ▶, swaps to inline <video>
 *   else meta.sample_path         → 'sample'  same inline video, badged SAMPLE,
 *                                             because the mp4 is what the
 *                                             component RENDERS, not the asset
 *   else a decodable image path   → 'image'   plain still
 *   else                          → 'none'    waveform / glyph placeholder
 *
 * Nothing ever autoplays: playback always starts from a click. Only ONE element
 * plays at a time page-wide (see the stage registry below).
 */

/* ── Single-player registry ────────────────────────────────────────────────
 * Module-level, so it spans every MediaPreview mounted on the page. Taking the
 * stage pauses whoever held it; the loser's own `pause` event flips its button
 * back to ▶, so the UI stays honest without any cross-component wiring. */
let ON_STAGE = null

function takeStage(el) {
  if (ON_STAGE && ON_STAGE !== el) {
    try { ON_STAGE.pause() } catch (_) { /* detached element */ }
  }
  ON_STAGE = el
}

function leaveStage(el) {
  if (ON_STAGE === el) ON_STAGE = null
}

export const DEFAULT_SAMPLE_NOTE = 'Sample output — a finished short this renders into'

const BARS_SM = [8, 15, 21, 11, 19, 7]
const BARS_LG = [9, 17, 25, 13, 22, 8, 19, 27, 12, 7, 20, 15]

const fmtT = (s) => {
  if (!isFinite(s) || s < 0) return '0:00'
  const m = Math.floor(s / 60)
  const r = Math.floor(s % 60)
  return m + ':' + (r < 10 ? '0' : '') + r
}

/**
 * What can we actually play for this revision?
 * → { mode, path, poster, note, glyph }
 */
export function previewSourceFor(assetType, v) {
  const declared = (SLOTS[assetType] && SLOTS[assetType].kind) || 'other'
  const glyph =
    declared === 'video' ? '▶' : declared === 'image' ? '🖼' : declared === 'audio' ? 'wave' : '{ }'
  if (!v) return { mode: 'none', glyph }

  const poster = (isImagePath(v.thumb_path) && v.thumb_path) || null
  const store = mediaKind('', v.storage_path || '')
  if (v.storage_path && store === 'audio') {
    return { mode: 'audio', path: v.storage_path, poster, glyph }
  }
  if (v.storage_path && store === 'video') {
    return { mode: 'video', path: v.storage_path, poster, glyph }
  }

  // Non-media slots (remotion_comp, step_chip_style, component_*) can't be
  // played — but the short they produced can.
  const meta = (v && v.meta) || {}
  if (meta.sample_path) {
    return {
      mode: 'sample',
      path: meta.sample_path,
      poster: (isImagePath(meta.sample_thumb) && meta.sample_thumb) || poster,
      note: meta.sample_note || DEFAULT_SAMPLE_NOTE,
      glyph,
    }
  }

  const img = poster || (isImagePath(v.storage_path) && v.storage_path) || null
  if (img) return { mode: 'image', path: img, glyph }
  return { mode: 'none', glyph }
}

/** True when this revision can actually be heard or watched. */
export function hasPreview(assetType, v) {
  const m = previewSourceFor(assetType, v).mode
  return m === 'audio' || m === 'video' || m === 'sample'
}

/** The sample caption for a non-media revision ('' when it has no sample). */
export function sampleNoteOf(v) {
  const meta = (v && v.meta) || {}
  return meta.sample_path ? meta.sample_note || DEFAULT_SAMPLE_NOTE : ''
}

/**
 * @param assetType  slot key (drives the glyph fallback only)
 * @param version    a factory_asset_versions row
 * @param size       'row' (slot rows) | 'tile' (pickers/strips) | 'cover' (16:9 band)
 * @param className  the container class the host layout already sizes
 * @param name       accessible name for the play buttons
 */
export default function MediaPreview({
  assetType,
  version,
  size = 'row',
  className = '',
  name = 'this revision',
}) {
  const src = previewSourceFor(assetType, version)
  const mediaRef = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [live, setLive] = useState(false) // poster swapped for a real <video>
  const [t, setT] = useState(0)
  const [dur, setDur] = useState(0)

  // A callback ref is the only detach signal we can trust: it fires with null
  // on unmount AND when the poster⇄video swap tears the element down, so a
  // playing clip can never outlive its card or squat on the stage.
  const setMediaEl = useCallback((el) => {
    const prev = mediaRef.current
    if (!el && prev) {
      try { prev.pause() } catch (_) { /* already gone */ }
      leaveStage(prev)
    }
    mediaRef.current = el
  }, [])

  // Swapping the revision under us resets the player.
  const vid = version && version.id
  useEffect(() => {
    setLive(false)
    setPlaying(false)
    setT(0)
    setDur(0)
  }, [vid])

  // First click mounts the <video>; play it once it exists.
  useEffect(() => {
    if (!live) return
    const el = mediaRef.current
    if (!el) return
    takeStage(el)
    const p = el.play()
    if (p && p.catch) p.catch(() => { /* the controls are right there */ })
  }, [live])

  const swallow = (e) => e.stopPropagation()

  const toggleAudio = (e) => {
    e.preventDefault()
    e.stopPropagation()
    const el = mediaRef.current
    if (!el) return
    if (el.paused) {
      takeStage(el)
      const p = el.play()
      if (p && p.catch) p.catch(() => setPlaying(false))
    } else {
      el.pause()
    }
  }

  const openVideo = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setLive(true)
  }

  const closeVideo = (e) => {
    e.preventDefault()
    e.stopPropagation()
    const el = mediaRef.current
    if (el) {
      try { el.pause() } catch (_) { /* noop */ }
    }
    setLive(false)
  }

  const mediaEvents = {
    onPlay: () => {
      if (mediaRef.current) takeStage(mediaRef.current)
      setPlaying(true)
    },
    onPause: () => setPlaying(false),
    onEnded: () => setPlaying(false),
    onTimeUpdate: (e) => setT(e.currentTarget.currentTime || 0),
    onLoadedMetadata: (e) =>
      setDur(isFinite(e.currentTarget.duration) ? e.currentTarget.duration : 0),
    onClick: swallow,
  }

  const cls = [
    'media-prev',
    'media-prev-' + size,
    'media-prev-' + src.mode,
    live ? 'media-prev-live' : '',
    playing ? 'media-prev-playing' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  /* ── audio: compact transport + the existing waveform bars ─────────────── */
  if (src.mode === 'audio') {
    const bars = size === 'row' ? BARS_SM : BARS_LG
    // The whole player area toggles playback — and, crucially, swallows the
    // click, so auditioning a bed inside the swap picker never selects it.
    // The inner <button> stops propagation first, so this never double-fires.
    return (
      <div className={cls} onKeyDown={swallow} onClick={toggleAudio}>
        <button
          type="button"
          className="btn-ghost media-prev-play"
          aria-label={(playing ? 'Pause ' : 'Play ') + name}
          aria-pressed={playing}
          onClick={toggleAudio}
        >
          <span aria-hidden="true">{playing ? '⏸' : '▶'}</span>
        </button>
        <span className={'asset-wave' + (playing ? ' asset-wave-live' : '')} aria-hidden="true">
          {bars.map((h, i) => (
            <i key={i} style={{ height: h }} />
          ))}
        </span>
        {dur > 0 && (
          <span className="media-prev-time mono">
            {fmtT(t)} / {fmtT(dur)}
          </span>
        )}
        <audio ref={setMediaEl} src={RENDERS_BASE + src.path} preload="none" {...mediaEvents} />
      </div>
    )
  }

  /* ── video + sample: poster → inline <video> in the same box ───────────── */
  if (src.mode === 'video' || src.mode === 'sample') {
    const isSample = src.mode === 'sample'
    const posterUrl = src.poster ? RENDERS_BASE + src.poster : undefined
    const label = isSample ? 'Play the sample output for ' + name : 'Play ' + name
    return (
      <div className={cls} onKeyDown={swallow} title={isSample ? src.note : undefined}>
        {live ? (
          <>
            <video
              ref={setMediaEl}
              src={RENDERS_BASE + src.path}
              poster={posterUrl}
              preload="none"
              playsInline
              controls
              {...mediaEvents}
            />
            <button
              type="button"
              className="media-prev-stop"
              aria-label={'Close the preview of ' + name}
              onClick={closeVideo}
            >
              <span aria-hidden="true">✕</span>
            </button>
          </>
        ) : (
          <button type="button" className="media-prev-thumb" aria-label={label} onClick={openVideo}>
            {posterUrl ? (
              <img src={posterUrl} alt="" loading="lazy" />
            ) : (
              <span className="studio-cover-glyph" aria-hidden="true">
                ▶
              </span>
            )}
            <span className="media-prev-badge" aria-hidden="true">
              ▶
            </span>
          </button>
        )}
        {isSample && (
          <span className="media-prev-tag" aria-hidden="true">
            SAMPLE
          </span>
        )}
      </div>
    )
  }

  /* ── still image ───────────────────────────────────────────────────────── */
  if (src.mode === 'image') {
    return (
      <div className={cls}>
        <img src={RENDERS_BASE + src.path} alt="" loading="lazy" />
      </div>
    )
  }

  /* ── nothing playable and nothing to show ──────────────────────────────── */
  return (
    <div className={cls}>
      {src.glyph === 'wave' ? (
        <span className="asset-wave" aria-hidden="true">
          {(size === 'row' ? BARS_SM : BARS_LG).map((h, i) => (
            <i key={i} style={{ height: h }} />
          ))}
        </span>
      ) : (
        <span className="studio-cover-glyph" aria-hidden="true">
          {src.glyph}
        </span>
      )}
    </div>
  )
}
