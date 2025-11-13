import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, parseISO } from 'date-fns'
import { it } from 'date-fns/locale'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date, formatStr: string = 'PPP') {
  const dateObj = typeof date === 'string' ? parseISO(date) : date
  return format(dateObj, formatStr, { locale: it })
}

export function formatDateTime(date: string | Date) {
  return formatDate(date, 'PPP HH:mm')
}

export function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    richiesta_appuntamento: 'Richiesta Appuntamento',
    richiesta_tesseramento: 'Richiesta Tesseramento',
    comunicazione_ust_usr: 'Comunicazione UST/USR',
    comunicazione_snals_centrale: 'Comunicazione SNALS Centrale',
    convocazione_scuola: 'Convocazione Scuola',
    comunicazione_scuola: 'Comunicazione Scuola',
    newsletter: 'Newsletter',
    spam: 'Spam',
    altro: 'Altro',
  }
  return labels[category] || category
}

export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    non_letta: 'Non Letta',
    letta: 'Letta',
    in_lavorazione: 'In Lavorazione',
    completata: 'Completata',
    archiviata: 'Archiviata',
  }
  return labels[status] || status
}

export function getActionTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    bozza_risposta: 'Bozza Risposta',
    crea_evento_calendario: 'Crea Evento',
    carica_su_drive: 'Carica su Drive',
    invia_email: 'Invia Email',
    applica_regola: 'Applica Regola',
  }
  return labels[type] || type
}

export function getActionStateLabel(state: string): string {
  const labels: Record<string, string> = {
    pending: 'In Attesa',
    in_esecuzione: 'In Esecuzione',
    completata: 'Completata',
    fallita: 'Fallita',
  }
  return labels[state] || state
}

export function getTipoDocumentoLabel(tipo: string): string {
  const labels: Record<string, string> = {
    snals_centrale: 'SNALS Centrale',
    usr_usp: 'USR/USP',
    normativa: 'Normativa',
    circolare: 'Circolare',
    contratto: 'Contratto',
    faq: 'FAQ',
    altro: 'Altro',
  }
  return labels[tipo] || tipo
}

export function getStatoDocumentoLabel(stato: string): string {
  const labels: Record<string, string> = {
    caricato: 'Caricato',
    processato: 'Processato',
    embeddato: 'Embeddato',
    errore: 'Errore',
  }
  return labels[stato] || stato
}

export function getCategoryColor(category: string): string {
  const colors: Record<string, string> = {
    richiesta_appuntamento: 'bg-blue-100 text-blue-800',
    richiesta_tesseramento: 'bg-green-100 text-green-800',
    comunicazione_ust_usr: 'bg-purple-100 text-purple-800',
    comunicazione_snals_centrale: 'bg-yellow-100 text-yellow-800',
    convocazione_scuola: 'bg-orange-100 text-orange-800',
    comunicazione_scuola: 'bg-indigo-100 text-indigo-800',
    newsletter: 'bg-gray-100 text-gray-800',
    spam: 'bg-red-100 text-red-800',
    altro: 'bg-gray-100 text-gray-800',
  }
  return colors[category] || 'bg-gray-100 text-gray-800'
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    non_letta: 'bg-red-100 text-red-800',
    letta: 'bg-blue-100 text-blue-800',
    in_lavorazione: 'bg-yellow-100 text-yellow-800',
    completata: 'bg-green-100 text-green-800',
    archiviata: 'bg-gray-100 text-gray-800',
  }
  return colors[status] || 'bg-gray-100 text-gray-800'
}

export function getActionStateColor(state: string): string {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    in_esecuzione: 'bg-blue-100 text-blue-800',
    completata: 'bg-green-100 text-green-800',
    fallita: 'bg-red-100 text-red-800',
  }
  return colors[state] || 'bg-gray-100 text-gray-800'
}
