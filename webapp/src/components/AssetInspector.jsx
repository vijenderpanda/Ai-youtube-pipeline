import { useState } from 'react'
import { api } from '../api'
import { MODEL_OPTIONS, EFFORTS, modelLabel } from '../jobMeta'
import { timeAgo, fmtDate } from '../format'
import { renderMdLite } from '../mdlite'

const ASSET_CHIP = {
  queued: 'chip-queued',
  generating: 'chip-running',
  review: 'asset-review',
  approved: 'chip-done',
  skipped: 'chip-cancelled',
  superseded: 'chip-cancelled',
  failed: 'chip-failed',
}

export const ASSET_LABELS = {
  queued: 'Queued',
  generating: 'Generating',
  review: 'In review',
  approved: 'Approved',
  skipped: 'Skipped',
  superseded: 'Superseded',
  failed: 'Failed',
}

export function AssetStatusChip({ status }) {
  const s = String(status || 'queued').toLowerCase()
  return (
    <span className={`chip ${ASSET_CHIP[s] || 'chip-queued'}`}>
      <span className="chip-dot" />
      {ASSET_LABELS[s] || s}
    </span>
  )
}

/** v1 assets land approved straight from factory QC — mark them subtly. */
export function AutoApprovedBadge() {
  return (
    <span className="auto-badge" title="Auto-approved by factory QC — revise to challenge">
      auto
    </span>
  )
}

/** True when this (latest) row was approved by factory QC, not a human. */
export function isAutoApproved(asset) {
  return String(asset.status || '').toLowerCase() === 'approved' && (asset.version || 1) === 1
}

/** factory_assets.spec arrives as jsonb (object) or a JSON string — normalize. */
function parseSpec(spec) {
  if (!spec) return null
  if (typeof spec === 'object') return spec
  try {
    return JSON.parse(spec)
  } catch {
    return null
  }
}

/**
 * Inspector panel for the selected asset on the Studio board: identity,
 * status, version history (older versions preview in the stage), the
 * reviewer-notes trail, and the approve / revise / skip review actions.
 * Actions always target the LATEST version (`asset`), whatever is displayed.
 */
