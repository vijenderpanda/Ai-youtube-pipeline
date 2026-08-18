import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { RENDERS_BASE } from '../config'
import { usePoll } from '../hooks'
import {
  resolveAccents,
  accentFor,
  channelEmoji,
  channelMonogram,
} from '../channelColor'
import { templateForChannel, armable } from '../templates'
import {
  assetLabel,
  wiringOf,
  kindOf,
  isImagePath,
  heygenHealth,
} from '../assetCatalog'
import EmptyState from '../components/EmptyState'
import Toast, { useToast } from '../components/Toast'

/**
 * TemplateDetail — one factory_templates row.
 *
 * Two halves, and the difference between them is the whole point:
 *   1. "Frames & cosmetics" — what the CHANNEL LOCKS say production uses today
 *      (factory_asset_locks, the layer build_ep_v2 has always read).
 *   2. "Cast" (Phase 4) — composed template VERSIONS. A template names the
 *      PIPELINE; a version names the CAST that pipeline runs with. You fork a
 *      draft (seeded from what production runs today), swap individual slots,
 *      eyeball the picks side by side, then LOCK — and locking freezes each
 *      pick's build_ref into the version, which is what the renderer resolves.
 *
 * There is deliberately no "generate preview" here: the preview is the chosen
 * revisions shown together. Rendering a sample would spend HeyGen/ElevenLabs
 * credits to tell you what the thumbnails already show.
 */

const WIRING_LABEL = {
  live: 'Live in render',
  locked: 'Locked · wiring next',
  reference: 'Reference',
}

// Walk parent_version_id → "v3 ← v2 ← v1" (guards against cycles / missing parents).
function lineageOf(v, byId) {
  const chain = []
  const seen = new Set()
  let cur = v
  while (cur && !seen.has(cur.id)) {
    seen.add(cur.id)
    chain.push('v' + cur.version)
    cur = cur.parent_version_id ? byId[cur.parent_version_id] : null
  }
  return chain.join(' ← ')
}

/** Thumb for one revision — an <img> only for a path an <img> can decode. */
function SlotThumb({ type, v }) {
  const kind = kindOf(type, v)
  const path =
    (isImagePath(v && v.thumb_path) && v.thumb_path) ||
    (isImagePath(v && v.storage_path) && v.storage_path) ||
    null
  if (path) return <img src={RENDERS_BASE + path} alt="" loading="lazy" />
  if (kind === 'audio') {
    return (
      <span className="asset-wave" aria-hidden="true">
        {[9, 17, 25, 13, 22, 8, 19, 27].map((h, i) => (
          <i key={i} style={{ height: h }} />
        ))}
      </span>
    )
  }
  return (
    <span className="studio-cover-glyph" aria-hidden="true">
      {kind === 'video' ? '▶' : kind === 'image' ? '🖼' : '{ }'}
    </span>
  )
}

