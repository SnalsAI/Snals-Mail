import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles, Upload, Trash2, RefreshCw, Search, Filter } from 'lucide-react'
import { documentService, type DocumentFilters } from '@/services/documentService'
import { TipoDocumento, StatoDocumento } from '@/types'
import PageHeader from '@/components/PageHeader'
import LoadingSpinner from '@/components/LoadingSpinner'
import EmptyState from '@/components/EmptyState'
import Badge from '@/components/Badge'
import { formatDateTime, getTipoDocumentoLabel, getStatoDocumentoLabel } from '@/lib/utils'
import toast from 'react-hot-toast'

export default function Documents() {
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState<DocumentFilters>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadTipo, setUploadTipo] = useState<TipoDocumento>(TipoDocumento.FAQ)
  const [embedImmediately, setEmbedImmediately] = useState(true)

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', filters],
    queryFn: () => documentService.getDocuments(filters),
  })

  const { data: ragStats } = useQuery({
    queryKey: ['rag-stats'],
    queryFn: documentService.getRAGStats,
  })

  const uploadMutation = useMutation({
    mutationFn: (data: { file: File; tipo: TipoDocumento; metadata: Record<string, any>; embedImmediately: boolean }) =>
      documentService.uploadDocument(data.file, data.tipo, data.metadata, data.embedImmediately),
    onSuccess: () => {
      toast.success('Documento caricato con successo')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['rag-stats'] })
      setShowUploadModal(false)
      setUploadFile(null)
    },
    onError: () => {
      toast.error('Errore durante il caricamento')
    },
  })

  const embedMutation = useMutation({
    mutationFn: (id: number) => documentService.embedDocument(id),
    onSuccess: () => {
      toast.success('Documento embeddato con successo')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['rag-stats'] })
    },
    onError: () => {
      toast.error('Errore durante l\'embedding')
    },
  })

  const toggleEmbeddingMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      documentService.updateDocument(id, { embedding_abilitato: enabled }),
    onSuccess: () => {
      toast.success('Impostazione aggiornata')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })

  const deleteDocumentMutation = useMutation({
    mutationFn: (id: number) => documentService.deleteDocument(id),
    onSuccess: () => {
      toast.success('Documento eliminato')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['rag-stats'] })
    },
  })

  const handleUpload = () => {
    if (!uploadFile) {
      toast.error('Seleziona un file')
      return
    }

    uploadMutation.mutate({
      file: uploadFile,
      tipo: uploadTipo,
      metadata: { uploaded_from: 'frontend' },
      embedImmediately,
    })
  }

  const filteredDocuments = documents?.filter((doc) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      doc.titolo.toLowerCase().includes(query) ||
      doc.descrizione?.toLowerCase().includes(query)
    )
  })

  const getStatoBadgeVariant = (stato: StatoDocumento) => {
    switch (stato) {
      case StatoDocumento.EMBEDDATO:
        return 'success'
      case StatoDocumento.PROCESSATO:
        return 'info'
      case StatoDocumento.ERRORE:
        return 'danger'
      default:
        return 'default'
    }
  }

  return (
    <div className="p-8">
      <PageHeader
        title="Documenti RAG"
        description="Gestisci i documenti per il sistema RAG (Retrieval Augmented Generation)"
        actions={
          <button
            onClick={() => setShowUploadModal(true)}
            className="btn btn-primary"
          >
            <Upload className="w-4 h-4 mr-2" />
            Carica Documento
          </button>
        }
      />

      {/* Stats Cards */}
      {ragStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <div className="card">
            <p className="text-sm text-gray-600 mb-1">Documenti Totali</p>
            <p className="text-3xl font-bold text-primary-600">{ragStats.total_documents || 0}</p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-600 mb-1">Embeddati</p>
            <p className="text-3xl font-bold text-green-600">{ragStats.embedded_documents || 0}</p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-600 mb-1">Chunks Totali</p>
            <p className="text-3xl font-bold text-blue-600">{ragStats.total_chunks || 0}</p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-600 mb-1">Query RAG</p>
            <p className="text-3xl font-bold text-purple-600">{ragStats.total_queries || 0}</p>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="card mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Cerca documenti..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn btn-secondary"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filtri
          </button>
        </div>

        {showFilters && (
          <div className="mt-4 pt-4 border-t grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label">Tipo Documento</label>
              <select
                value={filters.tipo || ''}
                onChange={(e) => setFilters({ ...filters, tipo: e.target.value as TipoDocumento })}
                className="input"
              >
                <option value="">Tutti</option>
                {Object.values(TipoDocumento).map((tipo) => (
                  <option key={tipo} value={tipo}>
                    {getTipoDocumentoLabel(tipo)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Stato</label>
              <select
                value={filters.stato || ''}
                onChange={(e) => setFilters({ ...filters, stato: e.target.value as StatoDocumento })}
                className="input"
              >
                <option value="">Tutti</option>
                {Object.values(StatoDocumento).map((stato) => (
                  <option key={stato} value={stato}>
                    {getStatoDocumentoLabel(stato)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Embedding</label>
              <select
                value={filters.embedding_abilitato?.toString() || ''}
                onChange={(e) => setFilters({
                  ...filters,
                  embedding_abilitato: e.target.value === '' ? undefined : e.target.value === 'true'
                })}
                className="input"
              >
                <option value="">Tutti</option>
                <option value="true">Abilitato</option>
                <option value="false">Disabilitato</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Documents List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : filteredDocuments && filteredDocuments.length > 0 ? (
        <div className="space-y-4">
          {filteredDocuments.map((doc) => (
            <div key={doc.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">{doc.titolo}</h3>
                    <Badge variant="info">{getTipoDocumentoLabel(doc.tipo)}</Badge>
                    <Badge variant={getStatoBadgeVariant(doc.stato)}>
                      {getStatoDocumentoLabel(doc.stato)}
                    </Badge>
                    {doc.embedding_abilitato && (
                      <Badge variant="success">
                        <Sparkles className="w-3 h-3 mr-1 inline" />
                        Embedding ON
                      </Badge>
                    )}
                  </div>

                  {doc.descrizione && (
                    <p className="text-sm text-gray-600 mb-3">{doc.descrizione}</p>
                  )}

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-gray-700">Priorità:</span>
                      <span className="ml-2 text-gray-900">{doc.priorita}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">Versione:</span>
                      <span className="ml-2 text-gray-900">{doc.versione}</span>
                    </div>
                    {doc.num_chunks && (
                      <div>
                        <span className="font-medium text-gray-700">Chunks:</span>
                        <span className="ml-2 text-gray-900">{doc.num_chunks}</span>
                      </div>
                    )}
                    <div>
                      <span className="font-medium text-gray-700">Attivo:</span>
                      <span className="ml-2 text-gray-900">{doc.attivo ? 'Sì' : 'No'}</span>
                    </div>
                  </div>

                  <p className="text-xs text-gray-500 mt-3">
                    Creato: {formatDateTime(doc.created_at)}
                  </p>
                </div>

                <div className="flex flex-col items-end gap-2 ml-4">
                  {doc.stato !== StatoDocumento.EMBEDDATO && doc.stato !== StatoDocumento.ERRORE && (
                    <button
                      onClick={() => embedMutation.mutate(doc.id)}
                      disabled={embedMutation.isPending}
                      className="btn btn-primary btn-sm"
                    >
                      <Sparkles className="w-4 h-4 mr-2" />
                      Embedda
                    </button>
                  )}
                  <button
                    onClick={() => toggleEmbeddingMutation.mutate({
                      id: doc.id,
                      enabled: !doc.embedding_abilitato
                    })}
                    className="btn btn-secondary btn-sm"
                  >
                    {doc.embedding_abilitato ? 'Disabilita' : 'Abilita'} Embedding
                  </button>
                  <button
                    onClick={() => deleteDocumentMutation.mutate(doc.id)}
                    className="btn btn-danger btn-sm"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card">
          <EmptyState
            icon={Sparkles}
            title="Nessun documento"
            description="Carica documenti per alimentare il sistema RAG e migliorare le risposte automatiche."
            action={
              <button onClick={() => setShowUploadModal(true)} className="btn btn-primary">
                <Upload className="w-4 h-4 mr-2" />
                Carica Primo Documento
              </button>
            }
          />
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Carica Documento</h2>

            <div className="space-y-4">
              <div>
                <label className="label">File</label>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,.html"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="input"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Formati supportati: PDF, DOCX, TXT, HTML
                </p>
              </div>

              <div>
                <label className="label">Tipo Documento</label>
                <select
                  value={uploadTipo}
                  onChange={(e) => setUploadTipo(e.target.value as TipoDocumento)}
                  className="input"
                >
                  {Object.values(TipoDocumento).map((tipo) => (
                    <option key={tipo} value={tipo}>
                      {getTipoDocumentoLabel(tipo)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="embedImmediately"
                  checked={embedImmediately}
                  onChange={(e) => setEmbedImmediately(e.target.checked)}
                  className="mr-2"
                />
                <label htmlFor="embedImmediately" className="text-sm text-gray-700">
                  Embedda immediatamente dopo il caricamento
                </label>
              </div>
            </div>

            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={handleUpload}
                disabled={!uploadFile || uploadMutation.isPending}
                className="btn btn-primary flex-1"
              >
                {uploadMutation.isPending ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Caricamento...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Carica
                  </>
                )}
              </button>
              <button
                onClick={() => {
                  setShowUploadModal(false)
                  setUploadFile(null)
                }}
                className="btn btn-secondary"
                disabled={uploadMutation.isPending}
              >
                Annulla
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
