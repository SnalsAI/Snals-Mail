import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, MapPin, Plus, Trash2, Edit, Check, X, Mail, Phone, ChevronDown, ChevronUp } from 'lucide-react'
import toast from 'react-hot-toast'
import axios from 'axios'
import { schoolsApi } from '../lib/api'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

interface Zona {
  id: number
  nome: string
  descrizione: string
  attiva: boolean
  comuni: string[]
  num_delegati?: number
}

interface Delegato {
  id: number
  nome: string
  cognome: string
  nome_completo: string
  email: string
  telefono: string
  attivo: boolean
  note: string | null
  zone: { id: number; nome: string }[]
}

export default function Delegati() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'delegati' | 'zone'>('delegati')

  // Form state for new delegato
  const [showDelegatoForm, setShowDelegatoForm] = useState(false)
  const [editingDelegato, setEditingDelegato] = useState<Delegato | null>(null)
  const [delegatoForm, setDelegatoForm] = useState({
    nome: '',
    cognome: '',
    email: '',
    telefono: '',
    zone_ids: [] as number[],
    note: ''
  })

  // Form state for new zona
  const [showZonaForm, setShowZonaForm] = useState(false)
  const [editingZona, setEditingZona] = useState<Zona | null>(null)
  const [zonaForm, setZonaForm] = useState({
    nome: '',
    descrizione: '',
    comuni: ''
  })
  const [showComuniSelector, setShowComuniSelector] = useState(false)

  // Fetch delegati
  const { data: delegatiData, isLoading: loadingDelegati } = useQuery({
    queryKey: ['delegati'],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/delegati/`)
      return res.data
    }
  })

  // Fetch zone
  const { data: zoneData, isLoading: loadingZone } = useQuery({
    queryKey: ['zone'],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/delegati/zone/`)
      return res.data
    }
  })

  // Fetch schools to get comuni list
  const { data: schoolsData } = useQuery({
    queryKey: ['schools'],
    queryFn: () => schoolsApi.getAll().then(res => res.data)
  })

  const delegati: Delegato[] = delegatiData?.delegati || []
  const zone: Zona[] = zoneData?.zone || []

  // Extract unique comuni from schools - SOLO provincia Taranto (codice inizia con TA)
  const availableComuni = useMemo(() => {
    const schools = schoolsData?.schools || []
    const comuniSet = new Set<string>()
    schools.forEach((school: any) => {
      // Filtra solo scuole della provincia di Taranto (codice meccanografico inizia con TA)
      const codice = school.codice || ''
      if (codice.toUpperCase().startsWith('TA') && school.comune) {
        comuniSet.add(school.comune.toUpperCase())
      }
    })
    return Array.from(comuniSet).sort()
  }, [schoolsData])

  // Get currently selected comuni from form
  const selectedComuni = useMemo(() => {
    return zonaForm.comuni
      .split(',')
      .map(c => c.trim().toUpperCase())
      .filter(c => c)
  }, [zonaForm.comuni])

  // Toggle comune selection
  const toggleComune = (comune: string) => {
    const currentComuni = selectedComuni
    let newComuni: string[]
    if (currentComuni.includes(comune)) {
      newComuni = currentComuni.filter(c => c !== comune)
    } else {
      newComuni = [...currentComuni, comune]
    }
    setZonaForm({ ...zonaForm, comuni: newComuni.join(', ') })
  }

  // Riepilogo mappatura comuni -> zone -> delegati
  const comuniSummary = useMemo(() => {
    const summary: {
      comune: string
      zona: string | null
      zonaId: number | null
      delegati: string[]
    }[] = []

    // Per ogni comune disponibile, trova zona e delegati
    availableComuni.forEach(comune => {
      const zonaAssegnata = zone.find(z => z.comuni.map(c => c.toUpperCase()).includes(comune))
      const delegatiZona = zonaAssegnata
        ? delegati.filter(d => d.zone.some(z => z.id === zonaAssegnata.id)).map(d => d.nome_completo)
        : []

      summary.push({
        comune,
        zona: zonaAssegnata?.nome || null,
        zonaId: zonaAssegnata?.id || null,
        delegati: delegatiZona
      })
    })

    return summary
  }, [availableComuni, zone, delegati])

  // Comuni non assegnati a nessuna zona
  const comuniNonAssegnati = useMemo(() => {
    return comuniSummary.filter(c => !c.zona)
  }, [comuniSummary])

  // Zone senza delegati
  const zoneSenzaDelegati = useMemo(() => {
    return zone.filter(z => {
      const hasDelegati = delegati.some(d => d.zone.some(dz => dz.id === z.id))
      return !hasDelegati
    })
  }, [zone, delegati])

  // Mutations for delegati
  const createDelegatoMutation = useMutation({
    mutationFn: async (data: typeof delegatoForm) => {
      const res = await axios.post(`${API_URL}/delegati/`, data)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delegati'] })
      queryClient.invalidateQueries({ queryKey: ['zone'] })
      toast.success('Delegato creato')
      resetDelegatoForm()
    },
    onError: () => toast.error('Errore nella creazione')
  })

  const updateDelegatoMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: typeof delegatoForm }) => {
      const res = await axios.put(`${API_URL}/delegati/${id}`, data)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delegati'] })
      queryClient.invalidateQueries({ queryKey: ['zone'] })
      toast.success('Delegato aggiornato')
      resetDelegatoForm()
    },
    onError: () => toast.error('Errore nell\'aggiornamento')
  })

  const deleteDelegatoMutation = useMutation({
    mutationFn: async (id: number) => {
      await axios.delete(`${API_URL}/delegati/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delegati'] })
      queryClient.invalidateQueries({ queryKey: ['zone'] })
      toast.success('Delegato eliminato')
    },
    onError: () => toast.error('Errore nell\'eliminazione')
  })

  // Mutations for zone
  const createZonaMutation = useMutation({
    mutationFn: async (data: { nome: string; descrizione: string; comuni: string[] }) => {
      const res = await axios.post(`${API_URL}/delegati/zone/`, data)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zone'] })
      toast.success('Zona creata')
      resetZonaForm()
    },
    onError: () => toast.error('Errore nella creazione')
  })

  const updateZonaMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: { nome: string; descrizione: string; comuni: string[] } }) => {
      const res = await axios.put(`${API_URL}/delegati/zone/${id}`, data)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zone'] })
      toast.success('Zona aggiornata')
      resetZonaForm()
    },
    onError: () => toast.error('Errore nell\'aggiornamento')
  })

  const deleteZonaMutation = useMutation({
    mutationFn: async (id: number) => {
      await axios.delete(`${API_URL}/delegati/zone/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zone'] })
      queryClient.invalidateQueries({ queryKey: ['delegati'] })
      toast.success('Zona eliminata')
    },
    onError: () => toast.error('Errore nell\'eliminazione')
  })

  const resetDelegatoForm = () => {
    setShowDelegatoForm(false)
    setEditingDelegato(null)
    setDelegatoForm({ nome: '', cognome: '', email: '', telefono: '', zone_ids: [], note: '' })
  }

  const resetZonaForm = () => {
    setShowZonaForm(false)
    setEditingZona(null)
    setZonaForm({ nome: '', descrizione: '', comuni: '' })
    setShowComuniSelector(false)
  }

  const handleEditDelegato = (d: Delegato) => {
    setEditingDelegato(d)
    setDelegatoForm({
      nome: d.nome,
      cognome: d.cognome,
      email: d.email,
      telefono: d.telefono || '',
      zone_ids: d.zone.map(z => z.id),
      note: d.note || ''
    })
    setShowDelegatoForm(true)
  }

  const handleEditZona = (z: Zona) => {
    setEditingZona(z)
    setZonaForm({
      nome: z.nome,
      descrizione: z.descrizione || '',
      comuni: z.comuni.join(', ')
    })
    setShowZonaForm(true)
  }

  const handleSaveDelegato = () => {
    if (!delegatoForm.nome || !delegatoForm.cognome || !delegatoForm.email) {
      toast.error('Compila nome, cognome e email')
      return
    }
    if (editingDelegato) {
      updateDelegatoMutation.mutate({ id: editingDelegato.id, data: delegatoForm })
    } else {
      createDelegatoMutation.mutate(delegatoForm)
    }
  }

  const handleSaveZona = () => {
    if (!zonaForm.nome) {
      toast.error('Inserisci il nome della zona')
      return
    }
    const comuni = zonaForm.comuni.split(',').map(c => c.trim().toUpperCase()).filter(c => c)
    const data = { nome: zonaForm.nome, descrizione: zonaForm.descrizione, comuni }

    if (editingZona) {
      updateZonaMutation.mutate({ id: editingZona.id, data })
    } else {
      createZonaMutation.mutate(data)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Delegati e Zone</h1>
        <p className="mt-1 text-sm text-gray-500">
          Gestisci delegati sindacali e zone di competenza
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          <button
            onClick={() => setActiveTab('delegati')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'delegati'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Users className="w-4 h-4 inline mr-2" />
            Delegati ({delegati.length})
          </button>
          <button
            onClick={() => setActiveTab('zone')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'zone'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <MapPin className="w-4 h-4 inline mr-2" />
            Zone ({zone.length})
          </button>
        </nav>
      </div>

      {/* Content */}
      {activeTab === 'delegati' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => setShowDelegatoForm(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Nuovo Delegato
            </button>
          </div>

          {/* Form Delegato */}
          {showDelegatoForm && (
            <div className="card bg-blue-50 border-blue-200">
              <h3 className="font-semibold text-gray-900 mb-4">
                {editingDelegato ? 'Modifica Delegato' : 'Nuovo Delegato'}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Nome *"
                  className="input"
                  value={delegatoForm.nome}
                  onChange={(e) => setDelegatoForm({ ...delegatoForm, nome: e.target.value })}
                />
                <input
                  type="text"
                  placeholder="Cognome *"
                  className="input"
                  value={delegatoForm.cognome}
                  onChange={(e) => setDelegatoForm({ ...delegatoForm, cognome: e.target.value })}
                />
                <input
                  type="email"
                  placeholder="Email *"
                  className="input"
                  value={delegatoForm.email}
                  onChange={(e) => setDelegatoForm({ ...delegatoForm, email: e.target.value })}
                />
                <input
                  type="tel"
                  placeholder="Telefono"
                  className="input"
                  value={delegatoForm.telefono}
                  onChange={(e) => setDelegatoForm({ ...delegatoForm, telefono: e.target.value })}
                />
                <div className="md:col-span-2">
                  <label className="label">Zone di competenza</label>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {zone.map(z => (
                      <label key={z.id} className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border cursor-pointer hover:bg-gray-50">
                        <input
                          type="checkbox"
                          checked={delegatoForm.zone_ids.includes(z.id)}
                          onChange={(e) => {
                            const newIds = e.target.checked
                              ? [...delegatoForm.zone_ids, z.id]
                              : delegatoForm.zone_ids.filter(id => id !== z.id)
                            setDelegatoForm({ ...delegatoForm, zone_ids: newIds })
                          }}
                          className="w-4 h-4 text-primary-600"
                        />
                        <span className="text-sm">{z.nome}</span>
                      </label>
                    ))}
                    {zone.length === 0 && (
                      <p className="text-sm text-gray-500 italic">Nessuna zona disponibile. Crea prima una zona.</p>
                    )}
                  </div>
                </div>
                <textarea
                  placeholder="Note"
                  className="input md:col-span-2"
                  rows={2}
                  value={delegatoForm.note}
                  onChange={(e) => setDelegatoForm({ ...delegatoForm, note: e.target.value })}
                />
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <button onClick={resetDelegatoForm} className="btn-secondary">
                  <X className="w-4 h-4 mr-1" /> Annulla
                </button>
                <button onClick={handleSaveDelegato} className="btn-primary">
                  <Check className="w-4 h-4 mr-1" /> Salva
                </button>
              </div>
            </div>
          )}

          {/* Lista Delegati */}
          {loadingDelegati ? (
            <div className="card flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : delegati.length > 0 ? (
            <div className="grid gap-4">
              {delegati.map(d => (
                <div key={d.id} className="card hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 text-lg">
                        {d.nome_completo}
                        {!d.attivo && <span className="ml-2 text-sm text-red-500">(Disattivato)</span>}
                      </h3>
                      <div className="mt-2 space-y-1 text-sm text-gray-600">
                        <p className="flex items-center gap-2">
                          <Mail className="w-4 h-4" />
                          <a href={`mailto:${d.email}`} className="text-primary-600 hover:underline">{d.email}</a>
                        </p>
                        {d.telefono && (
                          <p className="flex items-center gap-2">
                            <Phone className="w-4 h-4" />
                            <a href={`tel:${d.telefono}`} className="text-primary-600 hover:underline">{d.telefono}</a>
                          </p>
                        )}
                      </div>
                      {d.zone.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {d.zone.map(z => (
                            <span key={z.id} className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                              <MapPin className="w-3 h-3 inline mr-1" />
                              {z.nome}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditDelegato(d)}
                        className="btn-secondary"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Eliminare ${d.nome_completo}?`)) {
                            deleteDelegatoMutation.mutate(d.id)
                          }
                        }}
                        className="btn-danger"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="card text-center py-12">
              <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">Nessun delegato configurato</p>
              <button onClick={() => setShowDelegatoForm(true)} className="btn-primary mt-4">
                Aggiungi Delegato
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'zone' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => setShowZonaForm(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Nuova Zona
            </button>
          </div>

          {/* Form Zona */}
          {showZonaForm && (
            <div className="card bg-green-50 border-green-200">
              <h3 className="font-semibold text-gray-900 mb-4">
                {editingZona ? 'Modifica Zona' : 'Nuova Zona'}
              </h3>
              <div className="space-y-4">
                <input
                  type="text"
                  placeholder="Nome zona *"
                  className="input"
                  value={zonaForm.nome}
                  onChange={(e) => setZonaForm({ ...zonaForm, nome: e.target.value })}
                />
                <input
                  type="text"
                  placeholder="Descrizione"
                  className="input"
                  value={zonaForm.descrizione}
                  onChange={(e) => setZonaForm({ ...zonaForm, descrizione: e.target.value })}
                />
                <div>
                  <label className="label">Comuni</label>

                  {/* Comuni Selector Toggle */}
                  <button
                    type="button"
                    onClick={() => setShowComuniSelector(!showComuniSelector)}
                    className="w-full mb-2 px-3 py-2 text-left text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center justify-between"
                  >
                    <span className="text-gray-600">
                      {selectedComuni.length > 0
                        ? `${selectedComuni.length} comuni selezionati`
                        : 'Clicca per selezionare i comuni'}
                    </span>
                    {showComuniSelector ? (
                      <ChevronUp className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    )}
                  </button>

                  {/* Clickable Comuni Grid */}
                  {showComuniSelector && availableComuni.length > 0 && (
                    <div className="mb-3 p-3 bg-white border border-gray-200 rounded-lg max-h-60 overflow-y-auto">
                      <div className="flex flex-wrap gap-2">
                        {availableComuni.map(comune => {
                          const isSelected = selectedComuni.includes(comune)
                          return (
                            <button
                              key={comune}
                              type="button"
                              onClick={() => toggleComune(comune)}
                              className={`px-3 py-1.5 text-sm rounded-lg border transition-all ${
                                isSelected
                                  ? 'bg-green-100 border-green-500 text-green-800 font-medium'
                                  : 'bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100 hover:border-gray-400'
                              }`}
                            >
                              {isSelected && <Check className="w-3 h-3 inline mr-1" />}
                              {comune}
                            </button>
                          )
                        })}
                      </div>
                      {availableComuni.length === 0 && (
                        <p className="text-sm text-gray-500 italic">
                          Nessun comune disponibile. Aggiungi prima delle scuole.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Selected comuni preview */}
                  {selectedComuni.length > 0 && (
                    <div className="mb-2 flex flex-wrap gap-1.5">
                      {selectedComuni.map(comune => (
                        <span
                          key={comune}
                          className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 rounded-md text-xs font-medium"
                        >
                          <MapPin className="w-3 h-3" />
                          {comune}
                          <button
                            type="button"
                            onClick={() => toggleComune(comune)}
                            className="ml-1 hover:text-red-600"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Manual input fallback */}
                  <textarea
                    placeholder="Oppure digita manualmente: Taranto, Grottaglie, Massafra..."
                    className="input"
                    rows={2}
                    value={zonaForm.comuni}
                    onChange={(e) => setZonaForm({ ...zonaForm, comuni: e.target.value })}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Puoi anche digitare i comuni manualmente, separati da virgola
                  </p>
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <button onClick={resetZonaForm} className="btn-secondary">
                  <X className="w-4 h-4 mr-1" /> Annulla
                </button>
                <button onClick={handleSaveZona} className="btn-primary">
                  <Check className="w-4 h-4 mr-1" /> Salva
                </button>
              </div>
            </div>
          )}

          {/* Lista Zone */}
          {loadingZone ? (
            <div className="card flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : zone.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {zone.map(z => (
                <div key={z.id} className="card hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 text-lg flex items-center gap-2">
                        <MapPin className="w-5 h-5 text-green-600" />
                        {z.nome}
                        {!z.attiva && <span className="text-sm text-red-500">(Disattivata)</span>}
                      </h3>
                      {z.descrizione && (
                        <p className="text-sm text-gray-600 mt-1">{z.descrizione}</p>
                      )}
                      <div className="mt-3 flex items-center gap-4 text-sm">
                        <span className="text-gray-500">
                          <Users className="w-4 h-4 inline mr-1" />
                          {z.num_delegati || 0} delegati
                        </span>
                        <span className="text-gray-500">
                          {z.comuni.length} comuni
                        </span>
                      </div>
                      {z.comuni.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {z.comuni.slice(0, 10).map(c => (
                            <span key={c} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                              {c}
                            </span>
                          ))}
                          {z.comuni.length > 10 && (
                            <span className="px-2 py-0.5 bg-gray-200 text-gray-600 rounded text-xs">
                              +{z.comuni.length - 10} altri
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditZona(z)}
                        className="btn-secondary"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Eliminare la zona "${z.nome}"?`)) {
                            deleteZonaMutation.mutate(z.id)
                          }
                        }}
                        className="btn-danger"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="card text-center py-12">
              <MapPin className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">Nessuna zona configurata</p>
              <button onClick={() => setShowZonaForm(true)} className="btn-primary mt-4">
                Crea Zona
              </button>
            </div>
          )}

          {/* Tabella Riepilogativa Comuni/Zone/Delegati */}
          <div className="card mt-6">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <MapPin className="w-5 h-5 text-blue-600" />
              Riepilogo Mappatura Territori
            </h3>

            {/* Warning per comuni non assegnati */}
            {comuniNonAssegnati.length > 0 && (
              <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm font-medium text-amber-800">
                  ⚠️ {comuniNonAssegnati.length} comuni senza zona assegnata:
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {comuniNonAssegnati.map(c => (
                    <span key={c.comune} className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">
                      {c.comune}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Warning per zone senza delegati */}
            {zoneSenzaDelegati.length > 0 && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm font-medium text-red-800">
                  ⚠️ {zoneSenzaDelegati.length} zone senza delegati:
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {zoneSenzaDelegati.map(z => (
                    <span key={z.id} className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs">
                      {z.nome}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Tabella completa */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Comune</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Zona</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Delegati</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {comuniSummary.map(row => (
                    <tr key={row.comune} className={!row.zona ? 'bg-amber-50' : ''}>
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">{row.comune}</td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {row.zona ? (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                            {row.zona}
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">
                            Non assegnato
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {row.delegati.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {row.delegati.map(d => (
                              <span key={d} className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                                {d}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-gray-400 text-xs italic">
                            {row.zona ? 'Nessun delegato' : '-'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {comuniSummary.length === 0 && (
              <p className="text-center text-gray-500 py-4 text-sm">
                Nessun comune trovato nel database scuole per la provincia di Taranto
              </p>
            )}

            {/* Statistiche riepilogative */}
            <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-blue-600">{availableComuni.length}</p>
                <p className="text-xs text-gray-500">Comuni Totali</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">{comuniSummary.filter(c => c.zona).length}</p>
                <p className="text-xs text-gray-500">Comuni Coperti</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-amber-600">{comuniNonAssegnati.length}</p>
                <p className="text-xs text-gray-500">Comuni Scoperti</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-purple-600">{delegati.length}</p>
                <p className="text-xs text-gray-500">Delegati Attivi</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
