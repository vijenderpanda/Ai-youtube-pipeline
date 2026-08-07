export function timeAgo(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const s = (Date.now() - d.getTime()) / 1000
  if (s < 45) return 'just now'
  if (s < 3600) return `${Math.max(1, Math.floor(s / 60))}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  if (s < 7 * 86400) return `${Math.floor(s / 86400)}d ago`
  return d.toLocaleDateString()
}

/**
 * Duration between two ISO timestamps, formatted as a human-readable window.
 * e.g. syncWindow("2026-08-06T10:00Z", "2026-08-07T08:00Z") → "22h"
 * Shows the span between the two syncs, NOT how long ago the previous one was.
 */
export function syncWindow(fromIso, toIso) {
  if (!fromIso || !toIso) return ''
  const a = new Date(fromIso)
  const b = new Date(toIso)
  if (isNaN(a.getTime()) || isNaN(b.getTime())) return ''
  const s = Math.abs(b.getTime() - a.getTime()) / 1000
  if (s < 120) return `${Math.max(1, Math.round(s))}s`
  if (s < 3600) return `${Math.round(s / 60)}m`
  if (s < 86400) return `${Math.round(s / 3600)}h`
  return `${Math.round(s / 86400)}d`
}

export function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString()
}

/** Local date -> 'YYYY-MM-DD' (no UTC shift). */
export function toISODate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** 'YYYY-MM-DD' -> "Today · Mon, Aug 4" style heading. */
export function fmtDayHeading(dateStr) {
  if (!dateStr) return ''
  const [y, m, d] = dateStr.split('-').map(Number)
  const date = new Date(y, m - 1, d)
  if (isNaN(date.getTime())) return dateStr
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = Math.round((date.getTime() - today.getTime()) / 86400000)
  const base = date.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
  if (diff === 0) return `Today · ${base}`
  if (diff === 1) return `Tomorrow · ${base}`
  if (diff === -1) return `Yesterday · ${base}`
  return base
}

export function fmtBytes(n) {
  const v0 = Number(n)
  if (n == null || isNaN(v0)) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  let v = v0
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v >= 10 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`
}
