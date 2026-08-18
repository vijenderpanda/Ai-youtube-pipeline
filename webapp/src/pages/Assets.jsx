import { useMemo, useState } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import { accentFor, resolveAccents } from '../channelColor'
import {
  assetLabel,
  wiringOf,
  kindOf,
  hasCover,
  lineageOf,
  usageOf,
  usageBadge,
  usageSummary,
  usageTitle,
} from '../assetCatalog'
import EmptyState from '../components/EmptyState'
import MediaPreview, { hasPreview, sampleNoteOf } from '../components/MediaPreview'
import Toast, { useToast } from '../components/Toast'
import { fmtDate } from '../format'

/**
 * Assets — Studio brand-asset board (docs/STUDIO-ASSET-VERSIONING.md).
 * One card per SLOT (asset_type); its versions are the interchangeable
 * revisions. factory_asset_locks is the ONLY authority on what is locked —
 * it is what build_ep_v2._lock_lookup() actually reads, so the board cannot
 * claim a lock the renderer would not honour.
 *
 * Visual treatment is per kind: image/video/audio get a cover band (an <img>
 * only when the path is genuinely decodable — an .mp3 is not), while
 * code/id/style render body-only with a mono build_ref chip.
 *
 * Every card is AUDITIONABLE (MediaPreview): the cover band plays the locked
 * revision, an "Audition" row plays each other revision, and a code/id/style
 * slot plays the finished short its composition rendered (meta.sample_path) so
 * a lock is chosen on the thing itself, not on a filename.
 *
 * Phase 3 adds USAGE backlinks (?r=asset_backlinks): which episodes each
 * revision was actually built into, and which casts compose it. Provenance
 * recording only began with migration 021, so a revision with no entry may
 * still have shipped many times before then — absence is rendered as an em-dash
 * or nothing, NEVER as "0" or "never used", and the sub-header states the date
 * attribution starts from.
 */

const CHANNEL_KEY = 'claude-tricks'

const WIRING_NOTE = {
  live: 'Live in render',
  locked: 'Locked · wiring next',
  reference: 'Reference',
}

/** Sub-header note — states exactly how far back attribution goes. */
function recordedFromNote(since) {
  if (!since) {
    // Nothing recorded yet at all — say so plainly rather than leaving the
    // blanks below to be read as "never used".
    return 'No episode usage recorded yet — attribution starts with the next build; earlier episodes aren’t attributed.'
  }
  const d = new Date(since)
  const day = isNaN(d.getTime())
    ? String(since).slice(0, 10)
    : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  return `Usage is recorded from ${day} onward — older episodes aren’t attributed.`
}

