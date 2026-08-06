import { useMemo, useState } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import { RENDERS_BASE } from '../config'
import Chips, { ChipsGroup } from '../components/Chips'
import TagsInput from '../components/TagsInput'
import EmptyState from '../components/EmptyState'
import Toast, { useToast } from '../components/Toast'
import { timeAgo, fmtDate } from '../format'

const STATUSES = [
  ['draft', 'Draft'],
  ['armed', 'Armed'],
  ['uploading', 'Uploading'],
  ['scheduled', 'Scheduled'],
  ['published', 'Published'],
  ['failed', 'Failed'],
]

// Chip filter set requested for the page (uploading posts show under "All")
const FILTER_STATUSES = ['draft', 'armed', 'scheduled', 'published', 'failed']

const POST_CHIP_CLASS = {
  draft: 'chip-queued',
  armed: 'post-armed',
  uploading: 'chip-running',
  scheduled: 'cal-queued',
  published: 'chip-done',
  failed: 'chip-failed',
}

function PostStatusChip({ status }) {
  const s = String(status || 'draft').toLowerCase()
  const label = (STATUSES.find(([v]) => v === s) || [s, s])[1]
  return (
    <span className={`chip ${POST_CHIP_CLASS[s] || 'chip-queued'}`}>
      <span className="chip-dot" />
      {label}
    </span>
  )
}

function asArray(v) {
  if (Array.isArray(v)) return v.map(String)
  if (typeof v === 'string' && v.trim()) {
    try {
      const p = JSON.parse(v)
      return Array.isArray(p) ? p.map(String) : []
    } catch {
      return []
    }
  }
  return []
}

/** ISO timestamptz -> value for <input type="datetime-local"> (local time). */
function isoToLocal(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}

function localToIso(v) {
  if (!v) return null
  const d = new Date(v)
  return isNaN(d.getTime()) ? null : d.toISOString()
}

