import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Database,
  FileText,
  Trash2,
  Edit2,
  Save,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Filter,
  Users,
  Tag,
  Building2
} from 'lucide-react'
import { ragApi } from '../lib/api'

interface DocumentMetadata {
  email_id?: string
  categoria?: string
  sottocategoria?: string
  mittente?: string
  data_ricezione?: string
  oggetto?: string
  argomento?: string
  scuola?: string
  filename?: string
}

interface RAGDocument {
  id: string
  summary: string
  full_text: string
  metadata: DocumentMetadata
  text_length: number
}

interface DocumentsResponse {
  documents: RAGDocument[]
  total: number
  limit: number
  offset: number
}

// Classificazione mittenti
const SENDER_CLASSIFICATIONS: Record<string, { label: string; color: string; icon: string }> = {
  'USR/USP': { label: 'Ufficio Scolastico', color: 'blue', icon: '🏛️' },
  'Scuola': { label: 'Istituti Scolastici', color: 'green', icon: '🏫' },
  'SNALS': { label: 'Sindacato SNALS', color: 'purple', icon: '👥' },
  'Altro': { label: 'Altri Mittenti', color: 'gray', icon: '📧' }
}

function classifySender(mittente: string): string {
  if (!mittente) return 'Altro'
  const m = mittente.toLowerCase()

  if (m.includes('usp.') || m.includes('usr.') || m.includes('ambito') || m.includes('istruzione.it')) {
    if (m.match(/^ta[a-z]{2}\d+@/)) return 'Scuola' // Codice meccanografico
    return 'USR/USP'
  }
  if (m.match(/^ta[a-z]{2}\d+@/) || m.includes('scuola') || m.includes('istituto') || m.includes('liceo') || m.includes('comprensivo')) {
    return 'Scuola'
  }
  if (m.includes('snals') || m.includes('sindacato')) {
    return 'SNALS'
  }
  return 'Altro'
}

