export default function EmptyState({ message, hint }) {
  return (
    <div className="empty">
      <span className="empty-dot" />
      <p>{message}</p>
      {hint && <p className="empty-hint">{hint}</p>}
    </div>
  )
}
