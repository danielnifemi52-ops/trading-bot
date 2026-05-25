/**
 * Backtest.jsx
 * Simulates the RSI trading strategy against historical stock price records.
 */
import { useMemo, useState } from 'react'
import { useBacktest } from '../hooks/useBacktest'
import StatCard from '../components/StatCard'
import EquityChart from '../components/EquityChart'

import TickerSelect from '../components/TickerSelect'
import RSIPeriodSelect from '../components/RSIPeriodSelect'

const MIN_DAYS_REQUIRED = {
  '1d': 90,
  '1h': 7,
  '15m': 3,
  '5m': 2,
}

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

  const handleIntervalChange = (e) => {
    const newInterval = e.target.value
    const today = new Date()
    const fmt = (d) => {
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }

    const defaults = {
      '1d': {
        start: fmt(new Date(today.getFullYear() - 2, today.getMonth(), today.getDate())),
        end: fmt(today),
      },
      '1h': {
        start: fmt(new Date(today.getTime() - 55 * 24 * 60 * 60 * 1000)),
        end: fmt(today),
      },
      '15m': {
        start: fmt(new Date(today.getTime() - 55 * 24 * 60 * 60 * 1000)),
        end: fmt(today),
      },
      '5m': {
        start: fmt(new Date(today.getTime() - 55 * 24 * 60 * 60 * 1000)),
        end: fmt(today),
      },
    }

    const range = defaults[newInterval] || defaults['1d']
    setIntervalVal(newInterval)
    setStart(range.start)
    setEnd(range.end)
  }

  const dateRangeDays = useMemo(() => {
    if (!start || !end) return 0

    const startDate = new Date(start)
    const endDate = new Date(end)
    const days = Math.floor((endDate - startDate) / (1000 * 60 * 60 * 24))

    return Number.isFinite(days) ? days : 0
  }, [start, end])

  const minDays = MIN_DAYS_REQUIRED[interval] || 90
  const dateRangeTooShort = dateRangeDays < minDays
  const rsiThresholdInvalid = oversold !== "" && overbought !== "" && oversold >= overbought
  const runDisabled = loading || dateRangeTooShort || rsiThresholdInvalid

  const capitalValue = Number(startCapital)
  const capitalLabel = Number.isFinite(capitalValue) ? capitalValue.toLocaleString() : '0'

  const handleSubmit = (e) => {
    e.preventDefault()
    if (runDisabled) return

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
                onChange={handleIntervalChange}
                style={inputStyle}
              >
                <option value="1d">Daily (1d)</option>
                <option value="1wk">Weekly (1wk)</option>
                <option value="1h">Hourly (1h)</option>
                <option value="15m">15 Minute (15m)</option>
                <option value="5m">5 Minute (5m)</option>
              </select>
              {['1h', '15m', '5m'].includes(interval) && (
                <p style={{ fontSize: 11, color: '#f59e0b', marginTop: 4 }}>
                  Intraday intervals use Alpaca historical data and may take longer.
                </p>
              )}
            </div>
            <div>
              <label style={labelStyle}>RSI Period</label>
              <RSIPeriodSelect
                value={rsiPeriod}
                onChange={setRsiPeriod}
              />
            </div>
          </div>

          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Oversold (Buy)</label>
              <input
                type="number"
                min={1}
                max={49}
                value={oversold}
                onChange={(e) => {
                  const val = parseInt(e.target.value)
                  if (!isNaN(val)) setOversold(val)
                  else if (e.target.value === "") setOversold("")
                }}
                style={inputStyle}
                required
              />
            </div>
            <div>
              <label style={labelStyle}>Overbought (Sell)</label>
              <input
                type="number"
                min={51}
                max={99}
                value={overbought}
                onChange={(e) => {
                  const val = parseInt(e.target.value)
                  if (!isNaN(val)) setOverbought(val)
                  else if (e.target.value === "") setOverbought("")
                }}
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
                min={1}
                max={50}
                step="0.1"
                value={stopLossPct}
                onChange={(e) => {
                  const val = parseFloat(e.target.value)
                  if (!isNaN(val)) setStopLossPct(val)
                  else if (e.target.value === "") setStopLossPct("")
                }}
                style={inputStyle}
                required
              />
            </div>
            <div>
              <label style={labelStyle}>Take Profit %</label>
              <input
                type="number"
                min={1}
                max={100}
                step="0.1"
                value={takeProfitPct}
                onChange={(e) => {
                  const val = parseFloat(e.target.value)
                  if (!isNaN(val)) setTakeProfitPct(val)
                  else if (e.target.value === "") setTakeProfitPct("")
                }}
                style={inputStyle}
                required
              />
            </div>
          </div>

          {rsiThresholdInvalid && (
            <p style={{ color: "#ef4444", fontSize: 11, marginTop: -8, marginBottom: 12 }}>
              Oversold must be lower than Overbought
            </p>
          )}

          {dateRangeTooShort && (
            <div style={{
              background: "#1c0f0f",
              border: "1px solid #ef4444",
              borderRadius: 6,
              padding: "10px 14px",
              marginTop: 8,
              marginBottom: 12,
              fontSize: 12,
              color: "#fca5a5",
            }}>
              <span aria-hidden="true">&times;</span> Date range too short. {interval} interval needs at least {minDays} days.
              {' '}
              Currently selected: {dateRangeDays} days.
            </div>
          )}

          <div style={{
            background: "#0f1117",
            border: "1px solid #2a2d3a",
            borderRadius: 6,
            padding: "10px 14px",
            marginBottom: 12,
            fontSize: 12,
            color: "#64748b",
          }}>
            <span style={{ color: "#94a3b8" }}>Ready to test: </span>
            <span style={{ color: "#e2e8f0" }}>{symbol.toUpperCase()}</span>
            {' \u00b7 '}
            <span style={{ color: "#e2e8f0" }}>{interval}</span>
            {' \u00b7 '}
            <span style={{ color: "#e2e8f0" }}>{dateRangeDays} days</span>
            {' \u00b7 '}
            RSI {rsiPeriod} {'\u00b7'} SL {stopLossPct}% {'\u00b7'} TP {takeProfitPct}%
            {' \u00b7 '}
            <span style={{ color: "#10b981" }}>${capitalLabel} capital</span>
          </div>

          <button
            type="submit"
            disabled={runDisabled}
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
              cursor: runDisabled ? 'not-allowed' : 'pointer',
              opacity: runDisabled ? 0.5 : 1,
              boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
            }}
          >
            {loading ? 'Running simulation...' : 'Run Simulation'}
          </button>
          {loading && (
            <p style={{ fontSize: 12, color: '#64748b', marginTop: 8, textAlign: 'center' }}>
              Intraday backtests can take 60-90 seconds. Please wait...
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

            {result && result.stats.total_trades === 0 && (
              <div style={{
                background: "#1c1a0f",
                border: "1px solid #f59e0b",
                borderRadius: 8,
                padding: "12px 16px",
                marginTop: 24,
                marginBottom: 0,
                fontSize: 13,
                color: "#fbbf24",
              }}>
                ⚠ No trades were executed in this period. This usually means:
                <ul style={{ marginTop: 6, paddingLeft: 20, color: "#94a3b8" }}>
                  <li>Date range is too short (use at least 1 year)</li>
                  <li>RSI never crossed your thresholds in this period</li>
                  <li>Try widening thresholds: oversold 35, overbought 65</li>
                  <li>Try a more volatile stock or a bear market date range</li>
                </ul>
              </div>
            )}

            {/* Equity Curve Chart */}
            <EquityChart data={result.equity_curve} />

            {(() => {
              const interpret = (stats) => {
                const tips = []
                if (stats.total_trades < 10 && stats.total_trades > 0)
                  tips.push({ level: "warn", msg: "Less than 10 trades — results are not statistically reliable. Use a longer date range." })
                if (stats.total_trades > 0 && stats.profit_factor < 1)
                  tips.push({ level: "bad",  msg: "Profit factor below 1 means this strategy loses money overall in this period." })
                if (stats.total_trades > 0 && stats.profit_factor >= 1 && stats.profit_factor < 1.3)
                  tips.push({ level: "warn", msg: "Profit factor between 1 and 1.3 is marginal — fees and slippage could erase this edge." })
                if (stats.total_trades > 0 && stats.profit_factor >= 1.5)
                  tips.push({ level: "good", msg: "Profit factor above 1.5 is solid. Validate on a different date range before going live." })
                if (stats.total_trades > 0 && stats.win_rate < 0.4)
                  tips.push({ level: "warn", msg: "Win rate below 40% — the strategy loses more often than it wins. Widen RSI thresholds." })
                if (stats.total_trades > 0 && stats.max_drawdown_pct < -20)
                  tips.push({ level: "bad",  msg: "Max drawdown over 20% — too much risk per trade. Reduce stop loss % or risk per trade %." })
                if (stats.total_trades > 0 && stats.sharpe_ratio > 1)
                  tips.push({ level: "good", msg: "Sharpe ratio above 1 — good risk-adjusted return." })
                if (stats.total_trades > 0 && stats.sharpe_ratio < 0)
                  tips.push({ level: "bad",  msg: "Negative Sharpe ratio — you would have done better holding cash." })
                if (stats.total_trades > 0 && Math.abs(stats.avg_loss) > stats.avg_win)
                  tips.push({ level: "bad",  msg: "Average loss is bigger than average win — increase take profit % or decrease stop loss %." })
                return tips
              }

              const COLORS = { good: "#10b981", warn: "#f59e0b", bad: "#ef4444" }
              const ICONS  = { good: "✓", warn: "⚠", bad: "✕" }

              const tipsList = interpret(result.stats);
              if (tipsList.length === 0) return null;

              return (
                <div style={{ marginTop: 16 }}>
                  <p style={{ fontSize: 12, color: "#64748b", marginBottom: 8, fontWeight: '600', letterSpacing: '0.05em' }}>
                    STRATEGY ANALYSIS
                  </p>
                  {tipsList.map((tip, i) => (
                    <div key={i} style={{
                      display: "flex", gap: 10, padding: "10px 14px",
                      marginBottom: 6, borderRadius: 6,
                      background: COLORS[tip.level] + "12",
                      border: `1px solid ${COLORS[tip.level]}33`,
                    }}>
                      <span style={{ color: COLORS[tip.level], fontWeight: 700, fontSize: 14 }}>
                        {ICONS[tip.level]}
                      </span>
                      <span style={{ fontSize: 13, color: "#cbd5e1" }}>{tip.msg}</span>
                    </div>
                  ))}
                </div>
              );
            })()}

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
