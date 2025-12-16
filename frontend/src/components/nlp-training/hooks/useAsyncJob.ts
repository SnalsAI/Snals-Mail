/**
 * Hook per gestione job asincroni (analisi, benchmark, training)
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import type { AsyncJob, JobType } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

interface UseAsyncJobOptions {
  onComplete?: (result: any) => void
  onError?: (error: string) => void
  pollingInterval?: number
  maxDuration?: number
}

export function useAsyncJob(options: UseAsyncJobOptions = {}) {
  const {
    onComplete,
    onError,
    pollingInterval = 2000,
    maxDuration = 600000 // 10 minuti
  } = options

  const [job, setJob] = useState<AsyncJob | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef<number>(0)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    setIsPolling(false)
  }, [])

  // Poll job status
  const pollJobStatus = useCallback(async (jobId: string, jobType: JobType) => {
    try {
      // Determina l'endpoint in base al tipo
      let url: string
      if (jobType === 'bert_training') {
        url = `${API_BASE}/training/bert/job/${jobId}`
      } else {
        url = `${API_BASE}/training/job/${jobId}`
      }

      const res = await fetch(url)
      if (!res.ok) {
        stopPolling()
        setJob(prev => prev ? { ...prev, status: 'failed', error: 'Job non trovato' } : null)
        onError?.('Job non trovato')
        return
      }

      const data = await res.json()

      setJob({
        job_id: jobId,
        type: jobType,
        status: data.status,
        progress: data.progress || 0,
        message: data.message || '',
        result: data.result,
        error: data.error
      })

      // Gestisci completamento
      if (data.status === 'completed') {
        stopPolling()
        onComplete?.(data.result)
      } else if (data.status === 'failed') {
        stopPolling()
        onError?.(data.error || 'Job fallito')
      }

      // Check timeout
      if (Date.now() - startTimeRef.current > maxDuration) {
        stopPolling()
        setJob(prev => prev ? { ...prev, status: 'failed', error: 'Timeout' } : null)
        onError?.('Job timeout')
      }
    } catch (err) {
      console.error('Errore polling job:', err)
    }
  }, [stopPolling, onComplete, onError, maxDuration])

  // Start polling
  const startPolling = useCallback((jobId: string, jobType: JobType) => {
    // Stop any existing polling
    stopPolling()

    // Initialize job state
    setJob({
      job_id: jobId,
      type: jobType,
      status: 'running',
      progress: 0,
      message: 'Avvio...'
    })

    startTimeRef.current = Date.now()
    setIsPolling(true)

    // Start polling
    pollingRef.current = setInterval(() => {
      pollJobStatus(jobId, jobType)
    }, pollingInterval)

    // First poll immediately
    pollJobStatus(jobId, jobType)
  }, [stopPolling, pollJobStatus, pollingInterval])

  // Start analyze batch job
  const startAnalyze = useCallback(async (emailIds: number[], tipo: string) => {
    const res = await fetch(`${API_BASE}/training/analyze/async`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email_ids: emailIds, tipo })
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Errore avvio analisi')
    }

    const data = await res.json()
    startPolling(data.job_id, 'analyze_batch')
    return data.job_id
  }, [startPolling])

  // Start benchmark job
  const startBenchmark = useCallback(async (
    emailIds: number[],
    tipo: string,
    name?: string,
    engine?: 'spacy' | 'bert'
  ) => {
    const endpoint = engine
      ? `${API_BASE}/training/${engine}/benchmark`
      : `${API_BASE}/training/benchmark/async`

    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email_ids: emailIds, tipo, name })
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Errore avvio benchmark')
    }

    const data = await res.json()

    // Se il benchmark restituisce direttamente il risultato (non async)
    if (data.benchmark) {
      return { immediate: true, result: data.benchmark }
    }

    startPolling(data.job_id, 'benchmark')
    return { immediate: false, job_id: data.job_id }
  }, [startPolling])

  // Start BERT training job
  const startBertTraining = useCallback(async (config: {
    epochs?: number
    batch_size?: number
    learning_rate?: number
  }) => {
    const res = await fetch(`${API_BASE}/training/bert/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Errore avvio training BERT')
    }

    const data = await res.json()
    startPolling(data.job_id, 'bert_training')
    return data.job_id
  }, [startPolling])

  // Reset job state
  const reset = useCallback(() => {
    stopPolling()
    setJob(null)
  }, [stopPolling])

  return {
    job,
    isPolling,
    isRunning: job?.status === 'running',
    isComplete: job?.status === 'completed',
    isFailed: job?.status === 'failed',
    progress: job?.progress || 0,
    message: job?.message || '',
    result: job?.result,
    error: job?.error,

    // Actions
    startAnalyze,
    startBenchmark,
    startBertTraining,
    stopPolling,
    reset
  }
}
