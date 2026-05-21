export default function StatCard({ label, value, sub, highlight }) {
  return (
    <div style={{
      border: 1px solid ,
      borderRadius: '8px',
      padding: '16px',
      textAlign: 'center',
      backgroundColor: highlight ? '#1e40af' : '#1a1d27',
    }}>
      <div style={{ fontSize: '14px', color: '#64748b', marginBottom: '4px' }}>
        {label}
      </div>
      <div style={{ fontSize: '24px', fontWeight: '600', color: '#e2e8f0' }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
          {sub}
        </div>
      )}
    </div>
  )
}
