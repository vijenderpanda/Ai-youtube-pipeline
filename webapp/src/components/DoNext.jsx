import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { resolveStage, stageIndex } from '../pipeline'
import { resolveAccents, accentFor } from '../channelColor'

/**
 * DoNext — the guided execution queue. Every in-flight episode that needs the
 * creator becomes one pipeline-ordered task with a single one-click action that
 * drops them exactly where the work is. This is the "plan once, then step by
 * step" surface: once a plan is locked, the creator only ever answers "what's
 * next?" here.
 */

// Sort key: unblock failures first, then review, then ship-ready.
const URGENCY = { fix: 0, review: 1, arm: 2 }

export default function DoNext() {
  const stagedQ = usePoll(() => api.get('?r=staged'), 10000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const navigate = useNavigate()

  const items = (stagedQ.data && stagedQ.data.items) || []
  const counts = (stagedQ.data && stagedQ.data.counts) || {}
  const channels = (chansQ.data && chansQ.data.channels) || []
  const accents = useMemo(() => resolveAccents(channels), [channels])
  const chanName = useMemo(() => {
    const m = {}
    for (const c of channels) m[c.key] = c.name || c.key
    return m
  }, [channels])

  const { tasks, producing } = useMemo(() => {
    const tasks = []
    let producing = 0
    for (const it of items) {
      const st = resolveStage(it, counts[it.id] || {})
      if (st.action) tasks.push({ it, ...st })
      else if (st.stage === 'produce') producing += 1
    }
    tasks.sort(
      (a, b) =>
        (URGENCY[a.action.kind] - URGENCY[b.action.kind]) ||
        (stageIndex(a.stage) - stageIndex(b.stage))
    )
    return { tasks, producing }
  }, [items, counts])

  const loading = stagedQ.loading && stagedQ.data == null

  return (
    <section className="card panel donext-panel">
      <div className="panel-head">
        <h2>Do next</h2>
        <span className="dim small">
          {producing > 0 ? `${producing} in production · ` : ''}guided, in pipeline order
        </span>
      </div>

      {loading ? (
        <p className="dim" style={{ padding: '4px 2px' }}>Loading…</p>
      ) : tasks.length === 0 ? (
        <div className="donext-clear">
          <span className="donext-clear-mark" aria-hidden="true">✓</span>
          <div>
            <div className="donext-clear-title">You're all caught up</div>
            <div className="dim small">
              {producing > 0
                ? `${producing} episode${producing > 1 ? 's' : ''} in production — nothing needs you right now.`
                : 'Nothing in the pipeline needs you. Plan the next one when you’re ready.'}
            </div>
          </div>
        </div>
      ) : (
        <ul className="donext-list">
          {tasks.map(({ it, stage, action }) => {
            const accent = accentFor(it.channel_key, accents)
            const name = chanName[it.channel_key] || it.channel_key
            return (
              <li key={it.id} className="donext-row">
                <span className="donext-dot" style={{ background: accent }} aria-hidden="true" />
                <div className="donext-main">
                  <div className="donext-title">{it.title || '(untitled)'}</div>
                  <div className="donext-sub dim small">{name}</div>
                </div>
                <span className={`donext-stage stage-${stage}`}>{stage.toUpperCase()}</span>
                <button
                  className={'btn btn-sm ' + (action.kind === 'arm' ? 'btn-primary' : 'btn-ghost')}
                  onClick={() => navigate('/studio/' + it.id)}
                >
                  {action.label}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
