import { useQuery } from '@tanstack/react-query'
import { Mail, Clock, AlertCircle, CheckCircle } from 'lucide-react'
import { emailsApi } from '../lib/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#6366f1', '#ec4899', '#14b8a6']

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => emailsApi.getStats().then(res => res.data),
  })

  const { data: recentEmails } = useQuery({
    queryKey: ['emails', 'recent'],
    queryFn: () => emailsApi.getAll({ limit: 5 }).then(res => res.data),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const categoryData = stats?.categories_distribution
    ? Object.entries(stats.categories_distribution).map(([name, value]) => ({
        name: name.replace(/_/g, ' '),
        value,
      }))
    : []

  const accountData = stats?.emails_by_account
    ? Object.entries(stats.emails_by_account).map(([name, value]) => ({
        name,
        emails: value,
      }))
    : []

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Panoramica generale del sistema di gestione email
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Email Totali</p>
              <p className="mt-2 text-3xl font-bold text-gray-900">
                {stats?.total_emails || 0}
              </p>
            </div>
            <div className="p-3 bg-primary-100 rounded-lg">
              <Mail className="w-6 h-6 text-primary-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Oggi</p>
              <p className="mt-2 text-3xl font-bold text-gray-900">
                {stats?.emails_today || 0}
              </p>
            </div>
            <div className="p-3 bg-green-100 rounded-lg">
              <Clock className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Da Leggere</p>
              <p className="mt-2 text-3xl font-bold text-gray-900">
                {stats?.unread_emails || 0}
              </p>
            </div>
            <div className="p-3 bg-yellow-100 rounded-lg">
              <AlertCircle className="w-6 h-6 text-yellow-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Azioni Pending</p>
              <p className="mt-2 text-3xl font-bold text-gray-900">
                {stats?.pending_actions || 0}
              </p>
            </div>
            <div className="p-3 bg-purple-100 rounded-lg">
              <CheckCircle className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Categories Distribution */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Distribuzione Categorie
          </h2>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center text-gray-500 py-8">Nessun dato disponibile</p>
          )}
        </div>

        {/* Emails by Account */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Email per Account
          </h2>
          {accountData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={accountData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="emails" fill="#0ea5e9" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center text-gray-500 py-8">Nessun dato disponibile</p>
          )}
        </div>
      </div>

      {/* Recent Emails */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Email Recenti
        </h2>
        {recentEmails && recentEmails.length > 0 ? (
          <div className="space-y-4">
            {recentEmails.map((email) => (
              <div
                key={email.id}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {email.oggetto}
                  </p>
                  <p className="text-sm text-gray-500 truncate">
                    Da: {email.mittente}
                  </p>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  {email.categoria && (
                    <span className="badge-primary">
                      {email.categoria.replace(/_/g, ' ')}
                    </span>
                  )}
                  <span className="text-xs text-gray-500">
                    {new Date(email.data_ricezione).toLocaleDateString('it-IT')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-gray-500 py-8">Nessuna email recente</p>
        )}
      </div>
    </div>
  )
}
