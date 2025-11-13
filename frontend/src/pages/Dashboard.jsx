import { useQuery } from '@tanstack/react-query';
import { Mail, TrendingUp, Clock, CheckCircle } from 'lucide-react';
import { emailService } from '../services/emailService';

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['email-stats'],
    queryFn: emailService.getStats,
    refetchInterval: 30000, // Refresh ogni 30s
  });

  if (isLoading) {
    return <div className="p-8">Caricamento...</div>;
  }

  const kpis = [
    {
      title: 'Email Oggi',
      value: stats?.today || 0,
      icon: Mail,
      color: 'blue',
    },
    {
      title: 'In Elaborazione',
      value: stats?.processing || 0,
      icon: Clock,
      color: 'yellow',
    },
    {
      title: 'Completate',
      value: stats?.completed || 0,
      icon: CheckCircle,
      color: 'green',
    },
    {
      title: 'Questa Settimana',
      value: stats?.week || 0,
      icon: TrendingUp,
      color: 'purple',
    },
  ];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Panoramica attività email</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div key={kpi.title} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-lg bg-${kpi.color}-100`}>
                  <Icon className={`text-${kpi.color}-600`} size={24} />
                </div>
              </div>
              <h3 className="text-gray-600 text-sm font-medium">{kpi.title}</h3>
              <p className="text-3xl font-bold text-gray-900 mt-2">{kpi.value}</p>
            </div>
          );
        })}
      </div>

      {/* Categorie Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Distribuzione Categorie</h2>
          <div className="space-y-3">
            {stats?.categories?.map((cat) => (
              <div key={cat.name} className="flex items-center">
                <div className="flex-1">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">{cat.name}</span>
                    <span className="text-sm text-gray-500">{cat.count}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${(cat.count / stats.total) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Stream Attività */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Attività Recenti</h2>
          <div className="space-y-4">
            {stats?.recent_activities?.map((activity, idx) => (
              <div key={idx} className="flex items-start gap-3 border-l-2 border-blue-500 pl-3">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                  <p className="text-xs text-gray-500">{activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
