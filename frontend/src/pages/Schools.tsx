import { useState, useEffect } from 'react'
import { School, Search, Plus, Trash2, RefreshCw, MapPin, Building2, CheckCircle, XCircle, Loader, Clock, AlertTriangle, Edit3, Save, X } from 'lucide-react'
import toast from 'react-hot-toast'
import { schoolsApi } from '../lib/api'

interface School {
  codice: string
  nome: string
  comune: string
  indirizzo: string
  tipo: string
  distretto: string
  verified?: boolean
  last_verified?: string
  confidence?: number
  changes?: any[]
}

interface PendingSchool {
  codice: string
  nome_proposto: string | null
  comune_proposto: string | null
  indirizzo_proposto: string | null
  tipo_proposto: string | null
  source: string | null
  created_at: string
}

interface SchoolStats {
  total_schools: number
  comuni: Record<string, number>
  distretti: Record<string, number>
  verified_count: number
  last_update: string | null
}

export default function Schools() {
  const [schools, setSchools] = useState<School[]>([])
  const [stats, setStats] = useState<SchoolStats | null>(null)
  const [pendingSchools, setPendingSchools] = useState<PendingSchool[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedComune, setSelectedComune] = useState('')
  const [selectedDistretto, setSelectedDistretto] = useState('')
  const [addingSchool, setAddingSchool] = useState(false)
  const [newSchoolCode, setNewSchoolCode] = useState('')
  const [updatingSchool, setUpdatingSchool] = useState<string | null>(null)
  const [editingPending, setEditingPending] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<{ nome: string; comune: string; indirizzo: string; tipo: string }>({
    nome: '', comune: '', indirizzo: '', tipo: ''
  })
  const [processingPending, setProcessingPending] = useState<string | null>(null)

  useEffect(() => {
    loadSchools()
    loadStats()
    loadPendingSchools()
  }, [])

  const loadSchools = async () => {
    setLoading(true)
    try {
      const response = await schoolsApi.getAll()
      setSchools(response.data.schools)
    } catch (error: any) {
      console.error('Errore caricamento scuole:', error)
      toast.error('Errore nel caricamento delle scuole')
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const response = await schoolsApi.getStats()
      setStats(response.data)
    } catch (error: any) {
      console.error('Errore caricamento statistiche:', error)
    }
  }

  const loadPendingSchools = async () => {
    try {
      const response = await schoolsApi.getPending()
      setPendingSchools(response.data.pending_schools || [])
    } catch (error: any) {
      console.error('Errore caricamento scuole in attesa:', error)
    }
  }

  const handleApprovePending = async (school: PendingSchool) => {
    setProcessingPending(school.codice)
    try {
      const data = editingPending === school.codice ? editForm : {
        nome: school.nome_proposto || '',
        comune: school.comune_proposto || '',
        indirizzo: school.indirizzo_proposto || '',
        tipo: school.tipo_proposto || 'Istituto Comprensivo'
      }

      await schoolsApi.approvePending(school.codice, data)
      toast.success(`Scuola ${school.codice} approvata e aggiunta al database`)
      loadPendingSchools()
      loadSchools()
      loadStats()
      setEditingPending(null)
    } catch (error: any) {
      console.error('Errore approvazione scuola:', error)
      toast.error(error.response?.data?.detail || 'Errore nell\'approvazione')
    } finally {
      setProcessingPending(null)
    }
  }

  const handleRejectPending = async (schoolCode: string) => {
    if (!confirm(`Sei sicuro di voler rifiutare la proposta per ${schoolCode}?`)) {
      return
    }

    setProcessingPending(schoolCode)
    try {
      await schoolsApi.rejectPending(schoolCode)
      toast.success('Proposta rifiutata')
      loadPendingSchools()
    } catch (error: any) {
      console.error('Errore rifiuto proposta:', error)
      toast.error(error.response?.data?.detail || 'Errore nel rifiuto')
    } finally {
      setProcessingPending(null)
    }
  }

  const startEditPending = (school: PendingSchool) => {
    setEditingPending(school.codice)
    setEditForm({
      nome: school.nome_proposto || '',
      comune: school.comune_proposto || '',
      indirizzo: school.indirizzo_proposto || '',
      tipo: school.tipo_proposto || 'Istituto Comprensivo'
    })
  }

  const cancelEditPending = () => {
    setEditingPending(null)
    setEditForm({ nome: '', comune: '', indirizzo: '', tipo: '' })
  }

  const handleAddSchool = async () => {
    if (!newSchoolCode.trim()) {
      toast.error('Inserisci un codice meccanografico')
      return
    }

    setAddingSchool(true)
    try {
      await schoolsApi.add(newSchoolCode.trim().toUpperCase())
      toast.success('Scuola aggiunta con successo')
      setNewSchoolCode('')
      loadSchools()
      loadStats()
    } catch (error: any) {
      console.error('Errore aggiunta scuola:', error)
      toast.error(error.response?.data?.detail || 'Errore nell\'aggiunta della scuola')
    } finally {
      setAddingSchool(false)
    }
  }

  const handleUpdateSchool = async (schoolCode: string) => {
    setUpdatingSchool(schoolCode)
    try {
      const _response = await schoolsApi.update(schoolCode)
      toast.success(`Scuola ${schoolCode} aggiornata`)

      if (_response.data.changes && _response.data.changes.length > 0) {
        toast.success(`Rilevati ${_response.data.changes.length} cambiamenti`)
      }

      loadSchools()
      loadStats()
    } catch (error: any) {
      console.error('Errore aggiornamento scuola:', error)
      toast.error(error.response?.data?.detail || 'Errore nell\'aggiornamento')
    } finally {
      setUpdatingSchool(null)
    }
  }

  const handleDeleteSchool = async (schoolCode: string, schoolName: string) => {
    if (!confirm(`Sei sicuro di voler rimuovere la scuola ${schoolName}?`)) {
      return
    }

    try {
      await schoolsApi.delete(schoolCode)
      toast.success('Scuola rimossa')
      loadSchools()
      loadStats()
    } catch (error: any) {
      console.error('Errore eliminazione scuola:', error)
      toast.error(error.response?.data?.detail || 'Errore nell\'eliminazione')
    }
  }

  const filteredSchools = schools.filter(school => {
    const matchesSearch = !searchQuery ||
      school.nome.toLowerCase().includes(searchQuery.toLowerCase()) ||
      school.comune.toLowerCase().includes(searchQuery.toLowerCase()) ||
      school.codice.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesComune = !selectedComune || school.comune === selectedComune
    const matchesDistretto = !selectedDistretto || school.distretto === selectedDistretto

    return matchesSearch && matchesComune && matchesDistretto
  })

  const uniqueComuni = Array.from(new Set(schools.map(s => s.comune))).sort()
  const uniqueDistretti = Array.from(new Set(schools.map(s => s.distretto))).sort()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Gestione Scuole</h1>
          <p className="mt-1 text-sm text-gray-500">
            Database delle scuole della provincia di Taranto
          </p>
        </div>
        <School className="w-10 h-10 text-primary-600" />
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <School className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Totale Scuole</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_schools}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <MapPin className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Comuni</p>
                <p className="text-2xl font-bold text-gray-900">{Object.keys(stats.comuni).length}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Building2 className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Distretti</p>
                <p className="text-2xl font-bold text-gray-900">{Object.keys(stats.distretti).length}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <CheckCircle className="w-6 h-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Verificate</p>
                <p className="text-2xl font-bold text-gray-900">{stats.verified_count}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pending Schools Section */}
      {pendingSchools.length > 0 && (
        <div className="card border-2 border-orange-300 bg-orange-50">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-orange-100 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-orange-900">
                Scuole in Attesa di Approvazione ({pendingSchools.length})
              </h2>
              <p className="text-sm text-orange-700">
                Queste scuole sono state rilevate automaticamente dalle email ma necessitano di verifica manuale
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {pendingSchools.map(school => (
              <div
                key={school.codice}
                className="p-4 bg-white border border-orange-200 rounded-lg"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-mono font-bold text-gray-900">{school.codice}</span>
                      {school.source && (
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          school.source === 'allegati' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                        }`}>
                          {school.source === 'allegati' ? 'Da allegati' : 'Ricerca online'}
                        </span>
                      )}
                      <span className="text-xs text-gray-500">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {new Date(school.created_at).toLocaleDateString('it-IT')}
                      </span>
                    </div>

                    {editingPending === school.codice ? (
                      // Edit form
                      <div className="space-y-3 mt-3">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div>
                            <label className="label text-xs">Nome Scuola</label>
                            <input
                              type="text"
                              className="input"
                              value={editForm.nome}
                              onChange={(e) => setEditForm({...editForm, nome: e.target.value})}
                              placeholder="Nome istituto"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Comune</label>
                            <input
                              type="text"
                              className="input"
                              value={editForm.comune}
                              onChange={(e) => setEditForm({...editForm, comune: e.target.value.toUpperCase()})}
                              placeholder="COMUNE"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Indirizzo</label>
                            <input
                              type="text"
                              className="input"
                              value={editForm.indirizzo}
                              onChange={(e) => setEditForm({...editForm, indirizzo: e.target.value})}
                              placeholder="Via..."
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Tipo Istituto</label>
                            <select
                              className="input"
                              value={editForm.tipo}
                              onChange={(e) => setEditForm({...editForm, tipo: e.target.value})}
                            >
                              <option value="Istituto Comprensivo">Istituto Comprensivo</option>
                              <option value="Istituto Superiore">Istituto Superiore</option>
                              <option value="Liceo">Liceo</option>
                              <option value="Istituto Tecnico">Istituto Tecnico</option>
                              <option value="Istituto Professionale">Istituto Professionale</option>
                              <option value="Circolo Didattico">Circolo Didattico</option>
                            </select>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleApprovePending(school)}
                            disabled={processingPending === school.codice || !editForm.nome || !editForm.comune}
                            className="btn-primary flex items-center gap-1 text-sm"
                          >
                            {processingPending === school.codice ? (
                              <Loader className="w-4 h-4 animate-spin" />
                            ) : (
                              <Save className="w-4 h-4" />
                            )}
                            Salva e Approva
                          </button>
                          <button
                            onClick={cancelEditPending}
                            className="btn-secondary flex items-center gap-1 text-sm"
                          >
                            <X className="w-4 h-4" />
                            Annulla
                          </button>
                        </div>
                      </div>
                    ) : (
                      // Display proposed info
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-gray-500 text-sm">Nome proposto:</span>
                          <span className={`font-medium ${school.nome_proposto ? 'text-gray-900' : 'text-red-500 italic'}`}>
                            {school.nome_proposto || 'Non trovato'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-gray-500 text-sm">Comune:</span>
                          <span className={`font-medium ${school.comune_proposto && school.comune_proposto !== 'MAIUSCOLO' ? 'text-gray-900' : 'text-red-500 italic'}`}>
                            {school.comune_proposto && school.comune_proposto !== 'MAIUSCOLO' ? school.comune_proposto : 'Non trovato'}
                          </span>
                        </div>
                        {school.indirizzo_proposto && (
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500 text-sm">Indirizzo:</span>
                            <span className="text-gray-900">{school.indirizzo_proposto}</span>
                          </div>
                        )}
                        {school.tipo_proposto && (
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500 text-sm">Tipo:</span>
                            <span className="text-gray-900">{school.tipo_proposto}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {editingPending !== school.codice && (
                    <div className="flex items-center gap-2 ml-4">
                      <button
                        onClick={() => startEditPending(school)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                        title="Modifica e approva"
                      >
                        <Edit3 className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleApprovePending(school)}
                        disabled={processingPending === school.codice || !school.nome_proposto || !school.comune_proposto || school.comune_proposto === 'MAIUSCOLO'}
                        className="p-2 text-green-600 hover:bg-green-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Approva così com'è"
                      >
                        {processingPending === school.codice ? (
                          <Loader className="w-5 h-5 animate-spin" />
                        ) : (
                          <CheckCircle className="w-5 h-5" />
                        )}
                      </button>
                      <button
                        onClick={() => handleRejectPending(school.codice)}
                        disabled={processingPending === school.codice}
                        className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                        title="Rifiuta proposta"
                      >
                        <XCircle className="w-5 h-5" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 p-3 bg-orange-100 rounded-lg">
            <p className="text-sm text-orange-800">
              <strong>Come funziona:</strong> Quando arriva un'email da una scuola non presente nel database,
              il sistema cerca automaticamente le informazioni online o negli allegati.
              Verifica i dati proposti e clicca su <CheckCircle className="w-4 h-4 inline text-green-600" /> per approvare,
              <Edit3 className="w-4 h-4 inline text-blue-600 mx-1" /> per modificare prima di approvare, o
              <XCircle className="w-4 h-4 inline text-red-600 ml-1" /> per rifiutare.
            </p>
          </div>
        </div>
      )}

      {/* Add New School */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Aggiungi Nuova Scuola</h2>
        <div className="flex gap-3">
          <input
            type="text"
            className="input flex-1"
            placeholder="Codice meccanografico (es: TAIC851009)"
            value={newSchoolCode}
            onChange={(e) => setNewSchoolCode(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && handleAddSchool()}
          />
          <button
            onClick={handleAddSchool}
            disabled={addingSchool || !newSchoolCode.trim()}
            className="btn-primary flex items-center gap-2"
          >
            {addingSchool ? (
              <>
                <Loader className="w-4 h-4 animate-spin" />
                Ricerca in corso...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                Aggiungi
              </>
            )}
          </button>
        </div>
        <p className="mt-2 text-sm text-gray-500">
          💡 Il sistema cercherà automaticamente le informazioni della scuola online
        </p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">
              <Search className="w-4 h-4 inline mr-2" />
              Cerca
            </label>
            <input
              type="text"
              className="input"
              placeholder="Nome, comune o codice..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div>
            <label className="label">
              <MapPin className="w-4 h-4 inline mr-2" />
              Comune
            </label>
            <select
              className="input"
              value={selectedComune}
              onChange={(e) => setSelectedComune(e.target.value)}
            >
              <option value="">Tutti i comuni</option>
              {uniqueComuni.map(comune => (
                <option key={comune} value={comune}>{comune}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">
              <Building2 className="w-4 h-4 inline mr-2" />
              Distretto
            </label>
            <select
              className="input"
              value={selectedDistretto}
              onChange={(e) => setSelectedDistretto(e.target.value)}
            >
              <option value="">Tutti i distretti</option>
              {uniqueDistretti.map(distretto => (
                <option key={distretto} value={distretto}>Distretto {distretto}</option>
              ))}
            </select>
          </div>
        </div>

        {(searchQuery || selectedComune || selectedDistretto) && (
          <div className="mt-3 flex items-center justify-between">
            <p className="text-sm text-gray-500">
              {filteredSchools.length} di {schools.length} scuole
            </p>
            <button
              onClick={() => {
                setSearchQuery('')
                setSelectedComune('')
                setSelectedDistretto('')
              }}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              Rimuovi filtri
            </button>
          </div>
        )}
      </div>

      {/* Schools List */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Scuole ({filteredSchools.length})
        </h2>

        <div className="space-y-3">
          {filteredSchools.map(school => (
            <div
              key={school.codice}
              className="p-4 border border-gray-200 rounded-lg hover:border-primary-300 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-900">{school.nome}</h3>
                    {school.verified && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Verificata
                      </span>
                    )}
                  </div>

                  <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                    <div>
                      <span className="text-gray-500">Codice:</span>
                      <span className="ml-2 font-mono text-gray-900">{school.codice}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Comune:</span>
                      <span className="ml-2 text-gray-900">{school.comune}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Distretto:</span>
                      <span className="ml-2 text-gray-900">{school.distretto}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Tipo:</span>
                      <span className="ml-2 text-gray-900">{school.tipo}</span>
                    </div>
                  </div>

                  <p className="mt-1 text-sm text-gray-600">{school.indirizzo}</p>

                  {school.last_verified && (
                    <p className="mt-2 text-xs text-gray-500">
                      Ultima verifica: {new Date(school.last_verified).toLocaleDateString('it-IT')}
                      {school.confidence && ` • Confidenza: ${(school.confidence * 100).toFixed(0)}%`}
                    </p>
                  )}

                  {school.changes && school.changes.length > 0 && (
                    <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
                      <p className="font-medium text-yellow-800">Cambiamenti rilevati:</p>
                      <ul className="mt-1 list-disc list-inside text-yellow-700">
                        {school.changes.map((change, idx) => (
                          <li key={idx}>{JSON.stringify(change)}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => handleUpdateSchool(school.codice)}
                    disabled={updatingSchool === school.codice}
                    className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                    title="Aggiorna informazioni"
                  >
                    {updatingSchool === school.codice ? (
                      <Loader className="w-5 h-5 animate-spin" />
                    ) : (
                      <RefreshCw className="w-5 h-5" />
                    )}
                  </button>
                  <button
                    onClick={() => handleDeleteSchool(school.codice, school.nome)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                    title="Rimuovi scuola"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          ))}

          {filteredSchools.length === 0 && (
            <div className="text-center py-12">
              <School className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">Nessuna scuola trovata</p>
            </div>
          )}
        </div>
      </div>

      {/* Info Box */}
      <div className="card bg-blue-50 border-blue-200">
        <div className="flex gap-3">
          <div className="flex-shrink-0">
            <div className="p-2 bg-blue-100 rounded-lg">
              <School className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-blue-900 mb-2">Come funziona l'aggiornamento automatico</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Quando arriva un'email da una scuola non presente nel database, viene <strong>automaticamente aggiunta</strong></li>
              <li>• Il sistema usa l'<strong>LLM per cercare informazioni online</strong> sulla scuola</li>
              <li>• Puoi <strong>aggiornare manualmente</strong> una scuola per verificare se ci sono cambiamenti</li>
              <li>• Le scuole soppresse o accorpate possono essere <strong>rimosse dal database</strong></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
