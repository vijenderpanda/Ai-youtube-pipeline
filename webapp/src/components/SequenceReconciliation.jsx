/**
 * SequenceReconciliation — the SEQUENCE twin of CastReconciliation (S4).
 *
 * The cast card diffs, per slot, what a piece is PINNED TO against what the build
 * actually used. This does the same for the composition SEQUENCE: per position,
 * the locked composition._sequence block vs the block the build actually rendered
 * (factory_episode_blocks_used, written by build_ep_v2._flush_sequence_provenance,
 * read as `sequence` on ?r=episode_assets). A silent block drop — a locked block
 * whose _seq_segment produced nothing — is the exact failure this makes legible,
 * the sequence analog of EP15's silent host swap.
 *
 * Unlike the cast, the built side IS wired end-to-end from day one, so `rendered`
 * is ground truth: a locked block with rendered===false shipped as nothing.
 *
 * @param item        factory_calendar row (gates on preview_path)
 * @param pickedCast  the cast/composition in force — its .composition._sequence is LOCKED truth
 * @param deadPin     a pinned cast the build refuses, or null (whole-sequence divergence)
 * @param boundId     item.template_version_id (pinned) or null
 * @param builtBlocks factory_episode_blocks_used rows for this piece, or null
 */

// Mirror build_ep_v2._block_ref — the identity string of WHAT filled a block, so
// a built.ref can be diffed against the same value derived from the locked block.
function blockRef(block) {
  const conf = (block && block.config) || {}
  const cb = conf.cookbook
  if (cb && typeof cb.id === 'string' && cb.id) return cb.id
  const broll = conf.broll
  if (broll && broll.id) return String(broll.id)
  const host = conf.host || {}
  if (host.label || host.id) return 'host:' + String(host.label || host.id)
  return conf.layout || block.layout || block.block_type || '—'
}

export default function SequenceReconciliation({
  item,
  pickedCast,
  deadPin,
  boundId,
  builtBlocks = null,
}) {
  if (!item || !item.preview_path) return null

  // A composition with no designed sequence renders classic beats only — there is
  // nothing to reconcile, and the classic path must show no new UI (byte-identity).
  const lockedSeq =
    pickedCast && pickedCast.composition && Array.isArray(pickedCast.composition._sequence)
      ? pickedCast.composition._sequence
      : []
  if (lockedSeq.length === 0) return null

  // Built blocks keyed by position, most-recent build wins (server orders
  // created_at desc, so the first row seen for a position is the newest).
  const builtByPos = {}
  if (Array.isArray(builtBlocks)) {
    for (const r of builtBlocks) {
      if (!(r.position in builtByPos)) builtByPos[r.position] = r
    }
  }
  const haveBuilt = Array.isArray(builtBlocks)

  // The build ignored the pinned cast/composition entirely (refused / vanished) →
  // it rendered off the channel locks, so no locked block below actually played.
  const wholeCastDiverged = !!deadPin || (!!boundId && !pickedCast)

  const rows = [...lockedSeq]
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
    .map((blk) => {
      const lockedRef = blockRef(blk)
      const built = builtByPos[blk.position] || null

      let flag = ''
      let bad = false
      if (wholeCastDiverged) {
        flag = 'built off channel locks — not this sequence'
        bad = true
      } else if (haveBuilt && built && built.rendered === false) {
        flag = 'locked block rendered nothing'
        bad = true
      } else if (haveBuilt && !built) {
        flag = 'no provenance row for this block'
        bad = true
      } else if (
        haveBuilt &&
        built &&
        (built.ref !== lockedRef || built.block_type !== blk.block_type)
      ) {
        flag = 'built ≠ locked'
        bad = true
      }

      return { blk, lockedRef, built, flag, bad }
    })

  const diverged = rows.filter((r) => r.bad).length
  const clean = diverged === 0

  return (
    <section className="cast-recon seq-recon card" aria-labelledby="seq-recon-title">
      <div className="cast-recon-head">
        <div className="cast-recon-title" id="seq-recon-title">
          Sequence reconciliation — what shipped vs the locked composition
        </div>
        <span className={'chip cast-recon-verdict' + (clean ? ' recon-ok' : ' recon-bad')}>
          {clean
            ? haveBuilt
              ? '✓ built matches the sequence'
              : 'no divergence detectable'
            : `⚠ ${diverged} block${diverged === 1 ? '' : 's'} diverged`}
        </span>
      </div>

      <p className="dim small cast-recon-sub">
        {lockedSeq.length} designed block{lockedSeq.length === 1 ? '' : 's'} in{' '}
        <b>
          {pickedCast
            ? `cast v${pickedCast.version}${pickedCast.label ? ' · ' + pickedCast.label : ''}`
            : 'the pinned composition'}
        </b>
        {haveBuilt ? '.' : ' — build provenance not recorded for this piece yet.'}
      </p>

      {wholeCastDiverged && (
        <p className="cast-recon-banner">
          This piece is pinned to a composition the build won’t use
          {deadPin ? ` (${deadPin.status})` : ''} — it rendered off the channel’s locks
          instead, so none of the designed blocks below actually played.
        </p>
      )}

      <div className="cast-recon-table" role="table">
        <div className="cast-recon-row cast-recon-hrow" role="row">
          <span role="columnheader">#</span>
          <span role="columnheader">Locked block</span>
          <span role="columnheader">Built</span>
          <span role="columnheader">Status</span>
        </div>
        {rows.map((r) => (
          <div
            key={r.blk.position}
            className={'cast-recon-row' + (r.bad ? ' recon-diverged' : '')}
            role="row"
          >
            <span role="cell" className="cast-recon-slot">
              {r.blk.position}
            </span>
            <span role="cell" className="cast-recon-cell">
              <b>{r.blk.block_type || 'block'}</b>
              {r.blk.layout ? <span className="dim small"> · {r.blk.layout}</span> : null}
              <span className="mono dim small cast-recon-ref">{r.lockedRef}</span>
            </span>
            <span role="cell" className="cast-recon-cell">
              {r.built ? (
                r.built.rendered === false ? (
                  <span className="dim small" title="This locked block produced no segment.">
                    (nothing)
                  </span>
                ) : (
                  <span className="mono dim small cast-recon-ref">{r.built.ref}</span>
                )
              ) : (
                <span
                  className="dim small"
                  title={
                    haveBuilt
                      ? 'No build provenance row recorded at this position.'
                      : 'Sequence build provenance isn’t recorded for this piece yet.'
                  }
                >
                  —
                </span>
              )}
            </span>
            <span role="cell" className="cast-recon-cell">
              {r.flag ? (
                <span className={'chip cast-warn-dead'} title={r.flag}>
                  {r.flag}
                </span>
              ) : (
                <span className="dim small">{haveBuilt ? 'match' : 'as designed'}</span>
              )}
            </span>
          </div>
        ))}
      </div>

      {!haveBuilt && (
        <p className="dim small cast-recon-note">
          The <b>Built</b> column reads em-dashes because this piece was produced
          before sequence provenance (factory_episode_blocks_used) was recorded —
          re-cut it to populate the diff. New produces record it automatically.
        </p>
      )}
    </section>
  )
}
