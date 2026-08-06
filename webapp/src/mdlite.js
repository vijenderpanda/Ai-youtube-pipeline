/**
 * mdlite — dependency-free markdown-lite → HTML for review docs.
 *
 * Safety model: the WHOLE source is HTML-escaped first, then a small trusted
 * subset of tags is rebuilt from the escaped text. No raw HTML from the
 * document ever reaches the output. Supported: # ## ### headings, **bold**,
 * *italic*, `inline code`, ``` fenced blocks, - and 1. lists, > blockquotes,
 * [text](url) links (http/https only), --- rules, and simple | tables.
 */

/** Escape for HTML text nodes (& < > — quotes are safe in element content). */
export function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/** Inline spans on already-escaped text: code, links, bold, italic. */
function inline(escaped) {
  const codes = []
  let out = escaped.replace(/`([^`]+)`/g, (m, c) => {
    codes.push(c)
    return `\x00${codes.length - 1}\x00`
  })
  out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, (m, txt, url) => {
    const href = url.replace(/"/g, '%22')
    return `<a href="${href}" target="_blank" rel="noopener">${txt}</a>`
  })
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  out = out.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
  return out.replace(/\x00(\d+)\x00/g, (m, i) => `<code>${codes[+i]}</code>`)
}

/** '| a | b |' -> ['a', 'b'] (cells inline-rendered). */
function cells(row) {
  const parts = row.trim().split('|')
  if (parts.length && parts[0].trim() === '') parts.shift()
  if (parts.length && parts[parts.length - 1].trim() === '') parts.pop()
  return parts.map((c) => inline(c.trim()))
}

const isTableSep = (row) => /^\s*\|?[\s:|-]+\|?\s*$/.test(row) && row.includes('-')

function table(rows) {
  let head = null
  let body = rows
  if (rows.length >= 2 && isTableSep(rows[1])) {
    head = cells(rows[0])
    body = rows.slice(2)
  }
  const out = ['<table>']
  if (head) out.push(`<thead><tr>${head.map((c) => `<th>${c}</th>`).join('')}</tr></thead>`)
  out.push(
    `<tbody>${body
      .map((r) => `<tr>${cells(r).map((c) => `<td>${c}</td>`).join('')}</tr>`)
      .join('')}</tbody>`
  )
  out.push('</table>')
  return out.join('')
}

/** Render markdown-lite source to a safe HTML string (style with .mdlite). */
export function renderMdLite(md) {
  const lines = escapeHtml(md).split(/\r?\n/)
  const out = []
  const para = []
  const flush = () => {
    if (para.length) out.push(`<p>${para.map(inline).join('<br>')}</p>`)
    para.length = 0
  }

  let i = 0
  while (i < lines.length) {
    const line = lines[i]

    // ``` fenced code block (contents stay literal)
    if (/^```/.test(line)) {
      flush()
      const buf = []
      i++
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++])
      i++ // closing fence (or EOF)
      out.push(`<pre class="md-fence"><code>${buf.join('\n')}</code></pre>`)
      continue
    }

    if (!line.trim()) {
      flush()
      i++
      continue
    }

    const h = /^(#{1,3})\s+(.+)$/.exec(line)
    if (h) {
      flush()
      const n = h[1].length
      out.push(`<h${n}>${inline(h[2])}</h${n}>`)
      i++
      continue
    }

    if (/^\s*-{3,}\s*$/.test(line)) {
      flush()
      out.push('<hr>')
      i++
      continue
    }

    // blockquote — '>' is '&gt;' after escaping
    if (/^&gt;\s?/.test(line)) {
      flush()
      const buf = []
      while (i < lines.length && /^&gt;\s?/.test(lines[i]))
        buf.push(lines[i++].replace(/^&gt;\s?/, ''))
      out.push(`<blockquote>${buf.map(inline).join('<br>')}</blockquote>`)
      continue
    }

    if (/^\s*[-*]\s+/.test(line)) {
      flush()
      const buf = []
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i]))
        buf.push(lines[i++].replace(/^\s*[-*]\s+/, ''))
      out.push(`<ul>${buf.map((t) => `<li>${inline(t)}</li>`).join('')}</ul>`)
      continue
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      flush()
      const buf = []
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i]))
        buf.push(lines[i++].replace(/^\s*\d+\.\s+/, ''))
      out.push(`<ol>${buf.map((t) => `<li>${inline(t)}</li>`).join('')}</ol>`)
      continue
    }

    if (/^\s*\|/.test(line)) {
      flush()
      const rows = []
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++])
      out.push(table(rows))
      continue
    }

    para.push(line)
    i++
  }
  flush()
  return out.join('\n')
}
