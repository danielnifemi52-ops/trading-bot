/**
 * RSIGauge.jsx
 * SVG arc gauge for RSI values.
 */
const RSIGauge = ({ value, rsi_period }) => {
  // Handle null/undefined values gracefully
  if (value === null || value === undefined || isNaN(Number(value))) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: 200,
          color: "#475569",
          fontSize: 13,
        }}
      >
        <div
          style={{
            width: 40,
            height: 40,
            border: "3px solid #1e293b",
            borderTop: "3px solid #3b82f6",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
            marginBottom: 12,
          }}
        />
        Calculating RSI...
        <span style={{ fontSize: 11, marginTop: 4, color: "#334155" }}>
          Warming up ({rsi_period || 14} bars needed)
        </span>
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Calculate color based on RSI value
  const getColor = (rsi) => {
    if (rsi < 30) return "#10b981"; // Green for oversold
    if (rsi > 70) return "#ef4444"; // Red for overbought
    return "#94a3b8"; // Gray for neutral
  };

  const rsiColor = getColor(value);

  return (
    <div className="rsi-gauge">
      <div className="gauge-container">
        <svg width="200" height="120" viewBox="0 0 200 120">
          {/* Background arc (grey) */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#334155"
            strokeWidth="8"
            strokeLinecap="round"
          />
          {/* RSI value arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={rsiColor}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${(value / 100) * 251.2}, 251.2`}
            transform="rotate(180 100 100)"
          />
          {/* RSI value text */}
          <text x="100" y="60" textAnchor="middle" className="value">
            {value.toFixed(1)}
          </text>
          <text x="100" y="80" textAnchor="middle" className="label">
            {value < 30 ? "OVERSOLD" : value > 70 ? "OVERBOUGHT" : "NEUTRAL"}
          </text>
        </svg>
      </div>
      <style>{`
        .rsi-gauge {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 20px;
        }
        .gauge-container {
          position: relative;
          width: 200px;
          height: 120px;
        }
        .value {
          font-size: 24px;
          font-weight: bold;
          fill: #e2e8f0;
        }
        .label {
          font-size: 14px;
          fill: #94a3b8;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
};

export default RSIGauge;
