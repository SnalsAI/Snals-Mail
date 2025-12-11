import { useState, useEffect } from 'react'
import { X, Users } from 'lucide-react'
import { ActionType } from '../types'
import type { Action } from '../types'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

interface ActionFormProps {
  emailId?: number
  emailMittente?: string
  onSave: (action: Partial<Action>) => void
  onClose: () => void
}

export default function ActionForm({ emailId, emailMittente, onSave, onClose }: ActionFormProps) {
  const [tipoAzione, setTipoAzione] = useState<ActionType | ''>('')
  const [params, setParams] = useState<Record<string, any>>({})
  const [selectedDelegati, setSelectedDelegati] = useState<number[]>([])
  const [schoolCode, setSchoolCode] = useState<string | null>(null)

  // Estrai codice scuola dal mittente
  useEffect(() => {
    if (emailMittente) {
      const match = emailMittente.match(/([a-z]{4}\d{6}[a-z]?)@istruzione\.it/i)
      setSchoolCode(match ? match[1].toUpperCase() : null)
    }
  }, [emailMittente])

  // Carica delegati se è una scuola
  const { data: delegatiData } = useQuery({
    queryKey: ['delegati-by-school', schoolCode],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/delegati/zone/by-school/${schoolCode}`)
      return response.data
    },
    enabled: !!schoolCode && tipoAzione === ActionType.INOLTRA_EMAIL
  })

  // Azioni disponibili in ordine alfabetico
  const actionTypes = [
    { value: ActionType.BOZZA_RISPOSTA, label: 'Crea Bozza Risposta' },
    { value: ActionType.EVENTO_CALENDARIO, label: 'Crea Evento Calendario' },
    // Google Drive rimosso - non disponibile con account Gmail personale
    // { value: ActionType.UPLOAD_DRIVE, label: 'Carica Allegati su Drive' },
    { value: ActionType.INOLTRA_EMAIL, label: 'Inoltra Email' },
  ].sort((a, b) => a.label.localeCompare(b.label, 'it'))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const actionData: Partial<Action> = {
      email_id: emailId,
      tipo_azione: tipoAzione as ActionType,
      stato: 'PENDING' as any,
      parametri: params,
    }

    onSave(actionData)
  }

  const renderParamsForm = () => {
    switch (tipoAzione) {
      case ActionType.BOZZA_RISPOSTA:
        return (
          <div className="space-y-4">
            <div>
              <label className="label">Destinatario *</label>
              <input
                type="email"
                className="input"
                value={params.to || ''}
                onChange={(e) => setParams({ ...params, to: e.target.value })}
                required
                placeholder="email@example.com"
              />
            </div>
            <div>
              <label className="label">Oggetto *</label>
              <input
                type="text"
                className="input"
                value={params.subject || ''}
                onChange={(e) => setParams({ ...params, subject: e.target.value })}
                required
                placeholder="Re: ..."
              />
            </div>
            <div>
              <label className="label">Corpo Email *</label>
              <textarea
                className="input"
                value={params.body || ''}
                onChange={(e) => setParams({ ...params, body: e.target.value })}
                rows={6}
                required
                placeholder="Testo della risposta..."
              />
            </div>
          </div>
        )

      case ActionType.EVENTO_CALENDARIO:
        return (
          <div className="space-y-4">
            <div>
              <label className="label">Titolo Evento *</label>
              <input
                type="text"
                className="input"
                value={params.summary || ''}
                onChange={(e) => setParams({ ...params, summary: e.target.value })}
                required
                placeholder="Convocazione..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Data</label>
                <input
                  type="date"
                  className="input"
                  value={params.date || ''}
                  onChange={(e) => setParams({ ...params, date: e.target.value })}
                />
              </div>
              <div>
                <label className="label">Ora</label>
                <input
                  type="time"
                  className="input"
                  value={params.time || ''}
                  onChange={(e) => setParams({ ...params, time: e.target.value })}
                />
              </div>
            </div>
            <div>
              <label className="label">Luogo</label>
              <input
                type="text"
                className="input"
                value={params.location || ''}
                onChange={(e) => setParams({ ...params, location: e.target.value })}
                placeholder="Sede, indirizzo..."
              />
            </div>
            <div>
              <label className="label">Descrizione</label>
              <textarea
                className="input"
                value={params.description || ''}
                onChange={(e) => setParams({ ...params, description: e.target.value })}
                rows={3}
              />
            </div>
          </div>
        )

      // Google Drive rimosso - non disponibile con account Gmail personale
      // case ActionType.CARICA_SU_DRIVE:
      //   return (...)

      case ActionType.INOLTRA_EMAIL:
        return (
          <div className="space-y-4">
            {/* Delegati della zona (se disponibili) */}
            {delegatiData?.found && delegatiData.delegati?.length > 0 && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <Users className="w-5 h-5 text-blue-600" />
                  <h4 className="font-semibold text-blue-900">
                    Delegati Zona: {delegatiData.zona.nome}
                  </h4>
                </div>
                <p className="text-sm text-blue-700 mb-3">
                  Scuola di {delegatiData.comune} - Seleziona i delegati da notificare:
                </p>
                <div className="space-y-2">
                  {delegatiData.delegati.map((delegato: any) => (
                    <label key={delegato.id} className="flex items-center gap-3 p-2 bg-white rounded border cursor-pointer hover:bg-blue-50">
                      <input
                        type="checkbox"
                        checked={selectedDelegati.includes(delegato.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedDelegati([...selectedDelegati, delegato.id])
                            // Aggiungi email ai parametri
                            const emails = params.to ? params.to.split(',').map((e: string) => e.trim()) : []
                            if (!emails.includes(delegato.email)) {
                              emails.push(delegato.email)
                              setParams({ ...params, to: emails.join(', ') })
                            }
                          } else {
                            setSelectedDelegati(selectedDelegati.filter(id => id !== delegato.id))
                            // Rimuovi email dai parametri
                            const emails = params.to ? params.to.split(',').map((e: string) => e.trim()) : []
                            setParams({ ...params, to: emails.filter((e: string) => e !== delegato.email).join(', ') })
                          }
                        }}
                        className="w-4 h-4"
                      />
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{delegato.nome_completo}</p>
                        <p className="text-sm text-gray-600">{delegato.email}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}

            <div>
              <label className="label">Inoltra a (Email) *</label>
              <input
                type="text"
                className="input"
                value={params.to || ''}
                onChange={(e) => setParams({ ...params, to: e.target.value })}
                required
                placeholder="destinatario@example.com, altro@example.com"
              />
              <p className="text-xs text-gray-500 mt-1">
                Puoi inserire più email separate da virgola
              </p>
            </div>
            <div>
              <label className="label">CC (opzionale)</label>
              <input
                type="text"
                className="input"
                value={params.cc || ''}
                onChange={(e) => setParams({ ...params, cc: e.target.value })}
                placeholder="copia@example.com"
              />
            </div>
            <div>
              <label className="label">Nota aggiuntiva</label>
              <textarea
                className="input"
                value={params.note || ''}
                onChange={(e) => setParams({ ...params, note: e.target.value })}
                rows={3}
                placeholder="Messaggio aggiuntivo da includere..."
              />
            </div>
          </div>
        )

      default:
        return (
          <p className="text-sm text-gray-500 py-4">
            Seleziona un tipo di azione per configurare i parametri
          </p>
        )
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            Nuova Azione Manuale
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <label className="label">Tipo Azione *</label>
            <select
              className="input"
              value={tipoAzione}
              onChange={(e) => {
                setTipoAzione(e.target.value as ActionType)
                setParams({}) // Reset params quando cambia tipo
              }}
              required
            >
              <option value="">Seleziona un'azione...</option>
              {actionTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {tipoAzione && (
            <div className="border-t border-gray-200 pt-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Parametri Azione
              </h3>
              {renderParamsForm()}
            </div>
          )}

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
              disabled={!tipoAzione}
            >
              Crea Azione
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
