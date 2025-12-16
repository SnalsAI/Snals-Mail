import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2, AlertTriangle, Shield, Server, Database, ChevronDown, ChevronRight, History, CheckCircle } from 'lucide-react'
import { spamApi, systemSettingsApi } from '../lib/api'

interface SpamEmail {
  id: number
  mittente: string
  oggetto: string
  data_ricezione: string
  corpo_testo: string
  data_eliminazione?: string
}

export default function Spam() {
  const queryClient = useQueryClient()
  const [expandedEmailId, setExpandedEmailId] = useState<number | null>(null)
  const [autoDeleteEnabled, setAutoDeleteEnabled] = useState(false)
  const [showDeletedHistory, setShowDeletedHistory] = useState(false)

  // Carica impostazione auto-delete
  const { data: settingsData } = useQuery({
    queryKey: ['system-settings'],
    queryFn: () => systemSettingsApi.getAll().then(res => res.data)
  })

  // Carica email spam
  const { data: spamData, isLoading } = useQuery({
    queryKey: ['spam-emails'],
    queryFn: () => spamApi.getAll().then(res => res.data)
  })

  // Carica email spam eliminate (storico)
  const { data: deletedData, isLoading: isLoadingDeleted } = useQuery({
    queryKey: ['spam-deleted'],
    queryFn: () => spamApi.getDeleted().then(res => res.data),
    enabled: showDeletedHistory
  })

  // Carica statistiche
  const { data: statsData } = useQuery({
    queryKey: ['spam-stats'],
    queryFn: () => spamApi.getStats().then(res => res.data)
  })

  const spamEmails: SpamEmail[] = spamData?.emails || []
  const deletedEmails: SpamEmail[] = deletedData?.emails || []
  const totalSpam = statsData?.total_spam || 0
  const totalDeleted = statsData?.total_deleted || 0

  // Aggiorna auto-delete setting
  const updateAutoDeleteMutation = useMutation({
    mutationFn: (enabled: boolean) =>
      systemSettingsApi.update('auto_delete_spam', enabled.toString()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] })
    }
  })

  // Elimina singola email dal server
  const deleteFromServerMutation = useMutation({
    mutationFn: (_emailId: number) =>
      spamApi.deleteFromServer(_emailId),
    onMutate: async (emailId) => {
      // Cancella query precedenti
      await queryClient.cancelQueries({ queryKey: ['spam-emails'] })
      await queryClient.cancelQueries({ queryKey: ['spam-stats'] })

      // Snapshot dello stato precedente
      const previousEmails = queryClient.getQueryData(['spam-emails'])
      const previousStats = queryClient.getQueryData(['spam-stats'])

      // Aggiorna optimistically rimuovendo l'email dalla lista
      queryClient.setQueryData(['spam-emails'], (old: any) => {
        if (!old) return old
        return {
          ...old,
          emails: old.emails.filter((e: SpamEmail) => e.id !== emailId),
          total: Math.max(0, (old.total || old.emails.length) - 1)
        }
      })

      // Aggiorna anche le stats
      queryClient.setQueryData(['spam-stats'], (old: any) => {
        if (!old) return old
        return {
          ...old,
          total_spam: Math.max(0, (old.total_spam || 0) - 1),
          total_deleted: (old.total_deleted || 0) + 1
        }
      })

      // Ritorna context per rollback in caso di errore
      return { previousEmails, previousStats }
    },
    onError: (_err, _emailId, context) => {
      // Rollback in caso di errore
      if (context?.previousEmails) {
        queryClient.setQueryData(['spam-emails'], context.previousEmails)
      }
      if (context?.previousStats) {
        queryClient.setQueryData(['spam-stats'], context.previousStats)
      }
      console.error('Errore eliminazione spam:', _err)
      alert('Errore durante l\'eliminazione dal server')
    },
    onSettled: () => {
      // Ricarica dati per sicurezza dopo successo o errore
      queryClient.invalidateQueries({ queryKey: ['spam-emails'] })
      queryClient.invalidateQueries({ queryKey: ['spam-stats'] })
      queryClient.invalidateQueries({ queryKey: ['spam-deleted'] })
    }
  })

  // Elimina tutte le email dal server
  const deleteAllFromServerMutation = useMutation({
    mutationFn: () =>
      spamApi.deleteAllFromServer(),
    onMutate: async () => {
      // Cancella query precedenti
      await queryClient.cancelQueries({ queryKey: ['spam-emails'] })

      // Snapshot dello stato precedente
      const previousEmails = queryClient.getQueryData(['spam-emails'])

      // Aggiorna optimistically svuotando la lista
      queryClient.setQueryData(['spam-emails'], (old: any) => {
        if (!old) return old
        return {
          ...old,
          emails: []
        }
      })

      // Ritorna context per rollback in caso di errore
      return { previousEmails }
    },
    onError: (_err, _variables, context) => {
      // Rollback in caso di errore
      if (context?.previousEmails) {
        queryClient.setQueryData(['spam-emails'], context.previousEmails)
      }
      alert('Errore durante l\'eliminazione dal server')
    },
    onSettled: async () => {
      // Ricarica dati per sicurezza
      await queryClient.invalidateQueries({ queryKey: ['spam-emails'] })
      await queryClient.invalidateQueries({ queryKey: ['spam-stats'] })
      await queryClient.invalidateQueries({ queryKey: ['spam-deleted'] })
    }
  })

  // Segna come non spam
  const unmarkAsSpamMutation = useMutation({
    mutationFn: ({ emailId: _emailId, newCategoria }: { emailId: number; newCategoria: string }) =>
      spamApi.unmarkAsSpam(_emailId, newCategoria),
    onMutate: async ({ emailId }) => {
      await queryClient.cancelQueries({ queryKey: ['spam-emails'] })
      await queryClient.cancelQueries({ queryKey: ['spam-stats'] })

      const previousEmails = queryClient.getQueryData(['spam-emails'])
      const previousStats = queryClient.getQueryData(['spam-stats'])

      // Rimuovi email dalla lista spam ottimisticamente
      queryClient.setQueryData(['spam-emails'], (old: any) => {
        if (!old) return old
        return {
          ...old,
          emails: old.emails.filter((e: SpamEmail) => e.id !== emailId),
          total: Math.max(0, (old.total || old.emails.length) - 1)
        }
      })

      queryClient.setQueryData(['spam-stats'], (old: any) => {
        if (!old) return old
        return {
          ...old,
          total_spam: Math.max(0, (old.total_spam || 0) - 1)
        }
      })

      return { previousEmails, previousStats }
    },
    onError: (_err, _variables, context) => {
      if (context?.previousEmails) {
        queryClient.setQueryData(['spam-emails'], context.previousEmails)
      }
      if (context?.previousStats) {
        queryClient.setQueryData(['spam-stats'], context.previousStats)
      }
      console.error('Errore rimozione spam:', _err)
      alert('Errore durante la rimozione da spam')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['spam-emails'] })
      queryClient.invalidateQueries({ queryKey: ['spam-stats'] })
      queryClient.invalidateQueries({ queryKey: ['emails'] })
    }
  })

  const handleDeleteFromServer = (emailId: number) => {
    if (confirm('Vuoi eliminare questa email dal server di posta? L\'email verrà conservata nello storico.')) {
      deleteFromServerMutation.mutate(emailId)
    }
  }

  const handleUnmarkAsSpam = (emailId: number) => {
    if (confirm('Vuoi segnare questa email come NON spam? Verrà spostata nella categoria "altro".')) {
      unmarkAsSpamMutation.mutate({ emailId, newCategoria: 'altro' })
    }
  }

  const handleDeleteAllFromServer = () => {
    if (confirm(`Sei sicuro di voler eliminare TUTTE le ${totalSpam} email spam dal server? Le email verranno conservate nello storico.`)) {
      deleteAllFromServerMutation.mutate()
    }
  }

  const handleToggleAutoDelete = () => {
    const newValue = !autoDeleteEnabled
    setAutoDeleteEnabled(newValue)
    updateAutoDeleteMutation.mutate(newValue)
  }

  // Sincronizza auto-delete con settings
  useState(() => {
    if (settingsData?.settings) {
      const autoDeleteSetting = settingsData.settings.find((s: any) => s.key === 'auto_delete_spam')
      if (autoDeleteSetting) {
        setAutoDeleteEnabled(autoDeleteSetting.value === 'true')
      }
    }
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Shield className="w-8 h-8 text-red-600" />
            Gestione Spam
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Controlla e elimina le email categorizzate come spam
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Spam */}
        <div className="card bg-gradient-to-br from-red-50 to-white border-l-4 border-l-red-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Email Spam</p>
              <p className="text-3xl font-bold text-red-600 mt-1">{totalSpam}</p>
            </div>
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-red-600" />
            </div>
          </div>
        </div>

        {/* Total Deleted */}
        <div className="card bg-gradient-to-br from-gray-50 to-white border-l-4 border-l-gray-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Eliminate</p>
              <p className="text-3xl font-bold text-gray-600 mt-1">{totalDeleted}</p>
            </div>
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
              <History className="w-6 h-6 text-gray-600" />
            </div>
          </div>
        </div>

        {/* Auto-Delete Status */}
        <div className="card bg-gradient-to-br from-blue-50 to-white border-l-4 border-l-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Auto-Eliminazione</p>
              <p className="text-lg font-semibold text-blue-600 mt-1">
                {autoDeleteEnabled ? '✅ Attiva' : '❌ Disattiva'}
              </p>
            </div>
            <button
              onClick={handleToggleAutoDelete}
              disabled={updateAutoDeleteMutation.isPending}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                autoDeleteEnabled ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  autoDeleteEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="card bg-gradient-to-br from-orange-50 to-white border-l-4 border-l-orange-500">
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-600">Azioni Bulk</p>
            <button
              onClick={handleDeleteAllFromServer}
              disabled={deleteAllFromServerMutation.isPending || totalSpam === 0}
              className="w-full px-4 py-2 bg-gradient-to-r from-red-600 to-red-700 text-white rounded-lg hover:from-red-700 hover:to-red-800 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium shadow-md text-sm"
            >
              <Server className="w-4 h-4" />
              {deleteAllFromServerMutation.isPending ? 'Eliminazione...' : 'Elimina Tutto'}
            </button>
          </div>
        </div>
      </div>

      {/* Spam List */}
      <div className="card p-0 overflow-hidden shadow-lg">
        <div className="px-6 py-4 bg-gradient-to-r from-red-100 via-red-50 to-red-100 border-b-2 border-red-200">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <Database className="w-5 h-5 text-red-600" />
            Email Spam da Eliminare ({spamEmails.length})
          </h2>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-red-600 border-t-transparent"></div>
            <p className="mt-4 text-gray-500 font-medium">Caricamento spam...</p>
          </div>
        ) : spamEmails.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {spamEmails.map((email) => {
              const isExpanded = expandedEmailId === email.id

              return (
                <div
                  key={email.id}
                  className="p-4 hover:bg-red-50/30 transition-colors border-l-4 border-l-red-400"
                >
                  {/* Email Header */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <button
                          onClick={() => setExpandedEmailId(isExpanded ? null : email.id)}
                          className="text-gray-400 hover:text-red-600 transition-colors"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                        </button>
                        <h3 className="text-sm font-semibold text-gray-900 truncate">
                          {email.oggetto}
                        </h3>
                      </div>
                      <p className="text-xs text-gray-600 ml-6">
                        Da: <span className="font-medium">{email.mittente}</span>
                      </p>
                      <p className="text-xs text-gray-500 ml-6">
                        {new Date(email.data_ricezione).toLocaleString('it-IT', { timeZone: 'Europe/Rome' })}
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleUnmarkAsSpam(email.id)}
                        disabled={unmarkAsSpamMutation.isPending}
                        className="px-3 py-1.5 text-sm bg-gradient-to-r from-green-600 to-green-700 text-white rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-150 disabled:opacity-50 flex items-center gap-1.5 font-medium shadow-md"
                        title="Segna come non spam"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Non Spam</span>
                      </button>
                      <button
                        onClick={() => handleDeleteFromServer(email.id)}
                        disabled={deleteFromServerMutation.isPending}
                        className="px-3 py-1.5 text-sm bg-gradient-to-r from-red-600 to-red-700 text-white rounded-lg hover:from-red-700 hover:to-red-800 transition-all duration-150 disabled:opacity-50 flex items-center gap-1.5 font-medium shadow-md"
                        title="Elimina dal server"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Elimina</span>
                      </button>
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="mt-3 ml-6 p-4 bg-white/60 backdrop-blur-sm rounded-lg border border-gray-200">
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">
                        {email.corpo_testo?.substring(0, 500) || 'Nessun contenuto'}
                        {email.corpo_testo && email.corpo_testo.length > 500 ? '...' : ''}
                      </p>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="text-center py-16 bg-gradient-to-br from-gray-50 to-white">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
              <Shield className="w-8 h-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-1">Nessuna email spam</h3>
            <p className="text-gray-500 text-sm">Ottimo! La tua casella è pulita</p>
          </div>
        )}
      </div>

      {/* Deleted History Section */}
      <div className="card p-0 overflow-hidden shadow-lg">
        <button
          onClick={() => setShowDeletedHistory(!showDeletedHistory)}
          className="w-full px-6 py-4 bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border-b-2 border-gray-200 flex items-center justify-between hover:bg-gray-100 transition-colors"
        >
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <History className="w-5 h-5 text-gray-600" />
            Storico Email Eliminate ({totalDeleted})
          </h2>
          <ChevronDown className={`w-5 h-5 text-gray-500 transition-transform ${showDeletedHistory ? 'rotate-180' : ''}`} />
        </button>

        {showDeletedHistory && (
          <>
            {isLoadingDeleted ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-gray-600 border-t-transparent"></div>
                <p className="mt-3 text-gray-500 text-sm">Caricamento storico...</p>
              </div>
            ) : deletedEmails.length > 0 ? (
              <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                {deletedEmails.map((email) => (
                  <div
                    key={email.id}
                    className="p-4 bg-gray-50/50 border-l-4 border-l-gray-300"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-gray-700 truncate">
                          {email.oggetto}
                        </h3>
                        <p className="text-xs text-gray-500 mt-1">
                          Da: {email.mittente}
                        </p>
                        <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                          <span>
                            Ricevuta: {new Date(email.data_ricezione).toLocaleDateString('it-IT', { timeZone: 'Europe/Rome' })}
                          </span>
                          {email.data_eliminazione && (
                            <span className="text-red-500">
                              🗑️ Eliminata: {new Date(email.data_eliminazione).toLocaleString('it-IT', { timeZone: 'Europe/Rome' })}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 bg-gray-50">
                <History className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Nessuna email spam eliminata</p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Info Box */}
      <div className="card bg-blue-50 border-l-4 border-l-blue-500">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900">
            <p className="font-semibold mb-1">ℹ️ Informazioni</p>
            <ul className="space-y-1 text-blue-800">
              <li>• <strong>Auto-Eliminazione:</strong> Se attivata, le email spam vengono eliminate automaticamente dal server dopo la categorizzazione</li>
              <li>• <strong>Elimina dal Server:</strong> Rimuove l'email dal server di posta ma la conserva nello storico</li>
              <li>• <strong>Storico:</strong> Le email eliminate rimangono visibili nello storico per riferimento</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
