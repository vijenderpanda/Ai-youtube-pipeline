/* =============================================================================
   PASTE — one parser for the numbers you bring in by hand.

   Two boxes take a paste: Make (before spending an agent run on ideas) and
   Scoreboard (to outrank stored stats). They had separate parsers, which is how
   two things that must agree drift apart — Scoreboard learned to read Studio
   links and Make did not, so the same paste read differently on two screens.

   TWO SHAPES, because two are what actually get pasted.

   BY LINK (exact, and preferred). Anything carrying a YouTube or Studio URL has
   the eleven-character video id in it — studio.youtube.com/video/<ID>/analytics,
   youtu.be/<ID>, watch?v=<ID>, /shorts/<ID>. That is an exact key: no title
   matching and no near-miss. It also means an analytics write-up pastes in as
   prose, which is what one actually looks like when it arrives.

   BY TITLE (the Studio table). Tab- or run-of-spaces separated rows: first
   column the title, first plain number the views, a % is CTR.

   A number is only read as views when the word "views" sits next to it. The
   same sentence routinely carries "45.45% Stayed to watch" or "the 12-second
   mark", and silently reading either as a view count is worse than reading
   nothing at all.
   ========================================================================== */

const VIDEO_ID = /(?:youtu\.be\/|\/video\/|[?&]v=|\/shorts\/)([A-Za-z0-9_-]{11})/g
const VIEWS_NEAR = /\*{0,2}([\d][\d,]*)\*{0,2}\s*views\b/i

/**
 * @returns {{
 *   byId: Map<string, number|null>,   // video id -> views, or null when named without one
 *   byTitle: Map<string, number>,     // lowercased title -> views
 *   rows: Array<{title, views, ctr}>, // the Studio-table rows, for the read-back
 *   ignored: number,                  // table-ish lines that carried no number
 *   size: number,                     // everything the paste named
 * }}
 */
export function parsePaste(txt) {
  const text = String(txt || '')
  const byId = new Map()
  const byTitle = new Map()
  const rows = []
  let ignored = 0

  // by link — per paragraph, so a number stays with its own video
  for (const para of text.split(/\n{2,}|\n(?=\s*[-*•\d])/)) {
    VIDEO_ID.lastIndex = 0
    const ids = [...para.matchAll(VIDEO_ID)].map((m) => m[1])
    if (!ids.length) continue
    const m = para.match(VIEWS_NEAR)
    const views = m ? Number(m[1].replace(/[^\d]/g, '')) : null
    for (const id of ids) if (!byId.has(id)) byId.set(id, views)
  }

  // by title — the Studio table shape. A line already read as a link is skipped
  // so one video is never counted twice.
  for (const raw of text.split('\n')) {
    const l = raw.trim()
    if (!l) continue
    VIDEO_ID.lastIndex = 0
    if (VIDEO_ID.test(l)) continue
    const nums = l.match(/[\d][\d,.]*%?/g) || []
    const title = l.split(/\s{2,}|\t/)[0].trim()
    if (!nums.length || !title || /^video\b/i.test(title)) { ignored += 1; continue }
    const pct = nums.find((n) => n.includes('%')) || null
    const plain = nums.filter((n) => !n.includes('%'))
    const views = plain[0] ? Number(plain[0].replace(/[^\d]/g, '')) : null
    rows.push({ title, views, ctr: pct })
    if (views != null) byTitle.set(title.replace(/[….]+$/, '').toLowerCase(), views)
  }

  return { byId, byTitle, rows, ignored, size: byId.size + byTitle.size }
}

/** Views this paste gives for a video, or null. An id beats a title guess. */
export function freshViewsFor(parsed, v) {
  if (!parsed || !v) return null
  if (v.video_id && parsed.byId.has(v.video_id)) {
    const n = parsed.byId.get(v.video_id)
    if (n != null) return n
  }
  const t = String(v.title || '').toLowerCase()
  for (const [k, views] of parsed.byTitle) {
    if (k.length > 12 && (t.startsWith(k.slice(0, 24)) || k.startsWith(t.slice(0, 24)))) return views
  }
  return null
}

/** The paste named this video by link but gave no view count for it. */
export function namedWithoutNumber(parsed, v) {
  return !!(parsed && v && v.video_id && parsed.byId.get(v.video_id) === null)
}
