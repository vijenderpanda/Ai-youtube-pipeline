import { Component, Suspense, lazy, useEffect, useMemo, useState } from 'react'

// S4 · deliverable #2 — client-side live preview. Lazy chunk: the preview pulls
// in remotion + @remotion/player (heavy), so it loads only when the designer
// opens it; the rest of the app is unaffected. The vite alias + React dedupe
// (webapp/vite.config.js) make importing the real Short.tsx composition safe.
const LivePreview = lazy(() => import('./LivePreview'))

// A preview failure (bad block config, a bundling hiccup) must never take down
// the designer — isolate it to a small inline notice.
class PreviewBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { err: null }
  }
  static getDerivedStateFromError(err) {
    return { err }
  }
  render() {
    if (this.state.err) {
      return (
        <div className="dim small" style={{ padding: '14px 0', textAlign: 'center' }}>
          Preview unavailable — {String((this.state.err && this.state.err.message) || this.state.err)}
        </div>
      )
    }
    return this.props.children
  }
}

/* =============================================================================
   SequenceEditor — the composition designer's SEQUENCE section (Sprint 3).

   The second half of a template version (the first being its CAST): the ordered
   list of typed blocks that play, each with a LAYOUT + config. Edited on a DRAFT
   one block at a time (set/delete_template_version_block); FROZEN into
   composition._sequence at lock, which build_ep_v2 turns into Short segments.
   Cookbook + layout + block-type vocabularies come live from ?r=cookbook, so
   this UI and the server validator share one source.

   The row position IS the storage key (UNIQUE(version, position)); set_… is an
   upsert-by-position, so reordering = rewriting the CONTENT at two positions
   (a clean swap), never "move a row".
   ========================================================================== */

/* layout slot geometry (mirrors remotion-studio/src/layouts.ts) for the frame
   diagrams. Rects are fractions of the 9:16 frame. */
const LAYOUT_GEO = {
  'full-broll': { broll: [0, 0, 1, 1], tag: [0.06, 0.06, 0.34, 0.05] },
  'host-top': { host: [0.06, 0.05, 0.88, 0.34], broll: [0.06, 0.42, 0.88, 0.42] },
  'host-bottom': { broll: [0.06, 0.05, 0.88, 0.44], host: [0.06, 0.52, 0.88, 0.42] },
  split: { host: [0.05, 0.28, 0.43, 0.44], broll: [0.52, 0.28, 0.43, 0.44] },
  'host-pip': { broll: [0, 0, 1, 1], host: [0.55, 0.62, 0.4, 0.3] },
  framed: { host: [0.08, 0.13, 0.84, 0.5] },
}
const SLOT_COLOR = { host: 'rgba(233,30,99,.62)', broll: 'rgba(94,198,214,.5)', caption: 'rgba(228,197,107,.85)', tag: 'rgba(164,136,224,.85)' }
function LayoutFrame({ id, w = 30, h = 50 }) {
  const geo = LAYOUT_GEO[id]
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ display: 'block', borderRadius: 4, background: '#0c0a0f' }}>
      {geo && Object.entries(geo).map(([slot, r]) => (
        <rect key={slot} x={r[0] * w} y={r[1] * h} width={r[2] * w} height={r[3] * h} rx={2} fill={SLOT_COLOR[slot] || '#333'} />
      ))}
    </svg>
  )
}

const DEFAULT_CONFIG = {
  broll: { cookbook: { id: 'LineReveal', props: {} }, dur: 5 },
  host: { host: { id: '', lines: [] }, dur: 5 },
  hook: { lines: [], until: 3, dur: 3 },
  statbars: { title: '', bars: [], dur: 5 },
  outro: { question: '', dur: 5 },
  cards: { dur: 5 },
  slot: { layout: 'host-top', host: {}, broll: { kind: 'cookbook', id: 'LineReveal', props: {} }, dur: 5 },
}

