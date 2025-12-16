import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Briefcase, MapPin, Clock, Calendar, ChevronDown, ChevronRight, Building2, AlertCircle, CheckCircle, XCircle, Copy, MessageCircle } from 'lucide-react'
import { interpelliApi } from '../lib/api'

interface Interpello {
  id: number
  email_id: number
  classe_concorso: string | null
  numero_posti?: number
  ore_settimanali?: number
  data_scadenza?: string
  data_inizio_servizio?: string
  data_fine_contratto?: string
  provincia?: string
  citta?: string
  istituto?: string
  tipo_contratto?: string
  orario_giorni?: string
  link_candidatura?: string
  email_contatto?: string
  telefono_contatto?: string
  referente_contatto?: string
  modalita_candidatura?: string
  stato: 'aperto' | 'chiuso' | 'scaduto'
  verificato: boolean
  data_pubblicazione?: string
  indirizzo?: string
  metadata_estrazione?: {
    classe_validazione?: {
      raw: string | null
      normalizzata: string | null
      valida: boolean
      motivo?: string
      info?: {
        codice_ufficiale: string
        codice_sidi: string
        grado: string
        denominazione: string
      }
    }
  }
}

interface ClasseGroup {
  classe_concorso: string | null
  totale_interpelli: number
  totale_posti: number
  province: string[]
  interpelli: Interpello[]
}

interface PerClasseResponse {
  total_classi: number
  per_classe: ClasseGroup[]
}