export default function AssetInspector({
  asset,
  history = [],
  displayed,
  onShowVersion,
  reviewNote,
  onToast,
  refresh,
}) {
  const [busy, setBusy] = useState('') // '' | 'approve' | 'skip' | 'revise'
  const [revising, setRevising] = useState(false)
  const [notes, setNotes] = useState('')
  const [model, setModel] = useState(asset.model || 'opus')
  const [effort, setEffort] = useState(EFFORTS.includes(asset.effort) ? asset.effort : 'high')

  const s = String(asset.status || 'queued').toLowerCase()
  const title = asset.title || asset.asset_key
  const spec = parseSpec(asset.spec)
  const trail = spec && Array.isArray(spec.revision_notes) ? spec.revision_notes : []
  const versions = [asset, ...history]

  const act = async (label, body, msg) => {
    if (busy) return
    setBusy(label)
    try {
      await api.post(body)
      onToast(msg, 'ok')
      refresh()
    } catch (e) {
      onToast(e.message, 'error')
    }
    setBusy('')
  }

  const approve = () =>
    act('approve', { action: 'approve_asset', id: asset.id }, `Approved ${asset.asset_key}`)
  const skip = () =>
    act('skip', { action: 'skip_asset', id: asset.id }, `Skipped ${asset.asset_key}`)

  const submitRevise = async () => {
    if (busy || !notes.trim()) return
    setBusy('revise')
    try {
      await api.post({
        action: 'revise_asset',
        id: asset.id,
        notes: notes.trim(),
        model,
        effort,
      })
      onToast(`Revision queued — v${(asset.version || 1) + 1} will regenerate`, 'ok')
      setRevising(false)
      setNotes('')
      refresh()
    } catch (e) {
      onToast(e.message, 'error')
    }
    setBusy('')
  }

  return (
    <aside className="card inspector">
      <div className="insp-head">
        <div className="insp-title" title={title}>
          {title}
        </div>
        <div className="insp-tags">
          <AssetStatusChip status={s} />
          {isAutoApproved(asset) && <AutoApprovedBadge />}
          <span
            className="v-badge"
            title={asset.notes ? `Feedback that requested this version:\n${asset.notes}` : undefined}
          >
            v{asset.version || 1}
          </span>
        </div>
        <div className="insp-tags">
          <span className="tag">{asset.asset_key}</span>
          {asset.group_key && <span className="tag dim-tag">{asset.group_key}</span>}
          {asset.model && (
            <span className="tag dim-tag" title={asset.model}>
              {modelLabel(asset.model)}
            </span>
          )}
          {asset.effort && <span className="tag dim-tag">{asset.effort}</span>}
          <span className="insp-time" title={fmtDate(asset.created_at)}>
            {timeAgo(asset.created_at)}
          </span>
        </div>
      </div>

      {reviewNote && String(reviewNote).trim() !== '' && (
        <div className="review-note">
          <div className="review-note-head">What to check</div>
          <div className="mdlite" dangerouslySetInnerHTML={{ __html: renderMdLite(reviewNote) }} />
        </div>
      )}

      <div className="asset-actions">
        {s === 'review' && (
          <button className="btn btn-primary btn-sm" onClick={approve} disabled={!!busy}>
            {busy === 'approve' ? 'Approving…' : 'Approve ✓'}
          </button>
        )}
        {(s === 'review' || s === 'approved' || s === 'failed') && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setRevising((v) => !v)}
            disabled={!!busy}
            title={
              s === 'failed'
                ? 'Queue a retry with feedback'
                : 'Re-open this asset — queue a new version with feedback'
            }
          >
            {revising ? 'Cancel' : s === 'failed' ? 'Revise & retry' : 'Revise'}
          </button>
        )}
        {(s === 'queued' || s === 'review' || s === 'failed') && (
          <button
            className="btn btn-danger btn-sm"
            onClick={skip}
            disabled={!!busy}
            title="Exclude this asset from assembly"
          >
            {busy === 'skip' ? 'Skipping…' : 'Skip'}
          </button>
        )}
      </div>

      {revising && (
        <div className="revise-panel">
          <label className="field">
            <span className="field-label">What should change?</span>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Required — feedback for the next version…"
            />
          </label>
          <div className="form-row">
            <label className="field">
              <span className="field-label">Model</span>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {/* models may arrive as full ids (claude-opus-5 etc.) — keep them selectable */}
                {!MODEL_OPTIONS.some((m) => m.value === model) && model && (
                  <option value={model}>{model}</option>
                )}
                {MODEL_OPTIONS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="field">
              <span className="field-label">Effort</span>
              <div className="effort-seg" role="radiogroup" aria-label="Effort">
                {EFFORTS.map((e) => (
                  <button
                    key={e}
                    type="button"
                    role="radio"
                    aria-checked={effort === e}
                    className={'effort-stop' + (effort === e ? ' active' : '')}
                    onClick={() => setEffort(e)}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="form-actions">
            <button
              className="btn btn-primary btn-sm"
              onClick={submitRevise}
              disabled={!!busy || !notes.trim()}
              title={!notes.trim() ? 'Feedback is required' : undefined}
            >
              {busy === 'revise' ? 'Queuing…' : `Queue v${(asset.version || 1) + 1}`}
            </button>
          </div>
        </div>
      )}

      {versions.length > 1 && (
        <div className="insp-section">
          <div className="insp-label">Versions</div>
          <div className="ver-list">
            {versions.map((v) => {
              const isLatest = v.id === asset.id
              const active = displayed && displayed.id === v.id
              return (
                <button
                  key={v.id}
                  type="button"
                  className={'ver-row' + (active ? ' active' : '')}
                  onClick={() => onShowVersion(v.version || 1)}
                  title={v.notes ? `Feedback that requested this version:\n${v.notes}` : undefined}
                >
                  <span className="v-badge">v{v.version || 1}</span>
                  <span className={isLatest ? 'ver-cur' : 'ver-sup'}>
                    {isLatest ? ASSET_LABELS[s] || s : `superseded v${v.version || 1}`}
                  </span>
                  <span className="ver-time" title={fmtDate(v.created_at)}>
                    {timeAgo(v.created_at)}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {trail.length > 0 && (
        <div className="insp-section">
          <div className="insp-label">Review trail</div>
          <ol className="note-trail">
            {trail.map((n, i) => (
              <li key={i} className="note-item">
                <div className="note-meta" title={fmtDate(n.ts)}>
                  {timeAgo(n.ts) || String(n.ts || '')}
                </div>
                <div className="note-text">{n.notes}</div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </aside>
  )
}
