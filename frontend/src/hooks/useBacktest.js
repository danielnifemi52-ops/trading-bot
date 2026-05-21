import { useState, useCallback } from 'react'
import { runBacktest } from '../api/client'

export function useBacktest() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = useCallback(async (params) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const response = await runBacktest(params)
      setResult(response.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Backtest failed')
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, loading, error, run }
}

