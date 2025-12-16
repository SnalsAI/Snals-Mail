/**
 * BenchmarkComparison - Confronto side-by-side spaCy vs BERT
 *
 * Mostra metriche comparative tra i due engine
 */

import { ArrowUp, ArrowDown, Minus, Trophy, Zap, Cpu, BarChart3 } from 'lucide-react'
import type { Benchmark, BenchmarkComparison as BenchmarkComparisonType } from './types'

interface BenchmarkComparisonProps {
  spacyBenchmark?: Benchmark | null
  bertBenchmark?: Benchmark | null
  comparison?: BenchmarkComparisonType | null  // Per confronto before/after
  mode?: 'engines' | 'versions'  // engines = spaCy vs BERT, versions = before vs after
}

export function BenchmarkComparison({
  spacyBenchmark,
  bertBenchmark,
  comparison,
  mode = 'engines'
}: BenchmarkComparisonProps) {
  // Se abbiamo comparison (before/after), usiamo quello
  if (comparison && mode === 'versions') {
    return <VersionComparison comparison={comparison} />
  }

  // Altrimenti confronto spaCy vs BERT
  if (!spacyBenchmark && !bertBenchmark) {
    return (
      <div className="bg-gray-50 rounded-lg p-6 text-center text-gray-500">
        <BarChart3 className="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p>Nessun benchmark disponibile</p>
        <p className="text-sm">Esegui un benchmark per confrontare le performance</p>
      </div>
    )
  }

  // Calcola delta
  const getDelta = (spacyVal: number, bertVal: number) => {
    return bertVal - spacyVal
  }

  const spacyF1 = spacyBenchmark?.metrics.overall.f1_score || 0
  const bertF1 = bertBenchmark?.metrics.overall.f1_score || 0
  const f1Delta = getDelta(spacyF1, bertF1)
  const winner = f1Delta > 0 ? 'bert' : f1Delta < 0 ? 'spacy' : 'tie'

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Confronto Engine</h3>
          {winner !== 'tie' && (
            <div className="flex items-center gap-1 bg-white/20 px-2 py-1 rounded-full text-sm">
              <Trophy className="w-4 h-4" />
              {winner === 'bert' ? 'BERT' : 'spaCy'} migliore di {Math.abs(f1Delta * 100).toFixed(1)}%
            </div>
          )}
        </div>
      </div>

      {/* Comparison table */}
      <div className="p-4">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="py-2 text-left text-sm font-medium text-gray-500">Metrica</th>
              <th className="py-2 text-center text-sm font-medium text-blue-600">
                <span className="inline-flex items-center gap-1">
                  <Zap className="w-4 h-4" />
                  spaCy
                </span>
              </th>
              <th className="py-2 text-center text-sm font-medium text-purple-600">
                <span className="inline-flex items-center gap-1">
                  <Cpu className="w-4 h-4" />
                  BERT
                </span>
              </th>
              <th className="py-2 text-center text-sm font-medium text-gray-500">Delta</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {/* F1 Score */}
            <MetricRow
              label="F1 Score"
              spacyValue={spacyBenchmark?.metrics.overall.f1_score}
              bertValue={bertBenchmark?.metrics.overall.f1_score}
              highlight
            />
            {/* Precision */}
            <MetricRow
              label="Precision"
              spacyValue={spacyBenchmark?.metrics.overall.precision}
              bertValue={bertBenchmark?.metrics.overall.precision}
            />
            {/* Recall */}
            <MetricRow
              label="Recall"
              spacyValue={spacyBenchmark?.metrics.overall.recall}
              bertValue={bertBenchmark?.metrics.overall.recall}
            />
          </tbody>
        </table>

        {/* Per-field breakdown */}
        {(spacyBenchmark || bertBenchmark) && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-3">Per Campo</h4>
            <div className="space-y-2">
              {getFieldsList(spacyBenchmark, bertBenchmark).map(field => (
                <FieldRow
                  key={field}
                  field={field}
                  spacyMetrics={spacyBenchmark?.metrics.by_field[field]}
                  bertMetrics={bertBenchmark?.metrics.by_field[field]}
                />
              ))}
            </div>
          </div>
        )}

        {/* Test info */}
        <div className="mt-4 pt-4 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
          <span>
            {spacyBenchmark && `spaCy: ${spacyBenchmark.email_count} email`}
            {spacyBenchmark && bertBenchmark && ' | '}
            {bertBenchmark && `BERT: ${bertBenchmark.email_count} email`}
          </span>
          <span>
            {spacyBenchmark && new Date(spacyBenchmark.timestamp).toLocaleDateString('it-IT')}
          </span>
        </div>
      </div>
    </div>
  )
}

// Helper per ottenere lista campi
function getFieldsList(spacy?: Benchmark | null, bert?: Benchmark | null): string[] {
  const fields = new Set<string>()
  if (spacy?.metrics.by_field) {
    Object.keys(spacy.metrics.by_field).forEach(f => fields.add(f))
  }
  if (bert?.metrics.by_field) {
    Object.keys(bert.metrics.by_field).forEach(f => fields.add(f))
  }
  return Array.from(fields).sort()
}

// Metric row component
interface MetricRowProps {
  label: string
  spacyValue?: number
  bertValue?: number
  highlight?: boolean
}

