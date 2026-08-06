import { useEffect, useMemo, useState } from 'react'
import { RENDERS_BASE } from '../config'
import { fileExt, extBadge } from '../mediaKind'
import { renderMdLite, escapeHtml } from '../mdlite'

// Module caches: fetched text per storage_path, expand preference per asset_key.
const textCache = new Map()
const expandPref = new Map()

const CLIP_LINES = 28
const CLIP_SLACK = 6 // only offer the toggle when meaningfully longer than the clip

/** Pretty-print + colorize JSON. Escapes FIRST, spans after. null = unparseable. */
function jsonHtml(raw) {
  let pretty
  try {
    pretty = JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return null
  }
  return escapeHtml(pretty).replace(
    /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b/g,
    (m, str, colon, kw) => {
      if (str) return colon ? `<span class="tp-key">${str}</span>${colon}` : `<span class="tp-str">${str}</span>`
      if (kw) return `<span class="tp-bool">${kw}</span>`
      return `<span class="tp-num">${m}</span>`
    }
  )
}

/**
 * Stage preview for text assets (.md / .json / .txt / anything text):
 * fetches the document from storage, renders the review_note cheat-sheet as
 * a "What to check" callout, and clips long docs behind a Show-all toggle.
 */
export default function TextPreview({ asset, reviewNote }) {
  const path = asset.storage_path || ''
  const url = RENDERS_BASE + path
  const filename = asset.filename || path.split('/').pop() || asset.asset_key
  const ext = fileExt(filename)
  const note = reviewNote != null ? reviewNote : asset.review_note

  const [state, setState] = useState(() => textCache.get(path) || null) // null | {text} | {error}
  const [expanded, setExpanded] = useState(() => expandPref.get(asset.asset_key) === true)

  useEffect(() => {
    let alive = true
    const cached = textCache.get(path)
    if (cached) {
      setState(cached)
    } else {
      setState(null)
      fetch(url)
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`)
          return r.text()
        })
        .then((text) => {
          const entry = { text }
          textCache.set(path, entry) // errors are NOT cached, so a remount retries
          if (alive) setState(entry)
        })
        .catch(() => {
          if (alive) setState({ error: true })
        })
    }
    return () => {
      alive = false
    }
  }, [path, url])

  const text = state && !state.error ? state.text : null
  const lines = text == null ? 0 : text.split('\n').length
  const clippable = lines > CLIP_LINES + CLIP_SLACK
  const clipped = clippable && !expanded

  const rendered = useMemo(() => {
    if (text == null) return null
    if (ext === 'md' || ext === 'markdown') return { kind: 'md', html: renderMdLite(text) }
    if (ext === 'json') {
      const html = jsonHtml(text)
      if (html) return { kind: 'json', html }
    }
    return { kind: 'plain' }
  }, [text, ext])

  const toggle = () => {
    const next = !expanded
    expandPref.set(asset.asset_key, next)
    setExpanded(next)
  }

  return (
    <div className="text-stage">
      {note && String(note).trim() !== '' && (
        <div className="review-note">
          <div className="review-note-head">What to check</div>
          <div className="mdlite" dangerouslySetInnerHTML={{ __html: renderMdLite(note) }} />
        </div>
      )}

      <div className="tp-head">
        <span className="tp-file">{filename}</span>
        {lines > 0 && <span className="tp-lines">{lines} lines</span>}
      </div>

      {state == null ? (
        <div className="tp-shimmer" aria-label="Loading document">
          <span />
          <span />
          <span />
        </div>
      ) : state.error ? (
        <div className="tp-error">
          <span>Could not load the document.</span>
          <a className="tag" href={url} target="_blank" rel="noreferrer" download={filename}>
            {extBadge(filename) || 'FILE'} · download
          </a>
        </div>
      ) : (
        <>
          <div className={'tp-body' + (clipped ? ' tp-clip' : '')}>
            {rendered.kind === 'md' ? (
              <div className="mdlite" dangerouslySetInnerHTML={{ __html: rendered.html }} />
            ) : rendered.kind === 'json' ? (
              <pre className="tp-pre tp-json" dangerouslySetInnerHTML={{ __html: rendered.html }} />
            ) : (
              <pre className="tp-pre">{text}</pre>
            )}
          </div>
          {clippable && (
            <button type="button" className="tp-toggle" onClick={toggle}>
              {expanded ? 'Collapse' : `Show all (${lines} lines)`}
            </button>
          )}
        </>
      )}
    </div>
  )
}
