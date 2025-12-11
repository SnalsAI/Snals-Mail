import { useQuery } from '@tanstack/react-query'
import { CheckCircle, XCircle, Clock, ChevronDown, ChevronUp } from 'lucide-react'
import { actionsApi } from '../lib/api'
import type { Action } from '../types'

interface EmailActionsPanelProps {
  emailId: number
  isExpanded: boolean
  onToggle: () => void
}

export default function EmailActionsPanel({ emailId, isExpanded, onToggle }: EmailActionsPanelProps) {
  const { data: actionsResponse, isLoading } = useQuery({
    queryKey: ['actions', emailId],
    queryFn: () => actionsApi.getAll({ email_id: emailId }).then(res => res.data),
    enabled: isExpanded,
  })

  const actions = actionsResponse?.azioni || []

  const getActionTypeLabel = (tipo: string) => {
    const labels: Record<string, string> = {
      'BOZZA_RISPOSTA': '📝 Bozza Risposta',
      'BOZZA_APPUNTAMENTO': '📅 Bozza Appuntamento',
      'BOZZA_TESSERAMENTO': '📋 Bozza Tesseramento',
      'EVENTO_CALENDARIO': '🗓️ Evento Calendario',
      'INOLTRA': '↪️ Inoltra',
      'INVIA_NOTIFICA': '🔔 Notifica',
      'SINTESI': '📄 Sintesi',
      'ARCHIVIA': '📦 Archivia',
      'SEGNA_IMPORTANTE': '⭐ Importante',
    }
    return labels[tipo] || tipo
  }

  const getStatusIcon = (stato: string) => {
    switch (stato) {
      case 'COMPLETATA':
        return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'FALLITA':
        return <XCircle className="w-4 h-4 text-red-600" />
      case 'IN_ESECUZIONE':
        return <Clock className="w-4 h-4 text-yellow-600 animate-spin" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusBadge = (stato: string) => {
    switch (stato) {
      case 'COMPLETATA':
        return 'badge-success'
      case 'FALLITA':
        return 'badge-danger'
      case 'IN_ESECUZIONE':
        return 'badge-warning'
      default:
        return 'badge-gray'
    }
  }

  return (
    <div className="border-t border-gray-200 mt-3">
      <button
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          onToggle()
        }}
        className="w-full flex items-center justify-between py-2 px-1 text-sm font-medium text-gray-700 hover:text-gray-900"
      >
        <span>
          {actions.length > 0 ? `Azioni (${actions.length})` : 'Azioni'}
        </span>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      {isExpanded && (
        <div className="pb-3 space-y-2">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
            </div>
          ) : actions.length > 0 ? (
            actions.map((action: Action) => (
              <div
                key={action.id}
                className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                onClick={(e) => e.preventDefault()}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">
                    {getStatusIcon(action.stato)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-900">
                        {getActionTypeLabel(action.tipo)}
                      </span>
                      <span className={`text-xs ${getStatusBadge(action.stato)}`}>
                        {action.stato}
                      </span>
                    </div>

                    {/* Timestamp */}
                    <p className="text-xs text-gray-500">
                      {action.timestamp_inizio ? (
                        <>
                          Creata: {new Date(action.timestamp_inizio).toLocaleString('it-IT')}
                          {action.timestamp_fine && (
                            <> • Eseguita: {new Date(action.timestamp_fine).toLocaleString('it-IT')}</>
                          )}
                        </>
                      ) : (
                        'Data non disponibile'
                      )}
                    </p>

                    {/* Risultato */}
                    {action.risultato && action.stato === 'COMPLETATA' && (
                      <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded text-xs">
                        <p className="font-medium text-green-900 mb-1">✓ Risultato:</p>
                        {action.risultato.status === 'skipped' ? (
                          <p className="text-green-700">
                            ⚠️ {action.risultato.message}
                          </p>
                        ) : action.risultato.status === 'draft_created' ? (
                          <p className="text-green-700">
                            Bozza creata in: {action.risultato.location}
                          </p>
                        ) : action.risultato.status === 'event_created' ? (
                          <p className="text-green-700">
                            Evento creato: {action.risultato.event_id}
                          </p>
                        ) : action.risultato.status === 'uploaded' ? (
                          <p className="text-green-700">
                            File caricati: {action.risultato.uploaded_files?.length || 0}
                          </p>
                        ) : action.risultato.status === 'summary_created' ? (
                          <p className="text-green-700">
                            Sintesi generata
                          </p>
                        ) : (
                          <pre className="text-green-700 whitespace-pre-wrap">
                            {JSON.stringify(action.risultato, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}

                    {/* Intervento Manuale Richiesto */}
                    {action.risultato?.status === 'manual_intervention_required' && (
                      <div className="mt-2 p-2 bg-orange-50 border border-orange-200 rounded text-xs">
                        <p className="font-medium text-orange-900 mb-1">⚠️ Intervento Umano Richiesto</p>
                        <p className="text-orange-700">{action.risultato.message || action.risultato.error}</p>
                        {action.risultato.extracted_data && (
                          <details className="mt-2">
                            <summary className="cursor-pointer text-orange-600 hover:text-orange-800">
                              Dati estratti (incompleti)
                            </summary>
                            <pre className="mt-1 text-xs text-orange-600 whitespace-pre-wrap">
                              {JSON.stringify(action.risultato.extracted_data, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    )}

                    {/* Errore */}
                    {action.errore && action.risultato?.status !== 'manual_intervention_required' && (
                      <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                        <p className="font-medium mb-1">✗ Errore:</p>
                        <p>{action.errore}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-500 text-center py-4">
              Nessuna azione eseguita per questa email
            </p>
          )}
        </div>
      )}
    </div>
  )
}
