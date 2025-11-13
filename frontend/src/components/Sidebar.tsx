import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Mail,
  Calendar,
  FileText,
  CheckSquare,
  Settings,
  Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { name: 'Email', to: '/emails', icon: Mail },
  { name: 'Calendario', to: '/calendar', icon: Calendar },
  { name: 'Regole', to: '/rules', icon: FileText },
  { name: 'Documenti', to: '/documents', icon: Sparkles },
  { name: 'Azioni', to: '/actions', icon: CheckSquare },
  { name: 'Impostazioni', to: '/settings', icon: Settings },
]

export default function Sidebar() {
  return (
    <div className="flex flex-col w-64 bg-white border-r border-gray-200">
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b border-gray-200">
        <h1 className="text-xl font-bold text-primary-600">SNALS Agent</h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-700 hover:bg-gray-100'
              )
            }
          >
            <item.icon className="w-5 h-5 mr-3" />
            {item.name}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          SNALS Email Agent v0.1.0
        </p>
      </div>
    </div>
  )
}
