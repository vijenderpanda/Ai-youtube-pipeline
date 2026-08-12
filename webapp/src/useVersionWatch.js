import { useEffect, useState } from 'react'

/**
 * useVersionWatch — detect when a new frontend build has been deployed while
 * this tab stayed open, and offer a reload.
 *
 * Why: the dashboard polls DATA every few seconds but never reloads its own
 * CODE. A tab left open across a deploy keeps running the old bundle forever —
 * which is exactly how a `direct`-mode episode (Studio's v16 path) can look
 * "missing" in an old tab while it's actually there. We fingerprint the running
 * bundle from index.html at boot, then re-fetch index.html on an interval and
 * compare. index.html is served no-store (see webapp/public/_headers), so the
 * fetch always sees the freshly-deployed shell.
 *
 * Returns `stale` — true once a different main bundle is live. The caller shows
 * a reload banner; we never auto-reload (could interrupt mid-edit).
 */
const BUNDLE_RE = /assets\/index-[\w-]+\.js/

async function fetchBundleId() {
  try {
    const res = await fetch('/index.html', { cache: 'no-store' })
    if (!res.ok) return null
    const html = await res.text()
    const m = html.match(BUNDLE_RE)
    return m ? m[0] : null
  } catch {
    return null // offline / transient — treat as "unchanged"
  }
}

export function useVersionWatch(intervalMs = 60000) {
  const [stale, setStale] = useState(false)

  useEffect(() => {
    let cancelled = false
    let current = null

    const check = async () => {
      const id = await fetchBundleId()
      if (cancelled || !id) return
      if (current == null) {
        current = id // first successful read = the bundle we booted with
        return
      }
      if (id !== current) setStale(true)
    }

    check() // establish baseline immediately
    const t = setInterval(check, intervalMs)
    // also re-check when the tab regains focus (common: user comes back hours later)
    const onVis = () => {
      if (document.visibilityState === 'visible') check()
    }
    document.addEventListener('visibilitychange', onVis)

    return () => {
      cancelled = true
      clearInterval(t)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [intervalMs])

  return stale
}
