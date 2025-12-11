import axios from 'axios'
import type { Email, Action, Rule, CalendarEvent, Stats } from '../types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Email endpoints
export const emailsApi = {
  getAll: (params?: { skip?: number; limit?: number; categoria?: string; stato?: string }) =>
    api.get<Email[]>('/emails/', { params }),

  getById: (id: number) =>
    api.get<Email>(`/emails/${id}`),

  updateCategoria: (id: number, categoria: string) =>
    api.put(`/emails/${id}/categoria`, { categoria }),

  update: (id: number, data: { categoria?: string; sottocategoria?: string; letto?: boolean; note?: string }) =>
    api.put(`/emails/${id}`, data),

  markAsRead: (id: number) =>
    api.put(`/emails/${id}/revisiona`),

  reprocess: (id: number) =>
    api.post(`/emails/${id}/reprocess`),

  delete: (id: number) =>
    api.delete(`/emails/${id}`),

  getStats: () =>
    api.get<Stats>('/emails/stats'),

  fetchManual: () =>
    api.post('/emails/fetch'),

  // Subcategory proposals
  getProposals: (params?: { skip?: number; limit?: number }) =>
    api.get('/emails/proposals', { params }),

  approveSubcategory: (id: number) =>
    api.post(`/emails/${id}/approve-subcategory`),

  rejectSubcategory: (id: number) =>
    api.post(`/emails/${id}/reject-subcategory`),

  // Email interpretation and actions
  getInterpretazione: (id: number) =>
    api.get(`/emails/${id}/interpretazione`),

  getAzioni: (id: number) =>
    api.get(`/emails/${id}/azioni`),
}

// Actions endpoints
export const actionsApi = {
  getAll: (params?: { skip?: number; limit?: number; stato?: string; email_id?: number }) =>
    api.get<Action[]>('/azioni/', { params }),

  getById: (id: number) =>
    api.get<Action>(`/azioni/${id}`),

  create: (data: Partial<Action>) =>
    api.post<Action>('/azioni/', data),

  execute: (id: number) =>
    api.post(`/azioni/${id}/execute`),

  delete: (id: number) =>
    api.delete(`/azioni/${id}`),

  processEmail: (emailId: number) =>
    api.post(`/azioni/process-email/${emailId}`),

  getDailyReports: (days: number = 7) =>
    api.get('/azioni/reports/daily', { params: { days } }),

  getEmailSummaries: (days: number = 7, limit: number = 50) =>
    api.get('/azioni/reports/summaries', { params: { days, limit } }),

  getForwardsReport: (days: number = 7) =>
    api.get('/azioni/reports/forwards', { params: { days } }),

  getIssuesReport: (days: number = 7) =>
    api.get('/azioni/reports/issues', { params: { days } }),

  getSummariesBySender: (days: number = 7) =>
    api.get('/azioni/reports/summaries-by-sender', { params: { days } }),

  // Issue resolution workflow
  getIssueDetails: (azioneId: number) =>
    api.get(`/azioni/issues/${azioneId}/details`),

  resolveIssue: (azioneId: number, data: Record<string, any>) =>
    api.post(`/azioni/issues/${azioneId}/resolve`, data),
}

// Rules endpoints
export const rulesApi = {
  getAll: (params?: { skip?: number; limit?: number; attivo?: boolean }) =>
    api.get<Rule[]>('/regole/', { params }),

  getById: (id: number) =>
    api.get<Rule>(`/regole/${id}`),

  create: (data: Partial<Rule>) =>
    api.post<Rule>('/regole/', data),

  update: (id: number, data: Partial<Rule>) =>
    api.put<Rule>(`/regole/${id}`, data),

  delete: (id: number) =>
    api.delete(`/regole/${id}`),

  toggle: (id: number) =>
    api.put(`/regole/${id}/toggle`),

  test: (id: number, emailId: number) =>
    api.post(`/regole/${id}/test`, { email_id: emailId }),
}

