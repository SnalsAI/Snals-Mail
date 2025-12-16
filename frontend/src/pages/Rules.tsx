import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings, Power, PowerOff, Trash2, Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import { rulesApi } from '../lib/api'
import RuleBuilder from '../components/RuleBuilder'
import type { Rule } from '../types'

// Mappa tipi azione → label leggibili
const getActionLabel = (actionType: string): string => {
  const actionLabels: Record<string, string> = {
    'BOZZA_RISPOSTA': 'Crea Bozza Risposta',
    'BOZZA_APPUNTAMENTO': 'Crea Bozza Appuntamento',
    'BOZZA_TESSERAMENTO': 'Crea Bozza Tesseramento',
    'EVENTO_CALENDARIO': 'Crea Evento Calendario',
    // Google Drive rimosso
    // 'UPLOAD_DRIVE': 'Carica su Google Drive',
    'SINTESI': 'Genera Sintesi',
    'INDICIZZA_RAG': 'Indicizza nel RAG',
    'PARSE_INTERPELLO': 'Estrai Dati Interpello',
    'ARCHIVIA': 'Archivia Email',
    'SEGNA_IMPORTANTE': 'Segna Importante',
    'segna_importante': 'Segna Importante',
    'INOLTRA': 'Inoltra Email',
    'INOLTRA_DELEGATI_ZONA': 'Inoltra a Delegati Zona',
    'INVIA_NOTIFICA': 'Invia Notifica',
    'NOTIFICA': 'Invia Notifica',
    'assegna_categoria': 'Assegna Categoria',
    'aggiungi_tag': 'Aggiungi Tag',
    'marca_come_letto': 'Marca come Letto',
    // Legacy/alias
    'crea_bozza_risposta': 'Crea Bozza Risposta',
    'crea_evento_calendario': 'Crea Evento Calendario',
    // 'carica_allegati_drive': 'Carica su Google Drive',
    'indicizza_rag': 'Indicizza nel RAG',
    'inoltra_a': 'Inoltra Email',
  }

  return actionLabels[actionType] || actionType.replace(/_/g, ' ')
}

export default function Rules() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState<Rule | undefined>(undefined)

  const { data: rulesResponse, isLoading } = useQuery({
    queryKey: ['rules'],
    queryFn: () => rulesApi.getAll().then(res => res.data),
  })

  const rules: Rule[] = Array.isArray(rulesResponse) ? rulesResponse : []

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
    // Converti regole legacy al nuovo formato per il builder
    const normalizedRule: Rule = {
      ...rule,
      condizioni: normalizeCondizioni(rule.condizioni),
      azioni: normalizeAzioni(rule.azioni)
    }
    setEditingRule(normalizedRule)
    setShowModal(true)
  }

  // Funzione per normalizzare condizioni legacy
  const normalizeCondizioni = (condizioni: any) => {
    // Se è già nel nuovo formato, restituiscilo
    if (condizioni?.rules && Array.isArray(condizioni.rules)) {
      return condizioni
    }

    // Se è vuoto, usa default
    if (!condizioni || Object.keys(condizioni).length === 0) {
      return {
        operator: 'AND' as const,
        rules: [],
        stop_on_match: false
      }
    }

    // Converti formato legacy {categoria: "..."} al nuovo formato
    const rules = []

    if (condizioni.categoria) {
      rules.push({
        field: 'categoria',
        condition: 'uguale',
        value: condizioni.categoria
      })
    }

    if (condizioni.mittente) {
      rules.push({
        field: 'mittente',
        condition: 'contiene',
        value: condizioni.mittente
      })
    }

    // Aggiungi altre condizioni se presenti
    for (const [key, value] of Object.entries(condizioni)) {
      if (key !== 'categoria' && key !== 'mittente' && typeof value === 'string') {
        rules.push({
          field: key,
          condition: 'uguale',
          value: value as string
        })
      }
    }

    return {
      operator: 'AND' as const,
      rules,
      stop_on_match: false
    }
  }

  // Funzione per normalizzare azioni legacy
  const normalizeAzioni = (azioni: any) => {
    // Se è già nel nuovo formato oggetto con actions, restituiscilo
    if (azioni?.actions && Array.isArray(azioni.actions)) {
      return azioni
    }

    // Se è un array (formato database standard), convertilo per il builder
    if (Array.isArray(azioni)) {
      return {
        actions: azioni.map((azione: any) => ({
          type: azione.tipo || azione.type || '',
          params: azione.params || {}
        }))
      }
    }

    // Default vuoto
    return {
      actions: []
    }
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
                            CONDIZIONI{rule.condizioni?.operator ? ` (${rule.condizioni.operator})` : ''}:
                          </p>
                          <div className="space-y-1">
                            {/* Nuovo formato condizioni con rules array */}
                            {rule.condizioni?.rules?.map((cond, idx) => (
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
                            {/* Vecchio formato condizioni (legacy) - mostra come JSON */}
                            {rule.condizioni && !rule.condizioni.rules && (
                              <div className="text-sm text-gray-700 bg-white px-2 py-1 rounded font-mono">
                                {JSON.stringify(rule.condizioni)}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Actions */}
                        <div>
                          {(() => {
                            // Gestisci entrambi i formati: array diretto o oggetto con actions
                            const actions = Array.isArray(rule.azioni)
                              ? rule.azioni
                              : (rule.azioni?.actions || []);

                            return (
                              <>
                                <p className="text-xs font-medium text-gray-500 mb-1">
                                  AZIONI ({actions.length}):
                                </p>
                                <div className="flex flex-wrap gap-2">
                                  {actions.map((action, idx) => {
                                    const actionType = action.type || action.tipo || 'UNKNOWN'
                                    const label = (action as any).descrizione || getActionLabel(actionType)
                                    return (
                                      <span key={idx} className="badge-primary" title={actionType}>
                                        {label}
                                      </span>
                                    )
                                  })}
                                </div>
                              </>
                            );
                          })()}
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
