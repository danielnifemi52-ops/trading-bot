/**
 * client.js
 * Central Axios instance. All API calls go through this file.
 * Swap the baseURL here when deploying - nothing else changes.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 30000,
})

// Attach X-API-Key header if configured
if (import.meta.env.VITE_API_KEY) {
  api.defaults.headers.common['X-API-Key'] = import.meta.env.VITE_API_KEY
}

// -- Bot ----------------------------------------------------------------------

export const getStatus   = ()        => api.get('/api/bot/status')
export const startBot    = (config)  => api.post('/api/bot/start', config)
export const stopBot     = ()        => api.post('/api/bot/stop')
export const getBotLogs  = (limit)   => api.get(`/api/bot/logs?limit=${limit ?? 100}`)

// -- Backtest -----------------------------------------------------------------

export const runBacktest = (params)  => api.post('/api/backtest/run', params)

// -- Optimizer ----------------------------------------------------------------

export const startOptimizer  = (params) => api.post('/api/optimizer/run', params)
export const getOptimizerJob = (id)     => api.get(`/api/optimizer/status/${id}`)

// -- Trades -------------------------------------------------------------------

export const getTrades     = (limit, symbol) =>
  api.get('/api/trades/', { params: { limit: limit ?? 50, symbol } })
export const getTradeStats = ()             => api.get('/api/trades/stats')
export const deleteTrade   = (id)           => api.delete(`/api/trades/${id}`)

export default api
