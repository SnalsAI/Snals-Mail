import { useState } from 'react'
import { X } from 'lucide-react'
import type { CalendarEvent } from '../types'

interface EventFormProps {
  event?: CalendarEvent
  onSave: (event: Partial<CalendarEvent>) => void
  onClose: () => void
}

export default function EventForm({ event, onSave, onClose }: EventFormProps) {
  const [formData, setFormData] = useState({
    titolo: event?.titolo || '',
    descrizione: event?.descrizione || '',
    data_inizio: event?.data_inizio ? event.data_inizio.split('T')[0] + 'T' + event.data_inizio.split('T')[1].substring(0, 5) : '',
    data_fine: event?.data_fine ? event.data_fine.split('T')[0] + 'T' + event.data_fine.split('T')[1].substring(0, 5) : '',
    luogo: event?.luogo || '',
    scuola: event?.scuola || '',
    partecipanti: event?.partecipanti?.join(', ') || '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const eventData: Partial<CalendarEvent> = {
      titolo: formData.titolo,
      descrizione: formData.descrizione || undefined,
      data_inizio: formData.data_inizio,
      data_fine: formData.data_fine || undefined,
      luogo: formData.luogo || undefined,
      scuola: formData.scuola || undefined,
      partecipanti: formData.partecipanti
        ? formData.partecipanti.split(',').map(p => p.trim()).filter(Boolean)
        : undefined,
      stato: 'PENDING',
    }

    onSave(eventData)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            {event ? 'Modifica Evento' : 'Nuovo Evento'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <label className="label">Titolo *</label>
            <input
              type="text"
              className="input"
              value={formData.titolo}
              onChange={(e) => setFormData({ ...formData, titolo: e.target.value })}
              required
              placeholder="es: Convocazione SNALS"
            />
          </div>

          <div>
            <label className="label">Descrizione</label>
            <textarea
              className="input"
              value={formData.descrizione}
              onChange={(e) => setFormData({ ...formData, descrizione: e.target.value })}
              rows={3}
              placeholder="Descrizione dettagliata dell'evento"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Data e Ora Inizio *</label>
              <input
                type="datetime-local"
                className="input"
                value={formData.data_inizio}
                onChange={(e) => setFormData({ ...formData, data_inizio: e.target.value })}
                required
              />
            </div>

            <div>
              <label className="label">Data e Ora Fine</label>
              <input
                type="datetime-local"
                className="input"
                value={formData.data_fine}
                onChange={(e) => setFormData({ ...formData, data_fine: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="label">Luogo</label>
            <input
              type="text"
              className="input"
              value={formData.luogo}
              onChange={(e) => setFormData({ ...formData, luogo: e.target.value })}
              placeholder="es: Sede SNALS, Via Roma 1"
            />
          </div>

          <div>
            <label className="label">Scuola/Istituto</label>
            <input
              type="text"
              className="input"
              value={formData.scuola}
              onChange={(e) => setFormData({ ...formData, scuola: e.target.value })}
              placeholder="es: IC Manzoni"
            />
          </div>

          <div>
            <label className="label">Partecipanti</label>
            <input
              type="text"
              className="input"
              value={formData.partecipanti}
              onChange={(e) => setFormData({ ...formData, partecipanti: e.target.value })}
              placeholder="Email separate da virgola: mario@snals.it, luigi@snals.it"
            />
            <p className="mt-1 text-sm text-gray-500">
              Inserisci gli indirizzi email separati da virgola
            </p>
          </div>

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
              {event ? 'Salva Modifiche' : 'Crea Evento'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
