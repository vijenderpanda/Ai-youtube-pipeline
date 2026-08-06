import { useNavigate } from 'react-router-dom'
import { RENDERS_BASE } from '../config'

function trunc(s, n = 60) {
  const t = String(s || '').trim()
  return t.length > n ? t.slice(0, n - 1).trimEnd() + '…' : t
}

/** New Job prefill that re-runs ONLY what an issue affected. */
function fixPrefill(job, issue) {
  return {
    channel_key: job.channel_key,
    type: 'custom',
    model: 'opus',
    effort: 'medium',
    title: 'Fix: ' + trunc(issue),
    prompt:
      `Previous job '${job.title || '(untitled)'}' (id ${job.id}) completed with this issue: ${issue}. ` +
      `Original brief:\n${job.prompt || ''}\n\n` +
      'Fix the issue and re-produce ONLY what is affected — reuse existing intermediates ' +
      'in the episode folder where valid. Follow docs/PRODUCTION-PLAYBOOK.md.',
  }
}

/** New Job prefill that runs a recap "next" step as its own job. */
function nextPrefill(job, next) {
  return {
    channel_key: job.channel_key,
    type: 'custom',
    title: trunc(next),
    prompt: next,
  }
}

/**
 * Normalize factory_jobs.result.recap into a safe shape (all fields optional
 * in the wild — worker recaps are best-effort). Returns null when absent.
 */
export function getRecap(job) {
  const r = job && job.result && job.result.recap
  if (!r || typeof r !== 'object' || Array.isArray(r)) return null
  const strs = (v) =>
    Array.isArray(v) ? v.filter((x) => typeof x === 'string' && x.trim()) : []
  const recap = {
    headline: typeof r.headline === 'string' ? r.headline.trim() : '',
    steps: strs(r.steps),
    decisions: strs(r.decisions),
    issues: strs(r.issues),
    outputs: Array.isArray(r.outputs)
      ? r.outputs.filter((o) => o && typeof o === 'object' && (o.filename || o.note))
      : [],
    next: strs(r.next),
  }
  const empty =
    !recap.headline &&
    !recap.steps.length &&
    !recap.decisions.length &&
    !recap.issues.length &&
    !recap.outputs.length &&
    !recap.next.length
  return empty ? null : recap
}

/** Find the render backing an output chip: job_id match first, then filename. */
function matchRender(output, renders, jobId) {
  if (!Array.isArray(renders) || !renders.length) return null
  const name = String(output.filename || '').toLowerCase()
  const fname = (r) =>
    String(r.filename || (r.storage_path || '').split('/').pop() || '').toLowerCase()
  const jobRenders = jobId ? renders.filter((r) => r.job_id === jobId) : []
  return (
    (name && jobRenders.find((r) => fname(r) === name)) ||
    (jobRenders.length === 1 ? jobRenders[0] : null) ||
    (name && renders.find((r) => fname(r) === name)) ||
    null
  )
}

export function RecapIssues({ issues, prominent = false, job = null }) {
  const navigate = useNavigate()
  if (!issues || !issues.length) return null
  return (
    <div className={'recap-issues' + (prominent ? ' prominent' : '')}>
      <span className="recap-label">⚠ Issues</span>
      <ul className="recap-list">
        {issues.map((it, i) => (
          <li key={i} className={job ? 'recap-li-act' : undefined}>
            {job ? <span className="recap-li-text">{it}</span> : it}
            {job && (
              <button
                type="button"
                className="recap-act"
                title="New Job pre-filled to fix this issue and re-produce only what's affected"
                onClick={() => navigate('/jobs', { state: { newJob: fixPrefill(job, it) } })}
              >
                <span aria-hidden="true">⚡</span> Fix &amp; re-run
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function JobRecap({ recap, renders = [], jobId, job = null, showIssues = true }) {
  const navigate = useNavigate()
  if (!recap) return null
  return (
    <div className="drawer-section">
      <span className="field-label">What happened</span>
      <div className="recap-box">
        {recap.headline && <div className="recap-headline">{recap.headline}</div>}

        {recap.steps.length > 0 && (
          <ul className="recap-steps">
            {recap.steps.map((s, i) => (
              <li key={i}>
                <span className="recap-check" aria-hidden="true">
                  ✓
                </span>
                {s}
              </li>
            ))}
          </ul>
        )}

        {recap.decisions.length > 0 && (
          <div className="recap-block">
            <span className="recap-label">🧭 Decisions</span>
            <ul className="recap-list">
              {recap.decisions.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          </div>
        )}

        {showIssues && <RecapIssues issues={recap.issues} job={job} />}

        {recap.outputs.length > 0 && (
          <div className="recap-block">
            <span className="recap-label">Outputs</span>
            <div className="recap-outputs">
              {recap.outputs.map((o, i) => {
                const render = matchRender(o, renders, jobId)
                const url = render
                  ? render.storage_path
                    ? RENDERS_BASE + render.storage_path
                    : render.published_url || null
                  : null
                const body = (
                  <>
                    <span className="out-name">{o.filename || o.kind || 'output'}</span>
                    {o.note && <span className="out-note">{o.note}</span>}
                    {url && (
                      <span className="out-link" aria-hidden="true">
                        ↗
                      </span>
                    )}
                  </>
                )
                return url ? (
                  <a
                    key={i}
                    className="out-chip"
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    title={o.kind ? `${o.kind} — open render` : 'Open render'}
                  >
                    {body}
                  </a>
                ) : (
                  <span key={i} className="out-chip" title={o.kind || undefined}>
                    {body}
                  </span>
                )
              })}
            </div>
          </div>
        )}

        {recap.next.length > 0 && (
          <div className="recap-next">
            {recap.next.map((n, i) => (
              <div key={i} className="recap-next-line">
                <span className="recap-li-text">→ {n}</span>
                {job && (
                  <button
                    type="button"
                    className="recap-act"
                    title="New Job pre-filled with this next step"
                    onClick={() =>
                      navigate('/jobs', { state: { newJob: nextPrefill(job, n) } })
                    }
                  >
                    <span aria-hidden="true">▶</span> Run
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
