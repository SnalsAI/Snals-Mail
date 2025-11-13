import api from '@/lib/api'
import type { DashboardStats } from '@/types'

export const dashboardService = {
  async getStats(): Promise<DashboardStats> {
    // Since backend doesn't have stats endpoint yet, we'll aggregate from existing endpoints
    try {
      const [emailsRes, actionsRes] = await Promise.all([
        api.get('/emails/'),
        api.get('/azioni/'),
      ])

      const emails = emailsRes.data || []
      const actions = actionsRes.data || []

      const oggi = new Date()
      oggi.setHours(0, 0, 0, 0)

      const emailsOggi = emails.filter((e: any) => {
        const dataRicezione = new Date(e.data_ricezione)
        return dataRicezione >= oggi
      }).length

      const emailsNonLette = emails.filter((e: any) => e.status === 'non_letta').length

      const azioniPending = actions.filter((a: any) => a.stato === 'pending').length

      const categorieDistribution = emails.reduce((acc: Record<string, number>, e: any) => {
        const cat = e.categoria || 'altro'
        acc[cat] = (acc[cat] || 0) + 1
        return acc
      }, {})

      const azioniDistribution = actions.reduce((acc: Record<string, number>, a: any) => {
        const tipo = a.tipo_azione || 'altro'
        acc[tipo] = (acc[tipo] || 0) + 1
        return acc
      }, {})

      return {
        emails_oggi: emailsOggi,
        emails_non_lette: emailsNonLette,
        azioni_pending: azioniPending,
        eventi_settimana: 0, // Will be implemented when calendar is ready
        categorie_distribution: categorieDistribution,
        azioni_distribution: azioniDistribution,
      }
    } catch (error) {
      console.error('Error fetching dashboard stats:', error)
      return {
        emails_oggi: 0,
        emails_non_lette: 0,
        azioni_pending: 0,
        eventi_settimana: 0,
        categorie_distribution: {},
        azioni_distribution: {},
      }
    }
  },
}
