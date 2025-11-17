import { useQuery } from '@tanstack/react-query'
import { Calendar as CalendarIcon, MapPin, Users } from 'lucide-react'
import { calendarApi } from '../lib/api'
import { format, parseISO } from 'date-fns'
import { it } from 'date-fns/locale'

export default function Calendar() {
  const { data: events, isLoading } = useQuery({
    queryKey: ['calendar'],
    queryFn: () => calendarApi.getAll().then(res => res.data),
  })

  const groupedEvents = events?.reduce((acc, event) => {
    const date = format(parseISO(event.data_inizio), 'yyyy-MM-dd')
    if (!acc[date]) acc[date] = []
    acc[date].push(event)
    return acc
  }, {} as Record<string, typeof events>)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Calendario</h1>
        <p className="mt-1 text-sm text-gray-500">
          Visualizza eventi e convocazioni
        </p>
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
                      <div className="flex items-start justify-between">
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

                        <div className="ml-4">
                          {event.google_event_id && (
                            <span className="badge-success">Su Google Calendar</span>
                          )}
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
            <p className="text-gray-500">Nessun evento in calendario</p>
          </div>
        )}
      </div>
    </div>
  )
}
