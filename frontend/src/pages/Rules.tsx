import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, Plus, Edit2, Trash2, ToggleLeft, ToggleRight } from 'lucide-react'
import { ruleService } from '@/services/ruleService'
import type { Regola } from '@/types'
import PageHeader from '@/components/PageHeader'
import LoadingSpinner from '@/components/LoadingSpinner'
import EmptyState from '@/components/EmptyState'
import Badge from '@/components/Badge'
import { formatDateTime } from '@/lib/utils'
import toast from 'react-hot-toast'

export default function Rules() {
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)

  const { data: rules, isLoading } = useQuery({
    queryKey: ['rules'],
    queryFn: ruleService.getRules,
  })

  const toggleRuleMutation = useMutation({
    mutationFn: ({ id, attiva }: { id: number; attiva: boolean }) =>
      ruleService.toggleRule(id, attiva),
    onSuccess: () => {
      toast.success('Regola aggiornata')
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
  })

  const deleteRuleMutation = useMutation({
    mutationFn: (id: number) => ruleService.deleteRule(id),
    onSuccess: () => {
      toast.success('Regola eliminata')
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
  })

  const sortedRules = rules?.sort((a, b) => b.priorita - a.priorita)

  return (
    <div className="p-8">
      <PageHeader
        title="Regole"
        description="Gestisci regole di automazione per le email"
        actions={
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary"
          >
            <Plus className="w-4 h-4 mr-2" />
            Nuova Regola
          </button>
        }
      />

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : sortedRules && sortedRules.length > 0 ? (
        <div className="space-y-4">
          {sortedRules.map((rule) => (
            <div key={rule.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {rule.nome}
                    </h3>
                    <Badge variant={rule.attiva ? 'success' : 'default'}>
                      {rule.attiva ? 'Attiva' : 'Inattiva'}
                    </Badge>
                    <Badge variant="info">Priorità: {rule.priorita}</Badge>
                  </div>

                  {rule.descrizione && (
                    <p className="text-sm text-gray-600 mb-3">{rule.descrizione}</p>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Condizioni</p>
                      <div className="bg-gray-50 rounded p-2">
                        <pre className="text-xs text-gray-700 overflow-x-auto">
                          {JSON.stringify(rule.condizioni, null, 2)}
                        </pre>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Azioni</p>
                      <div className="space-y-1">
                        {rule.azioni.map((azione, i) => (
                          <div key={i} className="bg-blue-50 rounded px-2 py-1 text-xs">
                            {azione.tipo}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <p className="text-xs text-gray-500 mt-3">
                    Creata: {formatDateTime(rule.created_at)}
                  </p>
                </div>

                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() =>
                      toggleRuleMutation.mutate({ id: rule.id, attiva: !rule.attiva })
                    }
                    className="text-gray-600 hover:text-gray-700"
                    title={rule.attiva ? 'Disattiva' : 'Attiva'}
                  >
                    {rule.attiva ? (
                      <ToggleRight className="w-6 h-6 text-green-600" />
                    ) : (
                      <ToggleLeft className="w-6 h-6" />
                    )}
                  </button>
                  <button className="text-blue-600 hover:text-blue-700">
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteRuleMutation.mutate(rule.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card">
          <EmptyState
            icon={FileText}
            title="Nessuna regola"
            description="Crea regole per automatizzare la gestione delle email."
            action={
              <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
                <Plus className="w-4 h-4 mr-2" />
                Crea Regola
              </button>
            }
          />
        </div>
      )}
    </div>
  )
}
