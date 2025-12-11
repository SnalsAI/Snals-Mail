import { X, CheckCircle, AlertCircle, Info, Clock } from 'lucide-react'

interface LogStep {
  timestamp: string
  step: string
  level: string
  details?: any
}

interface ProcessLogModalProps {
  isOpen: boolean
  onClose: () => void
  log: LogStep[]
  emailId?: number
  success?: boolean
  error?: string
}

export default function ProcessLogModal({
  isOpen,
  onClose,
  log,
  emailId,
  success,
  error
}: ProcessLogModalProps) {
  if (!isOpen) return null

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />
      default:
        return <Info className="w-5 h-5 text-blue-500" />
    }
  }

  const getLogBgColor = (level: string) => {
    switch (level) {
      case 'success':
        return 'bg-green-50 border-green-200'
      case 'error':
        return 'bg-red-50 border-red-200'
      case 'warning':
        return 'bg-yellow-50 border-yellow-200'
      default:
        return 'bg-blue-50 border-blue-200'
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Log Processamento Email
            </h2>
            {emailId && (
              <p className="text-sm text-gray-500 mt-1">
                Email ID: #{emailId}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-gray-500" />
          </button>
        </div>

        {/* Status Banner */}
        {(success !== undefined || error) && (
          <div className={`p-4 ${success ? 'bg-green-50' : 'bg-red-50'}`}>
            <div className="flex items-center gap-3">
              {success ? (
                <CheckCircle className="w-6 h-6 text-green-500" />
              ) : (
                <AlertCircle className="w-6 h-6 text-red-500" />
              )}
              <div>
                <p className={`font-medium ${success ? 'text-green-800' : 'text-red-800'}`}>
                  {success ? 'Processamento completato con successo!' : 'Errore durante il processamento'}
                </p>
                {error && (
                  <p className="text-sm text-red-600 mt-1">{error}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Log Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-3">
            {log.length === 0 ? (
              <div className="text-center py-12">
                <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">Nessun log disponibile</p>
              </div>
            ) : (
              log.map((step, index) => (
                <div
                  key={index}
                  className={`border rounded-lg p-4 ${getLogBgColor(step.level)}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{getLogIcon(step.level)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <h4 className="font-semibold text-gray-900">
                          {step.step}
                        </h4>
                        <span className="text-xs text-gray-500 whitespace-nowrap">
                          {new Date(step.timestamp).toLocaleTimeString('it-IT')}
                        </span>
                      </div>

                      {step.details && (
                        <div className="mt-2">
                          <pre className="text-sm bg-white bg-opacity-50 p-3 rounded border border-gray-200 overflow-x-auto">
                            {JSON.stringify(step.details, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="btn-primary w-full"
          >
            Chiudi
          </button>
        </div>
      </div>
    </div>
  )
}
