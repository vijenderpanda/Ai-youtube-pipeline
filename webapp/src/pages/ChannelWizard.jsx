import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

/**
 * ChannelWizard — create a new channel by answering a few questions, with
 * AI-suggested options at each step and a one-line input for your own words.
 * Answers accumulate into a draft (factory_channel_drafts); "Create channel"
 * spins up the channel (incubating) + queues its bring-up scaffold, then the
 * Ep01 temp loop begins.
 *
 * Every step ships with strong built-in suggestions so the wizard is fully
 * usable immediately; "✨ Suggest more" asks the factory for tailored options
 * (lights up once the worker runs the channel_intake job).
 */

const ACCENTS = [
  '#A78BFA', '#F97316', '#E11D48', '#14B8A6', '#6366F1', '#EAB308', '#EC4899', '#0EA5E9',
]

const STEPS = [
  {
    key: 'seed', title: 'The idea', kind: 'seed',
    q: 'In one line, what’s the channel?',
    ph: 'e.g. calm AI news explained for busy parents',
  },
  {
    key: 'vision', title: 'North star', field: 'vision', ai: true,
    q: 'What’s the vision — the feeling someone should get?',
    ph: 'e.g. AI news, without the hype',
    chips: [
      { label: 'Make a scary topic feel calm', value: 'Make a fast-moving, intimidating topic feel calm and understandable' },
      { label: 'Fastest way to stay current', value: 'The fastest, no-fluff way to stay current' },
      { label: 'Premium, cinematic explainers', value: 'Premium, cinematic explainers that feel expensive' },
    ],
  },
  {
    key: 'purpose', title: 'Purpose', field: 'purpose', ai: true,
    q: 'What’s it for?',
    ph: 'e.g. build authority, then a course funnel',
    chips: [
      { label: 'Build authority', value: 'Build authority in the niche' },
      { label: 'Earn ~$200+/mo', value: 'Monetize to ~$200+/mo' },
      { label: 'Feed a funnel', value: 'Top-of-funnel for a product or course' },
      { label: 'Pure craft', value: 'Craft-first, portfolio quality' },
    ],
  },
  {
    key: 'audience', title: 'Audience', field: 'audience', ai: true,
    q: 'Who’s it for?',
    ph: 'e.g. parents new to AI',
    chips: [
      { label: 'General adults', value: 'General adults, beginner-friendly', extra: { coppa: false } },
      { label: 'Tech professionals', value: 'Technical professionals', extra: { coppa: false } },
      { label: 'Kids (COPPA)', value: 'Kids', extra: { coppa: true } },
      { label: 'News followers', value: 'People who follow the news', extra: { coppa: false } },
    ],
  },
  {
    key: 'format', title: 'Format & cadence', field: 'format', ai: true,
    q: 'What do you post, and how often?',
    ph: 'e.g. Shorts, 3× a week',
    chips: [
      { label: 'Shorts 25–40s · 3×/wk', value: 'Shorts 25–40s, 3× per week', extra: { aspect: '9:16' } },
      { label: 'Daily Shorts', value: 'Shorts, daily', extra: { aspect: '9:16' } },
      { label: 'Mixed Shorts + long', value: 'Shorts plus occasional long-form', extra: { aspect: 'mixed' } },
      { label: 'Long-form', value: 'Long-form, weekly', extra: { aspect: '16:9' } },
    ],
  },
  {
    key: 'quality', title: 'Quality bar', field: 'quality',
    q: 'How high’s the bar? (sets the default production depth)',
    ph: '',
    chips: [
      { label: 'Premium — deepest', value: 'Premium', extra: { model: 'opus', effort: 'high' } },
      { label: 'Balanced', value: 'Balanced', extra: { model: 'opus', effort: 'medium' } },
      { label: 'Volume', value: 'Volume', extra: { model: 'sonnet', effort: 'medium' } },
    ],
  },
  {
    key: 'production', title: 'Production style', field: 'production', ai: true,
    q: 'How is it made?',
    ph: 'e.g. cinematic, no on-screen host',
    chips: [
      { label: 'Host-less cinematic', value: 'Host-less cinematic' },
      { label: 'Avatar host', value: 'Synthetic avatar host' },
      { label: 'Illustrated / baked-text', value: 'Illustrated, baked-in text' },
      { label: 'Image → video story', value: 'Image-to-video story' },
    ],
  },
  {
    key: 'competitors', title: 'References', field: 'competitors', ai: true, optional: true,
    q: 'Any creators or channels to learn from? (optional)',
    ph: 'e.g. @vaibhavsisinty — but avoid the AI-slop look',
    chips: [],
  },
  { key: 'identity', title: 'Name & look', kind: 'identity', q: 'Name it and pick a color.' },
  { key: 'review', title: 'Review', kind: 'review', q: 'Here’s your channel.' },
]