// Calendar endpoints
export const calendarApi = {
  getAll: (params?: { skip?: number; limit?: number; data_da?: string; data_a?: string }) =>
    api.get<CalendarEvent[]>('/calendario/', { params }),

  getById: (id: number) =>
    api.get<CalendarEvent>(`/calendario/${id}`),

  create: (data: Partial<CalendarEvent>) =>
    api.post<CalendarEvent>('/calendario/', data),

  update: (id: number, data: Partial<CalendarEvent>) =>
    api.put<CalendarEvent>(`/calendario/${id}`, data),

  delete: (id: number) =>
    api.delete(`/calendario/${id}`),

  syncWithGoogle: (id: number) =>
    api.post(`/calendario/${id}/sync-google`),

  // Report anomalie calendario
  getAnomalies: (params?: { data_da?: string }) =>
    api.get('/calendario/report/anomalie', { params }),

  // Risolvi anomalie automaticamente
  resolveAnomaliesAuto: () =>
    api.post('/calendario/report/anomalie/risolvi-auto'),

  // Risolvi singola anomalia
  resolveAnomaly: (eventoId: number, azione: string = 'completato') =>
    api.delete(`/calendario/report/anomalie/${eventoId}`, { params: { azione } }),
}

// Settings endpoints (configuration)
export const settingsApi = {
  getAll: () =>
    api.get('/settings/'),

  update: (data: Record<string, any>) =>
    api.put('/settings/', data),

  testEmailNormal: () =>
    api.post('/settings/test-email-normal'),

  testEmailPEC: () =>
    api.post('/settings/test-email-pec'),

  testGoogleCalendar: () =>
    api.post('/settings/test-google-calendar'),

  testGoogleDrive: () =>
    api.post('/settings/test-google-drive'),

  // Category management
  getCategories: () =>
    api.get('/settings/categories'),

  updateCategory: (categoryKey: string, data: any) =>
    api.put(`/settings/categories/${categoryKey}`, data),

  resetCategories: () =>
    api.post('/settings/categories/reset'),

  // API Stats - Monitoraggio chiamate esterne
  getApiStats: () =>
    api.get('/settings/api-stats'),

  resetApiStats: () =>
    api.post('/settings/api-stats/reset'),
}

