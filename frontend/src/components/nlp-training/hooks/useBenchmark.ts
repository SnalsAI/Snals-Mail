/**
 * Hook per gestione benchmark NLP
 */

import { useState, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { Benchmark, BenchmarkComparison, BenchmarkEngine } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

// Fetch benchmark list
async function fetchBenchmarks(): Promise<Benchmark[]> {
  const res = await fetch(`${API_BASE}/training/benchmark/list`)
  if (!res.ok) throw new Error('Errore caricamento benchmark')
  const data = await res.json()
  return data.benchmarks || []
}

// Compare two benchmarks
async function compareBenchmarks(
  beforeName: string,
  afterName: string
): Promise<BenchmarkComparison> {
  const res = await fetch(`${API_BASE}/training/benchmark/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      before_name: beforeName,
      after_name: afterName
    })
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Errore confronto benchmark')
  }
  const data = await res.json()
  return data.comparison
}

export function useBenchmark() {
  const queryClient = useQueryClient()

  // State per confronto
  const [selectedBefore, setSelectedBefore] = useState<string>('')
  const [selectedAfter, setSelectedAfter] = useState<string>('')
  const [comparison, setComparison] = useState<BenchmarkComparison | null>(null)
  const [isComparing, setIsComparing] = useState(false)

  // Query benchmark list
  const query = useQuery({
    queryKey: ['benchmarks'],
    queryFn: fetchBenchmarks,
    staleTime: 30000
  })

  const _benchmarks = query.data || []

  // Filtra per engine
  const spacyBenchmarks = _benchmarks.filter(b => b.engine === 'spacy')
  const bertBenchmarks = _benchmarks.filter(b => b.engine === 'bert')
  const unifiedBenchmarks = _benchmarks.filter(b => b.engine === 'unified' || !b.engine)

  // Compare benchmarks
  const compare = useCallback(async () => {
    if (!selectedBefore || !selectedAfter) return

    setIsComparing(true)
    try {
      const result = await compareBenchmarks(selectedBefore, selectedAfter)
      setComparison(result)
    } catch (err) {
      console.error('Errore confronto:', err)
      throw err
    } finally {
      setIsComparing(false)
    }
  }, [selectedBefore, selectedAfter])

  // Clear comparison
  const clearComparison = useCallback(() => {
    setComparison(null)
    setSelectedBefore('')
    setSelectedAfter('')
  }, [])

  // Get latest benchmark by engine
  const getLatestByEngine = useCallback((engine: BenchmarkEngine) => {
    const filtered = _benchmarks.filter(b => b.engine === engine)
    if (filtered.length === 0) return null
    return filtered.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )[0]
  }, [_benchmarks])

  // Get benchmark delta (F1 improvement)
  const _getDelta = useCallback((before: Benchmark, after: Benchmark) => {
    const beforeF1 = before.metrics.overall.f1_score
    const afterF1 = after.metrics.overall.f1_score
    return {
      f1: afterF1 - beforeF1,
      precision: after.metrics.overall.precision - before.metrics.overall.precision,
      recall: after.metrics.overall.recall - before.metrics.overall.recall,
      improved: afterF1 > beforeF1
    }
  }, [])

  return {
    // Data
    benchmarks: _benchmarks,
    spacyBenchmarks,
    bertBenchmarks,
    unifiedBenchmarks,

    // Loading
    isLoading: query.isLoading,
    isComparing,

    // Error
    error: query.error,

    // Comparison state
    selectedBefore,
    selectedAfter,
    comparison,

    // Actions
    refetch: query.refetch,
    setSelectedBefore,
    setSelectedAfter,
    compare,
    clearComparison,

    // Helpers
    getLatestByEngine,
    getDelta: _getDelta,

    // Invalidate after new benchmark
    invalidate: () => queryClient.invalidateQueries({ queryKey: ['benchmarks'] })
  }
}

// Hook per confronto diretto spaCy vs BERT
export function useEngineComparison() {
  const { getLatestByEngine } = useBenchmark()

  const latestSpacy = getLatestByEngine('spacy')
  const latestBert = getLatestByEngine('bert')

  const canCompare = latestSpacy !== null && latestBert !== null

  const comparison = canCompare && latestSpacy && latestBert
    ? {
        spacy: latestSpacy,
        bert: latestBert,
        delta: {
          f1: latestBert.metrics.overall.f1_score - latestSpacy.metrics.overall.f1_score,
          precision: latestBert.metrics.overall.precision - latestSpacy.metrics.overall.precision,
          recall: latestBert.metrics.overall.recall - latestSpacy.metrics.overall.recall
        },
        winner: latestBert.metrics.overall.f1_score > latestSpacy.metrics.overall.f1_score
          ? 'bert' as const
          : 'spacy' as const
      }
    : null

  return {
    latestSpacy,
    latestBert,
    canCompare,
    comparison
  }
}
