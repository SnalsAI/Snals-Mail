import { useState, useEffect } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import {
  Mail,
  ListChecks,
  Sliders,
  Calendar as CalendarIcon,
  School,
  Briefcase,
  Database,
  Shield,
  Settings,
  Menu,
  X,
  BookOpen,
  MessageSquare,
  Bug,
  Download,
  Smartphone,
  FileCheck,
  ChevronDown,
  ChevronRight,
  Cog,
  Users,
  BarChart3,
  Brain,
  Terminal
} from 'lucide-react'
import { usePWA } from '../hooks/usePWA'
import BugReporter from './BugReporter'

// Menu principale
const mainNavigation = [
  { name: 'Email', href: '/', icon: Mail },
  { name: 'Azioni', href: '/actions', icon: ListChecks },
  { name: 'Calendario', href: '/calendar', icon: CalendarIcon },
  { name: 'Interpelli', href: '/interpelli', icon: Briefcase },
  { name: 'Chat RAG', href: '/chat-rag', icon: MessageSquare },
  { name: 'Spam', href: '/spam', icon: Shield },
  { name: 'Ricevute PEC', href: '/ricevute-pec', icon: FileCheck },
  { name: 'Report', href: '/reports', icon: BarChart3 },
  { name: 'Bug Reports', href: '/bugs', icon: Bug },
]

// Sottomenu Configurazioni
const configNavigation = [
  { name: 'Impostazioni', href: '/settings', icon: Settings },
  { name: 'Regole', href: '/rules', icon: Sliders },
  { name: 'Delegati e Zone', href: '/delegati', icon: Users },
  { name: 'Scuole', href: '/schools', icon: School },
  { name: 'Classi Concorso', href: '/classi-concorso', icon: Briefcase },
  { name: 'Knowledge Base', href: '/knowledge', icon: BookOpen },
  { name: 'Documenti RAG', href: '/rag-documents', icon: Database },
  { name: 'NLP Training', href: '/nlp-training', icon: Brain },
  { name: 'Debug', href: '/debug', icon: Terminal },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [configOpen, setConfigOpen] = useState(false)
  const { canInstall, install, isInstalled } = usePWA()
  const location = useLocation()

  // Auto-expand config menu when navigating to a config route
  const isConfigRoute = configNavigation.some(item => location.pathname === item.href)

  useEffect(() => {
    if (isConfigRoute) {
      setConfigOpen(true)
    }
  }, [isConfigRoute])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile menu button */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-40 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mail className="w-6 h-6 text-primary-600" />
          <div>
            <h1 className="text-lg font-bold text-gray-900">SNALS</h1>
          </div>
        </div>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-lg hover:bg-gray-100"
        >
          {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200 z-50 transform transition-transform duration-200 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0
      `}>
        <div className="flex flex-col h-full">
          {/* Logo - nascosto su mobile perché è nella topbar */}
          <div className="hidden lg:flex items-center gap-2 px-6 py-4 border-b border-gray-200">
            <Mail className="w-8 h-8 text-primary-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-900">SNALS</h1>
              <p className="text-xs text-gray-500">Email Agent</p>
            </div>
          </div>

          {/* Mobile: spazio per la topbar */}
          <div className="lg:hidden h-14"></div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
            {/* Menu principale */}
            {mainNavigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                end={item.href === '/'}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`
                }
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </NavLink>
            ))}

            {/* Separatore */}
            <div className="my-3 border-t border-gray-200"></div>

            {/* Sottomenu Configurazioni */}
            <div>
              <button
                onClick={() => setConfigOpen(!configOpen)}
                className={`w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                  isConfigRoute
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Cog className="w-5 h-5" />
                  <span>Configurazioni</span>
                </div>
                {configOpen ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>

              {/* Sottovoci */}
              {configOpen && (
                <div className="mt-1 ml-4 space-y-1 border-l-2 border-gray-200 pl-3">
                  {configNavigation.map((item) => (
                    <NavLink
                      key={item.name}
                      to={item.href}
                      onClick={() => setSidebarOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center gap-3 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                          isActive
                            ? 'bg-primary-50 text-primary-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                        }`
                      }
                    >
                      <item.icon className="w-4 h-4" />
                      {item.name}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200 space-y-3">
            {/* Pulsante Installa App PWA */}
            {canInstall && !isInstalled && (
              <button
                onClick={install}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
              >
                <Download className="w-5 h-5" />
                Installa App
              </button>
            )}

            {/* Mostra se già installata */}
            {isInstalled && (
              <div className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded-lg text-sm font-medium">
                <Smartphone className="w-4 h-4" />
                App Installata
              </div>
            )}

            <p className="text-xs text-gray-500 text-center">
              v0.1.0 - Powered by Ollama LLM
            </p>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64 pt-14 lg:pt-0">
        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>

      {/* Bug Reporter - Floating button */}
      <BugReporter />
    </div>
  )
}
