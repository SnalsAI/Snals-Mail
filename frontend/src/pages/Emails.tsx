import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Mail, RefreshCw, Filter, Search } from 'lucide-react'
import { emailService, type EmailFilters } from '@/services/emailService'
import { EmailCategory, EmailStatus, AccountType } from '@/types'
import PageHeader from '@/components/PageHeader'
import LoadingSpinner from '@/components/LoadingSpinner'
import EmptyState from '@/components/EmptyState'
import Badge from '@/components/Badge'
import { formatDateTime, getCategoryLabel, getStatusLabel, getCategoryColor, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'

export default function Emails() {
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState<EmailFilters>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const { data: emails, isLoading } = useQuery({
    queryKey: ['emails', filters],
    queryFn: () => emailService.getEmails(filters),
  })

  const syncMutation = useMutation({
    mutationFn: (accountType: 'normale' | 'pec') => emailService.syncEmails(accountType),
    onSuccess: () => {
      toast.success('Email sincronizzate con successo')
      queryClient.invalidateQueries({ queryKey: ['emails'] })
    },
    onError: () => {
      toast.error('Errore durante la sincronizzazione')
    },
  })

  const filteredEmails = emails?.filter((email) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      email.oggetto.toLowerCase().includes(query) ||
      email.mittente.toLowerCase().includes(query) ||
      email.corpo_testo.toLowerCase().includes(query)
    )
  })

  return (
    <div className="p-8">
      <PageHeader
        title="Email"
        description="Gestisci tutte le email ricevute"
        actions={
          <>
            <button
              onClick={() => syncMutation.mutate('normale')}
              disabled={syncMutation.isPending}
              className="btn btn-secondary"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
              Sync Normale
            </button>
            <button
              onClick={() => syncMutation.mutate('pec')}
              disabled={syncMutation.isPending}
              className="btn btn-secondary"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
              Sync PEC
            </button>
          </>
        }
      />

      {/* Search and Filters */}
      <div className="card mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Cerca email per oggetto, mittente o contenuto..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn btn-secondary"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filtri
          </button>
        </div>

        {showFilters && (
          <div className="mt-4 pt-4 border-t grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label">Categoria</label>
              <select
                value={filters.categoria || ''}
                onChange={(e) => setFilters({ ...filters, categoria: e.target.value as EmailCategory })}
                className="input"
              >
                <option value="">Tutte</option>
                {Object.values(EmailCategory).map((cat) => (
                  <option key={cat} value={cat}>
                    {getCategoryLabel(cat)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Stato</label>
              <select
                value={filters.status || ''}
                onChange={(e) => setFilters({ ...filters, status: e.target.value as EmailStatus })}
                className="input"
              >
                <option value="">Tutti</option>
                {Object.values(EmailStatus).map((status) => (
                  <option key={status} value={status}>
                    {getStatusLabel(status)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Tipo Account</label>
              <select
                value={filters.account_type || ''}
                onChange={(e) => setFilters({ ...filters, account_type: e.target.value })}
                className="input"
              >
                <option value="">Tutti</option>
                <option value="normale">Normale</option>
                <option value="pec">PEC</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Emails List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : filteredEmails && filteredEmails.length > 0 ? (
        <div className="space-y-3">
          {filteredEmails.map((email) => (
            <Link
              key={email.id}
              to={`/emails/${email.id}`}
              className="card hover:shadow-md transition-shadow block"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900 truncate">
                      {email.oggetto}
                    </h3>
                    <Badge className={getCategoryColor(email.categoria)}>
                      {getCategoryLabel(email.categoria)}
                    </Badge>
                    <Badge className={getStatusColor(email.status)}>
                      {getStatusLabel(email.status)}
                    </Badge>
                    {email.account_type === AccountType.PEC && (
                      <Badge variant="info">PEC</Badge>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mb-2">
                    <span className="font-medium">Da:</span> {email.mittente}
                  </p>
                  <p className="text-sm text-gray-500 line-clamp-2">
                    {email.corpo_testo.substring(0, 200)}...
                  </p>
                </div>
                <div className="ml-4 text-right flex-shrink-0">
                  <p className="text-sm text-gray-500">
                    {formatDateTime(email.data_ricezione)}
                  </p>
                  {email.allegati && email.allegati.length > 0 && (
                    <p className="text-xs text-gray-400 mt-1">
                      {email.allegati.length} allegati
                    </p>
                  )}
                  {email.priorita > 7 && (
                    <Badge variant="warning" className="mt-2">Alta priorità</Badge>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="card">
          <EmptyState
            icon={Mail}
            title="Nessuna email trovata"
            description="Non ci sono email che corrispondono ai criteri di ricerca."
          />
        </div>
      )}
    </div>
  )
}
