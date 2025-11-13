import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Calendar as CalendarIcon, Plus, Trash2, RefreshCw } from 'lucide-react'
import { calendarService } from '@/services/calendarService'
import type { EventoCalendario } from '@/types'
import PageHeader from '@/components/PageHeader'
import LoadingSpinner from '@/components/LoadingSpinner'
import EmptyState from '@/components/EmptyState'
import { formatDate, formatDateTime } from '@/lib/utils'
import toast from 'react-hot-toast'

export default function Calendar() {
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<EventoCalendario | null>(null)

  const { data: events, isLoading } = useQuery({
    queryKey: ['events'],
    queryFn: () => calendarService.getEvents(),
  })

  const syncMutation = useMutation({
    mutationFn: calendarService.syncWithGoogle,
    onSuccess: () => {
      toast.success('Calendario sincronizzato')
      queryClient.invalidateQueries({ queryKey: ['events'] })
    },
    onError: () => {
      toast.error('Errore sincronizzazione')
    },
  })

  const deleteEventMutation = useMutation({
    mutationFn: (id: number) => calendarService.deleteEvent(id),
    onSuccess: () => {
      toast.success('Evento eliminato')
      queryClient.invalidateQueries({ queryKey: ['events'] })
      setSelectedEvent(null)
    },
  })

  const sortedEvents = events?.sort((a, b) =>
    new Date(a.data_inizio).getTime() - new Date(b.data_inizio).getTime()
  )

  return (
    <div className="p-8">
      <PageHeader
        title="Calendario"
        description="Gestisci eventi e appuntamenti"
        actions={
          <>
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="btn btn-secondary"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
              Sync Google
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn btn-primary"
            >
              <Plus className="w-4 h-4 mr-2" />
              Nuovo Evento
            </button>
          </>
        }
      />

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : sortedEvents && sortedEvents.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {sortedEvents.map((event) => (
            <div key={event.id} className="card">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {event.titolo}
                  </h3>
                  <div className="space-y-1 text-sm text-gray-600">
                    <p>
                      <span className="font-medium">Inizio:</span>{' '}
                      {formatDateTime(event.data_inizio)}
                    </p>
                    <p>
                      <span className="font-medium">Fine:</span>{' '}
                      {formatDateTime(event.data_fine)}
                    </p>
                    {event.luogo && (
                      <p>
                        <span className="font-medium">Luogo:</span> {event.luogo}
                      </p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => deleteEventMutation.mutate(event.id)}
                  className="text-red-600 hover:text-red-700"
                  disabled={deleteEventMutation.isPending}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {event.descrizione && (
                <p className="text-sm text-gray-700 mb-3">{event.descrizione}</p>
              )}

              {event.partecipanti && event.partecipanti.length > 0 && (
                <div className="text-sm">
                  <span className="font-medium text-gray-700">Partecipanti:</span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {event.partecipanti.map((p, i) => (
                      <span
                        key={i}
                        className="px-2 py-1 bg-gray-100 rounded text-xs"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {event.google_event_id && (
                <p className="text-xs text-gray-400 mt-3">
                  Sincronizzato con Google Calendar
                </p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="card">
          <EmptyState
            icon={CalendarIcon}
            title="Nessun evento"
            description="Non ci sono eventi in calendario. Crea il primo evento o sincronizza con Google Calendar."
            action={
              <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
                <Plus className="w-4 h-4 mr-2" />
                Crea Evento
              </button>
            }
          />
        </div>
      )}
    </div>
  )
}
