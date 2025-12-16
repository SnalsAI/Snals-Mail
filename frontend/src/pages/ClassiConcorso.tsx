import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Briefcase, Search, TrendingUp, Check, AlertCircle } from 'lucide-react'
import { classiConcorsoApi } from '../lib/api'

interface ClasseConcorso {
  codice_ufficiale: string
  codice_sidi: string
  grado: string
  denominazione: string
  interpelli_count: number
}

interface ClassiResponse {
  total: number
  classi: ClasseConcorso[]
}

interface StatsResponse {
  totale_classi_database: number
  classi_con_interpelli: number
  interpelli_senza_classe: number
  top_classi: Array<{
    classe: string
    interpelli_count: number
    info: {
      codice_ufficiale: string
      denominazione: string
      grado: string
    }
  }>
  per_grado: {
    'I GRADO': number
    'II GRADO': number
    'NON_VALIDE': number
  }
}

export default function ClassiConcorso() {
  const [search, setSearch] = useState('')
  const [gradoFilter, setGradoFilter] = useState<string>('')

  // Carica statistiche
  const { data: stats } = useQuery<StatsResponse>({
    queryKey: ['classi-stats'],
    queryFn: async () => {
      const response = await classiConcorsoApi.getStats()
      return response.data
    }
  })

  // Carica classi
  const { data: classiData, isLoading } = useQuery<ClassiResponse>({
    queryKey: ['classi-concorso', search, gradoFilter],
    queryFn: async () => {
      const response = await classiConcorsoApi.getAll({
        search: search || undefined,
        grado: gradoFilter || undefined
      })
      return response.data
    }
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Classi di Concorso</h1>
        <p className="text-sm text-gray-500 mt-1">
          Database ufficiale delle classi di concorso italiane (DPR 19/2016)
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Totale Classi</p>
              <p className="text-3xl font-bold text-blue-600 mt-2">
                {stats?.totale_classi_database || 0}
              </p>
            </div>
            <Briefcase className="w-10 h-10 text-blue-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Con Interpelli</p>
              <p className="text-3xl font-bold text-green-600 mt-2">
                {stats?.classi_con_interpelli || 0}
              </p>
            </div>
            <Check className="w-10 h-10 text-green-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">I Grado</p>
              <p className="text-3xl font-bold text-purple-600 mt-2">
                {stats?.per_grado['I GRADO'] || 0}
              </p>
            </div>
            <TrendingUp className="w-10 h-10 text-purple-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">II Grado</p>
              <p className="text-3xl font-bold text-orange-600 mt-2">
                {stats?.per_grado['II GRADO'] || 0}
              </p>
            </div>
            <TrendingUp className="w-10 h-10 text-orange-500 opacity-20" />
          </div>
        </div>
      </div>

      {/* Top Classi */}
      {stats && stats.top_classi.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Classi più richieste
          </h2>
          <div className="space-y-3">
            {stats.top_classi.map((item) => (
              <div
                key={item.classe}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <div className="bg-blue-100 px-3 py-1 rounded-full">
                    <span className="text-sm font-medium text-blue-700">
                      {item.info?.codice_ufficiale || item.classe}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {item.info?.denominazione || 'N/A'}
                    </p>
                    <p className="text-xs text-gray-500">{item.info?.grado}</p>
                  </div>
                </div>
                <span className="text-sm font-semibold text-gray-700">
                  {item.interpelli_count} {item.interpelli_count === 1 ? 'interpello' : 'interpelli'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filtri e Ricerca */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Ricerca */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Cerca per codice o denominazione..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Filtro Grado */}
          <div className="md:w-48">
            <select
              value={gradoFilter}
              onChange={(e) => setGradoFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Tutti i gradi</option>
              <option value="I GRADO">I GRADO</option>
              <option value="II GRADO">II GRADO</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabella Classi */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Codice
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Codice SIDI
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Grado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Denominazione
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Interpelli
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    Caricamento...
                  </td>
                </tr>
              ) : classiData && classiData.classi.length > 0 ? (
                classiData.classi.map((classe) => (
                  <tr key={classe.codice_ufficiale} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <span className="px-3 py-1 text-sm font-medium text-blue-700 bg-blue-100 rounded-full">
                          {classe.codice_ufficiale}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {classe.codice_sidi}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        classe.grado.includes('I GRADO')
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-orange-100 text-orange-700'
                      }`}>
                        {classe.grado}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {classe.denominazione}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      {classe.interpelli_count > 0 ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          {classe.interpelli_count}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    {search || gradoFilter
                      ? 'Nessuna classe trovata con i filtri applicati'
                      : 'Nessuna classe disponibile'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Footer con totale */}
        {classiData && classiData.total > 0 && (
          <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              Totale: <span className="font-medium">{classiData.total}</span> classi
            </p>
          </div>
        )}
      </div>

      {/* Alert per interpelli senza classe */}
      {stats && stats.interpelli_senza_classe > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-yellow-800">
              Attenzione: {stats.interpelli_senza_classe} interpelli senza classe di concorso
            </p>
            <p className="text-sm text-yellow-700 mt-1">
              Alcuni interpelli non hanno una classe di concorso valida estratta.
              Considera di riprocessare queste email per migliorare l'estrazione.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
