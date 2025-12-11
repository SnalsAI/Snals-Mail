import { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import { Bug, RefreshCw, ChevronDown, ChevronUp, CheckCircle, XCircle, AlertCircle, Loader, FileText } from 'lucide-react'
import { debugApi } from '../lib/api'

interface DebugEmail {
  id: number
  oggetto: string
  mittente: string
  data_ricezione: string | null
  stato: string
  categoria: string | null
  sottocategoria: string | null
  categoria_confidence: number | null
  azioni: DebugAzione[]
  interpello: DebugInterpello | null
}

interface DebugAzione {
  id: number
  tipo: string
  stato: string
  dettagli: any
  risultato: any
  errore: string | null
  eseguita_at: string | null
}

interface DebugInterpello {
  id: number
  classe_concorso: string | null
  numero_posti: number | null
  ore_settimanali: number | null
  data_scadenza: string | null
  provincia: string | null
  citta: string | null
  istituto: string | null
  data_fine_contratto: string | null
  metadata_estrazione: any
  stato: string | null
  verificato: boolean | null
}

export default function Debug() {
  const [emails, setEmails] = useState<DebugEmail[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedEmail, setExpandedEmail] = useState<number | null>(null)
  const [reparsing, setReparsing] = useState<number | null>(null)

  // Filtri
  const [filterCategoria, setFilterCategoria] = useState('')
  const [filterConAzioni, setFilterConAzioni] = useState(false)
  const [filterConInterpelli, setFilterConInterpelli] = useState(false)

  useEffect(() => {
    fetchDebugEmails()
  }, [filterCategoria, filterConAzioni, filterConInterpelli])

  const fetchDebugEmails = async () => {
    setLoading(true)
    try {
      const response = await debugApi.getEmails({
        limit: 50,
        skip: 0,
        categoria: filterCategoria || undefined,
        con_azioni: filterConAzioni ? 'true' : undefined,
        con_interpelli: filterConInterpelli ? 'true' : undefined
      })

      setEmails(response.data.emails)
    } catch (error) {
      console.error('Errore caricamento debug emails:', error)
      toast.error('Errore caricamento email')
    } finally {
      setLoading(false)
    }
  }

  const handleReparse = async (interpelloId: number, strategy: string) => {
    setReparsing(interpelloId)
    try {
      await debugApi.reparseInterpello(interpelloId, strategy)
      toast.success(`Interpello ri-parsato con ${strategy}`)

      // Ricarica email per mostrare nuovi dati
      await fetchDebugEmails()
    } catch (error) {
      console.error('Errore re-parsing:', error)
      toast.error('Errore durante re-parsing')
    } finally {
      setReparsing(null)
    }
  }

  const getStatusIcon = (stato: string) => {
    switch (stato) {
      case 'COMPLETATA':
        return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'ERRORE':
        return <XCircle className="w-4 h-4 text-red-600" />
      case 'IN_CORSO':
        return <Loader className="w-4 h-4 text-blue-600 animate-spin" />
      default:
        return <AlertCircle className="w-4 h-4 text-yellow-600" />
    }
  }

  const getStatusColor = (stato: string) => {
    switch (stato) {
      case 'COMPLETATA':
        return 'bg-green-100 text-green-800'
      case 'ERRORE':
        return 'bg-red-100 text-red-800'
      case 'IN_CORSO':
        return 'bg-blue-100 text-blue-800'
      default:
        return 'bg-yellow-100 text-yellow-800'
    }
  }

  const calculateCompletezza = (interp: DebugInterpello | null): number => {
    if (!interp) return 0
    const campiRichiesti = ['classe_concorso', 'ore_settimanali', 'provincia', 'data_scadenza']
    const campiPresenti = campiRichiesti.filter(field => interp[field as keyof DebugInterpello])
    return (campiPresenti.length / campiRichiesti.length) * 100
  }

  const getExtractorInfo = (metadata: any): { extractor: string; color: string; icon: string } => {
    if (!metadata) return { extractor: 'Sconosciuto', color: 'gray', icon: '❓' }

    const strategyFinal = metadata.strategy_final || metadata.reparse_strategy

    // OpenAI (rosso - attenzione ai costi!)
    if (strategyFinal?.includes('openai')) {
      return { extractor: 'OpenAI', color: 'red', icon: '💰' }
    }

    // Ollama/Local LLM (verde - gratis!)
    if (strategyFinal?.includes('ollama') || strategyFinal?.includes('local')) {
      return { extractor: 'Ollama (Local)', color: 'green', icon: '🤖' }
    }

    // Regex validated/corrected (giallo - buono!)
    if (strategyFinal?.includes('regex_validated') || strategyFinal?.includes('regex_corrected') || strategyFinal?.includes('regex_llm')) {
      return { extractor: 'Regex + LLM', color: 'yellow', icon: '⚡' }
    }

    // Regex only (blu - veloce!)
    if (strategyFinal?.includes('regex_only') || strategyFinal === 'regex') {
      return { extractor: 'Regex Only', color: 'blue', icon: '🚀' }
    }

    // Best effort
    if (strategyFinal?.includes('best_effort')) {
      return { extractor: 'Best Effort', color: 'orange', icon: '🔧' }
    }

    return { extractor: strategyFinal || 'Sconosciuto', color: 'gray', icon: '❓' }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bug className="w-8 h-8 text-purple-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Debug & Monitoring</h1>
            <p className="text-sm text-gray-500">Analizza processing email e estrazione dati</p>
          </div>
        </div>

        <button onClick={fetchDebugEmails} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Ricarica
        </button>
      </div>

      {/* Filtri */}
      <div className="card p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">Categoria</label>
            <select
              className="input"
              value={filterCategoria}
              onChange={(e) => setFilterCategoria(e.target.value)}
            >
              <option value="">Tutte</option>
              <option value="COMUNICAZIONE_UST_USR">UST/USR</option>
              <option value="COMUNICAZIONE_SCUOLA">Scuola</option>
              <option value="CONVOCAZIONE_SCUOLA">Convocazioni</option>
              <option value="INFO_GENERICHE">Info Generiche</option>
              <option value="SPAM">Spam</option>
            </select>
          </div>

          <div className="flex items-center gap-4 pt-6">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={filterConAzioni}
                onChange={(e) => setFilterConAzioni(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm">Solo con azioni</span>
            </label>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={filterConInterpelli}
                onChange={(e) => setFilterConInterpelli(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm">Solo interpelli</span>
            </label>
          </div>
        </div>
      </div>

      {/* Lista Email */}
      {loading ? (
        <div className="card p-8 text-center">
          <Loader className="w-8 h-8 animate-spin mx-auto text-primary-600" />
          <p className="mt-2 text-gray-600">Caricamento...</p>
        </div>
      ) : (
        <div className="space-y-3">
          {emails.map(email => {
            const isExpanded = expandedEmail === email.id
            const completezza = calculateCompletezza(email.interpello)

            return (
              <div key={email.id} className="card">
                {/* Header Email */}
                <div
                  className="p-4 cursor-pointer hover:bg-gray-50 transition"
                  onClick={() => setExpandedEmail(isExpanded ? null : email.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-mono text-sm font-semibold text-gray-700">#{email.id}</span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(email.stato)}`}>
                          {email.stato}
                        </span>
                        {email.categoria && (
                          <span className="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                            {email.categoria.replace(/_/g, ' ')}
                          </span>
                        )}
                        {email.interpello && (
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            completezza >= 75 ? 'bg-green-100 text-green-800' :
                            completezza >= 50 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            Interpello {completezza.toFixed(0)}% completo
                          </span>
                        )}
                      </div>

                      <h3 className="font-semibold text-gray-900 mb-1">{email.oggetto}</h3>
                      <p className="text-sm text-gray-600">{email.mittente}</p>

                      {email.azioni.length > 0 && (
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                          <span className="text-xs text-gray-500">{email.azioni.length} azioni:</span>
                          {email.azioni.slice(0, 5).map(azione => (
                            <div key={azione.id} className="flex items-center gap-1">
                              {getStatusIcon(azione.stato)}
                              <span className="text-xs text-gray-600">{azione.tipo}</span>
                            </div>
                          ))}
                          {email.azioni.length > 5 && (
                            <span className="text-xs text-gray-500">+{email.azioni.length - 5} altre</span>
                          )}
                        </div>
                      )}
                    </div>

                    <button className="text-gray-400 hover:text-gray-600">
                      {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                {/* Dettagli Espansi */}
                {isExpanded && (
                  <div className="border-t border-gray-200 p-4 bg-gray-50 space-y-4">
                    {/* Azioni */}
                    {email.azioni.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                          <FileText className="w-4 h-4" />
                          Azioni Eseguite
                        </h4>
                        <div className="space-y-2">
                          {email.azioni.map(azione => (
                            <div key={azione.id} className="bg-white p-3 rounded border border-gray-200">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  {getStatusIcon(azione.stato)}
                                  <span className="font-medium text-sm">{azione.tipo}</span>
                                  <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(azione.stato)}`}>
                                    {azione.stato}
                                  </span>
                                </div>
                                {azione.eseguita_at && (
                                  <span className="text-xs text-gray-500">
                                    {new Date(azione.eseguita_at).toLocaleString('it-IT')}
                                  </span>
                                )}
                              </div>

                              {azione.risultato && (
                                <div className="mt-2 p-2 bg-gray-50 rounded">
                                  <p className="text-xs font-semibold text-gray-700 mb-1">Risultato:</p>
                                  <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                                    {JSON.stringify(azione.risultato, null, 2)}
                                  </pre>
                                </div>
                              )}

                              {azione.errore && (
                                <div className="mt-2 p-2 bg-red-50 rounded">
                                  <p className="text-xs font-semibold text-red-700">Errore:</p>
                                  <p className="text-xs text-red-600">{azione.errore}</p>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Interpello */}
                    {email.interpello && (
                      <div>
                        <h4 className="font-semibold text-gray-900 mb-2">Interpello - Dati Estratti</h4>

                        {/* Metadata estrazione */}
                        {email.interpello.metadata_estrazione && (
                          <div className="bg-purple-50 border border-purple-200 p-3 rounded mb-3">
                            <p className="text-xs font-semibold text-purple-900 mb-2">Strategia Estrazione:</p>
                            <div className="flex items-center gap-2 flex-wrap mb-3">
                              {(() => {
                                const { extractor, color, icon } = getExtractorInfo(email.interpello.metadata_estrazione)
                                const badgeClasses = {
                                  red: 'bg-red-100 text-red-800 border border-red-300',
                                  green: 'bg-green-100 text-green-800 border border-green-300',
                                  yellow: 'bg-yellow-100 text-yellow-800 border border-yellow-300',
                                  blue: 'bg-blue-100 text-blue-800 border border-blue-300',
                                  orange: 'bg-orange-100 text-orange-800 border border-orange-300',
                                  gray: 'bg-gray-100 text-gray-800 border border-gray-300',
                                }
                                return (
                                  <span className={`px-3 py-1.5 rounded-lg text-sm font-semibold flex items-center gap-2 ${badgeClasses[color as keyof typeof badgeClasses]}`}>
                                    <span className="text-base">{icon}</span>
                                    {extractor}
                                  </span>
                                )
                              })()}

                              {/* Mostra tempo */}
                              {email.interpello.metadata_estrazione.total_time_ms && (
                                <span className="px-2 py-1 rounded text-xs bg-gray-100 text-gray-700">
                                  ⏱️ {Math.round(email.interpello.metadata_estrazione.total_time_ms)}ms
                                </span>
                              )}
                            </div>
                            <details className="text-xs">
                              <summary className="cursor-pointer text-purple-700 font-semibold hover:underline">
                                Mostra metadata completo
                              </summary>
                              <pre className="text-xs text-purple-700 mt-2 whitespace-pre-wrap bg-white p-2 rounded border border-purple-200">
                                {JSON.stringify(email.interpello.metadata_estrazione, null, 2)}
                              </pre>
                            </details>
                          </div>
                        )}

                        {/* Dati estratti */}
                        <div className="bg-white border border-gray-200 rounded p-3">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            <div>
                              <span className="font-semibold text-gray-700">Classe:</span>
                              <span className={`ml-2 ${email.interpello.classe_concorso ? 'text-green-600' : 'text-red-600'}`}>
                                {email.interpello.classe_concorso || '❌ Mancante'}
                              </span>
                            </div>
                            <div>
                              <span className="font-semibold text-gray-700">Ore:</span>
                              <span className={`ml-2 ${email.interpello.ore_settimanali ? 'text-green-600' : 'text-red-600'}`}>
                                {email.interpello.ore_settimanali || '❌ Mancante'}
                              </span>
                            </div>
                            <div>
                              <span className="font-semibold text-gray-700">Provincia:</span>
                              <span className={`ml-2 ${email.interpello.provincia ? 'text-green-600' : 'text-red-600'}`}>
                                {email.interpello.provincia || '❌ Mancante'}
                              </span>
                            </div>
                            <div>
                              <span className="font-semibold text-gray-700">Scadenza:</span>
                              <span className={`ml-2 ${email.interpello.data_scadenza ? 'text-green-600' : 'text-red-600'}`}>
                                {email.interpello.data_scadenza ? new Date(email.interpello.data_scadenza).toLocaleDateString('it-IT') : '❌ Mancante'}
                              </span>
                            </div>
                            <div>
                              <span className="font-semibold text-gray-700">Città:</span>
                              <span className={`ml-2 ${email.interpello.citta ? 'text-green-600' : 'text-gray-400'}`}>
                                {email.interpello.citta || 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="font-semibold text-gray-700">Istituto:</span>
                              <span className={`ml-2 ${email.interpello.istituto ? 'text-green-600' : 'text-gray-400'}`}>
                                {email.interpello.istituto || 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="font-semibold text-gray-700">Posti:</span>
                              <span className={`ml-2 ${email.interpello.numero_posti ? 'text-green-600' : 'text-gray-400'}`}>
                                {email.interpello.numero_posti || 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="font-semibold text-gray-700">Fine contratto:</span>
                              <span className={`ml-2 ${email.interpello.data_fine_contratto ? 'text-green-600' : 'text-gray-400'}`}>
                                {email.interpello.data_fine_contratto ? new Date(email.interpello.data_fine_contratto).toLocaleDateString('it-IT') : 'N/A'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Re-parse buttons */}
                        {completezza < 100 && (
                          <div className="mt-3 flex gap-2">
                            <button
                              onClick={() => handleReparse(email.interpello!.id, 'smart')}
                              disabled={reparsing === email.interpello!.id}
                              className="btn-secondary text-xs flex items-center gap-1"
                            >
                              {reparsing === email.interpello!.id ? (
                                <Loader className="w-3 h-3 animate-spin" />
                              ) : (
                                <RefreshCw className="w-3 h-3" />
                              )}
                              Re-parse (Smart)
                            </button>
                            <button
                              onClick={() => handleReparse(email.interpello!.id, 'regex')}
                              disabled={reparsing === email.interpello!.id}
                              className="btn-secondary text-xs flex items-center gap-1"
                            >
                              Re-parse (Regex)
                            </button>
                            <button
                              onClick={() => handleReparse(email.interpello!.id, 'ollama')}
                              disabled={reparsing === email.interpello!.id}
                              className="btn-secondary text-xs flex items-center gap-1"
                            >
                              Re-parse (Ollama)
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {emails.length === 0 && (
            <div className="card p-8 text-center">
              <Bug className="w-12 h-12 mx-auto text-gray-400 mb-3" />
              <p className="text-gray-600">Nessuna email trovata con i filtri selezionati</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
