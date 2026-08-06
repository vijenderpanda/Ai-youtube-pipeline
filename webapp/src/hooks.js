import { useState, useEffect, useRef, useCallback } from 'react'

/**
 * Fetch + optional polling hook.
 * - Polls every `intervalMs` while the tab is visible (intervalMs 0 = fetch once).
 * - Re-fetches immediately when the tab becomes visible again.
 * - `refresh()` forces a re-fetch (used after mutations).
 */
export function usePoll(fetcher, intervalMs = 0, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [tick, setTick] = useState(0)
  const fnRef = useRef(fetcher)
  fnRef.current = fetcher

  const refresh = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => {
    let alive = true
    const run = async () => {
      if (document.hidden) return
      try {
        const data = await fnRef.current()
        if (alive) setState({ data, error: null, loading: false })
      } catch (e) {
        if (alive) setState((s) => ({ data: s.data, error: e, loading: false }))
      }
    }
    run()
    let id = null
    if (intervalMs > 0) id = setInterval(run, intervalMs)
    const onVis = () => {
      if (!document.hidden) run()
    }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      alive = false
      if (id) clearInterval(id)
      document.removeEventListener('visibilitychange', onVis)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, intervalMs, ...deps])

  return { ...state, refresh }
}
