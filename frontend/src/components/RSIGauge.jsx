/**
 * RSIGauge.jsx
 * SVG arc gauge for RSI values.
 */
import React from 'react';

const RSIGauge = ({ value }) => {
  // Handle null/undefined values gracefully
  if (value === null || value === undefined) {
    return (
      <div className="rsi-gauge">
        <div className="gauge-container">
          <svg width="200" height="120" viewBox="0 0 200 120">
            <text x="100" y="60" textAnchor="middle" className="value">
              —
            </text>
            <text x="100" y="80" textAnchor="middle" className="label">
              NO DATA
            </text>
          </svg>
        </div>
        <style jsx>{`
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
  }

  // Calculate color based on RSI value
  const getColor = (rsi) => {
    if (rsi < 30) return '#10b981'; // Green for oversold
    if (rsi > 70) return '#ef4444'; // Red for overbought
    return '#94a3b8'; // Gray for neutral
  };

  // Calculate position on the gauge
  const calculatePosition = (rsi) => {
    // Map RSI (0-100) to angle (0-180 degrees)
    return (rsi / 100) * 180;
  };

  const rsiColor = getColor(value);
  const rsiPosition = calculatePosition(value);

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
            {value < 30 ? 'OVERSOLD' : value > 70 ? 'OVERBOUGHT' : 'NEUTRAL'}
          </text>
        </svg>
      </div>
      <style jsx>{`
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