import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Mail, Calendar as CalendarIcon, Paperclip, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { emailsApi } from '../lib/api'
import { EmailCategory } from '../types'

export default function EmailDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: email, isLoading } = useQuery({
    queryKey: ['email', id],
    queryFn: () => emailsApi.getById(Number(id)).then(res => res.data),
    enabled: !!id,
  })

  const updateCategoriaMutation = useMutation({
    mutationFn: ({ categoria }: { categoria: string }) =>
      emailsApi.updateCategoria(Number(id), categoria),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email', id] })
      toast.success('Categoria aggiornata')
    },
    onError: () => {
      toast.error('Errore nell\'aggiornamento della categoria')
    },
  })

  const markAsReadMutation = useMutation({
    mutationFn: () => emailsApi.markAsRead(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email', id] })
      toast.success('Email segnata come revisionata')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => emailsApi.delete(Number(id)),
    onSuccess: () => {
      toast.success('Email eliminata')
      navigate('/emails')
    },
    onError: () => {
      toast.error('Errore nell\'eliminazione dell\'email')
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!email) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Email non trovata</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/emails')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-5 h-5" />
          Torna alle email
        </button>
        <div className="flex items-center gap-2">
          {email.richiede_revisione && !email.revisionata && (
            <button
              onClick={() => markAsReadMutation.mutate()}
              className="btn-primary"
              disabled={markAsReadMutation.isPending}
            >
              Segna come Revisionata
            </button>
          )}
          <button
            onClick={() => {
              if (confirm('Sei sicuro di voler eliminare questa email?')) {
                deleteMutation.mutate()
              }
            }}
            className="btn-danger"
            disabled={deleteMutation.isPending}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Email Content */}
      <div className="card">
        <div className="space-y-6">
          {/* Subject */}
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{email.oggetto}</h1>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm font-medium text-gray-500">Da</p>
              <p className="text-sm text-gray-900">{email.mittente}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">A</p>
              <p className="text-sm text-gray-900">{email.destinatario}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Data Ricezione</p>
              <p className="text-sm text-gray-900">
                {new Date(email.data_ricezione).toLocaleString('it-IT')}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Account</p>
              <p className="text-sm text-gray-900">{email.account_type}</p>
            </div>
          </div>

          {/* Category */}
          <div>
            <label className="label">Categoria</label>
            <div className="flex items-center gap-2">
              <select
                className="input flex-1"
                value={email.categoria || ''}
                onChange={(e) =>
                  updateCategoriaMutation.mutate({ categoria: e.target.value })
                }
                disabled={updateCategoriaMutation.isPending}
              >
                <option value="">Non categorizzata</option>
                {Object.values(EmailCategory).map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
              {email.categoria_confidence && (
                <span className="text-sm text-gray-500">
                  Confidenza: {(email.categoria_confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>

          {/* Body */}
          <div>
            <label className="label">Contenuto</label>
            <div className="p-4 bg-gray-50 rounded-lg whitespace-pre-wrap text-sm">
              {email.corpo}
            </div>
          </div>

          {/* Attachments */}
          {email.allegati_nomi && email.allegati_nomi.length > 0 && (
            <div>
              <label className="label flex items-center gap-2">
                <Paperclip className="w-4 h-4" />
                Allegati ({email.allegati_nomi.length})
              </label>
              <div className="space-y-2">
                {email.allegati_nomi.map((nome, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg"
                  >
                    <Paperclip className="w-4 h-4 text-gray-500" />
                    <span className="text-sm text-gray-900">{nome}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Status badges */}
          <div className="flex items-center gap-2">
            <span className="badge-primary">{email.stato}</span>
            {email.richiede_revisione && (
              <span className="badge-warning">Richiede revisione</span>
            )}
            {email.revisionata && (
              <span className="badge-success">Revisionata</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
