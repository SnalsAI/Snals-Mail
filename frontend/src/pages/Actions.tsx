import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Trash2, Clock, CheckCircle, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { actionsApi } from '../lib/api'
import { ActionStatus, ActionType } from '../types'

export default function Actions() {
  const queryClient = useQueryClient()

  const { data: actions, isLoading } = useQuery({
    queryKey: ['actions'],
    queryFn: () => actionsApi.getAll().then(res => res.data),
  })

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

  const getStatusIcon = (stato: ActionStatus) => {
    switch (stato) {
      case ActionStatus.COMPLETED:
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case ActionStatus.FAILED:
        return <XCircle className="w-5 h-5 text-red-600" />
      case ActionStatus.IN_PROGRESS:
        return <Clock className="w-5 h-5 text-yellow-600 animate-spin" />
      default:
        return <Clock className="w-5 h-5 text-gray-600" />
    }
  }

  const getActionTypeLabel = (tipo: ActionType) => {
    switch (tipo) {
      case ActionType.BOZZA_RISPOSTA:
        return 'Bozza Risposta'
      case ActionType.CREA_EVENTO_CALENDARIO:
        return 'Evento Calendario'
      case ActionType.CARICA_SU_DRIVE:
        return 'Upload Drive'
      case ActionType.INOLTRA_EMAIL:
        return 'Inoltra Email'
      default:
        return tipo
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Azioni</h1>
        <p className="mt-1 text-sm text-gray-500">
          Gestisci le azioni automatiche generate dal sistema
        </p>
      </div>

      <div className="card">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : actions && actions.length > 0 ? (
          <div className="space-y-4">
            {actions.map((action) => (
              <div
                key={action.id}
                className="p-4 border border-gray-200 rounded-lg"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="mt-1">
                      {getStatusIcon(action.stato)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-base font-semibold text-gray-900">
                          {getActionTypeLabel(action.tipo_azione)}
                        </h3>
                        <span
                          className={
                            action.stato === ActionStatus.COMPLETED
                              ? 'badge-success'
                              : action.stato === ActionStatus.FAILED
                              ? 'badge-danger'
                              : action.stato === ActionStatus.IN_PROGRESS
                              ? 'badge-warning'
                              : 'badge-gray'
                          }
                        >
                          {action.stato}
                        </span>
                      </div>

                      {/* Parameters */}
                      <div className="text-sm text-gray-600 mb-2">
                        {action.tipo_azione === ActionType.BOZZA_RISPOSTA && (
                          <p>A: {action.parametri.to}</p>
                        )}
                        {action.tipo_azione === ActionType.CREA_EVENTO_CALENDARIO && (
                          <p>Evento: {action.parametri.summary}</p>
                        )}
                        {action.tipo_azione === ActionType.CARICA_SU_DRIVE && (
                          <p>Cartella: {action.parametri.folder_name}</p>
                        )}
                        {action.tipo_azione === ActionType.INOLTRA_EMAIL && (
                          <p>Inoltra a: {action.parametri.to}</p>
                        )}
                      </div>

                      {/* Error */}
                      {action.errore && (
                        <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                          Errore: {action.errore}
                        </div>
                      )}

                      <p className="text-xs text-gray-500 mt-2">
                        Creata: {new Date(action.created_at).toLocaleString('it-IT')}
                        {action.executed_at && (
                          <> • Eseguita: {new Date(action.executed_at).toLocaleString('it-IT')}</>
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    {action.stato === ActionStatus.PENDING && (
                      <button
                        onClick={() => executeMutation.mutate(action.id)}
                        className="btn-primary"
                        disabled={executeMutation.isPending}
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
                      className="btn-secondary"
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <CheckCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">Nessuna azione trovata</p>
          </div>
        )}
      </div>
    </div>
  )
}
