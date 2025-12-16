/**
 * Hook per gestione stato training NLP
 */

import { useQuery } from '@tanstack/react-query'
import type { TrainingStatusResponse, SpacyStatus, BertStatus, PatternStats } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

// Fetch training status generale
async function fetchTrainingStatus(): Promise<TrainingStatusResponse> {
  const res = await fetch(`${API_BASE}/training/status`)
  if (!res.ok) throw new Error('Errore caricamento stato training')
  return res.json()
}

// Fetch spaCy status
async function fetchSpacyStatus(): Promise<SpacyStatus> {
  const res = await fetch(`${API_BASE}/training/spacy/status`)
  if (!res.ok) throw new Error('Errore caricamento stato spaCy')
  return res.json()
}

// Fetch BERT status
async function fetchBertStatus(): Promise<BertStatus> {
  const res = await fetch(`${API_BASE}/training/bert/status`)
  if (!res.ok) throw new Error('Errore caricamento stato BERT')
  return res.json()
}

// Fetch pattern stats
async function fetchPatternStats(): Promise<PatternStats> {
  const res = await fetch(`${API_BASE}/training/patterns/stats`)
  if (!res.ok) throw new Error('Errore caricamento statistiche pattern')
  return res.json()
}

export function useTrainingStatus() {
  const statusQuery = useQuery({
    queryKey: ['training-status'],
    queryFn: fetchTrainingStatus,
    staleTime: 30000, // 30 secondi
    refetchInterval: 60000 // Refresh ogni minuto
  })

  return {
    status: statusQuery.data,
    isLoading: statusQuery.isLoading,
    error: statusQuery.error,
    refetch: statusQuery.refetch
  }
}

export function useSpacyStatus() {
  const query = useQuery({
    queryKey: ['spacy-status'],
    queryFn: fetchSpacyStatus,
    staleTime: 30000
  })

  return {
    status: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch
  }
}

export function useBertStatus() {
  const query = useQuery({
    queryKey: ['bert-status'],
    queryFn: fetchBertStatus,
    staleTime: 30000
  })

  return {
    status: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch
  }
}

export function usePatternStats() {
  const query = useQuery({
    queryKey: ['pattern-stats'],
    queryFn: fetchPatternStats,
    staleTime: 30000
  })

  return {
    stats: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch
  }
}

// Hook combinato per tutti gli status
export function useAllStatus() {
  const training = useTrainingStatus()
  const spacy = useSpacyStatus()
  const bert = useBertStatus()
  const patterns = usePatternStats()

  return {
    training,
    spacy,
    bert,
    patterns,
    isLoading: training.isLoading || spacy.isLoading || bert.isLoading || patterns.isLoading,
    refetchAll: () => {
      training.refetch()
      spacy.refetch()
      bert.refetch()
      patterns.refetch()
    }
  }
}
