/**
 * NLP Training Page - Pagina per training modelli NLP con ChatGPT
 *
 * Architettura:
 * - Workflow guidato step-by-step
 * - Panel paralleli spaCy vs BERT
 * - Review sample semplificato
 * - Pattern editor per pattern manuali
 * - Benchmark separati e confronto
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Brain,
  Mail,
  Calendar,
  FileText,
  Search,
  CheckCircle,
  XCircle,
  RefreshCw,
  Play,
  Loader2
} from 'lucide-react'
import toast from 'react-hot-toast'
import { emailsApi } from '../lib/api'

// Import components and hooks from nlp-training
import {
  WorkflowStepper,
  SimplifiedSampleCard,
  EnginePanel,
  PatternEditor,
  BenchmarkComparison,
  useAllStatus,
  useSamples,
  useAsyncJob,
  useBenchmark,
  useEngineComparison
} from '../components/nlp-training'
import type {
  WorkflowStep,
  TipoAnalisi,
  Email as NLPEmail,
  BertTrainConfig
} from '../components/nlp-training'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

export default function NLPTraining() {
  // ============================================
  // STATE
  // ============================================

  // Workflow
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('select')

  // Email selection
  const [emails, setEmails] = useState<NLPEmail[]>([])
  const [selectedEmails, setSelectedEmails] = useState<Set<number>>(new Set())
  const [searchTerm, setSearchTerm] = useState('')
  const [tipoAnalisi, setTipoAnalisi] = useState<TipoAnalisi>('interpello')
  const [isLoadingEmails, setIsLoadingEmails] = useState(false)

  // Pattern editor
  const [showPatternEditor, setShowPatternEditor] = useState(false)

  // ============================================
  // HOOKS
  // ============================================

  const { training, spacy, bert, patterns, refetchAll } = useAllStatus()
  const samples = useSamples(tipoAnalisi)
  const asyncJob = useAsyncJob({
    onComplete: (_result) => {
      toast.success('Operazione completata!')
      samples.refetch()
      refetchAll()
      // Avanza nel workflow
      if (asyncJob.job?.type === 'analyze_batch') {
        setCurrentStep('approve')
      } else if (asyncJob.job?.type === 'benchmark') {
        if (currentStep === 'benchmark-before') {
          setCurrentStep('apply')
        } else if (currentStep === 'benchmark-after') {
          setCurrentStep('compare')
        }
      }
    },
    onError: (error) => {
      toast.error(`Errore: ${error}`)
    }
  })

  const benchmark = useBenchmark()
  const engineComparison = useEngineComparison()

  // ============================================
  // EFFECTS
  // ============================================

  // Carica email all'avvio
  useEffect(() => {
    loadEmails()
  }, [tipoAnalisi])

  // ============================================
  // HANDLERS
  // ============================================

  const loadEmails = async () => {
    setIsLoadingEmails(true)
    try {
      const res = await emailsApi.getAll({ limit: 500 })
      // Filtra per categoria in base al tipo
      let filtered = Array.isArray(res.data) ? res.data : []
      if (tipoAnalisi === 'interpello') {
        filtered = filtered.filter((e: any) =>
          e.categoria?.toLowerCase().includes('interpell') ||
          e.sottocategoria?.toLowerCase().includes('interpell')
        )
      } else if (tipoAnalisi === 'calendario') {
        filtered = filtered.filter((e: any) =>
          e.categoria?.toLowerCase().includes('convoc') ||
          e.categoria?.toLowerCase().includes('riunion') ||
          e.sottocategoria?.toLowerCase().includes('convoc')
        )
      }
      setEmails(filtered as unknown as NLPEmail[])
    } catch (err) {
      console.error('Errore caricamento email:', err)
      toast.error('Errore caricamento email')
    } finally {
      setIsLoadingEmails(false)
    }
  }

  // Toggle email selection
  const toggleEmailSelection = useCallback((emailId: number) => {
    setSelectedEmails(prev => {
      const next = new Set(prev)
      if (next.has(emailId)) {
        next.delete(emailId)
      } else {
        next.add(emailId)
      }
      return next
    })
  }, [])

  const selectAllEmails = useCallback(() => {
    setSelectedEmails(new Set(filteredEmails.map(e => e.id)))
  }, [])

  const clearEmailSelection = useCallback(() => {
    setSelectedEmails(new Set())
  }, [])

  // Start analysis
  const handleStartAnalysis = async () => {
    if (selectedEmails.size === 0) {
      toast.error('Seleziona almeno una email')
      return
    }
    setCurrentStep('analyze')
    await asyncJob.startAnalyze(Array.from(selectedEmails), tipoAnalisi)
  }

  // Apply spaCy training
  const handleApplySpacyTraining = async () => {
    try {
      const res = await fetch(`${API_BASE}/training/spacy/apply`, { method: 'POST' })
      if (!res.ok) throw new Error('Errore applicazione training')
      const data = await res.json()
      toast.success(`Training applicato: ${data.patterns_added} nuovi pattern`)
      refetchAll()
    } catch (err: any) {
      toast.error(err.message || 'Errore')
    }
  }

  // Rollback spaCy
  const handleRollbackSpacy = async () => {
    if (!confirm('Ripristinare la versione precedente?')) return
    try {
      const res = await fetch(`${API_BASE}/training/spacy/rollback`, { method: 'POST' })
      if (!res.ok) throw new Error('Errore rollback')
      toast.success('Rollback completato')
      refetchAll()
    } catch (err: any) {
      toast.error(err.message || 'Errore')
    }
  }

  // Run spaCy benchmark
  const handleSpacyBenchmark = async () => {
    if (selectedEmails.size === 0) {
      toast.error('Seleziona almeno una email per il benchmark')
      return
    }
    try {
      const res = await fetch(`${API_BASE}/training/spacy/benchmark`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_ids: Array.from(selectedEmails),
          tipo: tipoAnalisi,
          name: `pre_${Date.now()}`
        })
      })
      if (!res.ok) throw new Error('Errore benchmark')
      const data = await res.json()
      toast.success(`Benchmark spaCy completato: F1 ${(data.benchmark.metrics.overall.f1_score * 100).toFixed(1)}%`)
      benchmark.invalidate()
    } catch (err: any) {
      toast.error(err.message || 'Errore')
    }
  }

  // BERT training
  const handleStartBertTraining = async (config: BertTrainConfig) => {
    try {
      await asyncJob.startBertTraining(config)
      toast.success('Training BERT avviato')
    } catch (err: any) {
      toast.error(err.message || 'Errore avvio training BERT')
    }
  }

  // Rollback BERT
  const handleRollbackBert = async () => {
    const models = bert.status?.available_models || []
    if (models.length < 2) {
      toast.error('Nessuna versione precedente disponibile')
      return
    }
    const prevModel = models[1] // Second model is previous
    if (!confirm(`Ripristinare ${prevModel.version_id}?`)) return
    try {
      const res = await fetch(`${API_BASE}/training/bert/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version_id: prevModel.version_id })
      })
      if (!res.ok) throw new Error('Errore rollback')
      toast.success('Rollback BERT completato')
      refetchAll()
    } catch (err: any) {
      toast.error(err.message || 'Errore')
    }
  }

  // BERT benchmark
  const handleBertBenchmark = async () => {
    if (selectedEmails.size === 0) {
      toast.error('Seleziona almeno una email per il benchmark')
      return
    }
    try {
      const res = await fetch(`${API_BASE}/training/bert/benchmark`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_ids: Array.from(selectedEmails),
          tipo: tipoAnalisi,
          name: `bert_${Date.now()}`
        })
      })
      if (!res.ok) throw new Error('Errore benchmark')
      const data = await res.json()
      toast.success(`Benchmark BERT completato: F1 ${(data.benchmark.metrics.overall.f1_score * 100).toFixed(1)}%`)
      benchmark.invalidate()
    } catch (err: any) {
      toast.error(err.message || 'Errore')
    }
  }

  // Approve sample
  const handleApproveSample = async (sampleId: string) => {
    try {
      await samples.approve(sampleId)
      toast.success('Sample approvato')
    } catch (err: any) {
      toast.error(err.message || 'Errore approvazione')
    }
  }

  // Reject sample
  const handleRejectSample = async (sampleId: string) => {
    if (!confirm('Eliminare questo sample?')) return
    try {
      await samples.delete(sampleId)
      toast.success('Sample eliminato')
    } catch (err: any) {
      toast.error(err.message || 'Errore eliminazione')
    }
  }

  // Approve all pending
  const handleApproveAllPending = async () => {
    if (samples.pendingSamples.length === 0) return
    if (!confirm(`Approvare ${samples.pendingSamples.length} sample?`)) return
    samples.selectAllPending()
    const result = await samples.approveSelected()
    toast.success(`Approvati ${result.success} sample`)
  }

  // ============================================
  // COMPUTED
  // ============================================

  // Filtro email per ricerca
  const filteredEmails = useMemo(() => {
    if (!searchTerm) return emails
    const term = searchTerm.toLowerCase()
    return emails.filter(e =>
      e.oggetto?.toLowerCase().includes(term) ||
      e.mittente_email?.toLowerCase().includes(term)
    )
  }, [emails, searchTerm])

  // Validazione step
  const validation = useMemo(() => ({
    canProceedToAnalyze: selectedEmails.size > 0 && (training.status?.openai_available || false),
    canProceedToApprove: samples.samples.length > 0,
    canApplyTraining: samples.approvedSamples.length > 0,
    canBenchmark: selectedEmails.size > 0 && samples.approvedSamples.length > 0
  }), [selectedEmails.size, training.status, samples.samples.length, samples.approvedSamples.length])

  // Fetch training history for spaCy
  const [spacyHistory, setSpacyHistory] = useState<any[]>([])
  useEffect(() => {
    fetch(`${API_BASE}/training/spacy/history?limit=5`)
      .then(r => r.json())
      .then(d => setSpacyHistory(d.history || []))
      .catch(() => {})
  }, [spacy.status])

  // ============================================
  // RENDER
  // ============================================

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Brain className="w-7 h-7 text-primary-600" />
            NLP Training con ChatGPT
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Addestra i modelli NLP usando ChatGPT come "teacher"
          </p>
        </div>
        <button
          onClick={refetchAll}
          className="p-2 text-gray-400 hover:text-gray-600 rounded-md"
          title="Aggiorna"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* ChatGPT Status */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2">
            {training.status?.openai_available ? (
              <CheckCircle className="w-5 h-5 text-green-500" />
            ) : (
              <XCircle className="w-5 h-5 text-red-500" />
            )}
            <span className="font-medium">ChatGPT</span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {training.status?.openai_available ? 'Disponibile' : 'Non disponibile'}
          </p>
        </div>

        {/* Total Samples */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-gray-900">
            {training.status?.statistics?.total_samples || 0}
          </div>
          <p className="text-sm text-gray-500">Sample totali</p>
        </div>

        {/* Approved Samples */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-green-600">
            {training.status?.statistics?.approved_samples || 0}
          </div>
          <p className="text-sm text-gray-500">Approvati</p>
        </div>

        {/* Patterns */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-blue-600">
            {patterns.stats?.total || 0}
          </div>
          <p className="text-sm text-gray-500">Pattern totali</p>
        </div>
      </div>

      {/* Workflow Stepper */}
      <WorkflowStepper
        currentStep={currentStep}
        onStepClick={setCurrentStep}
        validation={validation}
        selectedEmailCount={selectedEmails.size}
        approvedSampleCount={samples.approvedSamples.length}
      />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Email Selection & Samples */}
        <div className="space-y-6">
          {/* Email Selection */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-4 py-3 border-b border-gray-200">
              <h3 className="font-semibold text-gray-900">Selezione Email</h3>
            </div>
            <div className="p-4">
              {/* Tipo analisi */}
              <div className="flex gap-2 mb-4">
                {(['interpello', 'calendario', 'generico'] as TipoAnalisi[]).map(tipo => (
                  <button
                    key={tipo}
                    onClick={() => {
                      setTipoAnalisi(tipo)
                      setSelectedEmails(new Set())
                    }}
                    className={`px-3 py-1.5 text-sm font-medium rounded-md ${
                      tipoAnalisi === tipo
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {tipo === 'interpello' && <Mail className="w-4 h-4 inline mr-1" />}
                    {tipo === 'calendario' && <Calendar className="w-4 h-4 inline mr-1" />}
                    {tipo === 'generico' && <FileText className="w-4 h-4 inline mr-1" />}
                    {tipo.charAt(0).toUpperCase() + tipo.slice(1)}
                  </button>
                ))}
              </div>

              {/* Search */}
              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Cerca email..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md"
                />
              </div>

              {/* Quick actions */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex gap-2">
                  <button
                    onClick={selectAllEmails}
                    className="text-sm text-primary-600 hover:text-primary-800"
                  >
                    Seleziona tutto ({filteredEmails.length})
                  </button>
                  <button
                    onClick={clearEmailSelection}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    Deseleziona
                  </button>
                </div>
                <span className="text-sm text-gray-500">
                  {selectedEmails.size} selezionate
                </span>
              </div>

              {/* Email list */}
              <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-md">
                {isLoadingEmails ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                  </div>
                ) : filteredEmails.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    Nessuna email trovata
                  </div>
                ) : (
                  filteredEmails.slice(0, 50).map(email => (
                    <label
                      key={email.id}
                      className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-0"
                    >
                      <input
                        type="checkbox"
                        checked={selectedEmails.has(email.id)}
                        onChange={() => toggleEmailSelection(email.id)}
                        className="w-4 h-4 text-primary-600 rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {email.oggetto || 'Senza oggetto'}
                        </div>
                        <div className="text-xs text-gray-500">
                          #{email.id}
                        </div>
                      </div>
                    </label>
                  ))
                )}
              </div>

              {/* Analyze button */}
              <div className="mt-4">
                <button
                  onClick={handleStartAnalysis}
                  disabled={selectedEmails.size === 0 || asyncJob.isRunning}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md disabled:opacity-50"
                >
                  {asyncJob.isRunning ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  Analizza con ChatGPT
                </button>
              </div>

              {/* Job progress */}
              {asyncJob.isRunning && (
                <div className="mt-4 bg-blue-50 rounded-md p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                    <span className="text-sm font-medium text-blue-900">
                      {asyncJob.message || 'Elaborazione...'}
                    </span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${asyncJob.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Pending Samples */}
          {samples.pendingSamples.length > 0 && (
            <div className="bg-white rounded-lg shadow">
              <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">
                  Sample da Approvare ({samples.pendingSamples.length})
                </h3>
                <button
                  onClick={handleApproveAllPending}
                  className="text-sm text-green-600 hover:text-green-800"
                >
                  Approva tutti
                </button>
              </div>
              <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
                {samples.pendingSamples.map(sample => (
                  <SimplifiedSampleCard
                    key={sample.id}
                    sample={sample}
                    onApprove={handleApproveSample}
                    onReject={handleRejectSample}
                    isApproving={samples.isApproving}
                    isRejecting={samples.isDeleting}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column - Engine Panels */}
        <div className="space-y-6">
          {/* spaCy Panel */}
          <EnginePanel
            engine="spacy"
            status={spacy.status || null}
            isLoading={spacy.isLoading}
            onApplyTraining={handleApplySpacyTraining}
            onRollback={handleRollbackSpacy}
            onBenchmark={handleSpacyBenchmark}
            onOpenPatternEditor={() => setShowPatternEditor(true)}
            trainingHistory={spacyHistory}
            latestBenchmark={engineComparison.latestSpacy}
          />

          {/* BERT Panel */}
          <EnginePanel
            engine="bert"
            status={bert.status || null}
            isLoading={bert.isLoading}
            onStartBertTraining={handleStartBertTraining}
            onRollback={handleRollbackBert}
            onBenchmark={handleBertBenchmark}
            latestBenchmark={engineComparison.latestBert}
            isTraining={asyncJob.job?.type === 'bert_training' && asyncJob.isRunning}
            trainingProgress={asyncJob.progress}
            trainingMessage={asyncJob.message}
          />

          {/* Engine Comparison */}
          {engineComparison.canCompare && (
            <BenchmarkComparison
              spacyBenchmark={engineComparison.latestSpacy}
              bertBenchmark={engineComparison.latestBert}
              mode="engines"
            />
          )}
        </div>
      </div>

      {/* Pattern Editor Modal */}
      <PatternEditor
        isOpen={showPatternEditor}
        onClose={() => setShowPatternEditor(false)}
      />
    </div>
  )
}
