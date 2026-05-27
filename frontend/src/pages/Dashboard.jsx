/**
 * Dashboard.jsx
 * The main bot control room. Shows live tickers, RSI gauge,
 * start/stop parameters, and recent tick history.
 */
import { useState, useEffect, useCallback } from 'react'
import { useBot } from '../hooks/useBot'
import { getBotLogs } from '../api/client'
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
          label="Simulated Account Value"
          value={account !== null ? formatPrice(account) : '--'}
          sub="Risk per trade capital base"
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

        <BotControls
          status={status}
          onStart={start}
          onStop={stop}
          loading={loading}
        />
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
    </div>
  )
}
