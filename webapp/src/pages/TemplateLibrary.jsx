import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { resolveAccents, accentFor, channelEmoji } from '../channelColor'
import { templateForChannel, armable } from '../templates'
import EmptyState from '../components/EmptyState'

/**
 * TemplateLibrary — the locked recipes each channel produces with (Studio
 * redesign, Phase A). One card per factory_templates row; click through to the
 * quick-look. Mirrors Studio.jsx / Assets.jsx scaffold (page shell, studio-grid,
 * card/studio-card, EmptyState, loading, --ch accent).
 */
export default function TemplateLibrary() {
  const tplQ = usePoll(() => api.get('?r=templates'), 20000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)

  const templates = (tplQ.data && tplQ.data.templates) || []
  const channels = (chansQ.data && chansQ.data.channels) || []
  const accents = useMemo(() => resolveAccents(channels), [channels])

  const nothing = !tplQ.loading && templates.length === 0

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Template Library</h1>
          <p className="sub">The locked recipes each channel produces with.</p>
        </div>
      </header>

      {tplQ.error && <div className="error-bar">{tplQ.error.message}</div>}

      {tplQ.loading && tplQ.data == null ? (
        <p className="dim">Loading…</p>
      ) : nothing ? (
        <EmptyState
          message="No templates registered yet"
          hint="Templates live in factory_templates — each one binds a produce style, plan style and finalize routing that a channel produces with."
        />
      ) : (
        <div className="studio-grid">
          {templates.map((tpl) => {
            const chan = templateForChannel(channels, tpl.key)
            const accent = chan ? accentFor(chan.key, accents) : null
            const emoji = chan ? channelEmoji(chan.key) : null
            const arm = armable(tpl)
            return (
              <Link
                key={tpl.key}
                className="card studio-card tpl-card"
                to={`/studio/templates/${tpl.key}`}
                style={accent ? { '--ch': accent } : undefined}
              >
                <div className="studio-card-body">
                  <div className="studio-card-title">{tpl.name || tpl.key}</div>
                  {tpl.description && (
                    <p className="tpl-desc dim small">{tpl.description}</p>
                  )}
                  <div className="studio-card-sub">
                    <span className="dim small">
                      {tpl.runtime_s}s · {tpl.aspect}
                    </span>
                  </div>

                  <div className="tpl-badges">
                    {tpl.produce_style && <span className="chip">{tpl.produce_style}</span>}
                    {tpl.plan_style && <span className="chip">{tpl.plan_style}</span>}
                    {arm ? (
                      <span className="chip tpl-armable">Ready to arm</span>
                    ) : (
                      <span className="chip tpl-starter">Starter — can’t arm yet</span>
                    )}
                  </div>

                  <div className="tpl-foot">
                    {chan ? (
                      <span className="tpl-chan-pill">
                        <span className="tpl-chan-dot" />
                        {emoji && <span className="tpl-chan-emoji">{emoji}</span>}
                        {chan.name || chan.key}
                      </span>
                    ) : (
                      <span className="tpl-chan-none">Not in use yet</span>
                    )}
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
