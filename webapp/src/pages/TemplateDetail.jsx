import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import {
  resolveAccents,
  accentFor,
  channelEmoji,
  channelMonogram,
} from '../channelColor'
import { templateForChannel, armable } from '../templates'
import {
  SLOTS,
  assetLabel,
  wiringOf,
  kindOf,
  hasCover,
  lineageOf,
  heygenHealth,
  shotCoverage,
  requiredShotRoles,
  usageOf,
  usageBadge,
  usageTitle,
  interchangeableWith,
} from '../assetCatalog'
import EmptyState from '../components/EmptyState'
import MediaPreview, { sampleNoteOf, previewSourceFor } from '../components/MediaPreview'
import ShotRoleChips from '../components/ShotRoleChips'
import Toast, { useToast } from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'

/**
 * TemplateDetail — one factory_templates row.
 *
 * Two halves, and the difference between them is the whole point:
 *   1. "Frames & cosmetics" — what the CHANNEL LOCKS say production uses today
 *      (factory_asset_locks, the layer build_ep_v2 has always read).
 *   2. "Cast" (Phase 4) — composed template VERSIONS. A template names the
 *      PIPELINE; a version names the CAST that pipeline runs with. You fork a
 *      draft (seeded from what production runs today), swap individual slots,
 *      eyeball the picks side by side, then LOCK — and locking freezes each
 *      pick's build_ref into the version, which is what the renderer resolves.
 *
 * There is deliberately no "generate preview" here: the preview is the chosen
 * revisions shown together — and, since MediaPreview landed, PLAYED. Every slot
 * row and every swap candidate can be heard/watched from its existing file, so
 * a pick is made on the thing itself instead of on a poster frame. Rendering a
 * fresh sample would spend HeyGen/ElevenLabs credits to show what the assets
 * already are.
 */

const WIRING_LABEL = {
  live: 'Live in render',
  locked: 'Locked · wiring next',
  reference: 'Reference',
}

// Walk parent_version_id → "v3 ← v2 ← v1" (guards against cycles / missing parents).

/* ── Cast SETTINGS ──────────────────────────────────────────────────────────
   Some of what ships is BEHAVIOUR, not a file. `outro_cta` makes the host speak
   a call-to-action over whatever card sits in the outro slot — there is nothing
   to pick from the library, so a composer that only listed frames did not
   describe the thing we actually publish. Drafts hold settings on
   meta.settings; locking freezes them into composition._settings, which is what
   build_ep_v2.resolve_setting() reads. */

/* ── "Generate a new one from this" ────────────────────────────────────────
   The swap drawer is where you notice a pick is close but the wording is
   wrong — so it is where the NEXT revision gets made, instead of sending you
   to a terminal. Mirrors scripts/regen_asset.py's GENERATORS table (and the
   edge action's own copy of it): a slot that is not listed here shows no
   control at all, because a button that could only ever fail is worse than no
   button. */
const GEN_SLOTS = {
  outro_card_gen: {
    what: 'question card',
    fields: [
      {
        name: 'q',
        label: 'Question — use | to split lines',
        placeholder: 'Which one will you try first?|Tell me below',
      },
      { name: 'pill', label: 'Button label', placeholder: 'Comment it below' },
    ],
  },
}

/** The generator behind a picker tile, or undefined — tiles can come from a
 *  sibling slot (outro_card_gen inside the outro_sting drawer), so the tile's
 *  OWN asset_type decides, not the row it is displayed under. */
const genSlotFor = (opt, rowType) => GEN_SLOTS[(opt && opt._fromSlot) || rowType]

/**
 * The inline "new revision from this one" form.
 *
 * Prefilled from the source revision's own meta.gen_params, because the reason
 * you opened it is almost always “this one, but the question should be
 * different”. regen_asset.py inherits anything you leave blank from the
 * parent, so an empty box never silently erases a value.
 */
function RegenForm({ slot, from, pending, onGenerate, onCancel }) {
  const seed = (from.meta && from.meta.gen_params) || {}
  const seedOf = (name) => (seed[name] == null ? '' : String(seed[name]))
  const [vals, setVals] = useState(() => {
    const o = {}
    for (const f of slot.fields) o[f.name] = seedOf(f.name)
    return o
  })
  const ready = slot.fields.every((f) => vals[f.name].trim())
  const changed = slot.fields.some((f) => vals[f.name].trim() !== seedOf(f.name).trim())

  return (
    <form
      className="cast-regen"
      onSubmit={(e) => {
        e.preventDefault()
        if (ready && changed && !pending) onGenerate(vals)
      }}
    >
      <div className="cast-regen-head">
        New {slot.what} from <b>v{from.version}</b> — change one thing
      </div>
      {slot.fields.map((f) => {
        const id = 'cast-regen-' + f.name + '-' + from.id
        return (
          <div key={f.name} className="cast-regen-field">
            <label className="cast-setting-lbl" htmlFor={id}>
              {f.label}
            </label>
            <input
              id={id}
              type="text"
              maxLength={200}
              value={vals[f.name]}
              placeholder={f.placeholder}
              disabled={pending}
              onChange={(e) => setVals((v) => ({ ...v, [f.name]: e.target.value }))}
            />
          </div>
        )
      })}
      <div className="cast-regen-actions">
        <button type="submit" className="btn-primary" disabled={pending || !ready || !changed}>
          {pending ? 'Generating…' : 'Generate'}
        </button>
        <button type="button" className="btn-ghost" disabled={pending} onClick={onCancel}>
          Cancel
        </button>
        <span className="dim small">
          {!ready
            ? 'Both fields are needed to draw the card.'
            : !changed
              ? 'Change a field — generating an identical copy would only add clutter.'
              : 'It lands here as a new candidate. Nothing is swapped for you.'}
        </span>
      </div>
    </form>
  )
}