export default function TemplateDetail() {
  const { key } = useParams()
  const tplQ = usePoll(() => api.get('?r=templates'), 20000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  // Fetch all asset versions once and filter to this channel client-side (only
  // claude-tricks has rows today) — mirrors Assets.jsx and sidesteps the
  // conditional-hook problem of a channel we only learn about after load.
  const assetsQ = usePoll(() => api.get('?r=assets'), 20000)
  // Phase 4: composed casts for THIS template (versions + their slot rows).
  const tvQ = usePoll(
    () => api.get('?r=template_versions&template_key=' + encodeURIComponent(key)),
    0,
  )
  const { toast, show } = useToast()
  const [selId, setSelId] = useState(null)   // version the composer is showing
  const [swapFor, setSwapFor] = useState(null) // asset_type whose picker is open
  const [showAllSlots, setShowAllSlots] = useState(false)
  const [busy, setBusy] = useState(null)

  const templates = (tplQ.data && tplQ.data.templates) || []
  const channels = (chansQ.data && chansQ.data.channels) || []
  const versions = (assetsQ.data && assetsQ.data.versions) || []
  const locks = (assetsQ.data && assetsQ.data.locks) || []
  const castVersions = (tvQ.data && tvQ.data.versions) || []
  const castSlots = (tvQ.data && tvQ.data.assets) || []
  const castJoined = (tvQ.data && tvQ.data.asset_versions) || []

  const tpl = templates.find((t) => t.key === key) || null
  const chan = tpl ? templateForChannel(channels, tpl.key) : null
  const channelKey = chan ? chan.key : null

  const accents = useMemo(() => resolveAccents(channels), [channels])
  const accent = channelKey ? accentFor(channelKey, accents) : null
  const emoji = channelKey ? channelEmoji(channelKey) : null

  // Lock row per asset_type for this template's channel.
  const lockByType = useMemo(() => {
    const m = {}
    if (!channelKey) return m
    for (const l of locks) if (l.channel_key === channelKey) m[l.asset_type] = l
    return m
  }, [locks, channelKey])

  // Group this channel's versions by asset_type (API orders version desc).
  const groups = useMemo(() => {
    if (!channelKey) return []
    const mine = versions.filter((v) => v.channel_key === channelKey)
    const byType = new Map()
    for (const v of mine) {
      if (!byType.has(v.asset_type)) byType.set(v.asset_type, [])
      byType.get(v.asset_type).push(v)
    }
    return [...byType.entries()]
      .map(([type, vers]) => ({ type, vers }))
      .sort((a, b) => a.type.localeCompare(b.type))
  }, [versions, channelKey])

  // Every revision we can draw, keyed by id — the board's own list plus the
  // rows the composer endpoint joined in (a cast may point at a revision the
  // channel filter above dropped).
  const revById = useMemo(() => {
    const m = {}
    for (const v of castJoined) m[v.id] = v
    for (const v of versions) m[v.id] = v
    return m
  }, [versions, castJoined])

  // Which composed version the composer is showing: explicit pick → the
  // template's active cast → the newest draft → the newest version.
  const selected = useMemo(() => {
    if (!castVersions.length) return null
    return (
      castVersions.find((v) => v.id === selId) ||
      (tpl && castVersions.find((v) => v.id === tpl.active_version_id)) ||
      castVersions.find((v) => v.status === 'draft') ||
      castVersions[0]
    )
  }, [castVersions, selId, tpl])

  // Slot rows of the selected version → { [asset_type]: {pick, alts:[]} }.
  const castByType = useMemo(() => {
    const m = {}
    if (!selected) return m
    for (const s of castSlots) {
      if (s.template_version_id !== selected.id) continue
      if (!m[s.asset_type]) m[s.asset_type] = { pick: null, alts: [] }
      if (s.position === 0) m[s.asset_type].pick = s
      else m[s.asset_type].alts.push(s)
    }
    return m
  }, [castSlots, selected])

  // Rows to show: everything the renderer consumes (live/locked wiring) plus
  // anything this cast already composes. "Show every slot" reveals the rest.
  const slotRows = useMemo(() => {
    const all = groups.map((g) => g.type)
    if (showAllSlots) return all
    const keep = new Set(all.filter((t) => wiringOf(t) !== 'reference'))
    for (const t of Object.keys(castByType)) keep.add(t)
    return all.filter((t) => keep.has(t))
  }, [groups, castByType, showAllSlots])

  // The frozen composition of a locked version (build_refs copied at lock).
  const frozen = (selected && selected.composition) || {}

  const isDraft = !!selected && selected.status === 'draft'
  const isActive = !!(tpl && selected && tpl.active_version_id === selected.id)

  // Position-0 picks, in row order — the side-by-side strip AND the lock guard.
  const chosen = useMemo(() => {
    const out = []
    for (const type of slotRows) {
      const slot = castByType[type]
      if (!slot || !slot.pick) continue
      const rev = revById[slot.pick.asset_version_id] || null
      out.push({ type, rev, health: heygenHealth(rev) })
    }
    return out
  }, [slotRows, castByType, revById])

  const deadPicks = chosen.filter((c) => c.health.dead)
  const missingRev = chosen.filter((c) => !c.rev)

  const post = async (bodyObj, tag, after) => {
    setBusy(tag)
    try {
      const res = await api.post(bodyObj)
      await tvQ.refresh()
      await tplQ.refresh()
      if (after) after(res)
    } catch (e) {
      show(e.message || 'That did not work')
    } finally {
      setBusy(null)
    }
  }

  // Fork: from the active cast if there is one, else from the version on screen,
  // else a fresh draft seeded from the channel's live locks (create_template_version
  // does the seeding — a new draft starts as exactly what production runs today).
  const fork = () => {
    const from =
      (tpl && tpl.active_version_id) || (selected && selected.id) || null
    post(
      {
        action: 'create_template_version',
        template_key: key,
        ...(channelKey ? { channel_key: channelKey } : {}),
        ...(from ? { from_version_id: from } : { seed_from_locks: true }),
      },
      'fork',
      (res) => {
        if (res && res.version) setSelId(res.version.id)
        setSwapFor(null)
      },
    )
  }

  const swapTo = (asset_type, asset_version_id) =>
    post(
      {
        action: 'set_template_version_asset',
        template_version_id: selected.id,
        asset_type,
        asset_version_id,
        position: 0,
      },
      'swap:' + asset_type,
      () => setSwapFor(null),
    )

  const lockCast = () =>
    post(
      { action: 'lock_template_version', template_version_id: selected.id, make_active: true },
      'lock',
    )

  const retireCast = (id) =>
    post({ action: 'retire_template_version', template_version_id: id }, 'retire:' + id, () =>
      setSelId(null),
    )

  // Still loading the template row.
  if (tplQ.loading && tplQ.data == null) {
    return (
      <div className="page">
        <header className="page-head">
          <div>
            <div className="crumbs">
              <Link className="link" to="/studio/templates">Templates</Link>{' '}
              <span className="dim">/</span> <span className="mono">{key}</span>
            </div>
            <h1>Loading…</h1>
          </div>
        </header>
      </div>
    )
  }

  if (!tpl) {
    return (
      <div className="page">
        <header className="page-head">
          <div>
            <div className="crumbs">
              <Link className="link" to="/studio/templates">Templates</Link>{' '}
              <span className="dim">/</span> <span className="mono">{key}</span>
            </div>
            <h1>Template not found</h1>
          </div>
        </header>
        <EmptyState
          message={`No template with key “${key}”`}
          hint="It may have been renamed or removed from factory_templates."
        />
      </div>
    )
  }

  const arm = armable(tpl)
  const uiTag = tpl.produce_ui && tpl.produce_ui.tag
  const hasFrames = groups.length > 0

  return (
    <div className="page" style={accent ? { '--ch': accent } : undefined}>
      <header className="page-head">
        <div>
          <div className="crumbs">
            <Link className="link" to="/studio/templates">Templates</Link>{' '}
            <span className="dim">/</span> <span className="mono">{tpl.key}</span>
          </div>
          <h1>{tpl.name || tpl.key}</h1>
          <p className="sub">
            {tpl.aspect} · {tpl.runtime_s}s
            {tpl.description ? ' · ' + tpl.description : ''}
          </p>
          <div className="tpl-head-meta">
            {arm ? (
              <span className="chip tpl-armable">Ready to arm</span>
            ) : (
              <span className="chip tpl-starter">Starter — can’t arm yet</span>
            )}
            {tpl.blueprint_source && (
              <span className="dim small mono">{tpl.blueprint_source}</span>
            )}
          </div>
        </div>
      </header>

      {assetsQ.error && <div className="error-bar">{assetsQ.error.message}</div>}

      <div className="tpl-section-title">Frames &amp; cosmetics</div>

      {hasFrames ? (
        <div className="tpl-frames">
          {groups.map(({ type, vers }) => {
            const byId = {}
            for (const v of vers) byId[v.id] = v
            const lock = lockByType[type]
            const locked =
              (lock && lock.locked_version_id && byId[lock.locked_version_id]) ||
              vers.find((v) => v.status === 'locked') ||
              null
            const head = locked || vers[0]
            const wiring = wiringOf(type)
            const kind = kindOf(type, head)
            const lineage = head ? lineageOf(head, byId) : ''
            // an <img> can't decode an .mp3 — only ever point it at a real image
            const imgPath =
              (isImagePath(head && head.thumb_path) && head.thumb_path) ||
              (isImagePath(head && head.storage_path) && head.storage_path) ||
              null
            return (
              <div key={type} className="card frame-tile" style={accent ? { '--ch': accent } : undefined}>
                {hasCover(kind) && (
                  <div className="studio-cover">
                    {imgPath ? (
                      <img src={RENDERS_BASE + imgPath} alt="" loading="lazy" />
                    ) : kind === 'audio' ? (
                      <span className="asset-wave" aria-hidden="true">
                        {[9, 17, 25, 13, 22, 8, 19, 27, 12, 7, 20, 15].map((h, i) => (
                          <i key={i} style={{ height: h }} />
                        ))}
                      </span>
                    ) : (
                      <span className="studio-cover-glyph" aria-hidden="true">
                        {kind === 'video' ? '▶' : '🖼'}
                      </span>
                    )}
                    <span className="studio-cover-chan">
                      <span className="studio-cover-dot" />
                      {assetLabel(type)}
                    </span>
                    {locked && (
                      <span className="studio-cover-live">🔒 v{locked.version}</span>
                    )}
                  </div>
                )}
                <div className="studio-card-body">
                  <div className="studio-card-title frame-title">{assetLabel(type)}</div>
                  <div className="studio-card-sub">
                    {locked && <span className="dim small">v{locked.version}</span>}
                    <span className={'chip frame-wiring frame-wiring-' + wiring}>
                      {WIRING_LABEL[wiring]}
                    </span>
                    <span className="dim small">
                      {vers.length} rev{vers.length > 1 ? 's' : ''}
                    </span>
                  </div>
                  {lineage && <div className="asset-lineage">{lineage}</div>}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="card tpl-blueprint">
          {tpl.blueprint_source && (
            <div className="tpl-blueprint-src">
              <span className="dim small">Blueprint</span>
              <span className="mono">{tpl.blueprint_source}</span>
            </div>
          )}
          {uiTag && <span className="chip">{uiTag}</span>}
          <p className="dim small">
            Frame previews arrive once this channel’s assets are registered.
          </p>
        </div>
      )}

      {/* ── Cast (Phase 4): composed template versions ───────────────── */}
      <div className="tpl-section-title">Cast — the revisions this recipe renders with</div>
      {tvQ.error && <div className="error-bar">{tvQ.error.message}</div>}

      <div className="card cast-card">
        <div className="cast-head">
          <div className="cast-head-copy">
            <div className="cast-head-title">
              {castVersions.length === 0
                ? 'No composed cast yet'
                : `${castVersions.length} version${castVersions.length > 1 ? 's' : ''}`}
            </div>
            <p className="dim small cast-head-sub">
              {castVersions.length === 0
                ? 'Production resolves each slot from the channel locks above. Fork a recipe to mix and match revisions without touching those locks.'
                : 'A locked version is what production renders. Drafts are private scratch — the build ignores them.'}
            </p>
          </div>
          <button
            type="button"
            className="btn-primary"
            disabled={busy === 'fork' || !channelKey}
            onClick={fork}
            title={
              channelKey
                ? 'Copy the current cast into a new draft you can edit'
                : 'No channel produces with this template yet'
            }
          >
            {busy === 'fork' ? 'Forking…' : 'Fork this recipe'}
          </button>
        </div>

        {castVersions.length > 0 && (
          <div className="cast-rail">
            {castVersions.map((v) => {
              const act = tpl.active_version_id === v.id
              return (
                <button
                  key={v.id}
                  type="button"
                  className={
                    'chip cast-ver-chip' +
                    (selected && selected.id === v.id ? ' cast-sel' : '') +
                    (v.status === 'locked' ? ' cast-locked' : ' cast-draft')
                  }
                  onClick={() => {
                    setSelId(v.id)
                    setSwapFor(null)
                  }}
                  title={(v.label || 'no label') + ' · ' + v.status}
                >
                  v{v.version}
                  <span className="cast-chip-tag">
                    {act ? 'ACTIVE' : v.status === 'locked' ? 'locked' : 'draft'}
                  </span>
                </button>
              )
            })}
          </div>
        )}

        {selected && (
          <>
            <div className="cast-status">
              <span className={'chip cast-state-' + selected.status}>
                {selected.status === 'locked' ? '🔒 Locked' : '✎ Draft'}
              </span>
              {isActive && <span className="chip cast-active">Active — production renders this</span>}
              {selected.label && <span className="dim small">{selected.label}</span>}
              <span className="dim small mono">
                {chosen.length} slot{chosen.length === 1 ? '' : 's'} composed
              </span>
            </div>

            {/* Side-by-side preview: the picks together, so the combo is
                eyeballable. Not a render — no credits are spent here. */}
            {chosen.length > 0 && (
              <div className="cast-strip">
                {chosen.map(({ type, rev, health }) => (
                  <div
                    key={type}
                    className={'cast-strip-tile' + (health.dead ? ' cast-dead' : '')}
                  >
                    <div className="cast-strip-cover">
                      <SlotThumb type={type} v={rev} />
                    </div>
                    <div className="cast-strip-label">{assetLabel(type)}</div>
                    <div className="dim small">
                      {rev ? 'v' + rev.version : 'missing revision'}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="cast-slots">
              {slotRows.map((type) => {
                const slot = castByType[type]
                const pick = slot && slot.pick
                const rev = pick ? revById[pick.asset_version_id] : null
                const health = heygenHealth(rev)
                const wiring = wiringOf(type)
                const froz = frozen[type]
                const opts = (groups.find((g) => g.type === type) || { vers: [] }).vers
                const open = swapFor === type
                return (
                  <div key={type} className={'cast-slot' + (open ? ' cast-slot-open' : '')}>
                    <div className="cast-slot-row">
                      <div className="cast-slot-cover">
                        {rev ? (
                          <SlotThumb type={type} v={rev} />
                        ) : (
                          <span className="studio-cover-glyph" aria-hidden="true">·</span>
                        )}
                      </div>
                      <div className="cast-slot-copy">
                        <div className="cast-slot-title">
                          {assetLabel(type)}
                          <span className={'chip frame-wiring frame-wiring-' + wiring}>
                            {WIRING_LABEL[wiring]}
                          </span>
                        </div>
                        <div className="cast-slot-sub">
                          {rev ? (
                            <>
                              <b>v{rev.version}</b>
                              <span className="dim small">{rev.label || assetLabel(type)}</span>
                            </>
                          ) : pick ? (
                            <span className="dim small">picked revision is missing</span>
                          ) : (
                            <span className="dim small">not in this cast</span>
                          )}
                          {health.dead && (
                            <span className="chip cast-warn-dead">{health.reason}</span>
                          )}
                          {!health.dead && health.warn && (
                            <span className="chip cast-warn">{health.warn}</span>
                          )}
                        </div>
                        {froz && froz.build_ref && (
                          <div className="asset-buildref mono">{froz.build_ref}</div>
                        )}
                      </div>
                      {isDraft ? (
                        <button
                          type="button"
                          className="btn-ghost cast-swap-btn"
                          onClick={() => setSwapFor(open ? null : type)}
                          disabled={busy === 'swap:' + type}
                        >
                          {busy === 'swap:' + type ? '…' : open ? 'Close' : 'Swap'}
                        </button>
                      ) : (
                        <span className="dim small cast-frozen-tag">frozen</span>
                      )}
                    </div>

                    {open && (
                      <div className="cast-picker">
                        {opts.length === 0 && (
                          <span className="dim small">No revisions registered for this slot.</span>
                        )}
                        {opts.map((o) => {
                          const h = heygenHealth(o)
                          const retired = o.status === 'retired'
                          const noRef = !(o.meta && o.meta.build_ref)
                          const isPick = pick && pick.asset_version_id === o.id
                          const blocked = h.dead || retired || noRef
                          const why = h.dead
                            ? h.reason
                            : retired
                              ? 'Retired revision'
                              : noRef
                                ? 'No build_ref — the build cannot resolve it'
                                : h.warn || 'Use this revision'
                          return (
                            <button
                              key={o.id}
                              type="button"
                              className={
                                'cast-opt' +
                                (isPick ? ' cast-opt-current' : '') +
                                (blocked ? ' cast-opt-dead' : '')
                              }
                              disabled={blocked || isPick || busy === 'swap:' + type}
                              title={why}
                              onClick={() => swapTo(type, o.id)}
                            >
                              <span className="cast-opt-cover">
                                <SlotThumb type={type} v={o} />
                              </span>
                              <span className="cast-opt-meta">
                                <b>v{o.version}</b>
                                <span className="dim small">{o.label || assetLabel(type)}</span>
                                {blocked && <span className="cast-opt-why">{why}</span>}
                                {isPick && !blocked && <span className="cast-opt-why">current pick</span>}
                              </span>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
              {groups.length > slotRows.length || showAllSlots ? (
                <button
                  type="button"
                  className="chip asset-more cast-show-all"
                  onClick={() => setShowAllSlots((s) => !s)}
                >
                  {showAllSlots
                    ? 'show only slots the renderer uses'
                    : `+${groups.length - slotRows.length} reference slots`}
                </button>
              ) : null}
            </div>

            <div className="cast-foot">
              <div className="cast-foot-copy">
                {isDraft ? (
                  <p className="dim small">
                    Locking freezes each pick’s build reference into this version and makes it the
                    cast production renders with. Locked versions never change — to alter the cast,
                    fork again.
                  </p>
                ) : (
                  <p className="dim small">
                    Locked {selected.locked_at ? 'and frozen' : ''} — this is a permanent snapshot.
                    Fork it to change a slot.
                  </p>
                )}
                {isDraft && deadPicks.length > 0 && (
                  <p className="cast-block">
                    {deadPicks.map((d) => assetLabel(d.type)).join(', ')} points at a freed HeyGen
                    id — swap it before locking.
                  </p>
                )}
                {isDraft && missingRev.length > 0 && (
                  <p className="cast-block">
                    {missingRev.map((d) => assetLabel(d.type)).join(', ')} points at a revision that
                    no longer exists — re-pick it.
                  </p>
                )}
              </div>
              <div className="cast-foot-actions">
                {!isActive && (
                  <button
                    type="button"
                    className="btn-ghost"
                    disabled={busy === 'retire:' + selected.id}
                    onClick={() => retireCast(selected.id)}
                    title="Shelve this version — it stays readable but stops being offered"
                  >
                    Retire
                  </button>
                )}
                {isDraft && (
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={
                      busy === 'lock' ||
                      chosen.length === 0 ||
                      deadPicks.length > 0 ||
                      missingRev.length > 0
                    }
                    onClick={lockCast}
                  >
                    {busy === 'lock' ? 'Locking…' : 'Lock this version'}
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>

      <div className="tpl-manage">
        <Link className="link" to="/assets">Manage frames →</Link>
      </div>

      <Toast toast={toast} />
    </div>
  )
}
