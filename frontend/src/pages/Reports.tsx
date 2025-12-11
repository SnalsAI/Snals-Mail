import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  Send,
  FileText,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  CheckCircle,
  XCircle,
  AlertCircle,
  Users,
  MapPin,
  X,
  Paperclip,
  Calendar,
  Clock,
  Building,
  RefreshCw,
  SkipForward,
  Edit,
  CalendarX,
  Info,
  Trash2,
  RotateCcw,
  Bug
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { actionsApi, calendarApi, bugsApi } from '../lib/api'
import { format, parseISO } from 'date-fns'
import { it } from 'date-fns/locale'
import toast from 'react-hot-toast'

// Tipo per anomalie calendario
interface CalendarAnomaly {
  tipo: string
  evento_id: number
  titolo: string
  dettaglio: string
  azione_suggerita: string
  email_id?: number
}

interface ForwardItem {
  id: number
  email_id: number
  email_oggetto: string
  email_mittente: string
  email_data: string
  stato: string
  status: string
  zona: string
  scuola: string
  delegati: Array<{ nome: string; email: string }>
  delegati_count: number
  error: string | null
  requires_attention: boolean
  timestamp: string
}

interface ForwardsResponse {
  forwards: ForwardItem[]
  stats: {
    totale: number
    completati: number
    falliti: number
    richiede_attenzione: number
  }
}

interface IssueItem {
  tipo: string
  severity: string
  azione_id: number
  azione_tipo: string
  email_id: number | null
  email_oggetto: string | null
  email_mittente: string | null
  errore: string | null
  messaggio: string | null
  timestamp: string
  dettagli: Record<string, unknown>
}

interface IssuesResponse {
  issues: IssueItem[]
  stats: {
    totale: number
    errori: number
    warning: number
  }
}

interface EmailSummary {
  email_id: number
  oggetto: string
  data: string
  sintesi: string
  categoria: string
}

interface SenderGroup {
  mittente: string
  mittente_completo: string
  count: number
  emails: EmailSummary[]
}

interface SummariesBySenderResponse {
  senders: SenderGroup[]
  stats: {
    totale_mittenti: number
    totale_email: number
  }
}

interface CampoRichiesto {
  campo: string
  label: string
  tipo: string
  obbligatorio: boolean
  mancante: boolean
}

interface AllegatoInfo {
  filename: string
  path: string | null
  testo_estratto: string | null
  has_text: boolean
}

interface IssueDetails {
  azione: {
    id: number
    tipo: string
    stato: string
    errore: string | null
    messaggio: string | null
    timestamp: string | null
  }
  email: {
    id: number
    mittente: string
    oggetto: string
    data: string | null
    corpo: string | null
    corpo_html: string | null
    categoria: string | null
    codice_scuola: string | null
  }
  allegati: AllegatoInfo[]
  dati_estratti: Record<string, unknown>
  campi_richiesti: CampoRichiesto[]
  risoluzione_disponibile: boolean
}

// Spiegazioni dettagliate per ogni tipo di anomalia calendario
const ANOMALY_EXPLANATIONS: Record<string, { title: string; why: string; impact: string; fix: string }> = {
  'stato_inconsistente': {
    title: 'Stato Inconsistente',
    why: 'Il titolo dell\'evento contiene [RINVIATO] o [ANNULLATO], ma lo stato nel database è ancora "confermato". Questo può accadere quando il titolo viene aggiornato manualmente ma lo stato non viene modificato.',
    impact: 'L\'evento potrebbe apparire nel calendario come attivo quando in realtà è stato cancellato o spostato.',
    fix: 'Modifica lo stato dell\'evento in "rinviato" o "annullato" per allinearlo al titolo.'
  },
  'evento_passato_confermato': {
    title: 'Evento Passato Non Aggiornato',
    why: 'L\'evento è già passato ma il suo stato è ancora "confermato". Normalmente, dopo che un evento si è svolto, dovrebbe essere marcato come completato o il suo stato dovrebbe essere aggiornato.',
    impact: 'Questi eventi "fantasma" possono creare confusione nella visualizzazione del calendario e nei report.',
    fix: 'Verifica se l\'evento si è svolto regolarmente. Se sì, puoi eliminarlo o marcarlo come completato. Se non si è svolto, aggiorna lo stato.'
  },
  'sottocategoria_errata': {
    title: 'Email Sorgente Non È Convocazione',
    why: 'L\'evento è stato creato da un\'email la cui sottocategoria NON è "Convocazione" (ad es. è "Comunicazione"). Questo significa che l\'email originale probabilmente non conteneva una vera convocazione a riunione.',
    impact: 'Potrebbero essere stati creati eventi calendario per email che erano semplici comunicazioni informative, non vere convocazioni.',
    fix: 'Verifica l\'email originale. Se non era una convocazione, elimina l\'evento. Se era una convocazione, correggi la sottocategoria dell\'email.'
  },
  'dati_incompleti': {
    title: 'Dati Evento Incompleti',
    why: 'L\'evento è stato salvato senza informazioni essenziali come la data o il luogo. Questo può accadere quando l\'estrazione automatica non riesce a trovare tutti i dati nell\'email.',
    impact: 'L\'evento potrebbe non essere utile senza sapere quando o dove si svolge.',
    fix: 'Completa manualmente i dati mancanti (data, ora, luogo) controllando l\'email originale.'
  }
}