const CTA_MODES = [
  { id: 'auto', label: 'Auto', hint: 'The host composes a fresh call-to-action for every episode' },
  { id: 'off', label: 'Off', hint: 'This cast adds no spoken call-to-action' },
  { id: 'custom', label: 'Custom line', hint: 'The host speaks the line you type, word for word' },
]

/** '' / null / undefined = the setting is not set → the build speaks nothing. */
const ctaModeOf = (value) =>
  value === 'auto' ? 'auto' : typeof value === 'string' && value.trim() ? 'custom' : 'off'

const ctaSummary = (value) => {
  const mode = ctaModeOf(value)
  if (mode === 'auto') return 'Auto — a fresh line composed per episode'
  if (mode === 'custom') return 'Custom line — spoken word for word'
  return 'Off — this cast adds no spoken call-to-action'
}

/**
 * The outro_cta control: Auto / Off / Custom line.
 *
 * Mounted with a key that includes the saved value, so the local radio + text
 * state can never drift from what the server last confirmed. A LOCKED version
 * renders read-only — the API returns 409 on a non-draft, and an editable
 * control that always failed would be a lie about what the page can do.
 */
function OutroCtaSetting({ value, isDraft, busy, onSet }) {
  const saved = ctaModeOf(value)
  const [mode, setMode] = useState(saved)
  const [line, setLine] = useState(saved === 'custom' ? value : '')
  const pending = busy === 'setting:outro_cta'
  const inputId = 'cast-setting-outro-cta-line'
  const trimmed = line.trim()

  if (!isDraft) {
    return (
      <div className="cast-setting-read">
        <span className={'chip cast-setting-val cast-setting-' + saved}>
          {CTA_MODES.find((m) => m.id === saved).label}
        </span>
        <span className="dim small">{ctaSummary(value)}</span>
        {saved === 'custom' && <span className="cast-setting-line">“{value}”</span>}
        <span className="dim small cast-frozen-tag">frozen</span>
      </div>
    )
  }

  const pick = (id) => {
    setMode(id)
    // "Custom line" only reveals the field — nothing is spoken until a line is
    // saved, so posting an empty value here would silently mean "off".
    if (id === 'auto') onSet('auto')
    else if (id === 'off') onSet(null)
  }

  return (
    <>
      <fieldset className="cast-setting-modes" disabled={pending}>
        <legend className="cast-setting-legend">Spoken outro call-to-action</legend>
        {CTA_MODES.map((m) => (
          <label
            key={m.id}
            className={'chip cast-setting-opt' + (mode === m.id ? ' cast-setting-opt-on' : '')}
            title={m.hint}
          >
            <input
              type="radio"
              name="cast-setting-outro-cta"
              value={m.id}
              checked={mode === m.id}
              onChange={() => pick(m.id)}
            />
            {m.label}
          </label>
        ))}
      </fieldset>

      {mode === 'custom' && (
        <div className="cast-setting-custom">
          <label className="cast-setting-lbl" htmlFor={inputId}>
            Line the host speaks, word for word
          </label>
          <div className="cast-setting-row">
            <input
              id={inputId}
              type="text"
              maxLength={240}
              value={line}
              disabled={pending}
              placeholder="Follow — I build one of these every day."
              onChange={(e) => setLine(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && trimmed && trimmed !== value) {
                  e.preventDefault()
                  onSet(trimmed)
                }
              }}
            />
            <button
              type="button"
              className="btn-ghost"
              disabled={pending || !trimmed || trimmed === value}
              onClick={() => onSet(trimmed)}
            >
              {pending ? 'Saving…' : 'Save line'}
            </button>
          </div>
        </div>
      )}

      <div className="cast-setting-now">
        <span className="dim small">Now:</span>
        <span className={'chip cast-setting-val cast-setting-' + saved}>{ctaSummary(value)}</span>
      </div>
    </>
  )
}

/**
 * The real HeyGen avatar id behind a host_outfit pick.
 *
 * host_outfit revisions now carry meta.heygen_face = {id, role, short_capable,
 * face}. MediaPreview already shows the `face` image; this names the avatar
 * (short, e.g. "HeyGen f55806a4") so "pick who is Sol" is made on the actual id,
 * not a look-alike still. Renders nothing for a non-host row or a host row with
 * no recorded face (older rows predate the field — absence is unknown).
 */
function HeygenIdChip({ version }) {
  const f = version && version.meta && version.meta.heygen_face
  const id = f && f.id
  if (!id) return null
  // short_capable arrives as a real or string boolean ("false" is truthy!).
  const shortCapable = f.short_capable === true || f.short_capable === 'true'
  const title =
    'HeyGen avatar ' + id + (f.role ? ' · ' + f.role : '') +
    (shortCapable ? ' · short-capable' : '')
  return (
    <span className="chip cast-host-id mono" title={title}>
      HeyGen {String(id).slice(0, 8)}
    </span>
  )
}

