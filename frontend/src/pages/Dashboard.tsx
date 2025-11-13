import { useQuery } from '@tanstack/react-query'
import { Mail, CheckSquare, Calendar, FileText } from 'lucide-react'
import { dashboardService } from '@/services/dashboardService'
import PageHeader from '@/components/PageHeader'
import StatCard from '@/components/StatCard'
import LoadingSpinner from '@/components/LoadingSpinner'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { getCategoryLabel, getTipoDocumentoLabel } from '@/lib/utils'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D']

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardService.getStats,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  // Prepare chart data
  const categorieData = Object.entries(stats?.categorie_distribution || {}).map(([name, value]) => ({
    name: getCategoryLabel(name),
    value,
  }))

  const azioniData = Object.entries(stats?.azioni_distribution || {}).map(([name, value]) => ({
    name: getTipoDocumentoLabel(name),
    value,
  }))

  return (
    <div className="p-8">
      <PageHeader
        title="Dashboard"
        description="Panoramica del sistema SNALS Email Agent"
      />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Email Oggi"
          value={stats?.emails_oggi || 0}
          icon={Mail}
        />
        <StatCard
          title="Email Non Lette"
          value={stats?.emails_non_lette || 0}
          icon={Mail}
        />
        <StatCard
          title="Azioni in Attesa"
          value={stats?.azioni_pending || 0}
          icon={CheckSquare}
        />
        <StatCard
          title="Eventi Settimana"
          value={stats?.eventi_settimana || 0}
          icon={Calendar}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Categories Distribution */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Distribuzione Categorie Email</h3>
          {categorieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categorieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {categorieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 text-center py-8">Nessun dato disponibile</p>
          )}
        </div>

        {/* Actions Distribution */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Distribuzione Azioni</h3>
          {azioniData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={azioniData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" fill="#0ea5e9" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 text-center py-8">Nessun dato disponibile</p>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card mt-6">
        <h3 className="text-lg font-semibold mb-4">Azioni Rapide</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="/emails"
            className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Mail className="w-8 h-8 text-primary-600 mr-3" />
            <div>
              <p className="font-medium">Gestisci Email</p>
              <p className="text-sm text-gray-500">Visualizza e gestisci email</p>
            </div>
          </a>
          <a
            href="/calendar"
            className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Calendar className="w-8 h-8 text-primary-600 mr-3" />
            <div>
              <p className="font-medium">Calendario</p>
              <p className="text-sm text-gray-500">Gestisci eventi</p>
            </div>
          </a>
          <a
            href="/documents"
            className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <FileText className="w-8 h-8 text-primary-600 mr-3" />
            <div>
              <p className="font-medium">Documenti RAG</p>
              <p className="text-sm text-gray-500">Gestisci knowledge base</p>
            </div>
          </a>
        </div>
      </div>
    </div>
  )
}
