import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Filter, Mail } from 'lucide-react';
import { emailService } from '../services/emailService';
import { format } from 'date-fns';
import { it } from 'date-fns/locale';

export default function EmailsPage() {
  const [filters, setFilters] = useState({
    categoria: '',
    search: '',
  });
  const [selectedEmail, setSelectedEmail] = useState(null);

  const { data: emails, isLoading } = useQuery({
    queryKey: ['emails', filters],
    queryFn: () => emailService.getEmails(filters),
  });

  const categorie = [
    { value: '', label: 'Tutte' },
    { value: 'info_generiche', label: 'Info Generiche' },
    { value: 'richiesta_appuntamento', label: 'Appuntamenti' },
    { value: 'richiesta_tesseramento', label: 'Tesseramento' },
    { value: 'convocazione_scuola', label: 'Convocazioni' },
    { value: 'comunicazione_ust_usr', label: 'UST/USR' },
    { value: 'comunicazione_scuola', label: 'Comunicazioni Scuole' },
    { value: 'comunicazione_snals_centrale', label: 'SNALS Centrale' },
    { value: 'varie', label: 'Varie' },
  ];

  const getCategoryColor = (categoria) => {
    const colors = {
      info_generiche: 'bg-blue-100 text-blue-800',
      richiesta_appuntamento: 'bg-green-100 text-green-800',
      richiesta_tesseramento: 'bg-purple-100 text-purple-800',
      convocazione_scuola: 'bg-red-100 text-red-800',
      comunicazione_ust_usr: 'bg-orange-100 text-orange-800',
      comunicazione_scuola: 'bg-yellow-100 text-yellow-800',
      comunicazione_snals_centrale: 'bg-indigo-100 text-indigo-800',
      varie: 'bg-gray-100 text-gray-800',
    };
    return colors[categoria] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="flex h-full">
      {/* Lista Email */}
      <div className="w-1/3 border-r bg-white overflow-auto">
        <div className="p-4 border-b sticky top-0 bg-white z-10">
          <h1 className="text-2xl font-bold mb-4">Email</h1>

          {/* Filtri */}
          <div className="space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Cerca email..."
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              />
            </div>

            <select
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={filters.categoria}
              onChange={(e) => setFilters({ ...filters, categoria: e.target.value })}
            >
              {categorie.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Lista */}
        <div className="divide-y">
          {isLoading ? (
            <div className="p-4 text-center text-gray-500">Caricamento...</div>
          ) : emails?.length === 0 ? (
            <div className="p-4 text-center text-gray-500">Nessuna email trovata</div>
          ) : (
            emails?.map((email) => (
              <div
                key={email.id}
                className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                  selectedEmail?.id === email.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                }`}
                onClick={() => setSelectedEmail(email)}
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="font-medium text-gray-900">{email.mittente}</span>
                  <span className="text-xs text-gray-500">
                    {format(new Date(email.data_ricezione), 'dd MMM', { locale: it })}
                  </span>
                </div>
                <p className="text-sm font-medium text-gray-700 mb-1">{email.oggetto}</p>
                <span className={`text-xs px-2 py-1 rounded-full ${getCategoryColor(email.categoria)}`}>
                  {email.categoria?.replace('_', ' ')}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Dettaglio Email */}
      <div className="flex-1 bg-gray-50 overflow-auto">
        {selectedEmail ? (
          <EmailDetail email={selectedEmail} />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <Mail size={64} className="mx-auto mb-4 text-gray-300" />
              <p>Seleziona un'email per visualizzare i dettagli</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EmailDetail({ email }) {
  const { data, isLoading } = useQuery({
    queryKey: ['email', email.id],
    queryFn: () => emailService.getEmail(email.id),
  });

  if (isLoading) return <div className="p-8">Caricamento...</div>;

  return (
    <div className="p-8">
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-2xl font-bold mb-4">{data.oggetto}</h2>

        <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
          <div>
            <span className="text-gray-600">Da:</span>
            <span className="ml-2 font-medium">{data.mittente}</span>
          </div>
          <div>
            <span className="text-gray-600">Data:</span>
            <span className="ml-2">
              {format(new Date(data.data_ricezione), 'dd MMMM yyyy HH:mm', { locale: it })}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Categoria:</span>
            <span className="ml-2 font-medium">{data.categoria}</span>
          </div>
          <div>
            <span className="text-gray-600">Confidence:</span>
            <span className="ml-2">{(data.categoria_confidence * 100).toFixed(0)}%</span>
          </div>
        </div>

        <div className="border-t pt-4">
          <h3 className="font-semibold mb-2">Corpo:</h3>
          <div className="whitespace-pre-wrap text-gray-700">{data.corpo}</div>
        </div>
      </div>

      {/* Interpretazione */}
      {data.interpretazione && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-xl font-semibold mb-4">Interpretazione</h3>
          <pre className="bg-gray-50 p-4 rounded overflow-auto text-sm">
            {JSON.stringify(data.interpretazione.interpretazione_json, null, 2)}
          </pre>
        </div>
      )}

      {/* Azioni */}
      {data.azioni?.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-semibold mb-4">Azioni Eseguite</h3>
          <div className="space-y-3">
            {data.azioni.map((azione) => (
              <div key={azione.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded">
                <span className="font-medium">{azione.tipo}</span>
                <span className={`text-sm px-2 py-1 rounded ${
                  azione.stato === 'completata' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {azione.stato}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
