/**
 * Dashboard.jsx
 * The main bot control room. Shows live tickers, RSI gauge,
 * start/stop parameters, and recent tick history.
 */
import { useState, useEffect, useCallback } from 'react'
import { useBot } from '../hooks/useBot'
import { getBotLogs, manualTrade, getAccount } from '../api/client'
import StatCard from '../components/StatCard'
import RSIGauge from '../components/RSIGauge'
import BotControls from '../components/BotControls'
import SignalBadge from '../components/SignalBadge'
import { getMarketStatus } from '../utils/marketHours'

export default function Dashboard() {
  const { status, liveData, loading, error, start, stop } = useBot()
  const [logs, setLogs] = useState([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [health, setHealth] = useState(null)  // FIX 6 — memory widget

  const [tradeLoading, setTradeLoading] = useState(null)
  const [tradeResult, setTradeResult]   = useState(null)
  const [tradeError, setTradeError]     = useState(null)
  const [showConfirm, setShowConfirm]   = useState(null)
  const [alpacaAccount, setAlpacaAccount] = useState(null)

  useEffect(() => {
    getAccount().then(r => setAlpacaAccount(r.data)).catch(() => {})
    const id = setInterval(() => {
      getAccount().then(r => setAlpacaAccount(r.data)).catch(() => {})
    }, 30000)
    return () => clearInterval(id)
  }, [])

  // ── FIX 6: Poll /health every 60 s for memory data ────────────────────
  useEffect(() => {
    const API = import.meta.env.VITE_API_URL || ''
    const fetchHealth = async () => {
      try {
        const res = await fetch(`${API}/health`)
        if (res.ok) setHealth(await res.json())
      } catch (_) {}
    }
    fetchHealth()
    const id = setInterval(fetchHealth, 60_000)
    return () => clearInterval(id)
  }, [])

  const handleTrade = async (side) => {
    const symbol = status?.symbol || status?.config?.symbol
    if (!symbol) {
      setTradeError("No symbol selected. Start the bot first.")
      return
    }
    setShowConfirm({ side, symbol, price: liveData?.price || status?.last_price })
  }

  const confirmTrade = async () => {
    const { side, symbol } = showConfirm
    setShowConfirm(null)
    setTradeLoading(side)
    setTradeError(null)
    setTradeResult(null)
    try {
      const { data } = await manualTrade(symbol, side)
      setTradeResult(data)
      setTimeout(() => setTradeResult(null), 5000)
    } catch (e) {
      setTradeError(
        e.response?.data?.detail || e.message
      )
      setTimeout(() => setTradeError(null), 8000)
    } finally {
      setTradeLoading(null)
    }
  }

  // Fetch logs on mount and whenever the bot status changes (e.g. started/stopped)
  const fetchLogs = useCallback(async () => {
    try {
      setLogsLoading(true)
      const { data } = await getBotLogs(10)
      setLogs(data)
    } catch (e) {
      console.error('Failed to fetch bot logs:', e)
    } finally {
      setLogsLoading(false)
    }
  }, [])

  useEffect(() => {
    queueMicrotask(fetchLogs)
  }, [fetchLogs, status?.running])

  // Refresh logs when new live tick data is received via WS
  useEffect(() => {
    if (liveData) {
      queueMicrotask(() => {
        setLogs((prevLogs) => {
          const newLog = {
            id: Date.now(), // temporary local id
            symbol: status?.symbol || 'Bot',
            price: liveData.price,
            rsi: liveData.rsi,
            signal: liveData.signal,
            account_value: liveData.account,
            timestamp: new Date().toISOString(),
          }
          return [newLog, ...prevLogs.slice(0, 9)]
        })
      })
    }
  }, [liveData, status?.symbol])

  // Get current active values (prefer WebSocket live data, fall back to last status value)
  const price = liveData?.price ?? status?.last_price ?? null
  const rsi = liveData?.rsi ?? status?.last_rsi ?? null
  const signal = liveData?.signal ?? status?.last_signal ?? 'HOLD'
  const account = liveData?.account ?? status?.account_value ?? null

  const marketStatus = getMarketStatus(
    status?.symbol || liveData?.symbol
  )

  const formatPrice = (val) => {
    if (val === undefined || val === null) return '--'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(val)
  }

  const formatRsi = (val) => {
    if (val === undefined || val === null) return '--'
    return val.toFixed(2)
  }

  if (loading && !status && !liveData) {
    return <div style={{padding:40, color:'#64748b'}}>Loading dashboard state...</div>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid var(--red)',
          color: 'var(--red)',
          padding: '16px 20px',
          borderRadius: 'var(--radius)',
          fontSize: '14px',
          fontWeight: '500',
        }}>
          Error: {error}
        </div>
      )}

      {status?.symbol?.includes('/') && (
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: '#1c1208',
          border: '1px solid #f59e0b',
          borderRadius: 999,
          padding: '3px 10px',
          fontSize: 11,
          color: '#f59e0b',
          marginBottom: 12,
          alignSelf: 'flex-start',
        }}>
          {'₿ CRYPTO MODE - 24/7 trading active · No PDT restrictions'}
        </div>
      )}

      {/* Market Status Banner */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: marketStatus.isOpen 
          ? "rgba(16,185,129,0.08)" 
          : "rgba(239,68,68,0.08)",
        border: `1px solid ${marketStatus.color}33`,
        borderRadius: 8,
        padding: "10px 16px",
        marginBottom: 16,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Animated dot */}
          <div style={{ position: "relative", width: 10, height: 10 }}>
            <div style={{
              width: 10, height: 10,
              borderRadius: "50%",
              background: marketStatus.dotColor,
              position: "absolute",
            }} />
            {marketStatus.isOpen && (
              <div style={{
                width: 10, height: 10,
                borderRadius: "50%",
                background: marketStatus.dotColor,
                position: "absolute",
                opacity: 0.4,
                animation: "ping 1.5s ease-in-out infinite",
              }} />
            )}
          </div>
          <div style={{ textAlign: 'left' }}>
            <p style={{
              fontSize: 13,
              fontWeight: 600,
              color: marketStatus.color,
              margin: 0,
            }}>
              {marketStatus.label}
            </p>
            <p style={{
              fontSize: 11,
              color: "#64748b",
              margin: 0,
              marginTop: 2,
            }}>
              {marketStatus.sublabel}
            </p>
          </div>
        </div>

        {/* NYSE schedule for stocks */}
        {!marketStatus.isOpen && !status?.symbol?.includes("/") && (
          <div style={{
            fontSize: 11,
            color: "#475569",
            textAlign: "right",
          }}>
            <p style={{ margin: 0 }}>Mon–Fri</p>
            <p style={{ margin: 0, fontWeight: 500, color: "#94a3b8" }}>
              2:30 PM – 9:00 PM Lagos
            </p>
          </div>
        )}

        {/* Crypto is always open */}
        {status?.symbol?.includes("/") && (
          <div style={{
            fontSize: 11,
            color: "#10b981",
            textAlign: "right",
          }}>
            <p style={{ margin: 0 }}>365 days/year</p>
            <p style={{ margin: 0, fontWeight: 500 }}>No restrictions</p>
          </div>
        )}
      </div>

      {/* Top row: 4 Metric Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '24px',
      }}>
        <StatCard
          label="Current Price"
          value={price !== null ? formatPrice(price) : '--'}
          sub={
            status?.symbol
              ? marketStatus.isOpen
                ? `Symbol: ${status.symbol}`
                : `${status.symbol} · Last close price`
              : 'Bot Idle'
          }
          highlight={price !== null ? 'var(--blue)' : undefined}
        />
        <StatCard
          label="RSI Value (14h)"
          value={rsi !== null ? formatRsi(rsi) : '--'}
          sub={
            marketStatus.isOpen
              ? `RSI ${status?.config?.rsi_period ?? 14} · Live`
              : `RSI ${status?.config?.rsi_period ?? 14} · Market closed`
          }
          highlight={rsi !== null ? (rsi <= status?.config?.oversold ? 'var(--green)' : rsi >= status?.config?.overbought ? 'var(--red)' : 'var(--text)') : undefined}
        />
        <StatCard
          label="Current Signal"
          value={<SignalBadge signal={signal} />}
          sub={status?.running ? 'Live Signal Polling' : 'Bot Offline'}
        />
        <StatCard
          label="Account Value"
          value={alpacaAccount?.portfolio_value
            ? `$${Number(alpacaAccount.portfolio_value).toLocaleString("en-US", {minimumFractionDigits: 2})}`
            : `$${(liveData?.account || 10000).toLocaleString()}`
          }
          sub={alpacaAccount?.connected
            ? `Cash: $${Number(alpacaAccount.cash).toFixed(2)}`
            : "Simulated"
          }
          highlight="var(--green)"
        />
      </div>

      {/* Middle row: RSIGauge & BotControls */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '32px',
      }}>
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '32px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '400px',
        }}>
          <h3 style={{
            alignSelf: 'flex-start',
            fontSize: '16px',
            fontWeight: '600',
            color: 'var(--text)',
            marginBottom: '24px',
          }}>
            RSI Technical Gauge
          </h3>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <RSIGauge value={rsi} />
          </div>
        </div>

        <div>
          <BotControls
            status={status}
            onStart={start}
            onStop={stop}
            loading={loading}
          />
          {/* MANUAL TRADING PANEL */}
          <div style={{
            background: "var(--surface, #1a1d27)",
            border: "1px solid var(--border, #2a2d3a)",
            borderRadius: 8,
            padding: 20,
            marginTop: 16,
            textAlign: "left",
          }}>
            <p style={{
              fontSize: 11, color: "#64748b",
              letterSpacing: "0.08em",
              marginBottom: 16, margin: "0 0 16px"
            }}>
              MANUAL TRADING
            </p>

            {/* Current price display */}
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 16,
              padding: "10px 14px",
              background: "#0f1117",
              borderRadius: 6,
              border: "1px solid #2a2d3a",
            }}>
              <span style={{ fontSize: 12, color: "#64748b" }}>
                {status?.symbol || "—"}
              </span>
              <span style={{ fontSize: 16, fontWeight: 600, color: "#e2e8f0" }}>
                ${(liveData?.price || status?.last_price || 0).toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </span>
              <span style={{
                fontSize: 11,
                color: (liveData?.rsi || status?.last_rsi) < 30 ? "#10b981" :
                       (liveData?.rsi || status?.last_rsi) > 70 ? "#ef4444" : "#64748b",
              }}>
                RSI {(liveData?.rsi || status?.last_rsi || 0).toFixed(1)}
              </span>
            </div>

            {/* Buy and Sell buttons */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <button
                onClick={() => handleTrade("BUY")}
                disabled={tradeLoading !== null || !status?.running}
                style={{
                  padding: "14px",
                  background: tradeLoading === "BUY" ? "#0a2d1a" : "#0f2d1a",
                  border: "1px solid #10b981",
                  borderRadius: 6,
                  color: "#10b981",
                  fontSize: 15,
                  fontWeight: 500,
                  cursor: (tradeLoading || !status?.running) ? "not-allowed" : "pointer",
                  opacity: (!status?.running || tradeLoading) ? 0.5 : 1,
                  fontFamily: "inherit",
                  transition: "all 0.15s",
                }}
              >
                {tradeLoading === "BUY" ? "Placing..." : "▲ Buy Now"}
              </button>

              <button
                onClick={() => handleTrade("SELL")}
                disabled={tradeLoading !== null || !status?.running}
                style={{
                  padding: "14px",
                  background: tradeLoading === "SELL" ? "#2d0a0a" : "#2d0f0f",
                  border: "1px solid #ef4444",
                  borderRadius: 6,
                  color: "#ef4444",
                  fontSize: 15,
                  fontWeight: 500,
                  cursor: (tradeLoading || !status?.running) ? "not-allowed" : "pointer",
                  opacity: (!status?.running || tradeLoading) ? 0.5 : 1,
                  fontFamily: "inherit",
                  transition: "all 0.15s",
                }}
              >
                {tradeLoading === "SELL" ? "Placing..." : "▼ Sell Now"}
              </button>
            </div>

            {/* Not running warning */}
            {!status?.running && (
              <p style={{
                fontSize: 11, color: "#475569",
                textAlign: "center", marginTop: 10, margin: "10px 0 0"
              }}>
                Start the bot to enable manual trading
              </p>
            )}

            {/* Success message */}
            {tradeResult && (
              <div style={{
                marginTop: 12,
                padding: "10px 14px",
                background: "#0a2d1a",
                border: "1px solid #10b981",
                borderRadius: 6,
                fontSize: 12,
                color: "#10b981",
              }}>
                ✅ {tradeResult.action} order placed — {tradeResult.qty} {tradeResult.symbol} at ${tradeResult.price?.toFixed(2)}
                {tradeResult.dry_run && " [DRY RUN]"}
              </div>
            )}

            {/* Error message */}
            {tradeError && (
              <div style={{
                marginTop: 12,
                padding: "10px 14px",
                background: "#2d0a0a",
                border: "1px solid #ef4444",
                borderRadius: 6,
                fontSize: 12,
                color: "#fca5a5",
              }}>
                ✕ {tradeError}
              </div>
            )}

            {/* Dry run notice */}
            {status?.config?.dry_run && (
              <p style={{
                fontSize: 10, color: "#475569",
                textAlign: "center", marginTop: 10, margin: "10px 0 0"
              }}>
                ⚠ Dry Run Mode — no real orders placed
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bottom row: Tick Logs Table */}
      <div style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '24px',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '20px',
        }}>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text)' }}>
              Recent Bot Activity Logs
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--muted)' }}>
              Last 10 updates processed by the running daemon
            </p>
          </div>
          <button
            onClick={fetchLogs}
            disabled={logsLoading}
            style={{
              padding: '6px 14px',
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              color: 'var(--text)',
              fontSize: '12px',
              fontWeight: '500',
              cursor: 'pointer',
            }}
          >
            {logsLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            textAlign: 'left',
          }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Timestamp</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Symbol</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Price</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>RSI</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Signal</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Account Value</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)' }}>
                    No activity logs recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((logItem, idx) => (
                  <tr
                    key={logItem.id || idx}
                    style={{
                      borderBottom: '1px solid var(--border)',
                      background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
                    }}
                  >
                    <td style={{ padding: '14px 16px', color: 'var(--muted)', fontSize: '13px' }}>
                      {new Date(logItem.timestamp).toLocaleString()}
                    </td>
                    <td style={{ padding: '14px 16px', fontWeight: '600' }}>
                      {logItem.symbol}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      {formatPrice(logItem.price)}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      {formatRsi(logItem.rsi)}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <SignalBadge signal={logItem.signal} />
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      {formatPrice(logItem.account_value)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      {/* ── FIX 6: Fixed RAM usage widget ──────────────────────────────── */}
      {health && (
        <div style={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          background: '#0f1117',
          border: `1px solid ${
            health.memory_pct > 85 ? '#ef4444'
            : health.memory_pct > 70 ? '#f59e0b'
            : '#2a2d3a'
          }`,
          borderRadius: 10,
          padding: '9px 14px',
          fontSize: 11,
          color: '#64748b',
          zIndex: 9999,
          minWidth: 110,
          boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
          userSelect: 'none',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 5 }}>
            <span style={{ fontSize: 9 }}>💾</span>
            <span style={{
              color: health.memory_pct > 85 ? '#ef4444'
                   : health.memory_pct > 70 ? '#f59e0b'
                   : '#94a3b8',
              fontWeight: 600,
            }}>
              {health.memory_mb} MB
            </span>
            <span style={{ color: '#334155' }}>/ 512</span>
          </div>
          {/* Progress bar */}
          <div style={{ width: 82, height: 3, background: '#1e2330', borderRadius: 2 }}>
            <div style={{
              width: `${Math.min(health.memory_pct, 100)}%`,
              height: '100%',
              borderRadius: 2,
              transition: 'width 0.4s ease',
              background: health.memory_pct > 85 ? '#ef4444'
                        : health.memory_pct > 70 ? '#f59e0b'
                        : '#10b981',
            }} />
          </div>
          <div style={{ marginTop: 4, fontSize: 9, color: '#334155' }}>
            {health.memory_pct}% · RAM
          </div>
        </div>
      )}

      {/* Confirmation modal */}
      {showConfirm && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.7)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000,
        }}>
          <div style={{
            background: "#1a1d27",
            border: "1px solid #2a2d3a",
            borderRadius: 12,
            padding: 28,
            width: 320,
            textAlign: "center",
          }}>
            <p style={{
              fontSize: 20,
              fontWeight: 600,
              color: showConfirm.side === "BUY" ? "#10b981" : "#ef4444",
              marginBottom: 8,
              marginTop: 0,
            }}>
              Confirm {showConfirm.side}
            </p>
            <p style={{ fontSize: 14, color: "#94a3b8", marginBottom: 4 }}>
              {showConfirm.symbol}
            </p>
            <p style={{ fontSize: 24, fontWeight: 600, color: "#e2e8f0", marginBottom: 20 }}>
              ${showConfirm.price?.toFixed(2) || "—"}
            </p>
            <p style={{ fontSize: 12, color: "#475569", marginBottom: 20 }}>
              {status?.config?.dry_run
                ? "This is a DRY RUN — no real money"
                : "This will place a REAL market order"
              }
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <button
                onClick={() => setShowConfirm(null)}
                style={{
                  padding: "10px",
                  background: "transparent",
                  border: "1px solid #2a2d3a",
                  borderRadius: 6,
                  color: "#64748b",
                  cursor: "pointer",
                  fontFamily: "inherit",
                  fontSize: 14,
                }}
              >
                Cancel
              </button>
              <button
                onClick={confirmTrade}
                style={{
                  padding: "10px",
                  background: showConfirm.side === "BUY" ? "#0f2d1a" : "#2d0f0f",
                  border: `1px solid ${showConfirm.side === "BUY" ? "#10b981" : "#ef4444"}`,
                  borderRadius: 6,
                  color: showConfirm.side === "BUY" ? "#10b981" : "#ef4444",
                  cursor: "pointer",
                  fontFamily: "inherit",
                  fontSize: 14,
                  fontWeight: 500,
                }}
              >
                Confirm {showConfirm.side}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
