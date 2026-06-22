import { useState, useRef } from 'react';
import { 
  CRYPTO_SYMBOLS, 
  STOCK_SYMBOLS, 
  ETF_SYMBOLS,
  isSupported,
  isCrypto,
} from "../utils/supportedAssets"

const TICKER_GROUPS = [
  {
    group: "Crypto — Alpaca 24/7",
    symbols: CRYPTO_SYMBOLS,
    icon: "₿",
    color: "#f59e0b",
    desc: "Available 24/7 · No PDT rule"
  },
  {
    group: "Stocks — NYSE hours",
    symbols: STOCK_SYMBOLS,
    icon: "📈",
    color: "#3b82f6",
    desc: "Mon–Fri 2:30pm–9pm Lagos"
  },
  {
    group: "ETFs — NYSE hours",
    symbols: ETF_SYMBOLS,
    icon: "📊",
    color: "#10b981",
    desc: "Mon–Fri 2:30pm–9pm Lagos"
  },
]

// Full component:
export default function TickerSelect({ value, onChange }) {
  const [search, setSearch]   = useState("")
  const [open, setOpen]       = useState(false)
  const inputRef = useRef(null)

  const filtered = TICKER_GROUPS.map(group => ({
    ...group,
    symbols: group.symbols.filter(s =>
      s.toLowerCase().includes(search.toLowerCase())
    )
  })).filter(g => g.symbols.length > 0)

  const handleSelect = (symbol) => {
    onChange(symbol)
    setSearch("")
    setOpen(false)
  }

  return (
    <div style={{ position: "relative" }}>
      <input
        ref={inputRef}
        value={open ? search : value}
        onChange={e => {
          setSearch(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 200)}
        placeholder="Search symbol..."
        style={{
          width: "100%",
          padding: "10px 12px",
          background: "#0f1117",
          border: "1px solid #2a2d3a",
          borderRadius: 6,
          color: "#e2e8f0",
          fontSize: 14,
          fontFamily: "inherit",
          outline: "none",
        }}
      />

      {/* Not supported warning */}
      {value && !isSupported(value) && (
        <p style={{
          fontSize: 11, color: "#ef4444",
          margin: "4px 0 0"
        }}>
          ✕ {value} is not supported by Alpaca.
          Select from the list below.
        </p>
      )}

      {open && (
        <div style={{
          position: "absolute",
          top: "calc(100% + 4px)",
          left: 0, right: 0,
          background: "#1a1d27",
          border: "1px solid #2a2d3a",
          borderRadius: 8,
          maxHeight: 320,
          overflowY: "auto",
          zIndex: 999,
          boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
        }}>
          {filtered.map(group => (
            <div key={group.group}>
              {/* Group header */}
              <div style={{
                padding: "8px 12px 4px",
                fontSize: 10,
                color: group.color,
                letterSpacing: "0.1em",
                fontWeight: 500,
                borderBottom: "1px solid #2a2d3a",
                background: "#0f1117",
                position: "sticky",
                top: 0,
              }}>
                {group.icon} {group.group.toUpperCase()}
                <span style={{
                  color: "#475569",
                  fontWeight: 400,
                  marginLeft: 8,
                  letterSpacing: 0,
                }}>
                  {group.desc}
                </span>
              </div>

              {/* Symbol buttons */}
              <div style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 4,
                padding: 8,
              }}>
                {group.symbols.map(symbol => (
                  <button
                    key={symbol}
                    onMouseDown={() => handleSelect(symbol)}
                    style={{
                      padding: "4px 10px",
                      fontSize: 12,
                      borderRadius: 4,
                      border: `1px solid ${value === symbol 
                        ? group.color : "#2a2d3a"}`,
                      background: value === symbol 
                        ? group.color + "22" : "#0f1117",
                      color: value === symbol 
                        ? group.color : "#94a3b8",
                      cursor: "pointer",
                      fontFamily: "inherit",
                      transition: "all 0.1s",
                    }}
                  >
                    {symbol}
                  </button>
                ))}
              </div>
            </div>
          ))}

          {filtered.length === 0 && (
            <div style={{
              padding: 16,
              fontSize: 13,
              color: "#475569",
              textAlign: "center",
            }}>
              No results for "{search}"
            </div>
          )}
        </div>
      )}
    </div>
  )
}
