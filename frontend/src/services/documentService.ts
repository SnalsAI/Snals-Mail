import api from '@/lib/api'
import type { Documento, TipoDocumento, StatoDocumento } from '@/types'

export interface DocumentFilters {
  tipo?: TipoDocumento
  stato?: StatoDocumento
  embedding_abilitato?: boolean
  attivo?: boolean
}

export const documentService = {
  async getDocuments(filters?: DocumentFilters) {
    const { data } = await api.get<Documento[]>('/documenti/', { params: filters })
    return data
  },

  async getDocument(id: number) {
    const { data } = await api.get<Documento>(`/documenti/${id}`)
    return data
  },

  async uploadDocument(file: File, tipo: TipoDocumento, metadata: Record<string, any>, embedImmediately: boolean = false) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('tipo', tipo)
    formData.append('metadata', JSON.stringify(metadata))
    formData.append('embed_immediately', embedImmediately.toString())

    const { data } = await api.post<Documento>('/documenti/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async updateDocument(id: number, updates: Partial<Documento>) {
    const { data } = await api.put<Documento>(`/documenti/${id}`, updates)
    return data
  },

  async deleteDocument(id: number) {
    await api.delete(`/documenti/${id}`)
  },

  async embedDocument(id: number) {
    const { data } = await api.post(`/documenti/${id}/embed`)
    return data
  },

  async queryRAG(query: string, tipoFilter?: TipoDocumento[], nDocs: number = 3) {
    const { data } = await api.post('/documenti/rag/query', {
      query,
      tipo_filter: tipoFilter,
      n_docs: nDocs,
    })
    return data
  },

  async getRAGStats() {
    const { data } = await api.get('/documenti/rag/stats')
    return data
  },
}
