import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { RENDERS_BASE } from '../config'
import { usePoll } from '../hooks'
import { resolveAccents, accentFor, channelEmoji } from '../channelColor'
import { templateForChannel, armable } from '../templates'
import EmptyState from '../components/EmptyState'

/**
 * TemplateLibrary — the locked recipes each channel produces with (Studio
 * redesign, Phase A). One card per factory_templates row; click through to the
 * quick-look. Mirrors Studio.jsx / Assets.jsx scaffold (page shell, studio-grid,
 * card/studio-card, EmptyState, loading, --ch accent).
 *
 * Each card leads with a cover band so templates read apart at a glance: a real
 * brand frame for channels in use (<channel>/assets/cover.jpg in the renders
 * bucket), falling back to a template-style glyph on the channel-accent tint for
 * starter templates (no channel) or when a channel has no cover uploaded yet.
 */

// Template-style glyph for the fallback cover. Matched against the template's
// key + produce/plan style so new rows read sensibly without a code change.
const TPL_GLYPHS = [
  [/avatar|unpacked/, '🧑‍🏫'], // avatar-host / ai-unpacked → teacher
  [/cinematic|animatic/, '🎬'], // host-less cinematic
  [/sensual|motion|image[-_]?story/, '💞'], // sensual-motion / image→video
  [/baked[-_]?text/, '🔤'], // illustrated / baked-text
  [/kinetic|countdown/, '⏱️'], // kinetic countdown
]
function glyphForTemplate(tpl) {
  const hay = `${tpl.key || ''} ${tpl.produce_style || ''} ${tpl.plan_style || ''}`.toLowerCase()
  for (const [re, g] of TPL_GLYPHS) if (re.test(hay)) return g
  return '🎞️' // generic film frame
}

/**
 * Cover band for a template card. Shows the channel's real brand frame when one
 * is uploaded; on a load error (or no channel) it degrades to the template-style
 * glyph on the channel-accent tint (--ch inherited from the card).
 */
function TemplateCover({ coverUrl, glyph }) {
  const [errored, setErrored] = useState(false)
  const showImg = coverUrl && !errored
  return (
    <div className={'studio-cover' + (showImg ? '' : ' studio-cover-fallback')}>
      {showImg ? (
        <img src={coverUrl} alt="" loading="lazy" onError={() => setErrored(true)} />
      ) : (
        <span className="studio-cover-glyph" aria-hidden="true">
          {glyph}
        </span>
      )}
    </div>
  )
}
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
            const coverUrl = chan ? RENDERS_BASE + chan.key + '/assets/cover.jpg' : null
            return (
              <Link
                key={tpl.key}
                className="card studio-card tpl-card"
                to={`/studio/templates/${tpl.key}`}
                style={accent ? { '--ch': accent } : undefined}
              >
                <TemplateCover coverUrl={coverUrl} glyph={glyphForTemplate(tpl)} />
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
