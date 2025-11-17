import { useState } from 'react'
import { X } from 'lucide-react'
import { ActionType } from '../types'
import type { Action } from '../types'

interface ActionFormProps {
  emailId?: number
  onSave: (action: Partial<Action>) => void
  onClose: () => void
}

export default function ActionForm({ emailId, onSave, onClose }: ActionFormProps) {
  const [tipoAzione, setTipoAzione] = useState<ActionType | ''>('')
  const [params, setParams] = useState<Record<string, any>>({})

  const actionTypes = [
    { value: ActionType.BOZZA_RISPOSTA, label: 'Crea Bozza Risposta' },
    { value: ActionType.CREA_EVENTO_CALENDARIO, label: 'Crea Evento Calendario' },
    { value: ActionType.CARICA_SU_DRIVE, label: 'Carica Allegati su Drive' },
    { value: ActionType.INOLTRA_EMAIL, label: 'Inoltra Email' },
  ]

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

      case ActionType.CREA_EVENTO_CALENDARIO:
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

      case ActionType.CARICA_SU_DRIVE:
        return (
          <div className="space-y-4">
            <div>
              <label className="label">Nome Cartella Drive *</label>
              <input
                type="text"
                className="input"
                value={params.folder_name || ''}
                onChange={(e) => setParams({ ...params, folder_name: e.target.value })}
                required
                placeholder="SNALS Allegati"
              />
            </div>
            <p className="text-sm text-gray-500">
              Gli allegati dell'email verranno caricati nella cartella specificata
            </p>
          </div>
        )

      case ActionType.INOLTRA_EMAIL:
        return (
          <div className="space-y-4">
            <div>
              <label className="label">Inoltra a (Email) *</label>
              <input
                type="email"
                className="input"
                value={params.to || ''}
                onChange={(e) => setParams({ ...params, to: e.target.value })}
                required
                placeholder="destinatario@example.com"
              />
            </div>
            <div>
              <label className="label">CC (opzionale)</label>
              <input
                type="email"
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
