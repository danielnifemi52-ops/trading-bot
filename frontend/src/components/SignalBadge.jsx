/**
 * SignalBadge.jsx
 * Coloured pill for BUY / SELL / HOLD signals.
 */
const COLORS = {
  BUY:  { bg: '#d1fae5', text: '#065f46', border: '#6ee7b7' },
  SELL: { bg: '#fee2e2', text: '#7f1d1d', border: '#fca5a5' },
  HOLD: { bg: '#f1f5f9', text: '#475569', border: '#cbd5e1' },
}

export default function SignalBadge({ signal }) {
  const c = COLORS[signal] || COLORS.HOLD
  return (
    <span style={{
      display: 'inline-block',
      padding: '3px 12px',
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 600,
      letterSpacing: '0.06em',
      background: c.bg,
      color: c.text,
      border: 1px solid ,
    }}>
      {signal || 'HOLD'}
    </span>
  )
}