function MetricRow({ label, spacyValue, bertValue, highlight }: MetricRowProps) {
  const delta = (bertValue ?? 0) - (spacyValue ?? 0)
  const deltaColor = delta > 0 ? 'text-green-600' : delta < 0 ? 'text-red-600' : 'text-gray-400'

  return (
    <tr className={highlight ? 'bg-gray-50' : ''}>
      <td className={`py-2 text-sm ${highlight ? 'font-semibold text-gray-900' : 'text-gray-600'}`}>
        {label}
      </td>
      <td className="py-2 text-center">
        {spacyValue !== undefined ? (
          <span className={`font-mono ${highlight ? 'text-lg font-bold' : ''} text-blue-600`}>
            {(spacyValue * 100).toFixed(1)}%
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td className="py-2 text-center">
        {bertValue !== undefined ? (
          <span className={`font-mono ${highlight ? 'text-lg font-bold' : ''} text-purple-600`}>
            {(bertValue * 100).toFixed(1)}%
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td className="py-2 text-center">
        <span className={`inline-flex items-center gap-1 font-mono text-sm ${deltaColor}`}>
          {delta > 0 ? <ArrowUp className="w-3 h-3" /> : delta < 0 ? <ArrowDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
          {Math.abs(delta * 100).toFixed(1)}%
        </span>
      </td>
    </tr>
  )
}

// Field row component
interface FieldRowProps {
  field: string
  spacyMetrics?: { f1_score: number; precision: number; recall: number }
  bertMetrics?: { f1_score: number; precision: number; recall: number }
}

function FieldRow({ field, spacyMetrics, bertMetrics }: FieldRowProps) {
  const spacyF1 = spacyMetrics?.f1_score ?? 0
  const bertF1 = bertMetrics?.f1_score ?? 0
  const delta = bertF1 - spacyF1
  const winner = delta > 0.01 ? 'bert' : delta < -0.01 ? 'spacy' : null

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-32 text-gray-600 truncate" title={field}>{field}</span>
      <div className="flex-1 flex items-center gap-2">
        {/* spaCy bar */}
        <div className="w-24 bg-gray-100 rounded-full h-2">
          <div
            className={`h-2 rounded-full ${winner === 'spacy' ? 'bg-blue-500' : 'bg-blue-300'}`}
            style={{ width: `${spacyF1 * 100}%` }}
          />
        </div>
        <span className="w-12 text-right text-xs text-blue-600 font-mono">
          {spacyMetrics ? `${(spacyF1 * 100).toFixed(0)}%` : '-'}
        </span>

        {/* BERT bar */}
        <div className="w-24 bg-gray-100 rounded-full h-2">
          <div
            className={`h-2 rounded-full ${winner === 'bert' ? 'bg-purple-500' : 'bg-purple-300'}`}
            style={{ width: `${bertF1 * 100}%` }}
          />
        </div>
        <span className="w-12 text-right text-xs text-purple-600 font-mono">
          {bertMetrics ? `${(bertF1 * 100).toFixed(0)}%` : '-'}
        </span>

        {/* Delta indicator */}
        {Math.abs(delta) > 0.01 && (
          <span className={`text-xs ${delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
            {delta > 0 ? '+' : ''}{(delta * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  )
}

// Version comparison (before/after training)
function VersionComparison({ comparison }: { comparison: BenchmarkComparisonType }) {
  const improvement = comparison.improvement.f1_score
  const isImproved = improvement > 0

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header */}
      <div className={`px-4 py-3 ${isImproved ? 'bg-green-600' : 'bg-red-600'} text-white`}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Confronto Pre/Post Training</h3>
          <div className="flex items-center gap-1 bg-white/20 px-2 py-1 rounded-full text-sm">
            {isImproved ? (
              <>
                <ArrowUp className="w-4 h-4" />
                +{(improvement * 100).toFixed(1)}% F1
              </>
            ) : (
              <>
                <ArrowDown className="w-4 h-4" />
                {(improvement * 100).toFixed(1)}% F1
              </>
            )}
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="p-4">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-sm text-gray-500 mb-1">Precision</div>
            <DeltaValue
              before={comparison.before.metrics.overall.precision}
              after={comparison.after.metrics.overall.precision}
            />
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Recall</div>
            <DeltaValue
              before={comparison.before.metrics.overall.recall}
              after={comparison.after.metrics.overall.recall}
            />
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">F1 Score</div>
            <DeltaValue
              before={comparison.before.metrics.overall.f1_score}
              after={comparison.after.metrics.overall.f1_score}
              highlight
            />
          </div>
        </div>

        {/* Recommendation */}
        <div className={`mt-4 p-3 rounded-md ${isImproved ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          <div className="flex items-center gap-2">
            {isImproved ? (
              <>
                <Trophy className="w-5 h-5" />
                <span className="font-medium">Training migliorato! Mantieni la nuova versione.</span>
              </>
            ) : (
              <>
                <ArrowDown className="w-5 h-5" />
                <span className="font-medium">Performance peggiorate. Considera il rollback.</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Delta value component
function DeltaValue({ before, after, highlight }: { before: number; after: number; highlight?: boolean }) {
  const delta = after - before
  const isPositive = delta > 0

  return (
    <div className={highlight ? 'bg-gray-50 rounded-md p-2' : ''}>
      <div className="flex items-center justify-center gap-2">
        <span className="text-gray-400 text-sm">{(before * 100).toFixed(1)}%</span>
        <span className="text-gray-400">→</span>
        <span className={`font-bold ${highlight ? 'text-lg' : ''}`}>
          {(after * 100).toFixed(1)}%
        </span>
      </div>
      <div className={`text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
        {isPositive ? '+' : ''}{(delta * 100).toFixed(1)}%
      </div>
    </div>
  )
}

export default BenchmarkComparison
