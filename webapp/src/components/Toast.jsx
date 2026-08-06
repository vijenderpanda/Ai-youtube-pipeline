import { useState, useRef, useCallback, useEffect } from 'react'

/** Tiny page-local toast: const { toast, show } = useToast(); <Toast toast={toast} /> */
export function useToast() {
  const [toast, setToast] = useState(null)
  const timer = useRef(null)

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current)
    },
    []
  )

  const show = useCallback((msg, tone = 'ok') => {
    setToast({ msg, tone, key: Date.now() })
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setToast(null), 4500)
  }, [])

  return { toast, show }
}

export default function Toast({ toast }) {
  if (!toast) return null
  return (
    <div key={toast.key} className={`toast toast-${toast.tone}`} role="status">
      {toast.msg}
    </div>
  )
}
