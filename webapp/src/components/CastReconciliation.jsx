import { assetLabel, shotCoverage } from '../assetCatalog'

/**
 * CastReconciliation — the one view that would have made EP15 legible.
 *
 * EP15 was locked to cast v2 (host outfit_12_longform_olive) but the build
 * SILENTLY shipped a different host (outfit_11) — because outfit_12 is a
 * long-form host that cannot render a Short, so a faithful build was impossible
 * and the substitution went unrecorded on screen. This card diffs, per slot,
 * what the piece is PINNED TO (the locked cast) against what the build actually
 * used, and flags every divergence.
 *
 * HONESTY: the ground truth for "what the build actually used" is
 * factory_episode_assets_used (build_ep_v2._flush_provenance), which has no
 * per-episode read endpoint yet — so `builtRows` is usually absent. Rather than
 * fake a built column, this renders the LOCKED cast plus every divergence we
 * CAN prove from data already fetched:
 *
 *   • a pinned cast the build refuses (draft/retired/vanished) → it fell back
 *     to the channel's asset locks, so every slot diverged;
 *   • a locked HOST that structurally cannot render this format (long-form host
 *     on a Short — the exact EP15 fault) → the build cannot have used it.
 *
 * When `builtRows` IS supplied (once the read is wired) it diffs build_ref by
 * build_ref and flags built≠locked plus any locked slot with no provenance row.
 *
 * @param item          factory_calendar row (preview_path, template_version_id)
 * @param pickedCast    the cast in force — bound, else the template's active
 * @param effCast       pickedCast only when it is locked (actually renders)
 * @param deadPin       a pinned cast the build refuses, or null
 * @param boundId       item.template_version_id (pinned) or null
 * @param brandVersions channel factory_asset_versions (for host meta lookup)
 * @param reqRoles      shot roles this format needs (Short ⇒ pip+wide)
 * @param builtRows     factory_episode_assets_used rows for this piece, or null
 * @param recordedSince honest "provenance starts here" date, or null
 */
