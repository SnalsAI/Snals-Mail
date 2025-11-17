import { useState } from 'react'
import { X, Plus, Trash2 } from 'lucide-react'
import type { Rule } from '../types'

interface RuleBuilderProps {
  rule?: Rule
  onSave: (rule: Partial<Rule>) => void
  onClose: () => void
}

interface Condition {
  field: string
  condition: string
  value: string
}

interface Action {
  type: string
  params: Record<string, any>
}

export default function RuleBuilder({ rule, onSave, onClose }: RuleBuilderProps) {
  const [nome, setNome] = useState(rule?.nome || '')
  const [descrizione, setDescrizione] = useState(rule?.descrizione || '')
  const [priorita, setPriorita] = useState(rule?.priorita || 10)
  const [operator, setOperator] = useState<'AND' | 'OR'>(rule?.condizioni.operator || 'AND')
  const [conditions, setConditions] = useState<Condition[]>(
    rule?.condizioni.rules || [{ field: '', condition: '', value: '' }]
  )
  const [actions, setActions] = useState<Action[]>(
    rule?.azioni.actions || [{ type: '', params: {} }]
  )
  const [stopOnMatch, setStopOnMatch] = useState(rule?.condizioni.stop_on_match || false)

  const fieldOptions = [
    { value: 'mittente', label: 'Mittente' },
    { value: 'destinatario', label: 'Destinatario' },
    { value: 'oggetto', label: 'Oggetto' },
    { value: 'corpo', label: 'Corpo' },
    { value: 'categoria', label: 'Categoria' },
    { value: 'account_type', label: 'Tipo Account' },
    { value: 'has_allegati', label: 'Ha Allegati' },
    { value: 'num_allegati', label: 'Numero Allegati' },
  ]

  const conditionOptions = [
    { value: 'uguale', label: 'Uguale a' },
    { value: 'diverso', label: 'Diverso da' },
    { value: 'contiene', label: 'Contiene' },
    { value: 'non_contiene', label: 'Non contiene' },
    { value: 'inizia_con', label: 'Inizia con' },
    { value: 'finisce_con', label: 'Finisce con' },
    { value: 'regex', label: 'Regex' },
    { value: 'maggiore', label: 'Maggiore di' },
    { value: 'minore', label: 'Minore di' },
    { value: 'vuoto', label: 'È vuoto' },
    { value: 'non_vuoto', label: 'Non è vuoto' },
  ]

  const actionTypeOptions = [
    { value: 'crea_bozza_risposta', label: 'Crea Bozza Risposta' },
    { value: 'crea_evento_calendario', label: 'Crea Evento Calendario' },
    { value: 'carica_allegati_drive', label: 'Carica Allegati su Drive' },
    { value: 'inoltra_a', label: 'Inoltra Email' },
    { value: 'assegna_categoria', label: 'Assegna Categoria' },
    { value: 'aggiungi_tag', label: 'Aggiungi Tag' },
    { value: 'marca_come_letto', label: 'Marca come Letto' },
  ]

  const addCondition = () => {
    setConditions([...conditions, { field: '', condition: '', value: '' }])
  }

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index))
  }

  const updateCondition = (index: number, field: keyof Condition, value: string) => {
    const newConditions = [...conditions]
    newConditions[index] = { ...newConditions[index], [field]: value }
    setConditions(newConditions)
  }

  const addAction = () => {
    setActions([...actions, { type: '', params: {} }])
  }

  const removeAction = (index: number) => {
    setActions(actions.filter((_, i) => i !== index))
  }

  const updateAction = (index: number, type: string) => {
    const newActions = [...actions]
    newActions[index] = { type, params: {} }
    setActions(newActions)
  }

  const updateActionParam = (index: number, param: string, value: any) => {
    const newActions = [...actions]
    newActions[index].params[param] = value
    setActions(newActions)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const ruleData: Partial<Rule> = {
      nome,
      descrizione,
      priorita,
      attivo: true,
      condizioni: {
        operator,
        rules: conditions.filter(c => c.field && c.condition),
        stop_on_match: stopOnMatch,
      },
      azioni: {
        actions: actions.filter(a => a.type),
      },
    }

    onSave(ruleData)
  }

  const renderActionParams = (action: Action, index: number) => {
    switch (action.type) {
      case 'crea_bozza_risposta':
        return (
          <div className="space-y-2">
            <textarea
              placeholder="Template risposta (usa {mittente}, {oggetto}, ecc.)"
              className="input"
              rows={3}
              value={action.params.template || ''}
              onChange={(e) => updateActionParam(index, 'template', e.target.value)}
            />
          </div>
        )
      case 'crea_evento_calendario':
        return (
          <div className="grid grid-cols-2 gap-2">
            <input
              placeholder="Titolo"
              className="input"
              value={action.params.title || ''}
              onChange={(e) => updateActionParam(index, 'title', e.target.value)}
            />
            <input
              placeholder="Luogo"
              className="input"
              value={action.params.location || ''}
              onChange={(e) => updateActionParam(index, 'location', e.target.value)}
            />
          </div>
        )
      case 'carica_allegati_drive':
        return (
          <input
            placeholder="Nome cartella Drive"
            className="input"
            value={action.params.folder_name || ''}
            onChange={(e) => updateActionParam(index, 'folder_name', e.target.value)}
          />
        )
      case 'inoltra_a':
        return (
          <input
            placeholder="Indirizzo email destinatario"
            type="email"
            className="input"
            value={action.params.to || ''}
            onChange={(e) => updateActionParam(index, 'to', e.target.value)}
          />
        )
      case 'assegna_categoria':
        return (
          <select
            className="input"
            value={action.params.categoria || ''}
            onChange={(e) => updateActionParam(index, 'categoria', e.target.value)}
          >
            <option value="">Seleziona categoria</option>
            <option value="info_generiche">Info Generiche</option>
            <option value="richiesta_appuntamento">Richiesta Appuntamento</option>
            <option value="convocazione_scuola">Convocazione Scuola</option>
            <option value="comunicazione_ust_usr">Comunicazione UST/USR</option>
          </select>
        )
      case 'aggiungi_tag':
        return (
          <input
            placeholder="Nome tag"
            className="input"
            value={action.params.tag || ''}
            onChange={(e) => updateActionParam(index, 'tag', e.target.value)}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            {rule ? 'Modifica Regola' : 'Nuova Regola'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Basic Info */}
          <div className="space-y-4">
            <div>
              <label className="label">Nome Regola *</label>
              <input
                type="text"
                className="input"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                required
                placeholder="es: Inoltra convocazioni urgenti"
              />
            </div>

            <div>
              <label className="label">Descrizione</label>
              <textarea
                className="input"
                value={descrizione}
                onChange={(e) => setDescrizione(e.target.value)}
                rows={2}
                placeholder="Descrizione opzionale della regola"
              />
            </div>

            <div>
              <label className="label">Priorità</label>
              <input
                type="number"
                className="input"
                value={priorita}
                onChange={(e) => setPriorita(Number(e.target.value))}
                min="0"
                max="100"
              />
              <p className="mt-1 text-sm text-gray-500">
                Priorità più alta = eseguita prima (0-100)
              </p>
            </div>
          </div>

          {/* Conditions */}
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Condizioni</h3>
              <div className="flex items-center gap-4">
                <select
                  className="input w-32"
                  value={operator}
                  onChange={(e) => setOperator(e.target.value as 'AND' | 'OR')}
                >
                  <option value="AND">AND</option>
                  <option value="OR">OR</option>
                </select>
                <button
                  type="button"
                  onClick={addCondition}
                  className="btn-secondary flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Aggiungi
                </button>
              </div>
            </div>

            <div className="space-y-3">
              {conditions.map((condition, index) => (
                <div key={index} className="flex items-center gap-2">
                  <select
                    className="input flex-1"
                    value={condition.field}
                    onChange={(e) => updateCondition(index, 'field', e.target.value)}
                  >
                    <option value="">Campo...</option>
                    {fieldOptions.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>

                  <select
                    className="input flex-1"
                    value={condition.condition}
                    onChange={(e) => updateCondition(index, 'condition', e.target.value)}
                  >
                    <option value="">Condizione...</option>
                    {conditionOptions.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>

                  <input
                    type="text"
                    className="input flex-1"
                    placeholder="Valore..."
                    value={condition.value}
                    onChange={(e) => updateCondition(index, 'value', e.target.value)}
                  />

                  <button
                    type="button"
                    onClick={() => removeCondition(index)}
                    className="btn-danger"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>

            <div className="mt-4 flex items-center gap-3">
              <input
                type="checkbox"
                id="stopOnMatch"
                checked={stopOnMatch}
                onChange={(e) => setStopOnMatch(e.target.checked)}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <label htmlFor="stopOnMatch" className="text-sm text-gray-700">
                Interrompi valutazione altre regole se questa si applica
              </label>
            </div>
          </div>

          {/* Actions */}
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Azioni</h3>
              <button
                type="button"
                onClick={addAction}
                className="btn-secondary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Aggiungi
              </button>
            </div>

            <div className="space-y-4">
              {actions.map((action, index) => (
                <div key={index} className="p-4 border border-gray-200 rounded-lg space-y-3">
                  <div className="flex items-center gap-2">
                    <select
                      className="input flex-1"
                      value={action.type}
                      onChange={(e) => updateAction(index, e.target.value)}
                    >
                      <option value="">Seleziona azione...</option>
                      {actionTypeOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>

                    <button
                      type="button"
                      onClick={() => removeAction(index)}
                      className="btn-danger"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  {action.type && renderActionParams(action, index)}
                </div>
              ))}
            </div>
          </div>

          {/* Submit */}
          <div className="border-t border-gray-200 pt-6 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
            >
              Annulla
            </button>
            <button
              type="submit"
              className="btn-primary"
            >
              {rule ? 'Salva Modifiche' : 'Crea Regola'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
