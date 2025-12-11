import { useState, useMemo, Fragment, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Mail, Filter, Search, Clock, ChevronDown, ChevronRight, ChevronLeft, Download, School, Paperclip, RefreshCw, XCircle, MapPin } from 'lucide-react'
import { emailsApi, actionsApi, schoolsApi } from '../lib/api'
import { EmailCategory, EmailStatus } from '../types'
import ProcessLogModal from '../components/ProcessLogModal'
import EmailActionsPanel from '../components/EmailActionsPanel'

const PAGE_SIZE = 25

export default function Emails() {
  const queryClient = useQueryClient()
  const eventSourceRef = useRef<EventSource | null>(null)

  // SSE listener per auto-refresh quando arrivano nuove email
  useEffect(() => {
    const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const eventSource = new EventSource(`${apiBaseUrl}/api/emails/stream`)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'new_emails') {
          console.log(`📬 ${data.count} nuove email (${data.account})`)
          // Refresh della lista email
          queryClient.invalidateQueries({ queryKey: ['emails'] })
        }
      } catch (e) {
        // Ignore parsing errors (heartbeat messages)
      }
    }

    eventSource.onerror = () => {
      // Riconnessione automatica gestita dal browser
      console.log('SSE: riconnessione...')
    }

    return () => {
      eventSource.close()
    }
  }, [queryClient])
  const [currentPage, setCurrentPage] = useState(0)
  const [filters, setFilters] = useState({
    categoriaFilter: '', // formato: "categoria" o "categoria:sottocategoria"
    search: '',
    scuola: '', // codice scuola
    comune: '', // comune della scuola
  })
  const [showLegend, setShowLegend] = useState(false)
  const [processModal, setProcessModal] = useState<{
    isOpen: boolean
    emailId?: number
    log: any[]
    success?: boolean
    error?: string
  }>({
    isOpen: false,
    log: []
  })
  const [expandedEmailId, setExpandedEmailId] = useState<number | null>(null)

  const { data: emailsResponse, isLoading } = useQuery({
    queryKey: ['emails'],
    queryFn: () => emailsApi.getAll({}).then(res => res.data),
  })

  const emails = emailsResponse?.emails || []

  // Load schools for filter
  const { data: schoolsResponse } = useQuery({
    queryKey: ['schools'],
    queryFn: () => schoolsApi.getAll().then(res => res.data),
  })

  const processEmailMutation = useMutation({
    mutationFn: (emailId: number) => actionsApi.processEmail(emailId),
    onSuccess: (response, emailId) => {
      const data = response.data as any
      setProcessModal({
        isOpen: true,
        emailId: emailId,
        log: data.log || [],
        success: data.success,
        error: data.error
      })
      // Refresh emails list
      queryClient.invalidateQueries({ queryKey: ['emails'] })
    },
    onError: (error: any, emailId) => {
      const errorData = error.response?.data
      setProcessModal({
        isOpen: true,
        emailId: emailId,
        log: errorData?.log || [],
        success: false,
        error: errorData?.error || error.message
      })
    }
  })

  const fetchEmailsMutation = useMutation({
    mutationFn: () => emailsApi.fetchManual(),
    onSuccess: (response) => {
      const data = response.data as any
      // Show success message with count
      alert(data.message || 'Email scaricate con successo')
      // Refresh emails list after fetching
      queryClient.invalidateQueries({ queryKey: ['emails'] })
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Errore durante lo scaricamento delle email')
    }
  })

  const handleProcessEmail = (e: React.MouseEvent, emailId: number) => {
    e.preventDefault()
    e.stopPropagation()
    processEmailMutation.mutate(emailId)
  }

  const handleFetchEmails = () => {
    fetchEmailsMutation.mutate()
  }

  const filteredEmails = emails.filter(email => {
    // Exclude spam emails - they are shown in the Spam page
    if (email.categoria === 'spam') return false
    // Exclude PEC receipts - they are shown in the RicevutePEC page
    if (email.categoria === 'ricevuta_pec') return false

    // Search filter
    if (filters.search) {
      const search = filters.search.toLowerCase()
      const matchesSearch = (
        email.oggetto?.toLowerCase().includes(search) ||
        email.mittente?.toLowerCase().includes(search) ||
        email.corpo_testo?.toLowerCase().includes(search)
      )
      if (!matchesSearch) return false
    }

    // Categoria/Sottocategoria filter (unificato)
    if (filters.categoriaFilter) {
      if (filters.categoriaFilter.includes(':')) {
        // Filtro per sottocategoria specifica (formato "categoria:sottocategoria")
        const [cat, sottocat] = filters.categoriaFilter.split(':')
        if (email.categoria !== cat || email.sottocategoria !== sottocat) return false
      } else {
        // Filtro solo per categoria
        if (email.categoria !== filters.categoriaFilter) return false
      }
    }

    // Scuola filter - usa il campo codice_scuola salvato
    if (filters.scuola) {
      if (email.codice_scuola !== filters.scuola) return false
    }

    // Comune filter - filtra per comune della scuola
    if (filters.comune) {
      const school = (schoolsResponse?.schools || []).find((s: any) => s.codice === email.codice_scuola)
      if (!school || school.comune?.toUpperCase() !== filters.comune.toUpperCase()) return false
    }

    return true
  })

  // Reset page when filters change
  const handleFilterChange = (newFilters: typeof filters) => {
    setFilters(newFilters)
    setCurrentPage(0) // Reset to first page when filters change
  }

  // Pagination calculations
  const totalPages = Math.ceil(filteredEmails.length / PAGE_SIZE)
  const paginatedEmails = filteredEmails.slice(
    currentPage * PAGE_SIZE,
    (currentPage + 1) * PAGE_SIZE
  )

  // Build hierarchical category/subcategory structure
  const categoryHierarchy = useMemo(() => {
    const hierarchy: Record<string, string[]> = {}

    emails.forEach(email => {
      if (email.categoria && email.categoria !== 'spam' && email.categoria !== 'ricevuta_pec') {
        if (!hierarchy[email.categoria]) {
          hierarchy[email.categoria] = []
        }
        if (email.sottocategoria && !hierarchy[email.categoria].includes(email.sottocategoria)) {
          hierarchy[email.categoria].push(email.sottocategoria)
        }
      }
    })

    // Sort subcategories
    Object.keys(hierarchy).forEach(cat => {
      hierarchy[cat].sort()
    })

    return hierarchy
  }, [emails])

  // Get unique school codes from emails (usa campo salvato)
  const emailSchoolCodes = Array.from(
    new Set(emails.map(e => e.codice_scuola).filter(Boolean))
  ) as string[]

  // Filter schools that appear in emails
  const availableSchools = (schoolsResponse?.schools || []).filter((school: any) =>
    emailSchoolCodes.includes(school.codice)
  ).sort((a: any, b: any) => a.nome.localeCompare(b.nome))

  // Get unique comuni from available schools
  const availableComuni = useMemo(() => {
    const comuni = new Set<string>()
    availableSchools.forEach((school: any) => {
      if (school.comune) {
        comuni.add(school.comune.toUpperCase())
      }
    })
    return Array.from(comuni).sort()
  }, [availableSchools])

  const getCategoryBadgeColor = (categoria?: string) => {
    switch (categoria) {
      case EmailCategory.CONVOCAZIONE_SCUOLA:
        return 'bg-red-100 text-red-800 border border-red-200'
      case EmailCategory.COMUNICAZIONE_UST_USR:
        return 'bg-purple-100 text-purple-800 border border-purple-200'
      case EmailCategory.COMUNICAZIONE_SCUOLA:
        return 'bg-green-100 text-green-800 border border-green-200'
      case EmailCategory.COMUNICAZIONE_SNALS_CENTRALE:
        return 'bg-blue-100 text-blue-800 border border-blue-200'
      case EmailCategory.SPAM:
        return 'bg-pink-100 text-pink-800 border border-pink-200'
      case EmailCategory.ERRORE_INVIO:
        return 'bg-red-100 text-red-700 border border-red-300'
      case EmailCategory.NOTIFICA_SISTEMA:
        return 'bg-slate-100 text-slate-600 border border-slate-300'
      case EmailCategory.DA_CATEGORIZZARE:
        return 'bg-orange-100 text-orange-800 border-2 border-orange-500 font-bold animate-pulse'
      case EmailCategory.VARIE:
        return 'bg-gray-100 text-gray-800 border border-gray-200'
      default:
        return 'bg-gray-100 text-gray-700 border border-gray-200'
    }
  }

  const getStatusBadgeColor = (stato: string) => {
    switch (stato) {
      case EmailStatus.PROCESSATA:
        return 'badge-success'
      case EmailStatus.INTERPRETATA:
        return 'badge-primary'
      case EmailStatus.CATEGORIZZATA:
        return 'badge-warning'
      case EmailStatus.ERRORE:
        return 'badge-danger'
      default:
        return 'badge-gray'
    }
  }

  // Indica se l'email arriva dall'account PEC
  const isPecAccount = (email: any): boolean => {
    return email.account_type === 'pec'
  }

  const getCategoryLabel = (categoria?: string) => {
    if (!categoria) return '-'
    const labels: Record<string, string> = {
      'comunicazione_scuola': '🏫 Comunicazione Scuola',
      'comunicazione_ust_usr': '🏛️ UST/USR',
      'comunicazione_snals_centrale': '🏢 SNALS Centrale',
      'richiesta_appuntamento': '📅 Richiesta Appuntamento',
      'richiesta_tesseramento': '📝 Richiesta Tesseramento',
      'revoca_sindacale': '📋 Revoca Sindacale',
      'ricevuta_pec': '📨 Ricevuta PEC',
      'fattura': '🧾 Fattura Elettronica',
      'errore_invio': '❌ Errore Invio',
      'spam': '🚫 Spam',
      'info_generiche': 'ℹ️ Info Generiche',
      'varie': '📦 Varie',
      'da_categorizzare': '⚠️ Da categorizzare',
    }
    return labels[categoria] || categoria
  }

  const getActionsSummary = (email: any) => {
    if (!email.azioni || email.azioni.length === 0) return { text: '-', icon: null, color: 'text-gray-400' }

    // Mappa tipi azioni con icone (allineato con le regole)
    const actionIcons: Record<string, string> = {
      // Azioni calendario/importanza
      'EVENTO_CALENDARIO': '📅',
      'SEGNA_IMPORTANTE': '⭐',
      // Azioni contenuto
      'SINTESI': '📝',
      'INDICIZZA_RAG': '🔍',
      'ARCHIVIA': '📁',
      'PARSE_INTERPELLO': '📋',
      // Azioni bozze risposta
      'BOZZA_RISPOSTA': '✉️',
      'BOZZA_APPUNTAMENTO': '🗓️',
      'BOZZA_TESSERAMENTO': '📋',
      // Spam
      'SPAM': '🚫',
      // Legacy (lowercase) - per retrocompatibilità
      'segna_importante': '⭐',
      'archivia': '📁',
      'rispondi': '↩️',
      'inoltra': '↪️',
      'notifica': '🔔',
      'estrai_interpello': '📋',
    }

    // Raggruppa azioni per tipo (solo completate o in corso)
    const actionTypes = email.azioni
      .filter((a: any) => a.stato === 'COMPLETATA' || a.stato === 'IN_PROGRESS')
      .map((a: any) => a.tipo)
      .filter((tipo: string, index: number, self: string[]) => self.indexOf(tipo) === index) // unique

    if (actionTypes.length === 0) {
      const pendingCount = email.azioni.filter((a: any) => a.stato === 'PENDING').length
      if (pendingCount > 0) {
        return { text: `${pendingCount} in attesa`, icon: Clock, color: 'text-yellow-600' }
      }
      const failedCount = email.azioni.filter((a: any) => a.stato === 'FALLITA').length
      if (failedCount > 0) {
        return { text: `${failedCount} fallite`, icon: XCircle, color: 'text-red-600' }
      }
      return { text: '-', icon: null, color: 'text-gray-400' }
    }

    // Mostra icone dei tipi di azioni eseguite
    const icons = actionTypes.map((tipo: string) => actionIcons[tipo] || '✓').join(' ')
    return { text: icons, icon: null, color: 'text-gray-700' }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Email</h1>
          <p className="mt-1 text-sm text-gray-500">
            Gestisci e visualizza tutte le email ricevute
          </p>
        </div>
        <button
          onClick={handleFetchEmails}
          disabled={fetchEmailsMutation.isPending}
          className="px-5 py-2.5 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-lg hover:from-primary-700 hover:to-primary-800 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 whitespace-nowrap shadow-lg shadow-primary-500/30 hover:shadow-xl hover:shadow-primary-500/40 hover:-translate-y-0.5"
        >
          <Download className={`w-4 h-4 ${fetchEmailsMutation.isPending ? 'animate-bounce' : ''}`} />
          <span className="hidden sm:inline font-medium">{fetchEmailsMutation.isPending ? 'Scaricamento...' : 'Scarica Email'}</span>
          <span className="sm:hidden font-medium">{fetchEmailsMutation.isPending ? 'Scaricamento...' : 'Scarica'}</span>
        </button>
      </div>

      {/* Filters */}
      <div className="card bg-gradient-to-br from-white to-gray-50/50 shadow-md">
        <div className="space-y-4">
          {/* First Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Search */}
            <div className="md:col-span-1">
              <label className="label">
                <Search className="w-4 h-4 inline mr-2" />
                Cerca
              </label>
              <input
                type="text"
                className="input"
                placeholder="Oggetto, mittente, contenuto..."
                value={filters.search}
                onChange={(e) => handleFilterChange({ ...filters, search: e.target.value })}
              />
            </div>

            {/* Category/Subcategory Filter (Hierarchical) */}
            <div>
              <label className="label">
                <Filter className="w-4 h-4 inline mr-2" />
                Categoria
              </label>
              <select
                className="input"
                value={filters.categoriaFilter}
                onChange={(e) => handleFilterChange({ ...filters, categoriaFilter: e.target.value })}
              >
                <option value="">Tutte le categorie</option>
                {Object.keys(categoryHierarchy).sort().map((categoria) => (
                  <optgroup key={categoria} label={getCategoryLabel(categoria)}>
                    <option value={categoria}>
                      📁 Tutte: {getCategoryLabel(categoria)}
                    </option>
                    {categoryHierarchy[categoria].map((sottocat) => (
                      <option key={`${categoria}:${sottocat}`} value={`${categoria}:${sottocat}`}>
                        └ {sottocat}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>

          </div>

          {/* Second Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Comune Filter */}
            <div>
              <label className="label">
                <MapPin className="w-4 h-4 inline mr-2" />
                Comune
              </label>
              <select
                className="input"
                value={filters.comune}
                onChange={(e) => handleFilterChange({ ...filters, comune: e.target.value, scuola: '' })}
                disabled={availableComuni.length === 0}
              >
                <option value="">Tutti i comuni</option>
                {availableComuni.map((comune) => (
                  <option key={comune} value={comune}>
                    {comune}
                  </option>
                ))}
              </select>
            </div>

            {/* Scuola Filter */}
            <div className="md:col-span-2">
              <label className="label">
                <School className="w-4 h-4 inline mr-2" />
                Scuola
              </label>
              <select
                className="input"
                value={filters.scuola}
                onChange={(e) => handleFilterChange({ ...filters, scuola: e.target.value })}
                disabled={availableSchools.length === 0}
              >
                <option value="">Tutte le scuole</option>
                {availableSchools
                  .filter((school: any) => !filters.comune || school.comune?.toUpperCase() === filters.comune)
                  .map((school: any) => (
                  <option key={school.codice} value={school.codice}>
                    {school.nome} ({school.comune})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Active Filters Summary */}
          {(filters.search || filters.categoriaFilter || filters.scuola || filters.comune) && (
            <div className="flex items-center justify-between pt-3 border-t border-gray-200">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Filter className="w-4 h-4" />
                <span>
                  {filteredEmails.length} di {emails.length} email
                </span>
              </div>
              <button
                onClick={() => handleFilterChange({
                  categoriaFilter: '',
                  search: '',
                  scuola: '',
                  comune: '',
                })}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Rimuovi tutti i filtri
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Actions Legend */}
      <div className="card bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200">
        <button
          onClick={() => setShowLegend(!showLegend)}
          className="w-full flex items-center justify-between text-sm font-medium text-blue-800"
        >
          <span className="flex items-center gap-2">
            <span className="text-lg">ℹ️</span>
            Legenda Azioni
          </span>
          <ChevronDown className={`w-4 h-4 transition-transform ${showLegend ? 'rotate-180' : ''}`} />
        </button>
        {showLegend && (
          <div className="mt-3 pt-3 border-t border-blue-200 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-lg">📅</span>
              <span className="text-gray-700">Evento Calendario</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-lg">⭐</span>
              <span className="text-gray-700">Importante</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-lg">📝</span>
              <span className="text-gray-700">Sintesi</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-lg">🔍</span>
              <span className="text-gray-700">Indicizzato RAG</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-lg">📁</span>
              <span className="text-gray-700">Archiviata</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-lg">📋</span>
              <span className="text-gray-700">Interpello Estratto</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-lg">✉️</span>
              <span className="text-gray-700">Bozza Risposta</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-lg">🗓️</span>
              <span className="text-gray-700">Bozza Appuntamento</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-lg">🚫</span>
              <span className="text-gray-700">Spam</span>
            </div>
          </div>
        )}
      </div>

      {/* Email Table - Desktop */}
      <div className="hidden lg:block card overflow-hidden p-0 shadow-lg">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
            <p className="mt-4 text-gray-500 font-medium">Caricamento email...</p>
          </div>
        ) : filteredEmails && filteredEmails.length > 0 ? (
          <>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border-b-2 border-primary-200">
                <tr>
                  <th className="px-3 py-3.5 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider w-8"></th>
                  <th className="px-3 py-3.5 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider w-20">ID</th>
                  <th className="px-3 py-3.5 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Mittente</th>
                  <th className="px-3 py-3.5 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Oggetto</th>
                  <th className="px-3 py-3.5 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider w-56">Categoria</th>
                  <th className="px-3 py-3.5 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider w-24">Azioni</th>
                  <th className="px-3 py-3.5 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider w-32 whitespace-nowrap">Data</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {paginatedEmails.map((email) => {
                  const actionsSummary = getActionsSummary(email)
                  const isProcessed = email.stato === 'completata' || email.stato === 'azione_eseguita'
                  const isExpanded = expandedEmailId === email.id

                  return (
                    <Fragment key={email.id}>
                      <tr className={`transition-all duration-150 hover:bg-gradient-to-r hover:from-primary-50 hover:to-transparent border-l-4 ${isProcessed ? 'border-l-green-500' : 'border-l-amber-400'}`}>
                        {/* Expand Button */}
                        <td className="px-2 py-3">
                          <button
                            onClick={() => setExpandedEmailId(isExpanded ? null : email.id)}
                            className="text-gray-400 hover:text-primary-600 transition-colors p-1 rounded hover:bg-primary-50"
                          >
                            {isExpanded ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                          </button>
                        </td>

                        {/* ID */}
                        <td className="px-2 py-3">
                          <div className="flex items-center gap-1">
                            {!isProcessed && (
                              <div className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" title="Da processare"></div>
                            )}
                            <div className="text-xs font-mono text-gray-600 font-semibold">
                              #{email.id}
                            </div>
                            {isPecAccount(email) ? (
                              <span className="text-xs px-1 py-0.5 rounded bg-purple-100 text-purple-700 font-bold" title="Account PEC">
                                PEC
                              </span>
                            ) : (
                              <span className="text-xs px-1 py-0.5 rounded bg-gray-100 text-gray-500" title="Account normale">
                                ✉️
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Mittente */}
                        <td className="px-3 py-3">
                          <div className="text-sm font-medium text-gray-900 truncate max-w-[180px]" title={email.mittente}>
                            <Mail className="w-3 h-3 inline mr-1 text-gray-400" />
                            {email.mittente}
                          </div>
                        </td>

                        {/* Oggetto */}
                        <td className="px-3 py-3">
                          <Link to={`/emails/${email.id}`}>
                            <div className="text-sm text-gray-900 hover:text-primary-600 truncate max-w-[280px] font-medium" title={email.oggetto}>
                              {email.oggetto}
                            </div>
                          </Link>
                          <div className="flex items-center gap-2 mt-1">
                            {!email.revisionata && email.richiede_revisione && (
                              <span className="inline-block text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 font-medium">
                                ⚠️ Revisione
                              </span>
                            )}
                            {email.allegati_nomi && email.allegati_nomi.length > 0 && (
                              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-md bg-gray-100 text-gray-700 border border-gray-300 font-medium" title={email.allegati_nomi.join(', ')}>
                                <Paperclip className="w-3 h-3" />
                                {email.allegati_nomi.length}
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Categoria */}
                        <td className="px-3 py-3">
                          <div className="flex flex-col gap-1">
                            <span className={`text-xs px-2 py-1 rounded-md font-medium inline-flex items-center gap-1 whitespace-nowrap ${getCategoryBadgeColor(email.categoria)}`}>
                              {getCategoryLabel(email.categoria)}
                            </span>
                            {email.sottocategoria && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 whitespace-nowrap">
                                📂 {email.sottocategoria}
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Azioni Summary */}
                        <td className="px-2 py-3 text-center">
                          <div className={`flex items-center justify-center gap-1 text-sm ${actionsSummary.color}`}>
                            {actionsSummary.icon && <actionsSummary.icon className="w-4 h-4" />}
                            <span>{actionsSummary.text}</span>
                          </div>
                        </td>

                        {/* Data */}
                        <td className="px-3 py-3 whitespace-nowrap">
                          <div className="text-xs text-gray-500">
                            {new Date(email.data_ricezione).toLocaleDateString('it-IT', {
                              day: '2-digit',
                              month: '2-digit',
                              year: 'numeric',
                              timeZone: 'Europe/Rome'
                            })}
                            <br />
                            {new Date(email.data_ricezione).toLocaleTimeString('it-IT', {
                              hour: '2-digit',
                              minute: '2-digit',
                              timeZone: 'Europe/Rome'
                            })}
                          </div>
                        </td>
                      </tr>

                      {/* Expanded Row with Actions Panel */}
                      {isExpanded && (
                        <tr className="bg-gradient-to-br from-blue-50/30 via-purple-50/20 to-pink-50/30 border-l-4 border-l-primary-500">
                          <td colSpan={7} className="px-4 py-5">
                            <div className="space-y-4">
                              {/* Email metadata */}
                              <div className="grid grid-cols-2 gap-4 pb-4 border-b-2 border-primary-200">
                                <div className="bg-white/60 backdrop-blur-sm p-3 rounded-lg border border-gray-200">
                                  <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider flex items-center gap-1">
                                    📋 Categoria
                                  </span>
                                  <div className="mt-2 flex flex-col gap-1.5">
                                    <span className={`text-xs px-2.5 py-1 rounded-md font-medium w-fit ${getCategoryBadgeColor(email.categoria)}`}>
                                      {getCategoryLabel(email.categoria)}
                                    </span>
                                    {email.sottocategoria && (
                                      <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200 w-fit">
                                        📂 {email.sottocategoria}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="bg-white/60 backdrop-blur-sm p-3 rounded-lg border border-gray-200">
                                  <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider flex items-center gap-1">
                                    📊 Confidenza
                                  </span>
                                  <div className="mt-2">
                                    <span className="text-2xl font-bold text-primary-600">
                                      {email.confidence_score ? `${(email.confidence_score * 100).toFixed(0)}%` : 'N/A'}
                                    </span>
                                  </div>
                                </div>
                              </div>

                              {/* Email preview */}
                              <div className="bg-white/60 backdrop-blur-sm p-4 rounded-lg border border-gray-200">
                                <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider flex items-center gap-1 mb-2">
                                  📄 Anteprima
                                </span>
                                <p className="text-sm text-gray-700 leading-relaxed">
                                  {email.corpo_testo?.substring(0, 300) || 'Nessun contenuto disponibile'}...
                                </p>
                              </div>

                              {/* Attachment summaries */}
                              {email.allegati_testo && Object.keys(email.allegati_testo).length > 0 && (
                                <div className="bg-white/60 backdrop-blur-sm p-4 rounded-lg border border-gray-200">
                                  <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider flex items-center gap-1 mb-3">
                                    📎 Sintesi Allegati
                                  </span>
                                  <div className="space-y-3">
                                    {Object.entries(email.allegati_testo).map(([filename, text]) => (
                                      <div key={filename} className="border-l-2 border-blue-300 pl-3">
                                        <p className="text-xs font-medium text-gray-900 mb-1">{filename}</p>
                                        <p className="text-xs text-gray-600">
                                          {typeof text === 'string' ? text.substring(0, 200) : ''}
                                          {typeof text === 'string' && text.length > 200 && '...'}
                                        </p>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Reprocess button */}
                              <div className="flex justify-end">
                                <button
                                  onClick={(e) => handleProcessEmail(e, email.id)}
                                  disabled={processEmailMutation.isPending}
                                  className="px-4 py-2 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-lg hover:from-primary-700 hover:to-primary-800 transition-all duration-150 disabled:opacity-50 flex items-center gap-2 font-medium shadow-md shadow-primary-500/30 hover:shadow-lg text-sm"
                                >
                                  <RefreshCw className={`w-4 h-4 ${processEmailMutation.isPending ? 'animate-spin' : ''}`} />
                                  {processEmailMutation.isPending ? 'Elaborazione...' : 'Riprocessa Email'}
                                </button>
                              </div>

                              {/* Actions panel */}
                              <div className="bg-white/60 backdrop-blur-sm p-4 rounded-lg border border-gray-200">
                                <EmailActionsPanel
                                  emailId={email.id}
                                  isExpanded={true}
                                  onToggle={() => {}}
                                />
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls - Desktop */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gradient-to-r from-gray-50 to-white">
              <div className="text-sm text-gray-600">
                Pagina {currentPage + 1} di {totalPages} ({filteredEmails.length} email)
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(0)}
                  disabled={currentPage === 0}
                  className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Prima
                </button>
                <button
                  onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                  disabled={currentPage === 0}
                  className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Precedente
                </button>
                <span className="px-3 py-1.5 text-sm font-semibold text-primary-700 bg-primary-50 border border-primary-200 rounded-md">
                  {currentPage + 1}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={currentPage >= totalPages - 1}
                  className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
                >
                  Successiva
                  <ChevronRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setCurrentPage(totalPages - 1)}
                  disabled={currentPage >= totalPages - 1}
                  className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Ultima
                </button>
              </div>
            </div>
          )}
          </>
        ) : (
          <div className="text-center py-16 bg-gradient-to-br from-gray-50 to-white">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
              <Mail className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-1">Nessuna email trovata</h3>
            <p className="text-gray-500 text-sm">Prova a modificare i filtri o scarica nuove email</p>
          </div>
        )}
      </div>

      {/* Email Cards - Mobile */}
      <div className="lg:hidden space-y-3">
        {isLoading ? (
          <div className="card flex flex-col items-center justify-center py-16 bg-gradient-to-br from-gray-50 to-white">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
            <p className="mt-4 text-gray-500 font-medium">Caricamento email...</p>
          </div>
        ) : filteredEmails && filteredEmails.length > 0 ? (
          <>
          {paginatedEmails.map((email) => {
            const actionsSummary = getActionsSummary(email)
            const isProcessed = email.stato === 'completata' || email.stato === 'azione_eseguita'
            const isExpanded = expandedEmailId === email.id

            return (
              <div key={email.id} className={`card hover:shadow-lg transition-all duration-200 border-l-4 ${isProcessed ? 'border-l-green-500 bg-gradient-to-r from-green-50/30 to-transparent' : 'border-l-amber-400 bg-gradient-to-r from-amber-50/30 to-transparent'}`}>
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {!isProcessed && (
                        <div className="w-2 h-2 bg-amber-400 rounded-full animate-pulse flex-shrink-0" title="Da processare"></div>
                      )}
                      <Link to={`/emails/${email.id}`} className="flex-1 min-w-0">
                        <h3 className="text-sm font-semibold text-gray-900 truncate hover:text-primary-600 transition-colors">
                          {email.oggetto}
                        </h3>
                      </Link>
                    </div>
                    <p className="text-xs text-gray-500 truncate mt-1 flex items-center gap-1">
                      <Mail className="w-3 h-3 text-gray-400" />
                      {email.mittente}
                    </p>
                  </div>
                  <div className="ml-2 flex items-center gap-1 flex-shrink-0">
                    <span className="text-xs font-mono font-semibold text-gray-500">
                      #{email.id}
                    </span>
                    {isPecAccount(email) ? (
                      <span className="text-xs px-1 py-0.5 rounded bg-purple-100 text-purple-700 font-bold" title="Account PEC">
                        PEC
                      </span>
                    ) : (
                      <span className="text-xs px-1 py-0.5 rounded bg-gray-100 text-gray-500" title="Account normale">
                        ✉️
                      </span>
                    )}
                  </div>
                </div>

                {/* Categoria e Sottocategoria */}
                <div className="flex flex-wrap gap-2 mb-3">
                  <span className={`text-xs px-2.5 py-1 rounded-md font-medium ${getCategoryBadgeColor(email.categoria)}`}>
                    {getCategoryLabel(email.categoria)}
                  </span>
                  {email.sottocategoria && (
                    <span className="text-xs px-2.5 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-md font-medium">
                      📂 {email.sottocategoria}
                    </span>
                  )}
                  {!email.revisionata && email.richiede_revisione && (
                    <span className="text-xs px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 border border-amber-200 font-medium">
                      ⚠️ Revisione
                    </span>
                  )}
                </div>

                {/* Info Row */}
                <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
                  <span>
                    {new Date(email.data_ricezione).toLocaleDateString('it-IT', {
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      timeZone: 'Europe/Rome'
                    })}
                  </span>
                  {actionsSummary.icon && (
                    <div className={`flex items-center gap-1 ${actionsSummary.color}`}>
                      <actionsSummary.icon className="w-3 h-3" />
                      <span>{actionsSummary.text}</span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-3 border-t border-gray-200">
                  <button
                    onClick={() => setExpandedEmailId(isExpanded ? null : email.id)}
                    className="flex-1 text-xs px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all duration-150 flex items-center justify-center gap-1 font-medium"
                  >
                    {isExpanded ? (
                      <>
                        <ChevronDown className="w-3.5 h-3.5" />
                        Chiudi
                      </>
                    ) : (
                      <>
                        <ChevronRight className="w-3.5 h-3.5" />
                        Dettagli
                      </>
                    )}
                  </button>
                </div>

                {/* Expanded Actions Panel */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <EmailActionsPanel
                      emailId={email.id}
                      isExpanded={true}
                      onToggle={() => {}}
                    />
                  </div>
                )}
              </div>
            )
          })}

          {/* Pagination Controls - Mobile */}
          {totalPages > 1 && (
            <div className="card bg-gradient-to-r from-gray-50 to-white">
              <div className="flex flex-col gap-3">
                <div className="text-sm text-gray-600 text-center">
                  Pagina {currentPage + 1} di {totalPages} ({filteredEmails.length} email)
                </div>
                <div className="flex items-center justify-center gap-2">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                    disabled={currentPage === 0}
                    className="flex-1 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-1"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Precedente
                  </button>
                  <span className="px-4 py-2 text-sm font-semibold text-primary-700 bg-primary-50 border border-primary-200 rounded-lg">
                    {currentPage + 1}
                  </span>
                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
                    disabled={currentPage >= totalPages - 1}
                    className="flex-1 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-1"
                  >
                    Successiva
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}
          </>
        ) : (
          <div className="card text-center py-16 bg-gradient-to-br from-gray-50 to-white">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
              <Mail className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-1">Nessuna email trovata</h3>
            <p className="text-gray-500 text-sm">Prova a modificare i filtri o scarica nuove email</p>
          </div>
        )}
      </div>

      {/* Process Log Modal */}
      <ProcessLogModal
        isOpen={processModal.isOpen}
        onClose={() => setProcessModal({ isOpen: false, log: [] })}
        log={processModal.log}
        emailId={processModal.emailId}
        success={processModal.success}
        error={processModal.error}
      />
    </div>
  )
}
