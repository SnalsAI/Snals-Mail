/**
 * Pagina per gestire una prenotazione esistente tramite token
 */

import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Calendar,
  Clock,
  MapPin,
  CheckCircle,
  XCircle,
  AlertCircle,
  ArrowLeft,
  Loader2,
  Edit,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import toast from 'react-hot-toast'
import { format, parseISO, startOfWeek, endOfWeek, addWeeks, isSameDay, addDays } from 'date-fns'
import { it } from 'date-fns/locale'
import { bookingPublicApi } from '../lib/api'

export default function BookingManage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showCancelForm, setShowCancelForm] = useState(false)
  const [cancelReason, setCancelReason] = useState('')
  const [showModifyForm, setShowModifyForm] = useState(false)
  const [selectedNewSlot, setSelectedNewSlot] = useState<number | null>(null)
  const [currentWeekStart, setCurrentWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }))

  // Carica dettagli prenotazione
  const { data: prenotazione, isLoading, error } = useQuery({
    queryKey: ['booking-detail', token],
    queryFn: () => bookingPublicApi.getPrenotazioneByToken(token!).then(r => r.data),
    enabled: !!token,
  })

  // Carica slot disponibili per la modifica
  const weekEnd = useMemo(() => endOfWeek(currentWeekStart, { weekStartsOn: 1 }), [currentWeekStart])
  const { data: availableSlots, isLoading: loadingSlots } = useQuery({
    queryKey: ['available-slots-modify', prenotazione?.staff_id, prenotazione?.tipo_appuntamento_id, currentWeekStart],
    queryFn: () => prenotazione?.staff_id
      ? bookingPublicApi.getSlotsDisponibili({
          sede_id: prenotazione.slot?.sede_id,
          tipo_appuntamento_id: prenotazione.slot?.tipo_appuntamento_id,
          data_da: format(currentWeekStart, 'yyyy-MM-dd'),
          data_a: format(weekEnd, 'yyyy-MM-dd'),
        }).then((r: any) => r.data)
      : Promise.resolve([]),
    enabled: showModifyForm && !!prenotazione?.staff_id,
  })

  // Mutation per annullamento
  const cancelMutation = useMutation({
    mutationFn: () => bookingPublicApi.annullaPrenotazione(token!, cancelReason || undefined),
    onSuccess: () => {
      toast.success('Prenotazione annullata con successo')
      queryClient.invalidateQueries({ queryKey: ['booking-detail', token] })
      setShowCancelForm(false)
    },
    onError: () => {
      toast.error('Errore nell\'annullamento della prenotazione')
    }
  })

  // Mutation per spostamento
  const moveMutation = useMutation({
    mutationFn: () => bookingPublicApi.spostaPrenotazione(token!, selectedNewSlot!),
    onSuccess: () => {
      toast.success('Prenotazione spostata con successo')
      queryClient.invalidateQueries({ queryKey: ['booking-detail', token] })
      setShowModifyForm(false)
      setSelectedNewSlot(null)
    },
    onError: (error: any) => {
      const msg = error.response?.data?.detail || 'Errore nello spostamento'
      toast.error(msg)
    }
  })

  // Raggruppa slot per giorno
  const slotsByDay = useMemo(() => {
    if (!availableSlots) return {}
    return (availableSlots as any[]).reduce((acc, slot) => {
      const date = format(parseISO(slot.data_ora_inizio), 'yyyy-MM-dd')
      if (!acc[date]) acc[date] = []
      acc[date].push(slot)
      return acc
    }, {} as Record<string, any[]>)
  }, [availableSlots])

  // Giorni della settimana
  const weekDays = useMemo(() => {
    const days = []
    let current = new Date(currentWeekStart)
    for (let i = 0; i < 7; i++) {
      days.push(new Date(current))
      current = addDays(current, 1)
    }
    return days
  }, [currentWeekStart])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary-600 mx-auto mb-4" />
          <p className="text-gray-600">Caricamento prenotazione...</p>
        </div>
      </div>
    )
  }

  if (error || !prenotazione) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Prenotazione non trovata</h1>
          <p className="text-gray-600 mb-6">
            Il link potrebbe essere scaduto o la prenotazione non esiste.
          </p>
          <button
            onClick={() => navigate('/booking')}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            Nuova Prenotazione
          </button>
        </div>
      </div>
    )
  }

  const isCancelled = prenotazione.stato === 'annullata'
  const isPast = prenotazione.data_ora && new Date(prenotazione.data_ora) < new Date()

  const getStatusBadge = () => {
    switch (prenotazione.stato) {
      case 'confermata':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
            <CheckCircle className="w-4 h-4" />
            Confermata
          </span>
        )
      case 'annullata':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
            <XCircle className="w-4 h-4" />
            Annullata
          </span>
        )
      case 'completata':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
            <CheckCircle className="w-4 h-4" />
            Completata
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
            {prenotazione.stato}
          </span>
        )
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/booking')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-5 h-5" />
            Torna alle prenotazioni
          </button>
          <h1 className="text-3xl font-bold text-gray-900">La tua prenotazione</h1>
        </div>

        {/* Card principale */}
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
          {/* Status header */}
          <div className={`p-6 ${isCancelled ? 'bg-red-50' : 'bg-green-50'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Stato prenotazione</p>
                {getStatusBadge()}
              </div>
              {prenotazione.data_ora && (
                <div className="text-right">
                  <p className="text-2xl font-bold text-gray-900">
                    {format(parseISO(prenotazione.data_ora), 'HH:mm')}
                  </p>
                  <p className="text-gray-600">
                    {format(parseISO(prenotazione.data_ora), 'EEEE d MMMM yyyy', { locale: it })}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Dettagli */}
          <div className="p-6 space-y-6">
            {/* Tipo appuntamento */}
            {prenotazione.tipo_appuntamento && (
              <div className="flex items-start gap-4">
                <div className="p-3 bg-primary-100 rounded-xl">
                  <Calendar className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Tipo appuntamento</p>
                  <p className="text-lg font-semibold text-gray-900">{prenotazione.tipo_appuntamento}</p>
                </div>
              </div>
            )}

            {/* Sede */}
            {prenotazione.sede_nome && (
              <div className="flex items-start gap-4">
                <div className="p-3 bg-blue-100 rounded-xl">
                  <MapPin className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Sede</p>
                  <p className="text-lg font-semibold text-gray-900">{prenotazione.sede_nome}</p>
                  {prenotazione.sede_indirizzo && (
                    <p className="text-gray-600">{prenotazione.sede_indirizzo}</p>
                  )}
                </div>
              </div>
            )}

            {/* Durata */}
            {prenotazione.durata_minuti && (
              <div className="flex items-start gap-4">
                <div className="p-3 bg-purple-100 rounded-xl">
                  <Clock className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Durata</p>
                  <p className="text-lg font-semibold text-gray-900">{prenotazione.durata_minuti} minuti</p>
                </div>
              </div>
            )}

            {/* Istruzioni */}
            {prenotazione.istruzioni && (
              <div className="p-4 bg-blue-50 rounded-xl border border-blue-200">
                <p className="text-sm font-medium text-blue-800 mb-1">Istruzioni</p>
                <p className="text-blue-700">{prenotazione.istruzioni}</p>
              </div>
            )}

            {/* Note */}
            {prenotazione.note_utente && (
              <div className="p-4 bg-gray-50 rounded-xl">
                <p className="text-sm font-medium text-gray-700 mb-1">Le tue note</p>
                <p className="text-gray-600">{prenotazione.note_utente}</p>
              </div>
            )}
          </div>

          {/* Azioni */}
          {!isCancelled && !isPast && (
            <div className="p-6 bg-gray-50 border-t">
              {!showCancelForm && !showModifyForm ? (
                <div className="flex flex-col sm:flex-row gap-3">
                  <button
                    onClick={() => setShowModifyForm(true)}
                    className="flex-1 px-6 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors font-medium flex items-center justify-center gap-2"
                  >
                    <Edit className="w-5 h-5" />
                    Modifica Data/Ora
                  </button>
                  <button
                    onClick={() => setShowCancelForm(true)}
                    className="flex-1 px-6 py-3 border border-red-300 text-red-600 rounded-xl hover:bg-red-50 transition-colors font-medium"
                  >
                    Annulla Prenotazione
                  </button>
                </div>
              ) : showModifyForm ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900">Seleziona nuovo orario</h3>
                    <button
                      onClick={() => { setShowModifyForm(false); setSelectedNewSlot(null) }}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      ✕
                    </button>
                  </div>

                  {/* Navigazione settimana */}
                  <div className="flex items-center justify-between bg-white rounded-lg p-3 border">
                    <button
                      onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, -1))}
                      className="p-2 hover:bg-gray-100 rounded-lg"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <div className="text-sm font-medium text-gray-900">
                      {format(currentWeekStart, 'd MMM', { locale: it })} - {format(weekEnd, 'd MMM yyyy', { locale: it })}
                    </div>
                    <button
                      onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, 1))}
                      className="p-2 hover:bg-gray-100 rounded-lg"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Griglia slot */}
                  {loadingSlots ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                    </div>
                  ) : (
                    <div className="grid grid-cols-7 gap-1">
                      {weekDays.map(day => {
                        const dateStr = format(day, 'yyyy-MM-dd')
                        const daySlots = slotsByDay[dateStr] || []
                        const isToday = isSameDay(day, new Date())
                        const isPastDay = day < new Date() && !isToday

                        return (
                          <div key={dateStr} className="min-h-[100px]">
                            <div className={`text-center p-1 rounded-t text-xs ${
                              isToday ? 'bg-primary-100 text-primary-700' : isPastDay ? 'bg-gray-100 text-gray-400' : 'bg-gray-100'
                            }`}>
                              <div className="font-medium uppercase">
                                {format(day, 'EEE', { locale: it })}
                              </div>
                              <div className="text-lg font-semibold">
                                {format(day, 'd')}
                              </div>
                            </div>
                            <div className="border border-t-0 border-gray-200 rounded-b p-1 space-y-1 min-h-[80px]">
                              {daySlots.length === 0 ? (
                                <p className="text-[10px] text-gray-400 text-center py-2">-</p>
                              ) : (
                                daySlots.map((slot: any) => (
                                  <button
                                    key={slot.id}
                                    onClick={() => setSelectedNewSlot(slot.id)}
                                    className={`w-full text-xs py-1 px-1 rounded transition-colors ${
                                      selectedNewSlot === slot.id
                                        ? 'bg-primary-600 text-white'
                                        : 'bg-green-50 text-green-700 hover:bg-green-100 border border-green-200'
                                    }`}
                                  >
                                    {format(parseISO(slot.data_ora_inizio), 'HH:mm')}
                                  </button>
                                ))
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}

                  {/* Conferma spostamento */}
                  <div className="flex gap-3 pt-2">
                    <button
                      onClick={() => { setShowModifyForm(false); setSelectedNewSlot(null) }}
                      className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100"
                    >
                      Annulla
                    </button>
                    <button
                      onClick={() => moveMutation.mutate()}
                      disabled={!selectedNewSlot || moveMutation.isPending}
                      className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {moveMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                      Conferma Spostamento
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-start gap-3 p-4 bg-yellow-50 rounded-xl border border-yellow-200">
                    <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-yellow-800">Sei sicuro di voler annullare?</p>
                      <p className="text-sm text-yellow-700">Questa azione non può essere annullata.</p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Motivo annullamento (opzionale)
                    </label>
                    <textarea
                      value={cancelReason}
                      onChange={e => setCancelReason(e.target.value)}
                      rows={2}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                      placeholder="Indica il motivo dell'annullamento..."
                    />
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => setShowCancelForm(false)}
                      className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-100 transition-colors font-medium"
                    >
                      Annulla
                    </button>
                    <button
                      onClick={() => cancelMutation.mutate()}
                      disabled={cancelMutation.isPending}
                      className="flex-1 px-6 py-3 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {cancelMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                      Conferma Annullamento
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Messaggio se annullata */}
          {isCancelled && (
            <div className="p-6 bg-red-50 border-t border-red-100">
              <div className="flex items-start gap-3">
                <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-red-800">Prenotazione annullata</p>
                  <p className="text-sm text-red-700">
                    Questa prenotazione è stata annullata.
                    <button
                      onClick={() => navigate('/booking')}
                      className="ml-1 underline hover:no-underline"
                    >
                      Effettua una nuova prenotazione
                    </button>
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Messaggio se passata */}
          {isPast && !isCancelled && (
            <div className="p-6 bg-gray-50 border-t">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-gray-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-gray-800">Appuntamento passato</p>
                  <p className="text-sm text-gray-600">
                    Questo appuntamento è già avvenuto.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>SNALS Taranto - Segreteria Provinciale</p>
        </div>
      </div>
    </div>
  )
}