const slugify = (s) =>
  String(s || '').toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40)

export default function ChannelWizard() {
  const navigate = useNavigate()
  const [i, setI] = useState(0)
  const [draftId, setDraftId] = useState(null)
  const [answers, setAnswers] = useState({})
  const [text, setText] = useState('') // current step's free-text
  const [keyEdited, setKeyEdited] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [aiOptions, setAiOptions] = useState({}) // stepKey -> [{label,value}]
  const [aiState, setAiState] = useState({}) // stepKey -> 'loading' | 'done' | 'timeout'
  const [created, setCreated] = useState(null)

  const step = STEPS[i]
  const patch = (obj) => setAnswers((a) => ({ ...a, ...obj }))

  // persist the running answers into the draft (server merges)
  const persist = async (nextStep) => {
    if (!draftId) return
    await api.post({ action: 'update_channel_draft', draft_id: draftId, step: nextStep, patch: answers })
  }

  const goNext = async () => {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      if (step.kind === 'seed') {
        const seed = text.trim()
        const d = await api.post({ action: 'create_channel_draft', seed })
        setDraftId(d.draft.id)
        patch({ seed })
        setText('')
        setI(1)
      } else if (step.field) {
        // commit the free-text (if any) into the field, then persist + advance
        const val = text.trim()
        const merged = val ? { ...answers, [step.field]: val } : answers
        setAnswers(merged)
        if (draftId) {
          await api.post({ action: 'update_channel_draft', draft_id: draftId, step: i + 1, patch: merged })
        }
        setText('')
        setI(i + 1)
      } else {
        setI(i + 1)
      }
    } catch (e) {
      setError(e.message)
    }
    setBusy(false)
  }

  const goBack = () => {
    if (i === 0) { navigate('/channels'); return }
    setText('')
    setError('')
    setI(i - 1)
  }

  const chooseChip = (chip) => {
    if (step.field) {
      patch({ [step.field]: chip.value, ...(chip.extra || {}) })
      setText(chip.value)
    }
  }

  // opt-in AI suggestions for this step (worker-gated; static chips still work)
  const suggestMore = async () => {
    if (!draftId || !step.field) return
    setAiState((s) => ({ ...s, [step.key]: 'loading' }))
    try {
      const d = await api.post({
        action: 'wizard_suggest', draft_id: draftId, step: i,
        field: step.field, question: step.q, answers,
      })
      const jobId = d.job && d.job.id
      if (!jobId) throw new Error('no job')
      const start = Date.now()
      while (Date.now() - start < 30000) {
        await new Promise((r) => setTimeout(r, 3000))
        const jr = await api.get(`?r=job&id=${jobId}`)
        const job = jr.job || jr
        if (job.status === 'done') {
          const opts = ((job.result || {}).options || []).map((o) =>
            typeof o === 'string' ? { label: o, value: o } : { label: o.label || o.value, value: o.value || o.label }
          )
          setAiOptions((s) => ({ ...s, [step.key]: opts }))
          setAiState((s) => ({ ...s, [step.key]: 'done' }))
          return
        }
        if (job.status === 'failed' || job.status === 'cancelled') break
      }
      setAiState((s) => ({ ...s, [step.key]: 'timeout' }))
    } catch {
      setAiState((s) => ({ ...s, [step.key]: 'timeout' }))
    }
  }

  const createChannel = async () => {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      await api.post({ action: 'update_channel_draft', draft_id: draftId, patch: answers })
      const d = await api.post({ action: 'finalize_channel_draft', draft_id: draftId })
      setCreated(d.channel)
    } catch (e) {
      setError(e.message)
    }
    setBusy(false)
  }

  const chips = useMemo(
    () => [...(step.chips || []), ...(aiOptions[step.key] || [])],
    [step, aiOptions]
  )

  const pct = Math.round((i / (STEPS.length - 1)) * 100)

  if (created) {
    return (
      <div className="page wizard-page">
        <div className="wizard-done card">
          <div className="wizard-done-mark" style={{ background: created.accent || 'var(--accent)' }}>✓</div>
          <h1>{created.name} is live in the factory</h1>
          <p className="dim">
            It’s <strong>incubating</strong> — the factory is setting it up now. Produce Episode 1 as a
            temp, refine it, then lock it as the baseline your future episodes follow.
          </p>
          <div className="wizard-done-actions">
            <button className="btn btn-primary" onClick={() => navigate('/channels/' + created.key)}>
              Open {created.name} →
            </button>
            <button className="btn btn-ghost" onClick={() => navigate('/channels')}>All channels</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="page wizard-page">
      <div className="wizard-progress">
        <div className="wizard-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="wizard-head">
        <span className="wizard-step-n">Step {i + 1} / {STEPS.length}</span>
        <span className="wizard-step-title">{step.title}</span>
      </div>

      <div className="card wizard-card">
        <h1 className="wizard-q">{step.q}</h1>
        {error && <div className="error-bar">{error}</div>}

        {step.kind === 'seed' && (
          <>
            <input
              className="wizard-input"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={step.ph}
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && text.trim() && goNext()}
            />
            <p className="dim small">One sentence is plenty — we’ll shape the rest together.</p>
          </>
        )}

        {step.field && (
          <>
            <div className="wizard-chips">
              {chips.map((c, ci) => {
                const on = answers[step.field] === c.value
                return (
                  <button
                    key={ci}
                    className={'wizard-chip' + (on ? ' on' : '')}
                    onClick={() => chooseChip(c)}
                    type="button"
                  >
                    {c.label}
                  </button>
                )
              })}
              {step.ai && (
                <button className="wizard-chip wizard-chip-ai" onClick={suggestMore} type="button"
                  disabled={aiState[step.key] === 'loading'}>
                  {aiState[step.key] === 'loading' ? 'Thinking…' : '✨ Suggest more'}
                </button>
              )}
            </div>
            {aiState[step.key] === 'timeout' && (
              <p className="dim small">
                The idea engine will suggest here once your worker picks up the update — use an option
                above or type your own.
              </p>
            )}
            <input
              className="wizard-input"
              value={text}
              onChange={(e) => { setText(e.target.value); patch({ [step.field]: e.target.value }) }}
              placeholder={step.ph || 'Type your own…'}
            />
          </>
        )}

        {step.kind === 'identity' && (
          <div className="wizard-identity">
            <label className="field">
              <span className="field-label">Channel name</span>
              <input
                value={answers.name || ''}
                onChange={(e) => {
                  const name = e.target.value
                  patch({ name, ...(keyEdited ? {} : { key: slugify(name) }) })
                }}
                placeholder="e.g. Calm AI"
                autoFocus
              />
            </label>
            <label className="field">
              <span className="field-label">Handle / key <span className="dim">(lowercase, used in URLs)</span></span>
              <input
                value={answers.key || ''}
                onChange={(e) => { setKeyEdited(true); patch({ key: slugify(e.target.value) }) }}
                placeholder="calm-ai"
              />
            </label>
            <div className="field">
              <span className="field-label">Accent color <span className="dim">(shows only inside this channel)</span></span>
              <div className="wizard-swatches">
                {ACCENTS.map((hex) => (
                  <button
                    key={hex}
                    type="button"
                    className={'wizard-swatch' + (answers.accent === hex ? ' on' : '')}
                    style={{ background: hex }}
                    onClick={() => patch({ accent: hex })}
                    aria-label={hex}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {step.kind === 'review' && (
          <div className="wizard-review">
            <div className="wizard-brandcard" style={{ '--ch': answers.accent || 'var(--neutral)' }}>
              <div className="wizard-brandcard-top">
                <span className="wizard-brandcard-dot" />
                <div>
                  <div className="wizard-brandcard-name">{answers.name || '(unnamed)'}</div>
                  <div className="dim mono small">{answers.key || 'no-key'}</div>
                </div>
              </div>
              <dl className="wizard-summary">
                {[
                  ['Vision', answers.vision],
                  ['Purpose', answers.purpose],
                  ['Audience', answers.audience],
                  ['Format', answers.format],
                  ['Quality', answers.quality],
                  ['Production', answers.production],
                  ['References', answers.competitors],
                ].filter(([, v]) => v).map(([k, v]) => (
                  <div key={k} className="wizard-summary-row">
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <p className="dim small">
              Creating spins up the channel and its setup job. It starts <strong>incubating</strong> so
              you can produce Episode 1 as a temp and lock the look before it goes live.
            </p>
          </div>
        )}

        <div className="wizard-actions">
          <button className="btn btn-ghost" onClick={goBack} disabled={busy}>
            {i === 0 ? 'Cancel' : '← Back'}
          </button>
          {step.kind === 'review' ? (
            <button
              className="btn btn-primary"
              onClick={createChannel}
              disabled={busy || !answers.name || !answers.key}
            >
              {busy ? 'Creating…' : 'Create channel ▶'}
            </button>
          ) : step.kind === 'identity' ? (
            <button className="btn btn-primary" onClick={goNext} disabled={busy || !answers.name || !answers.key}>
              Review →
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={goNext}
              disabled={busy || (step.kind === 'seed' && !text.trim()) || (step.field && !step.optional && !answers[step.field] && !text.trim())}
            >
              {busy ? '…' : 'Next →'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
