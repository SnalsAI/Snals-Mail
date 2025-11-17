import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Mail, Filter, Search } from 'lucide-react'
import { emailsApi } from '../lib/api'
import { EmailCategory, EmailStatus } from '../types'

export default function Emails() {
  const [filters, setFilters] = useState({
    categoria: '',
    stato: '',
    search: '',
  })

  const { data: emails, isLoading } = useQuery({
    queryKey: ['emails', filters],
    queryFn: () => emailsApi.getAll({
      categoria: filters.categoria || undefined,
      stato: filters.stato || undefined,
    }).then(res => res.data),
  })

  const filteredEmails = emails?.filter(email => {
    if (!filters.search) return true
    const search = filters.search.toLowerCase()
    return (
      email.oggetto.toLowerCase().includes(search) ||
      email.mittente.toLowerCase().includes(search) ||
      email.corpo.toLowerCase().includes(search)
    )
  })

  const getCategoryBadgeColor = (categoria?: string) => {
    switch (categoria) {
      case EmailCategory.RICHIESTA_APPUNTAMENTO:
        return 'badge-warning'
      case EmailCategory.CONVOCAZIONE_SCUOLA:
        return 'badge-danger'
      case EmailCategory.COMUNICAZIONE_UST_USR:
        return 'badge-primary'
      default:
        return 'badge-gray'
    }
  }

  const getStatusBadgeColor = (stato: string) => {
    switch (stato) {
      case EmailStatus.PROCESSATA:
        return 'badge-success'
      case EmailStatus.INTERPRETATA:
        return 'badge-primary'
      case EmailStatus.CATEGORIZZATA:
        return 'badge-warning'
      case EmailStatus.ERRORE:
        return 'badge-danger'
      default:
        return 'badge-gray'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Email</h1>
          <p className="mt-1 text-sm text-gray-500">
            Gestisci e visualizza tutte le email ricevute
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="md:col-span-2">
            <label className="label">
              <Search className="w-4 h-4 inline mr-2" />
              Cerca
            </label>
            <input
              type="text"
              className="input"
              placeholder="Cerca per oggetto, mittente o contenuto..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            />
          </div>

          {/* Category Filter */}
          <div>
            <label className="label">
              <Filter className="w-4 h-4 inline mr-2" />
              Categoria
            </label>
            <select
              className="input"
              value={filters.categoria}
              onChange={(e) => setFilters({ ...filters, categoria: e.target.value })}
            >
              <option value="">Tutte</option>
              {Object.values(EmailCategory).map((cat) => (
                <option key={cat} value={cat}>
                  {cat.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <label className="label">Stato</label>
            <select
              className="input"
              value={filters.stato}
              onChange={(e) => setFilters({ ...filters, stato: e.target.value })}
            >
              <option value="">Tutti</option>
              {Object.values(EmailStatus).map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Email List */}
      <div className="card">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : filteredEmails && filteredEmails.length > 0 ? (
          <div className="space-y-2">
            {filteredEmails.map((email) => (
              <Link
                key={email.id}
                to={`/emails/${email.id}`}
                className="block p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1 min-w-0">
                    <div className="p-2 bg-primary-100 rounded-lg mt-1">
                      <Mail className="w-5 h-5 text-primary-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-base font-semibold text-gray-900 truncate">
                          {email.oggetto}
                        </h3>
                        {!email.revisionata && email.richiede_revisione && (
                          <span className="badge-warning">Revisione richiesta</span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        Da: <span className="font-medium">{email.mittente}</span>
                      </p>
                      <p className="text-sm text-gray-500 line-clamp-2">
                        {email.corpo.substring(0, 200)}...
                      </p>
                      <div className="flex items-center gap-2 mt-3">
                        {email.categoria && (
                          <span className={getCategoryBadgeColor(email.categoria)}>
                            {email.categoria.replace(/_/g, ' ')}
                          </span>
                        )}
                        <span className={getStatusBadgeColor(email.stato)}>
                          {email.stato}
                        </span>
                        {email.allegati_nomi && email.allegati_nomi.length > 0 && (
                          <span className="badge-gray">
                            {email.allegati_nomi.length} allegati
                          </span>
                        )}
                        <span className="text-xs text-gray-500 ml-auto">
                          {new Date(email.data_ricezione).toLocaleString('it-IT')}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Mail className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">Nessuna email trovata</p>
          </div>
        )}
      </div>
    </div>
  )
}
