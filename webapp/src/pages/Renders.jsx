import { useMemo, useState } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import Chips, { ChipSearch } from '../components/Chips'
import Lightbox from '../components/Lightbox'
import EmptyState from '../components/EmptyState'
import { resolveAccents, accentFor } from '../channelColor'
import { mediaKind } from '../mediaKind'
import { RENDERS_BASE } from '../config'
import { timeAgo } from '../format'

/**
 * Library — replacement for the flat renders dump (UX declutter redesign).
 * A media app, not a database: one hero with the single Play, one compact
 * search+type row, then channel shelves — latest pieces big, older folded.
 * Internals (paths, bytes, generators, origins) never render as text.
 */

const TYPE_OPTIONS = [
  { value: '', label: 'Everything' },
  { value: 'video', label: 'Videos' },
  { value: 'image', label: 'Images' },
  { value: 'audio', label: 'Audio' },
]

function displayTitle(r) {
  if (r.title) return r.title
  const base = (r.filename || (r.storage_path || '').split('/').pop() || 'Untitled')
    .replace(/\.[a-z0-9]+$/i, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return base ? base[0].toUpperCase() + base.slice(1) : 'Untitled'
}

const kindOf = (r) => mediaKind(r.kind, r.filename || r.storage_path || '')

function fmtDur(s) {
  const n = Number(s)
  if (!Number.isFinite(n) || n <= 0) return null
  const m = Math.floor(n / 60)
  return `${m}:${String(Math.round(n % 60)).padStart(2, '0')}`
}

function CardVisual({ r, kind, src }) {
  if (kind === 'video') return <video src={src} preload="metadata" muted playsInline />
  if (kind === 'image') return <img src={src} loading="lazy" alt="" />
  if (kind === 'audio')
    return (
      <div className="lib-audio" aria-hidden="true">
        <span className="lib-audio-glyph">♪</span>
      </div>
    )
  return (
    <div className="lib-audio" aria-hidden="true">
      <span className="lib-audio-glyph">▣</span>
    </div>
  )
}

function LibraryCard({ r, onOpen }) {
  const kind = kindOf(r)
  const src = RENDERS_BASE + (r.storage_path || '')
  const dur = fmtDur(r.duration_s)
  const title = displayTitle(r)
  return (
    <div className="lib-card">
      <button
        className="lib-card-hit"
        onClick={() => onOpen(r, kind, src, title)}
        aria-label={`${kind === 'image' ? 'View' : 'Play'} ${title}, made ${timeAgo(r.created_at)}`}
      >
        <span className="lib-visual">
          <CardVisual r={r} kind={kind} src={src} />
          {dur && (
            <span className="lib-pill lib-dur" title={`${Math.round(Number(r.duration_s))} seconds long`}>
              {dur}
            </span>
          )}
        </span>
        <span className="lib-caption">
          <span className="lib-title">{title}</span>
          <span className="lib-meta dim small">{timeAgo(r.created_at)}</span>
        </span>
      </button>
      {r.published_url && (
        <a
          className="lib-pill lib-yt"
          href={r.published_url}
          target="_blank"
          rel="noreferrer"
          title="Watch it on YouTube"
          onClick={(e) => e.stopPropagation()}
        >
          ▶ On YouTube
        </a>
      )}
    </div>
  )
}

export default function Renders() {
  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [expanded, setExpanded] = useState({}) // channel_key -> bool
  const [viewer, setViewer] = useState(null) // {src, kind, title}
  const [audio, setAudio] = useState(null) // {src, title}

  // 60s poll — the Library must not fossilize while Activity updates next door.
  const rendersQ = usePoll(() => api.get('?r=renders'), 60000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)

  const renders = (rendersQ.data && rendersQ.data.renders) || []
  const channels = (chansQ.data && chansQ.data.channels) || []
  const accents = useMemo(() => resolveAccents(channels), [channels])
  const chanName = useMemo(() => {
    const m = {}
    for (const c of channels) m[c.key] = c.name || c.key
    return m
  }, [channels])

  const q = search.trim().toLowerCase()
  const filtering = !!q || !!type
  const filtered = useMemo(() => {
    let list = renders
    if (type) list = list.filter((r) => kindOf(r) === type)
    if (q)
      list = list.filter((r) =>
        [r.title, r.filename, r.storage_path, r.generator, r.channel_key]
          .filter(Boolean).join(' ').toLowerCase().includes(q)
      )
    return list
  }, [renders, q, type])

  // Hero: newest video overall (else newest anything). Hidden while filtering.
  const hero = useMemo(() => {
    if (filtering || renders.length === 0) return null
    const sorted = [...renders].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    return sorted.find((r) => kindOf(r) === 'video') || sorted[0]
  }, [renders, filtering])

  // Channel shelves, most recently active first; unknown channels last.
  const shelves = useMemo(() => {
    const by = new Map()
    for (const r of filtered) {
      const k = r.channel_key || '_misc'
      if (!by.has(k)) by.set(k, [])
      by.get(k).push(r)
    }
    const out = [...by.entries()].map(([k, list]) => {
      list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      return { key: k, list, newest: list[0] ? new Date(list[0].created_at).getTime() : 0 }
    })
    out.sort((a, b) => (a.key === '_misc') - (b.key === '_misc') || b.newest - a.newest)
    return out
  }, [filtered])

  const open = (r, kind, src, title) => {
    if (kind === 'audio') setAudio({ src, title })
    else setViewer({ src, kind: kind === 'image' ? 'image' : 'video', title })
  }

  const loading = rendersQ.loading && rendersQ.data == null
  const heroKind = hero ? kindOf(hero) : null
  const heroSrc = hero ? RENDERS_BASE + (hero.storage_path || '') : null
  const heroTitle = hero ? displayTitle(hero) : ''

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Library</h1>
          <p className="sub">Everything the factory has finished — browse it like your own streaming app.</p>
        </div>
      </header>

      {rendersQ.error && <div className="error-bar">{rendersQ.error.message}</div>}

      {hero && (
        <section className="lib-hero card" style={{ '--ch': accentFor(hero.channel_key, accents) }}>
          <div className="lib-hero-media">
            {heroKind === 'video' ? (
              <video src={heroSrc} preload="metadata" muted playsInline />
            ) : heroKind === 'image' ? (
              <img src={heroSrc} alt="" />
            ) : (
              <div className="lib-audio lib-audio-hero"><span className="lib-audio-glyph">♪</span></div>
            )}
          </div>
          <div className="lib-hero-body">
            <span className="lib-eyebrow">Fresh off the line</span>
            <h2 className="lib-hero-title">{heroTitle}</h2>
            <p className="lib-hero-sub">
              Made for <span className="act-chan"><span className="act-chan-dot" style={{ background: accentFor(hero.channel_key, accents) }} />{chanName[hero.channel_key] || hero.channel_key}</span> · finished {timeAgo(hero.created_at)}.
            </p>
            <div className="lib-hero-actions">
              <button className="btn btn-primary" onClick={() => open(hero, heroKind, heroSrc, heroTitle)}>
                {heroKind === 'image' ? 'View' : '▶ Play'}
              </button>
              {hero.published_url && (
                <a className="link" href={hero.published_url} target="_blank" rel="noreferrer">
                  Already on YouTube ↗
                </a>
              )}
            </div>
          </div>
        </section>
      )}

      <div className="lib-controls">
        <ChipSearch value={search} onChange={setSearch} placeholder="Search your library…" />
        <Chips options={TYPE_OPTIONS} value={type} onChange={setType} ariaLabel="Type" />
      </div>

      {loading ? (
        <div className="lib-skeleton-shelf">
          {[0, 1, 2, 3].map((i) => <div key={i} className="lib-card lib-skeleton" />)}
        </div>
      ) : renders.length === 0 ? (
        <EmptyState
          message="Nothing on the shelves yet."
          hint="Finished videos, artwork and audio land here on their own as the factory finishes work."
        />
      ) : filtered.length === 0 ? (
        <EmptyState message={`Nothing matches “${search || TYPE_OPTIONS.find((t) => t.value === type)?.label}”.`} hint="Try a different word, or clear the filters." />
      ) : (
        shelves.map(({ key, list }) => {
          const isOpen = !!expanded[key]
          const shown = isOpen ? list : list.slice(0, 4)
          const name = key === '_misc' ? 'Everything else' : chanName[key] || key
          const accent = key === '_misc' ? 'var(--neutral)' : accentFor(key, accents)
          return (
            <section key={key} className="lib-shelf" style={{ '--ch': accent }}>
              <div className="lib-shelf-head">
                <span className="act-chan-dot" style={{ background: accent }} />
                <h2 className="lib-shelf-name">{name}</h2>
                <span className="dim small">
                  {list.length} finished piece{list.length === 1 ? '' : 's'} · newest {timeAgo(list[0].created_at)}
                </span>
                {list.length > 4 && (
                  <button className="btn btn-ghost btn-sm lib-showall" onClick={() => setExpanded((s) => ({ ...s, [key]: !isOpen }))}>
                    {isOpen ? 'Show the latest 4' : `Show all ${list.length}`}
                  </button>
                )}
              </div>
              <div className={'lib-grid' + (isOpen ? ' dense' : '')}>
                {shown.map((r) => (
                  <LibraryCard key={r.id || r.storage_path} r={r} onOpen={open} />
                ))}
              </div>
            </section>
          )
        })
      )}

      {viewer && <Lightbox item={viewer} onClose={() => setViewer(null)} />}
      {audio && (
        <div className="lib-audio-bar card" role="region" aria-label="Now playing">
          <span className="lib-title">{audio.title}</span>
          <audio src={audio.src} controls autoPlay style={{ flex: 1 }} />
          <button className="icon-btn" onClick={() => setAudio(null)} aria-label="Close player">✕</button>
        </div>
      )}
    </div>
  )
}