export default function CastReconciliation({
  item,
  pickedCast,
  effCast,
  deadPin,
  boundId,
  brandVersions = [],
  reqRoles,
  builtRows = null,
  recordedSince = null,
}) {
  // Only meaningful once the piece has actually been produced.
  if (!item || !item.preview_path) return null

  const comp = (pickedCast && pickedCast.composition) || {}
  const slotTypes = Object.keys(comp).filter((k) => !k.startsWith('_'))
  // Always account for the three brand frames even if the cast didn't compose
  // them (they still resolve from the channel lock).
  for (const t of ['host_outfit', 'outro_sting', 'music_bed']) {
    if (!slotTypes.includes(t)) slotTypes.push(t)
  }

  const byId = {}
  for (const v of brandVersions) byId[v.id] = v

  // Built provenance keyed by asset_type (last write wins — one per slot).
  const builtByType = {}
  if (Array.isArray(builtRows)) {
    for (const r of builtRows) builtByType[r.asset_type] = r
  }
  const haveBuilt = Array.isArray(builtRows)

  // The build ignored the pinned cast entirely (refused / vanished) → every
  // slot below is served from the channel locks, not this cast.
  const wholeCastDiverged = !!deadPin || (!!boundId && !pickedCast)

  const rows = slotTypes.sort().map((type) => {
    const locked = comp[type] || null
    const lockedVer = byId[locked && locked.version_id] || null
    // Structural: a long-form host locked onto a Short cannot have rendered —
    // provable now, from the host's own meta.heygen, no provenance needed.
    const structFail =
      type === 'host_outfit' && lockedVer && !shotCoverage(lockedVer, reqRoles).fits
    const built = builtByType[type] || null

    let flag = ''
    let bad = false
    if (wholeCastDiverged) {
      flag = 'built off channel locks — not this cast'
      bad = true
    } else if (structFail) {
      flag = 'locked host can’t render a short — build substituted a fallback'
      bad = true
    } else if (haveBuilt && built && locked && built.build_ref !== locked.build_ref) {
      flag = 'built ≠ locked'
      bad = true
    } else if (haveBuilt && locked && !built) {
      flag = 'no provenance row for this slot'
      bad = true
    } else if (haveBuilt && built && built.resolved_from === 'refused') {
      flag = 'refused at build'
      bad = true
    }

    return { type, locked, lockedVer, built, flag, bad, structFail }
  })

  const diverged = rows.filter((r) => r.bad).length
  const clean = diverged === 0

  return (
    <section className="cast-recon card" aria-labelledby="cast-recon-title">
      <div className="cast-recon-head">
        <div className="cast-recon-title" id="cast-recon-title">
          Cast reconciliation — what shipped vs the locked cast
        </div>
        <span className={'chip cast-recon-verdict' + (clean ? ' recon-ok' : ' recon-bad')}>
          {clean
            ? haveBuilt
              ? '✓ built matches the cast'
              : 'no divergence detectable'
            : `⚠ ${diverged} slot${diverged === 1 ? '' : 's'} diverged`}
        </span>
      </div>

      <p className="dim small cast-recon-sub">
        Pinned to{' '}
        <b>
          {pickedCast
            ? `cast v${pickedCast.version}${pickedCast.label ? ' · ' + pickedCast.label : ''}`
            : boundId
              ? 'a cast that no longer exists'
              : 'no cast — the channel’s asset locks'}
        </b>
        {effCast ? ' — locked and in force.' : pickedCast ? ' — the build refuses it (see below).' : '.'}
      </p>

      {wholeCastDiverged && (
        <p className="cast-recon-banner">
          This piece is pinned to a cast the build won’t use
          {deadPin ? ` (${deadPin.status})` : ''} — it rendered off the channel’s asset locks
          instead, so every slot below diverged from what was pinned.
        </p>
      )}

      <div className="cast-recon-table" role="table">
        <div className="cast-recon-row cast-recon-hrow" role="row">
          <span role="columnheader">Slot</span>
          <span role="columnheader">Locked cast</span>
          <span role="columnheader">Built</span>
          <span role="columnheader">Status</span>
        </div>
        {rows.map((r) => (
          <div
            key={r.type}
            className={'cast-recon-row' + (r.bad ? ' recon-diverged' : '')}
            role="row"
          >
            <span role="cell" className="cast-recon-slot">
              {assetLabel(r.type)}
            </span>
            <span role="cell" className="cast-recon-cell">
              {r.locked ? (
                <>
                  {r.locked.version ? <b>v{r.locked.version}</b> : null}
                  <span className="mono dim small cast-recon-ref">
                    {r.locked.build_ref || '—'}
                  </span>
                </>
              ) : (
                <span className="dim small">channel lock</span>
              )}
            </span>
            <span role="cell" className="cast-recon-cell">
              {r.built ? (
                <span className="mono dim small cast-recon-ref">{r.built.build_ref}</span>
              ) : (
                <span
                  className="dim small"
                  title="Per-slot build provenance isn’t wired into this view yet — see the note below."
                >
                  —
                </span>
              )}
            </span>
            <span role="cell" className="cast-recon-cell">
              {r.flag ? (
                <span
                  className={'chip ' + (r.bad ? 'cast-warn-dead' : 'cast-warn')}
                  title={
                    r.structFail
                      ? shotCoverage(r.lockedVer, reqRoles).warn
                      : r.flag
                  }
                >
                  {r.flag}
                </span>
              ) : (
                <span className="dim small">{haveBuilt ? 'match' : 'as pinned'}</span>
              )}
            </span>
          </div>
        ))}
      </div>

      {!haveBuilt && (
        <p className="dim small cast-recon-note">
          The <b>Built</b> column reads em-dashes because per-episode build
          provenance (factory_episode_assets_used) has no read endpoint yet —
          divergences above are the ones provable from the pinned cast itself
          (a refused cast, or a host that can’t render this format). Full
          slot-by-slot reconciliation lands once that read is wired
          {recordedSince ? ` (recorded from ${String(recordedSince).slice(0, 10)} onward)` : ''}.
        </p>
      )}
    </section>
  )
}
