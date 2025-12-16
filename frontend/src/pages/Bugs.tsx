import { useState, useEffect, useRef } from 'react'
import {
  Bug,
  RefreshCw,
  Bot,
  AlertCircle,
  CheckCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Trash2,
  ExternalLink,
  Terminal,
  XCircle,
  Loader2,
  PlayCircle,
  StopCircle
} from 'lucide-react'
import { bugsApi } from '../lib/api'

interface BugReport {
  id: number
  descrizione: string
  pagina?: string
  componente?: string
  browser?: string
  viewport?: string
  console_errors?: any[]
  network_errors?: any[]
  email_id?: number
  azione_id?: number
  stato: string
  priorita: string
  note_tecniche?: string
  file_coinvolti?: string[]
  soluzione_proposta?: string
  created_at?: string
  updated_at?: string
  resolved_at?: string
}

interface StreamEvent {
  type: string
  timestamp?: string
  message?: string
  data?: any
  exit_code?: number
  success?: boolean
  prompt?: string
}

const statoColors: Record<string, string> = {
  aperto: 'bg-red-100 text-red-800',
  in_analisi: 'bg-yellow-100 text-yellow-800',
  in_corso: 'bg-blue-100 text-blue-800',
  risolto: 'bg-green-100 text-green-800',
  chiuso: 'bg-gray-100 text-gray-800',
  non_riproducibile: 'bg-purple-100 text-purple-800',
}

const prioritaColors: Record<string, string> = {
  bassa: 'bg-gray-100 text-gray-600',
  media: 'bg-blue-100 text-blue-600',
  alta: 'bg-orange-100 text-orange-600',
  critica: 'bg-red-100 text-red-600',
}

const statoIcons: Record<string, React.ReactNode> = {
  aperto: <AlertCircle className="w-4 h-4" />,
  in_analisi: <Clock className="w-4 h-4" />,
  in_corso: <Loader2 className="w-4 h-4 animate-spin" />,
  risolto: <CheckCircle className="w-4 h-4" />,
  chiuso: <XCircle className="w-4 h-4" />,
}

