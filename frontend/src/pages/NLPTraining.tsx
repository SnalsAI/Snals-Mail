import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Brain,
  CheckCircle,
  AlertCircle,
  Play,
  Trash2,
  Download,
  Check,
  X,
  RefreshCw,
  Search,
  Mail,
  Database,
  BarChart3,
  Zap,
  TrendingUp,
  TrendingDown,
  Clock,
  Target,
  Layers,
  ArrowRight,
  AlertTriangle,
  CheckSquare,
  History,
  Cpu,
  Settings,
  Activity
} from 'lucide-react'
import { emailsApi } from '../lib/api'

interface Email {
  id: number
  oggetto: string
  mittente: string
  categoria: string
  data_ricezione: string
}

interface TrainingSample {
  id: string
  email_id: number
  timestamp: string
  type: string
  text: string
  openai_extraction: Record<string, any>
  entities: Array<{ start: number; end: number; label: string; text?: string }>
  approved: boolean
  corrections?: Record<string, any>
}

interface TrainingStatus {
  openai_available: boolean
  statistics: {
    total_samples: number
    approved_samples: number
    pending_approval: number
    entity_counts: Record<string, number>
    by_type: Record<string, number>
  }
}

interface Benchmark {
  name: string
  timestamp: string
  tipo: string
  email_count: number
  with_ground_truth: number
  without_ground_truth?: number
  testable_percentage?: number
  warning?: string
  emails_without_gt_list?: { id: number; oggetto: string }[]
  metrics: {
    avg_precision: number
    avg_recall: number
    avg_f1_score: number
  }
}

interface BenchmarkComparison {
  before: {
    name: string
    timestamp: string
    metrics: {
      avg_precision: number
      avg_recall: number
      avg_f1_score: number
    }
  }
  after: {
    name: string
    timestamp: string
    metrics: {
      avg_precision: number
      avg_recall: number
      avg_f1_score: number
    }
  }
  delta: {
    avg_precision: number
    avg_recall: number
    avg_f1_score: number
  }
  by_field: Record<string, { before_f1: number; after_f1: number; delta: number }>
  improved: boolean
}

// BERT ML Training Types
interface BERTModelInfo {
  version_id: string
  path: string | null
  timestamp: string | null
  metrics: {
    f1: number
    precision: number
    recall: number
    train_loss?: number
    samples?: number
  } | null
  is_base?: boolean
  is_current?: boolean
}

interface BERTStatus {
  current_model: BERTModelInfo
  available_models: BERTModelInfo[]
  is_trained: boolean
  models_count: number
}

