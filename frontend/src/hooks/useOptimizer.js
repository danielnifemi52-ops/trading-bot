import { useState, useCallback, useEffect } from 'react'
import { startOptimizer as apiStartOptimizer, getOptimizerJob } from '../api/client'

export function useOptimizer() {
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [pollInterval, setPollInterval] = useState(null)

  const start = useCallback(async (params) => {
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
            clearInterval(interval)
            setLoading(false)
          }
        } catch (e) {
          clearInterval(interval)
          setError(e.response?.data?.detail || e.message || 'Failed to poll optimizer')
          setLoading(false)
        }
      }, 2000)
      
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to start optimizer')
      setLoading(false)
    }
  }, [])

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval)
      }
    }
  }, [pollInterval])

  return { job, loading, error, start }
}

