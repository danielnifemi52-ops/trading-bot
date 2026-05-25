/**
 * Backtest.jsx
 * Simulates the RSI trading strategy against historical stock price records.
 */
import React, { useState } from 'react'
import { useBacktest } from '../hooks/useBacktest'
import StatCard from '../components/StatCard'
import EquityChart from '../components/EquityChart'

export default function Backtest() {
  const { result, loading, error, run } = useBacktest()

  // Form state
  const [symbol, setSymbol] = useState('AAPL')
  const [start, setStart] = useState('2022-01-01')
  const [end, setEnd] = useState('2023-01-01')
  const [interval, setIntervalVal] = useState('1d')
  const [rsiPeriod, setRsiPeriod] = useState(14)
  const [oversold, setOversold] = useState(30)
  const [overbought, setOverbought] = useState(70)
  const [stopLossPct, setStopLossPct] = useState(5)
  const [takeProfitPct, setTakeProfitPct] = useState(10)
  const [startCapital, setStartCapital] = useState(10000)

  const handleSubmit = (e) => {
    e.preventDefault()
    run({
      symbol: symbol.toUpperCase(),
      start,
      end,
      interval,
      rsi_period: parseInt(rsiPeriod),
      oversold: parseFloat(oversold),
      overbought: parseFloat(overbought),
      stop_loss_pct: parseFloat(stopLossPct),
      take_profit_pct: parseFloat(takeProfitPct),
      start_capital: parseFloat(startCapital),
    })
  }

  const formatPrice = (val) => {
    if (val === undefined || val === null) return '--'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(val)
  }

  const inputStyle = {
    width: '100%',
    padding: '10px 14px',
    background: '#12141c',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    color: 'var(--text)',
    fontSize: '14px',
    marginTop: '6px',
    outline: 'none',
  }

  const labelStyle = {
    fontSize: '12px',
    color: 'var(--muted)',
    fontWeight: '500',
  }

  const rowStyle = {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
    marginBottom: '16px',
  }

  // Calculate return percent for stats display
  const returnPct = result?.stats && result.trades.length > 0
    ? ((result.stats.total_pnl / startCapital) * 100).toFixed(2)
    : '0.00'

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
      gap: '32px',
      alignItems: 'start',
    }}>
      {/* Left panel: Form */}
      <div style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '28px',
      }}>
        <h3 style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text)', marginBottom: '4px' }}>
          Backtest Parameters
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '24px' }}>
          Set dates and risk targets to run historical backtests
        </p>

        <form onSubmit={handleSubmit}>
          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Ticker Symbol</label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                style={inputStyle}
                required
              />
            </div>
            <div>
              <label style={labelStyle}>Start Capital ($)</label>
              <input
                type="number"
                value={startCapital}
                onChange={(e) => setStartCapital(e.target.value)}
                style={inputStyle}
                required
                min="100"
              />
            </div>
          </div>

          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Start Date</label>
              <input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                style={inputStyle}
                required
              />
            </div>
            <div>
              <label style={labelStyle}>End Date</label>
              <input
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                style={inputStyle}
                required
              />
            </div>
          </div>

          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Interval</label>
              <select
                value={interval}
                onChange={(e) => setIntervalVal(e.target.value)}
                style={inputStyle}
              >
                <option value="1d">Daily (1d)</option>
                <option value="1h">Hourly (1h)</option>
              </select>
              {interval === '1h' && (
                <p style={{ fontSize: 11, color: '#f59e0b', marginTop: 4 }}>
                  ⚠ Hourly interval downloads more data and takes ~60s longer
                </p>
              )}
            </div>
            <div>
              <label style={labelStyle}>RSI Period</label>
              <input
                type="number"
                value={rsiPeriod}
                onChange={(e) => setRsiPeriod(e.target.value)}
                style={inputStyle}
                required
              />
            </div>
          </div>

          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Oversold (Buy)</label>
              <input
                type="number"
                value={oversold}
                onChange={(e) => setOversold(e.target.value)}
                style={inputStyle}
                required
              />
            </div>
            <div>
              <label style={labelStyle}>Overbought (Sell)</label>
              <input
                type="number"
                value={overbought}
                onChange={(e) => setOverbought(e.target.value)}
                style={inputStyle}
                required
              />
            </div>
          </div>

          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Stop Loss %</label>
              <input
                type="number"
                step="0.1"
                value={stopLossPct}
                onChange={(e) => setStopLossPct(e.target.value)}
                style={inputStyle}
                required
              />
            </div>
            <div>
              <label style={labelStyle}>Take Profit %</label>
              <input
                type="number"
                step="0.1"
                value={takeProfitPct}
                onChange={(e) => setTakeProfitPct(e.target.value)}
                style={inputStyle}
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px',
              background: 'var(--blue)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--radius)',
              fontWeight: '600',
              fontSize: '14px',
              marginTop: '12px',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
            }}
          >
            {loading ? 'Running simulation...' : 'Run Simulation'}
          </button>
          {loading && (
            <p style={{ fontSize: 12, color: '#64748b', marginTop: 8, textAlign: 'center' }}>
              Hourly backtests can take 60-90 seconds. Please wait...
            </p>
          )}
        </form>

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid var(--red)',
            color: 'var(--red)',
            padding: '14px',
            borderRadius: 'var(--radius)',
            fontSize: '13px',
            marginTop: '16px',
          }}>
            {error}
          </div>
        )}
      </div>

      {/* Right panel: Results */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
        {loading ? (
          <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            height: '400px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--muted)',
            gap: '16px',
          }}>
            <div style={{
              width: '40px',
              height: '40px',
              border: '4px solid var(--border)',
              borderTopColor: 'var(--blue)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
            }} />
            <span>Analyzing historical prices. Please wait...</span>
            <style>{`
              @keyframes spin {
                to { transform: rotate(360deg); }
              }
            `}</style>
          </div>
        ) : result ? (
          <>
            {/* Stats Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '16px',
            }}>
              <StatCard
                label="Total Return"
                value={`${returnPct}%`}
                sub={`PNL: ${formatPrice(result.stats.total_pnl)}`}
                highlight={result.stats.total_pnl >= 0 ? 'var(--green)' : 'var(--red)'}
              />
              <StatCard
                label="Win Rate"
                value={`${(result.stats.win_rate * 100).toFixed(1)}%`}
                sub={`${result.stats.total_trades} trades executed`}
                highlight="var(--blue)"
              />
              <StatCard
                label="Max Drawdown"
                value={`${result.stats.max_drawdown_pct}%`}
                sub="Peak-to-trough risk"
                highlight="var(--yellow)"
              />
              <StatCard
                label="Sharpe Ratio"
                value={result.stats.sharpe_ratio}
                sub="Risk-adjusted return"
              />
              <StatCard
                label="Profit Factor"
                value={result.stats.profit_factor}
                sub="Gross wins / gross losses"
              />
              <StatCard
                label="Avg Win Trade"
                value={formatPrice(result.stats.avg_win)}
                sub="Average win amount"
              />
              <StatCard
                label="Avg Loss Trade"
                value={formatPrice(result.stats.avg_loss)}
                sub="Average loss amount"
              />
            </div>

            {/* Equity Curve Chart */}
            <EquityChart data={result.equity_curve} />

            {/* Trade Log */}
            <div style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '24px',
            }}>
              <h3 style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text)', marginBottom: '16px' }}>
                Simulated Trades History ({result.trades.length})
              </h3>
              <div style={{ overflowX: 'auto', maxHeight: '350px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      <th style={{ padding: '10px 14px', color: 'var(--muted)', fontSize: '12px' }}>Date</th>
                      <th style={{ padding: '10px 14px', color: 'var(--muted)', fontSize: '12px' }}>Buy/Entry</th>
                      <th style={{ padding: '10px 14px', color: 'var(--muted)', fontSize: '12px' }}>Sell/Exit</th>
                      <th style={{ padding: '10px 14px', color: 'var(--muted)', fontSize: '12px' }}>Qty</th>
                      <th style={{ padding: '10px 14px', color: 'var(--muted)', fontSize: '12px' }}>RSI</th>
                      <th style={{ padding: '10px 14px', color: 'var(--muted)', fontSize: '12px' }}>PNL</th>
                      <th style={{ padding: '10px 14px', color: 'var(--muted)', fontSize: '12px' }}>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.length === 0 ? (
                      <tr>
                        <td colSpan="7" style={{ padding: '20px', textAlign: 'center', color: 'var(--muted)' }}>
                          No trades were opened during this simulation period.
                        </td>
                      </tr>
                    ) : (
                      result.trades.map((t, idx) => (
                        <tr
                          key={idx}
                          style={{
                            borderBottom: '1px solid var(--border)',
                            background: t.pnl > 0 ? 'rgba(16, 185, 129, 0.03)' : t.pnl < 0 ? 'rgba(239, 68, 68, 0.03)' : 'transparent',
                          }}
                        >
                          <td style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '13px' }}>{t.date}</td>
                          <td style={{ padding: '12px 14px' }}>{formatPrice(t.entry)}</td>
                          <td style={{ padding: '12px 14px' }}>{formatPrice(t.exit)}</td>
                          <td style={{ padding: '12px 14px' }}>{t.qty}</td>
                          <td style={{ padding: '12px 14px' }}>{t.rsi}</td>
                          <td style={{
                            padding: '12px 14px',
                            fontWeight: '600',
                            color: t.pnl > 0 ? 'var(--green)' : t.pnl < 0 ? 'var(--red)' : 'var(--text)',
                          }}>
                            {t.pnl > 0 ? '+' : ''}{formatPrice(t.pnl)}
                          </td>
                          <td style={{ padding: '12px 14px', fontSize: '12px', color: 'var(--muted)' }}>{t.exit_reason}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : (
          <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            height: '400px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--muted)',
            textAlign: 'center',
            padding: '24px',
          }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" style={{ marginBottom: '16px' }}>
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <h4 style={{ color: 'var(--text)', fontSize: '15px', fontWeight: '600', marginBottom: '8px' }}>
              No Simulation Results Yet
            </h4>
            <p style={{ fontSize: '12px', maxWidth: '280px' }}>
              Select parameters and click "Run Simulation" to generate backtest metrics.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
