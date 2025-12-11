import { useState } from 'react'
import { X, Plus, Trash2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { Rule } from '../types'
import { EmailCategory } from '../types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

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

  // Carica zone disponibili
  const { data: zoneData } = useQuery({
    queryKey: ['zone'],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/delegati/zone/`)
      return response.data
    },
  })

  const zone = zoneData?.zone || []

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
    { value: 'scuola_in_zona', label: 'Scuola appartiene a zona' },
  ]

  const actionTypeOptions = [
    { value: 'BOZZA_RISPOSTA', label: 'Crea Bozza Risposta' },
    { value: 'BOZZA_APPUNTAMENTO', label: 'Crea Bozza Appuntamento' },
    { value: 'BOZZA_TESSERAMENTO', label: 'Crea Bozza Tesseramento' },
    { value: 'EVENTO_CALENDARIO', label: 'Crea Evento Calendario' },
    // Google Drive rimosso - non disponibile con account Gmail personale
    // { value: 'UPLOAD_DRIVE', label: 'Carica Allegati su Drive' },
    { value: 'SINTESI', label: 'Genera Sintesi' },
    { value: 'INDICIZZA_RAG', label: 'Indicizza nel RAG' },
    { value: 'PARSE_INTERPELLO', label: 'Parse Interpello' },
    { value: 'ARCHIVIA', label: 'Archivia Email' },
    { value: 'SEGNA_IMPORTANTE', label: 'Segna Importante' },
    { value: 'INOLTRA', label: 'Inoltra Email' },
    { value: 'INOLTRA_DELEGATI_ZONA', label: 'Inoltra a Delegati Zona' },
    { value: 'INVIA_NOTIFICA', label: 'Invia Notifica' },
    { value: 'assegna_categoria', label: 'Assegna Categoria' },
    { value: 'aggiungi_tag', label: 'Aggiungi Tag' },
    { value: 'marca_come_letto', label: 'Marca come Letto' },
  ].sort((a, b) => a.label.localeCompare(b.label, 'it'))

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

    // Converti azioni al formato backend (array con campo "tipo" invece di "type")
    const azioniBackend = actions
      .filter(a => a.type)
      .map(a => ({
        tipo: a.type,
        descrizione: '', // Può essere vuoto
        params: a.params
      }))

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
      azioni: azioniBackend,
    }

    onSave(ruleData)
  }

  const renderActionParams = (action: Action, index: number) => {
    switch (action.type) {
      case 'crea_bozza_risposta':
      case 'BOZZA_RISPOSTA':
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
      case 'EVENTO_CALENDARIO':
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
      case 'inoltra_a':
      case 'INOLTRA':
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
            <option value="comunicazione_scuola">Comunicazione Scuola</option>
            <option value="comunicazione_ust_usr">Comunicazione UST/USR</option>
            <option value="comunicazione_snals_centrale">Comunicazione SNALS Centrale</option>
            <option value="richiesta_appuntamento">Richiesta Appuntamento</option>
            <option value="richiesta_tesseramento">Richiesta Tesseramento</option>
            <option value="revoca_sindacale">Revoca Sindacale</option>
            <option value="ricevuta_pec">Ricevuta PEC</option>
            <option value="fattura">Fattura Elettronica</option>
            <option value="spam">Spam</option>
            <option value="info_generiche">Info Generiche</option>
            <option value="varie">Varie</option>
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
      case 'INOLTRA_DELEGATI_ZONA':
        const selectedZone = action.params.zone || []
        return (
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Seleziona Zone (scelta multipla)</label>
            <div className="border border-gray-300 rounded-lg p-3 max-h-48 overflow-y-auto bg-gray-50">
              {zone.length > 0 ? (
                zone.map((z: any) => (
                  <label key={z.id} className="flex items-center gap-2 p-2 hover:bg-white rounded cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedZone.includes(z.nome)}
                      onChange={(e) => {
                        const newZone = e.target.checked
                          ? [...selectedZone, z.nome]
                          : selectedZone.filter((n: string) => n !== z.nome)
                        updateActionParam(index, 'zone', newZone)
                      }}
                      className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-700">
                      {z.nome}
                      <span className="text-gray-400 ml-1">
                        ({z.num_delegati || 0} delegati, {z.comuni?.length || 0} comuni)
                      </span>
                    </span>
                  </label>
                ))
              ) : (
                <p className="text-sm text-gray-500 italic">Nessuna zona configurata. Vai su Configurazioni → Zone per crearne.</p>
              )}
            </div>
            {selectedZone.length > 0 && (
              <p className="text-sm text-primary-600">
                Zone selezionate: {selectedZone.join(', ')}
              </p>
            )}
          </div>
        )
      case 'INVIA_NOTIFICA':
        return (
          <div className="space-y-2">
            <input
              placeholder="Destinatari (separati da virgola)"
              className="input"
              value={action.params.destinatari?.join(', ') || ''}
              onChange={(e) => updateActionParam(index, 'destinatari', e.target.value.split(',').map(s => s.trim()))}
            />
            <textarea
              placeholder="Messaggio notifica"
              className="input"
              rows={2}
              value={action.params.messaggio || ''}
              onChange={(e) => updateActionParam(index, 'messaggio', e.target.value)}
            />
            <select
              className="input"
              value={action.params.canale || 'email'}
              onChange={(e) => updateActionParam(index, 'canale', e.target.value)}
            >
              <option value="email">Email</option>
              <option value="telegram">Telegram</option>
              <option value="webhook">Webhook</option>
            </select>
          </div>
        )
      case 'SINTESI':
        return (
          <div className="space-y-2">
            <select
              className="input"
              value={action.params.tipo_sintesi || 'giornaliera'}
              onChange={(e) => updateActionParam(index, 'tipo_sintesi', e.target.value)}
            >
              <option value="giornaliera">Giornaliera</option>
              <option value="per_comunicazione">Per Comunicazione</option>
              <option value="settimanale">Settimanale</option>
            </select>
          </div>
        )
      case 'INDICIZZA_RAG':
      case 'indicizza_rag':
        return (
          <div className="text-sm text-gray-600 italic">
            Nessun parametro richiesto - indicizza automaticamente documenti e allegati
          </div>
        )
      case 'PARSE_INTERPELLO':
        return (
          <div className="text-sm text-gray-600 italic">
            Nessun parametro richiesto - estrae automaticamente dati interpello
          </div>
        )
      case 'ARCHIVIA':
      case 'SEGNA_IMPORTANTE':
      case 'marca_come_letto':
        return (
          <div className="text-sm text-gray-600 italic">
            Nessun parametro richiesto
          </div>
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

                  {/* Campo valore - select per categoria/account_type/zona, input per altri */}
                  {condition.field === 'categoria' ? (
                    <select
                      className="input flex-1"
                      value={condition.value}
                      onChange={(e) => updateCondition(index, 'value', e.target.value)}
                    >
                      <option value="">Seleziona categoria...</option>
                      {Object.values(EmailCategory).map((cat) => (
                        <option key={cat} value={cat}>
                          {cat.replace(/_/g, ' ')}
                        </option>
                      ))}
                    </select>
                  ) : condition.field === 'account_type' ? (
                    <select
                      className="input flex-1"
                      value={condition.value}
                      onChange={(e) => updateCondition(index, 'value', e.target.value)}
                    >
                      <option value="">Seleziona tipo account...</option>
                      <option value="NORMALE">Normale</option>
                      <option value="PEC">PEC</option>
                    </select>
                  ) : condition.condition === 'scuola_in_zona' ? (
                    <select
                      className="input flex-1"
                      value={condition.value}
                      onChange={(e) => updateCondition(index, 'value', e.target.value)}
                    >
                      <option value="">Seleziona zona...</option>
                      {zone.map((zona: any) => (
                        <option key={zona.id} value={zona.nome}>
                          {zona.nome} ({zona.comuni?.length || 0} comuni)
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      className="input flex-1"
                      placeholder="Valore..."
                      value={condition.value}
                      onChange={(e) => updateCondition(index, 'value', e.target.value)}
                    />
                  )}

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
