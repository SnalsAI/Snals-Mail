import axios from 'axios'
import type { Email, Action, Rule, CalendarEvent, Stats } from '../types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

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

  markAsRead: (id: number) =>
    api.put(`/emails/${id}/revisiona`),

  delete: (id: number) =>
    api.delete(`/emails/${id}`),

  getStats: () =>
    api.get<Stats>('/emails/stats'),
}

// Actions endpoints
export const actionsApi = {
  getAll: (params?: { skip?: number; limit?: number; stato?: string }) =>
    api.get<Action[]>('/azioni/', { params }),

  getById: (id: number) =>
    api.get<Action>(`/azioni/${id}`),

  create: (data: Partial<Action>) =>
    api.post<Action>('/azioni/', data),

  execute: (id: number) =>
    api.post(`/azioni/${id}/execute`),

  delete: (id: number) =>
    api.delete(`/azioni/${id}`),
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
}

// Settings endpoints (configuration)
export const settingsApi = {
  getAll: () =>
    api.get('/settings/'),

  update: (data: Record<string, any>) =>
    api.put('/settings/', data),

  testEmailNormal: () =>
    api.post('/api/settings/test-email-normal'),

  testEmailPEC: () =>
    api.post('/api/settings/test-email-pec'),
}

// Health check
export const healthCheck = () =>
  api.get('/health')