// Knowledge Base endpoints
export const knowledgeApi = {
  getAll: (params?: {
    tipo_documento?: string
    categoria_email?: string
    tags?: string
    ente_emittente?: string
    solo_attivi?: boolean
    skip?: number
    limit?: number
  }) =>
    api.get('/knowledge/documents', { params }),

  getById: (id: number) =>
    api.get(`/knowledge/documents/${id}`),

  upload: (formData: FormData) =>
    api.post('/knowledge/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),

  delete: (id: number) =>
    api.delete(`/knowledge/documents/${id}`),

  index: (id: number) =>
    api.post(`/knowledge/documents/${id}/index`),

  getStats: () =>
    api.get('/knowledge/stats'),
}

// Spam endpoints
export const spamApi = {
  getAll: () =>
    api.get('/spam/'),

  getDeleted: (params?: { skip?: number; limit?: number }) =>
    api.get('/spam/deleted', { params }),

  getStats: () =>
    api.get('/spam/stats'),

  deleteFromServer: (id: number) =>
    api.delete(`/spam/${id}/from-server`),

  deleteAllFromServer: () =>
    api.delete('/spam/bulk/from-server?confirm=true'),

  markAsSpam: (id: number) =>
    api.post(`/spam/${id}/mark`),

  unmarkAsSpam: (id: number, newCategoria: string = 'altro') =>
    api.post(`/spam/${id}/unmark?new_categoria=${newCategoria}`),
}

// Ricevute PEC endpoints
export const ricevutePecApi = {
  getAll: (params?: { skip?: number; limit?: number; tipo?: string }) =>
    api.get('/ricevute-pec/', { params }),

  getStats: () =>
    api.get('/ricevute-pec/stats'),

  getOne: (id: number) =>
    api.get(`/ricevute-pec/${id}`),
}

// Schools endpoints
export const schoolsApi = {
  getAll: () =>
    api.get('/schools/'),

  getStats: () =>
    api.get('/schools/stats'),

  add: (code: string) =>
    api.post('/schools/add', { school_code: code }),

  update: (code: string) =>
    api.post(`/schools/update/${code}?force_online=true`),

  delete: (code: string) =>
    api.delete(`/schools/${code}`),

  // Pending schools
  getPending: () =>
    api.get('/schools/pending/list'),

  approvePending: (code: string, data: { nome?: string; comune?: string; indirizzo?: string; tipo?: string }) =>
    api.post(`/schools/pending/${code}/approve`, data),

  rejectPending: (code: string) =>
    api.delete(`/schools/pending/${code}/reject`),

  generateProposal: (code: string) =>
    api.post(`/schools/pending/${code}/generate`),
}

// System Settings endpoints
export const systemSettingsApi = {
  getAll: () =>
    api.get('/system-settings/'),

  update: (key: string, value: string) =>
    api.put(`/system-settings/${key}`, { value }),
}

// Interpelli endpoints
export const interpelliApi = {
  getAll: (params?: { skip?: number; limit?: number }) =>
    api.get('/interpelli/', { params }),

  getById: (id: number) =>
    api.get(`/interpelli/${id}`),

  perClasse: (params?: { solo_aperti?: boolean }) =>
    api.get('/interpelli/per-classe', { params }),

  delete: (id: number) =>
    api.delete(`/interpelli/${id}`),

  markProcessed: (id: number) =>
    api.put(`/interpelli/${id}/mark-processed`),

  sendNotification: (id: number) =>
    api.post(`/interpelli/${id}/notify`),
}

// Classi Concorso endpoints
export const classiConcorsoApi = {
  getAll: (params?: { search?: string; grado?: string }) =>
    api.get('/classi-concorso/', { params }),

  getStats: () =>
    api.get('/classi-concorso/stats'),

  search: (query: string) =>
    api.get('/classi-concorso/search', { params: { q: query } }),
}

// Debug endpoints
export const debugApi = {
  getSystemInfo: () =>
    api.get('/debug/system-info'),

  getLogs: (lines?: number) =>
    api.get('/debug/logs', { params: { lines } }),

  testOllama: () =>
    api.post('/debug/test-ollama'),

  testEmail: () =>
    api.post('/debug/test-email'),

  getEmails: (params?: { limit?: number; skip?: number; categoria?: string; con_azioni?: string; con_interpelli?: string }) =>
    api.get('/debug/emails', { params }),

  reparseInterpello: (interpelloId: number, strategy: string) =>
    api.post(`/debug/interpelli/${interpelloId}/reparse`, null, { params: { strategy } }),
}

// Delegati endpoints
export const delegatiApi = {
  getAll: () =>
    api.get('/delegati/'),

  create: (data: any) =>
    api.post('/delegati/', data),

  update: (id: number, data: any) =>
    api.put(`/delegati/${id}`, data),

  delete: (id: number) =>
    api.delete(`/delegati/${id}`),

  // Zone
  getZone: () =>
    api.get('/delegati/zone/'),

  createZona: (data: any) =>
    api.post('/delegati/zone/', data),

  updateZona: (id: number, data: any) =>
    api.put(`/delegati/zone/${id}`, data),

  deleteZona: (id: number) =>
    api.delete(`/delegati/zone/${id}`),
}

// RAG endpoints
export const ragApi = {
  getDocuments: (params?: {
    limit?: number;
    offset?: number;
    filter_categoria?: string;
    filter_sottocategoria?: string;
    filter_mittente?: string;
  }) =>
    api.get('/rag/documents', { params }),

  query: (data: {
    query: string;
    n_results?: number;
    filter_categoria?: string;
    filter_sottocategoria?: string;
    filter_mittente?: string;
  }) =>
    api.post('/rag/query', data),

  chat: (data: {
    query: string;
    n_results?: number;
    filter_categoria?: string;
    filter_sottocategoria?: string;
    filter_mittente?: string;
    use_openai?: boolean;
  }) =>
    api.post('/rag/chat', data),

  getStatistics: () =>
    api.get('/rag/statistics'),

  indexEmail: (emailId: number) =>
    api.post('/rag/index-email', { email_id: emailId }),

  deleteEmailDocuments: (emailId: number) =>
    api.delete(`/rag/email/${emailId}`),

  updateMetadata: (docId: string, metadata: any) =>
    api.put(`/rag/document/${docId}/metadata`, { document_id: docId, metadata }),

  deleteDocument: (docId: string) =>
    api.delete(`/rag/document/${docId}`),

  reset: (confirm: string) =>
    api.post('/rag/reset', null, { params: { confirm } }),
}

// Verification API - Confronto locale vs OpenAI
export const verificationApi = {
  // Status del servizio
  getStatus: () =>
    api.get('/verification/status'),

  // Verifica singolo interpello
  verifyInterpello: (testo: string, model?: string) =>
    api.post('/verification/interpello', { testo, tipo: 'interpello' }, { params: { model } }),

  // Verifica singolo evento calendario
  verifyCalendario: (testo: string, model?: string) =>
    api.post('/verification/calendario', { testo, tipo: 'calendario' }, { params: { model } }),

  // Verifica categorizzazione
  verifyCategorizzazione: (oggetto: string, corpo: string, model?: string) =>
    api.post('/verification/categorizzazione', null, { params: { oggetto, corpo, model } }),

  // Verifica email specifica
  verifyEmail: (emailId: number, tipo?: string, model?: string) =>
    api.get(`/verification/email/${emailId}`, { params: { tipo: tipo || 'auto', model } }),

  // Batch verifica interpelli
  verifyInterpelliBatch: (limit?: number, model?: string) =>
    api.get('/verification/interpelli/batch', { params: { limit: limit || 5, model } }),

  // Batch verifica calendari
  verifyCalendariBatch: (limit?: number, model?: string) =>
    api.get('/verification/calendari/batch', { params: { limit: limit || 5, model } }),
}

// Bug Reports endpoints
export const bugsApi = {
  create: (bug: {
    descrizione: string
    pagina?: string
    componente?: string
    browser?: string
    viewport?: string
    console_errors?: any[]
    network_errors?: any[]
    email_id?: number
    azione_id?: number
  }) => api.post('/bugs/', bug),

  getAll: (params?: { stato?: string; priorita?: string; limit?: number }) =>
    api.get('/bugs/', { params }),

  getOpen: () =>
    api.get('/bugs/open'),

  getSummary: () =>
    api.get('/bugs/summary'),

  getById: (id: number) =>
    api.get(`/bugs/${id}`),

  update: (id: number, data: {
    stato?: string
    priorita?: string
    note_tecniche?: string
    file_coinvolti?: string[]
    soluzione_proposta?: string
  }) => api.patch(`/bugs/${id}`, data),

  delete: (id: number) =>
    api.delete(`/bugs/${id}`),
}

// Health check
export const healthCheck = () =>
  api.get('/health')

// ============================================================================
// BOOKING MODULE API
// ============================================================================

// Booking Public API (for external users)
export const bookingPublicApi = {
  // Get active campaigns
  getCampagne: () =>
    api.get('/booking/public/campagne'),

  // Get active locations
  getSedi: () =>
    api.get('/booking/public/sedi'),

  // Get appointment types (optionally filtered by campaign)
  getTipiAppuntamento: (campagnaId?: number) =>
    api.get('/booking/public/tipi-appuntamento', { params: { campagna_id: campagnaId } }),

  // Get available slots
  getSlotsDisponibili: (params: {
    campagna_id?: number
    sede_id?: number
    tipo_appuntamento_id?: number
    data_da?: string
    data_a?: string
  }) =>
    api.get('/booking/public/slots/disponibili', { params }),

  // Create a new booking
  creaPrenotazione: (data: {
    slot_id: number
    campagna_id?: number
    nome: string
    cognome: string
    email: string
    telefono?: string
    codice_fiscale?: string
    tipologia_contratto?: string
    scuola_attuale?: string
    note?: string
    motivo?: string
    privacy_accettata: boolean
  }) =>
    api.post('/booking/public/prenotazioni', data),

  // Get booking by token
  getPrenotazioneByToken: (token: string) =>
    api.get(`/booking/public/prenotazioni/${token}`),

  // Update booking by token
  aggiornaPrenotazione: (token: string, data: {
    telefono?: string
    note?: string
  }) =>
    api.put(`/booking/public/prenotazioni/${token}`, data),

  // Cancel booking by token
  annullaPrenotazione: (token: string, motivo?: string) =>
    api.delete(`/booking/public/prenotazioni/${token}`, { params: { motivo } }),

  // Reschedule booking
  spostaPrenotazione: (token: string, nuovoSlotId: number) =>
    api.post(`/booking/public/prenotazioni/${token}/sposta`, { nuovo_slot_id: nuovoSlotId }),
}

// Booking Staff API (for operators)
export const bookingStaffApi = {
  // Get staff's availabilities
  getDisponibilita: (staffId: number, params?: { data_da?: string; data_a?: string }) =>
    api.get('/booking/staff/disponibilita', { params: { staff_id: staffId, ...params } }),

  // Create availability
  creaDisponibilita: (data: {
    staff_id: number
    sede_id: number
    data: string
    ora_inizio: string
    ora_fine: string
    note?: string
  }) =>
    api.post('/booking/staff/disponibilita', data),

  // Bulk create availabilities
  creaDisponibilitaBulk: (data: {
    staff_id: number
    sede_id: number
    date_list: string[]
    ora_inizio: string
    ora_fine: string
    note?: string
  }) =>
    api.post('/booking/staff/disponibilita/bulk', data),

  // Update availability
  aggiornaDisponibilita: (id: number, data: {
    ora_inizio?: string
    ora_fine?: string
    note?: string
    attivo?: boolean
  }) =>
    api.put(`/booking/staff/disponibilita/${id}`, data),

  // Delete availability
  eliminaDisponibilita: (id: number) =>
    api.delete(`/booking/staff/disponibilita/${id}`),

  // Get staff calendar
  getCalendario: (staffId: number, params?: { data_da?: string; data_a?: string }) =>
    api.get('/booking/staff/calendario', { params: { staff_id: staffId, ...params } }),

  // Get staff's bookings
  getPrenotazioni: (staffId: number, params?: {
    data_da?: string
    data_a?: string
    stato?: string
    page?: number
    per_page?: number
  }) =>
    api.get('/booking/staff/prenotazioni', { params: { staff_id: staffId, ...params } }),

  // Mark booking as completed
  marcaCompletata: (id: number, esito?: string) =>
    api.put(`/booking/staff/prenotazioni/${id}/completata`, null, { params: { esito } }),

  // Mark booking as no-show
  marcaNoShow: (id: number, note?: string) =>
    api.put(`/booking/staff/prenotazioni/${id}/no-show`, null, { params: { note } }),

  // Cancel booking (by staff)
  annullaPrenotazione: (id: number, motivo?: string) =>
    api.put(`/booking/staff/prenotazioni/${id}/annulla`, null, { params: { motivo } }),
}

// Booking Admin API (for administrators)
export const bookingAdminApi = {
  // === SEDI ===
  getSedi: () =>
    api.get('/booking/admin/sedi'),

  creaSede: (data: {
    nome: string
    indirizzo?: string
    citta?: string
    cap?: string
    telefono?: string
    email?: string
  }) =>
    api.post('/booking/admin/sedi', data),

  aggiornaSede: (id: number, data: {
    nome?: string
    indirizzo?: string
    citta?: string
    cap?: string
    telefono?: string
    email?: string
    attivo?: boolean
  }) =>
    api.put(`/booking/admin/sedi/${id}`, data),

  eliminaSede: (id: number) =>
    api.delete(`/booking/admin/sedi/${id}`),

  // === STAFF ===
  getStaff: () =>
    api.get('/booking/admin/staff'),

  getStaffById: (id: number) =>
    api.get(`/booking/admin/staff/${id}`),

  creaStaff: (data: {
    nome: string
    cognome: string
    email: string
    telefono?: string
    ruolo?: string
  }) =>
    api.post('/booking/admin/staff', data),

  aggiornaStaff: (id: number, data: {
    nome?: string
    cognome?: string
    email?: string
    telefono?: string
    ruolo?: string
    attivo?: boolean
  }) =>
    api.put(`/booking/admin/staff/${id}`, data),

  eliminaStaff: (id: number) =>
    api.delete(`/booking/admin/staff/${id}`),

  // Staff competencies
  aggiungiCompetenza: (staffId: number, data: {
    tipo_appuntamento_id: number
    durata_minuti?: number
  }) =>
    api.post(`/booking/admin/staff/${staffId}/competenze`, data),

  rimuoviCompetenza: (staffId: number, competenzaId: number) =>
    api.delete(`/booking/admin/staff/${staffId}/competenze/${competenzaId}`),

  // === TIPI APPUNTAMENTO ===
  getTipiAppuntamento: () =>
    api.get('/booking/admin/tipi-appuntamento'),

  creaTipoAppuntamento: (data: {
    nome: string
    descrizione?: string
    durata_default_minuti: number
    colore?: string
    richiede_documenti?: boolean
    documenti_richiesti?: string[]
  }) =>
    api.post('/booking/admin/tipi-appuntamento', data),

  aggiornaTipoAppuntamento: (id: number, data: {
    nome?: string
    descrizione?: string
    durata_default_minuti?: number
    colore?: string
    richiede_documenti?: boolean
    documenti_richiesti?: string[]
    attivo?: boolean
  }) =>
    api.put(`/booking/admin/tipi-appuntamento/${id}`, data),

  eliminaTipoAppuntamento: (id: number) =>
    api.delete(`/booking/admin/tipi-appuntamento/${id}`),

  // === CAMPAGNE ===
  getCampagne: () =>
    api.get('/booking/admin/campagne'),

  creaCampagna: (data: {
    nome: string
    descrizione?: string
    data_inizio: string
    data_fine: string
    tipi_appuntamento_ids: number[]
  }) =>
    api.post('/booking/admin/campagne', data),

  aggiornaCampagna: (id: number, data: {
    nome?: string
    descrizione?: string
    data_inizio?: string
    data_fine?: string
    attiva?: boolean
    tipi_appuntamento_ids?: number[]
  }) =>
    api.put(`/booking/admin/campagne/${id}`, data),

  eliminaCampagna: (id: number) =>
    api.delete(`/booking/admin/campagne/${id}`),

  // === SLOTS ===
  generaSlots: (data: {
    staff_id?: number
    data_inizio: string
    data_fine: string
    tipi_appuntamento_ids?: number[]
  }) =>
    api.post('/booking/admin/slots/genera', data),

  bloccaSlot: (id: number, note?: string) =>
    api.put(`/booking/admin/slots/${id}/blocca`, null, { params: { note } }),

  sbloccaSlot: (id: number) =>
    api.put(`/booking/admin/slots/${id}/sblocca`),

  // === PRENOTAZIONI ===
  getPrenotazioni: (params?: {
    data_da?: string
    data_a?: string
    stato?: string
    sede_id?: number
    staff_id?: number
    page?: number
    per_page?: number
  }) =>
    api.get('/booking/admin/prenotazioni', { params }),

  getPrenotazioneById: (id: number) =>
    api.get(`/booking/admin/prenotazioni/${id}`),

  exportPrenotazioni: (params?: {
    data_da?: string
    data_a?: string
    stato?: string
    sede_id?: number
  }) =>
    api.get('/booking/admin/prenotazioni/export', { params, responseType: 'blob' }),

  // === CONTATTI ===
  getContatti: (params?: {
    search?: string
    page?: number
    per_page?: number
  }) =>
    api.get('/booking/admin/contatti', { params }),

  getContattoStorico: (id: number) =>
    api.get(`/booking/admin/contatti/${id}/storico`),

  // === AUDIT LOG ===
  getAuditLog: (params?: {
    prenotazione_id?: number
    data_da?: string
    data_a?: string
    page?: number
    per_page?: number
  }) =>
    api.get('/booking/admin/audit-log', { params }),

  // === STATISTICHE ===
  getStatistiche: (params?: { data_da?: string; data_a?: string }) =>
    api.get('/booking/admin/statistiche', { params }),

  // === CONFIGURAZIONE ===
  getConfig: () =>
    api.get('/booking/admin/config'),

  setConfig: (chiave: string, valore: any) =>
    api.put('/booking/admin/config', { chiave, valore }),
}
