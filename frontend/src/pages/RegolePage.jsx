import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit, Trash2, Power, TestTube } from 'lucide-react';
import apiClient from '../services/api';

export default function RegolePage() {
  const [showModal, setShowModal] = useState(false);
  const [editingRegola, setEditingRegola] = useState(null);
  const queryClient = useQueryClient();

  const { data: regole, isLoading } = useQuery({
    queryKey: ['regole'],
    queryFn: async () => {
      const response = await apiClient.get('/api/regole');
      return response.data;
    },
  });

  const deleteRegola = useMutation({
    mutationFn: (id) => apiClient.delete(`/api/regole/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries(['regole']);
    },
  });

  const toggleRegola = useMutation({
    mutationFn: (id) => apiClient.post(`/api/regole/${id}/toggle`),
    onSuccess: () => {
      queryClient.invalidateQueries(['regole']);
    },
  });

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Regole</h1>
          <p className="text-gray-600">Gestisci regole di automazione personalizzate</p>
        </div>
        <button
          onClick={() => {
            setEditingRegola(null);
            setShowModal(true);
          }}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus size={20} />
          Nuova Regola
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-8">Caricamento...</div>
      ) : regole?.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500 mb-4">Nessuna regola configurata</p>
          <button
            onClick={() => setShowModal(true)}
            className="text-blue-600 hover:underline"
          >
            Crea la prima regola
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {regole?.map((regola) => (
            <RegolaCard
              key={regola.id}
              regola={regola}
              onEdit={() => {
                setEditingRegola(regola);
                setShowModal(true);
              }}
              onDelete={() => deleteRegola.mutate(regola.id)}
              onToggle={() => toggleRegola.mutate(regola.id)}
            />
          ))}
        </div>
      )}

      {showModal && (
        <RegolaModal
          regola={editingRegola}
          onClose={() => {
            setShowModal(false);
            setEditingRegola(null);
          }}
        />
      )}
    </div>
  );
}

function RegolaCard({ regola, onEdit, onDelete, onToggle }) {
  const [showTest, setShowTest] = useState(false);

  const getPriorityBadge = (priorita) => {
    if (priorita <= 3) return 'bg-red-100 text-red-800';
    if (priorita <= 7) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-xl font-semibold">{regola.nome}</h3>
            <span className={`text-xs px-2 py-1 rounded-full ${getPriorityBadge(regola.priorita)}`}>
              Priorità {regola.priorita}
            </span>
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                regola.attivo ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
              }`}
            >
              {regola.attivo ? 'Attiva' : 'Disattiva'}
            </span>
          </div>
          {regola.descrizione && (
            <p className="text-gray-600 text-sm">{regola.descrizione}</p>
          )}
        </div>

        <div className="flex gap-2">
          <button
            onClick={onToggle}
            className="p-2 hover:bg-gray-100 rounded"
            title={regola.attivo ? 'Disattiva' : 'Attiva'}
          >
            <Power size={18} className={regola.attivo ? 'text-green-600' : 'text-gray-400'} />
          </button>
          <button
            onClick={() => setShowTest(!showTest)}
            className="p-2 hover:bg-gray-100 rounded"
            title="Testa regola"
          >
            <TestTube size={18} />
          </button>
          <button onClick={onEdit} className="p-2 hover:bg-gray-100 rounded" title="Modifica">
            <Edit size={18} />
          </button>
          <button onClick={onDelete} className="p-2 hover:bg-red-100 rounded text-red-600" title="Elimina">
            <Trash2 size={18} />
          </button>
        </div>
      </div>

      {/* Condizioni */}
      <div className="mb-4">
        <h4 className="font-medium text-sm text-gray-700 mb-2">Condizioni:</h4>
        <div className="bg-gray-50 p-3 rounded text-sm">
          <pre className="text-xs overflow-auto">{JSON.stringify(regola.condizioni, null, 2)}</pre>
        </div>
      </div>

      {/* Azioni */}
      <div className="mb-4">
        <h4 className="font-medium text-sm text-gray-700 mb-2">Azioni:</h4>
        <div className="flex flex-wrap gap-2">
          {regola.azioni.map((azione, idx) => (
            <span key={idx} className="bg-blue-100 text-blue-800 text-xs px-3 py-1 rounded-full">
              {azione.tipo}
            </span>
          ))}
        </div>
      </div>

      {/* Statistiche */}
      <div className="text-sm text-gray-600">
        Applicata {regola.volte_applicata} volte
        {regola.ultima_applicazione && (
          <span> • Ultima: {new Date(regola.ultima_applicazione).toLocaleString('it-IT')}</span>
        )}
      </div>

      {/* Test Panel */}
      {showTest && <TestRegolaPanel regolaId={regola.id} />}
    </div>
  );
}

function TestRegolaPanel({ regolaId }) {
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  const runTest = async () => {
    setTesting(true);
    try {
      const response = await apiClient.post(`/api/regole/${regolaId}/test`, {
        limit: 100,
      });
      setTestResult(response.data);
    } catch (error) {
      console.error('Errore test:', error);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="mt-4 border-t pt-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-sm">Test Regola</h4>
        <button
          onClick={runTest}
          disabled={testing}
          className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {testing ? 'Testing...' : 'Esegui Test'}
        </button>
      </div>

      {testResult && (
        <div className="bg-gray-50 p-3 rounded text-sm">
          <p className="font-medium mb-2">
            Trovate {testResult.matched_count} email corrispondenti (su ultime 100)
          </p>
          {testResult.matched_emails.length > 0 && (
            <div className="space-y-1 max-h-40 overflow-auto">
              {testResult.matched_emails.map((email) => (
                <div key={email.id} className="text-xs p-2 bg-white rounded">
                  <span className="font-medium">#{email.id}</span> - {email.oggetto}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RegolaModal({ regola, onClose }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState(
    regola || {
      nome: '',
      descrizione: '',
      attivo: true,
      priorita: 10,
      condizioni: {
        operator: 'AND',
        conditions: [],
      },
      azioni: [],
    }
  );

  const saveMutation = useMutation({
    mutationFn: async (data) => {
      if (regola) {
        return apiClient.put(`/api/regole/${regola.id}`, data);
      } else {
        return apiClient.post('/api/regole', data);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['regole']);
      onClose();
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    saveMutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-auto">
        <div className="p-6 border-b">
          <h2 className="text-2xl font-bold">{regola ? 'Modifica Regola' : 'Nuova Regola'}</h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6">
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium mb-1">Nome Regola</label>
              <input
                type="text"
                value={formData.nome}
                onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Descrizione</label>
              <textarea
                value={formData.descrizione}
                onChange={(e) => setFormData({ ...formData, descrizione: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                rows={2}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Priorità (0-99)</label>
                <input
                  type="number"
                  min="0"
                  max="99"
                  value={formData.priorita}
                  onChange={(e) => setFormData({ ...formData, priorita: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>

              <div className="flex items-center">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.attivo}
                    onChange={(e) => setFormData({ ...formData, attivo: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <span className="text-sm font-medium">Regola attiva</span>
                </label>
              </div>
            </div>
          </div>

          {/* Condizioni Editor - Semplificato */}
          <div className="mb-6">
            <h3 className="font-semibold mb-2">Condizioni (JSON)</h3>
            <textarea
              value={JSON.stringify(formData.condizioni, null, 2)}
              onChange={(e) => {
                try {
                  setFormData({ ...formData, condizioni: JSON.parse(e.target.value) });
                } catch (err) {
                  // Ignora errori parsing temporanei
                }
              }}
              className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
              rows={10}
            />
            <p className="text-xs text-gray-500 mt-1">
              Esempio: {`{"operator": "AND", "conditions": [{"field": "categoria", "operator": "equals", "value": "convocazione_scuola"}]}`}
            </p>
          </div>

          {/* Azioni Editor */}
          <div className="mb-6">
            <h3 className="font-semibold mb-2">Azioni (JSON)</h3>
            <textarea
              value={JSON.stringify(formData.azioni, null, 2)}
              onChange={(e) => {
                try {
                  setFormData({ ...formData, azioni: JSON.parse(e.target.value) });
                } catch (err) {}
              }}
              className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
              rows={6}
            />
            <p className="text-xs text-gray-500 mt-1">
              Esempio: {`[{"tipo": "inoltra", "destinatari": ["email@example.com"]}]`}
            </p>
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded-lg hover:bg-gray-50"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={saveMutation.isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saveMutation.isLoading ? 'Salvataggio...' : 'Salva Regola'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