export default function Bugs() {
  const [bugs, setBugs] = useState<BugReport[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedBug, setExpandedBug] = useState<number | null>(null)
  const [filterStato, setFilterStato] = useState<string>('')
  const [summary, setSummary] = useState<any>(null)

  // AI Fix state
  const [fixingBugId, setFixingBugId] = useState<number | null>(null)
  const [streamOutput, setStreamOutput] = useState<StreamEvent[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const outputRef = useRef<HTMLDivElement>(null)

  // Bulk fix state
  const [isBulkFixing, setIsBulkFixing] = useState(false)
  const [bulkFixProgress, setBulkFixProgress] = useState({ current: 0, total: 0, currentBugId: null as number | null })
  const [bulkFixLog, setBulkFixLog] = useState<string[]>([])
  const bulkFixAbortRef = useRef(false)

  useEffect(() => {
    loadBugs()
    loadSummary()
  }, [filterStato])

  useEffect(() => {
    // Auto-scroll to bottom of output
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [streamOutput])

  const loadBugs = async () => {
    try {
      setLoading(true)
      const params: any = { limit: 100 }
      if (filterStato) params.stato = filterStato
      const response = await bugsApi.getAll(params)
      setBugs(response.data)
    } catch (error) {
      console.error('Errore caricamento bugs:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSummary = async () => {
    try {
      const response = await bugsApi.getSummary()
      setSummary(response.data)
    } catch (error) {
      console.error('Errore caricamento summary:', error)
    }
  }

  const deleteBug = async (id: number) => {
    if (!confirm('Eliminare questo bug report?')) return
    try {
      await bugsApi.delete(id)
      loadBugs()
      loadSummary()
    } catch (error) {
      console.error('Errore eliminazione bug:', error)
    }
  }

  const updateBugStatus = async (id: number, stato: string) => {
    try {
      await bugsApi.update(id, { stato })
      loadBugs()
      loadSummary()
    } catch (error) {
      console.error('Errore aggiornamento stato:', error)
    }
  }

  const startAIFix = async (bugId: number) => {
    setFixingBugId(bugId)
    setStreamOutput([])
    setIsStreaming(true)
    setExpandedBug(bugId)

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

    try {
      const eventSource = new EventSource(`${API_URL}/bugs/${bugId}/fix-stream`)

      eventSource.onmessage = (event) => {
        try {
          const data: StreamEvent = JSON.parse(event.data)
          setStreamOutput(prev => [...prev, data])

          if (data.type === 'done' || data.type === 'complete' || data.type === 'error' || data.type === 'timeout') {
            eventSource.close()
            setIsStreaming(false)
            loadBugs()
            loadSummary()
          }
        } catch (e) {
          console.error('Errore parsing event:', e)
        }
      }

      eventSource.onerror = (error) => {
        console.error('EventSource error:', error)
        eventSource.close()
        setIsStreaming(false)
        setStreamOutput(prev => [...prev, {
          type: 'error',
          message: 'Connessione persa con il server'
        }])
      }
    } catch (error) {
      console.error('Errore avvio fix:', error)
      setIsStreaming(false)
    }
  }

  // Fix a single bug and wait for completion (returns promise) - reserved for bulk fix
  const fixBugAndWait = (bugId: number): Promise<boolean> => {
    void fixBugAndWait // prevent unused warning
    return new Promise((resolve) => {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'
      const eventSource = new EventSource(`${API_URL}/bugs/${bugId}/fix-stream`)

      setBulkFixLog(prev => [...prev, `[Bug #${bugId}] Avvio fix...`])

      eventSource.onmessage = (event) => {
        try {
          const data: StreamEvent = JSON.parse(event.data)

          if (data.message) {
            setBulkFixLog(prev => [...prev, `[Bug #${bugId}] ${data.message}`])
          }

          if (data.type === 'done' || data.type === 'complete') {
            eventSource.close()
            setBulkFixLog(prev => [...prev, `[Bug #${bugId}] ✅ Completato${data.success ? ' con successo' : ''}`])
            resolve(data.success || false)
          } else if (data.type === 'error' || data.type === 'timeout') {
            eventSource.close()
            setBulkFixLog(prev => [...prev, `[Bug #${bugId}] ❌ Errore: ${data.message || 'unknown'}`])
            resolve(false)
          }
        } catch (e) {
          console.error('Errore parsing event:', e)
        }
      }

      eventSource.onerror = () => {
        eventSource.close()
        setBulkFixLog(prev => [...prev, `[Bug #${bugId}] ❌ Connessione persa`])
        resolve(false)
      }
    })
  }

  const startBulkFix = async () => {
    // Get open bugs count
    const openBugs = bugs.filter(b =>
      b.stato !== 'risolto' && b.stato !== 'chiuso' && b.stato !== 'non_riproducibile'
    )

    if (openBugs.length === 0) {
      alert('Nessun bug aperto da risolvere')
      return
    }

    if (!confirm(`Vuoi risolvere ${openBugs.length} bug con AI in un'UNICA sessione? Claude Code leggerà il codebase una sola volta.`)) {
      return
    }

    setIsBulkFixing(true)
    setBulkFixProgress({ current: 0, total: openBugs.length, currentBugId: null })
    setBulkFixLog([`🚀 Avvio sessione unica per ${openBugs.length} bug...`])
    setStreamOutput([])  // Reset output
    bulkFixAbortRef.current = false

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

    try {
      const eventSource = new EventSource(`${API_URL}/bugs/fix-all-stream`)

      eventSource.onmessage = (event) => {
        try {
          const data: StreamEvent = JSON.parse(event.data)

          // Gestisci eventi batch
          if (data.type === 'batch_start') {
            const bugIds = (data as any).bug_ids || []
            setBulkFixProgress({ current: 0, total: bugIds.length, currentBugId: bugIds[0] })
            setBulkFixLog(prev => [...prev, `📋 Bug da risolvere: ${bugIds.join(', ')}`])
          } else if (data.type === 'batch_done') {
            setBulkFixLog(prev => [...prev, `🏁 Sessione completata! Successo: ${(data as any).success ? 'Sì' : 'No'}`])
            eventSource.close()
            setIsBulkFixing(false)
            loadBugs()
            loadSummary()
          } else {
            // Aggiungi all'output stream
            setStreamOutput(prev => [...prev, data])

            // Aggiorna log per eventi importanti
            if (data.type === 'system') {
              setBulkFixLog(prev => [...prev, `🤖 ${data.message}`])
            } else if (data.type === 'assistant' && (data as any).text) {
              const text = (data as any).text as string
              if (text.length < 150) {
                setBulkFixLog(prev => [...prev, `💬 ${text}`])
              }
            } else if (data.type === 'complete') {
              setBulkFixLog(prev => [...prev, `✅ Claude Code terminato (success: ${data.success})`])
            } else if (data.type === 'error') {
              setBulkFixLog(prev => [...prev, `❌ Errore: ${data.message}`])
            }
          }
        } catch (e) {
          console.error('Errore parsing event:', e)
        }
      }

      eventSource.onerror = () => {
        eventSource.close()
        setBulkFixLog(prev => [...prev, '❌ Connessione persa con il server'])
        setIsBulkFixing(false)
        loadBugs()
        loadSummary()
      }

    } catch (error) {
      console.error('Errore avvio bulk fix:', error)
      setBulkFixLog(prev => [...prev, `❌ Errore: ${error}`])
      setIsBulkFixing(false)
    }
  }

  const stopBulkFix = () => {
    bulkFixAbortRef.current = true
    setBulkFixLog(prev => [...prev, '⏹️ Interruzione in corso...'])
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const renderStreamEvent = (event: StreamEvent, index: number) => {
    const typeColors: Record<string, string> = {
      start: 'text-blue-400',
      running: 'text-cyan-400',
      assistant: 'text-green-400',
      tool_result: 'text-cyan-300',
      result: 'text-purple-400',
      system: 'text-gray-400',
      text: 'text-gray-300',
      waiting: 'text-yellow-400',
      complete: 'text-green-500',
      error: 'text-red-400',
      timeout: 'text-orange-400',
      done: 'text-gray-500',
      batch_start: 'text-purple-400',
      batch_done: 'text-green-500',
      stderr: 'text-orange-400',
      db_error: 'text-red-500',
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const evt = event as any

    return (
      <div key={index} className={`font-mono text-sm ${typeColors[event.type] || 'text-gray-300'}`}>
        <span className="text-gray-500">[{event.type}]</span>{' '}
        {/* Batch events */}
        {event.type === 'batch_start' && evt.bug_ids && (
          <span>📋 Bug da risolvere: {evt.bug_ids.join(', ')} ({evt.count} totali)</span>
        )}
        {event.type === 'batch_done' && (
          <span>🏁 Batch completato - {evt.count} bug {evt.success ? '✅' : '❌'}</span>
        )}
        {/* Standard events */}
        {event.message && event.type !== 'batch_start' && event.type !== 'batch_done' && (
          <span>{event.message}</span>
        )}
        {evt.text && <span>{evt.text}</span>}
        {evt.tools && evt.tools.length > 0 && (
          <div className="ml-4 text-xs text-cyan-300">
            {evt.tools.map((t: {tool: string, input: Record<string, unknown>}, i: number) => (
              <div key={i}>🔧 {t.tool}: {JSON.stringify(t.input).slice(0, 100)}...</div>
            ))}
          </div>
        )}
        {evt.results && (
          <div className="ml-4 text-xs text-gray-400">
            {evt.results.map((r: string, i: number) => (
              <div key={i}>→ {r}</div>
            ))}
          </div>
        )}
        {evt.result && <span className="text-purple-300"> {evt.result}</span>}
        {event.success !== undefined && event.type !== 'batch_start' && event.type !== 'batch_done' && (
          <span className={event.success ? 'text-green-500' : 'text-red-500'}>
            {' '}({event.success ? '✓' : '✗'})
          </span>
        )}
        {evt.duration && <span className="text-gray-500 ml-2">({Math.round(evt.duration/1000)}s)</span>}
        {evt.cost && <span className="text-yellow-500 ml-2">${evt.cost.toFixed(4)}</span>}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <Bug className="w-8 h-8 text-red-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Bug Reports</h1>
            <p className="text-sm text-gray-500">Gestione segnalazioni e fix automatici con AI</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {!isBulkFixing ? (
            <button
              onClick={startBulkFix}
              disabled={isStreaming || !summary?.aperti}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-medium hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PlayCircle className="w-5 h-5" />
              Risolvi tutti con AI
              {summary?.aperti > 0 && <span className="bg-white/20 px-2 py-0.5 rounded-full text-xs">{summary.aperti}</span>}
            </button>
          ) : (
            <button
              onClick={stopBulkFix}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700"
            >
              <StopCircle className="w-5 h-5" />
              Interrompi
            </button>
          )}
          <button
            onClick={() => { loadBugs(); loadSummary(); }}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Aggiorna
          </button>
        </div>
      </div>

      {/* Bulk Fix Progress - Sessione Unica */}
      {isBulkFixing && (
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <Bot className="w-6 h-6 text-purple-600 animate-pulse" />
              <span className="font-medium text-purple-900">
                Sessione unica in corso - {bulkFixProgress.total} bug
              </span>
            </div>
            <span className="text-sm text-purple-600 font-medium">
              Claude Code attivo
            </span>
          </div>

          {/* Log compatto */}
          <div className="bg-gray-800 rounded-lg p-3 max-h-32 overflow-y-auto font-mono text-xs mb-3">
            {bulkFixLog.slice(-10).map((log, idx) => (
              <div key={idx} className="text-gray-300">{log}</div>
            ))}
          </div>

          {/* Output completo Claude Code */}
          <details className="group">
            <summary className="cursor-pointer text-sm text-purple-700 hover:text-purple-900 mb-2">
              📺 Mostra output completo Claude Code ({streamOutput.length} eventi)
            </summary>
            <div
              ref={outputRef}
              className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto"
            >
              {streamOutput.length > 0 ? (
                streamOutput.map((event, idx) => renderStreamEvent(event, idx))
              ) : (
                <div className="text-gray-500 text-sm text-center py-4">
                  In attesa di output...
                </div>
              )}
            </div>
          </details>
        </div>
      )}

      {/* Bulk Fix Log (after completion) */}
      {!isBulkFixing && bulkFixLog.length > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-gray-700">Log ultima risoluzione batch</span>
            <button
              onClick={() => setBulkFixLog([])}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Nascondi
            </button>
          </div>
          <div className="bg-gray-900 rounded-lg p-3 max-h-32 overflow-y-auto font-mono text-xs">
            {bulkFixLog.map((log, idx) => (
              <div key={idx} className="text-gray-300">{log}</div>
            ))}
          </div>
        </div>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white p-4 rounded-lg shadow-sm border">
            <div className="text-2xl font-bold text-gray-900">{summary.totale}</div>
            <div className="text-sm text-gray-500">Totali</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-red-200">
            <div className="text-2xl font-bold text-red-600">{summary.aperti}</div>
            <div className="text-sm text-gray-500">Aperti</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-blue-200">
            <div className="text-2xl font-bold text-blue-600">{summary.in_corso}</div>
            <div className="text-sm text-gray-500">In Corso</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-green-200">
            <div className="text-2xl font-bold text-green-600">{summary.risolti}</div>
            <div className="text-sm text-gray-500">Risolti</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-orange-200">
            <div className="text-2xl font-bold text-orange-600">{summary.critici}</div>
            <div className="text-sm text-gray-500">Critici</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <select
          value={filterStato}
          onChange={(e) => setFilterStato(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
        >
          <option value="">Tutti gli stati</option>
          <option value="aperto">Aperti</option>
          <option value="in_analisi">In Analisi</option>
          <option value="in_corso">In Corso</option>
          <option value="risolto">Risolti</option>
          <option value="chiuso">Chiusi</option>
        </select>
      </div>

      {/* Bug List */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-12 text-gray-500">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
            Caricamento...
          </div>
        ) : bugs.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border">
            <Bug className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">Nessun bug report trovato</p>
          </div>
        ) : (
          bugs.map((bug) => (
            <div key={bug.id} className="bg-white rounded-lg shadow-sm border overflow-hidden">
              {/* Bug Header */}
              <div
                className="p-4 cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                onClick={() => setExpandedBug(expandedBug === bug.id ? null : bug.id)}
              >
                <div className="flex items-center gap-4">
                  {expandedBug === bug.id ? (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">#{bug.id}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium flex items-center gap-1 ${statoColors[bug.stato] || 'bg-gray-100'}`}>
                        {statoIcons[bug.stato]}
                        {bug.stato}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${prioritaColors[bug.priorita] || 'bg-gray-100'}`}>
                        {bug.priorita}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1 line-clamp-1">{bug.descrizione}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-gray-400">{formatDate(bug.created_at)}</span>
                  {bug.stato !== 'risolto' && bug.stato !== 'chiuso' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        startAIFix(bug.id)
                      }}
                      disabled={isStreaming}
                      className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg text-sm font-medium hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Bot className="w-4 h-4" />
                      {fixingBugId === bug.id && isStreaming ? 'In corso...' : 'Risolvi con AI'}
                    </button>
                  )}
                </div>
              </div>

              {/* Expanded Content */}
              {expandedBug === bug.id && (
                <div className="border-t border-gray-200">
                  <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Left Column - Bug Details */}
                    <div className="space-y-3">
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase">Descrizione</label>
                        <p className="text-sm text-gray-700 mt-1">{bug.descrizione}</p>
                      </div>

                      {bug.pagina && (
                        <div>
                          <label className="text-xs font-medium text-gray-500 uppercase">Pagina</label>
                          <p className="text-sm text-gray-700 mt-1 flex items-center gap-1">
                            {bug.pagina}
                            <ExternalLink className="w-3 h-3" />
                          </p>
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-4">
                        {bug.viewport && (
                          <div>
                            <label className="text-xs font-medium text-gray-500 uppercase">Viewport</label>
                            <p className="text-sm text-gray-700 mt-1">{bug.viewport}</p>
                          </div>
                        )}
                        {bug.browser && (
                          <div>
                            <label className="text-xs font-medium text-gray-500 uppercase">Browser</label>
                            <p className="text-sm text-gray-700 mt-1 text-xs">{bug.browser.substring(0, 50)}...</p>
                          </div>
                        )}
                      </div>

                      {bug.console_errors && bug.console_errors.length > 0 && (
                        <div>
                          <label className="text-xs font-medium text-gray-500 uppercase">Errori Console</label>
                          <pre className="mt-1 p-2 bg-gray-900 text-red-400 text-xs rounded overflow-x-auto max-h-32">
                            {JSON.stringify(bug.console_errors, null, 2)}
                          </pre>
                        </div>
                      )}

                      {bug.email_id && (
                        <div>
                          <label className="text-xs font-medium text-gray-500 uppercase">Email Correlata</label>
                          <p className="text-sm text-blue-600 mt-1">ID: {bug.email_id}</p>
                        </div>
                      )}

                      {/* Status Change */}
                      <div className="pt-2">
                        <label className="text-xs font-medium text-gray-500 uppercase">Cambia Stato</label>
                        <div className="flex gap-2 mt-2 flex-wrap">
                          {['aperto', 'in_analisi', 'in_corso', 'risolto', 'chiuso'].map((stato) => (
                            <button
                              key={stato}
                              onClick={() => updateBugStatus(bug.id, stato)}
                              className={`px-2 py-1 text-xs rounded ${
                                bug.stato === stato
                                  ? 'bg-primary-600 text-white'
                                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                              }`}
                            >
                              {stato}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Delete Button */}
                      <button
                        onClick={() => deleteBug(bug.id)}
                        className="flex items-center gap-2 text-red-600 hover:text-red-700 text-sm mt-4"
                      >
                        <Trash2 className="w-4 h-4" />
                        Elimina bug report
                      </button>
                    </div>

                    {/* Right Column - AI Output */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Terminal className="w-4 h-4 text-gray-500" />
                        <label className="text-xs font-medium text-gray-500 uppercase">Output Claude Code</label>
                        {fixingBugId === bug.id && isStreaming && (
                          <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                        )}
                      </div>
                      <div
                        ref={fixingBugId === bug.id ? outputRef : null}
                        className="bg-gray-900 rounded-lg p-4 h-80 overflow-y-auto"
                      >
                        {fixingBugId === bug.id && streamOutput.length > 0 ? (
                          streamOutput.map((event, idx) => renderStreamEvent(event, idx))
                        ) : (
                          <div className="text-gray-500 text-sm text-center py-8">
                            {bug.soluzione_proposta ? (
                              <div className="text-left text-gray-300">
                                <p className="text-green-400 mb-2">Soluzione precedente:</p>
                                <p>{bug.soluzione_proposta}</p>
                              </div>
                            ) : (
                              <>
                                <Bot className="w-8 h-8 mx-auto mb-2 text-gray-600" />
                                <p>Clicca "Risolvi con AI" per avviare Claude Code</p>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
