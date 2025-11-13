import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckSquare, Play, Trash2 } from 'lucide-react'
import { actionService } from '@/services/actionService'
import PageHeader from '@/components/PageHeader'
import LoadingSpinner from '@/components/LoadingSpinner'
import EmptyState from '@/components/EmptyState'
import Badge from '@/components/Badge'
import { formatDateTime, getActionTypeLabel, getActionStateLabel, getActionStateColor } from '@/lib/utils'
import toast from 'react-hot-toast'

export default function Actions() {
  const queryClient = useQueryClient()

  const { data: actions, isLoading } = useQuery({
    queryKey: ['actions'],
    queryFn: () => actionService.getActions(),
  })

  const executeActionMutation = useMutation({
    mutationFn: (id: number) => actionService.executeAction(id),
    onSuccess: () => {
      toast.success('Azione eseguita con successo')
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
    onError: () => {
      toast.error('Errore durante l\'esecuzione')
    },
  })

  const deleteActionMutation = useMutation({
    mutationFn: (id: number) => actionService.deleteAction(id),
    onSuccess: () => {
      toast.success('Azione eliminata')
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })

  const pendingActions = actions?.filter(a => a.stato === 'pending') || []
  const completedActions = actions?.filter(a => a.stato === 'completata') || []
  const failedActions = actions?.filter(a => a.stato === 'fallita') || []

  return (
    <div className="p-8">
      <PageHeader
        title="Azioni"
        description="Gestisci tutte le azioni automatiche del sistema"
      />

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="card">
          <p className="text-sm text-gray-600 mb-1">In Attesa</p>
          <p className="text-3xl font-bold text-yellow-600">{pendingActions.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600 mb-1">Completate</p>
          <p className="text-3xl font-bold text-green-600">{completedActions.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600 mb-1">Fallite</p>
          <p className="text-3xl font-bold text-red-600">{failedActions.length}</p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : actions && actions.length > 0 ? (
        <div className="space-y-6">
          {/* Pending Actions */}
          {pendingActions.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3">Azioni in Attesa</h2>
              <div className="space-y-3">
                {pendingActions.map((action) => (
                  <div key={action.id} className="card">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold">
                            {getActionTypeLabel(action.tipo_azione)}
                          </h3>
                          <Badge className={getActionStateColor(action.stato)}>
                            {getActionStateLabel(action.stato)}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">
                          Email ID: {action.email_id}
                        </p>
                        <p className="text-xs text-gray-500">
                          Creato: {formatDateTime(action.created_at)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => executeActionMutation.mutate(action.id)}
                          disabled={executeActionMutation.isPending}
                          className="btn btn-primary"
                        >
                          <Play className="w-4 h-4 mr-2" />
                          Esegui
                        </button>
                        <button
                          onClick={() => deleteActionMutation.mutate(action.id)}
                          className="btn btn-danger"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Failed Actions */}
          {failedActions.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3">Azioni Fallite</h2>
              <div className="space-y-3">
                {failedActions.map((action) => (
                  <div key={action.id} className="card bg-red-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold">
                            {getActionTypeLabel(action.tipo_azione)}
                          </h3>
                          <Badge variant="danger">
                            {getActionStateLabel(action.stato)}
                          </Badge>
                        </div>
                        {action.errore && (
                          <p className="text-sm text-red-700 mb-2">{action.errore}</p>
                        )}
                        <p className="text-xs text-gray-600">
                          Email ID: {action.email_id}
                        </p>
                      </div>
                      <button
                        onClick={() => deleteActionMutation.mutate(action.id)}
                        className="btn btn-danger"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Completed Actions */}
          {completedActions.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3">Azioni Completate (Ultime 10)</h2>
              <div className="space-y-3">
                {completedActions.slice(0, 10).map((action) => (
                  <div key={action.id} className="card">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold">
                            {getActionTypeLabel(action.tipo_azione)}
                          </h3>
                          <Badge variant="success">
                            {getActionStateLabel(action.stato)}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 mb-1">
                          Email ID: {action.email_id}
                        </p>
                        {action.eseguita_at && (
                          <p className="text-xs text-gray-500">
                            Eseguito: {formatDateTime(action.eseguita_at)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card">
          <EmptyState
            icon={CheckSquare}
            title="Nessuna azione"
            description="Non ci sono azioni da visualizzare."
          />
        </div>
      )}
    </div>
  )
}
