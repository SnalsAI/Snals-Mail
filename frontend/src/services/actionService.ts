import api from '@/lib/api'
import type { Azione, StatoAzione } from '@/types'

export const actionService = {
  async getActions(emailId?: number) {
    const params = emailId ? { email_id: emailId } : {}
    const { data } = await api.get<Azione[]>('/azioni/', { params })
    return data
  },

  async getAction(id: number) {
    const { data } = await api.get<Azione>(`/azioni/${id}`)
    return data
  },

  async executeAction(id: number) {
    const { data } = await api.post(`/azioni/${id}/execute`)
    return data
  },

  async createAction(emailId: number, actionData: Partial<Azione>) {
    const { data } = await api.post('/azioni/', { ...actionData, email_id: emailId })
    return data
  },

  async deleteAction(id: number) {
    await api.delete(`/azioni/${id}`)
  },
}
