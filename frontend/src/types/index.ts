// Email types
export enum EmailCategory {
  RICHIESTA_APPUNTAMENTO = 'richiesta_appuntamento',
  RICHIESTA_TESSERAMENTO = 'richiesta_tesseramento',
  COMUNICAZIONE_UST_USR = 'comunicazione_ust_usr',
  COMUNICAZIONE_SNALS_CENTRALE = 'comunicazione_snals_centrale',
  CONVOCAZIONE_SCUOLA = 'convocazione_scuola',
  COMUNICAZIONE_SCUOLA = 'comunicazione_scuola',
  NEWSLETTER = 'newsletter',
  SPAM = 'spam',
  ALTRO = 'altro',
}

export enum EmailStatus {
  NON_LETTA = 'non_letta',
  LETTA = 'letta',
  IN_LAVORAZIONE = 'in_lavorazione',
  COMPLETATA = 'completata',
  ARCHIVIATA = 'archiviata',
}

export enum AccountType {
  NORMALE = 'normale',
  PEC = 'pec',
}

export interface Email {
  id: number
  message_id: string
  account_type: AccountType
  mittente: string
  destinatario: string
  oggetto: string
  corpo_testo: string
  corpo_html?: string
  data_ricezione: string
  categoria: EmailCategory
  priorita: number
  status: EmailStatus
  allegati: Array<{
    filename: string
    content_type: string
    size: number
  }>
  created_at: string
  updated_at: string
}

// Action types
export enum TipoAzione {
  BOZZA_RISPOSTA = 'bozza_risposta',
  CREA_EVENTO_CALENDARIO = 'crea_evento_calendario',
  CARICA_SU_DRIVE = 'carica_su_drive',
  INVIA_EMAIL = 'invia_email',
  APPLICA_REGOLA = 'applica_regola',
}

export enum StatoAzione {
  PENDING = 'pending',
  IN_ESECUZIONE = 'in_esecuzione',
  COMPLETATA = 'completata',
  FALLITA = 'fallita',
}

export interface Azione {
  id: number
  email_id: number
  tipo_azione: TipoAzione
  stato: StatoAzione
  parametri: Record<string, any>
  risultato?: Record<string, any>
  errore?: string
  created_at: string
  eseguita_at?: string
}

// Rule types
export interface Regola {
  id: number
  nome: string
  descrizione?: string
  attiva: boolean
  condizioni: Record<string, any>
  azioni: Array<{
    tipo: string
    parametri: Record<string, any>
  }>
  priorita: number
  created_at: string
  updated_at: string
}

// Calendar types
export interface EventoCalendario {
  id: number
  email_id?: number
  titolo: string
  descrizione?: string
  data_inizio: string
  data_fine: string
  luogo?: string
  partecipanti: string[]
  google_event_id?: string
  created_at: string
}

// Document types
export enum TipoDocumento {
  SNALS_CENTRALE = 'snals_centrale',
  USR_USP = 'usr_usp',
  NORMATIVA = 'normativa',
  CIRCOLARE = 'circolare',
  CONTRATTO = 'contratto',
  FAQ = 'faq',
  ALTRO = 'altro',
}

export enum StatoDocumento {
  CARICATO = 'caricato',
  PROCESSATO = 'processato',
  EMBEDDATO = 'embeddato',
  ERRORE = 'errore',
}

export interface Documento {
  id: number
  titolo: string
  descrizione?: string
  tipo: TipoDocumento
  file_path: string
  contenuto_originale: string
  metadata: Record<string, any>
  embedding_abilitato: boolean
  stato: StatoDocumento
  priorita: number
  num_chunks?: number
  vector_store_id?: string
  attivo: boolean
  versione: number
  created_at: string
  updated_at: string
}

// Stats types
export interface DashboardStats {
  emails_oggi: number
  emails_non_lette: number
  azioni_pending: number
  eventi_settimana: number
  categorie_distribution: Record<string, number>
  azioni_distribution: Record<string, number>
}
