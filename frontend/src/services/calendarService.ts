import api from '@/lib/api'
import type { EventoCalendario } from '@/types'

export const calendarService = {
  async getEvents(dataInizio?: string, dataFine?: string) {
    const params = { data_inizio: dataInizio, data_fine: dataFine }
    const { data } = await api.get<EventoCalendario[]>('/calendario/eventi', { params })
    return data
  },

  async getEvent(id: number) {
    const { data } = await api.get<EventoCalendario>(`/calendario/eventi/${id}`)
    return data
  },

  async createEvent(eventData: Omit<EventoCalendario, 'id' | 'created_at'>) {
    const { data } = await api.post<EventoCalendario>('/calendario/eventi', eventData)
    return data
  },

  async updateEvent(id: number, eventData: Partial<EventoCalendario>) {
    const { data } = await api.put<EventoCalendario>(`/calendario/eventi/${id}`, eventData)
    return data
  },

  async deleteEvent(id: number) {
    await api.delete(`/calendario/eventi/${id}`)
  },

  async syncWithGoogle() {
    const { data } = await api.post('/calendario/sync')
    return data
  },
}
