import api from '@/lib/api'
import type { Regola } from '@/types'

export const ruleService = {
  async getRules() {
    const { data } = await api.get<Regola[]>('/regole/')
    return data
  },

  async getRule(id: number) {
    const { data } = await api.get<Regola>(`/regole/${id}`)
    return data
  },

  async createRule(ruleData: Omit<Regola, 'id' | 'created_at' | 'updated_at'>) {
    const { data } = await api.post<Regola>('/regole/', ruleData)
    return data
  },

  async updateRule(id: number, ruleData: Partial<Regola>) {
    const { data } = await api.put<Regola>(`/regole/${id}`, ruleData)
    return data
  },

  async deleteRule(id: number) {
    await api.delete(`/regole/${id}`)
  },

  async toggleRule(id: number, attiva: boolean) {
    const { data } = await api.patch(`/regole/${id}/toggle`, { attiva })
    return data
  },
}
