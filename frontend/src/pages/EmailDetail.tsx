import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, FileText, Calendar, Download, Trash2 } from 'lucide-react'
import { emailService } from '@/services/emailService'
import { actionService } from '@/services/actionService'
import { EmailStatus } from '@/types'
import PageHeader from '@/components/PageHeader'
import LoadingSpinner from '@/components/LoadingSpinner'
import Badge from '@/components/Badge'
import { formatDateTime, getCategoryLabel, getStatusLabel, getCategoryColor, getStatusColor, getActionTypeLabel, getActionStateLabel, getActionStateColor } from '@/lib/utils'
import toast from 'react-hot-toast'

export default function EmailDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: email, isLoading } = useQuery({
    queryKey: ['email', id],
    queryFn: () => emailService.getEmail(Number(id)),
  })

  const { data: actions } = useQuery({
    queryKey: ['actions', id],
    queryFn: () => actionService.getActions(Number(id)),
    enabled: !!id,
  })

  const updateStatusMutation = useMutation({
    mutationFn: (status: EmailStatus) => emailService.updateEmailStatus(Number(id), status),
    onSuccess: () => {
      toast.success('Stato aggiornato')
      queryClient.invalidateQueries({ queryKey: ['email', id] })
      queryClient.invalidateQueries({ queryKey: ['emails'] })
    },
  })

  const executeActionMutation = useMutation({
    mutationFn: (actionId: number) => actionService.executeAction(actionId),
    onSuccess: () => {
      toast.success('Azione eseguita')
      queryClient.invalidateQueries({ queryKey: ['actions', id] })
    },
    onError: () => {
      toast.error('Errore esecuzione azione')
    },
  })

  const deleteEmailMutation = useMutation({
    mutationFn: () => emailService.deleteEmail(Number(id)),
    onSuccess: () => {
      toast.success('Email eliminata')
      navigate('/emails')
    },
    onError: () => {
      toast.error('Errore eliminazione email')
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!email) {
    return <div className="p-8">Email non trovata</div>
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <Link to="/emails" className="flex items-center text-primary-600 hover:text-primary-700 mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Torna alle email
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Email Header */}
          <div className="card">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h1 className="text-2xl font-bold text-gray-900 mb-3">{email.oggetto}</h1>
                <div className="flex items-center gap-3 mb-4">
                  <Badge className={getCategoryColor(email.categoria)}>
                    {getCategoryLabel(email.categoria)}
                  </Badge>
                  <Badge className={getStatusColor(email.status)}>
                    {getStatusLabel(email.status)}
                  </Badge>
                </div>
              </div>
              <button
                onClick={() => deleteEmailMutation.mutate()}
                className="btn btn-danger"
                disabled={deleteEmailMutation.isPending}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 mb-4">
              <p className="text-sm">
                <span className="font-medium text-gray-700">Da:</span>{' '}
                <span className="text-gray-900">{email.mittente}</span>
              </p>
              <p className="text-sm">
                <span className="font-medium text-gray-700">A:</span>{' '}
                <span className="text-gray-900">{email.destinatario}</span>
              </p>
              <p className="text-sm">
                <span className="font-medium text-gray-700">Data:</span>{' '}
                <span className="text-gray-900">{formatDateTime(email.data_ricezione)}</span>
              </p>
            </div>

            <div className="border-t pt-4">
              <label className="label">Cambia Stato</label>
              <select
                value={email.status}
                onChange={(e) => updateStatusMutation.mutate(e.target.value as EmailStatus)}
                className="input"
                disabled={updateStatusMutation.isPending}
              >
                {Object.values(EmailStatus).map((status) => (
                  <option key={status} value={status}>
                    {getStatusLabel(status)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Email Body */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Contenuto</h2>
            {email.corpo_html ? (
              <div
                className="prose max-w-none"
                dangerouslySetInnerHTML={{ __html: email.corpo_html }}
              />
            ) : (
              <div className="whitespace-pre-wrap text-gray-700">{email.corpo_testo}</div>
            )}
          </div>

          {/* Attachments */}
          {email.allegati && email.allegati.length > 0 && (
            <div className="card">
              <h2 className="text-lg font-semibold mb-4">Allegati ({email.allegati.length})</h2>
              <div className="space-y-2">
                {email.allegati.map((allegato, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center">
                      <FileText className="w-5 h-5 text-gray-400 mr-3" />
                      <div>
                        <p className="font-medium text-sm">{allegato.filename}</p>
                        <p className="text-xs text-gray-500">
                          {(allegato.size / 1024).toFixed(2)} KB
                        </p>
                      </div>
                    </div>
                    <button className="btn btn-secondary btn-sm">
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Actions */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Azioni</h2>
            {actions && actions.length > 0 ? (
              <div className="space-y-3">
                {actions.map((action) => (
                  <div key={action.id} className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-medium text-sm">
                        {getActionTypeLabel(action.tipo_azione)}
                      </p>
                      <Badge className={getActionStateColor(action.stato)}>
                        {getActionStateLabel(action.stato)}
                      </Badge>
                    </div>
                    {action.stato === 'pending' && (
                      <button
                        onClick={() => executeActionMutation.mutate(action.id)}
                        disabled={executeActionMutation.isPending}
                        className="btn btn-primary w-full mt-2"
                      >
                        Esegui
                      </button>
                    )}
                    {action.errore && (
                      <p className="text-xs text-red-600 mt-2">{action.errore}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">Nessuna azione disponibile</p>
            )}
          </div>

          {/* Metadata */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Dettagli</h2>
            <dl className="space-y-2">
              <div>
                <dt className="text-sm font-medium text-gray-500">ID Messaggio</dt>
                <dd className="text-sm text-gray-900 break-all">{email.message_id}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Priorità</dt>
                <dd className="text-sm text-gray-900">{email.priorita}/10</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Tipo Account</dt>
                <dd className="text-sm text-gray-900">{email.account_type === 'pec' ? 'PEC' : 'Normale'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Creato</dt>
                <dd className="text-sm text-gray-900">{formatDateTime(email.created_at)}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}
