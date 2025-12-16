/**
 * Pagina Staff per visualizzazione calendario e gestione prenotazioni
 *
 * Include:
 * - Vista panoramica di tutto lo staff
 * - Calendario singolo staff
 * - Lista prenotazioni assegnate
 *
 * NOTA: La gestione delle disponibilità è nel pannello Admin
 */

import { useState, useMemo, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Calendar as CalendarIcon,
  Check,
  X,
  User,
  Users,
  Phone,
  Mail,
  FileText,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  MapPin,
  RefreshCw,
  Clock,
  FileDown
} from 'lucide-react'
import toast from 'react-hot-toast'
import { format, parseISO, startOfWeek, endOfWeek, addWeeks, isSameDay, addDays } from 'date-fns'
import { it } from 'date-fns/locale'
import { bookingStaffApi, bookingAdminApi } from '../lib/api'
import type {
  BookingDisponibilita,
  BookingSlot,
  BookingPrenotazione,
  BookingStaff as BookingStaffType
} from '../types'

type View = 'panoramica' | 'calendario' | 'prenotazioni'

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
  const [activeView, setActiveView] = useState<View>('panoramica')
  const [currentWeekStart, setCurrentWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }))
  const [selectedStaffId, setSelectedStaffId] = useState<number | null>(null)
  const [showSaturday, setShowSaturday] = useState(false)
  const [showSunday, setShowSunday] = useState(false)

  const weekEnd = useMemo(() => endOfWeek(currentWeekStart, { weekStartsOn: 1 }), [currentWeekStart])

  // === QUERIES ===

  const { data: staffList } = useQuery({
    queryKey: ['booking-staff-list'],
    queryFn: () => bookingAdminApi.getStaff().then(r => r.data),
  })

  // Auto-select first staff when list loads (for calendario view)
  useEffect(() => {
    if (staffList && (staffList as BookingStaffType[]).length > 0 && !selectedStaffId) {
      setSelectedStaffId((staffList as BookingStaffType[])[0].id)
    }
  }, [staffList, selectedStaffId])

  // Fetch disponibilità per TUTTI gli staff (per panoramica)
  const { data: allDisponibilita, isLoading: loadingAllDisp } = useQuery({
    queryKey: ['all-staff-disponibilita', currentWeekStart],
    queryFn: async () => {
      if (!staffList) return {}
      const results: Record<number, BookingDisponibilita[]> = {}
      for (const staff of (staffList as BookingStaffType[])) {
        try {
          const res = await bookingStaffApi.getDisponibilita(staff.id, {
            data_da: format(currentWeekStart, 'yyyy-MM-dd'),
            data_a: format(weekEnd, 'yyyy-MM-dd'),
          })
          results[staff.id] = res.data as BookingDisponibilita[]
        } catch {
          results[staff.id] = []
        }
      }
      return results
    },
    enabled: !!staffList && activeView === 'panoramica',
  })

  // Fetch slots per TUTTI gli staff (per panoramica - vedere occupazione)
  const { data: allSlots, isLoading: loadingAllSlots } = useQuery({
    queryKey: ['all-staff-slots', currentWeekStart],
    queryFn: async () => {
      if (!staffList) return {}
      const results: Record<number, BookingSlot[]> = {}
      for (const staff of (staffList as BookingStaffType[])) {
        try {
          const res = await bookingStaffApi.getCalendario(staff.id, {
            data_da: format(currentWeekStart, 'yyyy-MM-dd'),
            data_a: format(weekEnd, 'yyyy-MM-dd'),
          })
          results[staff.id] = res.data as BookingSlot[]
        } catch {
          results[staff.id] = []
        }
      }
      return results
    },
    enabled: !!staffList && activeView === 'panoramica',
  })

  // Fetch per singolo staff (calendario view)
  const { data: disponibilita, isLoading: loadingDisponibilita } = useQuery({
    queryKey: ['staff-disponibilita', selectedStaffId, currentWeekStart],
    queryFn: () => selectedStaffId
      ? bookingStaffApi.getDisponibilita(selectedStaffId, {
          data_da: format(currentWeekStart, 'yyyy-MM-dd'),
          data_a: format(weekEnd, 'yyyy-MM-dd'),
        }).then(r => r.data)
      : Promise.resolve([]),
    enabled: !!selectedStaffId && activeView === 'calendario',
  })

  const { data: calendario, isLoading: loadingCalendario } = useQuery({
    queryKey: ['staff-calendario', selectedStaffId, currentWeekStart],
    queryFn: () => selectedStaffId
      ? bookingStaffApi.getCalendario(selectedStaffId, {
          data_da: format(currentWeekStart, 'yyyy-MM-dd'),
          data_a: format(weekEnd, 'yyyy-MM-dd'),
        }).then(r => r.data)
      : Promise.resolve([]),
    enabled: !!selectedStaffId && activeView === 'calendario',
  })

  const { data: prenotazioniData, isLoading: loadingPrenotazioni, refetch: refetchPrenotazioni } = useQuery({
    queryKey: ['staff-prenotazioni', selectedStaffId],
    queryFn: () => selectedStaffId
      ? bookingStaffApi.getPrenotazioni(selectedStaffId, {
          stato: 'confermata',
        }).then(r => r.data)
      : Promise.resolve({ items: [] }),
    enabled: !!selectedStaffId && activeView === 'prenotazioni',
  })

  const prenotazioni = (prenotazioniData?.items || prenotazioniData || []) as BookingPrenotazione[]

  // === MUTATIONS ===

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

  const handleCompletePrenotazione = (prenotazione: BookingPrenotazione) => {
    const esito = prompt('Esito dell\'appuntamento (opzionale):')
    marcaCompletataMutation.mutate({ id: prenotazione.id, esito: esito || undefined })
  }

  const handleNoShow = (prenotazione: BookingPrenotazione) => {
    if (confirm('Confermi che l\'utente non si è presentato?')) {
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
      const dayOfWeek = current.getDay() // 0=domenica, 6=sabato
      const isSaturday = dayOfWeek === 6
      const isSunday = dayOfWeek === 0

      // Filtra sabato e domenica in base ai toggle
      if ((isSaturday && !showSaturday) || (isSunday && !showSunday)) {
        current = addDays(current, 1)
        continue
      }

      days.push(new Date(current))
      current = addDays(current, 1)
    }
    return days
  }, [currentWeekStart, showSaturday, showSunday])

  // Calcola numero colonne per la griglia (reserved for future use)
  void (weekDays.length + 1) // +1 per colonna orario

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
    <div className="space-y-6 print:space-y-2">
      {/* Header - hidden in print */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 print:hidden">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
            Area Staff
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Visualizza disponibilità e gestisci prenotazioni
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          {/* Staff selector (solo per calendario e prenotazioni) */}
          {activeView !== 'panoramica' && (
            <select
              value={selectedStaffId || ''}
              onChange={e => setSelectedStaffId(parseInt(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm font-medium"
            >
              {(staffList as BookingStaffType[] || []).map(s => (
                <option key={s.id} value={s.id}>
                  {s.nome} {s.cognome}
                </option>
              ))}
            </select>
          )}

          {/* View toggle */}
          <div className="flex rounded-lg border border-gray-300 overflow-hidden">
            {[
              { id: 'panoramica' as View, label: 'Panoramica', icon: Users },
              { id: 'calendario' as View, label: 'Calendario', icon: CalendarIcon },
              { id: 'prenotazioni' as View, label: 'Prenotazioni', icon: FileText },
            ].map((view, idx) => (
              <button
                key={view.id}
                onClick={() => setActiveView(view.id)}
                className={`px-3 py-2 text-sm font-medium flex items-center gap-1.5 ${
                  activeView === view.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                } ${idx > 0 ? 'border-l border-gray-300' : ''}`}
              >
                <view.icon className="w-4 h-4" />
                <span className="hidden sm:inline">{view.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Week navigation - hidden in print */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white rounded-lg p-4 shadow-sm print:hidden">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, -1))}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div className="text-lg font-medium text-gray-900 min-w-[200px] text-center">
            {format(currentWeekStart, 'd MMM', { locale: it })} - {format(weekEnd, 'd MMM yyyy', { locale: it })}
          </div>
          <button
            onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, 1))}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        {/* Toggle Sabato/Domenica + PDF (solo in Panoramica) */}
        {activeView === 'panoramica' && (
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={showSaturday}
                onChange={e => setShowSaturday(e.target.checked)}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded"
              />
              <span className="text-gray-700">Sab</span>
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={showSunday}
                onChange={e => setShowSunday(e.target.checked)}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded"
              />
              <span className="text-gray-700">Dom</span>
            </label>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg"
              title="Stampa/Esporta PDF"
            >
              <FileDown className="w-4 h-4" />
              <span className="hidden sm:inline">PDF</span>
            </button>
          </div>
        )}
      </div>

      {/* Print-only header */}
      <div className="hidden print:block mb-4">
        <h1 className="text-xl font-bold text-center">
          Calendario Prenotazioni SNALS
        </h1>
        <p className="text-center text-gray-600">
          {format(currentWeekStart, 'd MMMM', { locale: it })} - {format(weekEnd, 'd MMMM yyyy', { locale: it })}
        </p>
      </div>

      {/* PANORAMICA VIEW - Timetable per fascia oraria */}
      {activeView === 'panoramica' && (
        <div className="card overflow-x-auto">
          {(loadingAllDisp || loadingAllSlots) ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : (
            (() => {
              const staffTyped = (staffList as BookingStaffType[] || [])

              // Genera fasce orarie fisse da 08:00 a 20:00 ogni 30 minuti
              const generateTimeSlots = () => {
                const slots: string[] = []
                for (let hour = 8; hour < 20; hour++) {
                  slots.push(`${hour.toString().padStart(2, '0')}:00`)
                  slots.push(`${hour.toString().padStart(2, '0')}:30`)
                }
                return slots
              }
              const timeSlots = generateTimeSlots()

              // Funzione per verificare se un orario è coperto da una disponibilità
              const isTimeInDisponibilita = (time: string, disp: BookingDisponibilita) => {
                const oraInizio = disp.ora_inizio.slice(0, 5)
                const oraFine = disp.ora_fine.slice(0, 5)
                return time >= oraInizio && time < oraFine
              }

              // Funzione per ottenere lo staff disponibile per un orario e giorno
              const getStaffForTimeAndDay = (time: string, dateStr: string) => {
                const staffForSlot: { staff: BookingStaffType; disp: BookingDisponibilita; slots: BookingSlot[] }[] = []

                staffTyped.forEach(staff => {
                  const staffDisp = allDisponibilita?.[staff.id] || []
                  const staffSlots = allSlots?.[staff.id] || []

                  // Trova disponibilità che coprono questo orario
                  const matchingDisp = staffDisp.find(d =>
                    d.data === dateStr && isTimeInDisponibilita(time, d)
                  )

                  if (matchingDisp) {
                    // Trova slots per questo giorno e orario
                    const daySlots = staffSlots.filter(s => {
                      const slotDate = format(parseISO(s.data_ora_inizio), 'yyyy-MM-dd')
                      const slotTime = format(parseISO(s.data_ora_inizio), 'HH:mm')
                      return slotDate === dateStr && slotTime === time
                    })
                    staffForSlot.push({ staff, disp: matchingDisp, slots: daySlots })
                  }
                })

                return staffForSlot
              }

              return (
                <div className="print:min-w-0" style={{ minWidth: weekDays.length > 5 ? '800px' : '600px' }}>
                  {/* Header con giorni */}
                  <div
                    className="grid gap-1 mb-2"
                    style={{ gridTemplateColumns: `100px repeat(${weekDays.length}, 1fr)` }}
                  >
                    <div className="p-2 font-medium text-gray-700 text-sm flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      Orario
                    </div>
                    {weekDays.map(day => {
                      const isToday = isSameDay(day, new Date())
                      return (
                        <div
                          key={day.toISOString()}
                          className={`p-2 text-center rounded ${isToday ? 'bg-primary-100 text-primary-700' : 'bg-gray-100'}`}
                        >
                          <div className="text-xs font-medium uppercase">
                            {format(day, 'EEE', { locale: it })}
                          </div>
                          <div className="text-lg font-semibold">
                            {format(day, 'd')}
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  {/* Righe per ogni fascia oraria (30 min) */}
                  {timeSlots.map(time => (
                    <div
                      key={time}
                      className="grid gap-1 mb-0.5"
                      style={{ gridTemplateColumns: `100px repeat(${weekDays.length}, 1fr)` }}
                    >
                      {/* Fascia oraria */}
                      <div className="p-1 flex items-center gap-1 bg-gray-50 rounded text-xs">
                        <Clock className="w-3 h-3 text-gray-400" />
                        <span className="font-medium text-gray-700">{time}</span>
                      </div>

                      {/* Celle per ogni giorno */}
                      {weekDays.map(day => {
                        const dateStr = format(day, 'yyyy-MM-dd')
                        const staffForSlot = getStaffForTimeAndDay(time, dateStr)
                        const hasStaff = staffForSlot.length > 0

                        // Calcola statistiche
                        let totalBooked = 0
                        let totalFree = 0
                        let totalSlots = 0
                        staffForSlot.forEach(({ slots }) => {
                          const booked = slots.filter(s => s.stato === 'prenotato').length
                          const free = slots.filter(s => s.stato === 'libero').length
                          totalBooked += booked
                          totalFree += free
                          totalSlots += slots.length
                        })

                        // Determina lo stato della cella
                        let cellClass = 'bg-gray-50 border-gray-200' // Nessuno staff = vuoto

                        if (hasStaff) {
                          if (totalSlots === 0) {
                            // Staff disponibile ma nessuno slot generato
                            cellClass = 'bg-blue-50 border-blue-200'
                          } else if (totalBooked > 0 && totalFree === 0) {
                            // Tutti occupati
                            cellClass = 'bg-orange-100 border-orange-300'
                          } else if (totalBooked > 0) {
                            // Parzialmente occupato
                            cellClass = 'bg-yellow-50 border-yellow-200'
                          } else {
                            // Tutti liberi
                            cellClass = 'bg-green-50 border-green-200'
                          }
                        }

                        return (
                          <div
                            key={dateStr}
                            className={`p-1 rounded border min-h-[36px] text-xs ${cellClass}`}
                            title={hasStaff ? staffForSlot.map(s => s.staff.nome).join(', ') : 'Nessuno disponibile'}
                          >
                            {hasStaff && (
                              <div className="flex flex-wrap gap-1 justify-center">
                                {staffForSlot.map(({ staff, slots }) => {
                                  const bookedSlots = slots.filter(s => s.stato === 'prenotato')
                                  const booked = bookedSlots.length
                                  const free = slots.filter(s => s.stato === 'libero').length
                                  const total = slots.length

                                  // Trova il nome del prenotante se c'è uno slot prenotato
                                  const prenotazione = bookedSlots.length > 0 ? (bookedSlots[0] as any).prenotazione : null

                                  // Iniziali staff
                                  const staffInitials = `${staff.nome[0]}${staff.cognome[0]}`

                                  // Codice breve per tipo appuntamento (prime 3 lettere)
                                  const tipoCode = prenotazione?.tipo_appuntamento_nome
                                    ? prenotazione.tipo_appuntamento_nome.substring(0, 3).toUpperCase()
                                    : null
                                  // Codice breve per servizio (prime 3 lettere)
                                  const servizioCode = prenotazione?.servizio_nome
                                    ? prenotazione.servizio_nome.substring(0, 3).toUpperCase()
                                    : null

                                  // Tooltip dettagliato
                                  const titleText = prenotazione
                                    ? `${staff.nome} ${staff.cognome}\n📋 ${prenotazione.contatto_cognome} ${prenotazione.contatto_nome}\n🏷️ ${prenotazione.tipo_appuntamento_nome || 'N/D'}\n📁 ${prenotazione.servizio_nome || 'N/D'}`
                                    : `${staff.nome} ${staff.cognome}${total > 0 ? ` - ${free} liberi su ${total}` : ''}`

                                  // Stile badge in base allo stato
                                  let containerClass = 'bg-blue-100 border-blue-300'
                                  let initialsClass = 'bg-blue-200 text-blue-800'
                                  if (total > 0) {
                                    if (booked === total) {
                                      containerClass = 'bg-orange-100 border-orange-300'
                                      initialsClass = 'bg-orange-300 text-orange-900'
                                    } else if (booked > 0) {
                                      containerClass = 'bg-yellow-100 border-yellow-300'
                                      initialsClass = 'bg-yellow-200 text-yellow-800'
                                    } else {
                                      containerClass = 'bg-green-100 border-green-300'
                                      initialsClass = 'bg-green-200 text-green-800'
                                    }
                                  }

                                  return (
                                    <div
                                      key={staff.id}
                                      className={`flex flex-col items-center rounded border px-1 py-1 min-w-[70px] flex-1 ${containerClass}`}
                                      title={titleText}
                                    >
                                      {/* Riga 1: Iniziali staff */}
                                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${initialsClass}`}>
                                        {staffInitials}
                                      </span>
                                      {/* Riga 2: Nome prenotante (se occupato) */}
                                      {prenotazione && (
                                        <span className="text-[9px] text-orange-800 font-semibold mt-0.5 truncate w-full text-center">
                                          {prenotazione.contatto_nome} {prenotazione.contatto_cognome}
                                        </span>
                                      )}
                                      {/* Riga 3: Servizio e Tipo (codici brevi) */}
                                      {prenotazione && (tipoCode || servizioCode) && (
                                        <div className="flex items-center gap-1 mt-0.5">
                                          {servizioCode && (
                                            <span className="text-[8px] bg-purple-200 text-purple-800 px-1 rounded">
                                              {servizioCode}
                                            </span>
                                          )}
                                          {tipoCode && (
                                            <span
                                              className="text-[8px] px-1 rounded text-white"
                                              style={{ backgroundColor: prenotazione.tipo_appuntamento_colore || '#6b7280' }}
                                            >
                                              {tipoCode}
                                            </span>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  )
                                })}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  ))}

                  {/* Legenda */}
                  <div className="mt-4 pt-4 border-t border-gray-200 flex flex-wrap gap-4 text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded bg-gray-50 border border-gray-200"></div>
                      <span>Nessuno disponibile</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded bg-blue-50 border border-blue-200"></div>
                      <span>Disponibile</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded bg-green-50 border border-green-200"></div>
                      <span>Slot liberi</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded bg-yellow-50 border border-yellow-200"></div>
                      <span>Parzialmente occupato</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded bg-orange-100 border border-orange-300"></div>
                      <span>Tutto occupato</span>
                    </div>
                  </div>
                </div>
              )
            })()
          )}
        </div>
      )}

      {/* CALENDARIO VIEW - Singolo staff */}
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
                          <div className="font-medium text-blue-700 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {d.ora_inizio.slice(0, 5)} - {d.ora_fine.slice(0, 5)}
                          </div>
                          {d.sede && (
                            <div className="text-blue-600 mt-1 truncate flex items-center gap-1">
                              <MapPin className="w-3 h-3" />
                              {d.sede.nome}
                            </div>
                          )}
                        </div>
                      ))}

                      {/* Slots/Prenotazioni */}
                      {daySlots.map(slot => {
                        const isBooked = slot.stato === 'prenotato'
                        const isBlocked = slot.stato === 'bloccato'

                        const prenotazione = (slot as any).prenotazione

                        // Debug log
                        if (isBooked) {
                          console.log('Slot prenotato:', slot.id, 'stato:', slot.stato, 'prenotazione:', prenotazione)
                        }

                        return (
                          <div
                            key={slot.id}
                            className={`p-2 rounded text-xs border ${
                              isBooked
                                ? 'bg-orange-100 border-orange-300 ring-2 ring-orange-400'
                                : isBlocked
                                  ? 'bg-gray-100 border-gray-300'
                                  : 'bg-green-50 border-green-200'
                            }`}
                          >
                            <div className="font-medium flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {format(parseISO(slot.data_ora_inizio), 'HH:mm')}
                            </div>
                            {isBooked && prenotazione ? (
                              <div className="text-orange-700 font-semibold truncate" title={`${prenotazione.contatto_cognome} ${prenotazione.contatto_nome}`}>
                                {prenotazione.contatto_cognome} {prenotazione.contatto_nome}
                              </div>
                            ) : (
                              <div className={`font-semibold ${
                                isBooked ? 'text-orange-700' :
                                isBlocked ? 'text-gray-500' : 'text-green-600'
                              }`}>
                                {isBooked ? '🔒 PRENOTATO' :
                                 isBlocked ? 'Bloccato' : '✓ Libero'}
                              </div>
                            )}
                          </div>
                        )
                      })}

                      {/* Empty state */}
                      {dayDisponibilita.length === 0 && daySlots.length === 0 && (
                        <div className="text-xs text-gray-400 text-center py-4">
                          Nessuna attività
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
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
    </div>
  )
}
