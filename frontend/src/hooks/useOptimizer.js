import { useState, useCallback, useEffect, useRef } from 'react'
import { startOptimizer as apiStartOptimizer, getOptimizerJob } from '../api/client'

export function useOptimizer() {
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const pollIntervalRef = useRef(null)

  const clearPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  const start = useCallback(async (params) => {
    clearPolling()
    setLoading(true)
    setError(null)
    setJob(null)
    try {
      const response = await apiStartOptimizer(params)
      const jobId = response.data.job_id
      setJob({ ...response.data, job_id: jobId })
      
      // Start polling
      const interval = setInterval(async () => {
        try {
          const res = await getOptimizerJob(jobId)
          const jobData = res.data
          setJob(jobData)
          
          if (jobData.status === 'complete' || jobData.status === 'error') {
            clearPolling()
            setLoading(false)
          }
        } catch (e) {
          clearPolling()
          setError(e.response?.data?.detail || e.message || 'Failed to poll optimizer')
          setLoading(false)
        }
      }, 2000)
      pollIntervalRef.current = interval
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to start optimizer')
      setLoading(false)
    }
  }, [clearPolling])

  // Cleanup interval on unmount
  useEffect(() => {
    return clearPolling
  }, [clearPolling])

  return { job, loading, error, start }
}

