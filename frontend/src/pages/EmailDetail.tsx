import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Mail, Calendar as CalendarIcon, Paperclip, Trash2, Code, Eye, RotateCcw, CheckCircle, XCircle, AlertCircle, ShieldAlert, MapPin, School, Clock, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { emailsApi, settingsApi, actionsApi, spamApi, calendarApi } from '../lib/api'
import { EmailCategory } from '../types'
import { useState } from 'react'

interface SpamSuggestion {
  pattern: string
  type: string
  description: string
}

export default function EmailDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [viewMode, setViewMode] = useState<'text' | 'html'>('html')
  const [spamSuggestions, setSpamSuggestions] = useState<SpamSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)

  const { data: email, isLoading } = useQuery({
    queryKey: ['email', id],
    queryFn: () => emailsApi.getById(Number(id)).then(res => res.data),
    enabled: !!id,
  })

  // Load category settings to get available subcategories
  const { data: categoriesResponse } = useQuery({
    queryKey: ['categories'],
    queryFn: () => settingsApi.getCategories().then(res => res.data),
  })

  // Load actions for this email to check for failures
  const { data: actionsResponse } = useQuery({
    queryKey: ['actions', id],
    queryFn: () => actionsApi.getAll({ email_id: Number(id) }).then(res => res.data),
    enabled: !!id,
  })

  // Load calendar events for this email
  const { data: calendarResponse } = useQuery({
    queryKey: ['calendar-events', id],
    queryFn: () => calendarApi.getAll().then(res => {
      const eventi = res.data.eventi || []
      return eventi.filter((e: any) => e.email_id === Number(id))
    }),
    enabled: !!id,
  })

  // Check if there are any failed actions
  const hasFailedActions = actionsResponse?.azioni?.some((action: any) => action.stato === 'FALLITA')

  const reprocessMutation = useMutation({
    mutationFn: () => emailsApi.reprocess(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email', id] })
      queryClient.invalidateQueries({ queryKey: ['actions', id] })
      toast.success('Email riprocessata con successo')
    },
    onError: () => {
      toast.error('Errore nella riprocessazione dell\'email')
    },
  })

  const updateCategoriaMutation = useMutation({
    mutationFn: ({ categoria }: { categoria: string }) =>
      emailsApi.updateCategoria(Number(id), categoria),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email', id] })
      toast.success('Categoria aggiornata')
    },
    onError: () => {
      toast.error('Errore nell\'aggiornamento della categoria')
    },
  })

  const updateSottocategoriaMutation = useMutation({
    mutationFn: ({ sottocategoria }: { sottocategoria: string }) =>
      emailsApi.update(Number(id), { sottocategoria }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email', id] })
      toast.success('Sottocategoria aggiornata')
    },
    onError: () => {
      toast.error('Errore nell\'aggiornamento della sottocategoria')
    },
  })

  const markAsReadMutation = useMutation({
    mutationFn: () => emailsApi.markAsRead(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email', id] })
      toast.success('Email segnata come revisionata')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => emailsApi.delete(Number(id)),
    onSuccess: () => {
      toast.success('Email eliminata')
      navigate('/emails')
    },
    onError: () => {
      toast.error('Errore nell\'eliminazione dell\'email')
    },
  })

  const markAsSpamMutation = useMutation({
    mutationFn: () => spamApi.markAsSpam(Number(id)),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['email', id] })
      queryClient.invalidateQueries({ queryKey: ['emails'] })
      toast.success('Email marcata come spam')
      // Mostra suggerimenti se ce ne sono
      if (response.data.suggestions && response.data.suggestions.length > 0) {
        setSpamSuggestions(response.data.suggestions)
        setShowSuggestions(true)
      }
    },
    onError: () => {
      toast.error('Errore nel marcare l\'email come spam')
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!email) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Email non trovata</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/emails')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-5 h-5" />
          Torna alle email
        </button>
        <div className="flex items-center gap-2">
          {email.richiede_revisione && !email.revisionata && (
            <button
              onClick={() => markAsReadMutation.mutate()}
              className="btn-primary"
              disabled={markAsReadMutation.isPending}
            >
              Segna come Revisionata
            </button>
          )}
          {hasFailedActions && (
            <button
              onClick={() => reprocessMutation.mutate()}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors disabled:opacity-50"
              disabled={reprocessMutation.isPending}
              title="Riprocessa email con azioni fallite"
            >
              <RotateCcw className="w-4 h-4" />
              Riprocessa
            </button>
          )}
          {email.categoria !== 'spam' && (
            <button
              onClick={() => {
                if (confirm('Vuoi marcare questa email come spam?')) {
                  markAsSpamMutation.mutate()
                }
              }}
              className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50"
              disabled={markAsSpamMutation.isPending}
              title="Marca come spam"
            >
              <ShieldAlert className="w-4 h-4" />
              Spam
            </button>
          )}
          <button
            onClick={() => {
              if (confirm('Sei sicuro di voler eliminare questa email?')) {
                deleteMutation.mutate()
              }
            }}
            className="btn-danger"
            disabled={deleteMutation.isPending}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Conferma Spam */}
      {showSuggestions && (
        <div className="card bg-green-50 border-2 border-green-200">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-green-900">Email marcata come spam</h3>
              <p className="text-sm text-green-700">
                L'email è stata spostata nella cartella spam
              </p>
            </div>
          </div>

          {spamSuggestions.length > 0 && (
            <details className="mt-4">
              <summary className="text-sm text-gray-600 cursor-pointer hover:text-gray-800">
                Pattern suggeriti per bloccare email simili in futuro ({spamSuggestions.length})
              </summary>
              <div className="mt-3 space-y-2">
                {spamSuggestions.map((s, idx) => (
                  <div key={idx} className="p-2 bg-white rounded border border-gray-200 text-xs">
                    <span className={`px-1.5 py-0.5 rounded ${
                      s.type === 'sender' ? 'bg-blue-100 text-blue-700' :
                      s.type === 'subject' ? 'bg-green-100 text-green-700' :
                      'bg-purple-100 text-purple-700'
                    }`}>
                      {s.type === 'sender' ? 'Mittente' : s.type === 'subject' ? 'Oggetto' : 'Corpo'}
                    </span>
                    <span className="ml-2 text-gray-600">{s.description}</span>
                  </div>
                ))}
              </div>
            </details>
          )}

          <div className="mt-4 flex justify-end">
            <button
              onClick={() => setShowSuggestions(false)}
              className="btn-primary"
            >
              OK, ho capito
            </button>
          </div>
        </div>
      )}

      {/* Email Content */}
      <div className="card">
        <div className="space-y-6">
          {/* Subject */}
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{email.oggetto}</h1>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm font-medium text-gray-500">Da</p>
              <p className="text-sm text-gray-900">{email.mittente}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">A</p>
              <p className="text-sm text-gray-900">{email.destinatario}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Data Ricezione</p>
              <p className="text-sm text-gray-900">
                {new Date(email.data_ricezione).toLocaleString('it-IT')}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Account</p>
              <p className="text-sm text-gray-900">{email.account_type}</p>
            </div>
          </div>

          {/* Category */}
          <div>
            <label className="label">Categoria</label>
            <div className="flex items-center gap-2">
              <select
                className="input flex-1"
                value={email.categoria || ''}
                onChange={(e) =>
                  updateCategoriaMutation.mutate({ categoria: e.target.value })
                }
                disabled={updateCategoriaMutation.isPending}
              >
                <option value="">Non categorizzata</option>
                {Object.values(EmailCategory).map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
              {email.categoria_confidence && (
                <span className="text-sm text-gray-500">
                  Confidenza: {(email.categoria_confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
            {/* Sottocategoria */}
            <div className="mt-3">
              <label className="label">Sottocategoria</label>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <select
                    className="input flex-1"
                    value={email.sottocategoria && categoriesResponse?.categories?.[email.categoria]?.subcategories?.includes(email.sottocategoria) ? email.sottocategoria : ''}
                    onChange={(e) => {
                      if (e.target.value) {
                        updateSottocategoriaMutation.mutate({ sottocategoria: e.target.value })
                      }
                    }}
                    disabled={updateSottocategoriaMutation.isPending || !email.categoria}
                  >
                    <option value="">Seleziona da lista predefinite</option>
                    {email.categoria && categoriesResponse?.categories?.[email.categoria]?.subcategories?.map((subcat: string) => (
                      <option key={subcat} value={subcat}>
                        {subcat}
                      </option>
                    ))}
                  </select>
                  {email.sottocategoria && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 whitespace-nowrap">
                      📂 {email.sottocategoria}
                    </span>
                  )}
                </div>

                {/* Custom sottocategoria input */}
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    className="input flex-1 text-sm"
                    placeholder="oppure inserisci una sottocategoria personalizzata..."
                    defaultValue={email.sottocategoria || ''}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        const value = (e.target as HTMLInputElement).value.trim()
                        if (value) {
                          updateSottocategoriaMutation.mutate({ sottocategoria: value })
                        } else {
                          updateSottocategoriaMutation.mutate({ sottocategoria: '' })
                        }
                      }
                    }}
                    disabled={updateSottocategoriaMutation.isPending || !email.categoria}
                  />
                  <button
                    onClick={() => {
                      updateSottocategoriaMutation.mutate({ sottocategoria: '' })
                    }}
                    className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded transition-colors"
                    disabled={updateSottocategoriaMutation.isPending || !email.sottocategoria}
                  >
                    Rimuovi
                  </button>
                </div>
              </div>
              {!email.categoria && (
                <p className="mt-1 text-xs text-gray-500">Seleziona prima una categoria</p>
              )}
              {email.categoria && categoriesResponse?.categories?.[email.categoria]?.subcategories?.length === 0 && (
                <p className="mt-1 text-xs text-gray-500 italic">💡 Nessuna sottocategoria predefinita per questa categoria. Puoi inserirne una personalizzata.</p>
              )}
            </div>
          </div>

          {/* Subcategory Proposal */}
          {!email.revisionata && email.richiede_revisione && email.sottocategoria_proposta && (
            <div className="p-4 border-2 border-amber-300 bg-amber-50 rounded-lg">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  <AlertCircle className="w-5 h-5 text-amber-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-amber-900 mb-2">
                    ⚠️ Proposta Nuova Sottocategoria
                  </h3>
                  <div className="space-y-2 mb-3">
                    <div>
                      <span className="text-xs font-medium text-amber-700">Proposta:</span>
                      <div className="mt-1 px-3 py-2 bg-white border border-amber-200 rounded text-sm font-medium text-gray-900">
                        {email.sottocategoria_proposta}
                      </div>
                    </div>
                    {email.motivo_proposta && (
                      <div>
                        <span className="text-xs font-medium text-amber-700">Motivo:</span>
                        <div className="mt-1 px-3 py-2 bg-white border border-amber-200 rounded text-sm text-gray-700">
                          {email.motivo_proposta}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={async () => {
                        try {
                          await emailsApi.approveSubcategory(email.id)
                          queryClient.invalidateQueries({ queryKey: ['email', emailId] })
                          toast.success('Sottocategoria approvata!')
                        } catch (error) {
                          toast.error('Errore durante l\'approvazione')
                        }
                      }}
                      className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                    >
                      <CheckCircle className="w-4 h-4" />
                      Approva
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          await emailsApi.rejectSubcategory(email.id)
                          queryClient.invalidateQueries({ queryKey: ['email', emailId] })
                          toast.success('Proposta rifiutata')
                        } catch (error) {
                          toast.error('Errore durante il rifiuto')
                        }
                      }}
                      className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                    >
                      <XCircle className="w-4 h-4" />
                      Rifiuta
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Body */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="label">Contenuto</label>
              {email.corpo_html && (
                <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
                  <button
                    onClick={() => setViewMode('html')}
                    className={`flex items-center gap-1 px-3 py-1 rounded transition-all ${
                      viewMode === 'html'
                        ? 'bg-white text-primary-600 shadow-sm font-medium'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <Eye className="w-4 h-4" />
                    <span className="text-sm">HTML</span>
                  </button>
                  <button
                    onClick={() => setViewMode('text')}
                    className={`flex items-center gap-1 px-3 py-1 rounded transition-all ${
                      viewMode === 'text'
                        ? 'bg-white text-primary-600 shadow-sm font-medium'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <Code className="w-4 h-4" />
                    <span className="text-sm">Testo</span>
                  </button>
                </div>
              )}
            </div>

            {viewMode === 'html' && email.corpo_html ? (
              <div className="border rounded-lg overflow-hidden bg-white">
                <iframe
                  srcDoc={email.corpo_html}
                  className="w-full min-h-[400px] border-0"
                  sandbox="allow-same-origin"
                  style={{ height: '600px' }}
                  title="Email HTML Content"
                />
              </div>
            ) : viewMode === 'text' && email.corpo_html ? (
              <div className="p-4 bg-gray-50 rounded-lg whitespace-pre-wrap text-sm font-mono text-xs overflow-x-auto">
                {email.corpo_html}
              </div>
            ) : email.corpo && (email.corpo.includes('<') && email.corpo.includes('>')) ? (
              <div className="border rounded-lg overflow-hidden bg-white">
                <iframe
                  srcDoc={email.corpo}
                  className="w-full min-h-[400px] border-0"
                  sandbox="allow-same-origin"
                  style={{ height: '600px' }}
                  title="Email Content"
                />
              </div>
            ) : (
              <div className="p-4 bg-gray-50 rounded-lg whitespace-pre-wrap text-sm">
                {email.corpo || 'Nessun contenuto testuale disponibile'}
              </div>
            )}
          </div>

          {/* Attachments */}
          {email.allegati_nomi && email.allegati_nomi.length > 0 && (
            <div>
              <label className="label flex items-center gap-2">
                <Paperclip className="w-4 h-4" />
                Allegati ({email.allegati_nomi.length})
              </label>
              <div className="space-y-2">
                {email.allegati_nomi.map((nome, index) => {
                  const isZip = nome.toLowerCase().endsWith('.zip')
                  // Trova file estratti da questo ZIP
                  const zipContents = isZip && email.allegati_testo
                    ? Object.entries(email.allegati_testo)
                        .filter(([key]) => key.startsWith(nome + '/'))
                        .map(([key, value]) => ({
                          name: key.replace(nome + '/', ''),
                          content: value as string
                        }))
                    : []

                  return (
                    <div
                      key={index}
                      className="p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        {isZip ? (
                          <span className="text-lg">📦</span>
                        ) : (
                          <Paperclip className="w-4 h-4 text-gray-500" />
                        )}
                        <span className="text-sm font-medium text-gray-900">{nome}</span>
                        {isZip && zipContents.length > 0 && (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                            {zipContents.length} file estratti
                          </span>
                        )}
                      </div>

                      {/* Contenuto ZIP estratto */}
                      {isZip && zipContents.length > 0 && (
                        <div className="mt-2 space-y-3">
                          {zipContents.map((file, fileIndex) => (
                            <div key={fileIndex} className="pl-6 border-l-2 border-green-300">
                              <p className="text-xs font-semibold text-gray-600 mb-1 flex items-center gap-1">
                                {file.name.toLowerCase().endsWith('.pdf') ? '📄' : '📝'}
                                {file.name}
                                <span className="text-gray-400">({file.content.length} caratteri)</span>
                              </p>
                              <div className="text-xs text-gray-700 bg-white p-3 rounded border border-gray-200 max-h-64 overflow-y-auto whitespace-pre-wrap">
                                {file.content}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Mostra testo completo estratto dal PDF (non ZIP) */}
                      {!isZip && email.allegati_testo && email.allegati_testo[nome] && (
                        <div className="mt-2 pl-6 border-l-2 border-blue-300">
                          <p className="text-xs font-semibold text-gray-600 mb-1">📄 Contenuto estratto ({email.allegati_testo[nome].length} caratteri):</p>
                          <div className="text-xs text-gray-700 bg-white p-3 rounded border border-gray-200 max-h-96 overflow-y-auto whitespace-pre-wrap">
                            {email.allegati_testo[nome]}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Sintesi Automatica */}
          {email.note && (
            <div>
              <label className="label flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Sintesi Automatica
              </label>
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{email.note}</p>
              </div>
            </div>
          )}

          {/* Evento Calendario */}
          {calendarResponse && calendarResponse.length > 0 && (
            <div>
              <label className="label flex items-center gap-2">
                <CalendarIcon className="w-4 h-4" />
                Evento Calendario ({calendarResponse.length})
              </label>
              <div className="space-y-3">
                {calendarResponse.map((evento: any) => {
                  // Verifica problemi nei dati
                  const hasProblems = !evento.scuola ||
                    !evento.luogo ||
                    evento.luogo === 'ISTITUTO' ||
                    evento.luogo?.length < 15 ||
                    (evento.luogo && !evento.luogo.toLowerCase().includes('via') &&
                     !evento.luogo.toLowerCase().includes('piazza') &&
                     !evento.luogo.toLowerCase().includes('viale'));

                  return (
                    <div
                      key={evento.id}
                      className={`p-4 rounded-lg border-2 ${
                        hasProblems
                          ? 'bg-red-50 border-red-300'
                          : 'bg-green-50 border-green-300'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs font-bold ${
                            hasProblems ? 'bg-red-200 text-red-800' : 'bg-green-200 text-green-800'
                          }`}>
                            ID: {evento.id}
                          </span>
                          {hasProblems && (
                            <span className="flex items-center gap-1 text-red-600 text-xs font-medium">
                              <AlertTriangle className="w-3 h-3" />
                              Dati incompleti
                            </span>
                          )}
                          {evento.sincronizzato && (
                            <span className="flex items-center gap-1 text-green-600 text-xs">
                              <CheckCircle className="w-3 h-3" />
                              Sincronizzato
                            </span>
                          )}
                        </div>
                        <a
                          href={`/calendar`}
                          className="text-xs text-primary-600 hover:underline"
                        >
                          Vai al calendario
                        </a>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                        {/* Data e Ora */}
                        <div className="flex items-start gap-2">
                          <Clock className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                          <div>
                            <span className="text-gray-500 text-xs">Data/Ora:</span>
                            <p className="font-medium text-gray-900">
                              {evento.data_inizio ? new Date(evento.data_inizio).toLocaleString('it-IT', {
                                weekday: 'long',
                                day: '2-digit',
                                month: 'long',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              }) : <span className="text-red-600">Non impostata</span>}
                            </p>
                          </div>
                        </div>

                        {/* Scuola */}
                        <div className="flex items-start gap-2">
                          <School className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                          <div>
                            <span className="text-gray-500 text-xs">Scuola:</span>
                            <p className={`font-medium ${evento.scuola ? 'text-gray-900' : 'text-red-600'}`}>
                              {evento.scuola || 'MANCANTE!'}
                            </p>
                          </div>
                        </div>

                        {/* Luogo */}
                        <div className="flex items-start gap-2 md:col-span-2">
                          <MapPin className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                          <div className="flex-1">
                            <span className="text-gray-500 text-xs">Luogo:</span>
                            <p className={`font-medium ${
                              evento.luogo && evento.luogo !== 'ISTITUTO' && evento.luogo.length > 15
                                ? 'text-gray-900'
                                : 'text-red-600'
                            }`}>
                              {evento.luogo || 'MANCANTE!'}
                              {evento.luogo === 'ISTITUTO' && ' (generico!)'}
                            </p>
                          </div>
                        </div>

                        {/* Stato */}
                        {evento.stato && (
                          <div className="md:col-span-2">
                            <span className="text-gray-500 text-xs">Stato: </span>
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                              evento.stato === 'confermato' ? 'bg-blue-100 text-blue-800' :
                              evento.stato === 'completato' ? 'bg-gray-100 text-gray-800' :
                              evento.stato === 'annullato' ? 'bg-red-100 text-red-800' :
                              'bg-yellow-100 text-yellow-800'
                            }`}>
                              {evento.stato}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Sintesi motivo */}
                      {evento.sintesi_motivo && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <span className="text-gray-500 text-xs">Motivo: </span>
                          <span className="text-sm text-gray-700">{evento.sintesi_motivo}</span>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Status badges */}
          <div className="flex items-center gap-2">
            <span className="badge-primary">{email.stato}</span>
            {email.richiede_revisione && (
              <span className="badge-warning">Richiede revisione</span>
            )}
            {email.revisionata && (
              <span className="badge-success">Revisionata</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
