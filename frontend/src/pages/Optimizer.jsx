/**
 * Optimizer.jsx
 * Performs async parameter sweep optimization to discover the best RSI thresholds.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useOptimizer } from '../hooks/useOptimizer'

import TickerSelect from '../components/TickerSelect'

export default function Optimizer() {
  const { job, loading, error, start } = useOptimizer()
  const navigate = useNavigate()

  // Form parameters
  const [symbol, setSymbol] = useState('AAPL')
  const [startCapital, setStartCapital] = useState(10000)
  const [startDate, setStartDate] = useState('2019-01-01')
  const [endDate, setEndDate] = useState('2023-01-01')
  const optimizerResults = job?.status === 'complete' && Array.isArray(job.results)
    ? job.results
    : []

  const handleSubmit = (e) => {
    e.preventDefault()
    start({
      symbol: symbol.toUpperCase(),
      start_capital: parseFloat(startCapital),
      start: startDate,
      end: endDate,
    })
  }

  // Pre-fill bot config and redirect to dashboard
  const handleUseConfig = (cfg) => {
    const configPreset = {
      symbol: symbol.toUpperCase(),
      rsi_period: cfg.rsi_period,
      oversold: cfg.oversold,
      overbought: cfg.overbought,
      stop_loss_pct: cfg.stop_loss_pct,
      take_profit_pct: cfg.take_profit_pct,
      risk_per_trade_pct: 2.0, // default placeholder
    }
    localStorage.setItem('bot_config_preset', JSON.stringify(configPreset))
    navigate('/')
  }

  const metricValue = (row, ...keys) => {
    for (const key of keys) {
      const value = Number(row?.[key])
      if (Number.isFinite(value)) return value
    }
    return 0
  }

  const returnPct = (row) => {
    const explicitReturn = Number(row?.total_return)
    if (Number.isFinite(explicitReturn)) return explicitReturn

    const totalPnl = Number(row?.total_pnl)
    const capital = Number(startCapital)
    if (Number.isFinite(totalPnl) && Number.isFinite(capital) && capital > 0) {
      return (totalPnl / capital) * 100
    }

    return 0
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Parameters Form Card */}
      <div style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '28px',
      }}>
        <h3 style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text)', marginBottom: '4px' }}>
          Parameter Optimizer Setup
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '24px' }}>
          Simulate a grid of 100+ variations to discover optimal buy/sell boundaries
        </p>

        <form onSubmit={handleSubmit} style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '20px',
          alignItems: 'end',
        }}>
          <div>
            <label style={labelStyle}>Ticker Symbol</label>
            <TickerSelect
              value={symbol}
              onChange={setSymbol}
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
          <div>
            <label style={labelStyle}>Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              style={inputStyle}
              required
            />
          </div>
          <div>
            <label style={labelStyle}>End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              style={inputStyle}
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '12px 24px',
              background: 'var(--blue)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--radius)',
              fontWeight: '600',
              fontSize: '14px',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
              height: '42px',
            }}
          >
            {loading ? 'Starting...' : 'Run Optimization Grid'}
          </button>
        </form>

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid var(--red)',
            color: 'var(--red)',
            padding: '14px',
            borderRadius: 'var(--radius)',
            fontSize: '13px',
            marginTop: '20px',
          }}>
            {error}
          </div>
        )}
      </div>

      {/* Progress Monitor Card */}
      {job && (job.status === 'pending' || job.status === 'running') && (
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <span style={{ fontSize: '14px', fontWeight: '600' }}>Running Grid Sweep...</span>
              <span style={{ fontSize: '12px', color: 'var(--muted)', marginLeft: '12px' }}>
                Job ID: {job.job_id}
              </span>
            </div>
            <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--blue)' }}>
              {job.progress}%
            </span>
          </div>
          <div style={{
            height: '8px',
            background: '#12141c',
            borderRadius: '4px',
            overflow: 'hidden',
          }}>
            <div style={{
              width: `${job.progress}%`,
              height: '100%',
              background: 'var(--blue)',
              boxShadow: '0 0 8px var(--blue)',
              transition: 'width 0.4s ease',
            }} />
          </div>
        </div>
      )}

      {/* Results Table Card */}
      {job && job.status === 'complete' && (
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '24px',
        }}>
          <div style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text)' }}>
              Top 20 Optimized Configurations
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--muted)' }}>
              Sorted by overall profitability and risk metrics
            </p>
          </div>

          {optimizerResults.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                textAlign: 'left',
              }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Period</th>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Oversold</th>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Overbought</th>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Stop Loss %</th>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Take Profit %</th>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Trades</th>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Win Rate</th>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Total Return</th>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Sharpe</th>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600' }}>Score</th>
                    <th style={{ padding: '12px 14px', color: 'var(--muted)', fontSize: '12px', fontWeight: '600', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {optimizerResults.map((r, idx) => {
                    const isTopRow = idx === 0
                    const trades = metricValue(r, 'trades', 'total_trades')
                    const winRate = metricValue(r, 'win_rate')
                    const totalReturn = returnPct(r)
                    const sharpe = metricValue(r, 'sharpe', 'sharpe_ratio')
                    const score = metricValue(r, 'score')

                    return (
                      <tr
                        key={`${r.rsi_period}-${r.oversold}-${r.overbought}-${r.stop_loss_pct}-${r.take_profit_pct}`}
                        style={{
                          borderBottom: '1px solid var(--border)',
                          background: isTopRow
                            ? 'rgba(16, 185, 129, 0.05)'
                            : idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
                        }}
                      >
                        <td style={{ padding: '14px 14px', fontWeight: isTopRow ? '600' : 'normal' }}>{r.rsi_period}</td>
                        <td style={{ padding: '14px 14px' }}>{r.oversold}</td>
                        <td style={{ padding: '14px 14px' }}>{r.overbought}</td>
                        <td style={{ padding: '14px 14px' }}>{r.stop_loss_pct}%</td>
                        <td style={{ padding: '14px 14px' }}>{r.take_profit_pct}%</td>
                        <td style={{ padding: '14px 14px' }}>{trades}</td>
                        <td style={{ padding: '14px 14px' }}>{(winRate * 100).toFixed(1)}%</td>
                        <td style={{
                          padding: '14px 14px',
                          color: totalReturn >= 0 ? 'var(--green)' : 'var(--red)',
                          fontWeight: '600',
                        }}>
                          {totalReturn >= 0 ? '+' : ''}{totalReturn.toFixed(2)}%
                        </td>
                        <td style={{ padding: '14px 14px' }}>{sharpe.toFixed(2)}</td>
                        <td style={{ padding: '14px 14px', color: 'var(--blue)', fontWeight: '600' }}>{score.toFixed(2)}</td>
                        <td style={{ padding: '14px 14px', textAlign: 'right' }}>
                          <button
                            onClick={() => handleUseConfig(r)}
                            style={{
                              padding: '6px 12px',
                              background: isTopRow ? 'var(--green)' : 'transparent',
                              color: isTopRow ? 'white' : 'var(--muted)',
                              border: isTopRow ? 'none' : '1px solid var(--border)',
                              borderRadius: 'var(--radius)',
                              fontSize: '12px',
                              fontWeight: '600',
                              cursor: 'pointer',
                            }}
                          >
                            Use Config
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '24px',
              color: 'var(--muted)',
              fontSize: '13px',
              textAlign: 'center',
            }}>
              Optimization finished, but no valid parameter combinations returned results.
            </div>
          )}
        </div>
      )}

      {/* Idle / Initial State Placeholder */}
      {(!job || job.status === 'error') && (
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          height: '350px',
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
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
          <h4 style={{ color: 'var(--text)', fontSize: '15px', fontWeight: '600', marginBottom: '8px' }}>
            Optimizer Offline
          </h4>
          <p style={{ fontSize: '12px', maxWidth: '300px' }}>
            Start an optimization sweep above to test 100+ variations on backtest data and see results here.
          </p>
        </div>
      )}
    </div>
  )
}
