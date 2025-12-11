/**
 * Pagina Admin per gestione modulo prenotazioni
 *
 * Include tabs per:
 * - Dashboard statistiche
 * - Prenotazioni
 * - Sedi
 * - Staff
 * - Tipi Appuntamento
 * - Campagne
 * - Configurazione
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BarChart3,
  Calendar,
  MapPin,
  Users,
  Briefcase,
  Settings,
  Plus,
  Edit,
  Trash2,
  Eye,
  Download,
  RefreshCw,
  Check,
  X,
  Clock,
  FileText,
  Search,
  ChevronDown,
  Building,
  Tag
} from 'lucide-react'
import toast from 'react-hot-toast'
import { format, parseISO } from 'date-fns'
import { it } from 'date-fns/locale'
import { bookingAdminApi } from '../lib/api'
import type {
  BookingSede,
  BookingStaff,
  BookingTipoAppuntamento,
  BookingCampagna,
  BookingPrenotazione,
  BookingStats,
  StatoPrenotazione
} from '../types'

// Tabs
type Tab = 'dashboard' | 'prenotazioni' | 'sedi' | 'staff' | 'tipi' | 'campagne' | 'config'

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
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')

  // === TAB COMPONENTS ===

  const tabs = [
    { id: 'dashboard' as Tab, name: 'Dashboard', icon: BarChart3 },
    { id: 'prenotazioni' as Tab, name: 'Prenotazioni', icon: Calendar },
    { id: 'sedi' as Tab, name: 'Sedi', icon: MapPin },
    { id: 'staff' as Tab, name: 'Staff', icon: Users },
    { id: 'tipi' as Tab, name: 'Tipi Appuntamento', icon: Briefcase },
    { id: 'campagne' as Tab, name: 'Campagne', icon: Tag },
    { id: 'config' as Tab, name: 'Configurazione', icon: Settings },
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
        {activeTab === 'campagne' && <CampagneTab />}
        {activeTab === 'config' && <ConfigTab />}
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

  const { data: staff, isLoading } = useQuery({
    queryKey: ['booking-admin-staff'],
    queryFn: () => bookingAdminApi.getStaff().then(r => r.data),
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
              <div key={s.id} className="flex items-center justify-between p-4 hover:bg-gray-50">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-medium ${s.attivo ? 'bg-primary-500' : 'bg-gray-400'}`}>
                    {s.nome[0]}{s.cognome[0]}
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{s.nome} {s.cognome}</div>
                    <div className="text-sm text-gray-500">{s.email}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {s.ruolo && (
                    <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">
                      {s.ruolo}
                    </span>
                  )}
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
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <StaffModal
          staff={editItem}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditItem(null) }}
          isLoading={createMutation.isPending || updateMutation.isPending}
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

  const createMutation = useMutation({
    mutationFn: bookingAdminApi.creaTipoAppuntamento,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-tipi'] })
      toast.success('Tipo appuntamento creato')
      setShowModal(false)
    },
    onError: () => toast.error('Errore nella creazione'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => bookingAdminApi.aggiornaTipoAppuntamento(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-tipi'] })
      toast.success('Tipo appuntamento aggiornato')
      setShowModal(false)
      setEditItem(null)
    },
    onError: () => toast.error('Errore nell\'aggiornamento'),
  })

  const deleteMutation = useMutation({
    mutationFn: bookingAdminApi.eliminaTipoAppuntamento,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-tipi'] })
      toast.success('Tipo appuntamento eliminato')
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
  const [editItem, setEditItem] = useState<BookingCampagna | null>(null)

  const { data: campagne, isLoading } = useQuery({
    queryKey: ['booking-admin-campagne'],
    queryFn: () => bookingAdminApi.getCampagne().then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: bookingAdminApi.creaCampagna,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-campagne'] })
      toast.success('Campagna creata')
      setShowModal(false)
    },
    onError: () => toast.error('Errore nella creazione'),
  })

  const deleteMutation = useMutation({
    mutationFn: bookingAdminApi.eliminaCampagna,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booking-admin-campagne'] })
      toast.success('Campagna eliminata')
    },
    onError: () => toast.error('Errore nell\'eliminazione'),
  })

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => { setEditItem(null); setShowModal(true) }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nuova Campagna
        </button>
      </div>

      <div className="card">
        {isLoading ? (
          <LoadingSpinner />
        ) : (campagne as BookingCampagna[] || []).length === 0 ? (
          <EmptyState message="Nessuna campagna configurata" />
        ) : (
          <div className="divide-y divide-gray-200">
            {(campagne as BookingCampagna[]).map(c => (
              <div key={c.id} className="flex items-center justify-between p-4 hover:bg-gray-50">
                <div>
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${c.attiva ? 'bg-green-500' : 'bg-gray-300'}`} />
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
                      if (confirm('Eliminare questa campagna?')) {
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

      {/* Modal placeholder */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">
              {editItem ? 'Modifica Campagna' : 'Nuova Campagna'}
            </h3>
            <p className="text-gray-500 text-sm">Form campagna - da implementare</p>
            <div className="flex justify-end mt-4">
              <button onClick={() => setShowModal(false)} className="btn-secondary">
                Chiudi
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// === CONFIG TAB ===
function ConfigTab() {
  const { data: config, isLoading } = useQuery({
    queryKey: ['booking-admin-config'],
    queryFn: () => bookingAdminApi.getConfig().then(r => r.data),
  })

  const configMutation = useMutation({
    mutationFn: ({ chiave, valore }: { chiave: string; valore: any }) =>
      bookingAdminApi.setConfig(chiave, valore),
    onSuccess: () => {
      toast.success('Configurazione salvata')
    },
    onError: () => toast.error('Errore nel salvataggio'),
  })

  if (isLoading) {
    return <LoadingSpinner />
  }

  const configData = config as Record<string, any> || {}

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-6">Configurazione Sistema</h3>

      <div className="space-y-6">
        {Object.entries(configData).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">{key}</div>
              <div className="text-sm text-gray-500">Valore attuale: {String(value)}</div>
            </div>
            <button
              onClick={() => {
                const newValue = prompt(`Nuovo valore per ${key}:`, String(value))
                if (newValue !== null) {
                  configMutation.mutate({ chiave: key, valore: newValue })
                }
              }}
              className="btn-secondary"
            >
              Modifica
            </button>
          </div>
        ))}

        {Object.keys(configData).length === 0 && (
          <EmptyState message="Nessuna configurazione disponibile" />
        )}
      </div>
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

function StaffModal({ staff, onSave, onClose, isLoading }: {
  staff: BookingStaff | null
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
    attivo: staff?.attivo ?? true,
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

function TipoAppuntamentoModal({ tipo, onSave, onClose, isLoading }: {
  tipo: BookingTipoAppuntamento | null
  onSave: (data: any) => void
  onClose: () => void
  isLoading: boolean
}) {
  const [formData, setFormData] = useState({
    nome: tipo?.nome || '',
    descrizione: tipo?.descrizione || '',
    durata_default_minuti: tipo?.durata_default_minuti || 30,
    colore: tipo?.colore || '#3b82f6',
    attivo: tipo?.attivo ?? true,
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
