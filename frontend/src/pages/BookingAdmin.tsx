/**
 * Pagina Admin per gestione modulo prenotazioni
 *
 * Include tabs per:
 * - Dashboard statistiche
 * - Prenotazioni
 * - Sedi
 * - Staff
 * - Tipi Appuntamento
 * - Servizi
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BarChart3,
  Calendar,
  MapPin,
  Users,
  Briefcase,
  Plus,
  Edit,
  Trash2,
  Eye,
  Download,
  RefreshCw,
  Check,
  Clock,
  FileText,
  ChevronDown,
  Tag
} from 'lucide-react'
import toast from 'react-hot-toast'
import { format, parseISO } from 'date-fns'
import { it } from 'date-fns/locale'
import { bookingAdminApi, bookingStaffApi } from '../lib/api'
import type {
  BookingSede,
  BookingStaff,
  BookingTipoAppuntamento,
  BookingServizio,
  BookingPrenotazione,
  BookingStats
} from '../types'

// Helper per estrarre messaggi di errore dall'API
const getErrorMessage = (error: any, defaultMsg: string): string => {
  const detail = error?.response?.data?.detail
  if (!detail) return defaultMsg
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    // Pydantic validation error format
    return detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ')
  }
  return defaultMsg
}

// Tabs
type Tab = 'dashboard' | 'prenotazioni' | 'sedi' | 'staff' | 'tipi' | 'servizi'

// Helper per tradurre stati
const statoLabels: Record<string, string> = {
  confermata: 'Confermata',
  annullata_utente: 'Annullata (utente)',
  annullata_ufficio: 'Annullata (ufficio)',
  completata: 'Completata',
  no_show: 'No Show',
}

const statoColors: Record<string, string> = {
  confermata: 'bg-green-100 text-green-800',
  annullata_utente: 'bg-red-100 text-red-800',
  annullata_ufficio: 'bg-red-100 text-red-800',
  completata: 'bg-blue-100 text-blue-800',
  no_show: 'bg-yellow-100 text-yellow-800',
}

export default function BookingAdmin() {
  useQueryClient()
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')

  // === TAB COMPONENTS ===

  const tabs = [
    { id: 'dashboard' as Tab, name: 'Dashboard', icon: BarChart3 },
    { id: 'prenotazioni' as Tab, name: 'Prenotazioni', icon: Calendar },
    { id: 'sedi' as Tab, name: 'Sedi', icon: MapPin },
    { id: 'staff' as Tab, name: 'Staff', icon: Users },
    { id: 'tipi' as Tab, name: 'Tipi Appuntamento', icon: Briefcase },
    { id: 'servizi' as Tab, name: 'Servizi', icon: Tag },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
          Gestione Prenotazioni
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Amministrazione del sistema di prenotazione appuntamenti
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 overflow-x-auto">
        <nav className="-mb-px flex space-x-4 sm:space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="min-h-[500px]">
        {activeTab === 'dashboard' && <DashboardTab />}
        {activeTab === 'prenotazioni' && <PrenotazioniTab />}
        {activeTab === 'sedi' && <SediTab />}
        {activeTab === 'staff' && <StaffTab />}
        {activeTab === 'tipi' && <TipiAppuntamentoTab />}
        {activeTab === 'servizi' && <CampagneTab />}
      </div>
    </div>
  )
}

// === DASHBOARD TAB ===
function DashboardTab() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['booking-stats'],
    queryFn: () => bookingAdminApi.getStatistiche().then(r => r.data),
  })

  if (isLoading) {
    return <LoadingSpinner />
  }

  const statsData = stats as BookingStats | undefined

  return (
    <div className="space-y-6">
      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Prenotazioni Totali"
          value={statsData?.totale_prenotazioni || 0}
          icon={Calendar}
          color="blue"
        />
        <StatCard
          title="Oggi"
          value={statsData?.prenotazioni_oggi || 0}
          icon={Clock}
          color="green"
        />
        <StatCard
          title="Questa Settimana"
          value={statsData?.prenotazioni_settimana || 0}
          icon={BarChart3}
          color="purple"
        />
        <StatCard
          title="Completate"
          value={statsData?.per_stato?.completata || 0}
          icon={Check}
          color="emerald"
        />
      </div>

      {/* Per stato */}
      {statsData?.per_stato && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Per Stato</h3>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            {Object.entries(statsData.per_stato).map(([stato, count]) => (
              <div key={stato} className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-gray-900">{count}</div>
                <div className="text-sm text-gray-500">{statoLabels[stato] || stato}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Per tipo appuntamento */}
      {statsData?.per_tipo_appuntamento && Object.keys(statsData.per_tipo_appuntamento).length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Per Tipo Appuntamento</h3>
          <div className="space-y-2">
            {Object.entries(statsData.per_tipo_appuntamento).map(([tipo, count]) => (
              <div key={tipo} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="font-medium text-gray-700">{tipo}</span>
                <span className="text-lg font-bold text-primary-600">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// === PRENOTAZIONI TAB ===
function PrenotazioniTab() {
  const [filters, setFilters] = useState({
    data_da: '',
    data_a: '',
    stato: '',
    page: 1,
  })

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['booking-prenotazioni', filters],
    queryFn: () => bookingAdminApi.getPrenotazioni({
      ...filters,
      data_da: filters.data_da || undefined,
      data_a: filters.data_a || undefined,
      stato: filters.stato || undefined,
    }).then(r => r.data),
  })

  const prenotazioni = (data?.items || data || []) as BookingPrenotazione[]

  const handleExport = async () => {
    try {
      const response = await bookingAdminApi.exportPrenotazioni({
        data_da: filters.data_da || undefined,
        data_a: filters.data_a || undefined,
        stato: filters.stato || undefined,
      })
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `prenotazioni_${format(new Date(), 'yyyyMMdd')}.csv`
      a.click()
      toast.success('Export completato')
    } catch {
      toast.error('Errore durante l\'export')
    }
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Da</label>
            <input
              type="date"
              value={filters.data_da}
              onChange={e => setFilters({ ...filters, data_da: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">A</label>
            <input
              type="date"
              value={filters.data_a}
              onChange={e => setFilters({ ...filters, data_a: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Stato</label>
            <select
              value={filters.stato}
              onChange={e => setFilters({ ...filters, stato: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">Tutti</option>
              {Object.entries(statoLabels).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end gap-2 ml-auto">
            <button onClick={() => refetch()} className="btn-secondary p-2">
              <RefreshCw className="w-4 h-4" />
            </button>
            <button onClick={handleExport} className="btn-secondary flex items-center gap-2">
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <LoadingSpinner />
        ) : prenotazioni.length === 0 ? (
          <EmptyState message="Nessuna prenotazione trovata" />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data/Ora</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contatto</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sede</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stato</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Azioni</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {prenotazioni.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      {p.slot && (
                        <>
                          <div className="font-medium text-gray-900">
                            {format(parseISO(p.slot.data_ora_inizio), 'd MMM yyyy', { locale: it })}
                          </div>
                          <div className="text-gray-500">
                            {format(parseISO(p.slot.data_ora_inizio), 'HH:mm')}
                          </div>
                        </>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {p.contatto && (
                        <>
                          <div className="font-medium text-gray-900">
                            {p.contatto.nome} {p.contatto.cognome}
                          </div>
                          <div className="text-gray-500 text-xs">{p.contatto.email}</div>
                        </>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {p.slot?.tipo_appuntamento?.nome || '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {p.slot?.sede?.nome || '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${statoColors[p.stato] || 'bg-gray-100'}`}>
                        {statoLabels[p.stato] || p.stato}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <button className="text-gray-400 hover:text-gray-600 p-1">
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// === SEDI TAB ===
function SediTab() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editItem, setEditItem] = useState<BookingSede | null>(null)

  const { data: sedi, isLoading } = useQuery({
    queryKey: ['booking-admin-sedi'],
    queryFn: () => bookingAdminApi.getSedi().then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: bookingAdminApi.creaSede,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-sedi'] })
      toast.success('Sede creata')
      setShowModal(false)
    },
    onError: () => toast.error('Errore nella creazione'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => bookingAdminApi.aggiornaSede(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-sedi'] })
      toast.success('Sede aggiornata')
      setShowModal(false)
      setEditItem(null)
    },
    onError: () => toast.error('Errore nell\'aggiornamento'),
  })

  const deleteMutation = useMutation({
    mutationFn: bookingAdminApi.eliminaSede,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-sedi'] })
      toast.success('Sede eliminata')
    },
    onError: () => toast.error('Errore nell\'eliminazione'),
  })

  const handleSave = (data: any) => {
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => { setEditItem(null); setShowModal(true) }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nuova Sede
        </button>
      </div>

      <div className="card">
        {isLoading ? (
          <LoadingSpinner />
        ) : (sedi as BookingSede[] || []).length === 0 ? (
          <EmptyState message="Nessuna sede configurata" />
        ) : (
          <div className="divide-y divide-gray-200">
            {(sedi as BookingSede[]).map(sede => (
              <div key={sede.id} className="flex items-center justify-between p-4 hover:bg-gray-50">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${sede.attivo ? 'bg-green-500' : 'bg-gray-300'}`} />
                  <div>
                    <div className="font-medium text-gray-900">{sede.nome}</div>
                    {sede.indirizzo && (
                      <div className="text-sm text-gray-500">{sede.indirizzo}, {sede.citta}</div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => { setEditItem(sede); setShowModal(true) }}
                    className="p-2 text-gray-400 hover:text-gray-600"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Eliminare questa sede?')) {
                        deleteMutation.mutate(sede.id)
                      }
                    }}
                    className="p-2 text-red-400 hover:text-red-600"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <SedeModal
          sede={editItem}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditItem(null) }}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      )}
    </div>
  )
}

// === STAFF TAB ===
function StaffTab() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editItem, setEditItem] = useState<BookingStaff | null>(null)
  const [expandedStaffId, setExpandedStaffId] = useState<number | null>(null)
  const [showDisponibilitaModal, setShowDisponibilitaModal] = useState(false)
  const [selectedStaffForDisp, setSelectedStaffForDisp] = useState<BookingStaff | null>(null)
  const [selectedDispIds, setSelectedDispIds] = useState<Set<number>>(new Set())
  const [isDeletingMultiple, setIsDeletingMultiple] = useState(false)

  const { data: staff, isLoading } = useQuery({
    queryKey: ['booking-admin-staff'],
    queryFn: () => bookingAdminApi.getStaff().then(r => r.data),
  })

  // Fetch sedi per il selector nel form staff
  const { data: sedi } = useQuery({
    queryKey: ['booking-admin-sedi'],
    queryFn: () => bookingAdminApi.getSedi().then(r => r.data),
  })

  // Fetch tipi appuntamento per il modal disponibilità
  const { data: tipiAppuntamento } = useQuery({
    queryKey: ['booking-admin-tipi'],
    queryFn: () => bookingAdminApi.getTipiAppuntamento().then(r => r.data),
  })

  // Fetch servizi per il modal disponibilità
  const { data: servizi } = useQuery({
    queryKey: ['booking-admin-servizi'],
    queryFn: () => bookingAdminApi.getServizi().then(r => r.data),
  })

  // Fetch disponibilità per lo staff espanso
  const { data: disponibilita, refetch: refetchDisponibilita } = useQuery({
    queryKey: ['staff-disponibilita', expandedStaffId],
    queryFn: () => expandedStaffId
      ? bookingStaffApi.getDisponibilita(expandedStaffId, {}).then(r => r.data)
      : Promise.resolve([]),
    enabled: !!expandedStaffId,
  })

  const createMutation = useMutation({
    mutationFn: bookingAdminApi.creaStaff,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-staff'] })
      toast.success('Staff creato')
      setShowModal(false)
    },
    onError: () => toast.error('Errore nella creazione'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => bookingAdminApi.aggiornaStaff(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-staff'] })
      toast.success('Staff aggiornato')
      setShowModal(false)
      setEditItem(null)
    },
    onError: () => toast.error('Errore nell\'aggiornamento'),
  })

  const deleteMutation = useMutation({
    mutationFn: bookingAdminApi.eliminaStaff,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-staff'] })
      toast.success('Staff eliminato')
    },
    onError: () => toast.error('Errore nell\'eliminazione'),
  })

  const creaDisponibilitaMutation = useMutation({
    mutationFn: bookingStaffApi.creaDisponibilita,
    onSuccess: () => {
      refetchDisponibilita()
    },
    onError: (error: any) => {
      const msg = error.response?.data?.detail || 'Errore nella creazione'
      console.error('Errore creazione disponibilità:', msg)
    },
  })

  const eliminaDisponibilitaMutation = useMutation({
    mutationFn: bookingStaffApi.eliminaDisponibilita,
    onSuccess: () => {
      refetchDisponibilita()
      toast.success('Disponibilità eliminata')
    },
    onError: () => toast.error('Errore nell\'eliminazione'),
  })

  // State e mutation per modifica disponibilità
  const [editingDisponibilita, setEditingDisponibilita] = useState<any>(null)

  const aggiornaDisponibilitaMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => bookingStaffApi.aggiornaDisponibilita(id, data),
    onSuccess: () => {
      refetchDisponibilita()
      toast.success('Disponibilità aggiornata')
      setShowDisponibilitaModal(false)
      setEditingDisponibilita(null)
      setSelectedStaffForDisp(null)
    },
    onError: (error: any) => {
      const msg = error.response?.data?.detail || 'Errore nell\'aggiornamento'
      toast.error(msg)
    },
  })

  // Funzioni per selezione multipla disponibilità
  const toggleDispSelection = (dispId: number) => {
    setSelectedDispIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(dispId)) {
        newSet.delete(dispId)
      } else {
        newSet.add(dispId)
      }
      return newSet
    })
  }

  const toggleSelectAllDisp = () => {
    const dispList = (disponibilita as any[] || [])
    if (selectedDispIds.size === dispList.length) {
      setSelectedDispIds(new Set())
    } else {
      setSelectedDispIds(new Set(dispList.map((d: any) => d.id)))
    }
  }

  const handleDeleteSelectedDisp = async () => {
    if (selectedDispIds.size === 0) return

    if (!confirm(`Eliminare ${selectedDispIds.size} disponibilità selezionate?`)) return

    setIsDeletingMultiple(true)
    let successCount = 0
    let errorCount = 0

    for (const dispId of selectedDispIds) {
      try {
        await bookingStaffApi.eliminaDisponibilita(dispId)
        successCount++
      } catch {
        errorCount++
      }
    }

    setIsDeletingMultiple(false)
    setSelectedDispIds(new Set())
    refetchDisponibilita()

    if (errorCount === 0) {
      toast.success(`${successCount} disponibilità eliminate`)
    } else {
      toast.error(`${successCount} eliminate, ${errorCount} errori`)
    }
  }

  // Reset selezione quando cambia lo staff espanso
  const handleToggleStaffExpanded = (staffId: number) => {
    setSelectedDispIds(new Set())
    setExpandedStaffId(expandedStaffId === staffId ? null : staffId)
  }
  // Ensure function is used
  void handleToggleStaffExpanded

  const handleSave = (data: any) => {
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleAddDisponibilita = (staffMember: BookingStaff) => {
    setSelectedStaffForDisp(staffMember)
    setShowDisponibilitaModal(true)
  }

  const handleSaveDisponibilita = async (data: {
    sede_id: number
    servizio_id?: number
    data: string
    ora_inizio: string
    ora_fine: string
    note?: string
    tipi_appuntamento_ids?: number[]
  }): Promise<boolean> => {
    try {
      if (editingDisponibilita) {
        // Update existing
        await aggiornaDisponibilitaMutation.mutateAsync({
          id: editingDisponibilita.id,
          data: data,
        })
      } else {
        // Create new
        if (!selectedStaffForDisp) return false
        await creaDisponibilitaMutation.mutateAsync({
          staff_id: selectedStaffForDisp.id,
          ...data,
        })
      }
      return true
    } catch (error) {
      return false
    }
  }

  const handleCloseDisponibilitaModal = () => {
    setShowDisponibilitaModal(false)
    setSelectedStaffForDisp(null)
    setEditingDisponibilita(null)
    refetchDisponibilita()
  }

  const handleEditDisponibilita = (disp: any, staffMember: BookingStaff) => {
    setEditingDisponibilita(disp)
    setSelectedStaffForDisp(staffMember)
    setShowDisponibilitaModal(true)
  }

  const toggleExpand = (staffId: number) => {
    setSelectedDispIds(new Set()) // Reset selezione quando cambia staff
    setExpandedStaffId(expandedStaffId === staffId ? null : staffId)
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => { setEditItem(null); setShowModal(true) }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nuovo Staff
        </button>
      </div>

      <div className="card">
        {isLoading ? (
          <LoadingSpinner />
        ) : (staff as BookingStaff[] || []).length === 0 ? (
          <EmptyState message="Nessuno staff configurato" />
        ) : (
          <div className="divide-y divide-gray-200">
            {(staff as BookingStaff[]).map(s => (
              <div key={s.id}>
                {/* Staff row */}
                <div
                  className="flex items-center justify-between p-4 hover:bg-gray-50 cursor-pointer"
                  onClick={() => toggleExpand(s.id)}
                >
                  <div className="flex items-center gap-3">
                    <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${expandedStaffId === s.id ? 'rotate-180' : ''}`} />
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-medium ${s.attivo ? 'bg-primary-500' : 'bg-gray-400'}`}>
                      {s.nome[0]}{s.cognome[0]}
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">{s.nome} {s.cognome}</div>
                      <div className="text-sm text-gray-500">{s.email}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                    {s.ruolo && (
                      <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">
                        {s.ruolo}
                      </span>
                    )}
                    <button
                      onClick={() => handleAddDisponibilita(s)}
                      className="p-2 text-blue-400 hover:text-blue-600"
                      title="Aggiungi disponibilità"
                    >
                      <Calendar className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => { setEditItem(s); setShowModal(true) }}
                      className="p-2 text-gray-400 hover:text-gray-600"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Eliminare questo staff?')) {
                          deleteMutation.mutate(s.id)
                        }
                      }}
                      className="p-2 text-red-400 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Expanded disponibilità section */}
                {expandedStaffId === s.id && (
                  <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <h4 className="text-sm font-medium text-gray-700">Disponibilità di {s.nome}</h4>
                        {(disponibilita as any[] || []).length > 0 && (
                          <span className="text-xs text-gray-500">
                            ({(disponibilita as any[]).length} totali)
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {selectedDispIds.size > 0 && (
                          <button
                            onClick={handleDeleteSelectedDisp}
                            disabled={isDeletingMultiple}
                            className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1 px-2 py-1 bg-red-50 rounded"
                          >
                            <Trash2 className="w-3 h-3" />
                            {isDeletingMultiple ? 'Eliminazione...' : `Elimina (${selectedDispIds.size})`}
                          </button>
                        )}
                        <button
                          onClick={() => handleAddDisponibilita(s)}
                          className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                        >
                          <Plus className="w-3 h-3" />
                          Aggiungi
                        </button>
                      </div>
                    </div>

                    {(disponibilita as any[] || []).length === 0 ? (
                      <p className="text-sm text-gray-500 italic">Nessuna disponibilità configurata</p>
                    ) : (
                      <div className="space-y-2">
                        {/* Select all header */}
                        <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg">
                          <input
                            type="checkbox"
                            checked={selectedDispIds.size === (disponibilita as any[]).length && (disponibilita as any[]).length > 0}
                            onChange={toggleSelectAllDisp}
                            className="w-4 h-4 text-primary-600 border-gray-300 rounded cursor-pointer"
                          />
                          <span className="text-xs text-gray-600">
                            {selectedDispIds.size === 0
                              ? 'Seleziona tutti'
                              : `${selectedDispIds.size} selezionati`}
                          </span>
                        </div>

                        {(disponibilita as any[]).map((d: any) => (
                          <div
                            key={d.id}
                            className={`flex items-center gap-3 bg-white p-3 rounded-lg border ${
                              selectedDispIds.has(d.id) ? 'border-primary-400 bg-primary-50' : 'border-gray-200'
                            }`}
                          >
                            {/* Checkbox */}
                            <input
                              type="checkbox"
                              checked={selectedDispIds.has(d.id)}
                              onChange={() => toggleDispSelection(d.id)}
                              className="w-4 h-4 text-primary-600 border-gray-300 rounded cursor-pointer flex-shrink-0"
                            />

                            {/* Content */}
                            <div className="flex-1 flex flex-col gap-1">
                              <div className="flex items-center gap-4 flex-wrap">
                                <div className="text-sm">
                                  <span className="font-medium text-gray-900">
                                    {format(parseISO(d.data), 'EEE d MMM yyyy', { locale: it })}
                                  </span>
                                  <span className="text-gray-500 ml-2">
                                    {d.ora_inizio?.slice(0, 5)} - {d.ora_fine?.slice(0, 5)}
                                  </span>
                                  {d.durata_slot_minuti && (
                                    <span className="text-xs text-orange-600 ml-2">
                                      ({d.durata_slot_minuti} min/slot)
                                    </span>
                                  )}
                                </div>
                                {d.servizio && (
                                  <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                                    {d.servizio.nome}
                                  </span>
                                )}
                                {d.sede && (
                                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                                    {d.sede.nome}
                                  </span>
                                )}
                              </div>
                              {/* Tipi appuntamento */}
                              {d.tipi_appuntamento && d.tipi_appuntamento.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {d.tipi_appuntamento.map((t: any) => (
                                    <span
                                      key={t.id}
                                      className="text-xs px-2 py-0.5 rounded-full text-white"
                                      style={{ backgroundColor: t.colore || '#6b7280' }}
                                    >
                                      {t.nome}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>

                            {/* Actions */}
                            <div className="flex items-center gap-1 flex-shrink-0">
                              <button
                                onClick={() => handleEditDisponibilita(d, s)}
                                className="p-1 text-blue-400 hover:text-blue-600"
                                title="Modifica"
                              >
                                <Edit className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => {
                                  if (confirm('Eliminare questa disponibilità?')) {
                                    eliminaDisponibilitaMutation.mutate(d.id)
                                  }
                                }}
                                className="p-1 text-red-400 hover:text-red-600"
                                title="Elimina"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal Staff */}
      {showModal && (
        <StaffModal
          staff={editItem}
          sedi={(sedi as BookingSede[]) || []}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditItem(null) }}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      )}

      {/* Modal Disponibilità */}
      {showDisponibilitaModal && selectedStaffForDisp && (
        <DisponibilitaAdminModal
          staffName={`${selectedStaffForDisp.nome} ${selectedStaffForDisp.cognome}`}
          sedi={(sedi as BookingSede[]) || []}
          tipiAppuntamento={(tipiAppuntamento as BookingTipoAppuntamento[]) || []}
          servizi={(servizi as BookingServizio[]) || []}
          esistente={editingDisponibilita}
          onSaveAsync={handleSaveDisponibilita}
          onClose={handleCloseDisponibilitaModal}
          isLoading={creaDisponibilitaMutation.isPending || aggiornaDisponibilitaMutation.isPending}
        />
      )}
    </div>
  )
}

// === TIPI APPUNTAMENTO TAB ===
function TipiAppuntamentoTab() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editItem, setEditItem] = useState<BookingTipoAppuntamento | null>(null)

  const { data: tipi, isLoading } = useQuery({
    queryKey: ['booking-admin-tipi'],
    queryFn: () => bookingAdminApi.getTipiAppuntamento().then(r => r.data),
  })

  // Fetch servizi per associazione
  const { data: servizi } = useQuery({
    queryKey: ['booking-admin-servizi'],
    queryFn: () => bookingAdminApi.getServizi().then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: bookingAdminApi.creaTipoAppuntamento,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-tipi'] })
      queryClient.invalidateQueries({ queryKey: ['booking-admin-servizi'] })
      toast.success('Tipo appuntamento creato')
      setShowModal(false)
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Errore nella creazione'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => bookingAdminApi.aggiornaTipoAppuntamento(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-tipi'] })
      queryClient.invalidateQueries({ queryKey: ['booking-admin-servizi'] })
      toast.success('Tipo appuntamento aggiornato')
      setShowModal(false)
      setEditItem(null)
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Errore nell\'aggiornamento'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: bookingAdminApi.eliminaTipoAppuntamento,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-tipi'] })
      queryClient.invalidateQueries({ queryKey: ['booking-admin-servizi'] })
      toast.success('Tipo appuntamento eliminato')
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Errore nell\'eliminazione'))
    },
  })

  // Funzione per aggiornare le servizi associate al tipo
  const updateCampagneAssociation = async (tipoId: number, selectedCampagneIds: number[]) => {
    const allCampagne = (servizi as BookingServizio[]) || []

    for (const camp of allCampagne) {
      const currentTipiIds = (camp as any).tipi_appuntamento?.map((t: BookingTipoAppuntamento) => t.id) || []
      const isCurrentlyAssociated = currentTipiIds.includes(tipoId)
      const shouldBeAssociated = selectedCampagneIds.includes(camp.id)

      if (isCurrentlyAssociated !== shouldBeAssociated) {
        let newTipiIds: number[]
        if (shouldBeAssociated) {
          // Aggiungi il tipo al servizio
          newTipiIds = [...currentTipiIds, tipoId]
        } else {
          // Rimuovi il tipo dal servizio
          newTipiIds = currentTipiIds.filter((id: number) => id !== tipoId)
        }
        await bookingAdminApi.aggiornaServizio(camp.id, { tipi_appuntamento_ids: newTipiIds })
      }
    }
  }

  const handleSave = async (data: any) => {
    const { servizi_ids, ...tipoData } = data

    if (editItem) {
      // Update tipo
      await updateMutation.mutateAsync({ id: editItem.id, data: tipoData })
      // Update servizi associations
      if (servizi_ids) {
        await updateCampagneAssociation(editItem.id, servizi_ids)
        queryClient.invalidateQueries({ queryKey: ['booking-admin-servizi'] })
      }
    } else {
      // Create tipo and get the new ID
      const result = await createMutation.mutateAsync(tipoData)
      // Update servizi associations with the new tipo
      if (servizi_ids && servizi_ids.length > 0 && (result as any)?.data?.id) {
        await updateCampagneAssociation((result as any).data.id, servizi_ids)
        queryClient.invalidateQueries({ queryKey: ['booking-admin-servizi'] })
      }
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => { setEditItem(null); setShowModal(true) }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nuovo Tipo
        </button>
      </div>

      <div className="card">
        {isLoading ? (
          <LoadingSpinner />
        ) : (tipi as BookingTipoAppuntamento[] || []).length === 0 ? (
          <EmptyState message="Nessun tipo appuntamento configurato" />
        ) : (
          <div className="divide-y divide-gray-200">
            {(tipi as BookingTipoAppuntamento[]).map(tipo => (
              <div key={tipo.id} className="flex items-center justify-between p-4 hover:bg-gray-50">
                <div className="flex items-center gap-3">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: tipo.colore || '#6b7280' }}
                  />
                  <div>
                    <div className="font-medium text-gray-900">{tipo.nome}</div>
                    {tipo.descrizione && (
                      <div className="text-sm text-gray-500">{tipo.descrizione}</div>
                    )}
                    <div className="text-xs text-gray-400 mt-1">
                      <Clock className="w-3 h-3 inline mr-1" />
                      {tipo.durata_default_minuti} minuti
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${tipo.attivo ? 'bg-green-500' : 'bg-gray-300'}`} />
                  <button
                    onClick={() => { setEditItem(tipo); setShowModal(true) }}
                    className="p-2 text-gray-400 hover:text-gray-600"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Eliminare questo tipo?')) {
                        deleteMutation.mutate(tipo.id)
                      }
                    }}
                    className="p-2 text-red-400 hover:text-red-600"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <TipoAppuntamentoModal
          tipo={editItem}
          servizi={(servizi as BookingServizio[]) || []}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditItem(null) }}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      )}
    </div>
  )
}

// === CAMPAGNE TAB ===
function CampagneTab() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editItem, setEditItem] = useState<BookingServizio | null>(null)

  const { data: servizi, isLoading } = useQuery({
    queryKey: ['booking-admin-servizi'],
    queryFn: () => bookingAdminApi.getServizi().then(r => r.data),
  })

  // Fetch tipi appuntamento per il form
  const { data: tipiAppuntamento } = useQuery({
    queryKey: ['booking-admin-tipi'],
    queryFn: () => bookingAdminApi.getTipiAppuntamento().then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: bookingAdminApi.creaServizio,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-servizi'] })
      toast.success('Servizio creata')
      setShowModal(false)
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Errore nella creazione'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => bookingAdminApi.aggiornaServizio(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-servizi'] })
      toast.success('Servizio aggiornata')
      setShowModal(false)
      setEditItem(null)
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Errore nell\'aggiornamento'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: bookingAdminApi.eliminaServizio,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-servizi'] })
      toast.success('Servizio eliminata')
    },
    onError: () => toast.error('Errore nell\'eliminazione'),
  })

  const handleSave = (data: any) => {
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => { setEditItem(null); setShowModal(true) }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nuovo Servizio
        </button>
      </div>

      <div className="card">
        {isLoading ? (
          <LoadingSpinner />
        ) : (servizi as BookingServizio[] || []).length === 0 ? (
          <EmptyState message="Nessun servizio configurato" />
        ) : (
          <div className="divide-y divide-gray-200">
            {(servizi as BookingServizio[]).map(c => (
              <div key={c.id} className="flex items-center justify-between p-4 hover:bg-gray-50">
                <div>
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${c.attivo ? 'bg-green-500' : 'bg-gray-300'}`} />
                    <div className="font-medium text-gray-900">{c.nome}</div>
                  </div>
                  {c.descrizione && (
                    <div className="text-sm text-gray-500 mt-1">{c.descrizione}</div>
                  )}
                  <div className="text-xs text-gray-400 mt-2">
                    <Calendar className="w-3 h-3 inline mr-1" />
                    {format(parseISO(c.data_inizio), 'd MMM yyyy', { locale: it })} - {format(parseISO(c.data_fine), 'd MMM yyyy', { locale: it })}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => { setEditItem(c); setShowModal(true) }}
                    className="p-2 text-gray-400 hover:text-gray-600"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Eliminare questo servizio?')) {
                        deleteMutation.mutate(c.id)
                      }
                    }}
                    className="p-2 text-red-400 hover:text-red-600"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <ServizioModal
          servizio={editItem}
          tipiAppuntamento={(tipiAppuntamento as BookingTipoAppuntamento[]) || []}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditItem(null) }}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      )}
    </div>
  )
}

// === HELPER COMPONENTS ===

function LoadingSpinner() {
  return (
    <div className="flex justify-center py-12">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12">
      <div className="text-gray-400 mb-2">
        <FileText className="w-12 h-12 mx-auto" />
      </div>
      <p className="text-gray-500">{message}</p>
    </div>
  )
}

function StatCard({ title, value, icon: Icon, color }: {
  title: string
  value: number
  icon: any
  color: string
}) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    emerald: 'bg-emerald-100 text-emerald-600',
  }

  return (
    <div className="card">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <div className="text-2xl font-bold text-gray-900">{value}</div>
          <div className="text-sm text-gray-500">{title}</div>
        </div>
      </div>
    </div>
  )
}

// === MODALS ===

function SedeModal({ sede, onSave, onClose, isLoading }: {
  sede: BookingSede | null
  onSave: (data: any) => void
  onClose: () => void
  isLoading: boolean
}) {
  const [formData, setFormData] = useState({
    nome: sede?.nome || '',
    indirizzo: sede?.indirizzo || '',
    citta: sede?.citta || '',
    cap: sede?.cap || '',
    telefono: sede?.telefono || '',
    email: sede?.email || '',
    attivo: sede?.attivo ?? true,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">
            {sede ? 'Modifica Sede' : 'Nuova Sede'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
              <input
                type="text"
                value={formData.nome}
                onChange={e => setFormData({ ...formData, nome: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Indirizzo</label>
              <input
                type="text"
                value={formData.indirizzo}
                onChange={e => setFormData({ ...formData, indirizzo: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Citta</label>
                <input
                  type="text"
                  value={formData.citta}
                  onChange={e => setFormData({ ...formData, citta: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">CAP</label>
                <input
                  type="text"
                  value={formData.cap}
                  onChange={e => setFormData({ ...formData, cap: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Telefono</label>
              <input
                type="tel"
                value={formData.telefono}
                onChange={e => setFormData({ ...formData, telefono: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={e => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            {sede && (
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="attivo"
                  checked={formData.attivo}
                  onChange={e => setFormData({ ...formData, attivo: e.target.checked })}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded"
                />
                <label htmlFor="attivo" className="text-sm text-gray-700">Attivo</label>
              </div>
            )}
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

function StaffModal({ staff, sedi, onSave, onClose, isLoading }: {
  staff: BookingStaff | null
  sedi: BookingSede[]
  onSave: (data: any) => void
  onClose: () => void
  isLoading: boolean
}) {
  const [formData, setFormData] = useState({
    nome: staff?.nome || '',
    cognome: staff?.cognome || '',
    email: staff?.email || '',
    telefono: staff?.telefono || '',
    ruolo: staff?.ruolo || '',
    sede_id: (staff as any)?.sede_id || (sedi.length > 0 ? sedi[0].id : 0),
    attivo: staff?.attivo ?? true,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.sede_id && sedi.length > 0) {
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
            {staff ? 'Modifica Staff' : 'Nuovo Staff'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={e => setFormData({ ...formData, nome: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cognome *</label>
                <input
                  type="text"
                  value={formData.cognome}
                  onChange={e => setFormData({ ...formData, cognome: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
              <input
                type="email"
                value={formData.email}
                onChange={e => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sede *</label>
              {sedi.length === 0 ? (
                <p className="text-sm text-red-500">Nessuna sede disponibile. Crea prima una sede.</p>
              ) : (
                <select
                  value={formData.sede_id}
                  onChange={e => setFormData({ ...formData, sede_id: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  required
                >
                  {sedi.filter(s => s.attivo).map(sede => (
                    <option key={sede.id} value={sede.id}>{sede.nome}</option>
                  ))}
                </select>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Telefono</label>
              <input
                type="tel"
                value={formData.telefono}
                onChange={e => setFormData({ ...formData, telefono: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ruolo</label>
              <input
                type="text"
                value={formData.ruolo}
                onChange={e => setFormData({ ...formData, ruolo: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                placeholder="es. Consulente, Segretario..."
              />
            </div>
            {staff && (
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="attivo"
                  checked={formData.attivo}
                  onChange={e => setFormData({ ...formData, attivo: e.target.checked })}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded"
                />
                <label htmlFor="attivo" className="text-sm text-gray-700">Attivo</label>
              </div>
            )}
            <div className="flex justify-end gap-3 pt-4">
              <button type="button" onClick={onClose} className="btn-secondary">
                Annulla
              </button>
              <button type="submit" disabled={isLoading || sedi.length === 0} className="btn-primary">
                {isLoading ? 'Salvataggio...' : 'Salva'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

function TipoAppuntamentoModal({ tipo, servizi, onSave, onClose, isLoading }: {
  tipo: BookingTipoAppuntamento | null
  servizi: BookingServizio[]
  onSave: (data: any) => void
  onClose: () => void
  isLoading: boolean
}) {
  // Determina quali servizi sono attualmente associate a questo tipo
  const currentCampagneIds = tipo
    ? servizi
        .filter(c => (c as any).tipi_appuntamento?.some((t: BookingTipoAppuntamento) => t.id === tipo.id))
        .map(c => c.id)
    : []

  const [formData, setFormData] = useState({
    nome: tipo?.nome || '',
    descrizione: tipo?.descrizione || '',
    durata_default_minuti: tipo?.durata_default_minuti || 30,
    colore: tipo?.colore || '#3b82f6',
    attivo: tipo?.attivo ?? true,
    servizi_ids: currentCampagneIds,
  })

  const toggleServizio = (servizioId: number) => {
    setFormData(prev => ({
      ...prev,
      servizi_ids: prev.servizi_ids.includes(servizioId)
        ? prev.servizi_ids.filter(id => id !== servizioId)
        : [...prev.servizi_ids, servizioId]
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  // Filtra solo servizi attive
  const serviziAttivi = servizi.filter(c => c.attivo !== false)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">
            {tipo ? 'Modifica Tipo Appuntamento' : 'Nuovo Tipo Appuntamento'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
              <input
                type="text"
                value={formData.nome}
                onChange={e => setFormData({ ...formData, nome: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Descrizione</label>
              <textarea
                value={formData.descrizione}
                onChange={e => setFormData({ ...formData, descrizione: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                rows={2}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Durata (minuti) *</label>
                <input
                  type="number"
                  value={formData.durata_default_minuti}
                  onChange={e => setFormData({ ...formData, durata_default_minuti: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  min={5}
                  max={480}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Colore</label>
                <input
                  type="color"
                  value={formData.colore}
                  onChange={e => setFormData({ ...formData, colore: e.target.value })}
                  className="w-full h-10 px-1 py-1 border border-gray-300 rounded-lg cursor-pointer"
                />
              </div>
            </div>

            {/* Selezione Servizi */}
            {serviziAttivi.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Associa a Servizi
                </label>
                <div className="space-y-2 max-h-32 overflow-y-auto border border-gray-200 rounded-lg p-2">
                  {serviziAttivi.map(servizio => (
                    <label
                      key={servizio.id}
                      className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={formData.servizi_ids.includes(servizio.id)}
                        onChange={() => toggleServizio(servizio.id)}
                        className="w-4 h-4 text-purple-600 border-gray-300 rounded"
                      />
                      <span className="text-sm text-gray-700">{servizio.nome}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {tipo && (
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="attivo"
                  checked={formData.attivo}
                  onChange={e => setFormData({ ...formData, attivo: e.target.checked })}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded"
                />
                <label htmlFor="attivo" className="text-sm text-gray-700">Attivo</label>
              </div>
            )}
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

function ServizioModal({ servizio, tipiAppuntamento, onSave, onClose, isLoading }: {
  servizio: BookingServizio | null
  tipiAppuntamento: BookingTipoAppuntamento[]
  onSave: (data: any) => void
  onClose: () => void
  isLoading: boolean
}) {
  const today = format(new Date(), 'yyyy-MM-dd')
  const nextMonth = format(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), 'yyyy-MM-dd')

  const [formData, setFormData] = useState({
    nome: servizio?.nome || '',
    descrizione: servizio?.descrizione || '',
    data_inizio: servizio?.data_inizio ? format(parseISO(servizio.data_inizio), 'yyyy-MM-dd') : today,
    data_fine: servizio?.data_fine ? format(parseISO(servizio.data_fine), 'yyyy-MM-dd') : nextMonth,
    slug: servizio?.slug || '',
    tipi_appuntamento_ids: (servizio as any)?.tipi_appuntamento?.map((t: BookingTipoAppuntamento) => t.id) || [],
    attiva: servizio?.attivo ?? true,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (new Date(formData.data_fine) < new Date(formData.data_inizio)) {
      toast.error('La data fine deve essere successiva alla data inizio')
      return
    }
    // Converti stringhe vuote in null per campi opzionali
    const dataToSend = {
      nome: formData.nome,
      descrizione: formData.descrizione || null,
      data_inizio: formData.data_inizio,
      data_fine: formData.data_fine,
      slug: formData.slug || null,
      tipi_appuntamento_ids: formData.tipi_appuntamento_ids,
      // Non inviare 'attiva' in fase di creazione (solo update)
      ...(servizio ? { attivo: formData.attiva } : {}),
    }
    onSave(dataToSend)
  }

  const toggleTipo = (tipoId: number) => {
    setFormData(prev => ({
      ...prev,
      tipi_appuntamento_ids: prev.tipi_appuntamento_ids.includes(tipoId)
        ? prev.tipi_appuntamento_ids.filter((id: number) => id !== tipoId)
        : [...prev.tipi_appuntamento_ids, tipoId]
    }))
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">
            {servizio ? 'Modifica Servizio' : 'Nuovo Servizio'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
              <input
                type="text"
                value={formData.nome}
                onChange={e => setFormData({ ...formData, nome: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                placeholder="es. Consulenza Pensioni 2025"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Descrizione</label>
              <textarea
                value={formData.descrizione}
                onChange={e => setFormData({ ...formData, descrizione: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                rows={2}
                placeholder="Descrizione del servizio..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Inizio *</label>
                <input
                  type="date"
                  value={formData.data_inizio}
                  onChange={e => setFormData({ ...formData, data_inizio: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Fine *</label>
                <input
                  type="date"
                  value={formData.data_fine}
                  onChange={e => setFormData({ ...formData, data_fine: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Slug URL</label>
              <input
                type="text"
                value={formData.slug}
                onChange={e => setFormData({ ...formData, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                placeholder="consulenza-pensioni-2025"
              />
              <p className="text-xs text-gray-500 mt-1">Lascia vuoto per generare automaticamente dal nome</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Tipi Appuntamento Disponibili</label>
              {tipiAppuntamento.length === 0 ? (
                <p className="text-sm text-gray-500">Nessun tipo appuntamento configurato</p>
              ) : (
                <div className="space-y-2 max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3">
                  {tipiAppuntamento.filter(t => t.attivo).map(tipo => (
                    <label key={tipo.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                      <input
                        type="checkbox"
                        checked={formData.tipi_appuntamento_ids.includes(tipo.id)}
                        onChange={() => toggleTipo(tipo.id)}
                        className="w-4 h-4 text-primary-600 border-gray-300 rounded"
                      />
                      <span
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: tipo.colore || '#6b7280' }}
                      />
                      <span className="text-sm text-gray-700">{tipo.nome}</span>
                      <span className="text-xs text-gray-400">({tipo.durata_default_minuti} min)</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
            {servizio && (
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="attiva-servizio"
                  checked={formData.attiva}
                  onChange={e => setFormData({ ...formData, attiva: e.target.checked })}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded"
                />
                <label htmlFor="attiva-servizio" className="text-sm text-gray-700">Attiva</label>
              </div>
            )}
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

type DateSelectionMode = 'single' | 'multiple' | 'range'

const WEEKDAYS = [
  { id: 1, label: 'Lun', name: 'Lunedì' },
  { id: 2, label: 'Mar', name: 'Martedì' },
  { id: 3, label: 'Mer', name: 'Mercoledì' },
  { id: 4, label: 'Gio', name: 'Giovedì' },
  { id: 5, label: 'Ven', name: 'Venerdì' },
  { id: 6, label: 'Sab', name: 'Sabato' },
  { id: 0, label: 'Dom', name: 'Domenica' },
]

function DisponibilitaAdminModal({ staffName, sedi, tipiAppuntamento, servizi, esistente, onSaveAsync, onClose, isLoading }: {
  staffName: string
  sedi: BookingSede[]
  tipiAppuntamento: BookingTipoAppuntamento[]
  servizi: BookingServizio[]
  esistente?: any
  onSaveAsync: (data: { sede_id: number; servizio_id?: number; data: string; ora_inizio: string; ora_fine: string; durata_slot_minuti?: number; note?: string; tipi_appuntamento_ids?: number[] }) => Promise<boolean>
  onClose: () => void
  isLoading: boolean
}) {
  const today = format(new Date(), 'yyyy-MM-dd')

  // Filtra solo servizi attivi
  const serviziAttivi = servizi.filter(c => c.attivo !== false)

  // Modalità selezione date: single, multiple, range
  const [dateMode, setDateMode] = useState<DateSelectionMode>(esistente ? 'single' : 'single')

  // Per modalità multiple: array di date selezionate
  const [selectedDates, setSelectedDates] = useState<string[]>([])

  // Per modalità range: date inizio/fine + giorni settimana
  const [rangeData, setRangeData] = useState({
    dataInizio: today,
    dataFine: today,
    giorniSettimana: [1, 2, 3, 4, 5] as number[], // Lun-Ven default
  })

  const [formData, setFormData] = useState({
    servizio_id: esistente?.servizio_id || (serviziAttivi.length > 0 ? serviziAttivi[0].id : 0),
    sede_id: esistente?.sede_id || (sedi.length > 0 ? sedi[0].id : 0),
    data: esistente?.data || today,
    ora_inizio: esistente?.ora_inizio?.slice(0, 5) || '09:00',
    ora_fine: esistente?.ora_fine?.slice(0, 5) || '13:00',
    durata_slot_minuti: esistente?.durata_slot_minuti || null as number | null,
    note: esistente?.note || '',
    tipi_appuntamento_ids: esistente?.tipi_appuntamento?.map((t: any) => t.id) || [] as number[],
  })

  // Stato per salvare multiple disponibilità
  const [isSavingMultiple, setIsSavingMultiple] = useState(false)
  const [savedCount, setSavedCount] = useState(0)
  const [totalToSave, setTotalToSave] = useState(0)

  // Get selected servizio for date validation
  const selectedServizio = servizi.find(c => c.id === formData.servizio_id)
  const minDate = selectedServizio ? format(parseISO(selectedServizio.data_inizio), 'yyyy-MM-dd') : today
  const maxDate = selectedServizio ? format(parseISO(selectedServizio.data_fine), 'yyyy-MM-dd') : undefined

  // Get available tipi for selected servizio
  const availableTipi = selectedServizio?.tipi_appuntamento || tipiAppuntamento

  // Genera le date nel range che corrispondono ai giorni settimana selezionati
  const generateDatesFromRange = (): string[] => {
    if (!rangeData.dataInizio || !rangeData.dataFine || rangeData.giorniSettimana.length === 0) {
      return []
    }

    const dates: string[] = []
    const startDate = new Date(rangeData.dataInizio)
    const endDate = new Date(rangeData.dataFine)

    // Validate against servizio dates
    if (selectedServizio) {
      const servizioStart = new Date(selectedServizio.data_inizio)
      const servizioEnd = new Date(selectedServizio.data_fine)
      if (startDate < servizioStart) startDate.setTime(servizioStart.getTime())
      if (endDate > servizioEnd) endDate.setTime(servizioEnd.getTime())
    }

    const current = new Date(startDate)
    while (current <= endDate) {
      const dayOfWeek = current.getDay()
      if (rangeData.giorniSettimana.includes(dayOfWeek)) {
        dates.push(format(current, 'yyyy-MM-dd'))
      }
      current.setDate(current.getDate() + 1)
    }

    return dates
  }

  // Toggle date selection in multiple mode
  const toggleDateSelection = (date: string) => {
    setSelectedDates(prev =>
      prev.includes(date)
        ? prev.filter(d => d !== date)
        : [...prev, date].sort()
    )
  }

  // Toggle weekday in range mode
  const toggleWeekday = (dayId: number) => {
    setRangeData(prev => ({
      ...prev,
      giorniSettimana: prev.giorniSettimana.includes(dayId)
        ? prev.giorniSettimana.filter(d => d !== dayId)
        : [...prev.giorniSettimana, dayId].sort()
    }))
  }

  // Genera lista date disponibili per il servizio selezionato
  const getAvailableDatesForServizio = (): string[] => {
    if (!selectedServizio) return []

    const dates: string[] = []
    const startDate = new Date(selectedServizio.data_inizio)
    const endDate = new Date(selectedServizio.data_fine)

    const current = new Date(startDate)
    while (current <= endDate) {
      dates.push(format(current, 'yyyy-MM-dd'))
      current.setDate(current.getDate() + 1)
    }

    return dates
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.servizio_id) {
      toast.error('Seleziona un servizio')
      return
    }
    if (!formData.sede_id) {
      toast.error('Seleziona una sede')
      return
    }
    if (formData.ora_fine <= formData.ora_inizio) {
      toast.error('L\'ora fine deve essere successiva all\'ora inizio')
      return
    }

    // Determina le date da salvare
    let datesToSave: string[] = []

    if (dateMode === 'single') {
      // Validazione data singola
      if (selectedServizio) {
        const dataScelta = new Date(formData.data)
        const dataInizio = new Date(selectedServizio.data_inizio)
        const dataFine = new Date(selectedServizio.data_fine)
        if (dataScelta < dataInizio || dataScelta > dataFine) {
          toast.error(`La data deve essere compresa nel periodo del servizio (${format(parseISO(selectedServizio.data_inizio), 'd MMM yyyy', { locale: it })} - ${format(parseISO(selectedServizio.data_fine), 'd MMM yyyy', { locale: it })})`)
          return
        }
      }
      datesToSave = [formData.data]
    } else if (dateMode === 'multiple') {
      if (selectedDates.length === 0) {
        toast.error('Seleziona almeno una data')
        return
      }
      datesToSave = selectedDates
    } else if (dateMode === 'range') {
      datesToSave = generateDatesFromRange()
      if (datesToSave.length === 0) {
        toast.error('Nessuna data valida nel range selezionato')
        return
      }
    }

    // Salva le disponibilità (singola o multiple)
    setIsSavingMultiple(true)
    setTotalToSave(datesToSave.length)
    setSavedCount(0)

    let successCount = 0
    let errorCount = 0

    for (let i = 0; i < datesToSave.length; i++) {
      try {
        const success = await onSaveAsync({
          ...formData,
          data: datesToSave[i],
          servizio_id: formData.servizio_id || undefined,
          durata_slot_minuti: formData.durata_slot_minuti || undefined,
          tipi_appuntamento_ids: formData.tipi_appuntamento_ids.length > 0 ? formData.tipi_appuntamento_ids : undefined,
        })
        if (success) {
          successCount++
        } else {
          errorCount++
        }
        setSavedCount(i + 1)
      } catch (err) {
        console.error('Errore nel salvare la data', datesToSave[i], err)
        errorCount++
        setSavedCount(i + 1)
      }
    }

    setIsSavingMultiple(false)

    // Mostra messaggio di riepilogo
    if (successCount > 0 && errorCount === 0) {
      toast.success(`${successCount} disponibilità ${successCount === 1 ? 'creata' : 'create'}`)
      onClose()
    } else if (successCount > 0 && errorCount > 0) {
      toast.error(`${successCount} create, ${errorCount} errori`)
      onClose()
    } else {
      toast.error('Errore nella creazione delle disponibilità')
    }
  }

  const toggleTipo = (tipoId: number) => {
    setFormData(prev => ({
      ...prev,
      tipi_appuntamento_ids: prev.tipi_appuntamento_ids.includes(tipoId)
        ? prev.tipi_appuntamento_ids.filter((id: number) => id !== tipoId)
        : [...prev.tipi_appuntamento_ids, tipoId]
    }))
  }

  // When servizio changes, reset tipi selection and adjust date if needed
  const handleServizioChange = (servizioId: number) => {
    const newServizio = serviziAttivi.find(c => c.id === servizioId)
    let newData = formData.data
    if (newServizio) {
      const dataScelta = new Date(formData.data)
      const dataInizio = new Date(newServizio.data_inizio)
      const dataFine = new Date(newServizio.data_fine)
      if (dataScelta < dataInizio) {
        newData = format(parseISO(newServizio.data_inizio), 'yyyy-MM-dd')
      } else if (dataScelta > dataFine) {
        newData = format(parseISO(newServizio.data_fine), 'yyyy-MM-dd')
      }
      // Aggiorna anche il range
      setRangeData({
        dataInizio: format(parseISO(newServizio.data_inizio), 'yyyy-MM-dd'),
        dataFine: format(parseISO(newServizio.data_fine), 'yyyy-MM-dd'),
        giorniSettimana: rangeData.giorniSettimana,
      })
    }
    setFormData({
      ...formData,
      servizio_id: servizioId,
      data: newData,
      tipi_appuntamento_ids: [],
    })
    setSelectedDates([])
  }

  // Calcola le date nel range per il preview
  const rangeDatesPreview = dateMode === 'range' ? generateDatesFromRange() : []

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-1">
            {esistente ? 'Modifica Disponibilità' : 'Aggiungi Disponibilità'}
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            Per: <span className="font-medium text-gray-700">{staffName}</span>
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Servizio - REQUIRED */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Servizio *</label>
              {serviziAttivi.length === 0 ? (
                <p className="text-sm text-red-500">Nessun servizio attivo. Crea prima un servizio.</p>
              ) : (
                <select
                  value={formData.servizio_id}
                  onChange={e => handleServizioChange(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  required
                >
                  {serviziAttivi.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.nome} ({format(parseISO(c.data_inizio), 'd MMM', { locale: it })} - {format(parseISO(c.data_fine), 'd MMM yyyy', { locale: it })})
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Modalità selezione date - solo per nuove disponibilità */}
            {!esistente && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Modalità Selezione Date</label>
                <div className="flex gap-2 flex-wrap">
                  <button
                    type="button"
                    onClick={() => setDateMode('single')}
                    className={`px-3 py-1.5 text-sm rounded-lg border ${
                      dateMode === 'single'
                        ? 'bg-primary-100 border-primary-500 text-primary-700'
                        : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    Data Singola
                  </button>
                  <button
                    type="button"
                    onClick={() => setDateMode('multiple')}
                    className={`px-3 py-1.5 text-sm rounded-lg border ${
                      dateMode === 'multiple'
                        ? 'bg-primary-100 border-primary-500 text-primary-700'
                        : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    Date Multiple
                  </button>
                  <button
                    type="button"
                    onClick={() => setDateMode('range')}
                    className={`px-3 py-1.5 text-sm rounded-lg border ${
                      dateMode === 'range'
                        ? 'bg-primary-100 border-primary-500 text-primary-700'
                        : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    Range + Giorni Settimana
                  </button>
                </div>
              </div>
            )}

            {/* Data Singola */}
            {(dateMode === 'single' || esistente) && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data *</label>
                <input
                  type="date"
                  value={formData.data}
                  onChange={e => setFormData({ ...formData, data: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  min={minDate}
                  max={maxDate}
                  required={dateMode === 'single'}
                />
                {selectedServizio && (
                  <p className="text-xs text-gray-500 mt-1">
                    Periodo servizio: {format(parseISO(selectedServizio.data_inizio), 'd MMM', { locale: it })} - {format(parseISO(selectedServizio.data_fine), 'd MMM yyyy', { locale: it })}
                  </p>
                )}
              </div>
            )}

            {/* Date Multiple */}
            {dateMode === 'multiple' && !esistente && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Seleziona Date ({selectedDates.length} selezionate)
                </label>
                <div className="border border-gray-200 rounded-lg p-3 max-h-48 overflow-y-auto">
                  {selectedServizio ? (
                    <div className="grid grid-cols-3 gap-2">
                      {getAvailableDatesForServizio().map(date => {
                        const dateObj = new Date(date)
                        const dayName = format(dateObj, 'EEE', { locale: it })
                        const isSelected = selectedDates.includes(date)
                        const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6

                        return (
                          <button
                            key={date}
                            type="button"
                            onClick={() => toggleDateSelection(date)}
                            className={`p-2 text-xs rounded-lg border transition-colors ${
                              isSelected
                                ? 'bg-primary-100 border-primary-500 text-primary-700'
                                : isWeekend
                                  ? 'border-gray-200 text-gray-400 hover:bg-gray-50'
                                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                            }`}
                          >
                            <div className="font-medium">{format(dateObj, 'd MMM', { locale: it })}</div>
                            <div className="text-[10px] opacity-75">{dayName}</div>
                          </button>
                        )
                      })}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">Seleziona prima un servizio</p>
                  )}
                </div>
              </div>
            )}

            {/* Range + Giorni Settimana */}
            {dateMode === 'range' && !esistente && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Da *</label>
                    <input
                      type="date"
                      value={rangeData.dataInizio}
                      onChange={e => setRangeData({ ...rangeData, dataInizio: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      min={minDate}
                      max={maxDate}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">A *</label>
                    <input
                      type="date"
                      value={rangeData.dataFine}
                      onChange={e => setRangeData({ ...rangeData, dataFine: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      min={rangeData.dataInizio || minDate}
                      max={maxDate}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Giorni della Settimana</label>
                  <div className="flex gap-1 flex-wrap">
                    {WEEKDAYS.map(day => (
                      <button
                        key={day.id}
                        type="button"
                        onClick={() => toggleWeekday(day.id)}
                        className={`w-10 h-10 text-sm rounded-lg border transition-colors ${
                          rangeData.giorniSettimana.includes(day.id)
                            ? 'bg-primary-100 border-primary-500 text-primary-700'
                            : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                        }`}
                        title={day.name}
                      >
                        {day.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Preview date generate */}
                {rangeDatesPreview.length > 0 && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-500 mb-2">
                      Verranno create <span className="font-semibold text-primary-600">{rangeDatesPreview.length}</span> disponibilità:
                    </p>
                    <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                      {rangeDatesPreview.slice(0, 20).map(date => (
                        <span key={date} className="text-xs bg-white px-2 py-1 rounded border border-gray-200">
                          {format(new Date(date), 'd MMM', { locale: it })}
                        </span>
                      ))}
                      {rangeDatesPreview.length > 20 && (
                        <span className="text-xs text-gray-500 px-2 py-1">
                          +{rangeDatesPreview.length - 20} altre...
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sede *</label>
              {sedi.length === 0 ? (
                <p className="text-sm text-red-500">Nessuna sede disponibile. Crea prima una sede.</p>
              ) : (
                <select
                  value={formData.sede_id}
                  onChange={e => setFormData({ ...formData, sede_id: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  required
                >
                  {sedi.filter(s => s.attivo).map(sede => (
                    <option key={sede.id} value={sede.id}>{sede.nome}</option>
                  ))}
                </select>
              )}
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

            {/* Durata personalizzata slot */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Durata Slot (minuti)
                <span className="text-xs text-gray-400 ml-2">(opzionale - sovrascrive durata default)</span>
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min="10"
                  max="120"
                  step="5"
                  value={formData.durata_slot_minuti || ''}
                  onChange={e => setFormData({ ...formData, durata_slot_minuti: e.target.value ? parseInt(e.target.value) : null })}
                  className="w-32 px-3 py-2 border border-gray-300 rounded-lg"
                  placeholder="30"
                />
                <span className="text-sm text-gray-500">
                  Default: 30 min. Usa 45 min se la persona è più lenta.
                </span>
              </div>
            </div>

            {/* Tipi Appuntamento - filtrati per servizio selezionato */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tipi Appuntamento Gestibili
                <span className="text-xs text-gray-400 ml-2">(opzionale - se vuoto, tutti i tipi del servizio)</span>
              </label>
              {availableTipi.length === 0 ? (
                <p className="text-sm text-gray-500">Nessun tipo appuntamento disponibile per questo servizio</p>
              ) : (
                <div className="space-y-2 max-h-32 overflow-y-auto border border-gray-200 rounded-lg p-3">
                  {availableTipi.filter((t: any) => t.attivo !== false).map((tipo: any) => (
                    <label key={tipo.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                      <input
                        type="checkbox"
                        checked={formData.tipi_appuntamento_ids.includes(tipo.id)}
                        onChange={() => toggleTipo(tipo.id)}
                        className="w-4 h-4 text-primary-600 border-gray-300 rounded"
                      />
                      <span
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: tipo.colore || '#6b7280' }}
                      />
                      <span className="text-sm text-gray-700">{tipo.nome}</span>
                    </label>
                  ))}
                </div>
              )}
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

            {/* Progress bar per salvataggio multiplo */}
            {isSavingMultiple && (
              <div className="bg-primary-50 rounded-lg p-3">
                <div className="flex items-center justify-between text-sm text-primary-700 mb-2">
                  <span>Salvataggio in corso...</span>
                  <span>{savedCount}/{totalToSave}</span>
                </div>
                <div className="w-full bg-primary-200 rounded-full h-2">
                  <div
                    className="bg-primary-600 h-2 rounded-full transition-all"
                    style={{ width: `${(savedCount / totalToSave) * 100}%` }}
                  />
                </div>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-4">
              <button type="button" onClick={onClose} className="btn-secondary" disabled={isSavingMultiple}>
                Annulla
              </button>
              <button
                type="submit"
                disabled={isLoading || isSavingMultiple || sedi.length === 0 || servizi.length === 0}
                className="btn-primary"
              >
                {isSavingMultiple
                  ? `Salvataggio ${savedCount}/${totalToSave}...`
                  : isLoading
                    ? 'Salvataggio...'
                    : dateMode !== 'single' && !esistente
                      ? `Salva ${dateMode === 'multiple' ? selectedDates.length : rangeDatesPreview.length} Disponibilità`
                      : 'Salva'
                }
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
