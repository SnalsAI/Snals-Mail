/**
 * Hook per gestione pattern NLP
 */

import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Pattern, PatternLabel, PatternSource, PatternMatch } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

// Fetch patterns
async function fetchPatterns(
  source?: PatternSource,
  label?: PatternLabel
): Promise<{ patterns: Pattern[]; total: number; by_source: Record<string, number>; by_label: Record<string, number> }> {
  const params = new URLSearchParams()
  if (source) params.set('source', source)
  if (label) params.set('label', label)

  const url = `${API_BASE}/training/patterns${params.toString() ? '?' + params.toString() : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Errore caricamento pattern')
  return res.json()
}

// Add manual pattern
async function addPattern(data: {
  label: PatternLabel
  pattern: string
  description?: string
}): Promise<Pattern> {
  const res = await fetch(`${API_BASE}/training/patterns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Errore aggiunta pattern')
  }
  const result = await res.json()
  return result.pattern
}

// Update pattern
async function updatePattern(
  patternId: string,
  data: { label?: PatternLabel; pattern?: string; description?: string }
): Promise<Pattern> {
  const res = await fetch(`${API_BASE}/training/patterns/${patternId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Errore aggiornamento pattern')
  }
  const result = await res.json()
  return result.pattern
}

// Delete pattern
async function deletePattern(patternId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/training/patterns/${patternId}`, {
    method: 'DELETE'
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Errore eliminazione pattern')
  }
}

// Preview pattern
async function previewPattern(
  pattern: string,
  label: string,
  text: string
): Promise<{ matches: PatternMatch[]; matches_count: number }> {
  const res = await fetch(`${API_BASE}/training/patterns/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pattern, label, text })
  })
  if (!res.ok) throw new Error('Errore preview pattern')
  return res.json()
}

export function usePatterns(source?: PatternSource, label?: PatternLabel) {
  const queryClient = useQueryClient()
  const [previewResult, setPreviewResult] = useState<PatternMatch[] | null>(null)

  // Query patterns
  const query = useQuery({
    queryKey: ['patterns', source, label],
    queryFn: () => fetchPatterns(source, label),
    staleTime: 30000
  })

  // Add mutation
  const addMutation = useMutation({
    mutationFn: addPattern,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patterns'] })
      queryClient.invalidateQueries({ queryKey: ['pattern-stats'] })
    }
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ patternId, data }: { patternId: string; data: Parameters<typeof updatePattern>[1] }) =>
      updatePattern(patternId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patterns'] })
    }
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deletePattern,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patterns'] })
      queryClient.invalidateQueries({ queryKey: ['pattern-stats'] })
    }
  })

  // Preview function
  const preview = useCallback(async (pattern: string, labelToUse: string, text: string) => {
    const result = await previewPattern(pattern, labelToUse, text)
    setPreviewResult(result.matches)
    return result.matches
  }, [])

  const clearPreview = useCallback(() => {
    setPreviewResult(null)
  }, [])

  const data = query.data

  return {
    // Data
    patterns: data?.patterns || [],
    total: data?.total || 0,
    bySource: data?.by_source || {},
    byLabel: data?.by_label || {},

    // Filtered patterns
    manualPatterns: (data?.patterns || []).filter(p => p.source === 'manual'),
    trainedPatterns: (data?.patterns || []).filter(p => p.source === 'trained'),
    basePatterns: (data?.patterns || []).filter(p => p.source === 'base'),

    // Loading states
    isLoading: query.isLoading,
    isAdding: addMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,

    // Errors
    error: query.error,
    addError: addMutation.error,
    updateError: updateMutation.error,
    deleteError: deleteMutation.error,

    // Preview
    previewResult,
    preview,
    clearPreview,

    // Actions
    refetch: query.refetch,
    add: addMutation.mutateAsync,
    update: (patternId: string, data: Parameters<typeof updatePattern>[1]) =>
      updateMutation.mutateAsync({ patternId, data }),
    delete: deleteMutation.mutateAsync
  }
}

// Hook per fetch valid labels
export function usePatternLabels() {
  const query = useQuery({
    queryKey: ['pattern-labels'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/training/patterns/labels`)
      if (!res.ok) throw new Error('Errore caricamento labels')
      const data = await res.json()
      return data.labels as PatternLabel[]
    },
    staleTime: Infinity // Labels don't change
  })

  return {
    labels: query.data || [],
    isLoading: query.isLoading
  }
}
