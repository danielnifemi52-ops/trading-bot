import { useState, useEffect } from "react"
import { getAccount, getPositions, getOrders, closePosition } from "../api/client"

export default function AccountPanel() {
  const [account,   setAccount]   = useState(null)
  const [positions, setPositions] = useState([])
  const [orders,    setOrders]    = useState([])
  const [loading,   setLoading]   = useState(true)
  const [closing,   setClosing]   = useState(null)

  const refresh = async () => {
    try {
      const [a, p, o] = await Promise.all([
        getAccount(),
        getPositions(),
        getOrders(10),
      ])
      setAccount(a.data)
      setPositions(p.data.positions)
      setOrders(o.data.orders)
    } catch (e) {
      console.error("Account sync error:", e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 30000)
    return () => clearInterval(id)
  }, [])

  const handleClose = async (symbol) => {
    setClosing(symbol)
    try {
      await closePosition(symbol)
      await refresh()
    } catch (e) {
      alert("Failed to close: " + e.message)
    } finally {
      setClosing(null)
    }
  }

  if (loading) return (
    <div style={{ padding: 20, color: "#64748b", fontSize: 13 }}>
      Loading account data...
    </div>
  )

  return (
    <div>
      {/* Account summary */}
      {account?.connected && (
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
          marginBottom: 20,
        }}>
          {[
            { label: "Portfolio Value", value: `$${Number(account.portfolio_value).toLocaleString("en-US", {minimumFractionDigits: 2})}` },
            { label: "Cash Available",  value: `$${Number(account.cash).toLocaleString("en-US", {minimumFractionDigits: 2})}` },
            { label: "Buying Power",    value: `$${Number(account.buying_power).toLocaleString("en-US", {minimumFractionDigits: 2})}` },
            { 
              label: "Today P&L",
              value: `$${Number(account.pnl).toFixed(2)}`,
              color: account.pnl >= 0 ? "#10b981" : "#ef4444"
            },
          ].map(card => (
            <div key={card.label} style={{
              background: "var(--surface, #1a1d27)",
              border: "1px solid var(--border, #2a2d3a)",
              borderRadius: 8,
              padding: "14px 16px",
            }}>
              <p style={{ fontSize: 11, color: "#64748b", margin: "0 0 6px", letterSpacing: "0.06em" }}>
                {card.label.toUpperCase()}
              </p>
              <p style={{ fontSize: 18, fontWeight: 600, margin: 0, color: card.color || "#e2e8f0" }}>
                {card.value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Open positions */}
      <div style={{
        background: "var(--surface, #1a1d27)",
        border: "1px solid var(--border, #2a2d3a)",
        borderRadius: 8,
        padding: 16,
        marginBottom: 16,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
          <p style={{ fontSize: 11, color: "#64748b", margin: 0, letterSpacing: "0.08em" }}>
            OPEN POSITIONS
          </p>
          <button onClick={refresh} style={{
            fontSize: 11, color: "#3b82f6", background: "none",
            border: "none", cursor: "pointer", fontFamily: "inherit"
          }}>
            Refresh
          </button>
        </div>

        {positions.length === 0 ? (
          <p style={{ fontSize: 13, color: "#475569", margin: 0 }}>
            No open positions
          </p>
        ) : (
          <div>
            {/* Header */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 80px 100px 100px 100px 80px",
              gap: 8, padding: "6px 0",
              borderBottom: "1px solid #2a2d3a",
              fontSize: 10, color: "#475569",
              letterSpacing: "0.06em"
            }}>
              {["SYMBOL","QTY","ENTRY","CURRENT","P&L",""].map(h => (
                <span key={h}>{h}</span>
              ))}
            </div>

            {positions.map(pos => (
              <div key={pos.symbol} style={{
                display: "grid",
                gridTemplateColumns: "1fr 80px 100px 100px 100px 80px",
                gap: 8,
                padding: "10px 0",
                borderBottom: "1px solid #141414",
                alignItems: "center",
                fontSize: 13,
              }}>
                <span style={{ color: "#e2e8f0", fontWeight: 500 }}>
                  {pos.symbol}
                </span>
                <span style={{ color: "#94a3b8" }}>
                  {pos.qty}
                </span>
                <span style={{ color: "#94a3b8" }}>
                  ${Number(pos.entry_price).toFixed(2)}
                </span>
                <span style={{ color: "#e2e8f0" }}>
                  ${Number(pos.current_price).toFixed(2)}
                </span>
                <span style={{ color: pos.unrealized_pnl >= 0 ? "#10b981" : "#ef4444", fontWeight: 500 }}>
                  ${Number(pos.unrealized_pnl).toFixed(2)}
                  <span style={{ fontSize: 10, marginLeft: 4 }}>
                    ({Number(pos.unrealized_pct).toFixed(2)}%)
                  </span>
                </span>
                <button
                  onClick={() => handleClose(pos.symbol)}
                  disabled={closing === pos.symbol}
                  style={{
                    padding: "4px 10px",
                    background: "transparent",
                    border: "1px solid #ef4444",
                    borderRadius: 4,
                    color: "#ef4444",
                    fontSize: 11,
                    cursor: "pointer",
                    fontFamily: "inherit",
                    opacity: closing === pos.symbol ? 0.5 : 1,
                  }}
                >
                  {closing === pos.symbol ? "..." : "Close"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent orders */}
      <div style={{
        background: "var(--surface, #1a1d27)",
        border: "1px solid var(--border, #2a2d3a)",
        borderRadius: 8,
        padding: 16,
      }}>
        <p style={{ fontSize: 11, color: "#64748b", margin: "0 0 12px", letterSpacing: "0.08em" }}>
          RECENT ORDERS
        </p>

        {orders.length === 0 ? (
          <p style={{ fontSize: 13, color: "#475569", margin: 0 }}>
            No recent orders
          </p>
        ) : (
          <div>
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 60px 80px 80px 100px 80px",
              gap: 8, padding: "6px 0",
              borderBottom: "1px solid #2a2d3a",
              fontSize: 10, color: "#475569",
              letterSpacing: "0.06em"
            }}>
              {["SYMBOL","SIDE","QTY","PRICE","TIME","STATUS"].map(h => (
                <span key={h}>{h}</span>
              ))}
            </div>

            {orders.map(order => (
              <div key={order.id} style={{
                display: "grid",
                gridTemplateColumns: "1fr 60px 80px 80px 100px 80px",
                gap: 8,
                padding: "10px 0",
                borderBottom: "1px solid #141414",
                alignItems: "center",
                fontSize: 12,
              }}>
                <span style={{ color: "#e2e8f0", fontWeight: 500 }}>
                  {order.symbol}
                </span>
                <span style={{ 
                  color: order.side === "buy" ? "#10b981" : "#ef4444",
                  fontWeight: 500,
                  textTransform: "uppercase",
                }}>
                  {order.side}
                </span>
                <span style={{ color: "#94a3b8" }}>
                  {order.filled_qty || order.qty}
                </span>
                <span style={{ color: "#94a3b8" }}>
                  {order.filled_price 
                    ? `$${Number(order.filled_price).toFixed(2)}` 
                    : "—"
                  }
                </span>
                <span style={{ color: "#475569", fontSize: 10 }}>
                  {order.filled_at 
                    ? new Date(order.filled_at).toLocaleTimeString()
                    : new Date(order.created_at).toLocaleTimeString()
                  }
                </span>
                <span style={{
                  fontSize: 10,
                  padding: "2px 6px",
                  borderRadius: 4,
                  background: order.status === "filled" ? "#0a2d1a" :
                              order.status === "canceled" ? "#1c0a0a" : "#1a1d27",
                  color: order.status === "filled" ? "#10b981" :
                         order.status === "canceled" ? "#ef4444" : "#64748b",
                  border: `1px solid ${
                    order.status === "filled" ? "#10b981" :
                    order.status === "canceled" ? "#ef4444" : "#2a2d3a"
                  }`,
                }}>
                  {order.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
