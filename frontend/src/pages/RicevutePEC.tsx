import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileCheck, Send, Mail, ChevronDown, ChevronRight, Filter, CheckCircle, Clock } from 'lucide-react'
import { ricevutePecApi } from '../lib/api'

interface RicevutaPEC {
  id: number
  mittente: string
  oggetto: string
  data_ricezione: string
  corpo_testo: string
}

interface GruppoRicevute {
  destinatario: string
  accettazione?: RicevutaPEC
  consegna?: RicevutaPEC
  dataUltima: string
}

export default function RicevutePEC() {
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null)
  const [filtroStato, setFiltroStato] = useState<string>('')

  // Carica ricevute PEC
  const { data: ricevuteData, isLoading } = useQuery({
    queryKey: ['ricevute-pec'],
    queryFn: () => ricevutePecApi.getAll({ limit: 500 }).then(res => res.data)
  })

  // Carica statistiche
  const { data: statsData } = useQuery({
    queryKey: ['ricevute-pec-stats'],
    queryFn: () => ricevutePecApi.getStats().then(res => res.data)
  })

  const ricevute: RicevutaPEC[] = ricevuteData?.emails || []
  void (statsData?.total || 0) // totalRicevute reserved for future pagination
  const totalConsegne = statsData?.consegne || 0
  const totalAccettazioni = statsData?.accettazioni || 0

  const extractDestinatario = (oggetto: string) => {
    const match = oggetto.match(/^(?:CONSEGNA|ACCETTAZIONE):\s*(.+)$/i)
    return match ? match[1].trim() : oggetto
  }

  const getTipoRicevuta = (oggetto: string): 'consegna' | 'accettazione' | 'altro' => {
    if (oggetto.toUpperCase().startsWith('CONSEGNA:')) return 'consegna'
    if (oggetto.toUpperCase().startsWith('ACCETTAZIONE:')) return 'accettazione'
    return 'altro'
  }

  // Raggruppa le ricevute per destinatario
  const gruppi = useMemo(() => {
    const gruppiMap = new Map<string, GruppoRicevute>()

    ricevute.forEach(ricevuta => {
      const destinatario = extractDestinatario(ricevuta.oggetto)
      const tipo = getTipoRicevuta(ricevuta.oggetto)

      if (!gruppiMap.has(destinatario)) {
        gruppiMap.set(destinatario, {
          destinatario,
          dataUltima: ricevuta.data_ricezione
        })
      }

      const gruppo = gruppiMap.get(destinatario)!

      if (tipo === 'accettazione') {
        gruppo.accettazione = ricevuta
      } else if (tipo === 'consegna') {
        gruppo.consegna = ricevuta
      }

      // Aggiorna data ultima
      if (new Date(ricevuta.data_ricezione) > new Date(gruppo.dataUltima)) {
        gruppo.dataUltima = ricevuta.data_ricezione
      }
    })

    // Converti in array e ordina per data
    let result = Array.from(gruppiMap.values()).sort(
      (a, b) => new Date(b.dataUltima).getTime() - new Date(a.dataUltima).getTime()
    )

    // Filtra per stato se necessario
    if (filtroStato === 'completo') {
      result = result.filter(g => g.accettazione && g.consegna)
    } else if (filtroStato === 'incompleto') {
      result = result.filter(g => !g.accettazione || !g.consegna)
    }

    return result
  }, [ricevute, filtroStato])

  const getStatoGruppo = (gruppo: GruppoRicevute) => {
    if (gruppo.accettazione && gruppo.consegna) {
      return { label: 'Completato', icon: CheckCircle, color: 'text-green-600 bg-green-100' }
    }
    return { label: 'In attesa', icon: Clock, color: 'text-amber-600 bg-amber-100' }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ricevute PEC</h1>
          <p className="text-gray-500 mt-1">Ricevute di accettazione e consegna della Posta Elettronica Certificata</p>
        </div>
      </div>

      {/* Statistiche */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card bg-gradient-to-br from-purple-50 to-white border-purple-200">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-purple-100">
              <Mail className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-purple-600">{gruppi.length}</p>
              <p className="text-sm text-gray-600">Email Inviate</p>
            </div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-blue-50 to-white border-blue-200">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-blue-100">
              <Send className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-blue-600">{totalAccettazioni}</p>
              <p className="text-sm text-gray-600">Accettazioni</p>
            </div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-green-50 to-white border-green-200">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-green-100">
              <FileCheck className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600">{totalConsegne}</p>
              <p className="text-sm text-gray-600">Consegne</p>
            </div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-amber-50 to-white border-amber-200">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-amber-100">
              <CheckCircle className="w-6 h-6 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-amber-600">
                {gruppi.filter(g => g.accettazione && g.consegna).length}
              </p>
              <p className="text-sm text-gray-600">Completate</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filtri */}
      <div className="card">
        <div className="flex items-center gap-4">
          <Filter className="w-5 h-5 text-gray-400" />
          <select
            value={filtroStato}
            onChange={(e) => setFiltroStato(e.target.value)}
            className="input w-48"
          >
            <option value="">Tutte le email</option>
            <option value="completo">Solo completate</option>
            <option value="incompleto">Solo in attesa</option>
          </select>
        </div>
      </div>

      {/* Lista raggruppata */}
      <div className="card">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-4 border-purple-600 border-t-transparent"></div>
            <p className="mt-4 text-gray-500">Caricamento ricevute...</p>
          </div>
        ) : gruppi.length === 0 ? (
          <div className="text-center py-12">
            <Mail className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">Nessuna ricevuta PEC trovata</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {gruppi.map((gruppo) => {
              const isExpanded = expandedGroup === gruppo.destinatario
              const stato = getStatoGruppo(gruppo)
              const StatoIcon = stato.icon

              return (
                <div key={gruppo.destinatario} className="py-3">
                  <div
                    className="flex items-center gap-4 cursor-pointer hover:bg-gray-50 p-2 rounded-lg transition-colors"
                    onClick={() => setExpandedGroup(isExpanded ? null : gruppo.destinatario)}
                  >
                    {/* Expand icon */}
                    <div className="text-gray-400">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </div>

                    {/* Stato badge */}
                    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${stato.color}`}>
                      <StatoIcon className="w-3.5 h-3.5" />
                      {stato.label}
                    </div>

                    {/* Destinatario */}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate">
                        {gruppo.destinatario}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        {gruppo.accettazione && (
                          <span className="inline-flex items-center gap-1 text-xs text-blue-600">
                            <Send className="w-3 h-3" /> Accettata
                          </span>
                        )}
                        {gruppo.consegna && (
                          <span className="inline-flex items-center gap-1 text-xs text-green-600">
                            <FileCheck className="w-3 h-3" /> Consegnata
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Data */}
                    <div className="text-right text-xs text-gray-500 whitespace-nowrap">
                      {new Date(gruppo.dataUltima).toLocaleDateString('it-IT', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </div>
                  </div>

                  {/* Expanded content */}
                  {isExpanded && (
                    <div className="mt-3 ml-10 space-y-3">
                      {/* Accettazione */}
                      {gruppo.accettazione ? (
                        <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                          <div className="flex items-center gap-2 mb-2">
                            <Send className="w-4 h-4 text-blue-600" />
                            <span className="font-medium text-blue-800">Accettazione</span>
                            <span className="text-xs text-blue-600 ml-auto">
                              {new Date(gruppo.accettazione.data_ricezione).toLocaleString('it-IT')}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600">{gruppo.accettazione.mittente}</p>
                        </div>
                      ) : (
                        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 border-dashed">
                          <div className="flex items-center gap-2 text-gray-400">
                            <Send className="w-4 h-4" />
                            <span>Accettazione non ricevuta</span>
                          </div>
                        </div>
                      )}

                      {/* Consegna */}
                      {gruppo.consegna ? (
                        <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                          <div className="flex items-center gap-2 mb-2">
                            <FileCheck className="w-4 h-4 text-green-600" />
                            <span className="font-medium text-green-800">Consegna</span>
                            <span className="text-xs text-green-600 ml-auto">
                              {new Date(gruppo.consegna.data_ricezione).toLocaleString('it-IT')}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600">{gruppo.consegna.mittente}</p>
                        </div>
                      ) : (
                        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 border-dashed">
                          <div className="flex items-center gap-2 text-gray-400">
                            <FileCheck className="w-4 h-4" />
                            <span>Consegna non ricevuta</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
