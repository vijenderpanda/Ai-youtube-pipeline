import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { RENDERS_BASE } from '../config'
import Chips, { ChipSearch, ChipsGroup } from '../components/Chips'
import EmptyState from '../components/EmptyState'
import Lightbox from '../components/Lightbox'

// Fixed category set, in display order. 'uncategorized' always last.
const CATEGORIES = [
  ['recording', 'Recording'],
  ['framing-styles', 'Framing & Styles'],
  ['assembly', 'Assembly'],
  ['audio-voice', 'Audio & Voice'],
  ['captions-lyrics', 'Captions & Lyrics'],
  ['art-thumbnails', 'Art & Thumbnails'],
  ['publishing', 'Publishing'],
  ['automation-infra', 'Automation & Infra'],
  ['channel-tools', 'Channel Tools'],
  ['uncategorized', 'Uncategorized'],
]
const KNOWN = new Set(CATEGORIES.map(([key]) => key))

/** jsonb columns can arrive as arrays or serialized strings — normalize. */
function asArray(v) {
  if (Array.isArray(v)) return v
  if (typeof v === 'string' && v.trim()) {
    try {
      const p = JSON.parse(v)
      return Array.isArray(p) ? p : []
    } catch {
      return []
    }
  }
  return []
}

/** v4 scope field: network | multi | single:<channel_key> | unknown */
function scopeInfo(scope) {
  const s = String(scope || 'unknown')
  if (s === 'network') return { key: 'network', label: 'Network-wide' }
  if (s === 'multi') return { key: 'multi', label: 'Multi-channel' }
  if (s.startsWith('single:')) {
    return { key: 'single', label: `${s.slice(7)} only`, channel: s.slice(7) }
  }
  return { key: 'unknown', label: null }
}

const IMAGE_RE = /\.(png|jpe?g|webp|gif|avif)$/i

function renderKind(r) {
  if (r.kind === 'image' || r.kind === 'video') return r.kind
  return IMAGE_RE.test(r.storage_path || '') ? 'image' : 'video'
}

function SampleThumb({ render, role, onOpen }) {
  const src = RENDERS_BASE + (render.storage_path || '')
  const kind = renderKind(render)
  const title = render.title || (render.storage_path || '').split('/').pop()
  return (
    <div className="sample-item">
      <button
        type="button"
        className="sample-thumb"
        title={title}
        onClick={() => onOpen({ src, kind, title })}
      >
        {kind === 'image' ? (
          <img src={src} alt={title} loading="lazy" />
        ) : (
          <video src={src} preload="metadata" muted playsInline />
        )}
        {title && <span className="sample-thumb-title">{title}</span>}
      </button>
      {role && <div className="sample-cap">{role}</div>}
    </div>
  )
}

