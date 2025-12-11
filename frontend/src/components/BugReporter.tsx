import { useState, useEffect } from 'react'
import { Bug, X, Send, AlertTriangle, CheckCircle } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'

interface ConsoleError {
  message: string
  timestamp: string
  type: string
}

interface BugReportData {
  descrizione: string
  pagina: string
  componente: string | null
  browser: string
  viewport: string
  console_errors: ConsoleError[]
  network_errors: any[]
  email_id: number | null
  azione_id: number | null
}

export default function BugReporter() {
  const [isOpen, setIsOpen] = useState(false)
  const [descrizione, setDescrizione] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [consoleErrors, setConsoleErrors] = useState<ConsoleError[]>([])
  const [submitted, setSubmitted] = useState(false)
  const location = useLocation()

  // Cattura errori console
  useEffect(() => {
    const originalError = console.error
    const errors: ConsoleError[] = []

    console.error = (...args) => {
      errors.push({
        message: args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '),
        timestamp: new Date().toISOString(),
        type: 'error'
      })
      // Mantieni solo ultimi 10 errori
      if (errors.length > 10) errors.shift()
      setConsoleErrors([...errors])
      originalError.apply(console, args)
    }

    return () => {
      console.error = originalError
    }
  }, [])

  const collectContextData = (): Omit<BugReportData, 'descrizione'> => {
    // Estrai email_id o azione_id dalla URL se presente
    let email_id: number | null = null
    let azione_id: number | null = null

    const emailMatch = location.pathname.match(/\/emails?\/(\d+)/)
    if (emailMatch) email_id = parseInt(emailMatch[1])

    const actionMatch = location.pathname.match(/\/azioni?\/(\d+)/)
    if (actionMatch) azione_id = parseInt(actionMatch[1])

    return {
      pagina: location.pathname + location.search,
      componente: document.querySelector('[data-component]')?.getAttribute('data-component') || null,
      browser: navigator.userAgent,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      console_errors: consoleErrors.slice(-5), // Ultimi 5 errori
      network_errors: [], // TODO: implementare intercettazione fetch
      email_id,
      azione_id
    }
  }

  const handleSubmit = async () => {
    if (!descrizione.trim()) {
      toast.error('Descrivi il problema riscontrato')
      return
    }

    setIsSubmitting(true)

    const contextData = collectContextData()
    const bugReport: BugReportData = {
      descrizione: descrizione.trim(),
      ...contextData
    }

    try {
      const response = await fetch('/api/bugs/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bugReport)
      })

      if (response.ok) {
        setSubmitted(true)
        setTimeout(() => {
          setIsOpen(false)
          setSubmitted(false)
          setDescrizione('')
        }, 2000)
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Errore nel salvataggio')
      }
    } catch (error) {
      toast.error('Errore di connessione')
      console.error('Bug report error:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 p-4 bg-red-500 hover:bg-red-600 text-white rounded-full shadow-lg transition-all hover:scale-110 group"
        title="Segnala un bug"
      >
        <Bug className="w-6 h-6" />
        <span className="absolute right-full mr-3 top-1/2 -translate-y-1/2 bg-gray-900 text-white text-sm px-3 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
          Segnala un bug
        </span>
      </button>

      {/* Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden">
            {/* Header */}
            <div className="bg-red-500 text-white px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Bug className="w-6 h-6" />
                <h2 className="text-lg font-semibold">Segnala un Bug</h2>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-red-600 rounded transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="p-6">
              {submitted ? (
                <div className="text-center py-8">
                  <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    Bug segnalato!
                  </h3>
                  <p className="text-gray-600">
                    Grazie per la segnalazione. Il problema verrà analizzato e risolto.
                  </p>
                </div>
              ) : (
                <>
                  {/* Descrizione */}
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Descrivi il problema *
                    </label>
                    <textarea
                      value={descrizione}
                      onChange={(e) => setDescrizione(e.target.value)}
                      placeholder="Cosa stavi facendo? Cosa ti aspettavi che succedesse? Cosa è successo invece?"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                      rows={5}
                      autoFocus
                    />
                  </div>

                  {/* Context Info */}
                  <div className="bg-gray-50 rounded-lg p-4 mb-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-500" />
                      Dati raccolti automaticamente
                    </h4>
                    <div className="text-xs text-gray-500 space-y-1">
                      <p><span className="font-medium">Pagina:</span> {location.pathname}</p>
                      <p><span className="font-medium">Viewport:</span> {window.innerWidth}x{window.innerHeight}</p>
                      {consoleErrors.length > 0 && (
                        <p className="text-red-600">
                          <span className="font-medium">Errori console:</span> {consoleErrors.length} rilevati
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Console Errors Preview */}
                  {consoleErrors.length > 0 && (
                    <div className="mb-4">
                      <details className="text-xs">
                        <summary className="text-gray-600 cursor-pointer hover:text-gray-900">
                          Mostra errori console ({consoleErrors.length})
                        </summary>
                        <div className="mt-2 bg-red-50 p-2 rounded max-h-32 overflow-auto">
                          {consoleErrors.slice(-3).map((err, i) => (
                            <div key={i} className="text-red-700 mb-1 truncate">
                              {err.message.substring(0, 100)}...
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-3">
                    <button
                      onClick={() => setIsOpen(false)}
                      className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      Annulla
                    </button>
                    <button
                      onClick={handleSubmit}
                      disabled={isSubmitting || !descrizione.trim()}
                      className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {isSubmitting ? (
                        <>
                          <span className="animate-spin">⏳</span>
                          Invio...
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          Invia segnalazione
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
