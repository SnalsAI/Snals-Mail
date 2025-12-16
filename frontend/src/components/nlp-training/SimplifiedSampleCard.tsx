/**
 * SimplifiedSampleCard - Card per review semplificato dei sample
 *
 * Mostra solo i campi chiave in base al tipo (interpello/calendario/generico)
 * JSON raw nascosto di default
 */

import { useState } from 'react'
import { Check, X, ChevronDown, ChevronUp, Mail, Calendar, FileText } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { it } from 'date-fns/locale'
import type { TrainingSample } from './types'
import { INTERPELLO_FIELDS, CALENDARIO_FIELDS, FIELD_LABELS } from './types'

interface SimplifiedSampleCardProps {
  sample: TrainingSample
  onApprove: (sampleId: string) => void
  onReject: (sampleId: string) => void
  isApproving?: boolean
  isRejecting?: boolean
  selected?: boolean
  onToggleSelect?: (sampleId: string) => void
}

export function SimplifiedSampleCard({
  sample,
  onApprove,
  onReject,
  isApproving,
  isRejecting,
  selected,
  onToggleSelect
}: SimplifiedSampleCardProps) {
  const [showJson, setShowJson] = useState(false)
  const [showText, setShowText] = useState(false)

  const extraction = sample.openai_extraction || {}

  // Determina campi da mostrare in base al tipo
  const fieldsToShow = sample.type === 'interpello'
    ? INTERPELLO_FIELDS
    : sample.type === 'calendario'
      ? CALENDARIO_FIELDS
      : Object.keys(extraction).filter(k => k !== 'entities')

  // Icona per tipo
  const TypeIcon = sample.type === 'interpello'
    ? Mail
    : sample.type === 'calendario'
      ? Calendar
      : FileText

  // Colore badge tipo
  const typeColor = sample.type === 'interpello'
    ? 'bg-blue-100 text-blue-800'
    : sample.type === 'calendario'
      ? 'bg-purple-100 text-purple-800'
      : 'bg-gray-100 text-gray-800'

  // Formatta timestamp
  const formattedTime = sample.timestamp
    ? format(parseISO(sample.timestamp), 'dd/MM/yyyy HH:mm', { locale: it })
    : ''

  // Estrai valore campo
  const getFieldValue = (field: string): string | null => {
    const value = extraction[field]
    if (value === null || value === undefined) return null
    if (typeof value === 'string') return value || null
    if (typeof value === 'number') return String(value)
    if (Array.isArray(value)) return value.join(', ') || null
    return JSON.stringify(value)
  }

  return (
    <div
      className={`
        bg-white border rounded-lg overflow-hidden transition-all
        ${sample.approved ? 'border-green-200 bg-green-50/30' : 'border-gray-200'}
        ${selected ? 'ring-2 ring-primary-500' : ''}
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-3">
          {/* Checkbox selezione */}
          {onToggleSelect && (
            <input
              type="checkbox"
              checked={selected}
              onChange={() => onToggleSelect(sample.id)}
              className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
            />
          )}

          {/* Badge tipo */}
          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${typeColor}`}>
            <TypeIcon className="w-3 h-3" />
            {sample.type}
          </span>

          {/* Email ID */}
          <span className="text-sm text-gray-500">
            Email #{sample.email_id}
          </span>

          {/* Timestamp */}
          <span className="text-xs text-gray-400">
            {formattedTime}
          </span>

          {/* Badge approved */}
          {sample.approved && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
              <Check className="w-3 h-3" />
              Approvato
            </span>
          )}
        </div>

        {/* Actions */}
        {!sample.approved && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => onApprove(sample.id)}
              disabled={isApproving}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md disabled:opacity-50"
            >
              <Check className="w-4 h-4" />
              Approva
            </button>
            <button
              onClick={() => onReject(sample.id)}
              disabled={isRejecting}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md disabled:opacity-50"
            >
              <X className="w-4 h-4" />
              Rifiuta
            </button>
          </div>
        )}
      </div>

      {/* Fields Grid */}
      <div className="p-4">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {fieldsToShow.map(field => {
            const value = getFieldValue(field as string)
            if (value === null) return null

            return (
              <div key={field} className="bg-gray-50 rounded-md p-2">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  {FIELD_LABELS[field as string] || field}
                </div>
                <div className="mt-1 text-sm font-medium text-gray-900 truncate" title={value}>
                  {value}
                </div>
              </div>
            )
          })}
        </div>

        {/* Entities count */}
        {sample.entities && sample.entities.length > 0 && (
          <div className="mt-3 text-xs text-gray-500">
            {sample.entities.length} entità estratte
          </div>
        )}
      </div>

      {/* Expandable sections */}
      <div className="border-t border-gray-100">
        {/* Show original text */}
        <button
          onClick={() => setShowText(!showText)}
          className="w-full flex items-center justify-between px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
        >
          <span>Testo originale</span>
          {showText ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {showText && (
          <div className="px-4 pb-3">
            <div className="bg-gray-100 rounded-md p-3 text-xs text-gray-700 max-h-40 overflow-y-auto whitespace-pre-wrap">
              {sample.text?.substring(0, 1000) || 'Nessun testo'}
              {sample.text && sample.text.length > 1000 && '...'}
            </div>
          </div>
        )}

        {/* Show raw JSON */}
        <button
          onClick={() => setShowJson(!showJson)}
          className="w-full flex items-center justify-between px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 border-t border-gray-100"
        >
          <span>JSON completo</span>
          {showJson ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {showJson && (
          <div className="px-4 pb-3">
            <pre className="bg-gray-900 text-green-400 rounded-md p-3 text-xs overflow-x-auto max-h-60">
              {JSON.stringify(extraction, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default SimplifiedSampleCard
