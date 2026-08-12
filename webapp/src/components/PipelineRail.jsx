import { STAGES, stageIndex } from '../pipeline'

/**
 * PipelineRail — the fixed PLAN → PRODUCE → QC → ARM → LIVE rail for one
 * episode. Past stages read as done, the current stage is lit, future stages
 * wait. Orients the creator: "where is this, and what's left."
 *
 * `current` is a stage key; `accent` tints the active stage with the channel's
 * own color (a single-channel context), falling back to the app accent.
 */
export default function PipelineRail({ current = 'plan', accent }) {
  const idx = stageIndex(current)
  return (
    <ol className="rail" style={accent ? { '--ch': accent } : undefined} aria-label="Episode pipeline">
      {STAGES.map((s, i) => {
        const state = i < idx ? 'done' : i === idx ? 'now' : 'todo'
        return (
          <li key={s.key} className={`rail-step is-${state}`}>
            <span className="rail-node" aria-hidden="true">
              {state === 'done' ? '✓' : i + 1}
            </span>
            <span className="rail-label">{s.label}</span>
            {i < STAGES.length - 1 && <span className="rail-line" aria-hidden="true" />}
          </li>
        )
      })}
    </ol>
  )
}
