/**
 * Dashboard.jsx
 * The main bot control room. Shows live tickers, RSI gauge,
 * start/stop parameters, and recent tick history.
 */
import React, { useState, useEffect } from 'react'
import { useBot } from '../hooks/useBot'
import { getBotLogs } from '../api/client'
import StatCard from '../components/StatCard'
import RSIGauge from '../components/RSIGauge'
import BotControls from '../components/BotControls'
import SignalBadge from '../components/SignalBadge'

export default function Dashboard() {
  const { status, liveData, loading, error, start, stop } = useBot()
  const [logs, setLogs] = useState([])
  const [logsLoading, setLogsLoading] = useState(false)

  // Fetch logs on mount and whenever the bot status changes (e.g. started/stopped)
  const fetchLogs = async () => {
    try {
      setLogsLoading(true)
      const { data } = await getBotLogs(10)
      setLogs(data)
    } catch (e) {
      console.error('Failed to fetch bot logs:', e)
    } finally {
      setLogsLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [status?.running])

  // Refresh logs when new live tick data is received via WS
  useEffect(() => {
    if (liveData) {
      // Append the new tick to the local logs list, maintaining at most 10 items
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
    }
  }, [liveData])

  // Get current active values (prefer WebSocket live data, fall back to last status value)
  const currentPrice = liveData?.price ?? status?.last_price
  const currentRsi = liveData?.rsi ?? status?.last_rsi
  const currentSignal = liveData?.signal ?? status?.last_signal ?? 'HOLD'
  const accountValue = liveData?.account ?? status?.account_value ?? 10000.0

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

      {/* Top row: 4 Metric Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '24px',
      }}>
        <StatCard
          label="Current Price"
          value={currentPrice ? formatPrice(currentPrice) : '--'}
          sub={status?.symbol ? `Symbol: ${status.symbol}` : 'Bot Idle'}
          highlight={currentPrice ? 'var(--blue)' : undefined}
        />
        <StatCard
          label="RSI Value (14h)"
          value={currentRsi ? formatRsi(currentRsi) : '--'}
          sub="Wilder's Smoothed RSI"
          highlight={currentRsi ? (currentRsi <= status?.config?.oversold ? 'var(--green)' : currentRsi >= status?.config?.overbought ? 'var(--red)' : 'var(--text)') : undefined}
        />
        <StatCard
          label="Current Signal"
          value={<SignalBadge signal={currentSignal} />}
          sub={status?.running ? 'Live Signal Polling' : 'Bot Offline'}
        />
        <StatCard
          label="Simulated Account Value"
          value={formatPrice(accountValue)}
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
            <RSIGauge value={currentRsi} />
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
    </div>
  )
}
