/**
 * PatternEditor - Editor per pattern spaCy manuali
 *
 * Permette di aggiungere, modificare e eliminare pattern manuali
 * Include preview del pattern su testo di esempio
 */

import { useState, useMemo } from 'react'
import {
  Plus,
  Trash2,
  Search,
  Eye,
  X,
  Check,
  AlertCircle,
  Loader2
} from 'lucide-react'
import type { Pattern, PatternLabel, PatternSource } from './types'
import { usePatterns, usePatternLabels } from './hooks'

interface PatternEditorProps {
  isOpen: boolean
  onClose: () => void
}

export function PatternEditor({ isOpen, onClose }: PatternEditorProps) {
  const [filterSource, setFilterSource] = useState<PatternSource | 'all'>('all')
  const [filterLabel, setFilterLabel] = useState<PatternLabel | 'all'>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)
  const [_editingId, _setEditingId] = useState<string | null>(null)
  const [previewText, setPreviewText] = useState('')
  const [showPreview, setShowPreview] = useState(false)

  // Form state per nuovo pattern
  const [newPattern, setNewPattern] = useState({ label: 'CLASSE_CONCORSO' as PatternLabel, pattern: '', description: '' })

  // Hooks
  const {
    patterns,
    total,
    bySource,
    byLabel: _byLabel,
    isLoading,
    isAdding,
    isDeleting,
    add,
    delete: deletePattern,
    preview,
    previewResult,
    clearPreview
  } = usePatterns(
    filterSource === 'all' ? undefined : filterSource,
    filterLabel === 'all' ? undefined : filterLabel
  )

  const { labels } = usePatternLabels()

  // Filtra per ricerca
  const filteredPatterns = useMemo(() => {
    if (!searchTerm) return patterns
    const term = searchTerm.toLowerCase()
    return patterns.filter(p =>
      p.pattern.toLowerCase().includes(term) ||
      p.label.toLowerCase().includes(term) ||
      p.description?.toLowerCase().includes(term)
    )
  }, [patterns, searchTerm])

  // Handlers
  const handleAdd = async () => {
    if (!newPattern.pattern.trim()) return
    try {
      await add({
        label: newPattern.label,
        pattern: newPattern.pattern.trim(),
        description: newPattern.description.trim() || undefined
      })
      setNewPattern({ label: 'CLASSE_CONCORSO', pattern: '', description: '' })
      setShowAddForm(false)
    } catch (err) {
      console.error('Errore aggiunta pattern:', err)
    }
  }

  const handleDelete = async (patternId: string) => {
    if (!confirm('Eliminare questo pattern?')) return
    try {
      await deletePattern(patternId)
    } catch (err) {
      console.error('Errore eliminazione pattern:', err)
    }
  }

  const handlePreview = async () => {
    if (!previewText || !newPattern.pattern) return
    await preview(newPattern.pattern, newPattern.label, previewText)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Panel */}
      <div className="absolute inset-y-0 right-0 w-full max-w-2xl bg-white shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Pattern Editor</h2>
            <p className="text-sm text-gray-500">
              Gestisci pattern per EntityRuler di spaCy
            </p>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Stats bar */}
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center gap-4 text-sm">
          <span className="font-medium">{total} pattern totali</span>
          <span className="text-gray-400">|</span>
          <span className="text-blue-600">{bySource?.base || 0} base</span>
          <span className="text-green-600">{bySource?.trained || 0} trained</span>
          <span className="text-purple-600">{bySource?.manual || 0} manuali</span>
        </div>

        {/* Filters */}
        <div className="px-6 py-3 border-b border-gray-200 flex items-center gap-3">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Cerca pattern..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {/* Source filter */}
          <select
            value={filterSource}
            onChange={e => setFilterSource(e.target.value as PatternSource | 'all')}
            className="px-3 py-2 text-sm border border-gray-300 rounded-md"
          >
            <option value="all">Tutte le sorgenti</option>
            <option value="base">Base</option>
            <option value="trained">Trained</option>
            <option value="manual">Manuali</option>
          </select>

          {/* Label filter */}
          <select
            value={filterLabel}
            onChange={e => setFilterLabel(e.target.value as PatternLabel | 'all')}
            className="px-3 py-2 text-sm border border-gray-300 rounded-md"
          >
            <option value="all">Tutti i label</option>
            {labels.map(label => (
              <option key={label} value={label}>{label}</option>
            ))}
          </select>

          {/* Add button */}
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md"
          >
            <Plus className="w-4 h-4" />
            Aggiungi
          </button>
        </div>

        {/* Add form */}
        {showAddForm && (
          <div className="px-6 py-4 bg-blue-50 border-b border-blue-200">
            <h3 className="font-medium text-blue-900 mb-3">Nuovo Pattern Manuale</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Label</label>
                <select
                  value={newPattern.label}
                  onChange={e => setNewPattern(p => ({ ...p, label: e.target.value as PatternLabel }))}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md"
                >
                  {labels.map(label => (
                    <option key={label} value={label}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Pattern</label>
                <input
                  type="text"
                  value={newPattern.pattern}
                  onChange={e => setNewPattern(p => ({ ...p, pattern: e.target.value }))}
                  placeholder="es. A-42, TAIC824001, ..."
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-700 mb-1">Descrizione (opzionale)</label>
                <input
                  type="text"
                  value={newPattern.description}
                  onChange={e => setNewPattern(p => ({ ...p, description: e.target.value }))}
                  placeholder="Descrizione del pattern"
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md"
                />
              </div>
            </div>

            {/* Preview section */}
            <div className="mt-3">
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                <Eye className="w-4 h-4" />
                {showPreview ? 'Nascondi' : 'Anteprima'} su testo
              </button>
              {showPreview && (
                <div className="mt-2 space-y-2">
                  <textarea
                    value={previewText}
                    onChange={e => setPreviewText(e.target.value)}
                    placeholder="Incolla qui un testo di esempio per testare il pattern..."
                    rows={3}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md"
                  />
                  <button
                    onClick={handlePreview}
                    disabled={!previewText || !newPattern.pattern}
                    className="text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                  >
                    Testa pattern
                  </button>
                  {previewResult && (
                    <div className="text-sm">
                      {previewResult.length > 0 ? (
                        <span className="text-green-600">
                          Trovati {previewResult.length} match: {previewResult.map(m => `"${m.text}"`).join(', ')}
                        </span>
                      ) : (
                        <span className="text-orange-600">Nessun match trovato</span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="mt-4 flex items-center gap-2">
              <button
                onClick={handleAdd}
                disabled={!newPattern.pattern.trim() || isAdding}
                className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md disabled:opacity-50"
              >
                {isAdding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                Salva
              </button>
              <button
                onClick={() => {
                  setShowAddForm(false)
                  setNewPattern({ label: 'CLASSE_CONCORSO', pattern: '', description: '' })
                  clearPreview()
                }}
                className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
              >
                Annulla
              </button>
            </div>
          </div>
        )}

        {/* Pattern list */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : filteredPatterns.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-300" />
              Nessun pattern trovato
            </div>
          ) : (
            <div className="space-y-2">
              {filteredPatterns.map(p => (
                <PatternRow
                  key={p.id}
                  pattern={p}
                  onDelete={() => handleDelete(p.id)}
                  isDeleting={isDeleting}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Sub-component for pattern row
interface PatternRowProps {
  pattern: Pattern
  onDelete: () => void
  isDeleting: boolean
}

function PatternRow({ pattern, onDelete, isDeleting }: PatternRowProps) {
  // Colori per source
  const sourceColors: Record<PatternSource, string> = {
    base: 'bg-gray-100 text-gray-600',
    trained: 'bg-green-100 text-green-700',
    manual: 'bg-purple-100 text-purple-700'
  }

  // Colori per label
  const labelColors: Record<string, string> = {
    CLASSE_CONCORSO: 'bg-blue-100 text-blue-700',
    MECCANOGRAFICO: 'bg-orange-100 text-orange-700',
    ISTITUTO: 'bg-teal-100 text-teal-700',
    PROVINCIA: 'bg-yellow-100 text-yellow-700',
    MOTIVO: 'bg-pink-100 text-pink-700'
  }

  return (
    <div className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-md hover:bg-gray-100 group">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        {/* Source badge */}
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${sourceColors[pattern.source]}`}>
          {pattern.source}
        </span>

        {/* Label badge */}
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${labelColors[pattern.label] || 'bg-gray-100 text-gray-600'}`}>
          {pattern.label}
        </span>

        {/* Pattern text */}
        <span className="font-mono text-sm text-gray-900 truncate" title={pattern.pattern}>
          {pattern.pattern}
        </span>

        {/* Description */}
        {pattern.description && (
          <span className="text-xs text-gray-400 truncate" title={pattern.description}>
            - {pattern.description}
          </span>
        )}
      </div>

      {/* Delete button (solo per manuali) */}
      {pattern.source === 'manual' && (
        <button
          onClick={onDelete}
          disabled={isDeleting}
          className="p-1 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
          title="Elimina pattern"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

export default PatternEditor