export default function TemplateDetail() {
  const { key } = useParams()
  const tplQ = usePoll(() => api.get('?r=templates'), 20000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  // Fetch all asset versions once and filter to this channel client-side (only
  // claude-tricks has rows today) — mirrors Assets.jsx and sidesteps the
  // conditional-hook problem of a channel we only learn about after load.
  const assetsQ = usePoll(() => api.get('?r=assets'), 20000)
  // Phase 4: composed casts for THIS template (versions + their slot rows).
  const tvQ = usePoll(
    () => api.get('?r=template_versions&template_key=' + encodeURIComponent(key)),
    0,
  )
  // Phase 3: usage backlinks, so the swap picker can tell a battle-tested
  // revision from an untried one. Fetched unfiltered for the same reason
  // assetsQ is — the channel is only known after load. Recording started with
  // migration 021, so a candidate with NO entry gets no hint at all; it is not
  // claimed to be unused.
  const useQ = usePoll(() => api.get('?r=asset_backlinks'), 60000)
  const { toast, show } = useToast()
  const [selId, setSelId] = useState(null)   // version the composer is showing
  const [swapFor, setSwapFor] = useState(null) // asset_type whose picker is open
  const [regenFor, setRegenFor] = useState(null) // revision id the "new from this" form is open on
  const [showAllSlots, setShowAllSlots] = useState(false)
  const [unlockConfirm, setUnlockConfirm] = useState(false) // active-cast unlock confirm dialog
  const [busy, setBusy] = useState(null)

  const templates = (tplQ.data && tplQ.data.templates) || []
  const channels = (chansQ.data && chansQ.data.channels) || []
  const versions = (assetsQ.data && assetsQ.data.versions) || []
  const locks = (assetsQ.data && assetsQ.data.locks) || []
  const castVersions = (tvQ.data && tvQ.data.versions) || []
  const castSlots = (tvQ.data && tvQ.data.assets) || []
  const castJoined = (tvQ.data && tvQ.data.asset_versions) || []
  const usage = (useQ.data && useQ.data.usage) || {}

  const tpl = templates.find((t) => t.key === key) || null
  const chan = tpl ? templateForChannel(channels, tpl.key) : null
  const channelKey = chan ? chan.key : null

  // The shot roles THIS template's format demands of its host. A Short needs
  // pip+wide; unknown formats default to the Short roles (fail-safe). `isShort`
  // gates the ✓/⚠ fit badge — a non-Short template has no Short requirement to
  // assert, so the badge would be meaningless there.
  const reqRoles = useMemo(() => requiredShotRoles(tpl), [tpl])
  const isShort = reqRoles.length > 0

  const accents = useMemo(() => resolveAccents(channels), [channels])
  const accent = channelKey ? accentFor(channelKey, accents) : null
  const emoji = channelKey ? channelEmoji(channelKey) : null

  // Lock row per asset_type for this template's channel.
  const lockByType = useMemo(() => {
    const m = {}
    if (!channelKey) return m
    for (const l of locks) if (l.channel_key === channelKey) m[l.asset_type] = l
    return m
  }, [locks, channelKey])

  // Group this channel's versions by asset_type (API orders version desc).
  const groups = useMemo(() => {
    if (!channelKey) return []
    const mine = versions.filter((v) => v.channel_key === channelKey)
    const byType = new Map()
    for (const v of mine) {
      if (!byType.has(v.asset_type)) byType.set(v.asset_type, [])
      byType.get(v.asset_type).push(v)
    }
    return [...byType.entries()]
      .map(([type, vers]) => ({ type, vers }))
      .sort((a, b) => a.type.localeCompare(b.type))
  }, [versions, channelKey])

  // Every revision we can draw, keyed by id — the board's own list plus the
  // rows the composer endpoint joined in (a cast may point at a revision the
  // channel filter above dropped).
  const revById = useMemo(() => {
    const m = {}
    for (const v of castJoined) m[v.id] = v
    for (const v of versions) m[v.id] = v
    return m
  }, [versions, castJoined])

  // Which composed version the composer is showing: explicit pick → the
  // template's active cast → the newest draft → the newest version.
  const selected = useMemo(() => {
    if (!castVersions.length) return null
    return (
      castVersions.find((v) => v.id === selId) ||
      (tpl && castVersions.find((v) => v.id === tpl.active_version_id)) ||
      castVersions.find((v) => v.status === 'draft') ||
      castVersions[0]
    )
  }, [castVersions, selId, tpl])

  // Slot rows of the selected version → { [asset_type]: {pick, alts:[]} }.
  const castByType = useMemo(() => {
    const m = {}
    if (!selected) return m
    for (const s of castSlots) {
      if (s.template_version_id !== selected.id) continue
      if (!m[s.asset_type]) m[s.asset_type] = { pick: null, alts: [] }
      if (s.position === 0) m[s.asset_type].pick = s
      else m[s.asset_type].alts.push(s)
    }
    return m
  }, [castSlots, selected])

  // Rows to show by default (the "+N reference slots" toggle reveals the rest):
  //   • LOCKED cast — ONLY the slots actually frozen into its composition. A
  //     locked cast is 4-5 slots; listing every reference slot as "not in this
  //     cast" was pure clutter, so the rest collapse behind the toggle.
  //   • DRAFT — the slots you compose with (wired slots + whatever this cast
  //     already composes); reference slots stay one toggle away so you can still
  //     pull one in.
  const slotRows = useMemo(() => {
    const all = groups.map((g) => g.type)
    if (showAllSlots) return all
    const locked = !!selected && selected.status === 'locked'
    if (locked) {
      const inCast = new Set(Object.keys(castByType))
      const comp = (selected && selected.composition) || {}
      for (const k of Object.keys(comp)) if (k !== '_settings') inCast.add(k)
      return all.filter((t) => inCast.has(t))
    }
    const keep = new Set(all.filter((t) => wiringOf(t) !== 'reference'))
    for (const t of Object.keys(castByType)) keep.add(t)
    return all.filter((t) => keep.has(t))
  }, [groups, castByType, selected, showAllSlots])

  // The frozen composition of a locked version (build_refs copied at lock).
  const frozen = (selected && selected.composition) || {}

  const isDraft = !!selected && selected.status === 'draft'
  const isLocked = !!selected && selected.status === 'locked'
  const isActive = !!(tpl && selected && tpl.active_version_id === selected.id)

  // Cast SETTINGS live in two places by design: a DRAFT keeps them editable on
  // meta.settings, and locking copies them into composition._settings so the
  // frozen snapshot reproduces the behaviour as well as the frames.
  const settings = useMemo(() => {
    if (!selected) return {}
    const src = isDraft
      ? selected.meta && selected.meta.settings
      : selected.composition && selected.composition._settings
    return src || {}
  }, [selected, isDraft])
  const outroCta = settings.outro_cta
  const ctaOn = ctaModeOf(outroCta) !== 'off'

  // Position-0 picks, in row order — the side-by-side strip AND the lock guard.
  const chosen = useMemo(() => {
    const out = []
    for (const type of slotRows) {
      const slot = castByType[type]
      if (!slot || !slot.pick) continue
      const rev = revById[slot.pick.asset_version_id] || null
      out.push({ type, rev, health: heygenHealth(rev), cov: shotCoverage(rev, reqRoles) })
    }
    return out
  }, [slotRows, castByType, revById, reqRoles])

  const deadPicks = chosen.filter((c) => c.health.dead)
  const missingRev = chosen.filter((c) => !c.rev)
  // A host that structurally cannot render this format (long-form host on a
  // Short) — the EP15 cast. Blocks the lock exactly like a freed HeyGen id.
  const unfitPicks = chosen.filter((c) => c.rev && !c.cov.fits)

  const post = async (bodyObj, tag, after) => {
    setBusy(tag)
    try {
      const res = await api.post(bodyObj)
      await tvQ.refresh()
      await tplQ.refresh()
      if (after) after(res)
    } catch (e) {
      show(e.message || 'That did not work')
    } finally {
      setBusy(null)
    }
  }

  // Fork: from the active cast if there is one, else from the version on screen,
  // else a fresh draft seeded from the channel's live locks (create_template_version
  // does the seeding — a new draft starts as exactly what production runs today).
  const fork = () => {
    const from =
      (tpl && tpl.active_version_id) || (selected && selected.id) || null
    post(
      {
        action: 'create_template_version',
        template_key: key,
        ...(channelKey ? { channel_key: channelKey } : {}),
        ...(from ? { from_version_id: from } : { seed_from_locks: true }),
      },
      'fork',
      (res) => {
        if (res && res.version) setSelId(res.version.id)
        setSwapFor(null)
      },
    )
  }

  const swapTo = (asset_type, asset_version_id) =>
    post(
      {
        action: 'set_template_version_asset',
        template_version_id: selected.id,
        asset_type,
        asset_version_id,
        position: 0,
      },
      'swap:' + asset_type,
      () => setSwapFor(null),
    )

  // "Generate a new one from this" — the drawer's own generator. Queues
  // scripts/regen_asset.py on the existing shell_script job type; the worker
  // registers the result as a CANDIDATE derived from `src`, so it appears in
  // this same drawer (assetsQ) and is still chosen deliberately.
  const regenerate = (src, asset_type, params) => {
    const firstLine = String(params.q || '').split('|')[0].trim()
    post(
      {
        action: 'regenerate_asset',
        channel_key: channelKey,
        asset_type,
        from_version_id: src.id,
        params,
        label: firstLine ? firstLine.slice(0, 60) : '',
      },
      'regen:' + src.id,
      () => {
        setRegenFor(null)
        assetsQ.refresh()
        show('Generating — the new revision appears here when the worker finishes.')
      },
    )
  }

  // A cast setting is behaviour, not a slot — same post()/refresh path as a
  // swap. `value: null` deletes the key (the API's own contract for "unset").
  const setSetting = (name, value) =>
    post(
      {
        action: 'set_template_version_setting',
        template_version_id: selected.id,
        name,
        value,
      },
      'setting:' + name,
    )

  const lockCast = () =>
    post(
      { action: 'lock_template_version', template_version_id: selected.id, make_active: true },
      'lock',
    )

  // "Edit this cast" — the counterpart to Fork. Unlock this exact version back to
  // a draft so the existing swap/settings/Lock UI takes over and the owner edits
  // in place, then re-locks. confirm_active is only sent for the ACTIVE cast,
  // where re-opening it means production falls back until re-lock. The refresh
  // (mirrors lockCast/swapTo) flips the whole panel to draft/editable.
  const unlockCast = (confirmActive) =>
    post(
      {
        action: 'unlock_template_version',
        template_version_id: selected.id,
        ...(confirmActive ? { confirm_active: true } : {}),
      },
      'unlock',
      (res) => {
        if (res && res.version) setSelId(res.version.id)
        setUnlockConfirm(false)
        setSwapFor(null)
        setRegenFor(null)
      },
    )

  // A non-active locked version unlocks with no ceremony. The active cast is the
  // one production renders, so it gets the warning dialog first.
  const editCast = () => {
    if (isActive) setUnlockConfirm(true)
    else unlockCast(false)
  }

  const retireCast = (id) =>
    post({ action: 'retire_template_version', template_version_id: id }, 'retire:' + id, () =>
      setSelId(null),
    )

  // Still loading the template row.
  if (tplQ.loading && tplQ.data == null) {
    return (
      <div className="page">
        <header className="page-head">
          <div>
            <div className="crumbs">
              <Link className="link" to="/studio/templates">Templates</Link>{' '}
              <span className="dim">/</span> <span className="mono">{key}</span>
            </div>
            <h1>Loading…</h1>
          </div>
        </header>
      </div>
    )
  }

  if (!tpl) {
    return (
      <div className="page">
        <header className="page-head">
          <div>
            <div className="crumbs">
              <Link className="link" to="/studio/templates">Templates</Link>{' '}
              <span className="dim">/</span> <span className="mono">{key}</span>
            </div>
            <h1>Template not found</h1>
          </div>
        </header>
        <EmptyState
          message={`No template with key “${key}”`}
          hint="It may have been renamed or removed from factory_templates."
        />
      </div>
    )
  }

  const arm = armable(tpl)
  const uiTag = tpl.produce_ui && tpl.produce_ui.tag
  const hasFrames = groups.length > 0

  return (
    <div className="page" style={accent ? { '--ch': accent } : undefined}>
      <header className="page-head">
        <div>
          <div className="crumbs">
            <Link className="link" to="/studio/templates">Templates</Link>{' '}
            <span className="dim">/</span> <span className="mono">{tpl.key}</span>
          </div>
          <h1>{tpl.name || tpl.key}</h1>
          <p className="sub">
            {tpl.aspect} · {tpl.runtime_s}s
            {tpl.description ? ' · ' + tpl.description : ''}
          </p>
          <div className="tpl-head-meta">
            {arm ? (
              <span className="chip tpl-armable">Ready to arm</span>
            ) : (
              <span className="chip tpl-starter">Starter — can’t arm yet</span>
            )}
            {tpl.blueprint_source && (
              <span className="dim small mono">{tpl.blueprint_source}</span>
            )}
          </div>
        </div>
      </header>

      {assetsQ.error && <div className="error-bar">{assetsQ.error.message}</div>}

      <div className="tpl-section-title">Frames &amp; cosmetics</div>

      {hasFrames ? (
        <div className="tpl-frames">
          {groups.map(({ type, vers }) => {
            const byId = {}
            for (const v of vers) byId[v.id] = v
            const lock = lockByType[type]
            const locked =
              (lock && lock.locked_version_id && byId[lock.locked_version_id]) ||
              vers.find((v) => v.status === 'locked') ||
              null
            const head = locked || vers[0]
            const wiring = wiringOf(type)
            const kind = kindOf(type, head)
            const lineage = head ? lineageOf(head, byId) : ''
            return (
              <div key={type} className="card frame-tile" style={accent ? { '--ch': accent } : undefined}>
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
                    {locked && (
                      <span className="studio-cover-live">🔒 v{locked.version}</span>
                    )}
                  </div>
                )}
                <div className="studio-card-body">
                  <div className="studio-card-title frame-title">{assetLabel(type)}</div>
                  <div className="studio-card-sub">
                    {locked && <span className="dim small">v{locked.version}</span>}
                    <span className={'chip frame-wiring frame-wiring-' + wiring}>
                      {WIRING_LABEL[wiring]}
                    </span>
                    <span className="dim small">
                      {vers.length} rev{vers.length > 1 ? 's' : ''}
                    </span>
                  </div>
                  {lineage && <div className="asset-lineage">{lineage}</div>}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="card tpl-blueprint">
          {tpl.blueprint_source && (
            <div className="tpl-blueprint-src">
              <span className="dim small">Blueprint</span>
              <span className="mono">{tpl.blueprint_source}</span>
            </div>
          )}
          {uiTag && <span className="chip">{uiTag}</span>}
          <p className="dim small">
            Frame previews arrive once this channel’s assets are registered.
          </p>
        </div>
      )}

      {/* ── Cast (Phase 4): composed template versions ───────────────── */}
      <div className="tpl-section-title">Cast — the revisions this recipe renders with</div>
      {tvQ.error && <div className="error-bar">{tvQ.error.message}</div>}

      <div className="card cast-card">
        <div className="cast-head">
          <div className="cast-head-copy">
            <div className="cast-head-title">
              {castVersions.length === 0
                ? 'No composed cast yet'
                : `${castVersions.length} version${castVersions.length > 1 ? 's' : ''}`}
            </div>
            <p className="dim small cast-head-sub">
              {castVersions.length === 0
                ? 'Production resolves each slot from the channel locks above. Fork a recipe to mix and match revisions without touching those locks.'
                : 'A locked version is what production renders. Drafts are private scratch — the build ignores them.'}
            </p>
          </div>
          <button
            type="button"
            className="btn-primary"
            disabled={busy === 'fork' || !channelKey}
            onClick={fork}
            title={
              channelKey
                ? 'Copy the current cast into a new draft you can edit'
                : 'No channel produces with this template yet'
            }
          >
            {busy === 'fork' ? 'Forking…' : 'Fork this recipe'}
          </button>
        </div>

        {castVersions.length > 0 && (
          <div className="cast-rail">
            {castVersions.map((v) => {
              const act = tpl.active_version_id === v.id
              return (
                <button
                  key={v.id}
                  type="button"
                  className={
                    'chip cast-ver-chip' +
                    (selected && selected.id === v.id ? ' cast-sel' : '') +
                    (v.status === 'locked' ? ' cast-locked' : ' cast-draft')
                  }
                  onClick={() => {
                    setSelId(v.id)
                    setSwapFor(null)
                    setRegenFor(null)
                  }}
                  title={(v.label || 'no label') + ' · ' + v.status}
                >
                  v{v.version}
                  <span className="cast-chip-tag">
                    {act ? 'ACTIVE' : v.status === 'locked' ? 'locked' : 'draft'}
                  </span>
                </button>
              )
            })}
          </div>
        )}

        {selected && (
          <>
            <div className="cast-status">
              <span className={'chip cast-state-' + selected.status}>
                {selected.status === 'locked' ? '🔒 Locked' : '✎ Draft'}
              </span>
              {isActive && <span className="chip cast-active">Active — production renders this</span>}
              {selected.label && <span className="dim small">{selected.label}</span>}
              <span className="dim small mono">
                {chosen.length} slot{chosen.length === 1 ? '' : 's'} composed
              </span>
            </div>

            {/* Side-by-side preview: the picks together, so the combo is
                eyeballable. Not a render — no credits are spent here. */}
            {chosen.length > 0 && (
              <div className="cast-strip">
                {chosen.map(({ type, rev, health, cov }) => {
                  const isOutroSlot = (SLOTS[type] || {}).buildKey === 'outro_src'
                  // The pick's OWN slot decides whether it is a per-episode
                  // question card (it may sit in the outro_sting row) — an Auto
                  // spoken CTA over a card that already asks a question is the
                  // exact silent EP15 collision.
                  const pickSlot = rev && SLOTS[rev.asset_type]
                  const pickIsCard =
                    !!(pickSlot && pickSlot.perEpisode && pickSlot.buildKey === 'outro_src')
                  // A code/id slot (or a picked-but-missing revision) has no media
                  // to watch — show a labelled mono chip of its build_ref/id, not a
                  // bare glyph.
                  const stripMode = previewSourceFor(type, rev).mode
                  const stripRef =
                    (frozen[type] && frozen[type].build_ref) ||
                    (rev && rev.meta && rev.meta.build_ref) ||
                    (rev && rev.meta && rev.meta.remotion_id) ||
                    assetLabel(type)
                  return (
                    <div
                      key={type}
                      className={'cast-strip-tile' + (health.dead || !cov.fits ? ' cast-dead' : '')}
                    >
                      {rev && stripMode !== 'none' ? (
                        <MediaPreview
                          assetType={type}
                          version={rev}
                          size="tile"
                          className="cast-strip-cover"
                          name={assetLabel(type) + ' v' + rev.version}
                        />
                      ) : (
                        <div className="cast-strip-cover cast-slot-cover-ref">
                          <span className="cast-ref-chip mono" title={stripRef}>
                            {stripRef}
                          </span>
                        </div>
                      )}
                      <div className="cast-strip-label">{assetLabel(type)}</div>
                      <div className="dim small">
                        {rev ? 'v' + rev.version : 'missing revision'}
                      </div>
                      {/* Shot roles + fit, so a long-form host in the cast is
                          obvious at a glance rather than one look-alike cover.
                          The HeyGen id names the actual avatar behind the face. */}
                      <ShotRoleChips version={rev} required={reqRoles} showFit={isShort} />
                      <HeygenIdChip version={rev} />
                      {/* The outro ships with more than its frames when
                          outro_cta is set. If the pick is a question card, a
                          spoken CTA COLLIDES with it — warn instead of reassure. */}
                      {ctaOn && isOutroSlot && (
                        pickIsCard ? (
                          <span
                            className="chip cast-strip-conflict"
                            title="This card already asks a question; an Auto spoken CTA talks over it. Pick one — set the outro CTA to Off, or choose a plain outro sting."
                          >
                            ⚠ CTA talks over this card
                          </span>
                        ) : (
                          <span className="chip cast-strip-add" title={ctaSummary(outroCta)}>
                            ＋ spoken CTA
                          </span>
                        )
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            <div className="cast-slots">
              {slotRows.map((type) => {
                const slot = castByType[type]
                const pick = slot && slot.pick
                const rev = pick ? revById[pick.asset_version_id] : null
                const health = heygenHealth(rev)
                const cov = shotCoverage(rev, reqRoles)
                const wiring = wiringOf(type)
                const froz = frozen[type]
                // Offer every revision that feeds this slot's build key, not just
                // the ones filed under this exact asset_type — the outro slot must
                // include the per-episode question-CTA cards (what we actually
                // shipped), alongside the shared sting. Retired revisions drop out
                // entirely (the edge also refuses one with a 409) — they are dead
                // library assets, not pickable candidates.
                const opts = interchangeableWith(type)
                  .flatMap((t) =>
                    ((groups.find((g) => g.type === t) || { vers: [] }).vers || []).map(
                      (v) => (t === type ? v : { ...v, _fromSlot: t }),
                    ),
                  )
                  .filter((v) => v.status !== 'retired')
                // A reference row is "not in this cast" (no pick), but the slot is
                // still a real registered asset — so preview its locked/newest
                // revision instead of a bare pink dot. The label below still says
                // "not in this cast", so nothing is misread as composed.
                const slotVers = (groups.find((g) => g.type === type) || { vers: [] }).vers || []
                const coverRev =
                  rev || slotVers.find((v) => v.status === 'locked') || slotVers[0] || null
                const coverMode = previewSourceFor(type, coverRev).mode
                const coverRef =
                  (froz && froz.build_ref) ||
                  (coverRev && coverRev.meta && coverRev.meta.build_ref) ||
                  (coverRev && coverRev.meta && coverRev.meta.remotion_id) ||
                  assetLabel(type)
                const open = swapFor === type
                // Which tiles in this drawer can seed a new revision, and which
                // one has its form open right now.
                const anyGen = opts.some((o) => genSlotFor(o, type))
                const regenSrc =
                  opts.find((o) => o.id === regenFor && genSlotFor(o, type)) || null
                const sampleNote = sampleNoteOf(rev)
                return (
                  <div key={type} className={'cast-slot' + (open ? ' cast-slot-open' : '')}>
                    <div className="cast-slot-row">
                      {coverRev && coverMode !== 'none' ? (
                        <MediaPreview
                          assetType={type}
                          version={coverRev}
                          size="row"
                          className="cast-slot-cover"
                          name={
                            assetLabel(type) +
                            (coverRev ? ' v' + coverRev.version : '')
                          }
                        />
                      ) : (
                        // No previewable media (a code/id slot with no sample, or
                        // an empty slot): a labelled mono chip of the build_ref/id,
                        // never a bare dot.
                        <div className="cast-slot-cover cast-slot-cover-ref">
                          <span className="cast-ref-chip mono" title={coverRef}>
                            {coverRef}
                          </span>
                        </div>
                      )}
                      <div className="cast-slot-copy">
                        <div className="cast-slot-title">
                          {assetLabel(type)}
                          <span className={'chip frame-wiring frame-wiring-' + wiring}>
                            {WIRING_LABEL[wiring]}
                          </span>
                        </div>
                        <div className="cast-slot-sub">
                          {rev ? (
                            <>
                              <b>v{rev.version}</b>
                              <span className="dim small">{rev.label || assetLabel(type)}</span>
                            </>
                          ) : pick ? (
                            <span className="dim small">picked revision is missing</span>
                          ) : (
                            <span className="dim small">not in this cast</span>
                          )}
                          {health.dead && (
                            <span className="chip cast-warn-dead">{health.reason}</span>
                          )}
                          {!health.dead && health.warn && (
                            <span className="chip cast-warn">{health.warn}</span>
                          )}
                          {rev && !cov.fits && (
                            <span className="chip cast-warn-dead" title={cov.warn}>
                              can’t render this short
                            </span>
                          )}
                        </div>
                        {/* Shot roles the picked host provides (self-hidden for
                            non-host slots) — the piece the library never showed.
                            The HeyGen id names the actual avatar behind the face. */}
                        <ShotRoleChips version={rev} required={reqRoles} showFit={isShort} />
                        <HeygenIdChip version={rev} />
                        {sampleNote && (
                          <div className="dim small cast-slot-note" title={sampleNote}>
                            ▶ {sampleNote}
                          </div>
                        )}
                        {froz && froz.build_ref && (
                          <div className="asset-buildref mono">{froz.build_ref}</div>
                        )}
                      </div>
                      {isDraft ? (
                        <button
                          type="button"
                          className="btn-ghost cast-swap-btn"
                          onClick={() => {
                            setSwapFor(open ? null : type)
                            setRegenFor(null)
                          }}
                          disabled={busy === 'swap:' + type}
                        >
                          {busy === 'swap:' + type ? '…' : open ? 'Close' : 'Swap'}
                        </button>
                      ) : (
                        <span className="dim small cast-frozen-tag">frozen</span>
                      )}
                    </div>

                    {open && (
                      <div className="cast-picker">
                        {opts.length === 0 && (
                          <span className="dim small">No revisions registered for this slot.</span>
                        )}
                        {opts.map((o) => {
                          const h = heygenHealth(o)
                          // Structural fit: a long-form host cannot render this
                          // Short (no pip/wide). Blocks selection like a freed id.
                          const cov = shotCoverage(o, reqRoles)
                          const retired = o.status === 'retired'
                          const noRef = !(o.meta && o.meta.build_ref)
                          const isPick = pick && pick.asset_version_id === o.id
                          const blocked = h.dead || !cov.fits || retired || noRef
                          const why = h.dead
                            ? h.reason
                            : !cov.fits
                              ? cov.warn
                              : retired
                                ? 'Retired revision'
                                : noRef
                                  ? 'No build_ref — the build cannot resolve it'
                                  : h.warn || 'Use this revision'
                          // Track record. Absent = not recorded, so we render
                          // nothing rather than a "0 eps" that would read as
                          // "never used".
                          const u = usageOf(usage, o.id)
                          const badge = usageBadge(u)
                          const uTitle = usageTitle(u)
                          // The tile carries its own player, so it can no longer
                          // BE a <button> (a button inside a button is invalid
                          // and the inner one stops working). It is a
                          // role="button" instead, and MediaPreview swallows
                          // click/keydown so auditioning never selects.
                          const selectable = !blocked && !isPick && busy !== 'swap:' + type
                          const gen = genSlotFor(o, type)
                          const regenOpen = regenFor === o.id
                          return (
                            <div
                              key={o.id}
                              role="button"
                              tabIndex={selectable ? 0 : -1}
                              aria-disabled={!selectable}
                              aria-label={'Use ' + assetLabel(o._fromSlot || type) + ' v' + o.version}
                              className={
                                'cast-opt' +
                                (isPick ? ' cast-opt-current' : '') +
                                (blocked ? ' cast-opt-dead' : '')
                              }
                              title={[o._fromSlot && assetLabel(o._fromSlot) + ' — same outro slot',
                                      why, uTitle].filter(Boolean).join('\n\n')}
                              onClick={() => {
                                if (selectable) swapTo(type, o.id)
                              }}
                              onKeyDown={(e) => {
                                if (!selectable) return
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault()
                                  swapTo(type, o.id)
                                }
                              }}
                            >
                              <MediaPreview
                                assetType={type}
                                version={o}
                                size="tile"
                                className="cast-opt-cover"
                                name={assetLabel(type) + ' v' + o.version}
                              />
                              <span className="cast-opt-meta">
                                <span className="cast-opt-head">
                                  <b>v{o.version}</b>
                              {o._fromSlot && (
                                <span className="chip cast-alt-slot">{assetLabel(o._fromSlot)}</span>
                              )}
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
                                </span>
                                <span className="dim small">{o.label || assetLabel(type)}</span>
                                {/* Shot roles + fit badge — one source of truth
                                    with the block above (both use shotCoverage).
                                    Self-hidden for non-host candidates. The HeyGen
                                    id names the actual avatar behind the face, so
                                    "pick who is Sol" is made on the id, not a still. */}
                                <ShotRoleChips version={o} required={reqRoles} showFit={isShort} />
                                <HeygenIdChip version={o} />
                                {blocked && <span className="cast-opt-why">{why}</span>}
                                {isPick && !blocked && <span className="cast-opt-why">current pick</span>}
                                {/* Some slots have a real generator behind them,
                                    so the drawer does not have to end at "pick
                                    one of these". Stops the click from reaching
                                    the tile — opening the form must never be a
                                    selection, same rule the players follow. */}
                                {gen && (
                                  <button
                                    type="button"
                                    className="btn-ghost cast-regen-btn"
                                    aria-label={
                                      'Generate a new ' + assetLabel(o._fromSlot || type) +
                                      ' from v' + o.version
                                    }
                                    title={
                                      'Start from this ' + gen.what +
                                      ', change a word, and a new candidate appears here'
                                    }
                                    disabled={!!busy}
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setRegenFor(regenOpen ? null : o.id)
                                    }}
                                    onKeyDown={(e) => e.stopPropagation()}
                                  >
                                    {regenOpen ? 'Cancel' : '⟳ New from this'}
                                  </button>
                                )}
                              </span>
                            </div>
                          )
                        })}
                        {regenSrc && (
                          <RegenForm
                            key={regenSrc.id}
                            slot={genSlotFor(regenSrc, type)}
                            from={regenSrc}
                            pending={busy === 'regen:' + regenSrc.id}
                            onCancel={() => setRegenFor(null)}
                            onGenerate={(params) =>
                              regenerate(regenSrc, regenSrc._fromSlot || type, params)
                            }
                          />
                        )}
                        {opts.length > 0 && !anyGen && (
                          <span className="dim small cast-regen-none">
                            No generator wired for this slot yet — new revisions are registered
                            by the pipeline that builds them.
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
              {groups.length > slotRows.length || showAllSlots ? (
                <button
                  type="button"
                  className="chip asset-more cast-show-all"
                  onClick={() => setShowAllSlots((s) => !s)}
                >
                  {showAllSlots
                    ? isLocked
                      ? 'show only this cast’s slots'
                      : 'show only slots the renderer uses'
                    : `+${groups.length - slotRows.length} reference slots`}
                </button>
              ) : null}
            </div>

            {/* ── Cast settings: the parts of the cast that are not frames ──── */}
            <section className="cast-settings" aria-labelledby="cast-settings-title">
              <div>
                <div className="cast-settings-title" id="cast-settings-title">
                  Cast settings — behaviour that ships with the frames
                </div>
                <p className="dim small cast-settings-sub">
                  {isDraft
                    ? 'Things the build DOES with the frames above. There is no file to choose here.'
                    : 'Frozen with this locked version, so it reproduces the behaviour as well as the frames.'}
                </p>
              </div>

              <div className="cast-setting">
                <div className="cast-setting-copy">
                  <div className="cast-setting-name">
                    Spoken outro call-to-action
                    <span className="dim small mono">outro_cta</span>
                  </div>
                  <p className="dim small cast-setting-what">
                    The host speaks a call-to-action over the outro card. Auto composes a fresh
                    line per episode. An episode can still override this in its own spec.
                  </p>
                </div>
                <div className="cast-setting-ctl">
                  <OutroCtaSetting
                    key={selected.id + '|' + String(outroCta)}
                    value={outroCta}
                    isDraft={isDraft}
                    busy={busy}
                    onSet={(v) => setSetting('outro_cta', v)}
                  />
                </div>
              </div>
            </section>

            <div className="cast-foot">
              <div className="cast-foot-copy">
                {isDraft ? (
                  <p className="dim small">
                    Locking freezes each pick’s build reference into this version and makes it the
                    cast production renders with. You can re-open a locked version to edit it in
                    place, or fork a fresh copy.
                  </p>
                ) : (
                  <>
                    <p className="dim small">
                      Locked {selected.locked_at ? 'and frozen' : ''} — production renders this cast
                      as-is. Change it two ways: edit this version in place, or fork a fresh copy and
                      leave this one frozen.
                    </p>
                    <p className="dim small cast-edit-reproduce">
                      Editing changes what any episode pinned to this cast re-renders as. To keep
                      this version frozen for past episodes, Fork instead.
                    </p>
                  </>
                )}
                {isDraft && deadPicks.length > 0 && (
                  <p className="cast-block">
                    {deadPicks.map((d) => assetLabel(d.type)).join(', ')} points at a freed HeyGen
                    id — swap it before locking.
                  </p>
                )}
                {isDraft && missingRev.length > 0 && (
                  <p className="cast-block">
                    {missingRev.map((d) => assetLabel(d.type)).join(', ')} points at a revision that
                    no longer exists — re-pick it.
                  </p>
                )}
                {isDraft && unfitPicks.length > 0 && (
                  <p className="cast-block">
                    {unfitPicks.map((d) => assetLabel(d.type)).join(', ')} is a long-form host with
                    no pip/wide frames — a short can’t render it. Swap in a short-fit host before
                    locking. (This is the EP15 trap: a cast that can’t build.)
                  </p>
                )}
              </div>
              <div className="cast-foot-actions">
                {isLocked && (
                  <div className="cast-edit-choice">
                    <div className="cast-edit-opt">
                      <button
                        type="button"
                        className="btn-primary"
                        disabled={busy === 'unlock' || busy === 'fork'}
                        onClick={editCast}
                        title="Re-open this exact version as a draft so you can swap slots and re-lock it"
                      >
                        {busy === 'unlock' ? 'Opening…' : 'Edit this cast'}
                      </button>
                      <span className="dim small">Update this version in place</span>
                    </div>
                    <div className="cast-edit-opt">
                      <button
                        type="button"
                        className="btn-ghost"
                        disabled={busy === 'fork' || busy === 'unlock' || !channelKey}
                        onClick={fork}
                        title="Copy this cast into a new draft and leave this version frozen"
                      >
                        {busy === 'fork' ? 'Forking…' : 'Fork a new version'}
                      </button>
                      <span className="dim small">Leave this frozen, start a copy</span>
                    </div>
                  </div>
                )}
                {!isActive && (
                  <button
                    type="button"
                    className="btn-ghost"
                    disabled={busy === 'retire:' + selected.id}
                    onClick={() => retireCast(selected.id)}
                    title="Shelve this version — it stays readable but stops being offered"
                  >
                    Retire
                  </button>
                )}
                {isDraft && (
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={
                      busy === 'lock' ||
                      chosen.length === 0 ||
                      deadPicks.length > 0 ||
                      missingRev.length > 0 ||
                      unfitPicks.length > 0
                    }
                    onClick={lockCast}
                  >
                    {busy === 'lock' ? 'Locking…' : 'Lock this version'}
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>

      <div className="tpl-manage">
        <Link className="link" to="/assets">Manage frames →</Link>
      </div>

      {unlockConfirm && selected && (
        <ConfirmDialog
          title="Edit the active cast?"
          confirmLabel="Edit this cast"
          danger
          busy={busy === 'unlock'}
          onConfirm={() => unlockCast(true)}
          onCancel={() => setUnlockConfirm(false)}
        >
          <p>
            This is the <b>active cast</b> production renders with. Editing it re-opens it as a
            draft, and production falls back until you re-lock it.
          </p>
          <p className="dim small">
            Editing also changes what any episode pinned to this cast re-renders as. To keep this
            version frozen, cancel and Fork a new version instead.
          </p>
        </ConfirmDialog>
      )}

      <Toast toast={toast} />
    </div>
  )
}
