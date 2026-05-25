/**
 * Trades.jsx
 * View completed trades database history, check stats, and filter results.
 */
import React, { useState, useEffect } from 'react'
import { getTrades, getTradeStats, deleteTrade } from '../api/client'
import StatCard from '../components/StatCard'

export default function Trades() {
  const [trades, setTrades] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Filters state
  const [symbolFilter, setSymbolFilter] = useState('')
  const [sideFilter, setSideFilter] = useState('ALL')

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const statsRes = await getTradeStats()
      setStats(statsRes.data)

      const tradesRes = await getTrades(100, symbolFilter || undefined)
      setTrades(tradesRes.data)
    } catch (e) {
      setError('Failed to fetch trades data: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [symbolFilter]) // Re-run when symbol filter changes

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this trade record?')) return
    try {
      await deleteTrade(id)
      fetchData()
    } catch (e) {
      alert('Failed to delete trade: ' + e.message)
    }
  }

  const formatPrice = (val) => {
    if (val === undefined || val === null) return '--'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(val)
  }

  // Filter trades locally for "side"
  const filteredTrades = trades.filter((t) => {
    if (sideFilter === 'ALL') return true
    return t.side === sideFilter
  })

  // Compute local values
  const winRate = stats ? (stats.win_rate * 100).toFixed(1) : '0.0'
  const totalPnL = stats ? stats.total_pnl : 0.0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid var(--red)',
          color: 'var(--red)',
          padding: '14px',
          borderRadius: 'var(--radius)',
          fontSize: '13px',
        }}>
          {error}
        </div>
      )}

      {/* Top row: Stats cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '24px',
      }}>
        <StatCard
          label="Total Trades"
          value={stats?.total_trades ?? 0}
          sub="Stored in database"
        />
        <StatCard
          label="Win Rate"
          value={`${winRate}%`}
          sub="Percent of profitable closes"
          highlight="var(--blue)"
        />
        <StatCard
          label="Cumulative Profit/Loss"
          value={formatPrice(totalPnL)}
          sub="Total realized return"
          highlight={totalPnL >= 0 ? 'var(--green)' : 'var(--red)'}
        />
        <StatCard
          label="Profit Factor"
          value={stats?.profit_factor ?? '0.00'}
          sub="Ratio of gross gains/losses"
        />
      </div>

      {/* Filters & Control Panel */}
      <div style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '20px 24px',
        display: 'flex',
        flexWrap: 'wrap',
        gap: '20px',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: '600', textTransform: 'uppercase' }}>
              Filter Symbol
            </label>
            <input
              type="text"
              placeholder="e.g. AAPL"
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
              style={{
                display: 'block',
                marginTop: '4px',
                padding: '8px 12px',
                background: '#12141c',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                color: 'var(--text)',
                outline: 'none',
                width: '140px',
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: '600', textTransform: 'uppercase' }}>
              Filter Side
            </label>
            <select
              value={sideFilter}
              onChange={(e) => setSideFilter(e.target.value)}
              style={{
                display: 'block',
                marginTop: '4px',
                padding: '8px 12px',
                background: '#12141c',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                color: 'var(--text)',
                outline: 'none',
                width: '140px',
                cursor: 'pointer',
              }}
            >
              <option value="ALL">All Sides</option>
              <option value="BUY">Buy</option>
              <option value="SELL">Sell</option>
            </select>
          </div>
        </div>

        <button
          onClick={fetchData}
          disabled={loading}
          style={{
            padding: '8px 16px',
            background: 'transparent',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            color: 'var(--text)',
            fontSize: '13px',
            fontWeight: '600',
            cursor: 'pointer',
          }}
        >
          {loading ? 'Refreshing...' : 'Refresh Records'}
        </button>
      </div>

      {/* Trade Log Table Card */}
      <div style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '24px',
      }}>
        <h3 style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text)', marginBottom: '20px' }}>
          Historical Trade Log Entries
        </h3>

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
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Side</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Price</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Qty</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>RSI at Signal</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Realised PNL</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Exit Reason</th>
                <th style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.length === 0 ? (
                <tr>
                  <td colSpan="9" style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)' }}>
                    No matching trade records found.
                  </td>
                </tr>
              ) : (
                filteredTrades.map((t) => {
                  const hasPnL = t.pnl !== undefined && t.pnl !== null
                  const isProfit = hasPnL && t.pnl > 0
                  const isLoss = hasPnL && t.pnl < 0
                  return (
                    <tr
                      key={t.id}
                      style={{
                        borderBottom: '1px solid var(--border)',
                        background: isProfit
                          ? 'rgba(16, 185, 129, 0.02)'
                          : isLoss
                            ? 'rgba(239, 68, 68, 0.02)'
                            : 'transparent',
                      }}
                    >
                      <td style={{ padding: '14px 16px', color: 'var(--muted)', fontSize: '13px' }}>
                        {new Date(t.timestamp).toLocaleString()}
                      </td>
                      <td style={{ padding: '14px 16px', fontWeight: '700' }}>{t.symbol}</td>
                      <td style={{ padding: '14px 16px' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: '600',
                          background: t.side === 'BUY' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: t.side === 'BUY' ? 'var(--green)' : 'var(--red)',
                        }}>
                          {t.side}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px' }}>{formatPrice(t.price)}</td>
                      <td style={{ padding: '14px 16px' }}>{t.qty}</td>
                      <td style={{ padding: '14px 16px' }}>{t.rsi_at_signal.toFixed(2)}</td>
                      <td style={{
                        padding: '14px 16px',
                        fontWeight: '600',
                        color: isProfit ? 'var(--green)' : isLoss ? 'var(--red)' : 'var(--text)',
                      }}>
                        {hasPnL ? (isProfit ? '+' : '') + formatPrice(t.pnl) : '--'}
                      </td>
                      <td style={{ padding: '14px 16px', color: 'var(--muted)', fontSize: '12px' }}>
                        {t.exit_reason || '--'}
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        <button
                          onClick={() => handleDelete(t.id)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--muted)',
                            cursor: 'pointer',
                            fontSize: '16px',
                            padding: '4px 8px',
                            transition: 'color 0.2s',
                          }}
                          onMouseEnter={(e) => e.target.style.color = 'var(--red)'}
                          onMouseLeave={(e) => e.target.style.color = 'var(--muted)'}
                        >
                          &times;
                        </button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
