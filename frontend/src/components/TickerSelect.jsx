import React, { useState } from 'react';

const TICKERS = [
  { group: "Tech",        symbols: ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","NFLX","AMD","INTC"] },
  { group: "Finance",     symbols: ["JPM","BAC","GS","MS","V","MA","PYPL","BRK-B","C","WFC"] },
  { group: "ETFs",        symbols: ["SPY","QQQ","IWM","DIA","VTI","ARKK","GLD","SLV","USO","TLT"] },
  { group: "Healthcare",  symbols: ["JNJ","PFE","MRNA","UNH","ABBV","LLY","CVS","MRK","TMO","ABT"] },
  { group: "Energy",      symbols: ["XOM","CVX","COP","SLB","OXY","BP","PSX","VLO","MPC","HAL"] },
];

export default function TickerSelect({ value, onChange }) {
  const [showTickerDropdown, setShowTickerDropdown] = useState(false);

  return (
    <div style={{ position: "relative" }}>
      <input
        value={value}
        onChange={e => onChange(e.target.value.toUpperCase())}
        onFocus={() => setShowTickerDropdown(true)}
        onBlur={() => setTimeout(() => setShowTickerDropdown(false), 200)}
        placeholder="Search ticker..."
        style={{
          width: "100%",
          padding: "10px 12px",
          background: "#0f1117",
          border: "1px solid #2a2d3a",
          borderRadius: 6,
          color: "#e2e8f0",
          fontSize: "14px",
          marginTop: "6px",
          outline: "none"
        }}
      />
      {showTickerDropdown && (
        <div style={{
          position: "absolute", top: "100%", left: 0, right: 0, zIndex: 100,
          background: "#1a1d27", border: "1px solid #2a2d3a", borderRadius: 6,
          maxHeight: 260, overflowY: "auto", boxShadow: "0 8px 24px rgba(0,0,0,0.4)"
        }}>
          {TICKERS.map(group => {
            const filteredSymbols = group.symbols.filter(
              s => s.includes(value.toUpperCase()) || value === ""
            );
            if (filteredSymbols.length === 0) return null;
            return (
              <div key={group.group}>
                <div style={{ padding: "6px 12px", fontSize: 10, color: "#475569",
                              letterSpacing: "0.1em", borderBottom: "1px solid #2a2d3a" }}>
                  {group.group.toUpperCase()}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4, padding: 8 }}>
                  {filteredSymbols.map(symbol => (
                    <button
                      key={symbol}
                      type="button"
                      onMouseDown={() => onChange(symbol)}
                      style={{
                        padding: "4px 10px", fontSize: 11, borderRadius: 4,
                        background: value === symbol ? "#3b82f6" : "#0f1117",
                        color: value === symbol ? "#fff" : "#94a3b8",
                        border: "1px solid #2a2d3a", cursor: "pointer"
                      }}
                    >
                      {symbol}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
