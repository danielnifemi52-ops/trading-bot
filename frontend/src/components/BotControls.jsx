/**
 * BotControls.jsx
 * Control panel to start/stop the bot and configure its parameters.
 */
import React, { useState, useEffect } from 'react'

import TickerSelect from './TickerSelect'
import RSIPeriodSelect from './RSIPeriodSelect'

export default function BotControls({ status, onStart, onStop, loading }) {
  const [symbol, setSymbol] = useState('AAPL')
  const [rsiPeriod, setRsiPeriod] = useState(14)
  const [oversold, setOversold] = useState(30)
  const [overbought, setOverbought] = useState(70)
  const [stopLossPct, setStopLossPct] = useState(5)
  const [takeProfitPct, setTakeProfitPct] = useState(10)
  const [riskPerTradePct, setRiskPerTradePct] = useState(2)
  const [pollIntervalSeconds, setPollIntervalSeconds] = useState(300)
  const [dryRun, setDryRun] = useState(true)

  // Pre-fill form if bot is running with an active config
  useEffect(() => {
    if (status && status.running && status.config) {
      const cfg = status.config
      setSymbol(cfg.symbol || 'AAPL')
      setRsiPeriod(cfg.rsi_period || 14)
      setOversold(cfg.oversold || 30)
      setOverbought(cfg.overbought || 70)
      setStopLossPct(cfg.stop_loss_pct || 5)
      setTakeProfitPct(cfg.take_profit_pct || 10)
      setRiskPerTradePct(cfg.risk_per_trade_pct || 2)
      setPollIntervalSeconds(cfg.poll_interval_seconds || 300)
      setDryRun(cfg.dry_run !== undefined ? cfg.dry_run : true)
    }
  }, [status])

  const handleSubmit = (e) => {
    e.preventDefault()
    onStart({
      symbol: symbol.toUpperCase(),
      rsi_period: parseInt(rsiPeriod),
      oversold: parseFloat(oversold),
      overbought: parseFloat(overbought),
      stop_loss_pct: parseFloat(stopLossPct),
      take_profit_pct: parseFloat(takeProfitPct),
      risk_per_trade_pct: parseFloat(riskPerTradePct),
      poll_interval_seconds: parseInt(pollIntervalSeconds),
      dry_run: dryRun,
    })
  }

  const isRunning = status?.running

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
    transition: 'border-color 0.2s',
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

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      padding: '24px',
      height: '100%',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '24px',
        borderBottom: '1px solid var(--border)',
        paddingBottom: '16px',
      }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text)' }}>
            Bot Controls
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--muted)' }}>
            Configure and run the live RSI bot
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: isRunning ? 'var(--green)' : 'var(--muted)',
            boxShadow: isRunning ? '0 0 10px var(--green)' : 'none',
            display: 'inline-block',
          }} />
          <span style={{ fontSize: '12px', fontWeight: '600', textTransform: 'uppercase' }}>
            {isRunning ? 'Running' : 'Idle'}
          </span>
        </div>
      </div>

      {isRunning ? (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '280px',
          textAlign: 'center',
        }}>
          <div style={{
            fontSize: '15px',
            color: 'var(--text)',
            marginBottom: '8px',
            fontWeight: '500',
          }}>
            Trading active on <strong style={{ color: 'var(--blue)' }}>{status.symbol}</strong>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--muted)', marginBottom: '24px', maxWidth: '300px' }}>
            The bot is currently listening for hourly price alerts and executing trade logic in the background.
          </p>
          <button
            onClick={onStop}
            disabled={loading}
            style={{
              padding: '12px 36px',
              background: 'var(--red)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--radius)',
              fontWeight: '600',
              fontSize: '14px',
              boxShadow: '0 4px 12px rgba(239, 68, 68, 0.2)',
              transition: 'transform 0.2s, opacity 0.2s',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Stopping...' : 'Stop Trading Bot'}
          </button>
        </div>
      ) : (
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
                value={oversold}
                onChange={(e) => setOversold(e.target.value)}
                style={inputStyle}
                required
                min="1"
                max="99"
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
                min="1"
                max="99"
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
                min="0.1"
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
                min="0.1"
              />
            </div>
          </div>

          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Risk per Trade %</label>
              <input
                type="number"
                step="0.1"
                value={riskPerTradePct}
                onChange={(e) => setRiskPerTradePct(e.target.value)}
                style={inputStyle}
                required
                min="0.1"
                max="100"
              />
            </div>
            <div>
              <label style={labelStyle}>Poll Interval (Secs)</label>
              <input
                type="number"
                value={pollIntervalSeconds}
                onChange={(e) => setPollIntervalSeconds(e.target.value)}
                style={inputStyle}
                required
                min="5"
              />
            </div>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            marginBottom: '24px',
            marginTop: '8px',
          }}>
            <input
              type="checkbox"
              id="dryRun"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              style={{
                width: '18px',
                height: '18px',
                accentColor: 'var(--blue)',
                cursor: 'pointer',
              }}
            />
            <label htmlFor="dryRun" style={{
              fontSize: '13px',
              color: 'var(--text)',
              userSelect: 'none',
              cursor: 'pointer',
            }}>
              Dry Run Mode (Simulate orders without Alpaca)
            </label>
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
              boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Starting...' : 'Start Trading Bot'}
          </button>
        </form>
      )}
    </div>
  )
}
