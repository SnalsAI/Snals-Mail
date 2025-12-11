/**
 * Pagina Staff per gestione disponibilita e prenotazioni
 *
 * Include:
 * - Calendario disponibilita
 * - Lista prenotazioni assegnate
 * - Gestione stato prenotazioni
 */

import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Calendar as CalendarIcon,
  Clock,
  Plus,
  Edit,
  Trash2,
  Check,
  X,
  User,
  Phone,
  Mail,
  FileText,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  MapPin,
  RefreshCw
} from 'lucide-react'
import toast from 'react-hot-toast'
import { format, parseISO, startOfWeek, endOfWeek, addWeeks, isSameDay, addDays } from 'date-fns'
import { it } from 'date-fns/locale'
import { bookingStaffApi, bookingAdminApi } from '../lib/api'
import type {
  BookingDisponibilita,
  BookingSlot,
  BookingPrenotazione,
  BookingSede,
  StatoPrenotazione
} from '../types'

// Simula staff_id - in produzione verrebbe dal token JWT
const CURRENT_STAFF_ID = 1

type View = 'disponibilita' | 'prenotazioni' | 'calendario'

const statoLabels: Record<string, string> = {
  confermata: 'Confermata',
  annullata_utente: 'Annullata',
  annullata_ufficio: 'Annullata',
  completata: 'Completata',
  no_show: 'No Show',
}

const statoColors: Record<string, string> = {
  confermata: 'bg-green-100 text-green-800 border-green-200',
  annullata_utente: 'bg-red-100 text-red-800 border-red-200',
  annullata_ufficio: 'bg-red-100 text-red-800 border-red-200',
  completata: 'bg-blue-100 text-blue-800 border-blue-200',
  no_show: 'bg-yellow-100 text-yellow-800 border-yellow-200',
}

