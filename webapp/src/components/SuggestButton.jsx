import { useState, useRef, useEffect } from 'react'
import { api } from '../api'

const POLL_MS = 3000
const MAX_MS = 3 * 60 * 1000

export const SUGGEST_FAIL_MSG =
  "Suggestion job didn't complete — is the worker daemon running?"

/** job.result may be a JSON string or object; extract {title, brief, tags}. */
function parseResult(raw) {
  let v = raw
  if (typeof v === 'string') {
    try {
      v = JSON.parse(v)
    } catch {
      return null
    }
  }
  if (!v || typeof v !== 'object') return null
  if (v.title == null && v.brief == null && v.result && typeof v.result === 'object') {
    v = v.result
  }
  return {
    title: typeof v.title === 'string' ? v.title : '',
    brief:
      typeof v.brief === 'string' ? v.brief : typeof v.prompt === 'string' ? v.prompt : '',
    tags: Array.isArray(v.tags) ? v.tags.map(String) : [],
  }
}

/**
 * "✨ Suggest" autofill: queues a suggest_brief job for the channel, polls the
 * job every 3s (max 3 min), then hands {title, brief, tags} to onResult.
 * Shows a subtle inline status while researching.
 */
export default function SuggestButton({ channelKey, seed, onResult, onError }) {
  const [busy, setBusy] = useState(false)
  const alive = useRef(true)
  useEffect(
    () => () => {
      alive.current = false
    },
    []
  )

  const start = async () => {
    if (busy || !channelKey) return
    setBusy(true)
    try {
      const d = await api.post({
        action: 'suggest_brief',
        channel_key: channelKey,
        seed: seed || '',
      })
      const jobId = d.job && d.job.id
      if (!jobId) throw new Error(SUGGEST_FAIL_MSG)
      const t0 = Date.now()
      while (alive.current && Date.now() - t0 < MAX_MS) {
        await new Promise((res) => setTimeout(res, POLL_MS))
        if (!alive.current) return
        let job = null
        try {
          job = (await api.get(`?r=job&id=${encodeURIComponent(jobId)}`)).job
        } catch {
          // transient poll failure — keep trying until timeout
        }
        if (!job) continue
        if (job.status === 'done') {
          const parsed = parseResult(job.result)
          if (parsed && (parsed.title || parsed.brief)) {
            setBusy(false)
            onResult(parsed)
            return
          }
          break // done but unparseable result -> treat as failure
        }
        if (job.status === 'failed' || job.status === 'cancelled') break
      }
      if (!alive.current) return
      setBusy(false)
      onError(SUGGEST_FAIL_MSG)
    } catch (e) {
      if (!alive.current) return
      setBusy(false)
      onError(e && e.message ? e.message : SUGGEST_FAIL_MSG)
    }
  }

  return (
    <span className="suggest-wrap">
      {busy && (
        <span className="suggest-status">Researching this channel's data + trends…</span>
      )}
      <button
        type="button"
        className="btn btn-ghost btn-xs"
        onClick={start}
        disabled={busy || !channelKey}
        title={
          channelKey
            ? 'AI-suggest a title + brief for this channel'
            : 'Select a channel first'
        }
      >
        {busy ? '✨ Working…' : '✨ Suggest'}
      </button>
    </span>
  )
}
