/**
 * Reusable filter chips (v4).
 *
 * <Chips options value onChange multi ariaLabel />
 *   options: [{ value, label, count?, icon?, className? }]
 *   Single-select: `value` is a string ('' usually means "All" when you include
 *   an { value: '' } option). Multi-select: `value` is an array of strings.
 *
 * <ChipSearch value onChange placeholder /> — matching pill-styled text search.
 * <ChipsGroup label> — optional labelled wrapper for a chips row.
 */
export default function Chips({ options, value, onChange, multi = false, ariaLabel }) {
  const isActive = (v) => (multi ? value.includes(v) : value === v)
  const click = (v) => {
    if (multi) onChange(isActive(v) ? value.filter((x) => x !== v) : [...value, v])
    else onChange(v)
  }
  return (
    <div className="chips-row" role="group" aria-label={ariaLabel}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={isActive(o.value)}
          className={
            'fchip' + (isActive(o.value) ? ' active' : '') + (o.className ? ` ${o.className}` : '')
          }
          onClick={() => click(o.value)}
        >
          {o.icon}
          <span>{o.label}</span>
          {o.count != null && <span className="fchip-count">{o.count}</span>}
        </button>
      ))}
    </div>
  )
}

export function ChipSearch({ value, onChange, placeholder = 'Search…' }) {
  return (
    <input
      type="search"
      className="chip-search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
    />
  )
}

export function ChipsGroup({ label, children }) {
  return (
    <div className="chips-group">
      {label && <span className="chips-group-label">{label}</span>}
      {children}
    </div>
  )
}
