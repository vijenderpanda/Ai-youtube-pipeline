import { useState } from 'react'
import { RENDERS_BASE } from '../config'
import { fmtBytes, timeAgo, fmtDate } from '../format'
import { mediaKind, extBadge } from '../mediaKind'
import Lightbox from './Lightbox'

const NoteIcon = (
  <svg
    width="26"
    height="26"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M9 18V5l12-2v13" />
    <circle cx="6" cy="18" r="3" />
    <circle cx="18" cy="16" r="3" />
  </svg>
)

/** Deterministic waveform-ish bars seeded from the filename. */
function Wave({ seed }) {
  let h = 2166136261
  for (let i = 0; i < seed.length; i++) h = ((h ^ seed.charCodeAt(i)) * 16777619) >>> 0
  const bars = []
  for (let i = 0; i < 28; i++) {
    h = (h * 1664525 + 1013904223) >>> 0
    bars.push(20 + (h % 1000) / 1000 * 80)
  }
  return (
    <div className="audio-wave" aria-hidden="true">
      {bars.map((b, i) => (
        <span key={i} style={{ height: `${Math.round(b)}%` }} />
      ))}
    </div>
  )
}

export default function RenderCard({ render }) {
  const [lightbox, setLightbox] = useState(false)
  const src = RENDERS_BASE + (render.storage_path || '')
  const filename =
    render.filename || (render.storage_path || '').split('/').pop() || 'render'
  const title = render.title || filename
  const size = fmtBytes(render.size_bytes != null ? render.size_bytes : render.size)
  const historical = render.origin === 'historical'
  const kind = mediaKind(render.kind, filename)
  const ext = extBadge(filename)

  let media
  if (kind === 'video') {
    media = <video controls preload="metadata" src={src} />
  } else if (kind === 'image') {
    media = (
      <button
        type="button"
        className="render-img-btn"
        onClick={() => setLightbox(true)}
        title="Open full size"
      >
        <img className="render-img" src={src} alt={title} loading="lazy" />
      </button>
    )
  } else if (kind === 'audio') {
    media = (
      <div className="audio-body">
        <span className="audio-note">{NoteIcon}</span>
        <Wave seed={filename} />
        <audio controls preload="none" src={src} />
      </div>
    )
  } else {
    media = (
      <div className="other-body">
        <span className="other-ext">{ext || 'FILE'}</span>
        <a className="btn btn-ghost btn-sm" href={src} download={filename}>
          Download
        </a>
      </div>
    )
  }

  return (
    <div className="card render-card">
      <div className="render-thumb">
        {media}
        {ext && <span className="ext-badge">{ext}</span>}
        {historical && <span className="archive-badge">archive</span>}
      </div>
      <div className="render-meta">
        <div className="render-name" title={title}>
          {title}
        </div>
        <div className="render-sub">
          {render.generator && (
            <span className="tag gen-tag" title={`generator: ${render.generator}`}>
              {render.generator}
            </span>
          )}
          <span className="tag">{render.channel_key || render.channel || '—'}</span>
          {size && <span>{size}</span>}
          <span title={fmtDate(render.created_at)}>{timeAgo(render.created_at)}</span>
        </div>
      </div>
      {lightbox && (
        <Lightbox item={{ src, kind: 'image', title }} onClose={() => setLightbox(false)} />
      )}
    </div>
  )
}