function PostCard({ post, renderPath, onToast, refresh }) {
  const editable = post.status === 'draft' || post.status === 'armed'
  const [form, setForm] = useState({
    yt_title: post.yt_title || '',
    yt_description: post.yt_description || '',
    tags: asArray(post.tags),
    publish_at: isoToLocal(post.publish_at),
  })
  const [busy, setBusy] = useState('')

  const dirty =
    form.yt_title !== (post.yt_title || '') ||
    form.yt_description !== (post.yt_description || '') ||
    form.publish_at !== isoToLocal(post.publish_at) ||
    JSON.stringify(form.tags) !== JSON.stringify(asArray(post.tags))

  const patch = () =>
    api.post({
      action: 'update_post',
      id: post.id,
      patch: {
        yt_title: form.yt_title,
        yt_description: form.yt_description,
        tags: form.tags,
        publish_at: localToIso(form.publish_at),
      },
    })

  const save = async () => {
    if (busy) return
    setBusy('save')
    try {
      await patch()
      onToast('Post saved', 'ok')
      refresh()
    } catch (e) {
      onToast(e.message, 'error')
    }
    setBusy('')
  }

  const arm = async () => {
    if (busy) return
    const when = form.publish_at
      ? new Date(form.publish_at).toLocaleString()
      : '(no publish time set)'
    if (!window.confirm(`This will upload to YouTube and schedule for ${when}. Continue?`)) {
      return
    }
    setBusy('arm')
    try {
      if (dirty) await patch()
      await api.post({ action: 'arm_post', id: post.id })
      onToast('Post armed — the worker will upload and schedule it', 'ok')
      refresh()
    } catch (e) {
      onToast(e.message, 'error')
    }
    setBusy('')
  }

  const disarm = async (msg) => {
    if (busy) return
    setBusy('disarm')
    try {
      await api.post({ action: 'disarm_post', id: post.id })
      onToast(msg, 'ok')
      refresh()
    } catch (e) {
      onToast(e.message, 'error')
    }
    setBusy('')
  }

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const videoSrc = renderPath ? RENDERS_BASE + renderPath : null
  const ytUrl = post.video_id ? `https://youtu.be/${post.video_id}` : null

  return (
    <div className="card post-card">
      {videoSrc ? (
        <video controls preload="metadata" src={videoSrc} />
      ) : (
        <div className="post-novideo">
          <span>No preview available</span>
          {post.local_path && <span className="mono">{post.local_path}</span>}
        </div>
      )}

      <div className="post-body">
        <div className="post-toprow">
          <PostStatusChip status={post.status} />
          <span className="tag">{post.channel_key}</span>
          {post.audience && (
            <span className="tag dim-tag" title="YouTube audience setting (read-only)">
              {post.audience}
            </span>
          )}
          {post.synthetic && (
            <span
              className="tag ultra-chip"
              title="Will be flagged as altered/synthetic content (read-only)"
            >
              synthetic
            </span>
          )}
          <span className="post-time" title={fmtDate(post.created_at)}>
            {timeAgo(post.created_at)}
          </span>
        </div>

        {post.status === 'failed' && post.error && (
          <div className="error-bar post-error">{String(post.error)}</div>
        )}

        <label className="field">
          <span className="field-label">YouTube title</span>
          <input
            className="post-title-input"
            value={form.yt_title}
            onChange={set('yt_title')}
            placeholder="Title shown on YouTube…"
            disabled={!editable}
          />
        </label>

        <label className="field">
          <span className="field-label">Description</span>
          <textarea
            rows={3}
            value={form.yt_description}
            onChange={set('yt_description')}
            placeholder="Description, links, hashtags…"
            disabled={!editable}
          />
        </label>

        <div className="field">
          <span className="field-label">Tags</span>
          <TagsInput
            value={form.tags}
            onChange={(tags) => setForm((f) => ({ ...f, tags }))}
            disabled={!editable}
          />
        </div>

        <label className="field">
          <span className="field-label">Publish at (local time)</span>
          <input
            type="datetime-local"
            value={form.publish_at}
            onChange={set('publish_at')}
            disabled={!editable}
          />
        </label>

        <div className="post-actions">
          {editable && (
            <button className="btn btn-ghost btn-sm" onClick={save} disabled={!!busy || !dirty}>
              {busy === 'save' ? 'Saving…' : 'Save'}
            </button>
          )}
          {post.status === 'draft' && (
            <button
              className="btn btn-primary btn-sm"
              onClick={arm}
              disabled={!!busy || !form.yt_title.trim() || !form.publish_at}
              title={
                !form.yt_title.trim()
                  ? 'Set a YouTube title first'
                  : !form.publish_at
                    ? 'Set a publish time first'
                    : 'Arm for upload'
              }
            >
              {busy === 'arm' ? 'Arming…' : 'Arm ▶'}
            </button>
          )}
          {post.status === 'armed' && (
            <button
              className="btn btn-danger btn-sm"
              onClick={() => disarm('Post disarmed — back to draft')}
              disabled={!!busy}
            >
              {busy === 'disarm' ? 'Disarming…' : 'Disarm'}
            </button>
          )}
          {post.status === 'failed' && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => disarm('Post reset to draft — update it, then arm again')}
              disabled={!!busy}
            >
              {busy === 'disarm' ? 'Resetting…' : 'Back to draft'}
            </button>
          )}
          {(post.status === 'scheduled' || post.status === 'published') && ytUrl && (
            <a className="link" href={ytUrl} target="_blank" rel="noreferrer">
              youtu.be/{post.video_id} →
            </a>
          )}
          {post.status === 'scheduled' && post.publish_at && (
            <span className="dim small">goes live {fmtDate(post.publish_at)}</span>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Posts() {
  const [status, setStatus] = useState('')
  const [channel, setChannel] = useState('')
  const postsQ = usePoll(() => api.get('?r=posts'), 10000)
  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const rendersQ = usePoll(() => api.get('?r=renders'), 0)
  const { toast, show } = useToast()

  const posts = (postsQ.data && postsQ.data.posts) || []
  const channels = (chansQ.data && chansQ.data.channels) || []

  // render_id -> storage_path (public preview URL), from the latest renders
  const renderPaths = useMemo(() => {
    const m = {}
    const renders = (rendersQ.data && rendersQ.data.renders) || []
    for (const r of renders) if (r.id && r.storage_path) m[r.id] = r.storage_path
    return m
  }, [rendersQ.data])

  const filtered = posts.filter(
    (p) => (!status || p.status === status) && (!channel || p.channel_key === channel)
  )

  const countBy = (key, v) => posts.filter((p) => p[key] === v).length

  const statusOptions = [
    { value: '', label: 'All', count: posts.length },
    ...FILTER_STATUSES.map((s) => ({
      value: s,
      label: (STATUSES.find(([v]) => v === s) || [s, s])[1],
      count: countBy('status', s),
    })),
  ]

  const channelOptions = [
    { value: '', label: 'All channels' },
    ...channels.map((c) => ({
      value: c.key,
      label: c.name || c.key,
      count: countBy('channel_key', c.key),
    })),
  ]

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Posts</h1>
          <p className="sub">Review, arm and schedule finished videos for YouTube</p>
        </div>
      </header>

      {postsQ.error && <div className="error-bar">{postsQ.error.message}</div>}

      <div className="chips-bar">
        <ChipsGroup label="Status">
          <Chips options={statusOptions} value={status} onChange={setStatus} ariaLabel="Status" />
        </ChipsGroup>
        <ChipsGroup label="Channel">
          <Chips
            options={channelOptions}
            value={channel}
            onChange={setChannel}
            ariaLabel="Channel"
          />
        </ChipsGroup>
      </div>

      {postsQ.loading && postsQ.data == null ? (
        <p className="dim">Loading…</p>
      ) : filtered.length === 0 ? (
        <EmptyState
          message={posts.length === 0 ? 'No posts yet' : 'No posts match these filters'}
          hint={
            posts.length === 0
              ? 'Production jobs create drafts here automatically — review the metadata, set a publish time, then Arm to upload and schedule.'
              : undefined
          }
        />
      ) : (
        <div className="post-grid">
          {filtered.map((p) => (
            <PostCard
              key={p.id}
              post={p}
              renderPath={p.render_id ? renderPaths[p.render_id] : null}
              onToast={show}
              refresh={postsQ.refresh}
            />
          ))}
        </div>
      )}

      <Toast toast={toast} />
    </div>
  )
}
