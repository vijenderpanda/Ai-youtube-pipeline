import { useMemo, useState } from 'react'
import { api } from '../api'
import { RENDERS_BASE } from '../config'
import { usePoll } from '../hooks'
import { accentFor, resolveAccents, channelEmoji, channelMonogram } from '../channelColor'
import EmptyState from '../components/EmptyState'
import Toast, { useToast } from '../components/Toast'
import { fmtDate } from '../format'

/**
 * Assets — Studio brand-asset board (docs/STUDIO-ASSET-VERSIONING.md, Phase 1).
 * One card per asset_type: the LOCKED version shown large (cover + label +
 * "locked since"), with a version rail + lineage beneath. Lock/unlock a version
 * straight from the board (writes factory_asset_locks via the lock_asset action).
 *
 * Mirrors Studio.jsx's scaffold (page shell, studio-grid, card/studio-card,
 * cover + fallback glyph, EmptyState, loading). Scoped to claude-tricks — the
 * only channel with registered assets today.
 */

const CHANNEL_KEY = 'claude-tricks'

// Human labels for known asset types (see the versioning spec §1); unknown
// types fall back to a titleized key so new asset kinds still read cleanly.
const ASSET_LABELS = {
  outro_sting: 'Outro sting',
  outro_card_gen: 'Outro card (per-episode)',
  host_outfit: 'Host — Sol',
  music_bed: 'Music bed',
  remotion_comp: 'Remotion composition',
  step_chip_style: 'Step chips',
  hook_image: 'Hook image',
  component_statbars: 'Component — StatBars',
  component_outrocard: 'Component — OutroCard',
  component_buildclub: 'Component — BuildClub',
}
const titleize = (s) =>
  String(s || '').replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
const assetLabel = (t) => ASSET_LABELS[t] || titleize(t)

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

export default function Assets() {
  const q = usePoll(() => api.get('?r=assets'), 15000)
  const { toast, show } = useToast()
  const [busy, setBusy] = useState(null) // version_id currently being (un)locked

  const versions = (q.data && q.data.versions) || []
  const locks = (q.data && q.data.locks) || []
  const accent = useMemo(() => accentFor(CHANNEL_KEY, resolveAccents([])), [])

  // Lock row per asset_type (this channel only).
  const lockByType = useMemo(() => {
    const m = {}
    for (const l of locks) if (l.channel_key === CHANNEL_KEY) m[l.asset_type] = l
    return m
  }, [locks])

  // Group this channel's versions by asset_type (API already orders version desc).
  const groups = useMemo(() => {
    const mine = versions.filter((v) => v.channel_key === CHANNEL_KEY)
    const byType = new Map()
    for (const v of mine) {
      if (!byType.has(v.asset_type)) byType.set(v.asset_type, [])
      byType.get(v.asset_type).push(v)
    }
    return [...byType.entries()]
      .map(([type, vers]) => ({ type, vers }))
      .sort((a, b) => a.type.localeCompare(b.type))
  }, [versions])

  const setLock = async (asset_type, version_id) => {
    setBusy(version_id ?? 'unlock:' + asset_type)
    try {
      await api.post({ action: 'lock_asset', channel_key: CHANNEL_KEY, asset_type, version_id })
      await q.refresh()
    } catch (err) {
      show('Could not update lock: ' + err.message, 'error')
    } finally {
      setBusy(null)
    }
  }

  const emoji = channelEmoji(CHANNEL_KEY)
  const nothing = !q.loading && groups.length === 0

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Assets</h1>
          <p className="sub">Locked brand assets + version history.</p>
        </div>
      </header>

      {q.error && <div className="error-bar">{q.error.message}</div>}

      {q.loading && q.data == null ? (
        <p className="dim">Loading…</p>
      ) : nothing ? (
        <EmptyState
          message="No registered assets yet"
          hint="Once the backfill registers this channel’s intro, outro, host faces and step-chip style as versions, they’ll show here with the locked one marked."
        />
      ) : (
        <div className="studio-grid">
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

            return (
              <div key={type} className="card studio-card" style={{ '--ch': accent }}>
                <div className={'studio-cover' + (coverUrl ? '' : ' studio-cover-fallback')}>
                  {coverUrl ? (
                    <img src={coverUrl} alt="" loading="lazy" />
                  ) : (
                    <span className="studio-cover-glyph" aria-hidden="true">
                      {emoji || channelMonogram(CHANNEL_KEY)}
                    </span>
                  )}
                  <span className="studio-cover-chan">
                    <span className="studio-cover-dot" />
                    {assetLabel(type)}
                  </span>
                  {locked ? (
                    <span className="studio-cover-live">🔒 v{locked.version}</span>
                  ) : (
                    <span className="studio-cover-live">unlocked</span>
                  )}
                </div>

                <div className="studio-card-body">
                  <div className="studio-card-title">{assetLabel(type)}</div>
                  <div className="studio-card-sub">
                    {locked && lock && lock.locked_at ? (
                      <span className="dim small">locked since {fmtDate(lock.locked_at)}</span>
                    ) : (
                      <span className="dim small">no version locked</span>
                    )}
                    {locked && locked.label && (
                      <span className="dim small">· {locked.label}</span>
                    )}
                  </div>

                  {/* Version rail — one chip per version; lineage caption beneath */}
                  <div className="asset-rail">
                    {vers.map((v) => {
                      const isLocked = locked && v.id === locked.id
                      const buildRef = v.meta && v.meta.build_ref
                      const working = busy === v.id
                      return (
                        <span key={v.id} className="asset-ver">
                          <span
                            className={'chip' + (isLocked ? ' asset-locked' : '')}
                            title={buildRef ? 'build ' + buildRef : v.status}
                          >
                            v{v.version}
                            {isLocked && <span className="asset-locked-tag">LOCKED</span>}
                          </span>
                          {!isLocked && (
                            <button
                              type="button"
                              className="btn btn-ghost btn-xs"
                              disabled={working}
                              onClick={() => setLock(type, v.id)}
                            >
                              {working ? '…' : 'Lock'}
                            </button>
                          )}
                        </span>
                      )
                    })}
                  </div>
                  {head && (
                    <div className="asset-lineage">{lineageOf(head, byId)}</div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <Toast toast={toast} />
    </div>
  )
}