export default function Reports() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [days, setDays] = useState(7)
  const [activeTab, setActiveTab] = useState<'issues' | 'delegati' | 'forwards' | 'summaries' | 'calendario'>('issues')
  const [expandedSenders, setExpandedSenders] = useState<string[]>([])
  const [expandedComuni, setExpandedComuni] = useState<string[]>([])
  const [selectedIssueId, setSelectedIssueId] = useState<number | null>(null)
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [showAllegato, setShowAllegato] = useState<string | null>(null)
  const [expandedAnomaly, setExpandedAnomaly] = useState<string | null>(null)

  // Query per anomalie
  const { data: issuesData, isLoading: issuesLoading } = useQuery<IssuesResponse>({
    queryKey: ['issues-report', days],
    queryFn: () => actionsApi.getIssuesReport(days).then(res => res.data),
  })

  // Query per dettagli anomalia selezionata
  const { data: issueDetails, isLoading: detailsLoading } = useQuery<IssueDetails>({
    queryKey: ['issue-details', selectedIssueId],
    queryFn: () => actionsApi.getIssueDetails(selectedIssueId!).then(res => res.data),
    enabled: !!selectedIssueId,
  })

  // Mutation per risolvere anomalia
  const resolveMutation = useMutation({
    mutationFn: ({ azioneId, data }: { azioneId: number; data: Record<string, unknown> }) =>
      actionsApi.resolveIssue(azioneId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issues-report'] })
      setSelectedIssueId(null)
      setFormData({})
    },
  })

  // Query per inoltri
  const { data: forwardsData, isLoading: forwardsLoading } = useQuery<ForwardsResponse>({
    queryKey: ['forwards-report', days],
    queryFn: () => actionsApi.getForwardsReport(days).then(res => res.data),
    enabled: activeTab === 'forwards' || activeTab === 'issues',
  })

  // Query per sintesi per mittente
  const { data: summariesData, isLoading: summariesLoading } = useQuery<SummariesBySenderResponse>({
    queryKey: ['summaries-by-sender', days],
    queryFn: () => actionsApi.getSummariesBySender(days).then(res => res.data),
    enabled: activeTab === 'summaries',
  })

  // Query per anomalie calendario
  const { data: calendarAnomaliesData, isLoading: calendarAnomaliesLoading } = useQuery({
    queryKey: ['calendar-anomalies'],
    queryFn: () => calendarApi.getAnomalies().then(res => res.data),
    enabled: activeTab === 'calendario',
  })

  const calendarAnomalies: CalendarAnomaly[] = calendarAnomaliesData?.anomalie || []
  const calendarAnomaliesStats = {
    totale: calendarAnomaliesData?.totale_anomalie || 0,
    per_tipo: calendarAnomaliesData?.per_tipo || {}
  }

  // Mutation per eliminare evento calendario
  const deleteEventMutation = useMutation({
    mutationFn: (eventId: number) => calendarApi.delete(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar-anomalies'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success('Evento eliminato con successo')
    },
    onError: () => {
      toast.error('Errore nell\'eliminazione dell\'evento')
    }
  })

  // Mutation per aggiornare stato evento
  const updateEventMutation = useMutation({
    mutationFn: ({ eventId, data }: { eventId: number; data: Record<string, unknown> }) =>
      calendarApi.update(eventId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar-anomalies'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success('Evento aggiornato con successo')
    },
    onError: () => {
      toast.error('Errore nell\'aggiornamento dell\'evento')
    }
  })

  const handleDeleteEvent = (eventId: number, titolo: string) => {
    if (confirm(`Sei sicuro di voler eliminare l'evento "${titolo}"?`)) {
      deleteEventMutation.mutate(eventId)
    }
  }

  const handleUpdateEventStatus = (eventId: number, newStatus: string) => {
    updateEventMutation.mutate({ eventId, data: { stato: newStatus } })
  }

  // Mutation per creare bug da anomalia
  const createBugMutation = useMutation({
    mutationFn: (data: { descrizione: string; pagina: string; email_id?: number }) =>
      bugsApi.create(data),
    onSuccess: () => {
      toast.success('Bug creato con successo')
    },
    onError: () => {
      toast.error('Errore nella creazione del bug')
    }
  })

  const handleCreateBugFromAnomaly = (anomaly: CalendarAnomaly) => {
    const descrizione = `[Anomalia Calendario] ${anomaly.tipo.replace(/_/g, ' ')}\n\nEvento: ${anomaly.titolo}\nDettaglio: ${anomaly.dettaglio}\nAzione suggerita: ${anomaly.azione_suggerita}`
    createBugMutation.mutate({
      descrizione,
      pagina: '/reports',
      email_id: anomaly.email_id
    })
  }

  // Mutation per risolvere anomalie automaticamente
  const resolveAnomaliesAutoMutation = useMutation({
    mutationFn: () => calendarApi.resolveAnomaliesAuto(),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['calendar-anomalies'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      const totale = res.data.totale || 0
      toast.success(`${totale} anomalie risolte automaticamente`)
    },
    onError: () => {
      toast.error('Errore nella risoluzione automatica')
    }
  })

  const handleResolveAllAnomalies = () => {
    if (confirm('Vuoi risolvere automaticamente tutte le anomalie?\n\n• Eventi passati → completati\n• Stati inconsistenti → corretti')) {
      resolveAnomaliesAutoMutation.mutate()
    }
  }

  const toggleSender = (mittente: string) => {
    setExpandedSenders(prev =>
      prev.includes(mittente)
        ? prev.filter(m => m !== mittente)
        : [...prev, mittente]
    )
  }

  const toggleComune = (comune: string) => {
    setExpandedComuni(prev =>
      prev.includes(comune)
        ? prev.filter(c => c !== comune)
        : [...prev, comune]
    )
  }

  // Separa issues normali da INOLTRA_DELEGATI_ZONA
  const delegatiIssues = issuesData?.issues.filter(i => i.azione_tipo === 'INOLTRA_DELEGATI_ZONA') || []
  const otherIssues = issuesData?.issues.filter(i => i.azione_tipo !== 'INOLTRA_DELEGATI_ZONA') || []

  // Raggruppa delegati issues per comune
  const delegatiByComune = delegatiIssues.reduce((acc, issue) => {
    const comune = (issue.dettagli as { comune?: string })?.comune || 'Sconosciuto'
    if (!acc[comune]) {
      acc[comune] = []
    }
    acc[comune].push(issue)
    return acc
  }, {} as Record<string, IssueItem[]>)

  const formatDate = (dateStr: string) => {
    try {
      return format(parseISO(dateStr), 'd MMM HH:mm', { locale: it })
    } catch {
      return dateStr
    }
  }

  const hasIssues = otherIssues.length > 0
  const hasDelegatiIssues = delegatiIssues.length > 0

  // Inizializza form quando si caricano i dettagli
  const initFormFromDetails = (details: IssueDetails) => {
    const initial: Record<string, string> = {}
    details.campi_richiesti.forEach(campo => {
      const valore = details.dati_estratti[campo.campo]
      if (valore !== null && valore !== undefined) {
        initial[campo.campo] = String(valore)
      }
    })
    setFormData(initial)
  }

  // Apri modal per risolvere anomalia
  const openIssueModal = (azioneId: number) => {
    setSelectedIssueId(azioneId)
    setFormData({})
  }

  // Gestisci submit form
  const handleResolve = () => {
    if (!selectedIssueId || !issueDetails) return
    resolveMutation.mutate({
      azioneId: selectedIssueId,
      data: formData,
    })
  }

  // Gestisci skip
  const handleSkip = () => {
    if (!selectedIssueId) return
    resolveMutation.mutate({
      azioneId: selectedIssueId,
      data: { azione: 'skip' },
    })
  }

  // Gestisci retry
  const handleRetry = () => {
    if (!selectedIssueId) return
    resolveMutation.mutate({
      azioneId: selectedIssueId,
      data: { azione: 'retry' },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Report Attività</h1>
          <p className="mt-1 text-sm text-gray-500 hidden sm:block">
            Inoltri, anomalie e sintesi email
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Periodo:</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="input-field w-auto"
          >
            <option value={7}>Ultimi 7 giorni</option>
            <option value={14}>Ultimi 14 giorni</option>
            <option value={30}>Ultimo mese</option>
          </select>
        </div>
      </div>

      {/* Alert anomalie */}
      {(hasIssues || hasDelegatiIssues) && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-red-800">
              {otherIssues.length + delegatiIssues.length} problemi richiedono attenzione
            </h3>
            <p className="text-sm text-red-600 mt-1">
              {otherIssues.length} anomalie, {delegatiIssues.length} inoltri delegati
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex rounded-lg border border-gray-300 overflow-hidden w-fit flex-wrap">
        <button
          onClick={() => setActiveTab('issues')}
          className={`px-4 py-2 text-sm font-medium flex items-center gap-2 ${
            activeTab === 'issues'
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          <AlertCircle className="w-4 h-4" />
          Anomalie
          {hasIssues && (
            <span className={`px-1.5 py-0.5 text-xs rounded-full ${
              activeTab === 'issues' ? 'bg-white/20' : 'bg-red-100 text-red-700'
            }`}>
              {otherIssues.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('delegati')}
          className={`px-4 py-2 text-sm font-medium border-l border-gray-300 flex items-center gap-2 ${
            activeTab === 'delegati'
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          <Users className="w-4 h-4" />
          Delegati Zona
          {hasDelegatiIssues && (
            <span className={`px-1.5 py-0.5 text-xs rounded-full ${
              activeTab === 'delegati' ? 'bg-white/20' : 'bg-yellow-100 text-yellow-700'
            }`}>
              {delegatiIssues.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('forwards')}
          className={`px-4 py-2 text-sm font-medium border-l border-gray-300 flex items-center gap-2 ${
            activeTab === 'forwards'
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          <Send className="w-4 h-4" />
          Inoltri
        </button>
        <button
          onClick={() => setActiveTab('summaries')}
          className={`px-4 py-2 text-sm font-medium border-l border-gray-300 flex items-center gap-2 ${
            activeTab === 'summaries'
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          <FileText className="w-4 h-4" />
          Sintesi
        </button>
        <button
          onClick={() => setActiveTab('calendario')}
          className={`px-4 py-2 text-sm font-medium border-l border-gray-300 flex items-center gap-2 ${
            activeTab === 'calendario'
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          <CalendarX className="w-4 h-4" />
          Calendario
          {calendarAnomaliesStats.totale > 0 && (
            <span className={`px-1.5 py-0.5 text-xs rounded-full ${
              activeTab === 'calendario' ? 'bg-white/20' : 'bg-orange-100 text-orange-700'
            }`}>
              {calendarAnomaliesStats.totale}
            </span>
          )}
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'issues' && (
        issuesLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <div className="space-y-4">
            {otherIssues.length > 0 ? (
              otherIssues.map((issue, idx) => (
                <div
                  key={`other-${issue.azione_id}-${issue.tipo}-${idx}`}
                  className={`card p-4 border-l-4 cursor-pointer hover:shadow-md transition-shadow ${
                    issue.severity === 'error'
                      ? 'border-l-red-500 bg-red-50/50'
                      : 'border-l-yellow-500 bg-yellow-50/50'
                  }`}
                  onClick={() => openIssueModal(issue.azione_id)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {issue.severity === 'error' ? (
                          <XCircle className="w-4 h-4 text-red-600" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-yellow-600" />
                        )}
                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                          issue.severity === 'error'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          {issue.azione_tipo}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatDate(issue.timestamp)}
                        </span>
                      </div>

                      {issue.email_oggetto && (
                        <h4 className="font-medium text-gray-900 text-sm mb-1 line-clamp-1">
                          {issue.email_oggetto}
                        </h4>
                      )}

                      {issue.messaggio && (
                        <p className="text-sm text-gray-700 mb-1">
                          {issue.messaggio}
                        </p>
                      )}

                      {issue.errore && !issue.messaggio && (
                        <p className="text-sm text-red-600">
                          {issue.errore}
                        </p>
                      )}

                      {issue.dettagli && typeof issue.dettagli === 'object' && Object.keys(issue.dettagli).length > 0 && (
                        <div className="mt-2 text-xs text-gray-500 bg-gray-100 rounded p-2">
                          {(issue.dettagli as { nome?: string; comune?: string }).nome && (
                            <span>Scuola: {(issue.dettagli as { nome?: string }).nome}</span>
                          )}
                          {(issue.dettagli as { comune?: string }).comune && (
                            <span className="ml-2">Comune: {(issue.dettagli as { comune?: string }).comune}</span>
                          )}
                        </div>
                      )}
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        issue.email_id && navigate(`/emails/${issue.email_id}`)
                      }}
                      className="text-gray-400 hover:text-primary-600"
                      title="Vai all'email"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="card text-center py-12">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <p className="text-gray-500">Nessuna anomalia rilevata</p>
              </div>
            )}
          </div>
        )
      )}

      {/* Tab Delegati Zona - raggruppati per comune */}
      {activeTab === 'delegati' && (
        issuesLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              {delegatiIssues.length} inoltri falliti in {Object.keys(delegatiByComune).length} comuni
            </p>

            {Object.keys(delegatiByComune).length > 0 ? (
              Object.entries(delegatiByComune)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([comune, issues]) => {
                  const isExpanded = expandedComuni.includes(comune)
                  return (
                    <div key={comune} className="card">
                      <button
                        onClick={() => toggleComune(comune)}
                        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 rounded-lg transition-colors"
                      >
                        <div className="flex items-center gap-3 text-left">
                          <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center">
                            <MapPin className="w-5 h-5 text-yellow-700" />
                          </div>
                          <div>
                            <h3 className="font-medium text-gray-900">{comune}</h3>
                            <p className="text-xs text-gray-500">{issues.length} inoltri falliti</p>
                          </div>
                        </div>
                        {isExpanded ? (
                          <ChevronUp className="w-5 h-5 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-gray-400" />
                        )}
                      </button>

                      {isExpanded && (
                        <div className="px-4 pb-4 border-t border-gray-100 mt-2 pt-4 space-y-3">
                          {issues.map((issue, idx) => (
                            <div
                              key={`${issue.azione_id}-${issue.tipo}-${idx}`}
                              className="p-3 bg-yellow-50 rounded-lg cursor-pointer hover:bg-yellow-100 border-l-4 border-yellow-400"
                              onClick={() => openIssueModal(issue.azione_id)}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs text-gray-500">
                                  {formatDate(issue.timestamp)}
                                </span>
                                {(issue.dettagli as { nome?: string })?.nome && (
                                  <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded flex items-center gap-1">
                                    <Building className="w-3 h-3" />
                                    {(issue.dettagli as { nome?: string }).nome}
                                  </span>
                                )}
                              </div>
                              <h4 className="font-medium text-gray-900 text-sm mb-1 line-clamp-1">
                                {issue.email_oggetto || 'Oggetto non disponibile'}
                              </h4>
                              {issue.messaggio && (
                                <p className="text-sm text-yellow-700">
                                  {issue.messaggio}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })
            ) : (
              <div className="card text-center py-12">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <p className="text-gray-500">Nessun problema con inoltri delegati</p>
              </div>
            )}
          </div>
        )
      )}

      {activeTab === 'forwards' && (
        forwardsLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="card p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">{forwardsData?.stats.totale || 0}</p>
                <p className="text-xs text-gray-500">Totale inoltri</p>
              </div>
              <div className="card p-4 text-center">
                <p className="text-2xl font-bold text-green-600">{forwardsData?.stats.completati || 0}</p>
                <p className="text-xs text-gray-500">Completati</p>
              </div>
              <div className="card p-4 text-center">
                <p className="text-2xl font-bold text-red-600">{forwardsData?.stats.falliti || 0}</p>
                <p className="text-xs text-gray-500">Falliti</p>
              </div>
              <div className="card p-4 text-center">
                <p className="text-2xl font-bold text-yellow-600">{forwardsData?.stats.richiede_attenzione || 0}</p>
                <p className="text-xs text-gray-500">Da verificare</p>
              </div>
            </div>

            {/* Separazione USR/USP vs Scuole */}
            {(() => {
              const isUsrUsp = (mittente: string) => {
                const m = mittente?.toLowerCase() || ''
                return m.includes('usp') || m.includes('usr') || m.includes('atp') || m.includes('ufficio scolastico')
              }
              const usrUspForwards = forwardsData?.forwards?.filter(f => isUsrUsp(f.email_mittente)) || []
              const schoolForwards = forwardsData?.forwards?.filter(f => !isUsrUsp(f.email_mittente)) || []

              const renderForwardItem = (fwd: ForwardItem) => (
                <div
                  key={fwd.id}
                  className={`p-3 bg-gray-50 rounded-lg ${fwd.requires_attention ? 'border-l-4 border-l-yellow-500' : ''}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        {fwd.stato === 'COMPLETATA' ? (
                          <CheckCircle className="w-4 h-4 text-green-600" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-600" />
                        )}
                        <span className="text-xs text-gray-500">{formatDate(fwd.timestamp)}</span>
                        {fwd.zona && (
                          <span className="flex items-center gap-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                            <MapPin className="w-3 h-3" />
                            {fwd.zona}
                          </span>
                        )}
                      </div>
                      <h4
                        className="font-medium text-gray-900 text-sm mb-1 line-clamp-1 cursor-pointer hover:text-primary-600"
                        onClick={() => navigate(`/emails/${fwd.email_id}`)}
                      >
                        {fwd.email_oggetto}
                      </h4>
                      {fwd.scuola && (
                        <p className="text-xs text-gray-500 mb-1">Scuola: {fwd.scuola}</p>
                      )}
                      {fwd.delegati && fwd.delegati.length > 0 && (
                        <div className="flex items-center gap-2 text-xs text-gray-600">
                          <Users className="w-3 h-3" />
                          <span>→ {fwd.delegati.map(d => d.nome).join(', ')}</span>
                        </div>
                      )}
                      {fwd.error && fwd.stato === 'FALLITA' && (
                        <p className="text-xs text-red-600 mt-1">{fwd.error}</p>
                      )}
                    </div>
                    <button
                      onClick={() => navigate(`/emails/${fwd.email_id}`)}
                      className="text-gray-400 hover:text-primary-600"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )

              return (
                <>
                  {/* USR/USP Section */}
                  {usrUspForwards.length > 0 && (
                    <div className="card p-4">
                      <h3 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <Building className="w-4 h-4 text-purple-600" />
                        USR / USP / ATP
                        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
                          {usrUspForwards.length}
                        </span>
                      </h3>
                      <div className="space-y-2">
                        {usrUspForwards.map(renderForwardItem)}
                      </div>
                    </div>
                  )}

                  {/* Scuole Section */}
                  {schoolForwards.length > 0 && (
                    <div className="card p-4">
                      <h3 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <Building className="w-4 h-4 text-blue-600" />
                        Scuole
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                          {schoolForwards.length}
                        </span>
                      </h3>
                      <div className="space-y-2">
                        {schoolForwards.map(renderForwardItem)}
                      </div>
                    </div>
                  )}

                  {/* Empty state */}
                  {usrUspForwards.length === 0 && schoolForwards.length === 0 && (
                    <div className="card text-center py-12">
                      <Send className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-500">Nessun inoltro nel periodo selezionato</p>
                    </div>
                  )}
                </>
              )
            })()}
          </div>
        )
      )}

      {activeTab === 'summaries' && (
        summariesLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              {summariesData?.stats.totale_email || 0} email da {summariesData?.stats.totale_mittenti || 0} mittenti
            </p>

            {summariesData?.senders && summariesData.senders.length > 0 ? (
              summariesData.senders.map((sender) => {
                const isExpanded = expandedSenders.includes(sender.mittente)

                return (
                  <div key={sender.mittente} className="card">
                    <button
                      onClick={() => toggleSender(sender.mittente)}
                      className="w-full flex items-center justify-between p-4 hover:bg-gray-50 rounded-lg transition-colors"
                    >
                      <div className="flex items-center gap-3 text-left">
                        <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                          <span className="text-primary-700 font-medium">
                            {sender.mittente.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <h3 className="font-medium text-gray-900">{sender.mittente}</h3>
                          <p className="text-xs text-gray-500">{sender.count} email</p>
                        </div>
                      </div>
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      )}
                    </button>

                    {isExpanded && (
                      <div className="px-4 pb-4 border-t border-gray-100 mt-2 pt-4 space-y-3">
                        {sender.emails.map((email) => (
                          <div
                            key={email.email_id}
                            className="p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100"
                            onClick={() => navigate(`/emails/${email.email_id}`)}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-gray-500">
                                {formatDate(email.data)}
                              </span>
                              {email.categoria && (
                                <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">
                                  {email.categoria}
                                </span>
                              )}
                            </div>
                            <h4 className="font-medium text-gray-900 text-sm mb-1 line-clamp-1">
                              {email.oggetto}
                            </h4>
                            {email.sintesi && (
                              <p className="text-sm text-gray-600 line-clamp-2">
                                {email.sintesi}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })
            ) : (
              <div className="card text-center py-12">
                <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">Nessuna sintesi disponibile per il periodo selezionato</p>
              </div>
            )}
          </div>
        )
      )}

      {/* Tab Calendario Anomalie */}
      {activeTab === 'calendario' && (
        calendarAnomaliesLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Stats per tipo */}
            {calendarAnomaliesStats.totale > 0 && (
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <CalendarX className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-medium text-orange-800">
                      {calendarAnomaliesStats.totale} anomalie negli eventi calendario
                    </h3>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {Object.entries(calendarAnomaliesStats.per_tipo).map(([tipo, count]) => (
                        <span key={tipo} className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                          {ANOMALY_EXPLANATIONS[tipo]?.title || tipo}: {count as number}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Bottone risoluzione automatica */}
            {calendarAnomaliesStats.totale > 0 && (
              <div className="flex justify-end">
                <button
                  onClick={handleResolveAllAnomalies}
                  disabled={resolveAnomaliesAutoMutation.isPending}
                  className="btn btn-primary flex items-center gap-2"
                >
                  <CheckCircle className="w-4 h-4" />
                  {resolveAnomaliesAutoMutation.isPending ? 'Risoluzione in corso...' : 'Risolvi tutte automaticamente'}
                </button>
              </div>
            )}

            {/* Lista anomalie con spiegazioni */}
            {calendarAnomalies.length > 0 ? (
              <div className="space-y-4">
                {calendarAnomalies.map((anomaly) => {
                  const explanation = ANOMALY_EXPLANATIONS[anomaly.tipo]
                  const isExpanded = expandedAnomaly === `${anomaly.evento_id}-${anomaly.tipo}`

                  return (
                    <div
                      key={`${anomaly.evento_id}-${anomaly.tipo}`}
                      className={`card overflow-hidden border-l-4 ${
                        anomaly.tipo === 'stato_inconsistente' || anomaly.tipo === 'sottocategoria_errata'
                          ? 'border-l-red-500'
                          : anomaly.tipo === 'evento_passato_confermato'
                          ? 'border-l-orange-500'
                          : 'border-l-yellow-500'
                      }`}
                    >
                      {/* Header anomalia */}
                      <div className="p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2 flex-wrap">
                              <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                                anomaly.tipo === 'stato_inconsistente' || anomaly.tipo === 'sottocategoria_errata'
                                  ? 'bg-red-100 text-red-700'
                                  : anomaly.tipo === 'evento_passato_confermato'
                                  ? 'bg-orange-100 text-orange-700'
                                  : 'bg-yellow-100 text-yellow-700'
                              }`}>
                                {explanation?.title || anomaly.tipo.replace(/_/g, ' ')}
                              </span>
                            </div>

                            <h4 className="font-medium text-gray-900 mb-1">
                              {anomaly.titolo}
                            </h4>

                            <p className="text-sm text-gray-600 mb-2">
                              {anomaly.dettaglio}
                            </p>

                            <p className="text-xs text-blue-600 italic flex items-center gap-1">
                              <Info className="w-3 h-3" />
                              {anomaly.azione_suggerita}
                            </p>
                          </div>

                          <div className="flex items-center gap-2 flex-shrink-0">
                            <button
                              onClick={() => setExpandedAnomaly(isExpanded ? null : `${anomaly.evento_id}-${anomaly.tipo}`)}
                              className="btn-secondary p-2"
                              title="Perché questa anomalia?"
                            >
                              <Info className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => navigate(`/calendar?edit=${anomaly.evento_id}`)}
                              className="btn-secondary p-2"
                              title="Modifica evento"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            {anomaly.email_id && (
                              <button
                                onClick={() => navigate(`/emails/${anomaly.email_id}`)}
                                className="btn-secondary p-2"
                                title="Vai all'email"
                              >
                                <ExternalLink className="w-4 h-4" />
                              </button>
                            )}
                            <button
                              onClick={() => handleCreateBugFromAnomaly(anomaly)}
                              className="btn-secondary p-2 text-red-600 hover:bg-red-50"
                              title="Crea bug report"
                              disabled={createBugMutation.isPending}
                            >
                              <Bug className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Spiegazione espandibile */}
                      {isExpanded && explanation && (
                        <div className="border-t bg-gray-50 p-4 space-y-3">
                          <div>
                            <h5 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                              <AlertTriangle className="w-4 h-4 text-orange-500" />
                              Perché viene segnalata questa anomalia?
                            </h5>
                            <p className="text-sm text-gray-600 mt-1">
                              {explanation.why}
                            </p>
                          </div>

                          <div>
                            <h5 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                              <XCircle className="w-4 h-4 text-red-500" />
                              Impatto
                            </h5>
                            <p className="text-sm text-gray-600 mt-1">
                              {explanation.impact}
                            </p>
                          </div>

                          <div>
                            <h5 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                              <CheckCircle className="w-4 h-4 text-green-500" />
                              Come risolvere
                            </h5>
                            <p className="text-sm text-gray-600 mt-1">
                              {explanation.fix}
                            </p>
                          </div>

                          {/* Azioni rapide */}
                          <div className="pt-3 border-t border-gray-200">
                            <h5 className="text-sm font-medium text-gray-900 mb-2">
                              Azioni rapide:
                            </h5>
                            <div className="flex flex-wrap gap-2">
                              {/* Per eventi passati: elimina */}
                              {anomaly.tipo === 'evento_passato_confermato' && (
                                <>
                                  <button
                                    onClick={() => handleDeleteEvent(anomaly.evento_id, anomaly.titolo)}
                                    className="btn-danger text-xs px-3 py-1.5 flex items-center gap-1"
                                    disabled={deleteEventMutation.isPending}
                                  >
                                    <Trash2 className="w-3 h-3" />
                                    Elimina evento
                                  </button>
                                  <button
                                    onClick={() => handleUpdateEventStatus(anomaly.evento_id, 'completato')}
                                    className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1"
                                    disabled={updateEventMutation.isPending}
                                  >
                                    <CheckCircle className="w-3 h-3" />
                                    Marca completato
                                  </button>
                                </>
                              )}

                              {/* Per stato inconsistente: aggiorna stato */}
                              {anomaly.tipo === 'stato_inconsistente' && (
                                <>
                                  <button
                                    onClick={() => handleUpdateEventStatus(anomaly.evento_id, 'rinviato')}
                                    className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1"
                                    disabled={updateEventMutation.isPending}
                                  >
                                    <RotateCcw className="w-3 h-3" />
                                    Marca rinviato
                                  </button>
                                  <button
                                    onClick={() => handleUpdateEventStatus(anomaly.evento_id, 'annullato')}
                                    className="btn-danger text-xs px-3 py-1.5 flex items-center gap-1"
                                    disabled={updateEventMutation.isPending}
                                  >
                                    <XCircle className="w-3 h-3" />
                                    Marca annullato
                                  </button>
                                </>
                              )}

                              {/* Per sottocategoria errata: elimina o vai all'email */}
                              {anomaly.tipo === 'sottocategoria_errata' && (
                                <>
                                  <button
                                    onClick={() => handleDeleteEvent(anomaly.evento_id, anomaly.titolo)}
                                    className="btn-danger text-xs px-3 py-1.5 flex items-center gap-1"
                                    disabled={deleteEventMutation.isPending}
                                  >
                                    <Trash2 className="w-3 h-3" />
                                    Elimina evento
                                  </button>
                                  {anomaly.email_id && (
                                    <button
                                      onClick={() => navigate(`/emails/${anomaly.email_id}`)}
                                      className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1"
                                    >
                                      <ExternalLink className="w-3 h-3" />
                                      Correggi sottocategoria email
                                    </button>
                                  )}
                                </>
                              )}

                              {/* Per dati incompleti: modifica */}
                              {anomaly.tipo === 'dati_incompleti' && (
                                <button
                                  onClick={() => navigate(`/calendar?edit=${anomaly.evento_id}`)}
                                  className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1"
                                >
                                  <Edit className="w-3 h-3" />
                                  Completa dati evento
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="card text-center py-12">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <p className="text-gray-500">Nessuna anomalia calendario rilevata</p>
                <p className="text-sm text-gray-400 mt-1">Tutti gli eventi sono coerenti e aggiornati</p>
              </div>
            )}
          </div>
        )
      )}

      {/* Modal risoluzione anomalia */}
      {selectedIssueId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="px-6 py-4 border-b flex items-center justify-between bg-gray-50">
              <h2 className="text-lg font-semibold text-gray-900">
                Risolvi Anomalia
              </h2>
              <button
                onClick={() => {
                  setSelectedIssueId(null)
                  setFormData({})
                  setShowAllegato(null)
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-6">
              {detailsLoading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
                </div>
              ) : issueDetails ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Colonna sinistra: Email */}
                  <div className="space-y-4">
                    <h3 className="font-medium text-gray-900 flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Email Originale
                    </h3>

                    <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                      <div>
                        <span className="text-xs text-gray-500">Da:</span>
                        <p className="text-sm font-medium">{issueDetails.email.mittente}</p>
                      </div>
                      <div>
                        <span className="text-xs text-gray-500">Oggetto:</span>
                        <p className="text-sm font-medium">{issueDetails.email.oggetto}</p>
                      </div>
                      {issueDetails.email.data && (
                        <div>
                          <span className="text-xs text-gray-500">Data:</span>
                          <p className="text-sm">{formatDate(issueDetails.email.data)}</p>
                        </div>
                      )}
                    </div>

                    {/* Corpo email */}
                    <div className="bg-white border rounded-lg p-4 max-h-64 overflow-auto">
                      <span className="text-xs text-gray-500 block mb-2">Contenuto:</span>
                      {issueDetails.email.corpo_html ? (
                        <div
                          className="text-sm prose prose-sm max-w-none"
                          dangerouslySetInnerHTML={{ __html: issueDetails.email.corpo_html }}
                        />
                      ) : (
                        <pre className="text-sm whitespace-pre-wrap font-sans">
                          {issueDetails.email.corpo || 'Nessun contenuto'}
                        </pre>
                      )}
                    </div>

                    {/* Allegati - solo testo estratto */}
                    {issueDetails.allegati.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                          <Paperclip className="w-4 h-4" />
                          Allegati ({issueDetails.allegati.length})
                        </h4>
                        <div className="space-y-2">
                          {issueDetails.allegati.map((allegato, idx) => (
                            <div key={idx} className="border rounded-lg overflow-hidden">
                              <button
                                onClick={() => allegato.has_text && setShowAllegato(
                                  showAllegato === allegato.filename ? null : allegato.filename
                                )}
                                className={`w-full p-2 bg-gray-100 flex items-center justify-between gap-2 text-left ${allegato.has_text ? 'hover:bg-gray-200 cursor-pointer' : ''}`}
                              >
                                <span className="text-sm truncate flex-1">{allegato.filename}</span>
                                {allegato.has_text && (
                                  <span className="text-xs text-primary-600">
                                    {showAllegato === allegato.filename ? '▲ Nascondi' : '▼ Mostra testo'}
                                  </span>
                                )}
                              </button>
                              {/* Testo estratto */}
                              {showAllegato === allegato.filename && allegato.testo_estratto && (
                                <div className="p-3 bg-blue-50 border-t max-h-64 overflow-auto">
                                  <pre className="text-sm whitespace-pre-wrap font-sans text-gray-800">
                                    {allegato.testo_estratto}
                                  </pre>
                                </div>
                              )}
                              {showAllegato === allegato.filename && !allegato.testo_estratto && (
                                <div className="p-3 bg-gray-50 border-t text-sm text-gray-500 italic">
                                  Nessun testo estratto disponibile
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Colonna destra: Form risoluzione */}
                  <div className="space-y-4">
                    <h3 className="font-medium text-gray-900 flex items-center gap-2">
                      {issueDetails.azione.tipo === 'EVENTO_CALENDARIO' && <Calendar className="w-4 h-4" />}
                      {(issueDetails.azione.tipo === 'INOLTRA' || issueDetails.azione.tipo === 'INOLTRA_DELEGATI_ZONA') && <Send className="w-4 h-4" />}
                      {issueDetails.azione.tipo === 'BOZZA_RISPOSTA' && <FileText className="w-4 h-4" />}
                      {issueDetails.azione.tipo === 'EVENTO_CALENDARIO' ? 'Crea Evento' :
                       (issueDetails.azione.tipo === 'INOLTRA' || issueDetails.azione.tipo === 'INOLTRA_DELEGATI_ZONA') ? 'Problema Inoltro' :
                       'Risoluzione'}
                    </h3>

                    {/* Info errore */}
                    {(issueDetails.azione.errore || issueDetails.azione.messaggio) && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                        <p className="text-sm text-red-700">
                          {issueDetails.azione.messaggio || issueDetails.azione.errore}
                        </p>
                      </div>
                    )}

                    {/* Sezione speciale per INOLTRA_DELEGATI_ZONA */}
                    {(issueDetails.azione.tipo === 'INOLTRA' || issueDetails.azione.tipo === 'INOLTRA_DELEGATI_ZONA') && (
                      <div className="space-y-3">
                        {/* Info scuola/zona */}
                        {issueDetails.dati_estratti && (
                          <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                            {(issueDetails.dati_estratti as Record<string, unknown>).scuola && (
                              <div className="flex items-center gap-2">
                                <Building className="w-4 h-4 text-gray-500" />
                                <span className="text-sm">
                                  <strong>Scuola:</strong> {String((issueDetails.dati_estratti as Record<string, unknown>).scuola)}
                                </span>
                              </div>
                            )}
                            {(issueDetails.dati_estratti as Record<string, unknown>).zona && (
                              <div className="flex items-center gap-2">
                                <MapPin className="w-4 h-4 text-gray-500" />
                                <span className="text-sm">
                                  <strong>Zona:</strong> {String((issueDetails.dati_estratti as Record<string, unknown>).zona)}
                                </span>
                              </div>
                            )}
                          </div>
                        )}

                        <p className="text-sm text-gray-600">
                          L'inoltro automatico è fallito. Puoi:
                        </p>
                        <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                          <li>Saltare questo inoltro se non necessario</li>
                          <li>Inoltrare manualmente dall'email originale</li>
                        </ul>
                      </div>
                    )}

                    {/* Form campi per EVENTO_CALENDARIO */}
                    {issueDetails.azione.tipo === 'EVENTO_CALENDARIO' && issueDetails.campi_richiesti.length > 0 && (
                      <div className="space-y-4">
                        {issueDetails.campi_richiesti.map((campo) => (
                          <div key={campo.campo}>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              {campo.label}
                              {campo.obbligatorio && <span className="text-red-500 ml-1">*</span>}
                              {campo.mancante && (
                                <span className="ml-2 text-xs text-yellow-600 bg-yellow-100 px-2 py-0.5 rounded">
                                  Da compilare
                                </span>
                              )}
                            </label>
                            {campo.tipo === 'date' ? (
                              <input
                                type="date"
                                value={formData[campo.campo] || ''}
                                onChange={(e) => setFormData(prev => ({
                                  ...prev,
                                  [campo.campo]: e.target.value
                                }))}
                                className={`input-field ${campo.mancante ? 'border-yellow-400 bg-yellow-50' : ''}`}
                              />
                            ) : campo.tipo === 'time' ? (
                              <input
                                type="time"
                                value={formData[campo.campo] || ''}
                                onChange={(e) => setFormData(prev => ({
                                  ...prev,
                                  [campo.campo]: e.target.value
                                }))}
                                className={`input-field ${campo.mancante ? 'border-yellow-400 bg-yellow-50' : ''}`}
                              />
                            ) : (
                              <input
                                type="text"
                                value={formData[campo.campo] || ''}
                                onChange={(e) => setFormData(prev => ({
                                  ...prev,
                                  [campo.campo]: e.target.value
                                }))}
                                placeholder={`Inserisci ${campo.label.toLowerCase()}`}
                                className={`input-field ${campo.mancante ? 'border-yellow-400 bg-yellow-50' : ''}`}
                              />
                            )}
                          </div>
                        ))}

                        {/* Inizializza form dai dati estratti */}
                        {Object.keys(formData).length === 0 && issueDetails.dati_estratti && (
                          <button
                            onClick={() => initFormFromDetails(issueDetails)}
                            className="text-sm text-primary-600 hover:text-primary-700"
                          >
                            Carica dati estratti automaticamente
                          </button>
                        )}
                      </div>
                    )}

                    {/* Messaggio per BOZZA_RISPOSTA */}
                    {issueDetails.azione.tipo === 'BOZZA_RISPOSTA' && (
                      <div className="text-sm text-gray-500 bg-gray-50 rounded-lg p-4">
                        <p>Per le bozze risposta puoi solo riprovare la generazione o saltarla.</p>
                      </div>
                    )}

                    {/* Dati estratti (info) - solo per EVENTO_CALENDARIO */}
                    {issueDetails.azione.tipo === 'EVENTO_CALENDARIO' && issueDetails.dati_estratti && Object.keys(issueDetails.dati_estratti).length > 0 && (
                      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                        <h4 className="text-xs font-medium text-blue-800 mb-2">Dati estratti automaticamente:</h4>
                        <dl className="text-xs space-y-1">
                          {Object.entries(issueDetails.dati_estratti).map(([key, value]) => (
                            value && (
                              <div key={key} className="flex">
                                <dt className="text-blue-600 w-24">{key}:</dt>
                                <dd className="text-blue-900 flex-1 truncate">
                                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                </dd>
                              </div>
                            )
                          ))}
                        </dl>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-center text-gray-500">Errore nel caricamento dei dettagli</p>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 flex items-center justify-between">
              <div className="flex gap-2">
                {issueDetails?.azione.tipo === 'BOZZA_RISPOSTA' && (
                  <button
                    onClick={handleRetry}
                    disabled={resolveMutation.isPending}
                    className="btn-secondary flex items-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Riprova
                  </button>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setSelectedIssueId(null)
                    setFormData({})
                  }}
                  className="btn-secondary"
                >
                  Chiudi
                </button>

                {/* Salta per inoltri e bozze */}
                {(issueDetails?.azione.tipo === 'INOLTRA' ||
                  issueDetails?.azione.tipo === 'INOLTRA_DELEGATI_ZONA' ||
                  issueDetails?.azione.tipo === 'BOZZA_RISPOSTA') && (
                  <button
                    onClick={handleSkip}
                    disabled={resolveMutation.isPending}
                    className="btn-secondary flex items-center gap-2"
                  >
                    <SkipForward className="w-4 h-4" />
                    Salta
                  </button>
                )}

                {/* Conferma solo per EVENTO_CALENDARIO */}
                {issueDetails?.azione.tipo === 'EVENTO_CALENDARIO' && (
                  <button
                    onClick={handleResolve}
                    disabled={resolveMutation.isPending}
                    className="btn-primary flex items-center gap-2"
                  >
                    {resolveMutation.isPending ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    ) : (
                      <CheckCircle className="w-4 h-4" />
                    )}
                    Crea Evento
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
