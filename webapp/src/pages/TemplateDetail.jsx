import { useMemo } from 'react'
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
import { templateForChannel, armable, assetLabel, wiringOf } from '../templates'
import EmptyState from '../components/EmptyState'

/**
 * TemplateDetail — quick-look for one factory_templates row (Studio redesign,
 * Phase A). Shows the recipe header + a "Frames & cosmetics" grid mirroring the
 * Assets board: one tile per asset_type showing the LOCKED version, its lineage
 * and how it's wired into the renderer. Only the channel that produces with the
 * template has registered frames today (claude-tricks); others get a blueprint
 * placeholder until their assets are registered.
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

export default function TemplateDetail() {
  const { key } = useParams()
  const tplQ = usePoll(() => api.get('?r=templates'), 20000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  // Fetch all asset versions once and filter to this channel client-side (only
  // claude-tricks has rows today) — mirrors Assets.jsx and sidesteps the
  // conditional-hook problem of a channel we only learn about after load.
  const assetsQ = usePoll(() => api.get('?r=assets'), 20000)

  const templates = (tplQ.data && tplQ.data.templates) || []
  const channels = (chansQ.data && chansQ.data.channels) || []
  const versions = (assetsQ.data && assetsQ.data.versions) || []
  const locks = (assetsQ.data && assetsQ.data.locks) || []

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
            const coverPath = locked && (locked.thumb_path || locked.storage_path)
            const coverUrl = coverPath ? RENDERS_BASE + coverPath : null
            const wiring = wiringOf(type)
            return (
              <div key={type} className="card frame-tile" style={accent ? { '--ch': accent } : undefined}>
                <div className={'studio-cover' + (coverUrl ? '' : ' studio-cover-fallback')}>
                  {coverUrl ? (
                    <img src={coverUrl} alt="" loading="lazy" />
                  ) : (
                    <span className="studio-cover-glyph" aria-hidden="true">
                      {emoji || channelMonogram(channelKey)}
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
                <div className="studio-card-body">
                  <div className="studio-card-title frame-title">{assetLabel(type)}</div>
                  <div className="studio-card-sub">
                    {locked ? (
                      <span className="dim small">v{locked.version}</span>
                    ) : (
                      <span className="dim small">no version locked</span>
                    )}
                    <span className={'chip frame-wiring frame-wiring-' + wiring}>
                      {WIRING_LABEL[wiring]}
                    </span>
                  </div>
                  {head && <div className="asset-lineage">{lineageOf(head, byId)}</div>}
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

      <div className="tpl-manage">
        <Link className="link" to="/assets">Manage frames →</Link>
      </div>
    </div>
  )
}
