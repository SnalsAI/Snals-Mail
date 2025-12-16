import { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.setState({ errorInfo })
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-red-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl w-full">
            <h1 className="text-2xl font-bold text-red-600 mb-4">Errore nell'applicazione</h1>
            <div className="bg-red-100 rounded p-4 mb-4">
              <p className="font-mono text-sm text-red-800 break-all">
                {this.state.error?.toString()}
              </p>
            </div>
            {this.state.errorInfo && (
              <details className="bg-gray-100 rounded p-4">
                <summary className="cursor-pointer font-medium text-gray-700">Stack trace</summary>
                <pre className="mt-2 text-xs text-gray-600 overflow-auto max-h-64">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Ricarica pagina
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
