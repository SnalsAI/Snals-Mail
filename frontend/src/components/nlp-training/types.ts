/**
 * TypeScript types per NLP Training
 */

// ============================================
// WORKFLOW
// ============================================

export type WorkflowStep =
  | 'select'           // 1. Seleziona email
  | 'analyze'          // 2. Analizza con ChatGPT
  | 'approve'          // 3. Rivedi e approva
  | 'benchmark-before' // 4. Benchmark pre-training
  | 'apply'            // 5. Applica training
  | 'benchmark-after'  // 6. Benchmark post-training
  | 'compare'          // 7. Confronta risultati

export interface StepValidation {
  canProceedToAnalyze: boolean
  canProceedToApprove: boolean
  canApplyTraining: boolean
  canBenchmark: boolean
}

// ============================================
// EMAIL & SAMPLES
// ============================================

export interface Email {
  id: number
  oggetto: string
  corpo_testo: string
  data_ricezione: string
  mittente_email: string
  categoria?: string
  sottocategoria?: string
}

export interface TrainingSample {
  id: string
  email_id: number
  timestamp: string
  type: 'interpello' | 'calendario' | 'generico'
  text: string
  text_hash?: string
  openai_extraction: Record<string, any>
  openai_model?: string
  entities: Entity[]
  approved: boolean
  approved_at?: string
  corrections?: Record<string, any>
}

export interface Entity {
  start: number
  end: number
  label: string
  text?: string
}

export type TipoAnalisi = 'interpello' | 'calendario' | 'generico'

// ============================================
// PATTERNS
// ============================================

export type PatternLabel =
  | 'CLASSE_CONCORSO'
  | 'MECCANOGRAFICO'
  | 'ISTITUTO'
  | 'PROVINCIA'
  | 'MOTIVO'
  | 'EMAIL'
  | 'PHONE'
  | 'DATE'
  | 'LOC'
  | 'ORG'
  | 'PER'

export type PatternSource = 'base' | 'trained' | 'manual'

export interface Pattern {
  id: string
  label: PatternLabel
  pattern: string
  source: PatternSource
  description?: string
  created_at?: string
  updated_at?: string
}

export interface PatternStats {
  total: number
  by_source: {
    base: number
    trained: number
    manual: number
  }
  by_label: Record<string, number>
}

export interface PatternMatch {
  start: number
  end: number
  text: string
  label: string
}

// ============================================
// BENCHMARK
// ============================================

export type BenchmarkEngine = 'spacy' | 'bert' | 'unified'

export interface BenchmarkMetrics {
  overall: {
    precision: number
    recall: number
    f1_score: number
    correct?: number
    predicted?: number
    actual?: number
  }
  by_field: Record<string, FieldMetrics>
}

export interface FieldMetrics {
  precision: number
  recall: number
  f1_score: number
  true_positives: number
  false_positives: number
  false_negatives: number
}

export interface Benchmark {
  name: string
  timestamp: string
  engine: BenchmarkEngine
  tipo: TipoAnalisi
  email_count: number
  with_ground_truth: number
  without_ground_truth?: number
  testable_percentage?: number
  metrics: BenchmarkMetrics
  model_info?: Record<string, any>
  warning?: string
}

export interface BenchmarkComparison {
  before: Benchmark
  after: Benchmark
  improvement: {
    precision: number
    recall: number
    f1_score: number
  }
  by_field: Record<string, {
    before: FieldMetrics
    after: FieldMetrics
    delta: number
  }>
  recommendation: 'keep' | 'rollback'
}

// ============================================
// ENGINE STATUS
// ============================================

export interface SpacyStatus {
  is_available: boolean
  current_version?: string
  patterns_count: number
  pattern_stats: PatternStats
  last_training?: string
  backup_available: boolean
}

export interface BertStatus {
  is_available: boolean
  is_trained: boolean
  current_model?: BertModelInfo
  available_models: BertModelInfo[]
  models_count: number
  error?: string
}

export interface BertModelInfo {
  version_id: string
  is_base: boolean
  is_current?: boolean
  timestamp?: string
  metrics?: {
    f1: number
    precision: number
    recall: number
  }
  config?: {
    epochs: number
    batch_size: number
    learning_rate: number
  }
}

// ============================================
// TRAINING HISTORY
// ============================================

export interface TrainingVersion {
  version_id: string
  timestamp: string
  type: 'apply' | 'rollback' | 'manual_add' | 'manual_delete'
  patterns_added?: number
  patterns_removed?: number
  total_patterns: number
  samples_used?: number
  status?: string
  pattern_types?: Record<string, number>
}

// ============================================
// ASYNC JOBS
// ============================================

export type JobType = 'analyze_batch' | 'benchmark' | 'bert_training'
export type JobStatus = 'running' | 'completed' | 'failed'

export interface AsyncJob {
  job_id: string
  type: JobType
  status: JobStatus
  progress: number
  message: string
  started_at?: string
  completed_at?: string
  result?: any
  error?: string
}

// ============================================
// TRAINING CONFIG
// ============================================

export interface BertTrainConfig {
  epochs: number
  batch_size: number
  learning_rate: number
}

export const DEFAULT_BERT_CONFIG: BertTrainConfig = {
  epochs: 3,
  batch_size: 8,
  learning_rate: 0.00002
}

// ============================================
// API RESPONSES
// ============================================

export interface TrainingStatusResponse {
  openai_available: boolean
  statistics: {
    total_samples: number
    approved_samples: number
    pending_samples: number
    by_type: Record<string, number>
  }
}

export interface ApplyTrainingResponse {
  success: boolean
  patterns_added: number
  total_patterns: number
  version_id: string
  backup_available: boolean
  model_reloaded: boolean
  message?: string
}

export interface RollbackResponse {
  success: boolean
  restored_patterns: number
  backup_timestamp: string
  model_reloaded: boolean
  message?: string
}

// ============================================
// UI STATE
// ============================================

export interface Message {
  type: 'success' | 'error' | 'warning' | 'info'
  text: string
}

export interface FilterState {
  tipo: TipoAnalisi
  search: string
  source?: PatternSource
  label?: PatternLabel
}

// ============================================
// FIELD MAPPINGS
// ============================================

export const INTERPELLO_FIELDS = [
  'classe_concorso',
  'ore_settimanali',
  'meccanografico',
  'istituto',
  'provincia',
  'data_scadenza',
  'email',
  'telefono',
  'referente'
] as const

export const CALENDARIO_FIELDS = [
  'data_inizio',
  'ora_inizio',
  'luogo',
  'modalita',
  'scuola_nome',
  'tipo_riunione',
  'motivo_convocazione',
  'contatto_email'
] as const

export const FIELD_LABELS: Record<string, string> = {
  classe_concorso: 'Classe Concorso',
  ore_settimanali: 'Ore Settimanali',
  meccanografico: 'Cod. Meccanografico',
  istituto: 'Istituto',
  provincia: 'Provincia',
  data_scadenza: 'Scadenza',
  email: 'Email',
  telefono: 'Telefono',
  referente: 'Referente',
  data_inizio: 'Data',
  ora_inizio: 'Ora',
  luogo: 'Luogo',
  modalita: 'Modalit\u00e0',
  scuola_nome: 'Scuola',
  tipo_riunione: 'Tipo Riunione',
  motivo_convocazione: 'Motivo',
  contatto_email: 'Email Contatto'
}
