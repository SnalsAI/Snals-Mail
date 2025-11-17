export enum EmailCategory {
  INFO_GENERICHE = 'info_generiche',
  RICHIESTA_APPUNTAMENTO = 'richiesta_appuntamento',
  RICHIESTA_TESSERAMENTO = 'richiesta_tesseramento',
  CONVOCAZIONE_SCUOLA = 'convocazione_scuola',
  COMUNICAZIONE_UST_USR = 'comunicazione_ust_usr',
  COMUNICAZIONE_SCUOLA = 'comunicazione_scuola',
  COMUNICAZIONE_SNALS_CENTRALE = 'comunicazione_snals_centrale',
  VARIE = 'varie',
}

export enum EmailStatus {
  RAW = 'RAW',
  CATEGORIZZATA = 'CATEGORIZZATA',
  INTERPRETATA = 'INTERPRETATA',
  PROCESSATA = 'PROCESSATA',
  ERRORE = 'ERRORE',
}

export enum AccountType {
  NORMALE = 'NORMALE',
  PEC = 'PEC',
}

export interface Email {
  id: number
  message_id: string
  account_type: AccountType
  mittente: string
  destinatario: string
  oggetto: string
  corpo: string
  data_ricezione: string
  data_elaborazione?: string
  allegati_path?: string[]
  allegati_nomi?: string[]
  categoria?: EmailCategory
  categoria_confidence?: number
  stato: EmailStatus
  richiede_revisione: boolean
  revisionata: boolean
  priorita: number
  created_at: string
  updated_at: string
}

export interface EmailInterpretation {
  id: number
  email_id: number
  dati_estratti: Record<string, any>
  confidence: number
  modello_usato: string
  created_at: string
}

export enum ActionType {
  BOZZA_RISPOSTA = 'BOZZA_RISPOSTA',
  CREA_EVENTO_CALENDARIO = 'CREA_EVENTO_CALENDARIO',
  CARICA_SU_DRIVE = 'CARICA_SU_DRIVE',
  INOLTRA_EMAIL = 'INOLTRA_EMAIL',
}

export enum ActionStatus {
  PENDING = 'PENDING',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
}

export interface Action {
  id: number
  email_id: number
  tipo_azione: ActionType
  stato: ActionStatus
  parametri: Record<string, any>
  risultato?: Record<string, any>
  errore?: string
  created_at: string
  updated_at: string
  executed_at?: string
}

export interface Rule {
  id: number
  nome: string
  descrizione?: string
  attivo: boolean
  priorita: number
  condizioni: {
    operator: 'AND' | 'OR'
    rules: Array<{
      field: string
      condition: string
      value: any
    }>
    stop_on_match?: boolean
  }
  azioni: {
    actions: Array<{
      type: string
      params: Record<string, any>
    }>
  }
  volte_applicata: number
  ultima_applicazione?: string
  created_at: string
  updated_at: string
}

export interface CalendarEvent {
  id: number
  email_id?: number
  titolo: string
  descrizione?: string
  data_inizio: string
  data_fine?: string
  luogo?: string
  scuola?: string
  partecipanti?: string[]
  google_event_id?: string
  stato: string
  created_at: string
  updated_at: string
}

export interface Stats {
  total_emails: number
  emails_today: number
  unread_emails: number
  pending_actions: number
  categories_distribution: Record<string, number>
  emails_by_account: Record<string, number>
}