const cookbookIdOfCfg = (cfg) => {
  const c = cfg || {}
  if (c.cookbook) return c.cookbook.id || null
  if (c.broll && c.broll.kind === 'cookbook') return c.broll.id || null
  return null
}
function blockSummary(b) {
  const c = b.config || {}
  if (b.block_type === 'broll' && c.cookbook) return 'cookbook ' + c.cookbook.id
  if (b.block_type === 'slot' && c.broll) return (b.layout || 'slot') + ' · ' + (c.broll.id || c.broll.kind || 'fill')
  if (b.block_type === 'host') return 'host ' + ((c.host && c.host.id) || '(cast)')
  if (b.block_type === 'statbars') return c.title || 'chart'
  if (b.block_type === 'outro') return c.question || 'CTA'
  if (b.block_type === 'hook') return (c.lines && c.lines[0]) || 'hook'
  return b.block_type
}
const LBL = { fontSize: 11, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-3)', fontWeight: 700 }

export default function SequenceEditor({ versionId, isDraft, blocks, cookbook = [], layouts = [], blockTypes = [], busy, onPost }) {
  const [openPos, setOpenPos] = useState(null)
  const [buf, setBuf] = useState('') // JSON config buffer for the open block
  const [cfgErr, setCfgErr] = useState('')
  const [preview, setPreview] = useState(false) // S4: live structural preview
  // S6 (Sprint 5) semi-auto compose: paste a script, pickCookbook picks per line.
  const [autoOpen, setAutoOpen] = useState(false)
  const [autoScript, setAutoScript] = useState('')
  const [autoBusy, setAutoBusy] = useState('')
  // D2: cookbook options RANKED for the open scene's line (mock's ranked picker).
  const [ranked, setRanked] = useState([])

  const sorted = useMemo(() => [...(blocks || [])].sort((a, b) => a.position - b.position), [blocks])

  // upsert the CONTENT at a position (position is the key).
  const put = (position, block_type, layout, config, tag, after) =>
    onPost(
      { action: 'set_template_version_block', template_version_id: versionId, position, block_type, layout, cookbook_id: cookbookIdOfCfg(config), config },
      tag,
      after,
    )

  const addBlock = () => {
    const pos = sorted.length ? Math.max(...sorted.map((b) => b.position)) + 1 : 0
    put(pos, 'broll', 'full-broll', DEFAULT_CONFIG.broll, 'block:add', () => open({ position: pos, config: DEFAULT_CONFIG.broll }))
  }
  const del = (pos) => onPost({ action: 'delete_template_version_block', template_version_id: versionId, position: pos }, 'block:del:' + pos)

  // swap the content at two adjacent positions.
  const move = (pos, dir) => {
    const i = sorted.findIndex((b) => b.position === pos)
    const j = i + dir
    if (j < 0 || j >= sorted.length) return
    const a = sorted[i]
    const b = sorted[j]
    put(a.position, b.block_type, b.layout, b.config, 'block:mv', () => put(b.position, a.block_type, a.layout, a.config, 'block:mv'))
  }

  const open = (b) => {
    setOpenPos(b.position)
    setBuf(JSON.stringify(b.config || {}, null, 2))
    setCfgErr('')
  }
  const parseBuf = (fallback) => {
    try {
      return JSON.parse(buf || '{}')
    } catch (e) {
      return fallback
    }
  }
  // layout is an independent column — keep the unsaved config buffer as-is.
  const setLayout = (b, lid) => put(b.position, b.block_type, lid, parseBuf(b.config), 'block:set:' + b.position)
  // changing type resets to that type's default config and re-syncs the buffer.
  const setType = (b, type) => {
    const cfg = DEFAULT_CONFIG[type] || {}
    setBuf(JSON.stringify(cfg, null, 2))
    setCfgErr('')
    put(b.position, type, b.layout, cfg, 'block:set:' + b.position)
  }
  // cookbook pick edits the LOCAL buffer only (committed on Save config).
  const pickCookbook = (b, id) => {
    const cfg = parseBuf(b.config || {})
    if (b.block_type === 'slot') cfg.broll = { kind: 'cookbook', id, props: (cfg.broll && cfg.broll.props) || {} }
    else cfg.cookbook = { id, props: (cfg.cookbook && cfg.cookbook.props) || {} }
    setBuf(JSON.stringify(cfg, null, 2))
    setCfgErr('')
  }
  const saveConfig = (b) => {
    let parsed
    try {
      parsed = JSON.parse(buf || '{}')
    } catch (e) {
      setCfgErr('Not valid JSON — ' + (e.message || 'check the syntax'))
      return
    }
    setCfgErr('')
    put(b.position, b.block_type, b.layout, parsed, 'block:set:' + b.position)
  }

  // S6 semi-auto compose: one script line = one scene. pickCookbook (the SAME
  // ranker registry.ts/build_ep_v2 use — lazy-imported so it and the demo props
  // stay out of the main bundle) chooses the best-fit visual per line; each block
  // is seeded with that component's demo props so the sequence renders immediately,
  // then the operator refines. Stamps sequence_mode='replace' (this IS the short).
  const STOP = new Set('the a an to of and or in on for it is you your with that this my our we i me just can could what if get got are be by as at so'.split(' '))
  const kwOf = (line) => (line.toLowerCase().match(/[a-z0-9']+/g) || []).filter((w) => w.length > 2 && !STOP.has(w))
  const beatOf = (i, n) => (i === 0 ? 'hook' : i === n - 1 ? 'cta' : i === 1 ? 'context' : 'demo')

  const autoCompose = async () => {
    const lines = autoScript.split('\n').map((l) => l.trim()).filter(Boolean)
    if (!lines.length || autoBusy) return
    setAutoBusy('compose')
    try {
      const [{ pickCookbook }, demosMod] = await Promise.all([
        import('@remotion-src/cookbook/registry'),
        import('@remotion-src/cookbook/demos').catch(() => ({ COOKBOOK_DEMOS: {} })),
      ])
      const demos = demosMod.COOKBOOK_DEMOS || {}
      const existing = sorted.map((b) => b.position)
      for (let i = 0; i < lines.length; i++) {
        const [top] = pickCookbook({ beat: beatOf(i, lines.length), keywords: kwOf(lines[i]) }, 1)
        if (!top) continue
        const id = top.entry.id
        const confidence = Math.min(1, Math.round((top.score / 8) * 100) / 100)
        await put(i, 'broll', 'full-broll', { cookbook: { id, props: demos[id] || {} }, line: lines[i], confidence }, 'auto:' + i)
      }
      for (const pos of existing.filter((p) => p >= lines.length)) {
        await onPost({ action: 'delete_template_version_block', template_version_id: versionId, position: pos }, 'auto:del:' + pos)
      }
      await onPost({ action: 'set_template_version_setting', template_version_id: versionId, name: 'sequence_mode', value: 'replace' }, 'auto:mode')
      setAutoOpen(false)
      setAutoScript('')
    } finally {
      setAutoBusy('')
    }
  }

  // D2: rank the cookbook for the open scene's line (reuses the auto-compose
  // ranker, lazy-loaded). Empty when there's no line — the plain list shows then.
  useEffect(() => {
    const b = sorted.find((x) => x.position === openPos)
    const line = b && b.config && b.config.line
    if (!b || !line || (b.block_type !== 'broll' && b.block_type !== 'slot')) { setRanked([]); return }
    let ok = true
    import('@remotion-src/cookbook/registry')
      .then(({ pickCookbook }) => {
        if (!ok) return
        setRanked(
          pickCookbook({ keywords: kwOf(line) }, 6).map((s) => ({
            id: s.entry.id, title: s.entry.title, role: s.entry.role, needs: s.entry.needs,
            score: s.score, why: (s.why || []).slice(0, 3).join(' · '),
          })),
        )
      })
      .catch(() => setRanked([]))
    return () => { ok = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openPos])

  return (
    <section className="card" aria-labelledby="seq-title" style={{ marginTop: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div>
          <h2 id="seq-title" style={{ margin: 0, fontSize: 16 }}>Sequence</h2>
          <div style={{ fontSize: 12.5, color: 'var(--text-2)', marginTop: 2 }}>
            The ordered scenes that play — each a layout + config. Frozen into the composition at lock.
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            type="button"
            className={preview ? 'btn-primary' : 'btn-ghost'}
            style={{ padding: '5px 12px' }}
            disabled={!sorted.length}
            onClick={() => setPreview((v) => !v)}
            title={sorted.length ? 'Play this sequence live in the browser — free, no render' : 'Add a block to preview'}
          >
            {preview ? '▣ Hide preview' : '▷ Preview'}
          </button>
          <span className="chip">{sorted.length} scene{sorted.length === 1 ? '' : 's'}</span>
        </div>
      </div>

      {preview && sorted.length > 0 && (
        <PreviewBoundary>
          <Suspense fallback={<div className="dim small" style={{ padding: '18px 0', textAlign: 'center' }}>Loading preview…</div>}>
            <LivePreview blocks={sorted} />
          </Suspense>
        </PreviewBoundary>
      )}

      {!sorted.length && (
        <div style={{ color: 'var(--text-3)', fontSize: 13, padding: '10px 0' }}>
          No scenes yet. {isDraft ? 'Add one to start designing the composition.' : 'This version has no sequence.'}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {sorted.map((b, i) => {
          const isOpen = openPos === b.position
          return (
            <div key={b.position} style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'var(--panel-2)', overflow: 'hidden' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '30px 34px 1fr auto', gap: 11, alignItems: 'center', padding: '10px 12px' }}>
                <span style={{ fontFamily: 'var(--mono, monospace)', fontSize: 12, color: 'var(--text-3)', textAlign: 'center' }}>{String(i).padStart(2, '0')}</span>
                <LayoutFrame id={b.layout} />
                <button type="button" onClick={() => (isOpen ? setOpenPos(null) : open(b))} style={{ textAlign: 'left', background: 'none', border: 0, color: 'inherit', cursor: 'pointer', minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--accent-hi)', fontWeight: 700 }}>{b.block_type}</span>
                    <span>{b.layout || '—'}</span>
                    {b.config && typeof b.config.confidence === 'number' && (
                      <span
                        title="Auto-compose fit for this scene"
                        style={{ marginLeft: 'auto', fontSize: 10.5, fontFamily: 'var(--mono, monospace)', fontWeight: 600, letterSpacing: '.02em', padding: '2px 7px', borderRadius: 999, border: '1px solid var(--border-strong)', color: b.config.confidence < 0.5 ? '#e0a84a' : 'var(--ok, #5cc08a)' }}
                      >
                        {Math.round(b.config.confidence * 100)}% fit
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-2)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{blockSummary(b)}</div>
                  {b.config && b.config.line && (
                    <div style={{ fontSize: 12, color: 'var(--text-3)', fontStyle: 'italic', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: 1 }}>
                      “{b.config.line}”
                    </div>
                  )}
                </button>
                {isDraft && (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button type="button" className="btn-ghost" style={{ padding: '4px 8px' }} disabled={i === 0 || !!busy} onClick={() => move(b.position, -1)} aria-label="Move up">▲</button>
                    <button type="button" className="btn-ghost" style={{ padding: '4px 8px' }} disabled={i === sorted.length - 1 || !!busy} onClick={() => move(b.position, 1)} aria-label="Move down">▼</button>
                    <button type="button" className="btn-ghost" style={{ padding: '4px 8px' }} disabled={!!busy} onClick={() => del(b.position)} aria-label="Delete block">✕</button>
                  </div>
                )}
              </div>

              {isOpen && (
                <div style={{ borderTop: '1px solid var(--border-soft)', padding: 14, display: 'flex', flexDirection: 'column', gap: 14, background: 'var(--panel)' }}>
                  <div>
                    <label style={LBL}>Block type</label>
                    <select className="input" disabled={!isDraft || !!busy} value={b.block_type} onChange={(e) => setType(b, e.target.value)} style={{ marginTop: 6 }}>
                      {blockTypes.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>

                  <div>
                    <label style={LBL}>Layout</label>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
                      {layouts.map((lid) => (
                        <button key={lid} type="button" disabled={!isDraft || !!busy} onClick={() => setLayout(b, lid)} title={lid}
                          style={{ background: 'none', border: b.layout === lid ? '1px solid var(--accent)' : '1px solid var(--border)', borderRadius: 8, padding: 4, cursor: isDraft ? 'pointer' : 'default', boxShadow: b.layout === lid ? '0 0 0 1px var(--accent) inset' : 'none' }}>
                          <LayoutFrame id={lid} w={34} h={56} />
                          <div style={{ fontSize: 9.5, color: b.layout === lid ? 'var(--text)' : 'var(--text-3)', marginTop: 3 }}>{lid}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {(b.block_type === 'broll' || b.block_type === 'slot') && (
                    <div>
                      <label style={LBL}>Cookbook component{b.config && b.config.line ? ' · ranked for this line' : ''}</label>
                      {ranked.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8, maxHeight: 280, overflowY: 'auto' }}>
                          {ranked.map((r) => {
                            const sel = cookbookIdOfCfg(parseBuf(b.config)) === r.id
                            return (
                              <button key={r.id} type="button" disabled={!isDraft || !!busy} onClick={() => pickCookbook(b, r.id)}
                                style={{ textAlign: 'left', background: sel ? 'var(--accent-soft)' : 'var(--input, #101116)', border: sel ? '1px solid var(--accent)' : '1px solid var(--border)', borderRadius: 8, padding: '8px 10px', cursor: isDraft ? 'pointer' : 'default', display: 'flex', alignItems: 'center', gap: 10 }}>
                                <div style={{ minWidth: 0, flex: 1 }}>
                                  <div style={{ fontSize: 12.5, fontWeight: 700 }}>{r.id}<span style={{ color: 'var(--text-3)', fontWeight: 400, marginLeft: 7 }}>{r.title}</span></div>
                                  <div style={{ fontSize: 10.5, color: 'var(--text-3)', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    <span style={{ color: 'var(--cyan, #5ec6d6)' }}>{r.role}</span> · needs {r.needs}{r.why ? ' · ' + r.why : ''}
                                  </div>
                                </div>
                                <span style={{ fontFamily: 'var(--mono, monospace)', fontSize: 12, fontWeight: 700, color: sel ? 'var(--accent-hi)' : 'var(--text-2)' }}>{r.score}</span>
                              </button>
                            )
                          })}
                        </div>
                      ) : (
                        <select className="input" disabled={!isDraft || !!busy} value={cookbookIdOfCfg(parseBuf(b.config)) || ''} onChange={(e) => pickCookbook(b, e.target.value)} style={{ marginTop: 6 }}>
                          <option value="">— pick —</option>
                          {cookbook.map((c) => <option key={c.id} value={c.id}>{c.id} — {c.label} ({c.needs})</option>)}
                        </select>
                      )}
                    </div>
                  )}

                  <div>
                    <label style={LBL}>Config (JSON)</label>
                    <textarea className="input" disabled={!isDraft || !!busy} value={buf} onChange={(e) => { setBuf(e.target.value); if (cfgErr) setCfgErr('') }} spellCheck={false}
                      style={{ marginTop: 6, minHeight: 120, fontFamily: 'var(--mono, monospace)', fontSize: 12.5, lineHeight: 1.5, resize: 'vertical' }} />
                    {cfgErr && <div style={{ color: 'var(--dead, #d1706a)', fontSize: 12, marginTop: 6 }}>{cfgErr}</div>}
                    {isDraft && (
                      <button type="button" className="btn-primary" style={{ marginTop: 8 }} disabled={!!busy} onClick={() => saveConfig(b)}>Save config</button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {isDraft && (
        <>
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            <button type="button" className="btn-ghost" style={{ flex: 1, borderStyle: 'dashed' }} disabled={!!busy} onClick={addBlock}>
              ＋ Add scene
            </button>
            <button
              type="button"
              className={autoOpen ? 'btn-primary' : 'btn-ghost'}
              style={autoOpen ? undefined : { borderStyle: 'dashed' }}
              disabled={!!busy}
              onClick={() => setAutoOpen((v) => !v)}
              title="Turn a script into a composed sequence — pickCookbook chooses a best-fit visual per line"
            >
              ✨ Auto-compose
            </button>
          </div>
          {autoOpen && (
            <div className="card" style={{ marginTop: 10 }}>
              <div className="field-label">Script — one line per scene</div>
              <textarea
                rows={6}
                value={autoScript}
                onChange={(e) => setAutoScript(e.target.value)}
                placeholder={'What if one line could build your whole app?\nWatch the agent plan every step ahead.\nIt shipped in twelve seconds.'}
                style={{ width: '100%', marginTop: 6, fontSize: 13 }}
              />
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn-primary"
                  disabled={!!autoBusy || !autoScript.trim()}
                  onClick={autoCompose}
                >
                  {autoBusy
                    ? 'Composing…'
                    : `Compose ${autoScript.split('\n').map((l) => l.trim()).filter(Boolean).length} scene(s) →`}
                </button>
                <span className="dim small">
                  Each line becomes one scene with a best-fit visual (seeded with sample content), and this sequence becomes the whole short. Refine each scene below, then lock.
                </span>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  )
}