function GeneratorCard({ gen, catKey, onImprove, onOpenSample }) {
  const [open, setOpen] = useState(false)
  const [samples, setSamples] = useState(null) // null = not loaded
  const [impact, setImpact] = useState(null) // { count, channels } | null
  const inputs = asArray(gen.inputs)
  const outputs = asArray(gen.outputs)
  const channels = asArray(gen.channels)
  const tags = asArray(gen.tags)
  const legacySamples = asArray(gen.samples).filter((s) => s && s.storage_path)
  const what = gen.what_it_does || gen.description || ''
  const scope = scopeInfo(gen.scope)

  // Lazy-load impact + recent contributed outputs the first time the card opens.
  useEffect(() => {
    if (!open || samples !== null) return
    setSamples([])
    api
      .get(`?r=generator_samples&name=${encodeURIComponent(gen.name)}`)
      .then((d) => setSamples((d.samples || []).filter((s) => s && s.render && s.render.storage_path)))
      .catch(() => setSamples([]))
    api
      .get(`?r=renders&generator=${encodeURIComponent(gen.name)}`)
      .then((d) => {
        const rs = d.renders || []
        setImpact({
          count: rs.length,
          channels: new Set(rs.map((r) => r.channel_key).filter(Boolean)).size,
        })
      })
      .catch(() => {})
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  const shown = samples && samples.length > 0
    ? samples
    : legacySamples.map((s) => ({ render: s, role: null }))

  return (
    <div className={'card gen-card-v3' + (open ? ' open' : '')}>
      <div
        className="gen-head"
        role="button"
        tabIndex={0}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setOpen((o) => !o)
          }
        }}
      >
        <div className="gen-head-main">
          <div className="gen-name-row">
            <span className="gen-name mono">{gen.name}</span>
            {scope.label && (
              <span className={`scope-badge scope-${scope.key}`}>{scope.label}</span>
            )}
          </div>
          {what && <div className="gen-what">{what}</div>}
          {tags.length > 0 && (
            <div className="gen-tags">
              {tags.map((t, i) => (
                <span className="tag dim-tag" key={i}>
                  {String(t)}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="gen-head-side">
          <button
            className="btn btn-ghost btn-sm"
            onClick={(e) => {
              e.stopPropagation()
              onImprove(gen, catKey)
            }}
          >
            ⚡ Improve
          </button>
          <span className="gen-caret" aria-hidden>
            ▾
          </span>
        </div>
      </div>

      {open && (
        <div className="gen-body">
          {gen.path && <div className="gen-path mono">{gen.path}</div>}

          {impact && (
            <div className="impact-line">
              {impact.count === 0 ? (
                'No tracked renders yet'
              ) : (
                <>
                  Contributed to <b>{impact.count >= 100 ? '100+' : impact.count}</b>{' '}
                  {impact.count === 1 ? 'render' : 'renders'}
                  {impact.channels > 0 && (
                    <>
                      {' '}
                      across <b>{impact.channels}</b>{' '}
                      {impact.channels === 1 ? 'channel' : 'channels'}
                    </>
                  )}
                </>
              )}
            </div>
          )}

          <div className="gen-io">
            <div className="gen-io-col">
              <h4>Inputs</h4>
              {inputs.length === 0 ? (
                <p className="dim small">None listed</p>
              ) : (
                <ul>
                  {inputs.map((it, i) => (
                    <li key={i}>{String(it)}</li>
                  ))}
                </ul>
              )}
            </div>
            <div className="gen-io-col">
              <h4>Outputs</h4>
              {outputs.length === 0 ? (
                <p className="dim small">None listed</p>
              ) : (
                <ul>
                  {outputs.map((it, i) => (
                    <li key={i}>{String(it)}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {channels.length > 0 && (
            <div className="gen-channels">
              {channels.map((c, i) => (
                <span className="tag" key={i}>
                  {String(c)}
                </span>
              ))}
            </div>
          )}

          {shown.length > 0 && (
            <div className="gen-samples-section">
              <h4>Recent outputs</h4>
              <div className="gen-samples">
                {shown.slice(0, 3).map((s, i) => (
                  <SampleThumb
                    key={(s.render && s.render.id) || i}
                    render={s.render}
                    role={s.role}
                    onOpen={onOpenSample}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Generators() {
  const { data, error, loading } = usePoll(() => api.get('?r=generators'), 0)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const navigate = useNavigate()
  const [lightbox, setLightbox] = useState(null)
  const [cat, setCat] = useState('')
  const [channel, setChannel] = useState('')
  const [scope, setScope] = useState('')
  const [search, setSearch] = useState('')

  const generators = (data && data.generators) || []
  const channels = (chansQ.data && chansQ.data.channels) || []

  const improve = (g, catKey) => {
    navigate('/jobs', {
      state: {
        newJob: {
          type: 'custom',
          model: 'fable',
          effort: 'xhigh',
          title: `Improve ${g.name}`,
          prompt: `Improve scripts/${g.name} (${catKey}): <describe what to change based on the samples above>. Follow docs/PRODUCTION-PLAYBOOK.md; verify output quality frame-by-frame like the existing style scripts do.`,
        },
      },
    })
  }

  const catOf = (g) => {
    const raw = (g.category || 'uncategorized').toLowerCase()
    return KNOWN.has(raw) ? raw : 'uncategorized'
  }

  const matchesChannel = (g, key) => {
    if (!key) return true
    const s = scopeInfo(g.scope)
    if (s.channel === key) return true
    return asArray(g.channels).map(String).includes(key)
  }

  const q = search.trim().toLowerCase()
  const matchesSearch = (g) => {
    if (!q) return true
    const hay = [
      g.name,
      g.what_it_does,
      g.description,
      g.path,
      ...asArray(g.tags).map(String),
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return hay.includes(q)
  }

  const filtered = generators.filter(
    (g) =>
      (!cat || catOf(g) === cat) &&
      (!scope || scopeInfo(g.scope).key === scope) &&
      matchesChannel(g, channel) &&
      matchesSearch(g)
  )

  const catCounts = useMemo(() => {
    const m = {}
    for (const g of generators) m[catOf(g)] = (m[catOf(g)] || 0) + 1
    return m
  }, [generators]) // eslint-disable-line react-hooks/exhaustive-deps

  const catOptions = [
    { value: '', label: 'All', count: generators.length },
    ...CATEGORIES.filter(([key]) => catCounts[key]).map(([key, label]) => ({
      value: key,
      label,
      count: catCounts[key],
    })),
  ]

  const scopeOptions = [
    { value: '', label: 'All' },
    { value: 'network', label: 'Network-wide' },
    { value: 'multi', label: 'Multi-channel' },
    { value: 'single', label: 'Single-channel' },
  ]

  const channelOptions = [
    { value: '', label: 'All channels' },
    ...channels.map((c) => ({ value: c.key, label: c.name || c.key })),
  ]

  // Group filtered generators by category.
  const byCat = {}
  for (const g of filtered) {
    const key = catOf(g)
    ;(byCat[key] = byCat[key] || []).push(g)
  }
  const sections = CATEGORIES.filter(([key]) => (byCat[key] || []).length > 0)

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Generators</h1>
          <p className="sub">The scripts that build the content — your map of what to improve next</p>
        </div>
      </header>

      {error && <div className="error-bar">{error.message}</div>}

      <div className="chips-bar">
        <ChipsGroup label="Category">
          <Chips options={catOptions} value={cat} onChange={setCat} ariaLabel="Category" />
        </ChipsGroup>
        <ChipsGroup label="Scope">
          <Chips options={scopeOptions} value={scope} onChange={setScope} ariaLabel="Scope" />
        </ChipsGroup>
        <ChipsGroup label="Channel">
          <Chips
            options={channelOptions}
            value={channel}
            onChange={setChannel}
            ariaLabel="Channel"
          />
        </ChipsGroup>
        <ChipSearch value={search} onChange={setSearch} placeholder="Search generators…" />
      </div>

      {loading && data == null ? (
        <p className="dim">Loading…</p>
      ) : generators.length === 0 ? (
        <EmptyState message="No generators registered" hint="Generators appear once the pipeline registers them." />
      ) : filtered.length === 0 ? (
        <EmptyState message="No generators match these filters" />
      ) : (
        sections.map(([key, label]) => (
          <section key={key}>
            <div className="gen-section">
              <span className="gen-section-label">{label}</span>
              <span className="gen-section-count">{byCat[key].length}</span>
              <span className="gen-section-line" />
            </div>
            <div className="gen-list">
              {byCat[key].map((g, i) => (
                <GeneratorCard
                  key={g.id || g.name || i}
                  gen={g}
                  catKey={key}
                  onImprove={improve}
                  onOpenSample={setLightbox}
                />
              ))}
            </div>
          </section>
        ))
      )}

      {lightbox && <Lightbox item={lightbox} onClose={() => setLightbox(null)} />}
    </div>
  )
}
