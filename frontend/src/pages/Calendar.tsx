import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Calendar as CalendarIcon, MapPin, Users, Plus, Trash2, Edit, MessageCircle, Copy, Check, Mail } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import ReactCalendar from 'react-calendar'
import 'react-calendar/dist/Calendar.css'
import { calendarApi } from '../lib/api'
import { format, parseISO, isSameDay } from 'date-fns'
import { it } from 'date-fns/locale'
import EventForm from '../components/EventForm'
import type { CalendarEvent } from '../types'

// Helper per parsare date UTC dal backend e convertirle in ora locale
const parseUTCDate = (dateString: string): Date => {
  // Se la stringa non ha timezone, aggiungi Z per indicare UTC
  if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
    return parseISO(dateString + 'Z')
  }
  return parseISO(dateString)
}

export default function Calendar() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [showModal, setShowModal] = useState(false)
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | undefined>(undefined)
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [viewMode, setViewMode] = useState<'calendar' | 'list' | 'whatsapp'>('calendar')
  const [copied, setCopied] = useState(false)

  const { data: eventsResponse, isLoading } = useQuery({
    queryKey: ['calendar'],
    queryFn: () => calendarApi.getAll().then(res => res.data),
  })

  const events: CalendarEvent[] = Array.isArray(eventsResponse) ? eventsResponse : []

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

  // Get events for selected date
  const eventsForSelectedDate = events.filter(event =>
    isSameDay(parseUTCDate(event.data_inizio), selectedDate)
  )

  // Get dates with events for tile content
  const getDatesWithEvents = () => {
    const dates = new Set<string>()
    events.forEach(event => {
      const eventDate = format(parseUTCDate(event.data_inizio), 'yyyy-MM-dd')
      dates.add(eventDate)
    })
    return dates
  }

  const datesWithEvents = getDatesWithEvents()

  // Tile content to show event indicators
  const tileContent = ({ date, view }: { date: Date; view: string }) => {
    if (view === 'month') {
      const dateStr = format(date, 'yyyy-MM-dd')
      const hasEvents = datesWithEvents.has(dateStr)

      if (hasEvents) {
        const dayEvents = events.filter(event =>
          isSameDay(parseUTCDate(event.data_inizio), date)
        )

        return (
          <div className="flex justify-center gap-1 mt-1">
            {dayEvents.slice(0, 3).map((_, i) => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-primary-600" />
            ))}
          </div>
        )
      }
    }
    return null
  }

  // Tile class name for styling
  const tileClassName = ({ date, view }: { date: Date; view: string }) => {
    if (view === 'month') {
      const dateStr = format(date, 'yyyy-MM-dd')
      if (datesWithEvents.has(dateStr)) {
        return 'has-events'
      }
    }
    return null
  }

  const groupedEvents = events?.reduce((acc: Record<string, CalendarEvent[]>, event: CalendarEvent) => {
    const date = format(parseUTCDate(event.data_inizio), 'yyyy-MM-dd')
    if (!acc[date]) acc[date] = []
    acc[date].push(event)
    return acc
  }, {} as Record<string, CalendarEvent[]>)

  // Ordina eventi all'interno di ogni giorno per orario
  if (groupedEvents) {
    Object.keys(groupedEvents).forEach(date => {
      groupedEvents[date].sort((a: CalendarEvent, b: CalendarEvent) =>
        parseUTCDate(a.data_inizio).getTime() - parseUTCDate(b.data_inizio).getTime()
      )
    })
  }

  // Generate WhatsApp message
  const generateWhatsAppMessage = () => {
    if (!events || events.length === 0) {
      return '*CALENDARIO EVENTI SNALS*\n\nNessun evento in programma.'
    }

    // Filter only future events (from today onwards)
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    const futureEvents = events.filter(event => {
      const eventDate = parseUTCDate(event.data_inizio)
      return eventDate >= today
    })

    if (futureEvents.length === 0) {
      return '*CALENDARIO EVENTI SNALS*\n\nNessun evento futuro in programma.'
    }

    // Sort events by date
    const sortedEvents = [...futureEvents].sort((a, b) =>
      parseISO(a.data_inizio).getTime() - parseISO(b.data_inizio).getTime()
    )

    // Group by date
    const grouped = sortedEvents.reduce((acc: Record<string, CalendarEvent[]>, event: CalendarEvent) => {
      const date = format(parseUTCDate(event.data_inizio), 'EEEE d MMMM yyyy', { locale: it })
      if (!acc[date]) acc[date] = []
      acc[date].push(event)
      return acc
    }, {} as Record<string, CalendarEvent[]>)

    let message = '*CALENDARIO EVENTI SNALS*\n'
    message += `_Aggiornato al ${format(new Date(), 'd/MM/yyyy', { locale: it })}_\n`
    message += '━━━━━━━━━━━━━━━━━━━━\n\n'

    Object.entries(grouped).forEach(([date, dateEvents]: [string, CalendarEvent[]], index: number) => {
      // Capitalize first letter
      const capitalizedDate = date.charAt(0).toUpperCase() + date.slice(1)
      message += `*${capitalizedDate}*\n`

      dateEvents.forEach((event: CalendarEvent) => {
        const startTime = format(parseUTCDate(event.data_inizio), 'HH:mm')
        const endTime = event.data_fine ? format(parseUTCDate(event.data_fine), 'HH:mm') : null

        message += `\n${startTime}${endTime ? ` - ${endTime}` : ''}\n`
        message += `${event.titolo}\n`

        if (event.luogo) {
          message += `Luogo: ${event.luogo}\n`
        }

        if (event.scuola) {
          message += `Scuola: ${event.scuola}\n`
        }

        // Mostra la sintesi motivo
        const sintesiMotivo = (event as any).sintesi_motivo
        if (sintesiMotivo) {
          message += `_${sintesiMotivo}_\n`
        }
      })

      message += '\n'
      if (index < Object.entries(grouped).length - 1) {
        message += '- - - - - - - - - - - - - - -\n\n'
      }
    })

    message += '━━━━━━━━━━━━━━━━━━━━\n'
    message += `*Totale: ${futureEvents.length} event${futureEvents.length !== 1 ? 'i' : 'o'}*`

    return message
  }

  const copyToClipboard = async () => {
    const message = generateWhatsAppMessage()
    try {
      // Prova prima con Clipboard API
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(message)
      } else {
        // Fallback per mobile/browser vecchi
        const textArea = document.createElement('textarea')
        textArea.value = message
        textArea.style.position = 'fixed'
        textArea.style.left = '-9999px'
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
      }
      setCopied(true)
      toast.success('Messaggio copiato negli appunti!')
      setTimeout(() => setCopied(false), 3000)
    } catch (err) {
      console.error('Errore copia:', err)
      toast.error('Errore durante la copia')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Calendario</h1>
          <p className="mt-1 text-sm text-gray-500 hidden sm:block">
            Visualizza e gestisci eventi e convocazioni
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
          {/* Toggle view mode */}
          <div className="flex rounded-lg border border-gray-300 overflow-hidden">
            <button
              onClick={() => setViewMode('calendar')}
              className={`flex-1 sm:flex-none px-3 sm:px-4 py-2 text-sm font-medium ${
                viewMode === 'calendar'
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              <CalendarIcon className="w-4 h-4 inline sm:mr-2" />
              <span className="hidden sm:inline">Calendario</span>
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`flex-1 sm:flex-none px-3 sm:px-4 py-2 text-sm font-medium border-l border-gray-300 ${
                viewMode === 'list'
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              <span className="sm:hidden">📋</span>
              <span className="hidden sm:inline">Lista</span>
            </button>
            <button
              onClick={() => setViewMode('whatsapp')}
              className={`flex-1 sm:flex-none px-3 sm:px-4 py-2 text-sm font-medium border-l border-gray-300 ${
                viewMode === 'whatsapp'
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              <MessageCircle className="w-4 h-4 inline sm:mr-2" />
              <span className="hidden sm:inline">WhatsApp</span>
            </button>
          </div>

          <button
            onClick={handleNewEvent}
            className="btn-primary flex items-center justify-center gap-2"
          >
            <Plus className="w-4 h-4" />
            <span className="sm:inline">Nuovo</span>
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : viewMode === 'whatsapp' ? (
        /* WhatsApp Message View */
        <div className="card max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <MessageCircle className="w-6 h-6 text-green-600" />
              <h2 className="text-xl font-semibold text-gray-900">
                Messaggio WhatsApp
              </h2>
            </div>
            <button
              onClick={copyToClipboard}
              className={`btn-primary flex items-center gap-2 ${
                copied ? 'bg-green-600 hover:bg-green-700' : ''
              }`}
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4" />
                  Copiato!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copia Messaggio
                </>
              )}
            </button>
          </div>

          <div className="bg-gray-50 rounded-lg p-6 border-2 border-gray-200">
            <div className="bg-white rounded-lg shadow-sm p-6 font-mono text-sm whitespace-pre-wrap break-words">
              {generateWhatsAppMessage()}
            </div>
          </div>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-start gap-3">
              <MessageCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-blue-900">
                <p className="font-medium mb-1">Come usare:</p>
                <ol className="list-decimal list-inside space-y-1 text-blue-800">
                  <li>Clicca su "Copia Messaggio" per copiare il testo negli appunti</li>
                  <li>Apri WhatsApp sul tuo dispositivo</li>
                  <li>Incolla il messaggio nella chat o nel gruppo desiderato</li>
                  <li>Invia! Il messaggio manterrà la formattazione</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      ) : viewMode === 'calendar' ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Calendar View */}
          <div className="lg:col-span-2 card">
            <style>{`
              .react-calendar {
                width: 100%;
                border: none;
                font-family: inherit;
              }
              .react-calendar__navigation {
                display: flex;
                height: 44px;
                margin-bottom: 1em;
              }
              .react-calendar__navigation button {
                min-width: 44px;
                background: none;
                font-size: 16px;
                font-weight: 600;
                color: #374151;
              }
              .react-calendar__navigation button:enabled:hover,
              .react-calendar__navigation button:enabled:focus {
                background-color: #f3f4f6;
              }
              .react-calendar__month-view__weekdays {
                text-align: center;
                text-transform: uppercase;
                font-weight: 600;
                font-size: 0.75em;
                color: #6b7280;
              }
              .react-calendar__month-view__days__day {
                height: 80px;
                padding: 0.5rem;
              }
              .react-calendar__tile {
                max-width: 100%;
                padding: 10px 6px;
                background: none;
                text-align: center;
                line-height: 16px;
                font-size: 0.875rem;
              }
              .react-calendar__tile:enabled:hover,
              .react-calendar__tile:enabled:focus {
                background-color: #f3f4f6;
                border-radius: 6px;
              }
              .react-calendar__tile--now {
                background: #eff6ff;
                border-radius: 6px;
              }
              .react-calendar__tile--active {
                background: #2563eb !important;
                color: white !important;
                border-radius: 6px;
              }
              .react-calendar__tile.has-events {
                font-weight: 600;
              }
              .react-calendar__month-view__days__day--weekend {
                color: #dc2626;
              }
              .react-calendar__month-view__days__day--neighboringMonth {
                color: #d1d5db;
              }
            `}</style>
            <ReactCalendar
              onChange={(value) => setSelectedDate(value as Date)}
              value={selectedDate}
              locale="it-IT"
              tileContent={tileContent}
              tileClassName={tileClassName}
            />
          </div>

          {/* Selected Date Events */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              {format(selectedDate, 'EEEE, d MMMM yyyy', { locale: it })}
            </h3>

            {eventsForSelectedDate.length > 0 ? (
              <div className="space-y-3">
                {eventsForSelectedDate.map((event) => (
                  <div
                    key={event.id}
                    className="p-3 border-l-4 border-primary-600 bg-primary-50 rounded-r-lg"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-semibold text-gray-900 truncate">
                          {event.titolo}
                        </h4>

                        <div className="flex items-center gap-2 text-xs text-gray-600 mt-1">
                          <CalendarIcon className="w-3 h-3 flex-shrink-0" />
                          <span>
                            {format(parseUTCDate(event.data_inizio), 'HH:mm')}
                            {event.data_fine && ` - ${format(parseUTCDate(event.data_fine), 'HH:mm')}`}
                          </span>
                        </div>

                        {event.luogo && (
                          <div className="flex items-center gap-2 text-xs text-gray-600 mt-1">
                            <MapPin className="w-3 h-3 flex-shrink-0" />
                            <span className="truncate">{event.luogo}</span>
                          </div>
                        )}

                        {event.scuola && (
                          <div className="flex items-center gap-2 text-xs text-gray-600 mt-1">
                            <Users className="w-3 h-3 flex-shrink-0" />
                            <span className="truncate">{event.scuola}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-1 flex-shrink-0">
                        {event.email_id && (
                          <button
                            onClick={() => navigate(`/emails/${event.email_id}`)}
                            className="p-1 hover:bg-blue-100 rounded"
                            title="Vedi email"
                          >
                            <Mail className="w-3 h-3 text-blue-600" />
                          </button>
                        )}
                        <button
                          onClick={() => handleEditEvent(event)}
                          className="p-1 hover:bg-primary-100 rounded"
                          title="Modifica"
                        >
                          <Edit className="w-3 h-3 text-gray-600" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm('Sei sicuro di voler eliminare questo evento?')) {
                              deleteMutation.mutate(event.id)
                            }
                          }}
                          className="p-1 hover:bg-red-100 rounded"
                          title="Elimina"
                          disabled={deleteMutation.isPending}
                        >
                          <Trash2 className="w-3 h-3 text-red-600" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <CalendarIcon className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Nessun evento per questa data</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* List View */
        <div className="card">
          {events && events.length > 0 ? (
            <div className="space-y-6">
              {Object.entries(groupedEvents || {}).sort(([a], [b]) => a.localeCompare(b)).map(([date, dateEvents]: [string, CalendarEvent[]]) => (
                <div key={date}>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">
                    {format(parseISO(date), 'EEEE, d MMMM yyyy', { locale: it })}
                  </h3>
                  <div className="space-y-3">
                    {dateEvents.map((event) => (
                      <div
                        key={event.id}
                        className="p-3 sm:p-4 border-l-4 border-primary-600 bg-primary-50 rounded-r-lg"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm sm:text-base font-semibold text-gray-900 mb-2">
                              {event.titolo}
                            </h4>

                            {event.descrizione && (
                              <p className="text-xs sm:text-sm text-gray-600 mb-2 line-clamp-2">
                                {event.descrizione}
                              </p>
                            )}

                            <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm text-gray-600">
                              <div className="flex items-center gap-1">
                                <CalendarIcon className="w-3 h-3 sm:w-4 sm:h-4" />
                                <span>
                                  {format(parseUTCDate(event.data_inizio), 'HH:mm')}
                                  {event.data_fine && ` - ${format(parseUTCDate(event.data_fine), 'HH:mm')}`}
                                </span>
                              </div>

                              {event.luogo && (
                                <div className="flex items-center gap-1">
                                  <MapPin className="w-3 h-3 sm:w-4 sm:h-4" />
                                  <span className="truncate max-w-[150px] sm:max-w-none">{event.luogo}</span>
                                </div>
                              )}

                              {event.scuola && (
                                <div className="flex items-center gap-1">
                                  <Users className="w-3 h-3 sm:w-4 sm:h-4" />
                                  <span className="truncate max-w-[150px] sm:max-w-none">{event.scuola}</span>
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

                          <div className="flex items-center gap-2 pt-2 sm:pt-0 border-t sm:border-t-0 border-primary-200">
                            {event.google_event_id && (
                              <span className="badge-success text-xs">Google</span>
                            )}
                            {event.email_id && (
                              <button
                                onClick={() => navigate(`/emails/${event.email_id}`)}
                                className="btn-secondary p-2"
                                title="Vedi email originale"
                              >
                                <Mail className="w-4 h-4" />
                              </button>
                            )}
                            <button
                              onClick={() => handleEditEvent(event)}
                              className="btn-secondary p-2"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => {
                                if (confirm('Sei sicuro di voler eliminare questo evento?')) {
                                  deleteMutation.mutate(event.id)
                                }
                              }}
                              className="btn-danger p-2"
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
      )}

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
