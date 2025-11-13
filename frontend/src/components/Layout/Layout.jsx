import { Outlet, Link, useLocation } from 'react-router-dom';
import { Home, Mail, Calendar, Settings, FileText, Zap } from 'lucide-react';

export default function Layout() {
  const location = useLocation();

  const navItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/emails', icon: Mail, label: 'Email' },
    { path: '/calendario', icon: Calendar, label: 'Calendario' },
    { path: '/regole', icon: Zap, label: 'Regole' },
    { path: '/repository', icon: FileText, label: 'Repository' },
    { path: '/config', icon: Settings, label: 'Configurazione' },
  ];

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <aside className="w-64 bg-white shadow-md">
        <div className="p-4 border-b">
          <h1 className="text-xl font-bold text-blue-600">SNALS Email Agent</h1>
          <p className="text-sm text-gray-500">Gestione automatica email</p>
        </div>

        <nav className="p-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
