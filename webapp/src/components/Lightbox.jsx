import { useEffect } from 'react'

/**
 * Full-size media viewer (video or image) in an overlay.
 * item: { src, kind, title } — kind: 'video' | 'image'
 */
export default function Lightbox({ item, onClose }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!item) return null

  return (
    <div
      className="overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="modal lightbox">
        <div className="modal-head">
          <h3 className="lightbox-title" title={item.title}>
            {item.title || 'Sample'}
          </h3>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        {item.kind === 'image' ? (
          <img className="lightbox-media" src={item.src} alt={item.title || 'sample'} />
        ) : (
          <video className="lightbox-media" src={item.src} controls autoPlay playsInline />
        )}
      </div>
    </div>
  )
}
