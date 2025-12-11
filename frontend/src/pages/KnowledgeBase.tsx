import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  Upload,
  FileText,
  Trash2,
  Filter,
  Database,
  Tag,
  Calendar,
  Building,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Download,
  RefreshCw
} from 'lucide-react'
import { knowledgeApi } from '../lib/api'
import type { KnowledgeDocument, KnowledgeStats, TipoDocumento } from '../types'

const TIPO_DOCUMENTO_LABELS: Record<string, string> = {
  normativa: 'Normativa',
  circolare: 'Circolare',
  faq: 'FAQ',
  modello: 'Modello',
  contratto: 'Contratto',
  prassi: 'Prassi',
  guida: 'Guida',
  interpello_tipo: 'Interpello Tipo',
  altro: 'Altro',
}

interface DocumentsResponse {
  documenti: KnowledgeDocument[]
  total: number
  skip: number
  limit: number
}

export default function KnowledgeBase() {
  const queryClient = useQueryClient()
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [expandedDoc, setExpandedDoc] = useState<number | null>(null)

  // Filtri
  const [filters, setFilters] = useState({
    tipo_documento: '',
    categoria_email: '',
    tags: '',
    ente_emittente: '',
    skip: 0,
    limit: 50,
  })

  // Query documenti
  const { data, isLoading } = useQuery<DocumentsResponse>({
    queryKey: ['knowledge-documents', filters],
    queryFn: async () => {
      const response = await knowledgeApi.getAll(filters)
      return response.data
    },
  })

  // Query stats
  const { data: stats } = useQuery<KnowledgeStats>({
    queryKey: ['knowledge-stats'],
    queryFn: async () => {
      const response = await knowledgeApi.getStats()
      return response.data
    },
  })

  // Mutation delete
  const deleteMutation = useMutation({
    mutationFn: (id: number) => knowledgeApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-documents'] })
      queryClient.invalidateQueries({ queryKey: ['knowledge-stats'] })
    },
  })

  // Mutation reindex
  const reindexMutation = useMutation({
    mutationFn: (id: number) => knowledgeApi.index(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-documents'] })
    },
  })

  const handleDelete = (id: number, titolo: string) => {
    if (confirm(`Sei sicuro di voler eliminare "${titolo}"?`)) {
      deleteMutation.mutate(id)
    }
  }

  const handleReindex = (id: number) => {
    if (confirm('Vuoi reindicizzare questo documento nel RAG?')) {
      reindexMutation.mutate(id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <BookOpen className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Knowledge Base</h1>
            <p className="text-sm text-gray-600">
              {stats?.total_documenti || 0} documenti • {stats?.indicizzati_in_rag || 0} indicizzati
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn-secondary flex items-center gap-2"
          >
            <Filter className="w-4 h-4" />
            Filtri
          </button>
          <button
            onClick={() => setShowUploadModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Carica Documento
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {Object.entries(stats.by_tipo).map(([tipo, count]) => (
            count > 0 && (
              <div key={tipo} className="card">
                <div className="text-xs text-gray-600">{TIPO_DOCUMENTO_LABELS[tipo]}</div>
                <div className="text-2xl font-bold text-gray-900">{count}</div>
              </div>
            )
          ))}
        </div>
      )}

      {/* Filtri */}
      {showFilters && (
        <div className="card space-y-3">
          <h3 className="font-medium text-gray-900">Filtra documenti</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="text-sm font-medium text-gray-700">Tipo Documento</label>
              <select
                value={filters.tipo_documento}
                onChange={(e) => setFilters({ ...filters, tipo_documento: e.target.value, skip: 0 })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="">Tutti</option>
                {Object.entries(TIPO_DOCUMENTO_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Categoria Email</label>
              <input
                type="text"
                value={filters.categoria_email}
                onChange={(e) => setFilters({ ...filters, categoria_email: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="es. comunicazione_ust_usr"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Tags</label>
              <input
                type="text"
                value={filters.tags}
                onChange={(e) => setFilters({ ...filters, tags: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="es. ccnl,permessi"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Ente Emittente</label>
              <input
                type="text"
                value={filters.ente_emittente}
                onChange={(e) => setFilters({ ...filters, ente_emittente: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="es. MIUR"
              />
            </div>
          </div>
          <button
            onClick={() => setFilters({ tipo_documento: '', categoria_email: '', tags: '', ente_emittente: '', skip: 0, limit: 50 })}
            className="btn-secondary text-sm"
          >
            Reset Filtri
          </button>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="card">
          <p className="text-center text-gray-500">Caricamento documenti...</p>
        </div>
      )}

      {/* Lista documenti */}
      {data && data.documenti.length === 0 && (
        <div className="card text-center py-12">
          <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nessun documento</h3>
          <p className="text-gray-600 mb-4">Carica il primo documento nella knowledge base</p>
          <button
            onClick={() => setShowUploadModal(true)}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Carica Documento
          </button>
        </div>
      )}

      {data && data.documenti.length > 0 && (
        <div className="space-y-3">
          {data.documenti.map((doc) => (
            <div key={doc.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  {/* Header */}
                  <div className="flex items-start gap-3 mb-3">
                    <FileText className="w-5 h-5 text-gray-400 flex-shrink-0 mt-1" />
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-gray-900 mb-1">
                        {doc.titolo}
                      </h3>
                      {doc.descrizione && (
                        <p className="text-sm text-gray-600 mb-2">{doc.descrizione}</p>
                      )}
                      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded font-medium">
                          {TIPO_DOCUMENTO_LABELS[doc.tipo_documento]}
                        </span>
                        <span>{doc.file_name}</span>
                        <span>•</span>
                        <span>{doc.file_size_mb.toFixed(2)} MB</span>
                        <span>•</span>
                        <span>{(doc.testo_length / 1000).toFixed(1)}k caratteri</span>
                        {doc.indexed_in_rag && (
                          <>
                            <span>•</span>
                            <span className="flex items-center gap-1 text-green-600">
                              <Database className="w-3 h-3" />
                              Indicizzato
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Tags e metadati */}
                  <div className="flex flex-wrap gap-2 mb-3">
                    {doc.tags.map((tag) => (
                      <span key={tag} className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full text-xs flex items-center gap-1">
                        <Tag className="w-3 h-3" />
                        {tag}
                      </span>
                    ))}
                    {doc.ente_emittente && (
                      <span className="px-2 py-1 bg-green-50 text-green-700 rounded text-xs flex items-center gap-1">
                        <Building className="w-3 h-3" />
                        {doc.ente_emittente}
                      </span>
                    )}
                    {doc.data_emissione && (
                      <span className="px-2 py-1 bg-orange-50 text-orange-700 rounded text-xs flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(doc.data_emissione).toLocaleDateString('it-IT')}
                      </span>
                    )}
                    {doc.anno_riferimento && (
                      <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                        Anno: {doc.anno_riferimento}
                      </span>
                    )}
                    {doc.numero_protocollo && (
                      <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                        Prot. {doc.numero_protocollo}
                      </span>
                    )}
                  </div>

                  {/* Dettagli espansi */}
                  {expandedDoc === doc.id && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-2 text-sm">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <span className="font-medium text-gray-700">Caricato da:</span>
                          <span className="ml-2 text-gray-600">{doc.caricato_da}</span>
                        </div>
                        <div>
                          <span className="font-medium text-gray-700">Data caricamento:</span>
                          <span className="ml-2 text-gray-600">
                            {new Date(doc.created_at).toLocaleString('it-IT')}
                          </span>
                        </div>
                        {doc.rag_indexed_at && (
                          <div>
                            <span className="font-medium text-gray-700">Indicizzato il:</span>
                            <span className="ml-2 text-gray-600">
                              {new Date(doc.rag_indexed_at).toLocaleString('it-IT')}
                            </span>
                          </div>
                        )}
                        {doc.rag_document_ids && doc.rag_document_ids.length > 0 && (
                          <div>
                            <span className="font-medium text-gray-700">Chunks RAG:</span>
                            <span className="ml-2 text-gray-600">{doc.rag_document_ids.length}</span>
                          </div>
                        )}
                      </div>
                      {doc.note_interne && (
                        <div>
                          <span className="font-medium text-gray-700">Note:</span>
                          <p className="mt-1 text-gray-600">{doc.note_interne}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Toggle dettagli */}
                  <button
                    onClick={() => setExpandedDoc(expandedDoc === doc.id ? null : doc.id)}
                    className="text-xs text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1 mt-2"
                  >
                    {expandedDoc === doc.id ? (
                      <>
                        <ChevronUp className="w-3 h-3" />
                        Nascondi dettagli
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-3 h-3" />
                        Mostra dettagli
                      </>
                    )}
                  </button>
                </div>

                {/* Azioni */}
                <div className="flex flex-col gap-2 flex-shrink-0">
                  {!doc.indexed_in_rag && (
                    <button
                      onClick={() => handleReindex(doc.id)}
                      disabled={reindexMutation.isPending}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                      title="Indicizza nel RAG"
                    >
                      <Database className="w-4 h-4" />
                    </button>
                  )}
                  {doc.indexed_in_rag && (
                    <button
                      onClick={() => handleReindex(doc.id)}
                      disabled={reindexMutation.isPending}
                      className="p-2 text-green-600 hover:bg-green-50 rounded transition-colors"
                      title="Reindicizza"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(doc.id, doc.titolo)}
                    disabled={deleteMutation.isPending}
                    className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                    title="Elimina"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Upload */}
      {showUploadModal && (
        <UploadModal
          onClose={() => setShowUploadModal(false)}
          onSuccess={() => {
            setShowUploadModal(false)
            queryClient.invalidateQueries({ queryKey: ['knowledge-documents'] })
            queryClient.invalidateQueries({ queryKey: ['knowledge-stats'] })
          }}
        />
      )}
    </div>
  )
}

interface UploadModalProps {
  onClose: () => void
  onSuccess: () => void
}

function UploadModal({ onClose, onSuccess }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [formData, setFormData] = useState({
    titolo: '',
    descrizione: '',
    tipo_documento: 'altro' as TipoDocumento,
    categoria_email: '',
    tags: '',
    ente_emittente: '',
    data_emissione: '',
    numero_protocollo: '',
    anno_riferimento: '',
    note_interne: '',
    indicizza_subito: true,
  })

  const uploadMutation = useMutation({
    mutationFn: async (data: FormData) => {
      const response = await knowledgeApi.upload(data)
      return response.data
    },
    onSuccess: () => {
      onSuccess()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      alert('Seleziona un file')
      return
    }

    const data = new FormData()
    data.append('file', file)
    data.append('titolo', formData.titolo)
    if (formData.descrizione) data.append('descrizione', formData.descrizione)
    data.append('tipo_documento', formData.tipo_documento)
    if (formData.categoria_email) data.append('categoria_email', formData.categoria_email)
    if (formData.tags) data.append('tags', formData.tags)
    if (formData.ente_emittente) data.append('ente_emittente', formData.ente_emittente)
    if (formData.data_emissione) data.append('data_emissione', formData.data_emissione)
    if (formData.numero_protocollo) data.append('numero_protocollo', formData.numero_protocollo)
    if (formData.anno_riferimento) data.append('anno_riferimento', formData.anno_riferimento)
    if (formData.note_interne) data.append('note_interne', formData.note_interne)
    data.append('indicizza_subito', formData.indicizza_subito.toString())

    uploadMutation.mutate(data)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Carica Documento</h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* File */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              File * (PDF, DOCX, TXT, etc.)
            </label>
            <input
              type="file"
              required
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full px-3 py-2 border rounded-lg"
              accept=".pdf,.doc,.docx,.txt,.eml"
            />
            {file && (
              <p className="mt-1 text-xs text-gray-500">
                File selezionato: {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          {/* Titolo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Titolo *</label>
            <input
              type="text"
              required
              value={formData.titolo}
              onChange={(e) => setFormData({ ...formData, titolo: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="es. CCNL Scuola 2019-2021"
            />
          </div>

          {/* Descrizione */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Descrizione</label>
            <textarea
              value={formData.descrizione}
              onChange={(e) => setFormData({ ...formData, descrizione: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              rows={3}
              placeholder="Breve descrizione del documento..."
            />
          </div>

          {/* Tipo Documento */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Tipo Documento *</label>
            <select
              required
              value={formData.tipo_documento}
              onChange={(e) => setFormData({ ...formData, tipo_documento: e.target.value as TipoDocumento })}
              className="w-full px-3 py-2 border rounded-lg"
            >
              {Object.entries(TIPO_DOCUMENTO_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

          {/* Grid 2 colonne */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Categoria Email</label>
              <input
                type="text"
                value={formData.categoria_email}
                onChange={(e) => setFormData({ ...formData, categoria_email: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="es. comunicazione_ust_usr"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Ente Emittente</label>
              <input
                type="text"
                value={formData.ente_emittente}
                onChange={(e) => setFormData({ ...formData, ente_emittente: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="es. MIUR, USR Puglia"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Data Emissione</label>
              <input
                type="date"
                value={formData.data_emissione}
                onChange={(e) => setFormData({ ...formData, data_emissione: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Anno Riferimento</label>
              <input
                type="text"
                value={formData.anno_riferimento}
                onChange={(e) => setFormData({ ...formData, anno_riferimento: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="es. 2019-2021, 2024/2025"
              />
            </div>
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tags (separati da virgola)
            </label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="es. ccnl, permessi, ferie, congedi"
            />
          </div>

          {/* Numero Protocollo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Numero Protocollo</label>
            <input
              type="text"
              value={formData.numero_protocollo}
              onChange={(e) => setFormData({ ...formData, numero_protocollo: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="es. PROT123456"
            />
          </div>

          {/* Note Interne */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Note Interne</label>
            <textarea
              value={formData.note_interne}
              onChange={(e) => setFormData({ ...formData, note_interne: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              rows={2}
              placeholder="Note ad uso interno..."
            />
          </div>

          {/* Indicizza subito */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="indicizza_subito"
              checked={formData.indicizza_subito}
              onChange={(e) => setFormData({ ...formData, indicizza_subito: e.target.checked })}
              className="w-4 h-4 text-primary-600 rounded"
            />
            <label htmlFor="indicizza_subito" className="text-sm text-gray-700">
              Indicizza subito nel RAG (raccomandato)
            </label>
          </div>

          {/* Errore */}
          {uploadMutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              Errore durante l'upload. Riprova.
            </div>
          )}

          {/* Bottoni */}
          <div className="flex gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
              disabled={uploadMutation.isPending}
            >
              Annulla
            </button>
            <button
              type="submit"
              className="btn-primary flex-1 flex items-center justify-center gap-2"
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Caricamento...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Carica
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
