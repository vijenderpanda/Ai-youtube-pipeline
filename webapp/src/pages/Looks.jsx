import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { RENDERS_BASE } from '../config'
import Toast, { useToast } from '../components/Toast'

/* =============================================================================
   LOOKS — the design a channel's videos are made through.

   A LOOK is the frames (host, music bed, outro sting, composition) plus, when
   designed, the scene sequence. Locked versions are IMMUTABLE: that is what
   makes a shipped video reproducible months later, and it is why changing a
   frame never edits the live look in place — it opens a draft copy, and
   publishing it creates v(N+1).

   Two verbs on every frame, both of which the factory already supports:
     · CHANGE — swap the slot to another revision (set_template_version_asset)
     · MAKE A NEW ONE — hand it to a worker, which generates a fresh revision
       (regenerate_asset → a shell_script job) and hands it back as v(N+1) of
       that slot, ready to choose.
   ========================================================================== */

const SLOT_LABEL = {
  host_outfit: 'Host',
  music_bed: 'Music bed',
  outro_sting: 'Outro',
  remotion_comp: 'Composition',
  cover: 'Cover',
  hook: 'Hook card',
}
const SLOT_ORDER = ['host_outfit', 'music_bed', 'outro_sting', 'remotion_comp']

export default function Looks() {
  const { templateKey } = useParams()
  const { toast, show } = useToast()
  const [selId, setSelId] = useState('')
  const [openSlot, setOpenSlot] = useState(null)
  const [busy, setBusy] = useState('')

  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const channels = (chansQ.data && chansQ.data.channels) || []
  const chan = channels.find((c) => c.template === templateKey)
  const channelKey = chan && chan.key

  const tvQ = usePoll(
    () => (templateKey ? api.get(`?r=template_versions&template_key=${encodeURIComponent(templateKey)}`) : Promise.resolve(null)),
    12000,
    [templateKey]
  )
  const assetsQ = usePoll(
    () => (channelKey ? api.get(`?r=assets&channel=${encodeURIComponent(channelKey)}`) : Promise.resolve(null)),
    0,
    [channelKey]
  )
  const tplQ = usePoll(() => api.get('?r=templates'), 0)
  const jobsQ = usePoll(() => api.get('?r=jobs&limit=25'), 10000)

  const versions = (tvQ.data && tvQ.data.versions) || []
  const tplAssets = (tvQ.data && tvQ.data.assets) || []
  const allBlocks = (tvQ.data && tvQ.data.blocks) || []
  const revisions = (assetsQ.data && assetsQ.data.versions) || []
  // Which slots a worker can actually build. Every one of Looks' four slots was
  // offering "Make a new one on a worker" while the server had a generator for
  // none of them, so each click was a guaranteed 400 under copy that promised
  // the opposite. The list comes from the server; the button follows it.
  const generatable = (assetsQ.data && assetsQ.data.generatable) || []
  const templates = (tplQ.data && tplQ.data.templates) || []
  const jobs = (jobsQ.data && jobsQ.data.jobs) || []
  const tpl = templates.find((t) => t.key === templateKey)
  const liveId = tpl && tpl.active_version_id

  const selected = useMemo(
    () => versions.find((v) => v.id === selId) || versions.find((v) => v.id === liveId) || versions[0] || null,
    [versions, selId, liveId]
  )
  const isDraft = selected && selected.status === 'draft'
  const blocks = useMemo(
    () => allBlocks.filter((b) => selected && b.template_version_id === selected.id),
    [allBlocks, selected]
  )

  /* The frames this version carries — from the editable rows on a draft, or the
     frozen composition on a locked one. */
  const frames = useMemo(() => {
    if (!selected) return []
    const out = []
    if (isDraft) {
      for (const a of tplAssets.filter((a) => a.template_version_id === selected.id)) {
        const rev = revisions.find((r) => r.id === a.asset_version_id)
        out.push({
          slot: a.asset_type,
          version: rev && rev.version,
          label: (rev && rev.label) || a.asset_type,
          thumb: rev && rev.thumb_path,
          version_id: a.asset_version_id,
        })
      }
    } else {
      for (const [slot, v] of Object.entries(selected.composition || {})) {
        if (slot.startsWith('_') || !v || typeof v !== 'object') continue
        out.push({ slot, version: v.version, label: v.label, thumb: v.thumb_path, version_id: v.version_id })
      }
    }
    return out.sort(
      (a, b) => (SLOT_ORDER.indexOf(a.slot) + 99) % 99 - ((SLOT_ORDER.indexOf(b.slot) + 99) % 99)
    )
  }, [selected, isDraft, tplAssets, revisions])

  const revsFor = (slot) =>
    revisions
      .filter((r) => r.asset_type === slot && r.status !== 'retired')
      .sort((a, b) => (b.version || 0) - (a.version || 0))

  /* Any worker currently building a new revision, so the frame can say so. */
  const buildingSlot = (slot) =>
    jobs.find(
      (j) =>
        (j.status === 'queued' || j.status === 'running') &&
        j.meta && j.meta.asset_type === slot &&
        (!j.channel_key || j.channel_key === channelKey)
    )

  const post = async (body, tag, ok) => {
    setBusy(tag)
    try {
      const d = await api.post(body)
      if (d && d.error) throw new Error(d.error)
      show(ok, 'ok')
      tvQ.refresh(); assetsQ.refresh(); tplQ.refresh(); jobsQ.refresh()
    } catch (e) {
      show(e.message, 'error')
    }
    setBusy('')
  }

  const swap = (slot, asset_version_id) =>
    post(
      { action: 'set_template_version_asset', template_version_id: selected.id, asset_type: slot, asset_version_id },
      'swap:' + slot,
      'Frame swapped in this draft'
    ).then(() => setOpenSlot(null))

  const makeNew = (slot, from_version_id) =>
    post(
      { action: 'regenerate_asset', channel_key: channelKey, asset_type: slot, from_version_id },
      'regen:' + slot,
      'Handed to a worker — the new one arrives as a revision you can choose'
    )

  const editLook = () =>
    post(
      { action: 'create_template_version', template_key: templateKey, channel_key: channelKey, from_version_id: selected.id },
      'edit',
      'Draft opened — the live look keeps producing untouched'
    )

  const publish = () =>
    post(
      { action: 'lock_template_version', template_version_id: selected.id, make_active: true },
      'publish',
      'Published — new pieces run through this version'
    )

  /* ── index: every channel's look ─────────────────────────────────────── */
  if (!templateKey) {
    return (
      <div className="piece looks">
        <div className="piece-head">
          <div>
            <div className="crumb">Looks</div>
            <h1 className="piece-title">The designs your videos are made through</h1>
            <div className="piece-sub">One look per channel · locked versions are immutable</div>
          </div>
        </div>
        <div className="today-stack">
          {channels.filter((c) => c.template).map((c) => (
            <Link key={c.key} to={'/looks/' + c.template} className="today-card">
              <span className="ic">◈</span>
              <span>
                <span className="t">{c.name || c.key}</span>
                <span className="s">{c.template}</span>
              </span>
              <span className="verb">Open →</span>
            </Link>
          ))}
        </div>
        <Toast toast={toast} />
      </div>
    )
  }

  if (tvQ.loading && !tvQ.data) return <p className="dim">Loading…</p>

  return (
    <div className="piece looks">
      <div className="piece-head">
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="crumb">
            <Link className="link" to="/looks">Looks</Link> / {templateKey}
          </div>
          <h1 className="piece-title">{(chan && chan.name) || templateKey}</h1>
          <div className="piece-sub">
            {selected ? `v${selected.version}` : '—'}
            {selected && selected.id === liveId ? ' · live' : ''}
            {selected && selected.label ? ' · ' + selected.label : ''}
          </div>
        </div>
        <div className="piece-chips">
          {selected && (
            <span className={'chip ' + (isDraft ? 'warn-chip' : 'ok-chip')}>
              {isDraft ? 'draft — editable' : 'locked — immutable'}
            </span>
          )}
        </div>
      </div>

      {/* version rail */}
      <div className="looks-rail">
        {versions.map((v) => (
          <button
            key={v.id}
            type="button"
            className={'lv' + (selected && v.id === selected.id ? ' on' : '') + (v.id === liveId ? ' live' : '')}
            onClick={() => setSelId(v.id)}
          >
            v{v.version}
            <span className="st">{v.id === liveId ? 'live' : v.status}</span>
          </button>
        ))}
      </div>

      <div className="piece-cols">
        {/* ── frames ──────────────────────────────────────────────────── */}
        <section className="pc-card">
          <span className="pc-eyebrow">
            The frames this look locks {isDraft && <span className="soft">· click a frame to change it</span>}
          </span>
          <div className="piece-cast">
            {frames.map((f) => {
              const building = buildingSlot(f.slot)
              const open = openSlot === f.slot
              return (
                <div key={f.slot}>
                  <button
                    type="button"
                    className="cf as-btn"
                    onClick={() => isDraft && setOpenSlot(open ? null : f.slot)}
                    disabled={!isDraft}
                  >
                    {f.thumb ? <img src={RENDERS_BASE + f.thumb} alt="" loading="lazy" /> : <span className="ph" />}
                    <div className="meta">
                      <div className="k">{SLOT_LABEL[f.slot] || f.slot}</div>
                      <div className="l">{f.label}</div>
                    </div>
                    <span className="v">
                      {building ? <span className="warn-txt">building…</span> : 'v' + f.version}
                    </span>
                  </button>

                  {open && (
                    <div className="looks-swap">
                      <div className="pc-eyebrow" style={{ margin: '0 0 8px' }}>
                        Other revisions of {SLOT_LABEL[f.slot] || f.slot}
                      </div>
                      <div className="opts">
                        {revsFor(f.slot).map((r) => (
                          <button
                            key={r.id}
                            type="button"
                            className={'opt' + (r.id === f.version_id ? ' cur' : '')}
                            disabled={!!busy || r.id === f.version_id}
                            onClick={() => swap(f.slot, r.id)}
                          >
                            {r.thumb_path ? <img src={RENDERS_BASE + r.thumb_path} alt="" loading="lazy" /> : <span className="ph" />}
                            <span className="nm">v{r.version}</span>
                            <span className="lb">{r.label || '—'}</span>
                            {r.id === f.version_id && <span className="cu">in use</span>}
                          </button>
                        ))}
                      </div>
                      {generatable.includes(f.slot) ? (
                        <>
                          <button
                            type="button"
                            className="btn btn-ghost"
                            style={{ marginTop: 10 }}
                            disabled={!!busy || !!building}
                            onClick={() => makeNew(f.slot, f.version_id)}
                          >
                            {busy === 'regen:' + f.slot ? 'Handing over…' : '✦ Make a new one on a worker'}
                          </button>
                          <div className="dim small" style={{ marginTop: 7 }}>
                            A worker generates a fresh {(SLOT_LABEL[f.slot] || f.slot).toLowerCase()} from this one and
                            hands it back as the next revision — then you choose it here.
                          </div>
                        </>
                      ) : (
                        <div className="dim small" style={{ marginTop: 10 }}>
                          No worker can build a {(SLOT_LABEL[f.slot] || f.slot).toLowerCase()} yet — this one is made
                          by hand and swapped in above.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          {!isDraft && (
            <div className="dim small" style={{ marginTop: 11 }}>
              This version is locked, so its frames can’t change — that’s what keeps every video made
              with it reproducible. <b>Edit</b> opens a draft copy instead.
            </div>
          )}
        </section>

        {/* ── scenes + settings ───────────────────────────────────────── */}
        <section className="pc-card">
          <span className="pc-eyebrow">Scenes</span>
          {blocks.length ? (
            <>
              <div className="piece-kv"><span>Designed scenes</span><b>{blocks.length}</b></div>
              <div className="piece-kv">
                <span>Mode</span>
                <b>{((selected.meta && selected.meta.settings) || {}).sequence_mode || 'augment'}</b>
              </div>
            </>
          ) : (
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-2)' }}>
              No designed scene list — this look locks the frames, and each video’s beats are cut from
              its own script.
            </p>
          )}
          <Link className="btn btn-ghost" style={{ marginTop: 11, display: 'inline-block' }} to={'/studio/templates/' + templateKey}>
            Open the sequence designer →
          </Link>

          <span className="pc-eyebrow" style={{ marginTop: 18 }}>Settings</span>
          {Object.entries((selected && ((selected.composition || {})._settings || (selected.meta || {}).settings)) || {}).map(([k, v]) => (
            <div key={k} className="piece-kv"><span>{k.replace(/_/g, ' ')}</span><b>{String(v)}</b></div>
          ))}
        </section>
      </div>

      <div className="piece-foot">
        {isDraft ? (
          <>
            <button className="btn btn-primary" onClick={publish} disabled={!!busy}>
              {busy === 'publish' ? 'Publishing…' : `Publish v${selected.version} →`}
            </button>
            <span className="piece-why">Publishing locks it and points new pieces at it.</span>
          </>
        ) : (
          <>
            <button className="btn btn-primary" onClick={editLook} disabled={!!busy}>
              {busy === 'edit' ? 'Opening…' : 'Edit this look →'}
            </button>
            <span className="piece-why">
              Opens a draft copy. The live look keeps producing until you publish.
            </span>
          </>
        )}
      </div>

      <Toast toast={toast} />
    </div>
  )
}