export default function BookingStaff() {
  const queryClient = useQueryClient()
  const [activeView, setActiveView] = useState<View>('calendario')
  const [currentWeekStart, setCurrentWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }))
  const [showDisponibilitaModal, setShowDisponibilitaModal] = useState(false)
  const [selectedDate, setSelectedDate] = useState<Date | null>(null)

  const weekEnd = useMemo(() => endOfWeek(currentWeekStart, { weekStartsOn: 1 }), [currentWeekStart])

  // === QUERIES ===

  const { data: sedi } = useQuery({
    queryKey: ['booking-sedi'],
    queryFn: () => bookingAdminApi.getSedi().then(r => r.data),
  })

  const { data: disponibilita, isLoading: loadingDisponibilita } = useQuery({
    queryKey: ['staff-disponibilita', CURRENT_STAFF_ID, currentWeekStart],
    queryFn: () => bookingStaffApi.getDisponibilita(CURRENT_STAFF_ID, {
      data_da: format(currentWeekStart, 'yyyy-MM-dd'),
      data_a: format(weekEnd, 'yyyy-MM-dd'),
    }).then(r => r.data),
  })

  const { data: calendario, isLoading: loadingCalendario } = useQuery({
    queryKey: ['staff-calendario', CURRENT_STAFF_ID, currentWeekStart],
    queryFn: () => bookingStaffApi.getCalendario(CURRENT_STAFF_ID, {
      data_da: format(currentWeekStart, 'yyyy-MM-dd'),
      data_a: format(weekEnd, 'yyyy-MM-dd'),
    }).then(r => r.data),
  })

  const { data: prenotazioniData, isLoading: loadingPrenotazioni, refetch: refetchPrenotazioni } = useQuery({
    queryKey: ['staff-prenotazioni', CURRENT_STAFF_ID],
    queryFn: () => bookingStaffApi.getPrenotazioni(CURRENT_STAFF_ID, {
      stato: 'confermata',
    }).then(r => r.data),
  })

  const prenotazioni = (prenotazioniData?.items || prenotazioniData || []) as BookingPrenotazione[]

  // === MUTATIONS ===

  const creaDisponibilitaMutation = useMutation({
    mutationFn: bookingStaffApi.creaDisponibilita,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-disponibilita'] })
      toast.success('Disponibilita creata')
      setShowDisponibilitaModal(false)
      setSelectedDate(null)
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Errore nella creazione'
      toast.error(message)
    },
  })

  const eliminaDisponibilitaMutation = useMutation({
    mutationFn: bookingStaffApi.eliminaDisponibilita,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-disponibilita'] })
      toast.success('Disponibilita eliminata')
    },
    onError: () => toast.error('Errore nell\'eliminazione'),
  })

  const marcaCompletataMutation = useMutation({
    mutationFn: ({ id, esito }: { id: number; esito?: string }) =>
      bookingStaffApi.marcaCompletata(id, esito),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-prenotazioni'] })
      queryClient.invalidateQueries({ queryKey: ['staff-calendario'] })
      toast.success('Prenotazione completata')
    },
    onError: () => toast.error('Errore nel completamento'),
  })

  const marcaNoShowMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note?: string }) =>
      bookingStaffApi.marcaNoShow(id, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-prenotazioni'] })
      queryClient.invalidateQueries({ queryKey: ['staff-calendario'] })
      toast.success('Prenotazione marcata come no-show')
    },
    onError: () => toast.error('Errore'),
  })

  const annullaPrenotazioneMutation = useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo?: string }) =>
      bookingStaffApi.annullaPrenotazione(id, motivo),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-prenotazioni'] })
      queryClient.invalidateQueries({ queryKey: ['staff-calendario'] })
      toast.success('Prenotazione annullata')
    },
    onError: () => toast.error('Errore nell\'annullamento'),
  })

  // === HANDLERS ===

  const handleAddDisponibilita = (date: Date) => {
    setSelectedDate(date)
    setShowDisponibilitaModal(true)
  }

  const handleSaveDisponibilita = (data: {
    sede_id: number
    ora_inizio: string
    ora_fine: string
    note?: string
  }) => {
    if (!selectedDate) return
    creaDisponibilitaMutation.mutate({
      staff_id: CURRENT_STAFF_ID,
      sede_id: data.sede_id,
      data: format(selectedDate, 'yyyy-MM-dd'),
      ora_inizio: data.ora_inizio,
      ora_fine: data.ora_fine,
      note: data.note,
    })
  }

  const handleCompletePrenotazione = (prenotazione: BookingPrenotazione) => {
    const esito = prompt('Esito dell\'appuntamento (opzionale):')
    marcaCompletataMutation.mutate({ id: prenotazione.id, esito: esito || undefined })
  }

  const handleNoShow = (prenotazione: BookingPrenotazione) => {
    if (confirm('Confermi che l\'utente non si e presentato?')) {
      marcaNoShowMutation.mutate({ id: prenotazione.id })
    }
  }

  const handleCancelPrenotazione = (prenotazione: BookingPrenotazione) => {
    const motivo = prompt('Motivo dell\'annullamento:')
    if (motivo) {
      annullaPrenotazioneMutation.mutate({ id: prenotazione.id, motivo })
    }
  }

  // === COMPUTED ===

  const weekDays = useMemo(() => {
    const days = []
    let current = new Date(currentWeekStart)
    for (let i = 0; i < 7; i++) {
      days.push(new Date(current))
      current = addDays(current, 1)
    }
    return days
  }, [currentWeekStart])

  const disponibilitaByDate = useMemo(() => {
    if (!disponibilita) return {}
    return (disponibilita as BookingDisponibilita[]).reduce((acc, d) => {
      const date = d.data
      if (!acc[date]) acc[date] = []
      acc[date].push(d)
      return acc
    }, {} as Record<string, BookingDisponibilita[]>)
  }, [disponibilita])

  const slotsByDate = useMemo(() => {
    if (!calendario) return {}
    return (calendario as BookingSlot[]).reduce((acc, slot) => {
      const date = format(parseISO(slot.data_ora_inizio), 'yyyy-MM-dd')
      if (!acc[date]) acc[date] = []
      acc[date].push(slot)
      return acc
    }, {} as Record<string, BookingSlot[]>)
  }, [calendario])

  // === RENDER ===

  const isLoading = loadingDisponibilita || loadingCalendario

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
            Area Staff
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Gestisci le tue disponibilita e prenotazioni
          </p>
        </div>

        {/* View toggle */}
        <div className="flex rounded-lg border border-gray-300 overflow-hidden">
          {[
            { id: 'calendario' as View, label: 'Calendario' },
            { id: 'disponibilita' as View, label: 'Disponibilita' },
            { id: 'prenotazioni' as View, label: 'Prenotazioni' },
          ].map(view => (
            <button
              key={view.id}
              onClick={() => setActiveView(view.id)}
              className={`px-4 py-2 text-sm font-medium ${
                activeView === view.id
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              } ${view.id !== 'calendario' ? 'border-l border-gray-300' : ''}`}
            >
              {view.label}
            </button>
          ))}
        </div>
      </div>

      {/* Week navigation */}
      <div className="flex items-center justify-between bg-white rounded-lg p-4 shadow-sm">
        <button
          onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, -1))}
          className="p-2 hover:bg-gray-100 rounded-lg"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="text-lg font-medium text-gray-900">
          {format(currentWeekStart, 'd MMM', { locale: it })} - {format(weekEnd, 'd MMM yyyy', { locale: it })}
        </div>
        <button
          onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, 1))}
          className="p-2 hover:bg-gray-100 rounded-lg"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* CALENDARIO VIEW */}
      {activeView === 'calendario' && (
        <div className="card">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : (
            <div className="grid grid-cols-7 gap-2">
              {weekDays.map(day => {
                const dateStr = format(day, 'yyyy-MM-dd')
                const dayDisponibilita = disponibilitaByDate[dateStr] || []
                const daySlots = slotsByDate[dateStr] || []
                const isToday = isSameDay(day, new Date())
                const isPast = day < new Date(new Date().setHours(0, 0, 0, 0))

                return (
                  <div key={dateStr} className="min-h-[250px]">
                    {/* Day header */}
                    <div className={`text-center p-2 rounded-t-lg ${
                      isToday ? 'bg-primary-100 text-primary-700' : 'bg-gray-100'
                    }`}>
                      <div className="text-xs uppercase font-medium">
                        {format(day, 'EEE', { locale: it })}
                      </div>
                      <div className="text-lg font-semibold">
                        {format(day, 'd')}
                      </div>
                    </div>

                    {/* Day content */}
                    <div className="border border-t-0 border-gray-200 rounded-b-lg p-2 space-y-2 min-h-[200px]">
                      {/* Disponibilita */}
                      {dayDisponibilita.map(d => (
                        <div key={d.id} className="p-2 bg-blue-50 border border-blue-200 rounded text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-blue-700">
                              {d.ora_inizio.slice(0, 5)} - {d.ora_fine.slice(0, 5)}
                            </span>
                            <button
                              onClick={() => {
                                if (confirm('Eliminare questa disponibilita?')) {
                                  eliminaDisponibilitaMutation.mutate(d.id)
                                }
                              }}
                              className="text-red-400 hover:text-red-600"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                          {d.sede && (
                            <div className="text-blue-600 mt-1 truncate">
                              <MapPin className="w-3 h-3 inline" /> {d.sede.nome}
                            </div>
                          )}
                        </div>
                      ))}

                      {/* Slots/Prenotazioni */}
                      {daySlots.map(slot => (
                        <div
                          key={slot.id}
                          className={`p-2 rounded text-xs border ${
                            slot.stato === 'prenotato'
                              ? 'bg-green-50 border-green-200'
                              : slot.stato === 'bloccato'
                                ? 'bg-gray-100 border-gray-300'
                                : 'bg-white border-gray-200'
                          }`}
                        >
                          <div className="font-medium">
                            {format(parseISO(slot.data_ora_inizio), 'HH:mm')}
                          </div>
                          <div className={`${
                            slot.stato === 'prenotato' ? 'text-green-700' :
                            slot.stato === 'bloccato' ? 'text-gray-500' : 'text-gray-400'
                          }`}>
                            {slot.stato === 'prenotato' ? 'Prenotato' :
                             slot.stato === 'bloccato' ? 'Bloccato' : 'Libero'}
                          </div>
                        </div>
                      ))}

                      {/* Add button */}
                      {!isPast && (
                        <button
                          onClick={() => handleAddDisponibilita(day)}
                          className="w-full p-2 border-2 border-dashed border-gray-300 rounded text-gray-400 hover:border-primary-500 hover:text-primary-500 transition-colors"
                        >
                          <Plus className="w-4 h-4 mx-auto" />
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* DISPONIBILITA VIEW */}
      {activeView === 'disponibilita' && (
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Le mie Disponibilita</h2>
            <button
              onClick={() => setShowDisponibilitaModal(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Aggiungi
            </button>
          </div>

          {loadingDisponibilita ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : (disponibilita as BookingDisponibilita[] || []).length === 0 ? (
            <div className="text-center py-12">
              <CalendarIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">Nessuna disponibilita configurata per questa settimana</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {(disponibilita as BookingDisponibilita[]).map(d => (
                <div key={d.id} className="flex items-center justify-between py-4">
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <div className="text-xs text-gray-500 uppercase">
                        {format(parseISO(d.data), 'EEE', { locale: it })}
                      </div>
                      <div className="text-lg font-semibold text-gray-900">
                        {format(parseISO(d.data), 'd')}
                      </div>
                      <div className="text-xs text-gray-500">
                        {format(parseISO(d.data), 'MMM', { locale: it })}
                      </div>
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">
                        {d.ora_inizio.slice(0, 5)} - {d.ora_fine.slice(0, 5)}
                      </div>
                      {d.sede && (
                        <div className="text-sm text-gray-500 flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {d.sede.nome}
                        </div>
                      )}
                      {d.note && (
                        <div className="text-sm text-gray-400 mt-1">{d.note}</div>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      if (confirm('Eliminare questa disponibilita?')) {
                        eliminaDisponibilitaMutation.mutate(d.id)
                      }
                    }}
                    className="p-2 text-red-400 hover:text-red-600"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* PRENOTAZIONI VIEW */}
      {activeView === 'prenotazioni' && (
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Prenotazioni Assegnate</h2>
            <button
              onClick={() => refetchPrenotazioni()}
              className="btn-secondary p-2"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {loadingPrenotazioni ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : prenotazioni.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">Nessuna prenotazione confermata</p>
            </div>
          ) : (
            <div className="space-y-4">
              {prenotazioni.map(p => (
                <div key={p.id} className={`p-4 rounded-lg border ${statoColors[p.stato]}`}>
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                    {/* Info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <CalendarIcon className="w-5 h-5 text-gray-400" />
                        <div>
                          {p.slot && (
                            <>
                              <div className="font-medium text-gray-900">
                                {format(parseISO(p.slot.data_ora_inizio), 'EEEE d MMMM yyyy', { locale: it })}
                              </div>
                              <div className="text-sm text-gray-600">
                                {format(parseISO(p.slot.data_ora_inizio), 'HH:mm')} - {format(parseISO(p.slot.data_ora_fine), 'HH:mm')}
                              </div>
                            </>
                          )}
                        </div>
                      </div>

                      {p.contatto && (
                        <div className="ml-8 space-y-1 text-sm">
                          <div className="flex items-center gap-2 text-gray-700">
                            <User className="w-4 h-4" />
                            {p.contatto.nome} {p.contatto.cognome}
                          </div>
                          <div className="flex items-center gap-2 text-gray-500">
                            <Mail className="w-4 h-4" />
                            {p.contatto.email}
                          </div>
                          {p.contatto.telefono && (
                            <div className="flex items-center gap-2 text-gray-500">
                              <Phone className="w-4 h-4" />
                              {p.contatto.telefono}
                            </div>
                          )}
                        </div>
                      )}

                      {p.motivo && (
                        <div className="ml-8 mt-2 text-sm text-gray-600">
                          <strong>Motivo:</strong> {p.motivo}
                        </div>
                      )}

                      {p.note_utente && (
                        <div className="ml-8 mt-1 text-sm text-gray-500">
                          <strong>Note:</strong> {p.note_utente}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    {p.stato === 'confermata' && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleCompletePrenotazione(p)}
                          className="btn-primary flex items-center gap-1 text-sm"
                          title="Marca come completata"
                        >
                          <Check className="w-4 h-4" />
                          Completata
                        </button>
                        <button
                          onClick={() => handleNoShow(p)}
                          className="btn-secondary flex items-center gap-1 text-sm"
                          title="Utente non presentato"
                        >
                          <AlertCircle className="w-4 h-4" />
                          No Show
                        </button>
                        <button
                          onClick={() => handleCancelPrenotazione(p)}
                          className="btn-danger flex items-center gap-1 text-sm"
                          title="Annulla"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    )}

                    {p.stato !== 'confermata' && (
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${statoColors[p.stato]}`}>
                        {statoLabels[p.stato]}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* MODAL Disponibilita */}
      {showDisponibilitaModal && (
        <DisponibilitaModal
          date={selectedDate}
          sedi={(sedi as BookingSede[]) || []}
          onSave={handleSaveDisponibilita}
          onClose={() => { setShowDisponibilitaModal(false); setSelectedDate(null) }}
          isLoading={creaDisponibilitaMutation.isPending}
        />
      )}
    </div>
  )
}

// === MODAL COMPONENT ===

function DisponibilitaModal({ date, sedi, onSave, onClose, isLoading }: {
  date: Date | null
  sedi: BookingSede[]
  onSave: (data: { sede_id: number; ora_inizio: string; ora_fine: string; note?: string }) => void
  onClose: () => void
  isLoading: boolean
}) {
  const [formData, setFormData] = useState({
    sede_id: sedi.length > 0 ? sedi[0].id : 0,
    ora_inizio: '09:00',
    ora_fine: '13:00',
    note: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.sede_id) {
      toast.error('Seleziona una sede')
      return
    }
    onSave(formData)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">
            Aggiungi Disponibilita
            {date && (
              <span className="text-gray-500 font-normal ml-2">
                - {format(date, 'd MMMM yyyy', { locale: it })}
              </span>
            )}
          </h3>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sede *</label>
              <select
                value={formData.sede_id}
                onChange={e => setFormData({ ...formData, sede_id: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                required
              >
                <option value="">Seleziona sede</option>
                {sedi.filter(s => s.attivo).map(sede => (
                  <option key={sede.id} value={sede.id}>{sede.nome}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ora Inizio *</label>
                <input
                  type="time"
                  value={formData.ora_inizio}
                  onChange={e => setFormData({ ...formData, ora_inizio: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ora Fine *</label>
                <input
                  type="time"
                  value={formData.ora_fine}
                  onChange={e => setFormData({ ...formData, ora_fine: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Note</label>
              <textarea
                value={formData.note}
                onChange={e => setFormData({ ...formData, note: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                rows={2}
                placeholder="Note opzionali..."
              />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <button type="button" onClick={onClose} className="btn-secondary">
                Annulla
              </button>
              <button type="submit" disabled={isLoading} className="btn-primary">
                {isLoading ? 'Salvataggio...' : 'Salva'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
