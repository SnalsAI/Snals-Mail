import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Calendar as CalendarIcon, MapPin, Users, Plus, Trash2, Edit } from 'lucide-react'
import toast from 'react-hot-toast'
import { calendarApi } from '../lib/api'
import { format, parseISO } from 'date-fns'
import { it } from 'date-fns/locale'
import EventForm from '../components/EventForm'
import type { CalendarEvent } from '../types'

export default function Calendar() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | undefined>(undefined)

  const { data: events, isLoading } = useQuery({
    queryKey: ['calendar'],
    queryFn: () => calendarApi.getAll().then(res => res.data),
  })

  const createMutation = useMutation({
    mutationFn: (data: Partial<CalendarEvent>) => calendarApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success('Evento creato con successo')
      setShowModal(false)
      setEditingEvent(undefined)
    },
    onError: () => {
      toast.error('Errore nella creazione dell\'evento')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CalendarEvent> }) =>
      calendarApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success('Evento aggiornato con successo')
      setShowModal(false)
      setEditingEvent(undefined)
    },
    onError: () => {
      toast.error('Errore nell\'aggiornamento dell\'evento')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => calendarApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success('Evento eliminato')
    },
  })

  const handleSaveEvent = (data: Partial<CalendarEvent>) => {
    if (editingEvent) {
      updateMutation.mutate({ id: editingEvent.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleEditEvent = (event: CalendarEvent) => {
    setEditingEvent(event)
    setShowModal(true)
  }

  const handleNewEvent = () => {
    setEditingEvent(undefined)
    setShowModal(true)
  }

  const groupedEvents = events?.reduce((acc, event) => {
    const date = format(parseISO(event.data_inizio), 'yyyy-MM-dd')
    if (!acc[date]) acc[date] = []
    acc[date].push(event)
    return acc
  }, {} as Record<string, typeof events>)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Calendario</h1>
          <p className="mt-1 text-sm text-gray-500">
            Visualizza e gestisci eventi e convocazioni
          </p>
        </div>
        <button
          onClick={handleNewEvent}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nuovo Evento
        </button>
      </div>

      <div className="card">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : events && events.length > 0 ? (
          <div className="space-y-6">
            {Object.entries(groupedEvents || {}).sort().reverse().map(([date, dateEvents]) => (
              <div key={date}>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  {format(parseISO(date), 'EEEE, d MMMM yyyy', { locale: it })}
                </h3>
                <div className="space-y-3">
                  {dateEvents.map((event) => (
                    <div
                      key={event.id}
                      className="p-4 border-l-4 border-primary-600 bg-primary-50 rounded-r-lg"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <h4 className="text-base font-semibold text-gray-900 mb-2">
                            {event.titolo}
                          </h4>

                          {event.descrizione && (
                            <p className="text-sm text-gray-600 mb-2">
                              {event.descrizione}
                            </p>
                          )}

                          <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                              <CalendarIcon className="w-4 h-4" />
                              <span>
                                {format(parseISO(event.data_inizio), 'HH:mm')}
                                {event.data_fine && ` - ${format(parseISO(event.data_fine), 'HH:mm')}`}
                              </span>
                            </div>

                            {event.luogo && (
                              <div className="flex items-center gap-1">
                                <MapPin className="w-4 h-4" />
                                <span>{event.luogo}</span>
                              </div>
                            )}

                            {event.scuola && (
                              <div className="flex items-center gap-1">
                                <Users className="w-4 h-4" />
                                <span>{event.scuola}</span>
                              </div>
                            )}
                          </div>

                          {event.partecipanti && event.partecipanti.length > 0 && (
                            <div className="mt-2">
                              <span className="text-xs text-gray-500">
                                Partecipanti: {event.partecipanti.join(', ')}
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-2">
                          {event.google_event_id && (
                            <span className="badge-success">Su Google</span>
                          )}
                          <button
                            onClick={() => handleEditEvent(event)}
                            className="btn-secondary"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => {
                              if (confirm('Sei sicuro di voler eliminare questo evento?')) {
                                deleteMutation.mutate(event.id)
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
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <CalendarIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">Nessun evento in calendario</p>
            <button onClick={handleNewEvent} className="btn-primary">
              Crea il tuo primo evento
            </button>
          </div>
        )}
      </div>

      {/* Event Form Modal */}
      {showModal && (
        <EventForm
          event={editingEvent}
          onSave={handleSaveEvent}
          onClose={() => {
            setShowModal(false)
            setEditingEvent(undefined)
          }}
        />
      )}
    </div>
  )
}
