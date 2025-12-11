import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Trash2, Clock, CheckCircle, XCircle, Plus, Mail, Calendar, Archive, AlertCircle, Database, Bell, FileText, Star, ListChecks } from 'lucide-react'
import toast from 'react-hot-toast'
import { actionsApi } from '../lib/api'
import { ActionStatus, ActionType } from '../types'
import ActionForm from '../components/ActionForm'
import type { Action } from '../types'

type FilterStatus = 'all' | 'IN_CODA' | 'IN_ESECUZIONE' | 'COMPLETATA' | 'FALLITA'

export default function Actions() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')

  const { data: actionsResponse, isLoading } = useQuery({
    queryKey: ['actions'],
    queryFn: () => actionsApi.getAll().then(res => res.data),
  })

  const actions = actionsResponse?.azioni || []

  // Calculate statistics
  const stats = useMemo(() => {
    return {
      total: actions.length,
      pending: actions.filter((a: Action) => a.stato === 'IN_CODA').length,
      inProgress: actions.filter((a: Action) => a.stato === 'IN_ESECUZIONE').length,
      completed: actions.filter((a: Action) => a.stato === 'COMPLETATA').length,
      failed: actions.filter((a: Action) => a.stato === 'FALLITA').length,
    }
  }, [actions])

  // Filter actions
  const filteredActions = useMemo(() => {
    if (filterStatus === 'all') return actions
    return actions.filter((a: Action) => a.stato === filterStatus)
  }, [actions, filterStatus])

  const executeMutation = useMutation({
    mutationFn: (id: number) => actionsApi.execute(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
      toast.success('Azione eseguita')
    },
    onError: () => {
      toast.error('Errore nell\'esecuzione dell\'azione')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => actionsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
      toast.success('Azione eliminata')
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: Partial<Action>) => actionsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
      toast.success('Azione creata con successo')
      setShowModal(false)
    },
    onError: () => {
      toast.error('Errore nella creazione dell\'azione')
    },
  })

  const handleSaveAction = (data: Partial<Action>) => {
    createMutation.mutate(data)
  }

  const getStatusIcon = (stato: string) => {
    switch (stato) {
      case 'COMPLETATA':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'FALLITA':
        return <XCircle className="w-5 h-5 text-red-600" />
      case 'IN_ESECUZIONE':
        return <Clock className="w-5 h-5 text-yellow-600 animate-spin" />
      default:
        return <Clock className="w-5 h-5 text-gray-600" />
    }
  }

  const getActionTypeLabel = (tipo: string) => {
    const labels: Record<string, string> = {
      // Azioni di risposta
      'BOZZA_RISPOSTA': 'Bozza Risposta',
      'INVIA_RISPOSTA_AUTOMATICA': 'Invia Risposta Automatica',
      'invia_risposta_automatica': 'Invia Risposta Automatica',

      // Azioni di gestione
      'BOZZA_APPUNTAMENTO': 'Bozza Appuntamento',
      'BOZZA_TESSERAMENTO': 'Bozza Tesseramento',
      'CREA_TASK': 'Crea Task',
      'crea_task': 'Crea Task',

      // Azioni di calendario e drive
      'EVENTO_CALENDARIO': 'Evento Calendario',
      'UPLOAD_DRIVE': 'Upload Drive',

      // Azioni di comunicazione
      'INOLTRA': 'Inoltra Email',
      'INOLTRA_EMAIL': 'Inoltra Email',
      'inoltra_email': 'Inoltra Email',
      'INOLTRA_DELEGATI_ZONA': 'Inoltra Delegati Zona',
      'NOTIFICA': 'Notifica',
      'INVIA_NOTIFICA': 'Invia Notifica',
      'invia_notifica': 'Invia Notifica',

      // Azioni di archiviazione e organizzazione
      'ARCHIVIA': 'Archivia',
      'archivia': 'Archivia',
      'SEGNA_IMPORTANTE': 'Segna Importante',
      'segna_importante': 'Segna Importante',
      'PUBBLICA_SU_SITO': 'Pubblica su Sito',
      'pubblica_su_sito': 'Pubblica su Sito',

      // Azioni di elaborazione
      'SINTESI': 'Genera Sintesi',
      'INDICIZZA_RAG': 'Indicizza RAG',
      'PARSE_INTERPELLO': 'Parse Interpello',

      // Azioni di moderazione
      'ELIMINA': 'Elimina',
      'elimina': 'Elimina',
      'SPAM': 'Spam',
    }
    return labels[tipo] || tipo
  }

  const getActionTypeIcon = (tipo: string) => {
    const iconClass = "w-5 h-5"
    // Normalize to check
    const tipoNorm = tipo.toUpperCase()

    if (tipoNorm.includes('RISPOSTA')) return <Mail className={iconClass} />
    if (tipoNorm.includes('APPUNTAMENTO')) return <Calendar className={iconClass} />
    if (tipoNorm.includes('TESSERAMENTO')) return <FileText className={iconClass} />
    if (tipoNorm.includes('CALENDARIO')) return <Calendar className={iconClass} />
    if (tipoNorm.includes('DRIVE')) return <Database className={iconClass} />
    if (tipoNorm.includes('INOLTRA')) return <Mail className={iconClass} />
    if (tipoNorm.includes('NOTIFICA')) return <Bell className={iconClass} />
    if (tipoNorm.includes('SINTESI')) return <FileText className={iconClass} />
    if (tipoNorm.includes('ARCHIVIA')) return <Archive className={iconClass} />
    if (tipoNorm.includes('IMPORTANTE')) return <Star className={iconClass} />
    if (tipoNorm.includes('RAG') || tipoNorm.includes('INDICIZZA')) return <Database className={iconClass} />
    if (tipoNorm.includes('TASK')) return <ListChecks className={iconClass} />
    if (tipoNorm.includes('INTERPELLO')) return <FileText className={iconClass} />
    if (tipoNorm.includes('PUBBLICA')) return <FileText className={iconClass} />
    if (tipoNorm.includes('ELIMINA') || tipoNorm.includes('SPAM')) return <AlertCircle className={iconClass} />

    return <AlertCircle className={iconClass} />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Azioni</h1>
          <p className="mt-1 text-sm text-gray-500">
            Gestisci le azioni automatiche e crea azioni manuali
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="btn-primary flex items-center gap-2 shadow-lg hover:shadow-xl transition-all"
        >
          <Plus className="w-4 h-4" />
          Nuova Azione
        </button>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border border-blue-200 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-600">Totale</p>
              <p className="text-3xl font-bold text-blue-900 mt-1">{stats.total}</p>
            </div>
            <div className="p-3 bg-blue-200 rounded-lg">
              <ListChecks className="w-6 h-6 text-blue-700" />
            </div>
          </div>
        </div>

        {/* Pending */}
        <div
          className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-6 border border-gray-200 shadow-sm hover:shadow-md transition-all cursor-pointer"
          onClick={() => setFilterStatus(filterStatus === 'IN_CODA' ? 'all' : 'IN_CODA')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">In Coda</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.pending}</p>
            </div>
            <div className="p-3 bg-gray-200 rounded-lg">
              <Clock className="w-6 h-6 text-gray-700" />
            </div>
          </div>
          {filterStatus === 'IN_CODA' && (
            <div className="mt-2 text-xs text-gray-600 font-medium">✓ Filtro attivo</div>
          )}
        </div>

        {/* In Progress */}
        <div
          className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-lg p-6 border border-yellow-200 shadow-sm hover:shadow-md transition-all cursor-pointer"
          onClick={() => setFilterStatus(filterStatus === 'IN_ESECUZIONE' ? 'all' : 'IN_ESECUZIONE')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-yellow-600">In Esecuzione</p>
              <p className="text-3xl font-bold text-yellow-900 mt-1">{stats.inProgress}</p>
            </div>
            <div className="p-3 bg-yellow-200 rounded-lg">
              <Clock className="w-6 h-6 text-yellow-700 animate-spin" />
            </div>
          </div>
          {filterStatus === 'IN_ESECUZIONE' && (
            <div className="mt-2 text-xs text-yellow-600 font-medium">✓ Filtro attivo</div>
          )}
        </div>

        {/* Completed */}
        <div
          className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6 border border-green-200 shadow-sm hover:shadow-md transition-all cursor-pointer"
          onClick={() => setFilterStatus(filterStatus === 'COMPLETATA' ? 'all' : 'COMPLETATA')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-600">Completate</p>
              <p className="text-3xl font-bold text-green-900 mt-1">{stats.completed}</p>
            </div>
            <div className="p-3 bg-green-200 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-700" />
            </div>
          </div>
          {filterStatus === 'COMPLETATA' && (
            <div className="mt-2 text-xs text-green-600 font-medium">✓ Filtro attivo</div>
          )}
        </div>

        {/* Failed */}
        <div
          className="bg-gradient-to-br from-red-50 to-red-100 rounded-lg p-6 border border-red-200 shadow-sm hover:shadow-md transition-all cursor-pointer"
          onClick={() => setFilterStatus(filterStatus === 'FALLITA' ? 'all' : 'FALLITA')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-red-600">Fallite</p>
              <p className="text-3xl font-bold text-red-900 mt-1">{stats.failed}</p>
            </div>
            <div className="p-3 bg-red-200 rounded-lg">
              <XCircle className="w-6 h-6 text-red-700" />
            </div>
          </div>
          {filterStatus === 'FALLITA' && (
            <div className="mt-2 text-xs text-red-600 font-medium">✓ Filtro attivo</div>
          )}
        </div>
      </div>

      {/* Filter indicator */}
      {filterStatus !== 'all' && (
        <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-blue-700">
            <span className="font-semibold">Filtro attivo:</span> {filterStatus.replace('_', ' ')}
          </p>
          <button
            onClick={() => setFilterStatus('all')}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium underline"
          >
            Rimuovi filtro
          </button>
        </div>
      )}

      {/* Actions List */}
      <div className="card">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : filteredActions && filteredActions.length > 0 ? (
          <div className="space-y-3">
            {filteredActions.map((action: Action) => {
              const statusColor =
                action.stato === 'COMPLETATA' ? 'green' :
                action.stato === 'FALLITA' ? 'red' :
                action.stato === 'IN_ESECUZIONE' ? 'yellow' :
                'gray'

              return (
                <div
                  key={action.id}
                  className={`p-5 rounded-lg border-l-4 transition-all duration-200 hover:shadow-md
                    ${action.stato === 'COMPLETATA' ? 'border-l-green-500 bg-gradient-to-r from-green-50 to-transparent hover:from-green-100' :
                      action.stato === 'FALLITA' ? 'border-l-red-500 bg-gradient-to-r from-red-50 to-transparent hover:from-red-100' :
                      action.stato === 'IN_ESECUZIONE' ? 'border-l-yellow-500 bg-gradient-to-r from-yellow-50 to-transparent hover:from-yellow-100' :
                      'border-l-gray-500 bg-gradient-to-r from-gray-50 to-transparent hover:from-gray-100'
                    } border border-gray-200`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4 flex-1">
                      {/* Status Icon */}
                      <div className={`mt-1 p-2 rounded-lg ${
                        action.stato === 'COMPLETATA' ? 'bg-green-100' :
                        action.stato === 'FALLITA' ? 'bg-red-100' :
                        action.stato === 'IN_ESECUZIONE' ? 'bg-yellow-100' :
                        'bg-gray-100'
                      }`}>
                        {getStatusIcon(action.stato)}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        {/* Header with type and status */}
                        <div className="flex items-center gap-3 mb-3 flex-wrap">
                          <div className="flex items-center gap-2">
                            {getActionTypeIcon(action.tipo)}
                            <h3 className="text-lg font-semibold text-gray-900">
                              {getActionTypeLabel(action.tipo)}
                            </h3>
                          </div>
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                              action.stato === 'COMPLETATA'
                                ? 'bg-green-100 text-green-800 border-green-200'
                                : action.stato === 'FALLITA'
                                ? 'bg-red-100 text-red-800 border-red-200'
                                : action.stato === 'IN_ESECUZIONE'
                                ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
                                : 'bg-gray-100 text-gray-800 border-gray-200'
                            }`}
                          >
                            {action.stato.replace('_', ' ')}
                          </span>
                        </div>

                        {/* Email Info */}
                        {action.email && (
                          <div className="mb-3 p-3 bg-white rounded-lg border border-gray-200">
                            <div className="flex items-center gap-2 text-sm">
                              <Mail className="w-4 h-4 text-gray-400" />
                              <span className="text-gray-500">Email:</span>
                              <span className="font-medium text-gray-900 truncate">
                                {action.email.oggetto || 'Senza oggetto'}
                              </span>
                            </div>
                            {action.email.mittente && (
                              <div className="flex items-center gap-2 text-sm mt-1">
                                <span className="text-gray-500 ml-6">Da:</span>
                                <span className="text-gray-700">{action.email.mittente}</span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Description */}
                        {action.dettagli?.descrizione && (
                          <div className="mb-3">
                            <p className="text-sm text-gray-700">
                              {action.dettagli.descrizione}
                            </p>
                          </div>
                        )}

                        {/* Parameters (user-friendly display) */}
                        {action.dettagli?.parametri && Object.keys(action.dettagli.parametri).length > 0 && (
                          <div className="mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                            <p className="text-xs font-semibold text-gray-600 mb-2">Parametri:</p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                              {Object.entries(action.dettagli.parametri).map(([key, value]) => (
                                <div key={key} className="text-xs">
                                  <span className="font-medium text-gray-700">{key}:</span>{' '}
                                  <span className="text-gray-600">
                                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Error */}
                        {action.errore && (
                          <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                            <div className="flex items-start gap-2">
                              <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                              <div>
                                <p className="text-sm font-semibold text-red-800 mb-1">Errore:</p>
                                <p className="text-sm text-red-700">{action.errore}</p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Timestamps */}
                        <div className="flex items-center gap-4 text-xs text-gray-500">
                          {action.timestamp_inizio && (
                            <span>
                              <span className="font-medium">Inizio:</span>{' '}
                              {new Date(action.timestamp_inizio).toLocaleString('it-IT')}
                            </span>
                          )}
                          {action.timestamp_fine && (
                            <span>
                              <span className="font-medium">Fine:</span>{' '}
                              {new Date(action.timestamp_fine).toLocaleString('it-IT')}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Actions Buttons */}
                    <div className="flex items-start gap-2 flex-shrink-0">
                      {action.stato === 'IN_CODA' && (
                        <button
                          onClick={() => executeMutation.mutate(action.id)}
                          className="p-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors shadow-sm hover:shadow-md"
                          disabled={executeMutation.isPending}
                          title="Esegui azione"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => {
                          if (confirm('Sei sicuro di voler eliminare questa azione?')) {
                            deleteMutation.mutate(action.id)
                          }
                        }}
                        className="p-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-red-100 hover:text-red-700 transition-colors shadow-sm"
                        disabled={deleteMutation.isPending}
                        title="Elimina azione"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="p-4 bg-gray-100 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              {filterStatus !== 'all' ? (
                <AlertCircle className="w-8 h-8 text-gray-400" />
              ) : (
                <CheckCircle className="w-8 h-8 text-gray-400" />
              )}
            </div>
            <p className="text-gray-500 mb-2 font-medium">
              {filterStatus !== 'all'
                ? `Nessuna azione ${filterStatus.toLowerCase().replace('_', ' ')} trovata`
                : 'Nessuna azione trovata'
              }
            </p>
            <p className="text-sm text-gray-400 mb-4">
              {filterStatus !== 'all'
                ? 'Prova a cambiare filtro o crea una nuova azione'
                : 'Crea la tua prima azione per iniziare'
              }
            </p>
            {filterStatus === 'all' && (
              <button onClick={() => setShowModal(true)} className="btn-primary shadow-lg hover:shadow-xl transition-all">
                <Plus className="w-4 h-4 inline mr-2" />
                Crea Azione
              </button>
            )}
          </div>
        )}
      </div>

      {/* Action Form Modal */}
      {showModal && (
        <ActionForm
          onSave={handleSaveAction}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