export default function Assets() {
  const q = usePoll(() => api.get('?r=assets&channel=' + CHANNEL_KEY), 15000)
  // Phase 3: where each revision has actually been used (observed, not inferred).
  const useQ = usePoll(() => api.get('?r=asset_backlinks&channel=' + CHANNEL_KEY), 60000)
  const { toast, show } = useToast()
  const [busy, setBusy] = useState(null)
  const [expanded, setExpanded] = useState({}) // asset_type -> show full history
  const [openUse, setOpenUse] = useState({})   // asset_type -> show episode list

  const versions = (q.data && q.data.versions) || []
  const locks = (q.data && q.data.locks) || []
  const usage = (useQ.data && useQ.data.usage) || {}
  const recordedSince = (useQ.data && useQ.data.recorded_since) || null
  const chQ = usePoll(() => api.get('?r=channels'), 0)
  const accents = useMemo(
    () => resolveAccents((chQ.data && chQ.data.channels) || []),
    [chQ.data],
  )
  const accent = accentFor(CHANNEL_KEY, accents)

  // locks is not channel-filtered server-side — keep the client filter.
  const lockByType = useMemo(() => {
    const m = {}
    for (const l of locks) if (l.channel_key === CHANNEL_KEY) m[l.asset_type] = l
    return m
  }, [locks])

  const groups = useMemo(() => {
    const byType = new Map()
    for (const v of versions) {
      if (v.channel_key !== CHANNEL_KEY) continue
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
      await api.post({
        action: 'lock_asset',
        channel_key: CHANNEL_KEY,
        asset_type,
        version_id,
      })
      await q.refresh()
    } catch (e) {
      show(e.message || 'Could not change the lock')
    } finally {
      setBusy(null)
    }
  }

  const nothing = !q.loading && groups.length === 0

  return (
    <div className="page" style={{ '--ch': accent }}>
      <header className="page-head">
        <div>
          <h1>Assets</h1>
          <p className="sub">Locked brand assets + version history.</p>
          {/* HONESTY NOTE — the one place the page explains what a blank usage
              cell means. Without it, "no badge" reads as "never used". */}
          <p className="sub small assets-usage-note">
            {useQ.error
              ? 'Usage data could not be loaded (' + useQ.error.message +
                ') — the blanks below mean “unknown”, not “unused”.'
              : recordedFromNote(recordedSince)}
          </p>
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
            // The lock table is the ONLY authority (matches build_ep_v2).
            const locked =
              (lock && lock.locked_version_id && byId[lock.locked_version_id]) || null
            const head = locked || vers[0]
            const kind = kindOf(type, head)
            const wiring = wiringOf(type)
            const lineage = head ? lineageOf(head, byId) : ''
            const buildRef = head && head.meta && head.meta.build_ref
            // Usage of the revision this card is fronting (the locked one).
            const headUse = usageOf(usage, head && head.id)
            const headSummary = usageSummary(headUse)
            const headVideos = (headUse && headUse.videos) || []

            return (
              <div key={type} className="card studio-card" style={{ '--ch': accent }}>
                {hasCover(kind) && (
                  <div className="studio-cover">
                    <MediaPreview
                      assetType={type}
                      version={head}
                      size="cover"
                      name={assetLabel(type) + (head ? ' v' + head.version : '')}
                    />
                    <span className="studio-cover-chan">
                      <span className="studio-cover-dot" />
                      {assetLabel(type)}
                    </span>
                    {locked ? (
                      <span className="studio-cover-live">
                        🔒 v{locked.version}
                        {wiring === 'live' && <b className="asset-live-tag">LIVE</b>}
                      </span>
                    ) : (
                      <span className="studio-cover-live asset-ref">Reference only</span>
                    )}
                  </div>
                )}

                <div className="studio-card-body">
                  <div className="studio-card-title">{assetLabel(type)}</div>
                  <div className="studio-card-sub">
                    {locked && lock && lock.locked_at && (
                      <span className="dim small">locked since {fmtDate(lock.locked_at)}</span>
                    )}
                    <span className={'chip frame-wiring frame-wiring-' + wiring}>
                      {WIRING_NOTE[wiring]}
                    </span>
                    <span className="dim small">
                      {vers.length} revision{vers.length > 1 ? 's' : ''}
                    </span>
                  </div>
                  {!hasCover(kind) && buildRef && (
                    <div className="asset-buildref mono">{buildRef}</div>
                  )}
                  {/* A composition/style has no file you can watch — but the
                      short it rendered does. Badged SAMPLE so nobody reads the
                      mp4 as being the component itself. */}
                  {!hasCover(kind) && sampleNoteOf(head) && (
                    <div className="asset-sample">
                      <MediaPreview
                        assetType={type}
                        version={head}
                        size="tile"
                        className="asset-sample-prev"
                        name={assetLabel(type) + ' v' + head.version}
                      />
                      <span className="dim small">{sampleNoteOf(head)}</span>
                    </div>
                  )}
                  {head && head.label && <div className="dim small">{head.label}</div>}

                  {/* Where this revision has actually been used. A blank cell is
                      an em-dash, never "0" — see the note in the sub-header. */}
                  {head && (
                    <div className="asset-usage">
                      <span className="dim small">v{head.version}</span>
                      <span className="dim small">·</span>
                      {headSummary ? (
                        headVideos.length > 0 ? (
                          <button
                            type="button"
                            className="asset-usage-btn small"
                            title={usageTitle(headUse)}
                            onClick={() =>
                              setOpenUse((o) => ({ ...o, [type]: !o[type] }))
                            }
                          >
                            {headSummary}
                            <span className="asset-usage-caret">
                              {openUse[type] ? '▴' : '▾'}
                            </span>
                          </button>
                        ) : (
                          <span className="small asset-usage-txt" title={usageTitle(headUse)}>
                            {headSummary}
                          </span>
                        )
                      ) : (
                        <span
                          className="dim small"
                          title="No usage recorded for this revision — see the note at the top of the page."
                        >
                          —
                        </span>
                      )}
                    </div>
                  )}
                  {openUse[type] && headVideos.length > 0 && (
                    <ul className="asset-usage-list">
                      {headVideos.map((v) => (
                        <li key={v.video_id}>
                          <a
                            className="link"
                            href={'https://youtu.be/' + v.video_id}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {v.yt_title || v.video_id}
                          </a>
                          {v.publish_at && (
                            <span className="dim"> · {String(v.publish_at).slice(0, 10)}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* Version rail — the chip IS the control: click a revision to
                      make it the locked one. Long histories collapse behind a
                      "+N older" toggle so an 18-revision slot stays readable. */}
                  <div className="asset-rail">
                    {(expanded[type] ? vers : vers.slice(0, 6)).map((v) => {
                      const isLocked = locked && v.id === locked.id
                      const ref = v.meta && v.meta.build_ref
                      const working = busy === v.id
                      const retired = v.status === 'retired'
                      const u = usageOf(usage, v.id)
                      const badge = usageBadge(u)
                      const uTitle = usageTitle(u)
                      return (
                        <button
                          key={v.id}
                          type="button"
                          className={
                            'chip asset-ver-chip' +
                            (isLocked ? ' asset-locked' : '') +
                            (retired ? ' asset-retired' : '')
                          }
                          disabled={working}
                          title={
                            (isLocked
                              ? 'Locked — click to unlock' + (ref ? ' · build ' + ref : '')
                              : 'Make v' + v.version + ' the locked revision' +
                                (ref ? ' · build ' + ref : '')) +
                            (uTitle ? '\n\n' + uTitle : '')
                          }
                          onClick={() => setLock(type, isLocked ? null : v.id)}
                        >
                          {working ? '…' : 'v' + v.version}
                          {isLocked && <span className="asset-locked-tag">LOCKED</span>}
                          {/* nothing at all when no usage is recorded */}
                          {badge && (
                            <span
                              className={
                                'asset-ver-use' +
                                (u.shipped > 0 ? ' asset-ver-use-shipped' : '')
                              }
                            >
                              {badge}
                            </span>
                          )}
                        </button>
                      )
                    })}
                    {vers.length > 6 && (
                      <button
                        type="button"
                        className="chip asset-more"
                        onClick={() =>
                          setExpanded((e) => ({ ...e, [type]: !e[type] }))
                        }
                      >
                        {expanded[type] ? 'show less' : `+${vers.length - 6} older`}
                      </button>
                    )}
                  </div>
                  {/* Hear/see each revision BEFORE locking it. The rail chip is
                      the lock control, so auditioning gets its own row rather
                      than a second click target inside the chip. */}
                  {(() => {
                    const shown = (expanded[type] ? vers : vers.slice(0, 6)).filter((v) =>
                      hasPreview(type, v),
                    )
                    if (vers.length < 2 || shown.length === 0) return null
                    return (
                      <div className="asset-audition">
                        <span className="dim small asset-audition-lbl">Audition</span>
                        {shown.map((v) => (
                          <span key={v.id} className="asset-aud-item">
                            <MediaPreview
                              assetType={type}
                              version={v}
                              size="tile"
                              className="asset-aud-prev"
                              name={assetLabel(type) + ' v' + v.version}
                            />
                            <span className="dim small">v{v.version}</span>
                          </span>
                        ))}
                      </div>
                    )
                  })()}
                  {lineage && <div className="asset-lineage">{lineage}</div>}
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