interface BERTTrainConfig {
  epochs: number
  batch_size: number
  learning_rate: number
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001'

type WorkflowStep = 'select' | 'analyze' | 'approve' | 'benchmark-before' | 'apply' | 'benchmark-after' | 'compare'

export default function NLPTraining() {
  const [status, setStatus] = useState<TrainingStatus | null>(null)
  const [emails, setEmails] = useState<Email[]>([])
  const [samples, setSamples] = useState<TrainingSample[]>([])
  const [selectedEmails, setSelectedEmails] = useState<Set<number>>(new Set())
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedSample, setExpandedSample] = useState<string | null>(null)
  const [tipoAnalisi, setTipoAnalisi] = useState<'interpello' | 'calendario' | 'generico'>('generico')
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null)

  // Benchmark state
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([])
  const [benchmarkBefore, setBenchmarkBefore] = useState<string>('')
  const [benchmarkAfter, setBenchmarkAfter] = useState<string>('')
  const [comparison, setComparison] = useState<BenchmarkComparison | null>(null)
  const [applyingTraining, setApplyingTraining] = useState(false)
  const [backupInfo, setBackupInfo] = useState<{ backup_available: boolean; timestamp?: string; version_id?: string; pattern_count?: number } | null>(null)
  const [rollingBack, setRollingBack] = useState(false)
  const [trainingHistory, setTrainingHistory] = useState<{
    version_id: string
    timestamp: string
    patterns_added?: number
    total_patterns?: number
    status: string
    restored_to?: string
  }[]>([])
  const [currentVersion, setCurrentVersion] = useState<{ version_id: string; total_patterns: number } | null>(null)

  // BERT ML Training state
  const [bertStatus, setBertStatus] = useState<BERTStatus | null>(null)
  const [bertTrainConfig, setBertTrainConfig] = useState<BERTTrainConfig>({ epochs: 3, batch_size: 8, learning_rate: 0.00002 })
  const [bertTrainJob, setBertTrainJob] = useState<{ job_id: string; status: string; progress: number; message: string; result?: any } | null>(null)
  const [showBertConfig, setShowBertConfig] = useState(false)
  const [activeTab, setActiveTab] = useState<'spacy' | 'bert'>('spacy')

  // Workflow state
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('select')
  const [showWorkflowGuide, setShowWorkflowGuide] = useState(true)

  // Async job state
  interface JobStatus {
    job_id: string
    type: 'analyze_batch' | 'benchmark'
    status: 'running' | 'completed' | 'failed'
    progress: number
    message: string
    result?: any
    error?: string
  }
  const [activeJob, setActiveJob] = useState<JobStatus | null>(null)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Fetch functions
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/training/status`)
      const data = await res.json()
      setStatus(data)
    } catch (e) {
      console.error('Error fetching status:', e)
    }
  }, [])

  const fetchEmails = useCallback(async () => {
    try {
      const response = await emailsApi.getAll({ limit: 100 })
      // La risposta ha struttura {emails: [...], total: number, ...}
      const data = response.data as { emails?: Email[] } | Email[]
      if (Array.isArray(data)) {
        setEmails(data)
      } else if (data?.emails) {
        setEmails(data.emails)
      } else {
        setEmails([])
      }
    } catch (e) {
      console.error('Error fetching emails:', e)
    }
  }, [])

  const fetchSamples = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/training/samples`)
      const data = await res.json()
      setSamples(data.samples || [])
    } catch (e) {
      console.error('Error fetching samples:', e)
    }
  }, [])

  const fetchBenchmarks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/training/benchmark/list?limit=20`)
      const data = await res.json()
      setBenchmarks(data.benchmarks || [])
    } catch (e) {
      console.error('Error fetching benchmarks:', e)
    }
  }, [])

  // Fetch BERT status
  const fetchBertStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/training/bert/status`)
      if (res.ok) {
        const data = await res.json()
        setBertStatus(data)
      }
    } catch (e) {
      console.error('Error fetching BERT status:', e)
    }
  }, [])

  // Stop polling helper
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
  }, [])

  // Poll job status
  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      const res = await fetch(`${API_BASE}/training/job/${jobId}`)

      // Job non trovato - resetta stato
      if (!res.ok) {
        stopPolling()
        setActiveJob(null)
        return
      }

      const data = await res.json()

      setActiveJob({
        job_id: jobId,
        type: data.type,
        status: data.status,
        progress: data.progress || 0,
        message: data.message || '',
        result: data.result,
        error: data.error
      })

      // Job completato o fallito - ferma polling
      if (data.status === 'completed' || data.status === 'failed') {
        stopPolling()

        if (data.status === 'completed') {
          if (data.type === 'analyze_batch') {
            setMessage({ type: 'success', text: data.message || 'Analisi completata!' })
            fetchSamples()
            fetchStatus()
            setCurrentStep('approve')
          } else if (data.type === 'benchmark') {
            setMessage({ type: 'success', text: data.message || 'Benchmark completato!' })
            fetchBenchmarks()
            // Avanza allo step successivo
            if (currentStep === 'benchmark-before' || currentStep === 'approve') {
              setCurrentStep('apply')
            } else if (currentStep === 'benchmark-after' || currentStep === 'apply') {
              setCurrentStep('compare')
            }
          }
        } else {
          setMessage({ type: 'error', text: data.error || 'Errore nel job' })
        }

        // Clear job dopo un po'
        setTimeout(() => setActiveJob(null), 3000)
      }
    } catch (e) {
      console.error('Error polling job:', e)
      // Se polling fallisce, resetta stato per sbloccare UI
      stopPolling()
      setActiveJob(null)
    }
  }, [stopPolling, fetchSamples, fetchStatus, fetchBenchmarks, currentStep])

  // Start polling
  const startPolling = useCallback((jobId: string) => {
    // Stop any existing polling first
    stopPolling()

    // Poll immediately
    pollJobStatus(jobId)

    // Then poll every 2 seconds
    const interval = setInterval(() => pollJobStatus(jobId), 2000)
    pollingIntervalRef.current = interval

    // Cleanup after 10 minutes max
    setTimeout(() => {
      if (pollingIntervalRef.current === interval) {
        stopPolling()
        setActiveJob(null)
      }
    }, 600000)
  }, [pollJobStatus, stopPolling])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [stopPolling])

  useEffect(() => {
    fetchStatus()
    fetchEmails()
    fetchSamples()
    fetchBenchmarks()
    fetchBackupInfo()
    fetchTrainingHistory()
    fetchCurrentVersion()
    fetchBertStatus()
  }, [fetchStatus, fetchEmails, fetchSamples, fetchBenchmarks, fetchBertStatus])

  // Filter emails by tipo and search term
  const filteredEmails = emails.filter(email => {
    // Prima filtra per tipo analisi
    if (tipoAnalisi === 'interpello') {
      // Mostra solo email che potrebbero essere interpelli
      const isInterpello =
        email.categoria === 'interpello' ||
        email.oggetto?.toLowerCase().includes('interpello') ||
        email.oggetto?.toLowerCase().includes('disponibilit') ||
        email.oggetto?.toLowerCase().includes('supplenza') ||
        email.oggetto?.toLowerCase().includes('mad')
      if (!isInterpello) return false
    } else if (tipoAnalisi === 'calendario') {
      // Escludi ricevute di lettura e PEC
      const isRicevuta =
        email.categoria === 'ricevuta_pec' ||
        email.oggetto?.toLowerCase().startsWith('read:') ||
        email.oggetto?.toLowerCase().startsWith('letto:') ||
        email.oggetto?.toLowerCase().includes('conferma di lettura') ||
        email.oggetto?.toLowerCase().includes('ricevuta di lettura')
      if (isRicevuta) return false

      // Escludi rinvii, integrazioni e inoltri (non sono eventi originali)
      const oggettoLower = email.oggetto?.toLowerCase() || ''
      const isNonEvento =
        oggettoLower.includes('rinvio') ||
        oggettoLower.includes('rinviata') ||
        oggettoLower.includes('annullat') ||
        oggettoLower.startsWith('integrazione') ||
        oggettoLower.startsWith('i:') ||  // Inoltro
        oggettoLower.startsWith('fwd:') ||
        oggettoLower.startsWith('fw:') ||
        (oggettoLower.includes('inoltro') && !oggettoLower.includes('convocazione'))
      if (isNonEvento) return false

      // Mostra solo email che potrebbero essere eventi calendario
      const isCalendario =
        email.categoria === 'convocazione_scuola' ||
        oggettoLower.includes('convocazione') ||
        oggettoLower.includes('riunione') ||
        oggettoLower.includes('assemblea') ||
        oggettoLower.includes('incontro') ||
        oggettoLower.includes('collegio')
      if (!isCalendario) return false
    }
    // 'generico' mostra tutte le email

    // Poi filtra per ricerca
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      email.oggetto?.toLowerCase().includes(term) ||
      email.mittente?.toLowerCase().includes(term) ||
      email.categoria?.toLowerCase().includes(term)
    )
  })

  // Toggle email selection
  const toggleEmail = (id: number) => {
    const newSelected = new Set(selectedEmails)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedEmails(newSelected)
  }

  // Analyze selected emails with ChatGPT (ASYNC)
  const analyzeEmails = async () => {
    if (selectedEmails.size === 0) {
      setMessage({ type: 'warning', text: 'Seleziona almeno una email dalla lista' })
      return
    }
    if (activeJob) {
      setMessage({ type: 'warning', text: 'Un job è già in esecuzione. Attendi il completamento.' })
      return
    }

    setMessage(null)

    try {
      // Avvia job asincrono
      const res = await fetch(`${API_BASE}/training/analyze/async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_ids: Array.from(selectedEmails),
          tipo: tipoAnalisi
        })
      })

      const data = await res.json()

      if (data.success && data.job_id) {
        setMessage({
          type: 'success',
          text: `Analisi avviata per ${selectedEmails.size} email. Monitoraggio in corso...`
        })
        // NON cancellare la selezione - serve per benchmark DOPO
        // setSelectedEmails(new Set())

        // Inizia polling
        startPolling(data.job_id)
      } else {
        setMessage({ type: 'error', text: data.detail || 'Errore avvio analisi' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Errore connessione' })
    }
  }

  // Approve sample
  const approveSample = async (sampleId: string) => {
    try {
      const res = await fetch(`${API_BASE}/training/samples/${sampleId}/approve`, {
        method: 'POST'
      })

      if (res.ok) {
        setMessage({ type: 'success', text: 'Sample approvato!' })
        fetchSamples()
        fetchStatus()
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Errore approvazione' })
    }
  }

  // Reject (delete) sample
  const deleteSample = async (sampleId: string) => {
    try {
      const res = await fetch(`${API_BASE}/training/samples/${sampleId}`, {
        method: 'DELETE'
      })

      if (res.ok) {
        setMessage({ type: 'warning', text: 'Sample rifiutato e eliminato' })
        fetchSamples()
        fetchStatus()
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Errore eliminazione' })
    }
  }

  // Run benchmark (ASYNC)
  const runBenchmark = async (name: string) => {
    if (selectedEmails.size === 0) {
      setMessage({ type: 'warning', text: 'Seleziona almeno una email per il benchmark' })
      return
    }
    if (activeJob) {
      setMessage({ type: 'warning', text: 'Un job è già in esecuzione. Attendi il completamento.' })
      return
    }

    setMessage(null)

    try {
      // Avvia job asincrono
      const res = await fetch(`${API_BASE}/training/benchmark/async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_ids: Array.from(selectedEmails),
          tipo: tipoAnalisi,
          name: name
        })
      })

      const data = await res.json()

      if (data.success && data.job_id) {
        setMessage({
          type: 'success',
          text: `Benchmark "${name}" avviato per ${selectedEmails.size} email. Monitoraggio in corso...`
        })

        // Inizia polling
        startPolling(data.job_id)
      } else {
        setMessage({ type: 'error', text: data.detail || 'Errore avvio benchmark' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Errore esecuzione benchmark' })
    }
  }

  // Compare benchmarks
  const compareBenchmarks = async () => {
    if (!benchmarkBefore || !benchmarkAfter) {
      setMessage({ type: 'warning', text: 'Seleziona entrambi i benchmark da confrontare' })
      return
    }

    try {
      const res = await fetch(`${API_BASE}/training/benchmark/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          before_name: benchmarkBefore,
          after_name: benchmarkAfter
        })
      })

      const data = await res.json()

      if (data.success) {
        setComparison(data.comparison)
        setCurrentStep('compare')
      } else {
        setMessage({ type: 'error', text: data.detail || 'Errore confronto' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Errore confronto benchmark' })
    }
  }

  // Apply training
  const applyTraining = async () => {
    const approvedCount = status?.statistics?.approved_samples || 0
    if (approvedCount === 0) {
      setMessage({ type: 'warning', text: 'Nessun sample approvato da applicare. Approva prima alcuni sample.' })
      return
    }

    setApplyingTraining(true)
    setMessage(null)

    try {
      // Prima applica i pattern
      const applyRes = await fetch(`${API_BASE}/training/apply`, {
        method: 'POST'
      })

      const applyData = await applyRes.json()

      if (applyData.success) {
        // Poi ricarica il modello NLP
        const reloadRes = await fetch(`${API_BASE}/training/reload-patterns`, {
          method: 'POST'
        })

        if (reloadRes.ok) {
          setMessage({
            type: 'success',
            text: `Training applicato! Versione ${applyData.version_id}: ${applyData.patterns_added} nuovi pattern aggiunti (totale: ${applyData.total_patterns}). Modello NLP ricaricato.`
          })
          setCurrentStep('benchmark-after')
        } else {
          setMessage({
            type: 'warning',
            text: `Pattern salvati (${applyData.version_id}) ma errore ricaricamento modello. Potrebbe essere necessario riavviare il backend.`
          })
        }
        // Aggiorna history e versione corrente
        fetchTrainingHistory()
        fetchCurrentVersion()
      } else {
        setMessage({ type: 'error', text: applyData.message || 'Errore applicazione training' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Errore applicazione training' })
    } finally {
      setApplyingTraining(false)
      // Aggiorna info backup
      fetchBackupInfo()
    }
  }

  // Fetch backup info
  const fetchBackupInfo = async () => {
    try {
      const res = await fetch(`${API_BASE}/training/backup-info`)
      if (res.ok) {
        const data = await res.json()
        setBackupInfo(data)
      }
    } catch (e) {
      console.error('Error fetching backup info:', e)
    }
  }

  // Fetch training history
  const fetchTrainingHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/training/history?limit=10`)
      if (res.ok) {
        const data = await res.json()
        setTrainingHistory(data.history || [])
      }
    } catch (e) {
      console.error('Error fetching training history:', e)
    }
  }

  // Fetch current version
  const fetchCurrentVersion = async () => {
    try {
      const res = await fetch(`${API_BASE}/training/current-version`)
      if (res.ok) {
        const data = await res.json()
        setCurrentVersion(data)
      }
    } catch (e) {
      console.error('Error fetching current version:', e)
    }
  }

  // ==================== BERT ML TRAINING FUNCTIONS ====================

  // Start BERT training
  const startBertTraining = async () => {
    if (bertTrainJob?.status === 'running') {
      setMessage({ type: 'warning', text: 'Training BERT già in corso' })
      return
    }

    const approvedCount = status?.statistics?.approved_samples || 0
    if (approvedCount < 5) {
      setMessage({ type: 'warning', text: `Servono almeno 5 sample approvati per il training BERT. Attualmente: ${approvedCount}` })
      return
    }

    setMessage(null)

    try {
      const res = await fetch(`${API_BASE}/training/bert/train`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bertTrainConfig)
      })

      const data = await res.json()

      if (data.success && data.job_id) {
        setMessage({ type: 'success', text: `Training BERT avviato con ${data.samples_count} sample. Monitoraggio in corso...` })
        setBertTrainJob({ job_id: data.job_id, status: 'running', progress: 0, message: 'Avvio training...' })
        // Start polling BERT job
        pollBertJob(data.job_id)
      } else {
        setMessage({ type: 'error', text: data.detail || 'Errore avvio training BERT' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Errore connessione' })
    }
  }

  // Poll BERT job status
  const pollBertJob = async (jobId: string) => {
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/training/bert/job/${jobId}`)
        if (!res.ok) {
          setBertTrainJob(null)
          return
        }

        const data = await res.json()
        setBertTrainJob({
          job_id: jobId,
          status: data.status,
          progress: data.progress || 0,
          message: data.message || '',
          result: data.result
        })

        if (data.status === 'completed') {
          setMessage({
            type: 'success',
            text: `Training BERT completato! F1: ${(data.result?.metrics?.f1 * 100).toFixed(1)}%`
          })
          fetchBertStatus()
          setTimeout(() => setBertTrainJob(null), 5000)
        } else if (data.status === 'failed') {
          setMessage({ type: 'error', text: data.error || 'Training BERT fallito' })
          setTimeout(() => setBertTrainJob(null), 5000)
        } else {
          // Continue polling
          setTimeout(() => poll(), 3000)
        }
      } catch (e) {
        console.error('Error polling BERT job:', e)
      }
    }

    poll()
  }

  // Rollback BERT model
  const rollbackBertModel = async (versionId: string) => {
    if (!confirm(`Vuoi ripristinare il modello BERT alla versione ${versionId}?`)) return

    try {
      const res = await fetch(`${API_BASE}/training/bert/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version_id: versionId })
      })

      const data = await res.json()

      if (data.success) {
        setMessage({
          type: 'success',
          text: `Modello BERT ripristinato alla versione ${versionId}. F1: ${(data.metrics?.f1 * 100).toFixed(1)}%`
        })
        fetchBertStatus()
      } else {
        setMessage({ type: 'error', text: data.error || 'Errore rollback BERT' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Errore rollback' })
    }
  }

  // Run benchmark separato (spaCy o BERT)
  const runSeparateBenchmark = async (engine: 'spacy' | 'bert', name: string) => {
    if (selectedEmails.size === 0) {
      setMessage({ type: 'warning', text: 'Seleziona almeno una email per il benchmark' })
      return
    }

    setMessage(null)

    try {
      const res = await fetch(`${API_BASE}/training/benchmark/${engine}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_ids: Array.from(selectedEmails),
          tipo: tipoAnalisi,
          name: name
        })
      })

      const data = await res.json()

      if (data.success) {
        const metrics = data.benchmark?.metrics?.overall || {}
        setMessage({
          type: 'success',
          text: `Benchmark ${engine.toUpperCase()} completato! F1: ${metrics.f1?.toFixed(1) || 0}%, Precision: ${metrics.precision?.toFixed(1) || 0}%, Recall: ${metrics.recall?.toFixed(1) || 0}%`
        })
        fetchBenchmarks()
      } else {
        setMessage({ type: 'error', text: data.detail || `Errore benchmark ${engine}` })
      }
    } catch (e) {
      setMessage({ type: 'error', text: `Errore benchmark ${engine}` })
    }
  }

  // Rollback training
  const rollbackTraining = async () => {
    const backupVersion = backupInfo?.version_id || 'precedente'
    if (!confirm(`Sei sicuro di voler ripristinare il modello NLP alla versione ${backupVersion}?\n\nQuesta azione:\n- Annullerà l'ultimo training\n- Ripristinerà ${backupInfo?.pattern_count || 0} pattern\n- Verrà registrata nello storico`)) {
      return
    }

    setRollingBack(true)
    setMessage(null)

    try {
      const res = await fetch(`${API_BASE}/training/rollback`, {
        method: 'POST'
      })

      const data = await res.json()

      if (data.success) {
        setMessage({
          type: 'success',
          text: `Rollback completato! Versione ripristinata: ${data.restored_to_version}. Rimossi ${data.removed_patterns} pattern, ripristinati ${data.restored_patterns}.`
        })
        setComparison(null) // Reset comparison
        fetchBackupInfo()
        fetchBenchmarks()
        fetchTrainingHistory()
        fetchCurrentVersion()
      } else {
        setMessage({ type: 'error', text: data.message || 'Errore durante il rollback' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Errore durante il rollback' })
    } finally {
      setRollingBack(false)
    }
  }

  // Export data
  const exportData = async (format: 'spacy' | 'bert') => {
    try {
      const res = await fetch(`${API_BASE}/training/export/${format}?approved_only=true`)
      const data = await res.json()

      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `training_${format}_${data.total_samples}.json`
      a.click()
      URL.revokeObjectURL(url)

      setMessage({ type: 'success', text: `Esportati ${data.total_samples} samples approvati in formato ${format.toUpperCase()}` })
    } catch (e) {
      setMessage({ type: 'error', text: 'Errore esportazione' })
    }
  }

  // Approve all pending samples
  const approveAllPending = async () => {
    const pending = samples.filter(s => !s.approved)
    if (pending.length === 0) return

    for (const sample of pending) {
      await approveSample(sample.id)
    }
    setMessage({ type: 'success', text: `Approvati ${pending.length} samples` })
  }

  // Get workflow step status
  const getStepStatus = (step: WorkflowStep): 'completed' | 'current' | 'pending' => {
    const steps: WorkflowStep[] = ['select', 'benchmark-before', 'analyze', 'approve', 'apply', 'benchmark-after', 'compare']
    const currentIndex = steps.indexOf(currentStep)
    const stepIndex = steps.indexOf(step)

    if (stepIndex < currentIndex) return 'completed'
    if (stepIndex === currentIndex) return 'current'
    return 'pending'
  }

  const pendingSamples = samples.filter(s => !s.approved)
  const approvedSamples = samples.filter(s => s.approved)

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
        <Brain className="w-7 h-7 text-purple-600" />
        NLP Training con ChatGPT
      </h1>

      {/* Message */}
      {message && (
        <div className={`mb-4 p-4 rounded-lg flex items-start gap-3 ${
          message.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' :
          message.type === 'warning' ? 'bg-yellow-50 text-yellow-800 border border-yellow-200' :
          'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {message.type === 'success' && <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />}
          {message.type === 'warning' && <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />}
          {message.type === 'error' && <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />}
          {message.text}
        </div>
      )}

      {/* Active Job Progress */}
      {activeJob && activeJob.status === 'running' && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />
              <span className="font-medium text-blue-900">
                {activeJob.type === 'analyze_batch' ? 'Analisi ChatGPT' : 'Benchmark NLP'}
              </span>
            </div>
            <span className="text-sm text-blue-700 font-mono">{activeJob.progress}%</span>
          </div>
          <div className="w-full bg-blue-200 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${activeJob.progress}%` }}
            />
          </div>
          <p className="text-sm text-blue-700 mt-2">{activeJob.message}</p>
        </div>
      )}

      {/* Workflow Guide */}
      {showWorkflowGuide && (
        <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border border-purple-200">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-semibold text-purple-900 mb-2 flex items-center gap-2">
                <Layers className="w-5 h-5" />
                Workflow Training NLP
              </h3>
              <div className="flex flex-wrap gap-2 text-sm">
                {[
                  { step: 'select', label: '1. Seleziona Email', icon: Mail },
                  { step: 'analyze', label: '2. Analizza ChatGPT', icon: Play },
                  { step: 'approve', label: '3. Approva Risultati', icon: Check },
                  { step: 'benchmark-before', label: '4. Benchmark PRIMA', icon: BarChart3 },
                  { step: 'apply', label: '5. Applica Training', icon: Zap },
                  { step: 'benchmark-after', label: '6. Benchmark DOPO', icon: BarChart3 },
                  { step: 'compare', label: '7. Confronta', icon: Target }
                ].map(({ step, label, icon: Icon }) => {
                  const stepStatus = getStepStatus(step as WorkflowStep)
                  return (
                    <button
                      key={step}
                      onClick={() => setCurrentStep(step as WorkflowStep)}
                      className={`flex items-center gap-1 px-3 py-1.5 rounded-full transition-all ${
                        stepStatus === 'current'
                          ? 'bg-purple-600 text-white shadow-md'
                          : stepStatus === 'completed'
                          ? 'bg-green-100 text-green-700 border border-green-300'
                          : 'bg-white text-gray-600 border'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {label}
                      {stepStatus === 'completed' && <CheckCircle className="w-3 h-3 ml-1" />}
                    </button>
                  )
                })}
              </div>
            </div>
            <div className="flex items-center gap-4">
              {/* Riepilogo email selezionate - sempre visibile */}
              {selectedEmails.size > 0 && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-green-100 border border-green-300 rounded-full">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm font-medium text-green-700">
                    {selectedEmails.size} email selezionate
                  </span>
                  <span className="text-xs text-green-600">
                    (ID: {Array.from(selectedEmails).slice(0, 5).join(', ')}{selectedEmails.size > 5 ? '...' : ''})
                  </span>
                </div>
              )}
              <button
                onClick={() => setShowWorkflowGuide(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className={`p-4 rounded-lg border ${status?.openai_available ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <div className="flex items-center gap-2">
            {status?.openai_available ? (
              <CheckCircle className="w-5 h-5 text-green-600" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-600" />
            )}
            <span className="font-medium">ChatGPT</span>
          </div>
          <p className="text-sm mt-1">
            {status?.openai_available ? 'Disponibile' : 'Non configurato'}
          </p>
        </div>

        <div className="p-4 rounded-lg border bg-purple-50 border-purple-200">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-purple-600" />
            <span className="font-medium">Samples</span>
          </div>
          <p className="text-2xl font-bold mt-1">{status?.statistics?.total_samples || 0}</p>
        </div>

        <div className="p-4 rounded-lg border bg-green-50 border-green-200">
          <div className="flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-green-600" />
            <span className="font-medium">Approvati</span>
          </div>
          <p className="text-2xl font-bold mt-1">{status?.statistics?.approved_samples || 0}</p>
        </div>

        <div className="p-4 rounded-lg border bg-yellow-50 border-yellow-200">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-yellow-600" />
            <span className="font-medium">Da Approvare</span>
          </div>
          <p className="text-2xl font-bold mt-1">{status?.statistics?.pending_approval || 0}</p>
        </div>

        <div className="p-4 rounded-lg border bg-blue-50 border-blue-200">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            <span className="font-medium">Benchmarks</span>
          </div>
          <p className="text-2xl font-bold mt-1">{benchmarks.length}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Email Selection */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Mail className="w-5 h-5" />
              Seleziona Email
              <span className="ml-auto text-sm font-normal text-gray-500">
                {selectedEmails.size} selezionate
              </span>
            </h3>

            <div className="mb-4 flex gap-2">
              <div className="flex-1">
                <select
                  className="input w-full"
                  value={tipoAnalisi}
                  onChange={(e) => setTipoAnalisi(e.target.value as any)}
                >
                  <option value="interpello">Interpello</option>
                  <option value="calendario">Calendario</option>
                  <option value="generico">Generico</option>
                </select>
              </div>
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  className="input pl-10 w-full"
                  placeholder="Cerca..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>

            {/* Pulsanti selezione rapida */}
            <div className="mb-2 flex gap-2 text-xs">
              <button
                className="px-2 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                onClick={() => {
                  const allIds = new Set(filteredEmails.map(e => e.id))
                  setSelectedEmails(allIds)
                }}
              >
                Seleziona tutte ({filteredEmails.length})
              </button>
              <button
                className="px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                onClick={() => setSelectedEmails(new Set())}
              >
                Deseleziona tutte
              </button>
              {selectedEmails.size > 0 && (
                <span className="px-2 py-1 bg-green-100 text-green-700 rounded font-medium">
                  {selectedEmails.size} email pronte per analisi
                </span>
              )}
            </div>

            <div className="max-h-64 overflow-y-auto border rounded mb-4">
              {filteredEmails.map((email) => (
                <div
                  key={email.id}
                  className={`p-2 border-b cursor-pointer hover:bg-gray-50 ${selectedEmails.has(email.id) ? 'bg-purple-50' : ''}`}
                  onClick={() => toggleEmail(email.id)}
                >
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={selectedEmails.has(email.id)}
                      onChange={() => toggleEmail(email.id)}
                      className="mt-1"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{email.oggetto || '(Senza oggetto)'}</p>
                      <p className="text-xs text-gray-500 truncate">{email.mittente}</p>
                    </div>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      email.categoria === 'interpello' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100'
                    }`}>
                      {email.categoria || 'altro'}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                className={`btn flex-1 flex items-center justify-center gap-2 ${
                  activeJob || !status?.openai_available
                    ? 'bg-gray-400 cursor-not-allowed text-white'
                    : 'btn-primary'
                }`}
                onClick={analyzeEmails}
                disabled={!!activeJob || !status?.openai_available}
              >
                {activeJob?.type === 'analyze_batch' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {activeJob?.type === 'analyze_batch' ? 'Analisi in corso...' : 'Analizza con ChatGPT'}
              </button>
            </div>
            {selectedEmails.size === 0 && (
              <p className="text-sm text-amber-600 mt-2 flex items-center gap-1">
                <AlertTriangle className="w-4 h-4" />
                Seleziona almeno una email dalla lista sopra
              </p>
            )}
            {!status?.openai_available && (
              <p className="text-sm text-red-600 mt-2 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                ChatGPT non configurato. Imposta la API key in Impostazioni → LLM
              </p>
            )}
          </div>

          {/* Benchmark Section */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Benchmark NLP
              <button
                onClick={fetchBenchmarks}
                className="ml-auto p-1 hover:bg-gray-100 rounded"
                title="Ricarica"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </h3>

            {/* Spiegazione dettagliata benchmark */}
            <div className="mb-4 p-3 bg-blue-50 rounded text-sm text-blue-800 border border-blue-200">
              <strong>Cos'è il Benchmark?</strong>
              <p className="mt-1">
                Il benchmark confronta l'estrazione del modello NLP locale con i dati "corretti"
                (ground truth) estratti da ChatGPT e <strong>approvati da te</strong>.
              </p>
              <div className="mt-2 p-2 bg-white rounded border border-blue-100">
                <p><strong>F1 Score</strong> = accuratezza complessiva (0-100%)</p>
                <p className="text-xs text-gray-600 mt-1">
                  Precision = quanti dati trovati sono corretti |
                  Recall = quanti dati corretti sono stati trovati
                </p>
              </div>
            </div>

            {/* Warning se nessun sample approvato */}
            {(status?.statistics?.approved_samples || 0) === 0 && (
              <div className="mb-4 p-3 bg-amber-50 rounded text-sm text-amber-800 border border-amber-200">
                <strong>⚠️ Perché il benchmark mostra 0%?</strong>
                <p className="mt-1">
                  Non hai ancora <strong>approvato</strong> nessun sample ChatGPT!
                  Senza dati approvati, non c'è un "ground truth" con cui confrontare.
                </p>
                <p className="mt-2 font-medium">
                  Cosa fare: Analizza email con ChatGPT → Approva i risultati corretti → Esegui benchmark
                </p>
              </div>
            )}

            {/* Info sample disponibili */}
            {(status?.statistics?.approved_samples || 0) > 0 && (
              <div className="mb-4 p-2 bg-green-50 rounded text-sm text-green-800 border border-green-200 flex items-center gap-2">
                <Check className="w-4 h-4" />
                <span>
                  <strong>{status?.statistics?.approved_samples}</strong> sample approvati disponibili come ground truth.
                  Il benchmark sarà significativo solo per le email che hanno un sample approvato.
                </span>
              </div>
            )}

            <div className="flex gap-2 mb-4">
              <button
                className={`btn flex-1 flex items-center justify-center gap-2 ${
                  activeJob ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
                } text-white`}
                onClick={() => runBenchmark(`pre_training_${Date.now()}`)}
                disabled={!!activeJob}
              >
                {activeJob?.type === 'benchmark' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                {activeJob?.type === 'benchmark' ? 'Benchmark in corso...' : 'Benchmark PRIMA'}
              </button>
              <button
                className={`btn flex-1 flex items-center justify-center gap-2 ${
                  activeJob ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'
                } text-white`}
                onClick={() => runBenchmark(`post_training_${Date.now()}`)}
                disabled={!!activeJob}
              >
                {activeJob?.type === 'benchmark' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                {activeJob?.type === 'benchmark' ? 'Benchmark in corso...' : 'Benchmark DOPO'}
              </button>
            </div>
            {selectedEmails.size === 0 && (
              <p className="text-sm text-amber-600 mb-4 flex items-center gap-1">
                <AlertTriangle className="w-4 h-4" />
                Seleziona almeno una email dalla lista sopra per eseguire il benchmark
              </p>
            )}

            {/* Benchmark list */}
            {benchmarks.length > 0 && (
              <div className="mb-4">
                <p className="text-sm font-medium mb-2">Ultimi Benchmark:</p>
                <div className="max-h-40 overflow-y-auto border rounded">
                  {benchmarks.slice().reverse().map((b) => (
                    <div key={b.name} className="p-2 border-b text-sm flex items-center justify-between hover:bg-gray-50">
                      <div>
                        <span className={`font-medium ${b.name.includes('pre') ? 'text-blue-600' : 'text-green-600'}`}>
                          {b.name.includes('pre') ? 'PRE' : 'POST'}
                        </span>
                        <span className="text-gray-500 ml-2">{new Date(b.timestamp).toLocaleString('it-IT')}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">{b.email_count} email</span>
                        <span className="font-mono font-bold">
                          F1: {(b.metrics.avg_f1_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Compare benchmarks */}
            {benchmarks.length >= 2 && (
              <div className="border-t pt-4 mt-4">
                <p className="text-sm font-medium mb-2">Confronta Benchmark:</p>
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <select
                    className="input text-sm"
                    value={benchmarkBefore}
                    onChange={(e) => setBenchmarkBefore(e.target.value)}
                  >
                    <option value="">PRIMA (baseline)</option>
                    {benchmarks.map(b => (
                      <option key={b.name} value={b.name}>
                        {b.name.substring(0, 30)} - F1: {(b.metrics.avg_f1_score * 100).toFixed(1)}%
                      </option>
                    ))}
                  </select>
                  <select
                    className="input text-sm"
                    value={benchmarkAfter}
                    onChange={(e) => setBenchmarkAfter(e.target.value)}
                  >
                    <option value="">DOPO (nuovo)</option>
                    {benchmarks.map(b => (
                      <option key={b.name} value={b.name}>
                        {b.name.substring(0, 30)} - F1: {(b.metrics.avg_f1_score * 100).toFixed(1)}%
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  className="btn btn-outline w-full flex items-center justify-center gap-2"
                  onClick={compareBenchmarks}
                  disabled={!benchmarkBefore || !benchmarkAfter}
                >
                  <Target className="w-4 h-4" />
                  Confronta Performance
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Training Samples - Pending Approval */}
          <div className="card max-h-[80vh] overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 sticky top-0 bg-white pb-2 z-10">
              <Clock className="w-5 h-5 text-yellow-600" />
              Da Approvare ({pendingSamples.length})
              {pendingSamples.length > 0 && (
                <button
                  onClick={approveAllPending}
                  className="ml-auto btn btn-sm bg-green-600 text-white hover:bg-green-700 flex items-center gap-1"
                >
                  <Check className="w-3 h-3" />
                  Approva Tutti
                </button>
              )}
            </h3>

            <div className="space-y-3">
              {pendingSamples.length === 0 ? (
                <p className="text-gray-500 text-center py-4 text-sm">
                  Nessun sample in attesa di approvazione
                </p>
              ) : (
                pendingSamples.map((sample) => (
                  <div key={sample.id} className="border rounded-lg overflow-hidden bg-white shadow-sm">
                    {/* Header */}
                    <div className="flex items-center justify-between p-3 bg-yellow-50 border-b border-yellow-200">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium">
                          {sample.type || 'generico'}
                        </span>
                        <span className="text-sm font-medium">Email #{sample.email_id}</span>
                        <span className="text-xs text-gray-500">
                          {new Date(sample.timestamp).toLocaleString('it-IT')}
                        </span>
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => approveSample(sample.id)}
                          className="px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-1 text-sm font-medium"
                          title="Approva"
                        >
                          <Check className="w-4 h-4" />
                          Approva
                        </button>
                        <button
                          onClick={() => deleteSample(sample.id)}
                          className="px-3 py-1.5 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 flex items-center gap-1 text-sm font-medium"
                          title="Rifiuta"
                        >
                          <X className="w-4 h-4" />
                          Rifiuta
                        </button>
                      </div>
                    </div>

                    {/* Content - Always Expanded */}
                    <div className="p-3 space-y-3">
                      {/* Original Text Section */}
                      <div>
                        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1 flex items-center gap-1">
                          <Mail className="w-3 h-3" />
                          Testo Originale Email/Allegato
                        </p>
                        <div className="bg-gray-50 rounded-lg p-3 border max-h-48 overflow-y-auto">
                          <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans">
                            {sample.text || '(Nessun testo disponibile)'}
                          </pre>
                        </div>
                      </div>

                      {/* ChatGPT Extraction Section */}
                      <div>
                        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1 flex items-center gap-1">
                          <Brain className="w-3 h-3" />
                          Valori Estratti da ChatGPT
                        </p>
                        <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                          <div className="grid grid-cols-1 gap-2">
                            {Object.entries(sample.openai_extraction)
                              .filter(([k, v]) => v !== null && v !== undefined && v !== '' && k !== 'entities')
                              .map(([key, value]) => (
                                <div key={key} className="flex flex-col sm:flex-row sm:items-start gap-1 text-sm">
                                  <span className="font-semibold text-blue-700 sm:min-w-[140px] sm:max-w-[140px]">
                                    {key.replace(/_/g, ' ')}:
                                  </span>
                                  <span className="text-gray-800 break-words">
                                    {typeof value === 'object'
                                      ? JSON.stringify(value, null, 2)
                                      : String(value)
                                    }
                                  </span>
                                </div>
                              ))
                            }
                            {Object.entries(sample.openai_extraction).filter(([k, v]) => v && k !== 'entities').length === 0 && (
                              <p className="text-gray-500 italic text-sm">Nessun valore estratto</p>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Raw JSON Toggle */}
                      <button
                        className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                        onClick={() => setExpandedSample(expandedSample === sample.id ? null : sample.id)}
                      >
                        {expandedSample === sample.id ? 'Nascondi JSON raw' : 'Mostra JSON raw'}
                      </button>
                      {expandedSample === sample.id && (
                        <pre className="text-xs bg-gray-900 text-green-400 p-3 rounded-lg overflow-x-auto max-h-48">
                          {JSON.stringify(sample.openai_extraction, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Apply Training */}
          <div className="card bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-purple-600" />
              Applica Training
            </h3>

            <p className="text-sm text-gray-700 mb-4">
              Hai <strong>{status?.statistics?.approved_samples || 0}</strong> sample approvati pronti per il training.
              I pattern estratti verranno aggiunti all'EntityRuler di spaCy.
            </p>

            <button
              className="btn w-full bg-purple-600 text-white hover:bg-purple-700 flex items-center justify-center gap-2"
              onClick={applyTraining}
              disabled={applyingTraining || (status?.statistics?.approved_samples || 0) === 0}
            >
              {applyingTraining ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              Applica {status?.statistics?.approved_samples || 0} Pattern al Modello NLP
            </button>

            <div className="mt-4 flex gap-2">
              <button
                className="btn btn-outline flex-1 flex items-center justify-center gap-1 text-sm"
                onClick={() => exportData('spacy')}
                disabled={(status?.statistics?.approved_samples || 0) === 0}
              >
                <Download className="w-4 h-4" />
                Export spaCy
              </button>
              <button
                className="btn btn-outline flex-1 flex items-center justify-center gap-1 text-sm"
                onClick={() => exportData('bert')}
                disabled={(status?.statistics?.approved_samples || 0) === 0}
              >
                <Download className="w-4 h-4" />
                Export BERT
              </button>
            </div>

            {/* Current Version Info */}
            {currentVersion && (
              <div className="mt-4 pt-4 border-t border-purple-200">
                <div className="flex items-center gap-2 text-sm">
                  <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded font-mono font-bold">
                    {currentVersion.version_id}
                  </span>
                  <span className="text-gray-500">
                    {currentVersion.total_patterns} pattern attivi
                  </span>
                </div>
              </div>
            )}

            {/* Rollback Section */}
            {backupInfo?.backup_available && (
              <div className="mt-4 pt-4 border-t border-purple-200">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    <p className="font-medium">Rollback disponibile</p>
                    <p className="text-xs">
                      Versione: <span className="font-mono">{backupInfo.version_id || 'precedente'}</span> -
                      {backupInfo.pattern_count} pattern dal {backupInfo.timestamp ? new Date(backupInfo.timestamp).toLocaleString('it-IT') : 'N/A'}
                    </p>
                  </div>
                  <button
                    className="btn bg-amber-500 text-white hover:bg-amber-600 flex items-center gap-1 text-sm"
                    onClick={rollbackTraining}
                    disabled={rollingBack}
                  >
                    {rollingBack ? <RefreshCw className="w-4 h-4 animate-spin" /> : <History className="w-4 h-4" />}
                    Rollback
                  </button>
                </div>
              </div>
            )}

            {/* Training History */}
            {trainingHistory.length > 0 && (
              <div className="mt-4 pt-4 border-t border-purple-200">
                <p className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                  <History className="w-4 h-4" />
                  Storico Training (ultime {trainingHistory.length} versioni)
                </p>
                <div className="max-h-32 overflow-y-auto text-xs">
                  {trainingHistory.map((entry) => (
                    <div
                      key={entry.version_id}
                      className={`p-2 border-b flex items-center justify-between ${
                        entry.status === 'rollback' ? 'bg-amber-50' : 'bg-gray-50'
                      }`}
                    >
                      <div>
                        <span className={`font-mono font-bold ${
                          entry.status === 'rollback' ? 'text-amber-700' : 'text-green-700'
                        }`}>
                          {entry.version_id}
                        </span>
                        <span className="text-gray-500 ml-2">
                          {new Date(entry.timestamp).toLocaleString('it-IT')}
                        </span>
                      </div>
                      <div className="text-right">
                        {entry.status === 'applied' && (
                          <span className="text-green-600">
                            +{entry.patterns_added} pattern ({entry.total_patterns} totali)
                          </span>
                        )}
                        {entry.status === 'rollback' && (
                          <span className="text-amber-600">
                            Rollback a {entry.restored_to}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* BERT ML Training Section */}
          <div className="card bg-gradient-to-r from-blue-50 to-cyan-50 border-blue-200">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-blue-600" />
              Training BERT (Machine Learning)
              <button
                onClick={() => setShowBertConfig(!showBertConfig)}
                className="ml-auto p-1 hover:bg-blue-100 rounded"
                title="Configura"
              >
                <Settings className="w-4 h-4 text-blue-600" />
              </button>
            </h3>

            {/* Spiegazione BERT */}
            <div className="mb-4 p-3 bg-white rounded border border-blue-200 text-sm">
              <p className="text-blue-800">
                <strong>Cos'è il training BERT?</strong><br />
                A differenza di spaCy che usa pattern statici, BERT è un modello di
                <strong> Machine Learning</strong> che impara dai tuoi dati approvati.
                Fine-tuning BERT permette riconoscimento più intelligente delle entità.
              </p>
            </div>

            {/* BERT Status */}
            <div className="mb-4 p-3 bg-white rounded border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${bertStatus?.is_trained ? 'bg-green-500' : 'bg-gray-300'}`} />
                <div>
                  <p className="font-medium text-sm">
                    {bertStatus?.is_trained ? 'Modello Fine-Tuned' : 'Modello Base (Pre-trained)'}
                  </p>
                  {bertStatus?.current_model && !bertStatus.current_model.is_base && (
                    <p className="text-xs text-gray-500">
                      Versione: <span className="font-mono">{bertStatus.current_model.version_id}</span>
                      {bertStatus.current_model.metrics && (
                        <span className="ml-2">
                          F1: {(bertStatus.current_model.metrics.f1 * 100).toFixed(1)}%
                        </span>
                      )}
                    </p>
                  )}
                </div>
              </div>
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                {bertStatus?.models_count || 0} modelli
              </span>
            </div>

            {/* Configurazione (collapsible) */}
            {showBertConfig && (
              <div className="mb-4 p-3 bg-gray-50 rounded border">
                <p className="text-sm font-medium mb-2">Parametri Training:</p>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-xs text-gray-600">Epochs</label>
                    <input
                      type="number"
                      className="input w-full text-sm"
                      value={bertTrainConfig.epochs}
                      onChange={(e) => setBertTrainConfig({ ...bertTrainConfig, epochs: parseInt(e.target.value) || 3 })}
                      min={1}
                      max={10}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-600">Batch Size</label>
                    <input
                      type="number"
                      className="input w-full text-sm"
                      value={bertTrainConfig.batch_size}
                      onChange={(e) => setBertTrainConfig({ ...bertTrainConfig, batch_size: parseInt(e.target.value) || 8 })}
                      min={1}
                      max={32}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-600">Learning Rate</label>
                    <input
                      type="number"
                      className="input w-full text-sm"
                      value={bertTrainConfig.learning_rate}
                      onChange={(e) => setBertTrainConfig({ ...bertTrainConfig, learning_rate: parseFloat(e.target.value) || 0.00002 })}
                      step={0.00001}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* BERT Training Job Progress */}
            {bertTrainJob && bertTrainJob.status === 'running' && (
              <div className="mb-4 p-3 bg-blue-100 rounded border border-blue-300">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 text-blue-600 animate-spin" />
                    <span className="font-medium text-blue-900 text-sm">Training in corso</span>
                  </div>
                  <span className="text-sm text-blue-700 font-mono">{bertTrainJob.progress}%</span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${bertTrainJob.progress}%` }}
                  />
                </div>
                <p className="text-xs text-blue-700 mt-1">{bertTrainJob.message}</p>
              </div>
            )}

            {/* BERT Training Completed Result */}
            {bertTrainJob && bertTrainJob.status === 'completed' && bertTrainJob.result && (
              <div className="mb-4 p-3 bg-green-100 rounded border border-green-300">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="font-medium text-green-900 text-sm">Training completato!</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs mb-2">
                  <div className="bg-white p-2 rounded text-center">
                    <div className="font-bold text-green-700">
                      {((bertTrainJob.result.metrics?.f1 || 0) * 100).toFixed(1)}%
                    </div>
                    <div className="text-gray-500">F1 Score</div>
                  </div>
                  <div className="bg-white p-2 rounded text-center">
                    <div className="font-bold text-blue-700">
                      {((bertTrainJob.result.metrics?.precision || 0) * 100).toFixed(1)}%
                    </div>
                    <div className="text-gray-500">Precision</div>
                  </div>
                  <div className="bg-white p-2 rounded text-center">
                    <div className="font-bold text-purple-700">
                      {((bertTrainJob.result.metrics?.recall || 0) * 100).toFixed(1)}%
                    </div>
                    <div className="text-gray-500">Recall</div>
                  </div>
                </div>
                <p className="text-xs text-green-700">
                  Modello: {bertTrainJob.result.version_id} |
                  Samples: {bertTrainJob.result.metrics?.samples || 0} |
                  Epochs: {bertTrainJob.result.metrics?.epochs || 0}
                </p>
              </div>
            )}

            {/* BERT Training Failed */}
            {bertTrainJob && bertTrainJob.status === 'failed' && (
              <div className="mb-4 p-3 bg-red-100 rounded border border-red-300">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-red-600" />
                  <span className="font-medium text-red-900 text-sm">Training fallito</span>
                </div>
                <p className="text-xs text-red-700 mt-1">{bertTrainJob.message}</p>
              </div>
            )}

            {/* Train Button */}
            <button
              className={`btn w-full flex items-center justify-center gap-2 ${
                bertTrainJob?.status === 'running' || (status?.statistics?.approved_samples || 0) < 5
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              } text-white`}
              onClick={startBertTraining}
              disabled={bertTrainJob?.status === 'running' || (status?.statistics?.approved_samples || 0) < 5}
            >
              {bertTrainJob?.status === 'running' ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Training in corso...
                </>
              ) : (
                <>
                  <Brain className="w-4 h-4" />
                  Avvia Training BERT ({status?.statistics?.approved_samples || 0} samples)
                </>
              )}
            </button>

            {(status?.statistics?.approved_samples || 0) < 5 && (
              <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Servono almeno 5 sample approvati (hai {status?.statistics?.approved_samples || 0})
              </p>
            )}

            {/* Modelli disponibili per rollback */}
            {bertStatus && bertStatus.available_models.length > 0 && (
              <div className="mt-4 pt-4 border-t border-blue-200">
                <p className="text-sm font-medium text-gray-700 mb-2">Modelli BERT disponibili:</p>
                <div className="max-h-32 overflow-y-auto text-xs space-y-1">
                  {bertStatus.available_models.map((model) => (
                    <div
                      key={model.version_id}
                      className={`p-2 rounded flex items-center justify-between ${
                        model.is_current ? 'bg-green-100 border border-green-300' : 'bg-gray-50'
                      }`}
                    >
                      <div>
                        <span className={`font-mono font-bold ${model.is_current ? 'text-green-700' : 'text-gray-700'}`}>
                          {model.version_id}
                        </span>
                        {model.metrics && (
                          <span className="text-gray-500 ml-2">
                            F1: {(model.metrics.f1 * 100).toFixed(1)}%
                          </span>
                        )}
                        {model.is_current && (
                          <span className="ml-2 px-1 py-0.5 bg-green-200 text-green-800 rounded text-xs">
                            Attivo
                          </span>
                        )}
                      </div>
                      {!model.is_current && (
                        <button
                          onClick={() => rollbackBertModel(model.version_id)}
                          className="px-2 py-1 bg-amber-100 text-amber-700 rounded hover:bg-amber-200 text-xs"
                        >
                          Ripristina
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Benchmark Separati spaCy / BERT */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-orange-600" />
              Benchmark Separati
            </h3>

            {/* Tab selettore */}
            <div className="flex mb-4 bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setActiveTab('spacy')}
                className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'spacy'
                    ? 'bg-white shadow text-purple-700'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                <Zap className="w-4 h-4 inline mr-1" />
                spaCy (Pattern)
              </button>
              <button
                onClick={() => setActiveTab('bert')}
                className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'bert'
                    ? 'bg-white shadow text-blue-700'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                <Cpu className="w-4 h-4 inline mr-1" />
                BERT (ML)
              </button>
            </div>

            {/* Contenuto Tab */}
            <div className="p-3 bg-gray-50 rounded border mb-4">
              {activeTab === 'spacy' ? (
                <div>
                  <p className="text-sm text-gray-700 mb-2">
                    Benchmark su <strong>spaCy EntityRuler</strong>: misura l'accuratezza dei pattern
                    statici rispetto ai dati approvati da ChatGPT.
                  </p>
                  <button
                    onClick={() => runSeparateBenchmark('spacy', `spacy_${Date.now()}`)}
                    disabled={selectedEmails.size === 0}
                    className={`btn w-full flex items-center justify-center gap-2 ${
                      selectedEmails.size === 0 ? 'bg-gray-400 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-700'
                    } text-white`}
                  >
                    <Zap className="w-4 h-4" />
                    Esegui Benchmark spaCy
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-sm text-gray-700 mb-2">
                    Benchmark su <strong>BERT</strong>: misura l'accuratezza del modello ML
                    {bertStatus?.is_trained ? ' fine-tuned' : ' base (pre-trained)'}.
                  </p>
                  <button
                    onClick={() => runSeparateBenchmark('bert', `bert_${Date.now()}`)}
                    disabled={selectedEmails.size === 0}
                    className={`btn w-full flex items-center justify-center gap-2 ${
                      selectedEmails.size === 0 ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
                    } text-white`}
                  >
                    <Cpu className="w-4 h-4" />
                    Esegui Benchmark BERT
                  </button>
                </div>
              )}
            </div>

            {selectedEmails.size === 0 && (
              <p className="text-xs text-amber-600 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Seleziona email dalla lista per eseguire il benchmark
              </p>
            )}
          </div>

          {/* Comparison Results */}
          {comparison && (
            <div className={`card ${comparison.improved ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'}`}>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                {comparison.improved ? (
                  <TrendingUp className="w-5 h-5 text-green-600" />
                ) : (
                  <TrendingDown className="w-5 h-5 text-red-600" />
                )}
                Risultato Confronto
              </h3>

              <div className={`p-4 rounded-lg text-center mb-4 ${comparison.improved ? 'bg-green-100' : 'bg-red-100'}`}>
                <p className="text-lg font-bold">
                  {comparison.improved ? 'MIGLIORAMENTO!' : 'PEGGIORAMENTO'}
                </p>
                <p className="text-3xl font-mono font-bold mt-2">
                  {comparison.delta.avg_f1_score > 0 ? '+' : ''}{(comparison.delta.avg_f1_score * 100).toFixed(2)}%
                </p>
                <p className="text-sm text-gray-600">Delta F1 Score</p>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center">
                  <p className="text-sm text-gray-500">Precision</p>
                  <p className="font-mono">
                    {(comparison.before.metrics.avg_precision * 100).toFixed(1)}%
                    <ArrowRight className="w-4 h-4 inline mx-1" />
                    {(comparison.after.metrics.avg_precision * 100).toFixed(1)}%
                  </p>
                  <p className={`text-sm font-bold ${comparison.delta.avg_precision >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {comparison.delta.avg_precision >= 0 ? '+' : ''}{(comparison.delta.avg_precision * 100).toFixed(2)}%
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-gray-500">Recall</p>
                  <p className="font-mono">
                    {(comparison.before.metrics.avg_recall * 100).toFixed(1)}%
                    <ArrowRight className="w-4 h-4 inline mx-1" />
                    {(comparison.after.metrics.avg_recall * 100).toFixed(1)}%
                  </p>
                  <p className={`text-sm font-bold ${comparison.delta.avg_recall >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {comparison.delta.avg_recall >= 0 ? '+' : ''}{(comparison.delta.avg_recall * 100).toFixed(2)}%
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-gray-500">F1 Score</p>
                  <p className="font-mono">
                    {(comparison.before.metrics.avg_f1_score * 100).toFixed(1)}%
                    <ArrowRight className="w-4 h-4 inline mx-1" />
                    {(comparison.after.metrics.avg_f1_score * 100).toFixed(1)}%
                  </p>
                  <p className={`text-sm font-bold ${comparison.delta.avg_f1_score >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {comparison.delta.avg_f1_score >= 0 ? '+' : ''}{(comparison.delta.avg_f1_score * 100).toFixed(2)}%
                  </p>
                </div>
              </div>

              {Object.keys(comparison.by_field).length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">Dettaglio per Campo:</p>
                  <div className="space-y-1">
                    {Object.entries(comparison.by_field).map(([field, data]) => (
                      <div key={field} className="flex items-center justify-between text-sm bg-white rounded px-2 py-1">
                        <span className="text-gray-700">{field}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-gray-500">{(data.before_f1 * 100).toFixed(0)}%</span>
                          <ArrowRight className="w-3 h-3" />
                          <span className="font-medium">{(data.after_f1 * 100).toFixed(0)}%</span>
                          <span className={`text-xs font-bold ${data.delta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {data.delta >= 0 ? '+' : ''}{(data.delta * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-4 p-3 bg-white rounded">
                <p className="text-sm">
                  {comparison.improved ? (
                    <>
                      <CheckCircle className="w-4 h-4 inline text-green-600 mr-1" />
                      <strong>Raccomandazione:</strong> Il training ha migliorato le performance. Puoi fare commit delle modifiche.
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-4 h-4 inline text-red-600 mr-1" />
                      <strong>Attenzione:</strong> Il training ha peggiorato le performance. Usa il rollback per ripristinare lo stato precedente.
                    </>
                  )}
                </p>
              </div>

              {/* Rollback button when performance is worse */}
              {!comparison.improved && backupInfo?.backup_available && (
                <div className="mt-4">
                  <button
                    className="btn w-full bg-red-600 text-white hover:bg-red-700 flex items-center justify-center gap-2"
                    onClick={rollbackTraining}
                    disabled={rollingBack}
                  >
                    {rollingBack ? <RefreshCw className="w-4 h-4 animate-spin" /> : <History className="w-4 h-4" />}
                    Rollback - Ripristina Modello Precedente
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Approved Samples Summary */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              Approvati ({approvedSamples.length})
            </h3>

            {approvedSamples.length === 0 ? (
              <p className="text-gray-500 text-center py-4 text-sm">
                Nessun sample approvato
              </p>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-1">
                {approvedSamples.map((sample) => (
                  <div key={sample.id} className="flex items-center justify-between p-2 bg-green-50 rounded text-sm">
                    <span>Email #{sample.email_id} - {sample.type}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-green-600">{sample.entities?.length || 0} entita</span>
                      <button
                        onClick={() => deleteSample(sample.id)}
                        className="p-1 text-red-600 hover:bg-red-100 rounded"
                        title="Rimuovi"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
