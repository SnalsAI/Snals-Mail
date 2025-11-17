import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings, Power, PowerOff, Trash2, Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import { rulesApi } from '../lib/api'
import RuleBuilder from '../components/RuleBuilder'
import type { Rule } from '../types'

export default function Rules() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState<Rule | undefined>(undefined)

  const { data: rules, isLoading } = useQuery({
    queryKey: ['rules'],
    queryFn: () => rulesApi.getAll().then(res => res.data),
  })

  const toggleMutation = useMutation({
    mutationFn: (id: number) => rulesApi.toggle(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      toast.success('Regola aggiornata')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => rulesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      toast.success('Regola eliminata')
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: Partial<Rule>) => rulesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      toast.success('Regola creata con successo')
      setShowModal(false)
      setEditingRule(undefined)
    },
    onError: () => {
      toast.error('Errore nella creazione della regola')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Rule> }) =>
      rulesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      toast.success('Regola aggiornata con successo')
      setShowModal(false)
      setEditingRule(undefined)
    },
    onError: () => {
      toast.error('Errore nell\'aggiornamento della regola')
    },
  })

  const handleSaveRule = (data: Partial<Rule>) => {
    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleEditRule = (rule: Rule) => {
    setEditingRule(rule)
    setShowModal(true)
  }

  const handleNewRule = () => {
    setEditingRule(undefined)
    setShowModal(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Regole</h1>
          <p className="mt-1 text-sm text-gray-500">
            Gestisci regole automatiche per processare le email
          </p>
        </div>
        <button
          onClick={handleNewRule}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nuova Regola
        </button>
      </div>

      <div className="card">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : rules && rules.length > 0 ? (
          <div className="space-y-4">
            {rules
              .sort((a, b) => b.priorita - a.priorita)
              .map((rule) => (
                <div
                  key={rule.id}
                  className={`p-4 border-2 rounded-lg ${
                    rule.attivo
                      ? 'border-primary-200 bg-primary-50'
                      : 'border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4 flex-1">
                      <div className="mt-1">
                        <Settings className={`w-6 h-6 ${rule.attivo ? 'text-primary-600' : 'text-gray-400'}`} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">
                            {rule.nome}
                          </h3>
                          <span className="badge-gray">
                            Priorità: {rule.priorita}
                          </span>
                          {rule.attivo ? (
                            <span className="badge-success">Attiva</span>
                          ) : (
                            <span className="badge-gray">Disattivata</span>
                          )}
                        </div>

                        {rule.descrizione && (
                          <p className="text-sm text-gray-600 mb-3">
                            {rule.descrizione}
                          </p>
                        )}

                        {/* Conditions */}
                        <div className="mb-3">
                          <p className="text-xs font-medium text-gray-500 mb-1">
                            CONDIZIONI ({rule.condizioni.operator}):
                          </p>
                          <div className="space-y-1">
                            {rule.condizioni.rules?.map((cond, idx) => (
                              <div
                                key={idx}
                                className="text-sm text-gray-700 bg-white px-2 py-1 rounded"
                              >
                                <span className="font-medium">{cond.field}</span>{' '}
                                <span className="text-gray-500">{cond.condition}</span>{' '}
                                <span className="font-medium">
                                  {typeof cond.value === 'object'
                                    ? JSON.stringify(cond.value)
                                    : String(cond.value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Actions */}
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1">
                            AZIONI ({rule.azioni.actions?.length || 0}):
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {rule.azioni.actions?.map((action, idx) => (
                              <span key={idx} className="badge-primary">
                                {action.type.replace(/_/g, ' ')}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Stats */}
                        <div className="mt-3 text-xs text-gray-500">
                          Applicata {rule.volte_applicata} volte
                          {rule.ultima_applicazione && (
                            <> • Ultima: {new Date(rule.ultima_applicazione).toLocaleString('it-IT')}</>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 ml-4">
                      <button
                        onClick={() => handleEditRule(rule)}
                        className="btn-secondary"
                      >
                        Modifica
                      </button>
                      <button
                        onClick={() => toggleMutation.mutate(rule.id)}
                        className={rule.attivo ? 'btn-secondary' : 'btn-primary'}
                        disabled={toggleMutation.isPending}
                      >
                        {rule.attivo ? (
                          <PowerOff className="w-4 h-4" />
                        ) : (
                          <Power className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('Sei sicuro di voler eliminare questa regola?')) {
                            deleteMutation.mutate(rule.id)
                          }
                        }}
                        className="btn-danger"
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
            <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">Nessuna regola configurata</p>
            <button onClick={handleNewRule} className="btn-primary">
              Crea la tua prima regola
            </button>
          </div>
        )}
      </div>

      {/* Rule Builder Modal */}
      {showModal && (
        <RuleBuilder
          rule={editingRule}
          onSave={handleSaveRule}
          onClose={() => {
            setShowModal(false)
            setEditingRule(undefined)
          }}
        />
      )}
    </div>
  )
}
