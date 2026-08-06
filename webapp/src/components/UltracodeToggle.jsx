export default function UltracodeToggle({ checked, onChange }) {
  return (
    <div className="ultra-field">
      <label className="switch-row">
        <input
          type="checkbox"
          checked={!!checked}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className="switch-track">
          <span className="switch-thumb" />
        </span>
        <span className="switch-label">⚡ Ultracode</span>
      </label>
      <p className="switch-help">
        multi-agent orchestration — many agents, much deeper, uses far more of your plan
      </p>
    </div>
  )
}