export default function Interpelli() {
  const [soloAperti, setSoloAperti] = useState(true)
  const [expandedClasses, setExpandedClasses] = useState<Set<string>>(new Set())

  // Carica interpelli raggruppati per classe
  const { data, isLoading, refetch: _refetch } = useQuery<PerClasseResponse>({
    queryKey: ['interpelli-per-classe', soloAperti],
    queryFn: async () => {
      const response = await interpelliApi.perClasse({ solo_aperti: soloAperti })
      return response.data
    }
  })

  const toggleClass = (classe: string) => {
    const newExpanded = new Set(expandedClasses)
    if (newExpanded.has(classe)) {
      newExpanded.delete(classe)
    } else {
      newExpanded.add(classe)
    }
    setExpandedClasses(newExpanded)
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('it-IT')
  }

  // Genera messaggio WhatsApp con tutti gli interpelli aperti
  const generateWhatsAppMessage = () => {
    if (!data?.per_classe || data.per_classe.length === 0) {
      return '📢 *INTERPELLI DISPONIBILI*\n\nNessun interpello aperto al momento.\n\nContattaci per maggiori informazioni!'
    }

    let message = '📢 *INTERPELLI DISPONIBILI*\n\n'
    message += `Al momento ci sono *${totalInterpelli} interpelli* aperti!\n\n`

    data.per_classe.forEach((gruppo) => {
      if (gruppo.interpelli.length > 0) {
        message += `🔹 *${gruppo.classe_concorso || 'Classe non specificata'}*\n`

        gruppo.interpelli.forEach((interpello) => {
          message += `\n• ${interpello.istituto || 'Istituto non specificato'}\n`
          if (interpello.provincia || interpello.citta) {
            message += `  📍 ${interpello.citta ? interpello.citta + ', ' : ''}${interpello.provincia || ''}\n`
          }
          if (interpello.ore_settimanali) {
            message += `  ⏰ ${interpello.ore_settimanali}h/settimana\n`
          }
          if (interpello.data_scadenza) {
            message += `  📅 Scadenza: ${formatDate(interpello.data_scadenza)}\n`
          }
        })
        message += '\n'
      }
    })

    message += '📞 *Contattaci per maggiori informazioni e per candidarti!*'

    return message
  }

  const copyWhatsAppMessage = () => {
    const message = generateWhatsAppMessage()
    navigator.clipboard.writeText(message).then(() => {
      toast.success('Messaggio copiato! Incollalo in WhatsApp')
    }).catch(() => {
      toast.error('Errore durante la copia')
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Caricamento interpelli...</div>
      </div>
    )
  }

  const totalInterpelli = data?.per_classe.reduce((sum, c) => sum + c.totale_interpelli, 0) || 0

  // Calcola posti: se un interpello non specifica numero_posti, assumiamo 1 posto
  const totalPosti = data?.per_classe.reduce((sum, gruppo) => {
    // Se totale_posti è 0 o non specificato, assumiamo 1 posto per ogni interpello
    if (!gruppo.totale_posti || gruppo.totale_posti === 0) {
      return sum + gruppo.totale_interpelli
    }
    return sum + gruppo.totale_posti
  }, 0) || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Interpelli</h1>
          <p className="text-sm text-gray-500 mt-1">
            Organizzati per classe di concorso
          </p>
        </div>

        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={soloAperti}
            onChange={(e) => setSoloAperti(e.target.checked)}
            className="rounded border-gray-300"
          />
          <span className="text-sm text-gray-700">Solo aperti</span>
        </label>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Classi di Concorso</p>
              <p className="text-3xl font-bold text-blue-600 mt-2">{data?.total_classi || 0}</p>
            </div>
            <Briefcase className="w-10 h-10 text-blue-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Interpelli Totali</p>
              <p className="text-3xl font-bold text-green-600 mt-2">{totalInterpelli}</p>
            </div>
            <AlertCircle className="w-10 h-10 text-green-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Posti Disponibili</p>
              <p className="text-3xl font-bold text-purple-600 mt-2">{totalPosti || 'N/A'}</p>
            </div>
            <MapPin className="w-10 h-10 text-purple-500 opacity-20" />
          </div>
        </div>
      </div>

      {/* Messaggio WhatsApp */}
      {totalInterpelli > 0 && (
        <div className="bg-gradient-to-r from-green-50 to-green-100 p-6 rounded-lg shadow-sm border border-green-200">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-2">
                <MessageCircle className="w-5 h-5 text-green-600" />
                <h2 className="text-lg font-semibold text-gray-900">Messaggio WhatsApp per Docenti</h2>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                Copia questo messaggio e invialo ai docenti su WhatsApp. Il messaggio si aggiorna automaticamente con gli interpelli aperti.
              </p>
              <div className="bg-white p-4 rounded-lg border border-green-200 mb-4 max-h-96 overflow-y-auto">
                <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans">
                  {generateWhatsAppMessage()}
                </pre>
              </div>
              <button
                onClick={copyWhatsAppMessage}
                className="btn-primary flex items-center space-x-2"
              >
                <Copy className="w-4 h-4" />
                <span>Copia Messaggio</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Classi di Concorso */}
      <div className="space-y-3">
        {data?.per_classe.map((gruppo) => {
          const classeKey = gruppo.classe_concorso || 'NON_SPECIFICATA'
          const isExpanded = expandedClasses.has(classeKey)

          return (
            <div key={classeKey} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              {/* Header classe */}
              <button
                onClick={() => toggleClass(classeKey)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  )}

                  <div className="flex items-center space-x-3">
                    <div className="bg-blue-100 p-2 rounded-lg">
                      <Briefcase className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="text-left">
                      <h3 className="font-semibold text-gray-900">
                        {gruppo.classe_concorso || <span className="text-gray-400">Classe non specificata</span>}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {gruppo.totale_interpelli} {gruppo.totale_interpelli === 1 ? 'interpello' : 'interpelli'}
                        {gruppo.totale_posti > 0 && ` • ${gruppo.totale_posti} posti`}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Province */}
                {gruppo.province.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <MapPin className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-600">
                      {gruppo.province.slice(0, 3).join(', ')}
                      {gruppo.province.length > 3 && ` +${gruppo.province.length - 3}`}
                    </span>
                  </div>
                )}
              </button>

              {/* Interpelli espansi */}
              {isExpanded && (
                <div className="border-t border-gray-200 bg-gray-50">
                  <div className="p-6 space-y-4">
                    {gruppo.interpelli.map((interpello) => (
                      <div
                        key={interpello.id}
                        className="bg-white p-4 rounded-lg border border-gray-200 hover:shadow-md transition-shadow"
                      >
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Colonna sinistra */}
                          <div className="space-y-3">
                            {interpello.istituto && (
                              <div className="flex items-start space-x-2">
                                <Building2 className="w-4 h-4 text-gray-400 mt-1 flex-shrink-0" />
                                <div>
                                  <p className="text-sm font-medium text-gray-900">{interpello.istituto}</p>
                                  {interpello.indirizzo && (
                                    <p className="text-xs text-gray-500 mt-1">{interpello.indirizzo}</p>
                                  )}
                                </div>
                              </div>
                            )}

                            {(interpello.provincia || interpello.citta) && (
                              <div className="flex items-center space-x-2">
                                <MapPin className="w-4 h-4 text-gray-400" />
                                <span className="text-sm text-gray-700">
                                  {interpello.citta && `${interpello.citta}, `}
                                  {interpello.provincia}
                                </span>
                              </div>
                            )}

                            {interpello.tipo_contratto && (
                              <div className="flex items-center space-x-2">
                                <Clock className="w-4 h-4 text-gray-400" />
                                <span className="text-sm text-gray-700 capitalize">{interpello.tipo_contratto}</span>
                              </div>
                            )}
                          </div>

                          {/* Colonna destra */}
                          <div className="space-y-3">
                            {interpello.data_inizio_servizio && (
                              <div className="flex items-center space-x-2">
                                <Calendar className="w-4 h-4 text-gray-400" />
                                <span className="text-sm text-gray-700">
                                  Dal {formatDate(interpello.data_inizio_servizio)}
                                  {interpello.data_fine_contratto && ` al ${formatDate(interpello.data_fine_contratto)}`}
                                </span>
                              </div>
                            )}

                            {interpello.orario_giorni && (
                              <div className="text-sm text-gray-600">
                                <span className="font-medium">Orario:</span> {interpello.orario_giorni}
                              </div>
                            )}

                            {interpello.ore_settimanali && (
                              <div className="text-sm text-gray-600">
                                <span className="font-medium">Ore:</span> {interpello.ore_settimanali}h/settimana
                              </div>
                            )}

                            {interpello.data_scadenza && (
                              <div className="text-sm text-red-600 font-medium">
                                Scadenza: {formatDate(interpello.data_scadenza)}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Modalità di partecipazione */}
                        {(interpello.email_contatto || interpello.telefono_contatto || interpello.referente_contatto) && (
                          <div className="mt-3 pt-3 border-t border-gray-100">
                            <h4 className="text-sm font-semibold text-gray-900 mb-2">📞 Modalità di partecipazione</h4>
                            <div className="space-y-1 text-sm">
                              {interpello.email_contatto && (
                                <div>
                                  <span className="font-medium text-gray-700">Email:</span>{' '}
                                  <a href={`mailto:${interpello.email_contatto}`} className="text-blue-600 hover:underline">
                                    {interpello.email_contatto}
                                  </a>
                                </div>
                              )}
                              {interpello.telefono_contatto && (
                                <div>
                                  <span className="font-medium text-gray-700">Telefono:</span>{' '}
                                  <a href={`tel:${interpello.telefono_contatto}`} className="text-blue-600 hover:underline">
                                    {interpello.telefono_contatto}
                                  </a>
                                </div>
                              )}
                              {interpello.referente_contatto && (
                                <div>
                                  <span className="font-medium text-gray-700">Referente:</span> {interpello.referente_contatto}
                                </div>
                              )}
                              {interpello.modalita_candidatura && (
                                <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded">
                                  {interpello.modalita_candidatura}
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Footer */}
                        <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs text-gray-500">
                              Pubblicato: {formatDate(interpello.data_pubblicazione)}
                            </span>

                            {/* Validation indicator */}
                            {interpello.metadata_estrazione?.classe_validazione && (
                              <span className="flex items-center space-x-1">
                                {interpello.metadata_estrazione.classe_validazione.valida ? (
                                  <>
                                    <CheckCircle className="w-4 h-4 text-green-600" />
                                    <span className="text-xs text-green-600" title={`Classe validata: ${interpello.metadata_estrazione.classe_validazione.info?.denominazione}`}>
                                      Valida
                                    </span>
                                  </>
                                ) : (
                                  <>
                                    <XCircle className="w-4 h-4 text-red-600" />
                                    <span className="text-xs text-red-600" title={`Problema: ${interpello.metadata_estrazione.classe_validazione.motivo}`}>
                                      {interpello.metadata_estrazione.classe_validazione.motivo === 'non_estratta' ? 'Non estratta' : 'Non riconosciuta'}
                                    </span>
                                  </>
                                )}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center space-x-2">
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                              interpello.stato === 'aperto'
                                ? 'bg-green-100 text-green-800'
                                : interpello.stato === 'scaduto'
                                ? 'bg-gray-100 text-gray-800'
                                : 'bg-red-100 text-red-800'
                            }`}>
                              {interpello.stato}
                            </span>

                            <a
                              href={`/emails/${interpello.email_id}`}
                              className="text-sm text-blue-600 hover:text-blue-800"
                            >
                              Vedi email →
                            </a>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}

        {(!data || data.per_classe.length === 0) && (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <Briefcase className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">Nessun interpello trovato</p>
            {soloAperti && (
              <button
                onClick={() => setSoloAperti(false)}
                className="mt-2 text-sm text-blue-600 hover:text-blue-800"
              >
                Mostra anche chiusi/scaduti
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
