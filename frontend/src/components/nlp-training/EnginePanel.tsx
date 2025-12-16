/**
 * EnginePanel - Panel riusabile per spaCy e BERT
 *
 * Mostra stato, controlli training, benchmark e storico versioni
 */

import { useState } from 'react'
import {
  Play,
  RotateCcw,
  BarChart3,
  History,
  Settings,
  CheckCircle,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Zap
} from 'lucide-react'
import type { SpacyStatus, BertStatus, BertTrainConfig, TrainingVersion, Benchmark } from './types'
import { DEFAULT_BERT_CONFIG } from './types'

interface EnginePanelProps {
  engine: 'spacy' | 'bert'
  status: SpacyStatus | BertStatus | null
  isLoading?: boolean
  onApplyTraining?: () => Promise<void>
  onRollback?: (versionId?: string) => Promise<void>
  onBenchmark?: () => Promise<void>
  onOpenPatternEditor?: () => void  // Solo per spaCy
  onStartBertTraining?: (config: BertTrainConfig) => Promise<void>  // Solo per BERT
  trainingHistory?: TrainingVersion[]
  latestBenchmark?: Benchmark | null
  isTraining?: boolean
  trainingProgress?: number
  trainingMessage?: string
}

export function EnginePanel({
  engine,
  status,
  isLoading,
  onApplyTraining,
  onRollback,
  onBenchmark,
  onOpenPatternEditor,
  onStartBertTraining,
  trainingHistory = [],
  latestBenchmark,
  isTraining,
  trainingProgress,
  trainingMessage
}: EnginePanelProps) {
  const [showHistory, setShowHistory] = useState(false)
  const [showConfig, setShowConfig] = useState(false)
  const [bertConfig, setBertConfig] = useState<BertTrainConfig>(DEFAULT_BERT_CONFIG)
  const [isApplying, setIsApplying] = useState(false)
  const [isRollingBack, setIsRollingBack] = useState(false)
  const [isBenchmarking, setIsBenchmarking] = useState(false)

  const isSpacy = engine === 'spacy'
  const isBert = engine === 'bert'

  // Type guards
  const spacyStatus = isSpacy ? (status as SpacyStatus) : null
  const bertStatus = isBert ? (status as BertStatus) : null

  // Status indicators
  const isAvailable = status?.is_available ?? false
  // isTrained calculated but stored for potential future use
  void (isBert ? bertStatus?.is_trained : (spacyStatus?.patterns_count ?? 0) > 0)

  // Handler wrapper per gestire loading state
  const handleApply = async () => {
    if (!onApplyTraining) return
    setIsApplying(true)
    try {
      await onApplyTraining()
    } finally {
      setIsApplying(false)
    }
  }

  const handleRollback = async () => {
    if (!onRollback) return
    setIsRollingBack(true)
    try {
      await onRollback()
    } finally {
      setIsRollingBack(false)
    }
  }

  const handleBenchmark = async () => {
    if (!onBenchmark) return
    setIsBenchmarking(true)
    try {
      await onBenchmark()
    } finally {
      setIsBenchmarking(false)
    }
  }

  const handleStartBertTraining = async () => {
    if (!onStartBertTraining) return
    await onStartBertTraining(bertConfig)
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header */}
      <div className={`px-4 py-3 ${isSpacy ? 'bg-blue-600' : 'bg-purple-600'} text-white`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isSpacy ? <Zap className="w-5 h-5" /> : <Cpu className="w-5 h-5" />}
            <h3 className="font-semibold text-lg">
              {isSpacy ? 'spaCy' : 'BERT'}
            </h3>
            <span className="text-sm opacity-80">
              {isSpacy ? 'Pattern-based' : 'Machine Learning'}
            </span>
          </div>
          {/* Status indicator */}
          <div className="flex items-center gap-2">
            {isAvailable ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-white/20">
                <CheckCircle className="w-3 h-3" />
                Disponibile
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-red-500/50">
                <XCircle className="w-3 h-3" />
                Non disponibile
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="p-8 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      )}

      {/* Content */}
      {!isLoading && (
        <div className="p-4 space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-2 gap-3">
            {isSpacy && spacyStatus && (
              <>
                <div className="bg-gray-50 rounded-md p-3">
                  <div className="text-2xl font-bold text-gray-900">
                    {spacyStatus.patterns_count}
                  </div>
                  <div className="text-xs text-gray-500">Pattern totali</div>
                </div>
                <div className="bg-gray-50 rounded-md p-3">
                  <div className="text-sm font-medium text-gray-900 truncate">
                    {spacyStatus.current_version || 'N/A'}
                  </div>
                  <div className="text-xs text-gray-500">Versione</div>
                </div>
              </>
            )}
            {isBert && bertStatus && (
              <>
                <div className="bg-gray-50 rounded-md p-3">
                  <div className="text-2xl font-bold text-gray-900">
                    {bertStatus.is_trained ? (
                      `${((bertStatus.current_model?.metrics?.f1 || 0) * 100).toFixed(1)}%`
                    ) : (
                      'N/A'
                    )}
                  </div>
                  <div className="text-xs text-gray-500">F1 Score</div>
                </div>
                <div className="bg-gray-50 rounded-md p-3">
                  <div className="text-sm font-medium text-gray-900">
                    {bertStatus.is_trained ? 'Fine-tuned' : 'Base'}
                  </div>
                  <div className="text-xs text-gray-500">
                    {bertStatus.models_count} modelli
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Latest benchmark */}
          {latestBenchmark && (
            <div className="bg-blue-50 rounded-md p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-blue-900">Ultimo Benchmark</span>
                <span className="text-xs text-blue-600">
                  {latestBenchmark.email_count} email
                </span>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-lg font-bold text-blue-900">
                    {(latestBenchmark.metrics.overall.precision * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-blue-600">Precision</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-blue-900">
                    {(latestBenchmark.metrics.overall.recall * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-blue-600">Recall</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-blue-900">
                    {(latestBenchmark.metrics.overall.f1_score * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-blue-600">F1</div>
                </div>
              </div>
            </div>
          )}

          {/* Training progress */}
          {isTraining && (
            <div className="bg-yellow-50 rounded-md p-3">
              <div className="flex items-center gap-2 mb-2">
                <Loader2 className="w-4 h-4 animate-spin text-yellow-600" />
                <span className="text-sm font-medium text-yellow-800">Training in corso...</span>
              </div>
              <div className="w-full bg-yellow-200 rounded-full h-2">
                <div
                  className="bg-yellow-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${trainingProgress || 0}%` }}
                />
              </div>
              {trainingMessage && (
                <div className="mt-1 text-xs text-yellow-700">{trainingMessage}</div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {/* Apply Training (spaCy) */}
            {isSpacy && onApplyTraining && (
              <button
                onClick={handleApply}
                disabled={isApplying || isTraining}
                className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50"
              >
                {isApplying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Applica Training
              </button>
            )}

            {/* Start Training (BERT) */}
            {isBert && onStartBertTraining && (
              <button
                onClick={handleStartBertTraining}
                disabled={isTraining}
                className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md disabled:opacity-50"
              >
                {isTraining ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Avvia Fine-tuning
              </button>
            )}

            {/* Benchmark */}
            {onBenchmark && (
              <button
                onClick={handleBenchmark}
                disabled={isBenchmarking || isTraining}
                className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md disabled:opacity-50"
              >
                {isBenchmarking ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                Benchmark
              </button>
            )}

            {/* Pattern Editor (spaCy only) */}
            {isSpacy && onOpenPatternEditor && (
              <button
                onClick={onOpenPatternEditor}
                className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
              >
                <Settings className="w-4 h-4" />
                Pattern
              </button>
            )}

            {/* Rollback */}
            {onRollback && (spacyStatus?.backup_available || (bertStatus?.models_count ?? 0) > 1) && (
              <button
                onClick={handleRollback}
                disabled={isRollingBack || isTraining}
                className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-orange-700 bg-orange-100 hover:bg-orange-200 rounded-md disabled:opacity-50"
              >
                {isRollingBack ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                Rollback
              </button>
            )}
          </div>

          {/* BERT Config (collapsible) */}
          {isBert && (
            <div className="border-t border-gray-100 pt-3">
              <button
                onClick={() => setShowConfig(!showConfig)}
                className="flex items-center justify-between w-full text-sm text-gray-600 hover:text-gray-900"
              >
                <span className="flex items-center gap-1">
                  <Settings className="w-4 h-4" />
                  Configurazione Training
                </span>
                {showConfig ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {showConfig && (
                <div className="mt-3 grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Epochs</label>
                    <input
                      type="number"
                      value={bertConfig.epochs}
                      onChange={e => setBertConfig(c => ({ ...c, epochs: parseInt(e.target.value) || 3 }))}
                      min={1}
                      max={10}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Batch Size</label>
                    <input
                      type="number"
                      value={bertConfig.batch_size}
                      onChange={e => setBertConfig(c => ({ ...c, batch_size: parseInt(e.target.value) || 8 }))}
                      min={1}
                      max={32}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Learning Rate</label>
                    <input
                      type="number"
                      value={bertConfig.learning_rate}
                      onChange={e => setBertConfig(c => ({ ...c, learning_rate: parseFloat(e.target.value) || 0.00002 }))}
                      step={0.00001}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* History (collapsible) */}
          {trainingHistory.length > 0 && (
            <div className="border-t border-gray-100 pt-3">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="flex items-center justify-between w-full text-sm text-gray-600 hover:text-gray-900"
              >
                <span className="flex items-center gap-1">
                  <History className="w-4 h-4" />
                  Storico ({trainingHistory.length})
                </span>
                {showHistory ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {showHistory && (
                <div className="mt-2 max-h-40 overflow-y-auto space-y-2">
                  {trainingHistory.slice(0, 5).map((v, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs bg-gray-50 rounded px-2 py-1">
                      <span className="font-mono">{v.version_id}</span>
                      <span className="text-gray-500">{v.total_patterns} pattern</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default EnginePanel
