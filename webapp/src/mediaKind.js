/**
 * v5 — media kind + extension helpers for the renders library.
 * Kinds in use: video | image | audio | other. When the stored `kind` is
 * missing or contradicts the file extension, the extension wins.
 */

const EXT_KIND = {
  mp4: 'video',
  webm: 'video',
  mov: 'video',
  m4v: 'video',
  mkv: 'video',
  avi: 'video',
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  webp: 'image',
  gif: 'image',
  svg: 'image',
  bmp: 'image',
  mp3: 'audio',
  wav: 'audio',
  m4a: 'audio',
  aac: 'audio',
  ogg: 'audio',
  flac: 'audio',
}

const VALID_KINDS = ['video', 'image', 'audio']

/** 'song.final.WAV' -> 'wav' ('' when there is no extension). */
export function fileExt(name) {
  const m = /\.([a-z0-9]+)$/i.exec(String(name || ''))
  return m ? m[1].toLowerCase() : ''
}

/** 'song.wav' -> '.WAV' ('' when there is no extension). */
export function extBadge(name) {
  const e = fileExt(name)
  return e ? '.' + e.toUpperCase() : ''
}

/** Resolve the render kind: extension first, stored kind as fallback. */
export function mediaKind(kind, filename) {
  const fromExt = EXT_KIND[fileExt(filename)]
  if (fromExt) return fromExt
  if (VALID_KINDS.includes(kind)) return kind
  return 'other'
}
