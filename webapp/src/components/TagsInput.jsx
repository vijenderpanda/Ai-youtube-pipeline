import { useState } from 'react'

/** Chip-style tags input. value: string[]; Enter/comma adds, × or Backspace removes. */
export default function TagsInput({ value = [], onChange, disabled, placeholder = 'Add tag…' }) {
  const [text, setText] = useState('')

  const add = () => {
    const t = text.trim().replace(/,+$/, '')
    if (!t) return
    if (!value.includes(t)) onChange([...value, t])
    setText('')
  }

  const onKey = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      add()
    } else if (e.key === 'Backspace' && !text && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  return (
    <div className={'tags-input' + (disabled ? ' disabled' : '')}>
      {value.map((t) => (
        <span className="tag tag-removable" key={t}>
          {t}
          {!disabled && (
            <button
              type="button"
              className="tag-x"
              onClick={() => onChange(value.filter((x) => x !== t))}
              aria-label={`Remove tag ${t}`}
            >
              ×
            </button>
          )}
        </span>
      ))}
      {!disabled && (
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          onBlur={add}
          placeholder={value.length === 0 ? placeholder : ''}
        />
      )}
      {disabled && value.length === 0 && <span className="dim small">no tags</span>}
    </div>
  )
}
