#!/usr/bin/env node
/**
 * Fail the build on a CSS custom property that is used but never defined.
 *
 * This exists because the same bug shipped twice. An undefined custom property
 * does not fall back to anything sensible - the whole declaration becomes
 * invalid at computed-value time and the element INHERITS instead, so the text
 * silently renders in the parent's colour and nothing looks broken enough to
 * notice. First it was --ok and --dead across thirteen call sites; then
 * --text-3 across forty-four, which flattened the type hierarchy on every
 * redesigned page for days.
 *
 * A `var(--x, fallback)` is fine and is not reported: that one renders.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = join(dirname(fileURLToPath(import.meta.url)), '..', 'src')

const walk = (dir) =>
  readdirSync(dir).flatMap((f) => {
    const p = join(dir, f)
    return statSync(p).isDirectory() ? walk(p) : /\.(jsx?|css)$/.test(p) ? [p] : []
  })

const files = walk(SRC)
const css = files.filter((f) => f.endsWith('.css')).map((f) => readFileSync(f, 'utf8')).join('\n')
const defined = new Set([...css.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]))

const bad = []
for (const f of files) {
  const text = readFileSync(f, 'utf8')
  const lines = text.split('\n')
  lines.forEach((line, i) => {
    for (const m of line.matchAll(/var\(\s*(--[a-z0-9-]+)\s*(,)?/g)) {
      // A local property set on the element itself (--ch, --tone) is defined at
      // runtime by inline style, so only flag it when no fallback is given.
      if (!defined.has(m[1]) && !m[2]) {
        bad.push(`${f.replace(SRC, 'src')}:${i + 1}  var(${m[1]}) is never defined`)
      }
    }
  })
}

if (bad.length) {
  console.error(`\n✖ ${bad.length} undefined CSS custom propert${bad.length === 1 ? 'y' : 'ies'}:\n`)
  bad.forEach((b) => console.error('  ' + b))
  console.error(
    '\nAn undefined property inherits rather than falling back, so this renders\n' +
    'as the wrong colour instead of an obvious error. Define it in the :root in\n' +
    'styles.css, or give the use a fallback: var(--x, var(--neutral)).\n'
  )
  process.exit(1)
}
console.log(`✓ ${defined.size} tokens defined, every var() reference resolves`)
