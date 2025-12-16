/**
 * Hook per gestione training samples
 */

import { useState, useCallback, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { TrainingSample, TipoAnalisi } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

// Fetch samples
async function fetchSamples(tipo?: TipoAnalisi): Promise<TrainingSample[]> {
  const url = tipo
    ? `${API_BASE}/training/samples?tipo=${tipo}`
    : `${API_BASE}/training/samples`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Errore caricamento samples')
  const data = await res.json()
  return data.samples || []
}

// Approve sample
async function approveSample(sampleId: string, corrections?: Record<string, any>): Promise<void> {
  const res = await fetch(`${API_BASE}/training/samples/${sampleId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ corrections })
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Errore approvazione sample')
  }
}

// Delete sample
async function deleteSample(sampleId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/training/samples/${sampleId}`, {
    method: 'DELETE'
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Errore eliminazione sample')
  }
}

export function useSamples(tipo?: TipoAnalisi) {
  const queryClient = useQueryClient()
  const [selectedSamples, setSelectedSamples] = useState<Set<string>>(new Set())

  // Query samples
  const query = useQuery({
    queryKey: ['training-samples', tipo],
    queryFn: () => fetchSamples(tipo),
    staleTime: 30000
  })

  // Mutation approve
  const approveMutation = useMutation({
    mutationFn: ({ sampleId, corrections }: { sampleId: string; corrections?: Record<string, any> }) =>
      approveSample(sampleId, corrections),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training-samples'] })
      queryClient.invalidateQueries({ queryKey: ['training-status'] })
    }
  })

  // Mutation delete
  const deleteMutation = useMutation({
    mutationFn: deleteSample,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training-samples'] })
      queryClient.invalidateQueries({ queryKey: ['training-status'] })
    }
  })

  // Computed values
  const samples = query.data || []
  const pendingSamples = useMemo(() => samples.filter(s => !s.approved), [samples])
  const approvedSamples = useMemo(() => samples.filter(s => s.approved), [samples])

  // Sample selection
  const toggleSampleSelection = useCallback((sampleId: string) => {
    setSelectedSamples(prev => {
      const next = new Set(prev)
      if (next.has(sampleId)) {
        next.delete(sampleId)
      } else {
        next.add(sampleId)
      }
      return next
    })
  }, [])

  const selectAllPending = useCallback(() => {
    setSelectedSamples(new Set(pendingSamples.map(s => s.id)))
  }, [pendingSamples])

  const clearSelection = useCallback(() => {
    setSelectedSamples(new Set())
  }, [])

  // Bulk approve
  const approveSelected = useCallback(async () => {
    const results = { success: 0, errors: 0 }
    for (const sampleId of selectedSamples) {
      try {
        await approveSample(sampleId)
        results.success++
      } catch {
        results.errors++
      }
    }
    queryClient.invalidateQueries({ queryKey: ['training-samples'] })
    queryClient.invalidateQueries({ queryKey: ['training-status'] })
    clearSelection()
    return results
  }, [selectedSamples, queryClient, clearSelection])

  // Bulk delete
  const deleteSelected = useCallback(async () => {
    const results = { success: 0, errors: 0 }
    for (const sampleId of selectedSamples) {
      try {
        await deleteSample(sampleId)
        results.success++
      } catch {
        results.errors++
      }
    }
    queryClient.invalidateQueries({ queryKey: ['training-samples'] })
    queryClient.invalidateQueries({ queryKey: ['training-status'] })
    clearSelection()
    return results
  }, [selectedSamples, queryClient, clearSelection])

  return {
    // Data
    samples,
    pendingSamples,
    approvedSamples,

    // Loading states
    isLoading: query.isLoading,
    isApproving: approveMutation.isPending,
    isDeleting: deleteMutation.isPending,

    // Errors
    error: query.error,

    // Actions
    refetch: query.refetch,
    approve: (sampleId: string, corrections?: Record<string, any>) =>
      approveMutation.mutateAsync({ sampleId, corrections }),
    delete: (sampleId: string) => deleteMutation.mutateAsync(sampleId),

    // Selection
    selectedSamples,
    toggleSampleSelection,
    selectAllPending,
    clearSelection,
    approveSelected,
    deleteSelected
  }
}
