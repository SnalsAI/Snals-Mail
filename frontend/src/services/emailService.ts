import api from '@/lib/api'
import type { Email, EmailCategory, EmailStatus } from '@/types'

export interface EmailFilters {
  categoria?: EmailCategory
  status?: EmailStatus
  account_type?: string
  data_da?: string
  data_a?: string
  mittente?: string
  oggetto?: string
}

export const emailService = {
  async getEmails(filters?: EmailFilters) {
    const { data } = await api.get<Email[]>('/emails/', { params: filters })
    return data
  },

  async getEmail(id: number) {
    const { data } = await api.get<Email>(`/emails/${id}`)
    return data
  },

  async syncEmails(accountType: 'normale' | 'pec') {
    const { data } = await api.post('/emails/sync', { account_type: accountType })
    return data
  },

  async updateEmailStatus(id: number, status: EmailStatus) {
    const { data } = await api.patch(`/emails/${id}/status`, { status })
    return data
  },

  async deleteEmail(id: number) {
    await api.delete(`/emails/${id}`)
  },
}