export default function RAGDocuments() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(0)
  const [limit] = useState(100) // Più documenti per raggruppare meglio
  const [editingDoc, setEditingDoc] = useState<string | null>(null)
  const [editedMetadata, setEditedMetadata] = useState<DocumentMetadata>({})
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set())
  const [viewMode, setViewMode] = useState<'grouped' | 'list'>('grouped')

  // Filtri
  const [filters, setFilters] = useState({
    categoria: '',
    sottocategoria: '',
    mittente: ''
  })
  const [showFilters, setShowFilters] = useState(false)

  // Query documenti
  const { data, isLoading } = useQuery<DocumentsResponse>({
    queryKey: ['rag-documents', page, limit, filters],
    queryFn: async () => {
      const response = await ragApi.getDocuments({
        limit,
        offset: page * limit,
        filter_categoria: filters.categoria || undefined,
        filter_sottocategoria: filters.sottocategoria || undefined,
        filter_mittente: filters.mittente || undefined
      })
      return response.data
    }
  })

  // Raggruppa documenti per mittente/classificazione
  const groupedDocuments = useMemo(() => {
    if (!data?.documents) return {}

    const groups: Record<string, { classification: string; documents: RAGDocument[] }> = {}

    data.documents.forEach(doc => {
      const mittente = doc.metadata.mittente || 'Sconosciuto'
      const classification = classifySender(mittente)

      if (!groups[mittente]) {
        groups[mittente] = { classification, documents: [] }
      }
      groups[mittente].documents.push(doc)
    })

    // Ordina per classificazione e poi per mittente
    return Object.fromEntries(
      Object.entries(groups).sort((a, b) => {
        const classOrder = ['USR/USP', 'Scuola', 'SNALS', 'Altro']
        const orderA = classOrder.indexOf(a[1].classification)
        const orderB = classOrder.indexOf(b[1].classification)
        if (orderA !== orderB) return orderA - orderB
        return a[0].localeCompare(b[0])
      })
    )
  }, [data?.documents])

  // Statistiche per classificazione
  const classificationStats = useMemo(() => {
    const stats: Record<string, number> = { 'USR/USP': 0, 'Scuola': 0, 'SNALS': 0, 'Altro': 0 }
    Object.values(groupedDocuments).forEach(group => {
      stats[group.classification] += group.documents.length
    })
    return stats
  }, [groupedDocuments])

  // Mutations
  const updateMetadataMutation = useMutation({
    mutationFn: async ({ docId, metadata }: { docId: string; metadata: DocumentMetadata }) => {
      const response = await ragApi.updateMetadata(docId, metadata)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rag-documents'] })
      setEditingDoc(null)
    }
  })

  const deleteDocMutation = useMutation({
    mutationFn: async (docId: string) => {
      const response = await ragApi.deleteDocument(docId)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rag-documents'] })
    }
  })

  const totalPages = data ? Math.ceil(data.total / limit) : 0

  const toggleGroup = (mittente: string) => {
    const newExpanded = new Set(expandedGroups)
    if (newExpanded.has(mittente)) {
      newExpanded.delete(mittente)
    } else {
      newExpanded.add(mittente)
    }
    setExpandedGroups(newExpanded)
  }

  const toggleDoc = (docId: string) => {
    const newExpanded = new Set(expandedDocs)
    if (newExpanded.has(docId)) {
      newExpanded.delete(docId)
    } else {
      newExpanded.add(docId)
    }
    setExpandedDocs(newExpanded)
  }

  const handleEdit = (doc: RAGDocument) => {
    setEditingDoc(doc.id)
    setEditedMetadata(doc.metadata)
  }

  const handleSave = (docId: string) => {
    updateMetadataMutation.mutate({ docId, metadata: editedMetadata })
  }

  const handleDelete = (docId: string) => {
    if (confirm('Sei sicuro di voler eliminare questo documento?')) {
      deleteDocMutation.mutate(docId)
    }
  }

  const MetadataEditor = ({ metadata, onChange }: { metadata: DocumentMetadata; onChange: (m: DocumentMetadata) => void }) => (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2 p-3 bg-yellow-50 rounded-lg">
      <div>
        <label className="text-xs font-medium text-gray-700">Categoria</label>
        <input
          type="text"
          value={metadata.categoria || ''}
          onChange={(e) => onChange({ ...metadata, categoria: e.target.value })}
          className="w-full px-2 py-1 text-sm border rounded"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-700">Sottocategoria</label>
        <input
          type="text"
          value={metadata.sottocategoria || ''}
          onChange={(e) => onChange({ ...metadata, sottocategoria: e.target.value })}
          className="w-full px-2 py-1 text-sm border rounded"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-700">Argomento</label>
        <input
          type="text"
          value={metadata.argomento || ''}
          onChange={(e) => onChange({ ...metadata, argomento: e.target.value })}
          className="w-full px-2 py-1 text-sm border rounded"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-700">Scuola</label>
        <input
          type="text"
          value={metadata.scuola || ''}
          onChange={(e) => onChange({ ...metadata, scuola: e.target.value })}
          className="w-full px-2 py-1 text-sm border rounded"
        />
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Database className="w-6 h-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Documenti RAG</h1>
            <p className="text-sm text-gray-600">
              {data?.total || 0} documenti indicizzati
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setViewMode(viewMode === 'grouped' ? 'list' : 'grouped')}
            className="btn-secondary flex items-center gap-2"
          >
            <Users className="w-4 h-4" />
            {viewMode === 'grouped' ? 'Vista Lista' : 'Raggruppa'}
          </button>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn-secondary flex items-center gap-2"
          >
            <Filter className="w-4 h-4" />
            Filtri
          </button>
        </div>
      </div>

      {/* Statistiche Classificazioni */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Object.entries(SENDER_CLASSIFICATIONS).map(([key, { label, color, icon }]) => (
          <div
            key={key}
            className={`p-3 rounded-lg border bg-${color}-50 border-${color}-200 cursor-pointer hover:shadow-md transition-shadow`}
            onClick={() => {
              // Espandi tutti i gruppi di questa classificazione
              const newExpanded = new Set(expandedGroups)
              Object.entries(groupedDocuments).forEach(([mittente, group]) => {
                if (group.classification === key) {
                  newExpanded.add(mittente)
                }
              })
              setExpandedGroups(newExpanded)
            }}
          >
            <div className="flex items-center gap-2">
              <span className="text-xl">{icon}</span>
              <div>
                <div className="text-lg font-bold text-gray-900">{classificationStats[key] || 0}</div>
                <div className="text-xs text-gray-600">{label}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Filtri */}
      {showFilters && (
        <div className="card space-y-3">
          <h3 className="font-medium text-gray-900">Filtra documenti</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-sm font-medium text-gray-700">Categoria</label>
              <input
                type="text"
                value={filters.categoria}
                onChange={(e) => setFilters({ ...filters, categoria: e.target.value })}
                placeholder="es. comunicazione_ust_usr"
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Sottocategoria</label>
              <input
                type="text"
                value={filters.sottocategoria}
                onChange={(e) => setFilters({ ...filters, sottocategoria: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Mittente</label>
              <input
                type="text"
                value={filters.mittente}
                onChange={(e) => setFilters({ ...filters, mittente: e.target.value })}
                placeholder="es. info@snals.it"
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setPage(0)} className="btn-primary text-sm">
              Applica filtri
            </button>
            <button
              onClick={() => {
                setFilters({ categoria: '', sottocategoria: '', mittente: '' })
                setPage(0)
              }}
              className="btn-secondary text-sm"
            >
              Reset
            </button>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="card">
          <p className="text-center text-gray-500">Caricamento documenti...</p>
        </div>
      )}

      {/* Lista documenti raggruppata */}
      {data && data.documents.length === 0 && (
        <div className="card text-center py-8">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600">Nessun documento trovato</p>
        </div>
      )}

      {data && data.documents.length > 0 && viewMode === 'grouped' && (
        <div className="space-y-3">
          {Object.entries(groupedDocuments).map(([mittente, { classification, documents }]) => {
            const classInfo = SENDER_CLASSIFICATIONS[classification]
            const isExpanded = expandedGroups.has(mittente)

            return (
              <div key={mittente} className="card">
                {/* Header gruppo */}
                <div
                  className="flex items-center justify-between cursor-pointer p-2 -m-2 rounded-lg hover:bg-gray-50"
                  onClick={() => toggleGroup(mittente)}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{classInfo.icon}</span>
                    <div>
                      <div className="font-medium text-gray-900">{mittente}</div>
                      <div className="text-xs text-gray-500">
                        {documents.length} documento{documents.length !== 1 ? 'i' : ''} • {classInfo.label}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs rounded-full bg-${classInfo.color}-100 text-${classInfo.color}-700`}>
                      {classification}
                    </span>
                    {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </div>
                </div>

                {/* Documenti del gruppo */}
                {isExpanded && (
                  <div className="mt-4 space-y-3 border-t pt-4">
                    {documents.map(doc => (
                      <div key={doc.id} className="border rounded-lg p-3 bg-gray-50">
                        {/* Header documento */}
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2">
                              <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                              <span className="text-sm font-medium text-gray-700 truncate">
                                {doc.metadata.oggetto || doc.metadata.filename || 'Documento'}
                              </span>
                              <span className="text-xs text-gray-400">
                                ({(doc.text_length / 1000).toFixed(1)}k)
                              </span>
                            </div>

                            {/* Tags */}
                            <div className="flex flex-wrap gap-1 mb-2">
                              {doc.metadata.categoria && (
                                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                                  {doc.metadata.categoria}
                                </span>
                              )}
                              {doc.metadata.sottocategoria && (
                                <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">
                                  {doc.metadata.sottocategoria}
                                </span>
                              )}
                              {doc.metadata.argomento && (
                                <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs">
                                  <Tag className="w-3 h-3 inline mr-1" />
                                  {doc.metadata.argomento}
                                </span>
                              )}
                              {doc.metadata.scuola && (
                                <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                                  <Building2 className="w-3 h-3 inline mr-1" />
                                  {doc.metadata.scuola}
                                </span>
                              )}
                            </div>

                            {/* Testo documento */}
                            <div
                              className="cursor-pointer"
                              onClick={() => toggleDoc(doc.id)}
                            >
                              {expandedDocs.has(doc.id) ? (
                                <div className="bg-white rounded-lg p-3 max-h-96 overflow-y-auto border">
                                  <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">
                                    {doc.full_text}
                                  </pre>
                                </div>
                              ) : (
                                <p className="text-sm text-gray-600 line-clamp-2">
                                  {doc.summary}
                                </p>
                              )}
                              <button className="text-xs text-primary-600 mt-1">
                                {expandedDocs.has(doc.id) ? 'Nascondi' : 'Espandi'}
                              </button>
                            </div>

                            {/* Editor metadati */}
                            {editingDoc === doc.id && (
                              <MetadataEditor
                                metadata={editedMetadata}
                                onChange={setEditedMetadata}
                              />
                            )}
                          </div>

                          {/* Azioni */}
                          <div className="flex gap-1 flex-shrink-0">
                            {editingDoc === doc.id ? (
                              <>
                                <button
                                  onClick={() => handleSave(doc.id)}
                                  disabled={updateMetadataMutation.isPending}
                                  className="p-1.5 text-green-600 hover:bg-green-50 rounded"
                                  title="Salva"
                                >
                                  <Save className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => setEditingDoc(null)}
                                  className="p-1.5 text-gray-600 hover:bg-gray-100 rounded"
                                  title="Annulla"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={() => handleEdit(doc)}
                                  className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                                  title="Modifica"
                                >
                                  <Edit2 className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleDelete(doc.id)}
                                  disabled={deleteDocMutation.isPending}
                                  className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                                  title="Elimina"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Vista lista semplice */}
      {data && data.documents.length > 0 && viewMode === 'list' && (
        <div className="space-y-3">
          {data.documents.map((doc) => (
            <div key={doc.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium">{doc.metadata.oggetto || doc.metadata.filename}</span>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-3 max-h-48 overflow-y-auto">
                    <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">
                      {doc.full_text}
                    </pre>
                  </div>

                  <div className="mt-2 flex flex-wrap gap-1">
                    {doc.metadata.mittente && (
                      <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                        📧 {doc.metadata.mittente}
                      </span>
                    )}
                    {doc.metadata.categoria && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                        {doc.metadata.categoria}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex gap-1">
                  <button
                    onClick={() => handleEdit(doc)}
                    className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Paginazione */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Pagina {page + 1} di {totalPages}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="btn-secondary flex items-center gap-1 disabled:opacity-50"
            >
              <ChevronLeft className="w-4 h-4" />
              Precedente
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="btn-secondary flex items-center gap-1 disabled:opacity-50"
            >
              Successiva
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
