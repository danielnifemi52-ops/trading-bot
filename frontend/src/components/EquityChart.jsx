/**
 * EquityChart.jsx
 * Recharts area chart for showing the bot's equity curve over time.
 */
import React from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'

export default function EquityChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '350px',
        border: '1px dashed var(--border)',
        borderRadius: 'var(--radius)',
        color: 'var(--muted)',
        background: 'var(--surface)',
      }}>
        No data yet. Run a backtest to see the equity curve.
      </div>
    )
  }

  // Format currency helper
  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val)
  }

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      padding: '24px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{ marginBottom: '16px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text)' }}>
          Equity Curve
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--muted)' }}>
          Portfolio value simulation over time
        </p>
      </div>

      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--green)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="var(--green)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              stroke="var(--muted)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              dy={10}
            />
            <YAxis
              stroke="var(--muted)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `$${v}`}
              dx={-10}
              domain={['auto', 'auto']}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                color: 'var(--text)',
                fontSize: '12px',
                fontFamily: 'inherit',
              }}
              formatter={(value) => [formatCurrency(value), 'Equity']}
              labelStyle={{ fontWeight: '600', color: 'var(--text)', marginBottom: '4px' }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="var(--green)"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorEquity)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
