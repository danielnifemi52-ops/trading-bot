/**
 * useBot.js
 * Opens a WebSocket to /ws/live and exposes live bot data.
 * Also provides startBot / stopBot actions.
 * Re-connects automatically on disconnect.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { startBot as apiStart, stopBot as apiStop, getStatus } from '../api/client'

const WS_URL = (import.meta.env.VITE_WS_URL || 'ws://localhost:8000') + '/ws/live'

export function useBot() {
  const [status, setStatus]   = useState(null)   // BotStatusResponse
  const [liveData, setLive]   = useState(null)   // { price, rsi, signal, account }
  const [loading, setLoading] = useState(true)   // starts true for initial dashboard loading state
  const [error, setError]     = useState(null)
  const wsRef = useRef(null)

  // Poll status every 5 seconds
  useEffect(() => {
    let id = null
    const poll = async () => {
      try {
        const { data } = await getStatus()
        setStatus(data)
        setError(null)
      } catch (e) {
        setError(e.message)
        if (id) {
          clearInterval(id)
        }
      } finally {
        setLoading(false)
      }
    }
    id = setInterval(poll, 5000)
    poll()
    return () => {
      if (id) clearInterval(id)
    }
  }, [])

  // WebSocket for live tick data
  useEffect(() => {
    let reconnectTimer
    let attempts = 0

    const connect = () => {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        attempts = 0
      }
      ws.onmessage = (e) => {
        try {
          setLive(JSON.parse(e.data))
        } catch (err) {
          console.debug('Invalid WebSocket message', err)
        }
      }
      ws.onclose = () => {
        if (attempts < 5) {
          const delay = 1000 * Math.pow(2, attempts)
          attempts++
          reconnectTimer = setTimeout(connect, delay)
        } else {
          console.log('WebSocket: Max reconnect attempts reached (5)')
        }
      }
      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      clearTimeout(reconnectTimer)
      wsRef.current?.close()
    }
  }, [])

  const start = useCallback(async (config) => {
    setLoading(true)
    setError(null)
    try {
      await apiStart(config)
      const { data } = await getStatus()
      setStatus(data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const stop = useCallback(async () => {
    setLoading(true)
    try {
      await apiStop()
      const { data } = await getStatus()
      setStatus(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { status, liveData, loading, error, start, stop }
}

