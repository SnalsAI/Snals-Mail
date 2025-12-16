/**
 * Pagina pubblica per prenotazione appuntamenti
 *
 * Flusso:
 * 1. Selezione servizio (opzionale)
 * 2. Selezione sede
 * 3. Selezione tipo appuntamento
 * 4. Selezione data/slot
 * 5. Compilazione dati contatto
 * 6. Conferma prenotazione
 */

import { useState, useMemo } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Calendar as CalendarIcon,
  MapPin,
  Clock,
  User,
  Mail,
  Phone,
  FileText,
  ChevronLeft,
  ChevronRight,
  Check,
  AlertCircle,
  Building,
  Briefcase,
  School
} from 'lucide-react'
import toast from 'react-hot-toast'
import { format, parseISO, startOfWeek, endOfWeek, addWeeks, isSameDay } from 'date-fns'
import { it } from 'date-fns/locale'
import { bookingPublicApi } from '../lib/api'
import type {
  BookingSede,
  BookingTipoAppuntamento,
  BookingSlot,
  BookingServizio,
  PrenotazioneCreatePublic
} from '../types'

// Steps del wizard
type Step = 'selezione' | 'slot' | 'dati' | 'conferma' | 'successo'

export default function BookingPublic() {
  // Wizard state
  const [currentStep, setCurrentStep] = useState<Step>('selezione')

  // Selection state
  const [selectedServizio, setSelectedServizio] = useState<number | null>(null)
  const [selectedSede, setSelectedSede] = useState<number | null>(null)
  const [selectedTipo, setSelectedTipo] = useState<number | null>(null)
  const [selectedSlot, setSelectedSlot] = useState<BookingSlot | null>(null)

  // Calendar state
  const [currentWeekStart, setCurrentWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }))

  // Form state
  const [formData, setFormData] = useState<Partial<PrenotazioneCreatePublic>>({
    consenso_privacy: false
  })

  // Scuola selection state
  const [selectedComune, setSelectedComune] = useState<string | null>(null)
  const [selectedScuolaCodice, setSelectedScuolaCodice] = useState<string | null>(null)

  // Result state
  const [bookingToken, setBookingToken] = useState<string | null>(null)

  // === QUERIES ===

  const { data: servizi, isLoading: loadingCampagne } = useQuery({
    queryKey: ['booking-servizi'],
    queryFn: () => bookingPublicApi.getServizi().then(r => r.data),
  })

  const { data: sedi, isLoading: loadingSedi } = useQuery({
    queryKey: ['booking-sedi'],
    queryFn: () => bookingPublicApi.getSedi().then(r => r.data),
  })

  const { data: tipiAppuntamento, isLoading: loadingTipi } = useQuery({
    queryKey: ['booking-tipi', selectedServizio],
    queryFn: () => bookingPublicApi.getTipiAppuntamento(selectedServizio || undefined).then(r => r.data),
    enabled: true,
  })

  const weekEnd = useMemo(() => endOfWeek(currentWeekStart, { weekStartsOn: 1 }), [currentWeekStart])

  const { data: slots, isLoading: loadingSlots } = useQuery({
    queryKey: ['booking-slots', selectedSede, selectedTipo, currentWeekStart],
    queryFn: () => bookingPublicApi.getSlotsDisponibili({
      sede_id: selectedSede || undefined,
      tipo_appuntamento_id: selectedTipo || undefined,
      servizio_id: selectedServizio || undefined,
      data_da: format(currentWeekStart, 'yyyy-MM-dd'),
      data_a: format(weekEnd, 'yyyy-MM-dd'),
    }).then(r => r.data),
    enabled: currentStep === 'slot' && !!selectedTipo,
  })

  // Tutte le scuole dal database esistente
  const { data: allScuoleData } = useQuery({
    queryKey: ['all-schools'],
    queryFn: () => bookingPublicApi.getAllScuole().then(r => r.data),
  })

  // Estrai comuni unici dalle scuole
  const comuni = useMemo(() => {
    if (!allScuoleData?.schools) return []
    const uniqueComuni = [...new Set(allScuoleData.schools.map(s => s.comune))]
    return uniqueComuni.sort()
  }, [allScuoleData])

  // Scuole filtrate per comune selezionato
  const scuole = useMemo(() => {
    if (!allScuoleData?.schools || !selectedComune) return []
    return allScuoleData.schools
      .filter(s => s.comune === selectedComune)
      .sort((a, b) => a.nome.localeCompare(b.nome))
  }, [allScuoleData, selectedComune])

  // === MUTATIONS ===

  const createBookingMutation = useMutation({
    mutationFn: (data: any) => bookingPublicApi.creaPrenotazione(data),
    onSuccess: (response) => {
      setBookingToken(response.data.token)
      setCurrentStep('successo')
      toast.success('Prenotazione confermata!')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Errore nella prenotazione'
      toast.error(message)
    },
  })

  // === HANDLERS ===

  const handleSedeSelect = (sedeId: number) => {
    setSelectedSede(sedeId)
  }

  const handleTipoSelect = (tipoId: number) => {
    setSelectedTipo(tipoId)
  }

  const handleProceedToSlots = () => {
    if (!selectedServizio) {
      toast.error('Seleziona un servizio')
      return
    }
    if (!selectedTipo) {
      toast.error('Seleziona il tipo di appuntamento')
      return
    }
    if (!selectedSede) {
      toast.error('Seleziona una sede')
      return
    }
    setCurrentStep('slot')
  }

  const handleSlotSelect = (slot: BookingSlot) => {
    setSelectedSlot(slot)
    setCurrentStep('dati')
  }

  const handleFormChange = (field: keyof PrenotazioneCreatePublic, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmitForm = () => {
    // Validazione base
    if (!formData.nome || !formData.cognome || !formData.email) {
      toast.error('Compila tutti i campi obbligatori')
      return
    }
    if (!formData.consenso_privacy) {
      toast.error('Devi accettare l\'informativa privacy')
      return
    }
    setCurrentStep('conferma')
  }

  const handleConfirmBooking = () => {
    if (!selectedSlot) return

    // Trova il nome della scuola selezionata
    const scuolaSelezionata = scuole?.find((s: any) => s.codice === selectedScuolaCodice)

    createBookingMutation.mutate({
      slot_id: selectedSlot.id,
      servizio_id: selectedServizio || undefined,
      note_utente: formData.note_utente,
      contatto: {
        nome: formData.nome!,
        cognome: formData.cognome!,
        email: formData.email!,
        telefono: formData.telefono,
        iscritto_snals: formData.iscritto_snals,
        tipologia_contratto: formData.tipologia_contratto,
        scuola_attuale: scuolaSelezionata?.nome || formData.scuola_attuale,
        consenso_privacy: formData.consenso_privacy!,
      }
    })
  }

  const handleBack = () => {
    switch (currentStep) {
      case 'slot':
        setCurrentStep('selezione')
        setSelectedSlot(null)
        break
      case 'dati':
        setCurrentStep('slot')
        break
      case 'conferma':
        setCurrentStep('dati')
        break
    }
  }

  const handleNewBooking = () => {
    setCurrentStep('selezione')
    setSelectedServizio(null)
    setSelectedSede(null)
    setSelectedTipo(null)
    setSelectedSlot(null)
    setFormData({ consenso_privacy: false })
    setBookingToken(null)
  }

  // === HELPERS ===

  const getSedeById = (id: number) => sedi?.find((s: BookingSede) => s.id === id)
  const getTipoById = (id: number) => tipiAppuntamento?.find((t: BookingTipoAppuntamento) => t.id === id)
  const getServizioById = (id: number) => servizi?.find((c: BookingServizio) => c.id === id)

  // Group slots by date
  const slotsByDate = useMemo(() => {
    if (!slots) return {}
    // Handle both array and { items: [...] } response formats
    const slotsArray = Array.isArray(slots) ? slots : (slots as any)?.items || []
    return (slotsArray as BookingSlot[]).reduce((acc, slot) => {
      const date = format(parseISO(slot.data_ora_inizio), 'yyyy-MM-dd')
      if (!acc[date]) acc[date] = []
      acc[date].push(slot)
      return acc
    }, {} as Record<string, BookingSlot[]>)
  }, [slots])

  // Generate week days
  const weekDays = useMemo(() => {
    const days = []
    let current = new Date(currentWeekStart)
    for (let i = 0; i < 7; i++) {
      days.push(new Date(current))
      current.setDate(current.getDate() + 1)
    }
    return days
  }, [currentWeekStart])

  // === RENDER ===

  const isLoading = loadingCampagne || loadingSedi || loadingTipi

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Prenota un Appuntamento
          </h1>
          <p className="text-gray-600">
            SNALS - Sindacato Nazionale Autonomo Lavoratori Scuola
          </p>
        </div>

        {/* Progress indicator */}
        {currentStep !== 'successo' && (
          <div className="flex justify-center mb-8">
            <div className="flex items-center gap-2">
              {['selezione', 'slot', 'dati', 'conferma'].map((step, idx) => (
                <div key={step} className="flex items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    currentStep === step
                      ? 'bg-primary-600 text-white'
                      : idx < ['selezione', 'slot', 'dati', 'conferma'].indexOf(currentStep)
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-200 text-gray-500'
                  }`}>
                    {idx < ['selezione', 'slot', 'dati', 'conferma'].indexOf(currentStep) ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      idx + 1
                    )}
                  </div>
                  {idx < 3 && (
                    <div className={`w-12 h-1 ${
                      idx < ['selezione', 'slot', 'dati', 'conferma'].indexOf(currentStep)
                        ? 'bg-green-500'
                        : 'bg-gray-200'
                    }`} />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Main content card */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">

          {/* STEP: Selezione */}
          {currentStep === 'selezione' && (
            <div className="p-6 sm:p-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">
                Seleziona i dettagli dell'appuntamento
              </h2>

              {isLoading ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Step 1: Servizio (OBBLIGATORIA) */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      <Briefcase className="w-4 h-4 inline mr-2" />
                      Seleziona il Servizio *
                    </label>
                    {!servizi || servizi.length === 0 ? (
                      <div className="p-4 bg-yellow-50 rounded-xl border border-yellow-200 text-yellow-800 text-sm">
                        <AlertCircle className="w-4 h-4 inline mr-2" />
                        Nessun servizio attivo al momento. Riprova più tardi.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {(servizi as BookingServizio[]).map(c => (
                          <button
                            key={c.id}
                            onClick={() => {
                              setSelectedServizio(c.id)
                              setSelectedTipo(null) // Reset tipo when changing campaign
                            }}
                            className={`p-4 border-2 rounded-xl text-left transition-all ${
                              selectedServizio === c.id
                                ? 'border-primary-500 bg-primary-50'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <div className="font-medium text-gray-900">{c.nome}</div>
                            {c.descrizione && (
                              <div className="text-sm text-gray-500 mt-1">{c.descrizione}</div>
                            )}
                            <div className="text-xs text-gray-400 mt-2">
                              {format(parseISO(c.data_inizio), 'd MMM', { locale: it })} - {format(parseISO(c.data_fine), 'd MMM yyyy', { locale: it })}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Step 2: Tipo Appuntamento (filtrato per servizio) - mostrato solo se servizio selezionata */}
                  {selectedServizio && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-3">
                        <FileText className="w-4 h-4 inline mr-2" />
                        Tipo di Appuntamento *
                      </label>
                      {!tipiAppuntamento || tipiAppuntamento.length === 0 ? (
                        <div className="p-4 bg-gray-50 rounded-xl text-gray-600 text-sm">
                          Nessun tipo appuntamento disponibile per questo servizio.
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {(tipiAppuntamento as BookingTipoAppuntamento[] || []).map(tipo => (
                            <button
                              key={tipo.id}
                              onClick={() => handleTipoSelect(tipo.id)}
                              className={`p-4 border-2 rounded-xl text-left transition-all ${
                                selectedTipo === tipo.id
                                  ? 'border-primary-500 bg-primary-50'
                                  : 'border-gray-200 hover:border-gray-300'
                              }`}
                            >
                              <div className="flex items-center gap-2">
                                {tipo.colore && (
                                  <div
                                    className="w-3 h-3 rounded-full"
                                    style={{ backgroundColor: tipo.colore }}
                                  />
                                )}
                                <div className="font-medium text-gray-900">{tipo.nome}</div>
                              </div>
                              {tipo.descrizione && (
                                <div className="text-sm text-gray-500 mt-1">{tipo.descrizione}</div>
                              )}
                              <div className="text-xs text-gray-400 mt-2">
                                <Clock className="w-3 h-3 inline mr-1" />
                                {tipo.durata_default_minuti} minuti
                              </div>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Step 3: Sede - mostrata solo se tipo selezionato */}
                  {selectedServizio && selectedTipo && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-3">
                        <MapPin className="w-4 h-4 inline mr-2" />
                        Sede *
                      </label>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {(sedi as BookingSede[] || []).map(sede => (
                          <button
                            key={sede.id}
                            onClick={() => handleSedeSelect(sede.id)}
                            className={`p-4 border-2 rounded-xl text-left transition-all ${
                              selectedSede === sede.id
                                ? 'border-primary-500 bg-primary-50'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <div className="font-medium text-gray-900">{sede.nome}</div>
                            {sede.indirizzo && (
                              <div className="text-sm text-gray-500 mt-1">
                                {sede.indirizzo}, {sede.citta}
                              </div>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Proceed button */}
                  <div className="pt-4">
                    <button
                      onClick={handleProceedToSlots}
                      disabled={!selectedServizio || !selectedSede || !selectedTipo}
                      className="w-full py-3 px-4 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                    >
                      Continua
                      <ChevronRight className="w-5 h-5 inline ml-2" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP: Slot selection */}
          {currentStep === 'slot' && (
            <div className="p-6 sm:p-8">
              <div className="flex items-center gap-4 mb-6">
                <button
                  onClick={handleBack}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <h2 className="text-xl font-semibold text-gray-900">
                  Seleziona data e ora
                </h2>
              </div>

              {/* Week navigation */}
              <div className="flex items-center justify-between mb-6">
                <button
                  onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, -1))}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <div className="text-lg font-medium text-gray-900">
                  {format(currentWeekStart, 'd MMM', { locale: it })} - {format(weekEnd, 'd MMM yyyy', { locale: it })}
                </div>
                <button
                  onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, 1))}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>

              {loadingSlots ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
                </div>
              ) : (
                <div className="grid grid-cols-7 gap-2">
                  {weekDays.map(day => {
                    const dateStr = format(day, 'yyyy-MM-dd')
                    const daySlots = slotsByDate[dateStr] || []
                    const isToday = isSameDay(day, new Date())
                    const isPast = day < new Date(new Date().setHours(0, 0, 0, 0))

                    return (
                      <div key={dateStr} className="min-h-[200px]">
                        <div className={`text-center p-2 rounded-t-lg ${
                          isToday ? 'bg-primary-100 text-primary-700' : 'bg-gray-100'
                        }`}>
                          <div className="text-xs uppercase">
                            {format(day, 'EEE', { locale: it })}
                          </div>
                          <div className="text-lg font-semibold">
                            {format(day, 'd')}
                          </div>
                        </div>
                        <div className="border border-t-0 border-gray-200 rounded-b-lg p-1 space-y-1 min-h-[150px]">
                          {isPast ? (
                            <div className="text-xs text-gray-400 text-center py-4">
                              Passato
                            </div>
                          ) : daySlots.length === 0 ? (
                            <div className="text-xs text-gray-400 text-center py-4">
                              Nessuno slot
                            </div>
                          ) : (
                            daySlots.map(slot => (
                              <button
                                key={slot.id}
                                onClick={() => handleSlotSelect(slot)}
                                className="w-full text-xs p-1.5 bg-green-50 text-green-700 rounded hover:bg-green-100 transition-colors"
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

              {/* Selected info */}
              <div className="mt-6 p-4 bg-gray-50 rounded-xl">
                <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                  <div className="flex items-center gap-1">
                    <Briefcase className="w-4 h-4" />
                    {getServizioById(selectedServizio!)?.nome}
                  </div>
                  <div className="flex items-center gap-1">
                    <FileText className="w-4 h-4" />
                    {getTipoById(selectedTipo!)?.nome}
                  </div>
                  <div className="flex items-center gap-1">
                    <MapPin className="w-4 h-4" />
                    {getSedeById(selectedSede!)?.nome}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP: Dati contatto */}
          {currentStep === 'dati' && (
            <div className="p-6 sm:p-8">
              <div className="flex items-center gap-4 mb-6">
                <button
                  onClick={handleBack}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <h2 className="text-xl font-semibold text-gray-900">
                  I tuoi dati
                </h2>
              </div>

              {/* Selected slot summary */}
              {selectedSlot && (
                <div className="mb-6 p-4 bg-primary-50 rounded-xl border border-primary-200">
                  <div className="flex items-center gap-3">
                    <CalendarIcon className="w-5 h-5 text-primary-600" />
                    <div>
                      <div className="font-medium text-primary-900">
                        {format(parseISO(selectedSlot.data_ora_inizio), 'EEEE d MMMM yyyy', { locale: it })}
                      </div>
                      <div className="text-sm text-primary-700">
                        {format(parseISO(selectedSlot.data_ora_inizio), 'HH:mm')} - {format(parseISO(selectedSlot.data_ora_fine), 'HH:mm')}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nome *
                    </label>
                    <input
                      type="text"
                      value={formData.nome || ''}
                      onChange={e => handleFormChange('nome', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      placeholder="Il tuo nome"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Cognome *
                    </label>
                    <input
                      type="text"
                      value={formData.cognome || ''}
                      onChange={e => handleFormChange('cognome', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      placeholder="Il tuo cognome"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    <Mail className="w-4 h-4 inline mr-1" />
                    Email *
                  </label>
                  <input
                    type="email"
                    value={formData.email || ''}
                    onChange={e => handleFormChange('email', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="La tua email"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    <Phone className="w-4 h-4 inline mr-1" />
                    Telefono
                  </label>
                  <input
                    type="tel"
                    value={formData.telefono || ''}
                    onChange={e => handleFormChange('telefono', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Il tuo numero di telefono"
                  />
                </div>

                {/* Iscritto SNALS */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <User className="w-4 h-4 inline mr-1" />
                    Sei iscritto/a allo SNALS?
                  </label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="iscritto_snals"
                        checked={formData.iscritto_snals === true}
                        onChange={() => handleFormChange('iscritto_snals', true)}
                        className="w-4 h-4 text-primary-600"
                      />
                      <span className="text-sm">Sì</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="iscritto_snals"
                        checked={formData.iscritto_snals === false}
                        onChange={() => handleFormChange('iscritto_snals', false)}
                        className="w-4 h-4 text-primary-600"
                      />
                      <span className="text-sm">No</span>
                    </label>
                  </div>
                </div>

                {/* Tipologia Contratto */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    <Building className="w-4 h-4 inline mr-1" />
                    Tipologia Contratto
                  </label>
                  <select
                    value={formData.tipologia_contratto || ''}
                    onChange={e => handleFormChange('tipologia_contratto', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="">Seleziona...</option>
                    <option value="tempo_indeterminato">Tempo Indeterminato</option>
                    <option value="tempo_determinato">Tempo Determinato</option>
                    <option value="supplenza">Supplenza</option>
                    <option value="altro">Altro</option>
                  </select>
                </div>

                {/* Scuola Attuale - Cascading Dropdown */}
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-gray-700">
                    <School className="w-4 h-4 inline mr-1" />
                    Scuola Attuale
                  </label>

                  {/* Selezione Comune */}
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Comune</label>
                    <select
                      value={selectedComune || ''}
                      onChange={e => {
                        setSelectedComune(e.target.value || null)
                        setSelectedScuolaCodice(null)
                      }}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="">Seleziona comune...</option>
                      {comuni?.map((comune: string) => (
                        <option key={comune} value={comune}>{comune}</option>
                      ))}
                    </select>
                  </div>

                  {/* Selezione Scuola */}
                  {selectedComune && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Scuola</label>
                      <select
                        value={selectedScuolaCodice || ''}
                        onChange={e => setSelectedScuolaCodice(e.target.value || null)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      >
                        <option value="">Seleziona scuola...</option>
                        {scuole?.map((scuola: any) => (
                          <option key={scuola.codice} value={scuola.codice}>
                            {scuola.nome}{scuola.indirizzo ? ` - ${scuola.indirizzo}` : ''}{scuola.tipo ? ` (${scuola.tipo})` : ''}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Campo manuale se scuola non in lista */}
                  {selectedComune && !selectedScuolaCodice && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Oppure scrivi il nome della scuola</label>
                      <input
                        type="text"
                        value={formData.scuola_attuale || ''}
                        onChange={e => handleFormChange('scuola_attuale', e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        placeholder="Nome della scuola se non in elenco"
                      />
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Motivo dell'appuntamento
                  </label>
                  <input
                    type="text"
                    value={formData.motivo || ''}
                    onChange={e => handleFormChange('motivo', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Breve descrizione del motivo"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Note aggiuntive
                  </label>
                  <textarea
                    value={formData.note_utente || ''}
                    onChange={e => handleFormChange('note_utente', e.target.value)}
                    rows={3}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Eventuali informazioni aggiuntive..."
                  />
                </div>

                {/* Privacy checkbox */}
                <div className="p-4 bg-gray-50 rounded-xl">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.consenso_privacy || false}
                      onChange={e => handleFormChange('consenso_privacy', e.target.checked)}
                      className="mt-1 w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-600">
                      Ho letto e accetto l'<a href="#" className="text-primary-600 underline">informativa sulla privacy</a>
                      {' '}ai sensi del Regolamento UE 2016/679 (GDPR). *
                    </span>
                  </label>
                </div>

                <button
                  onClick={handleSubmitForm}
                  disabled={!formData.nome || !formData.cognome || !formData.email || !formData.consenso_privacy}
                  className="w-full py-3 px-4 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  Conferma Dati
                  <ChevronRight className="w-5 h-5 inline ml-2" />
                </button>
              </div>
            </div>
          )}

          {/* STEP: Conferma */}
          {currentStep === 'conferma' && (
            <div className="p-6 sm:p-8">
              <div className="flex items-center gap-4 mb-6">
                <button
                  onClick={handleBack}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <h2 className="text-xl font-semibold text-gray-900">
                  Conferma Prenotazione
                </h2>
              </div>

              <div className="space-y-6">
                {/* Riepilogo appuntamento */}
                <div className="p-4 bg-primary-50 rounded-xl border border-primary-200">
                  <h3 className="font-medium text-primary-900 mb-3">Dettagli Appuntamento</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Briefcase className="w-4 h-4 text-primary-600" />
                      <span>{getServizioById(selectedServizio!)?.nome}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <CalendarIcon className="w-4 h-4 text-primary-600" />
                      <span>
                        {selectedSlot && format(parseISO(selectedSlot.data_ora_inizio), 'EEEE d MMMM yyyy', { locale: it })}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-primary-600" />
                      <span>
                        {selectedSlot && `${format(parseISO(selectedSlot.data_ora_inizio), 'HH:mm')} - ${format(parseISO(selectedSlot.data_ora_fine), 'HH:mm')}`}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-primary-600" />
                      <span>{getTipoById(selectedTipo!)?.nome}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-primary-600" />
                      <span>{getSedeById(selectedSede!)?.nome}</span>
                    </div>
                  </div>
                </div>

                {/* Riepilogo dati */}
                <div className="p-4 bg-gray-50 rounded-xl">
                  <h3 className="font-medium text-gray-900 mb-3">I tuoi dati</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-gray-500">Nome:</div>
                    <div className="font-medium">{formData.nome} {formData.cognome}</div>
                    <div className="text-gray-500">Email:</div>
                    <div className="font-medium">{formData.email}</div>
                    {formData.telefono && (
                      <>
                        <div className="text-gray-500">Telefono:</div>
                        <div className="font-medium">{formData.telefono}</div>
                      </>
                    )}
                    {formData.iscritto_snals !== undefined && (
                      <>
                        <div className="text-gray-500">Iscritto SNALS:</div>
                        <div className="font-medium">{formData.iscritto_snals ? 'Sì' : 'No'}</div>
                      </>
                    )}
                    {(selectedScuolaCodice || formData.scuola_attuale) && (
                      <>
                        <div className="text-gray-500">Scuola:</div>
                        <div className="font-medium">
                          {scuole?.find((s: any) => s.codice === selectedScuolaCodice)?.nome || formData.scuola_attuale}
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Warning */}
                <div className="flex items-start gap-3 p-4 bg-yellow-50 rounded-xl border border-yellow-200">
                  <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-yellow-800">
                    <p className="font-medium">Importante</p>
                    <p>Riceverai una email di conferma all'indirizzo indicato con il link per gestire la tua prenotazione.</p>
                  </div>
                </div>

                <button
                  onClick={handleConfirmBooking}
                  disabled={createBookingMutation.isPending}
                  className="w-full py-3 px-4 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  {createBookingMutation.isPending ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      Prenotazione in corso...
                    </span>
                  ) : (
                    <>
                      <Check className="w-5 h-5 inline mr-2" />
                      Conferma Prenotazione
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* STEP: Successo */}
          {currentStep === 'successo' && (
            <div className="p-6 sm:p-8 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <Check className="w-8 h-8 text-green-600" />
              </div>

              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Prenotazione Confermata!
              </h2>

              <p className="text-gray-600 mb-6">
                Abbiamo inviato una email di conferma a <strong>{formData.email}</strong> con tutti i dettagli e il link per gestire la prenotazione.
              </p>

              {/* Riepilogo */}
              {selectedSlot && (
                <div className="p-4 bg-gray-50 rounded-xl mb-6 text-left">
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <CalendarIcon className="w-4 h-4 text-gray-400" />
                      <span>{format(parseISO(selectedSlot.data_ora_inizio), 'EEEE d MMMM yyyy', { locale: it })}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <span>{format(parseISO(selectedSlot.data_ora_inizio), 'HH:mm')} - {format(parseISO(selectedSlot.data_ora_fine), 'HH:mm')}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-gray-400" />
                      <span>{getSedeById(selectedSede!)?.nome}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Token info */}
              {bookingToken && (
                <div className="p-4 bg-blue-50 rounded-xl mb-6">
                  <p className="text-sm text-blue-800">
                    Il tuo codice prenotazione: <strong className="font-mono">{bookingToken.slice(0, 8)}...</strong>
                  </p>
                  <p className="text-xs text-blue-600 mt-1">
                    Conserva l'email ricevuta per gestire la prenotazione
                  </p>
                </div>
              )}

              <button
                onClick={handleNewBooking}
                className="px-6 py-3 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 transition-colors"
              >
                Prenota un altro appuntamento
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>SNALS - Sindacato Nazionale Autonomo Lavoratori Scuola</p>
          <p className="mt-1">
            Per assistenza: <a href="mailto:prenotazioni@snals.it" className="text-primary-600">prenotazioni@snals.it</a>
          </p>
        </div>
      </div>
    </div>
  )
}
