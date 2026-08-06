import Modal from './Modal'

/** Small confirmation modal on top of the existing Modal primitive. */
export default function ConfirmDialog({
  title,
  children,
  confirmLabel = 'Confirm',
  busy = false,
  danger = false,
  onConfirm,
  onCancel,
}) {
  return (
    <Modal title={title} onClose={onCancel} width={440}>
      <div className="confirm-body">{children}</div>
      <div className="form-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button
          type="button"
          className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}
          onClick={onConfirm}
          disabled={busy}
        >
          {busy ? 'Working…' : confirmLabel}
        </button>
      </div>
    </Modal>
  )
}
