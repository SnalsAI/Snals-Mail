export enum EmailCategory {
  COMUNICAZIONE_SCUOLA = 'comunicazione_scuola',
  COMUNICAZIONE_UST_USR = 'comunicazione_ust_usr',
  COMUNICAZIONE_SNALS_CENTRALE = 'comunicazione_snals_centrale',
  RICHIESTA_APPUNTAMENTO = 'richiesta_appuntamento',
  RICHIESTA_TESSERAMENTO = 'richiesta_tesseramento',
  REVOCA_SINDACALE = 'revoca_sindacale',
  RICEVUTA_PEC = 'ricevuta_pec',
  ERRORE_INVIO = 'errore_invio',
  SPAM = 'spam',
  INFO_GENERICHE = 'info_generiche',
  VARIE = 'varie',
  DA_CATEGORIZZARE = 'da_categorizzare',
}

export enum EmailStatus {
  RICEVUTA = 'ricevuta',
  IN_ELABORAZIONE = 'in_elaborazione',
  CATEGORIZZATA = 'categorizzata',
  INTERPRETATA = 'interpretata',
  AZIONE_ESEGUITA = 'azione_eseguita',
  ERRORE = 'errore',
  COMPLETATA = 'completata',
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
  corpo: string
  corpo_testo?: string
  corpo_html?: string
  data_ricezione: string
  data_elaborazione?: string
  allegati_path?: string[]
  allegati_nomi?: string[]
  allegati_testo?: Record<string, string>
  categoria?: EmailCategory | string
  sottocategoria?: string
  sottocategoria_proposta?: string
  motivo_proposta?: string
  categoria_confidence?: number
  confidence_score?: number
  stato: EmailStatus
  letto?: boolean
  richiede_revisione: boolean
  revisionata: boolean
  priorita: number
  note?: string
  interpretazione?: any
  azioni?: any[]
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
  // Azioni di risposta
  BOZZA_RISPOSTA = 'BOZZA_RISPOSTA',
  INVIA_RISPOSTA_AUTOMATICA = 'invia_risposta_automatica',

  // Azioni di gestione
  BOZZA_APPUNTAMENTO = 'BOZZA_APPUNTAMENTO',
  BOZZA_TESSERAMENTO = 'BOZZA_TESSERAMENTO',
  CREA_TASK = 'crea_task',

  // Azioni di calendario
  EVENTO_CALENDARIO = 'EVENTO_CALENDARIO',

  // Azioni di comunicazione
  INOLTRA = 'INOLTRA',
  INOLTRA_EMAIL = 'inoltra_email',
  INOLTRA_DELEGATI_ZONA = 'INOLTRA_DELEGATI_ZONA',
  NOTIFICA = 'NOTIFICA',
  INVIA_NOTIFICA = 'invia_notifica',

  // Azioni di archiviazione e organizzazione
  ARCHIVIA = 'archivia',
  SEGNA_IMPORTANTE = 'segna_importante',
  PUBBLICA_SU_SITO = 'pubblica_su_sito',

  // Azioni di elaborazione
  SINTESI = 'SINTESI',
  INDICIZZA_RAG = 'INDICIZZA_RAG',
  PARSE_INTERPELLO = 'PARSE_INTERPELLO',

  // Azioni di moderazione
  ELIMINA = 'elimina',
  SPAM = 'SPAM',
}

export enum ActionStatus {
  IN_CODA = 'IN_CODA',
  IN_ESECUZIONE = 'IN_ESECUZIONE',
  COMPLETATA = 'COMPLETATA',
  FALLITA = 'FALLITA',
  ANNULLATA = 'ANNULLATA',
}

export interface Action {
  id: number
  email_id: number
  tipo: string
  stato: string
  dettagli: Record<string, any>
  risultato?: Record<string, any>
  errore?: string
  timestamp_inizio: string
  timestamp_fine?: string
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
  // Supporta entrambi i formati: array diretto o oggetto con actions
  azioni: Array<{
    tipo?: string
    type?: string
    descrizione?: string
    params: Record<string, any>
  }> | {
    actions: Array<{
      type: string
      tipo?: string
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
  all_day?: boolean
  luogo?: string
  link_videocall?: string
  scuola?: string
  tipo_convocazione?: string
  assegnatario_id?: number
  google_calendar_id?: string
  google_event_id?: string
  sincronizzato?: boolean
  allegati?: any[]
  created_at: string
  updated_at: string
  // Legacy fields (kept for backward compatibility)
  partecipanti?: string[]
  stato?: string
}

export interface Stats {
  total_emails: number
  emails_today: number
  unread_emails: number
  pending_actions: number
  categories_distribution: Record<string, number>
  emails_by_account: Record<string, number>
}

export enum TipoDocumento {
  NORMATIVA = 'normativa',
  CIRCOLARE = 'circolare',
  FAQ = 'faq',
  MODELLO = 'modello',
  CONTRATTO = 'contratto',
  PRASSI = 'prassi',
  GUIDA = 'guida',
  INTERPELLO_TIPO = 'interpello_tipo',
  ALTRO = 'altro',
}

export interface KnowledgeDocument {
  id: number
  titolo: string
  descrizione?: string
  tipo_documento: TipoDocumento
  categoria_email?: string
  tags: string[]
  ente_emittente?: string
  data_emissione?: string
  numero_protocollo?: string
  anno_riferimento?: string
  file_name: string
  file_path: string
  file_size: number
  file_size_mb: number
  file_type: string
  testo_length: number
  indexed_in_rag: boolean
  rag_document_ids?: string[]
  rag_indexed_at?: string
  created_at: string
  updated_at: string
  caricato_da: string
  note_interne?: string
  attivo: boolean
  verificato: boolean
}

export interface KnowledgeStats {
  total_documenti: number
  indicizzati_in_rag: number
  by_tipo: Record<string, number>
}

// ============================================================================
// BOOKING MODULE TYPES
// ============================================================================

export enum StatoSlot {
  LIBERO = 'libero',
  PRENOTATO = 'prenotato',
  BLOCCATO = 'bloccato',
}

export enum StatoPrenotazione {
  CONFERMATA = 'confermata',
  ANNULLATA_UTENTE = 'annullata_utente',
  ANNULLATA_UFFICIO = 'annullata_ufficio',
  COMPLETATA = 'completata',
  NO_SHOW = 'no_show',
}

export interface BookingSede {
  id: number
  nome: string
  indirizzo?: string
  citta?: string
  cap?: string
  telefono?: string
  email?: string
  attivo: boolean
  created_at: string
  updated_at: string
}

export interface BookingStaff {
  id: number
  nome: string
  cognome: string
  email: string
  telefono?: string
  ruolo?: string
  attivo: boolean
  utente_id?: number
  created_at: string
  updated_at: string
}

export interface BookingTipoAppuntamento {
  id: number
  nome: string
  descrizione?: string
  durata_default_minuti: number
  attivo: boolean
  colore?: string
  richiede_documenti?: boolean
  documenti_richiesti?: string[]
  created_at: string
  updated_at: string
}

export interface BookingStaffCompetenza {
  id: number
  staff_id: number
  tipo_appuntamento_id: number
  durata_minuti?: number
  attivo: boolean
  tipo_appuntamento?: BookingTipoAppuntamento
}

export interface BookingCampagna {
  id: number
  nome: string
  descrizione?: string
  data_inizio: string
  data_fine: string
  attiva: boolean
  tipi_appuntamento?: BookingTipoAppuntamento[]
  created_at: string
  updated_at: string
}

export interface BookingDisponibilita {
  id: number
  staff_id: number
  sede_id: number
  data: string
  ora_inizio: string
  ora_fine: string
  note?: string
  attivo: boolean
  staff?: BookingStaff
  sede?: BookingSede
  created_at: string
  updated_at: string
}

export interface BookingSlot {
  id: number
  disponibilita_id: number
  staff_id: number
  sede_id: number
  tipo_appuntamento_id: number
  data_ora_inizio: string
  data_ora_fine: string
  stato: StatoSlot
  note?: string
  staff?: BookingStaff
  sede?: BookingSede
  tipo_appuntamento?: BookingTipoAppuntamento
  created_at: string
  updated_at: string
}

export interface BookingContatto {
  id: number
  email: string
  nome: string
  cognome: string
  telefono?: string
  codice_fiscale?: string
  tipologia_contratto?: string
  scuola_attuale?: string
  privacy_accettata: boolean
  privacy_version?: string
  privacy_accettata_at?: string
  email_verificata: boolean
  created_at: string
  updated_at: string
}

export interface BookingPrenotazione {
  id: number
  contatto_id: number
  slot_id: number
  campagna_id?: number
  token_pubblico: string
  stato: StatoPrenotazione
  note_utente?: string
  note_admin?: string
  motivo?: string
  allegati_paths?: string[]
  annullato_at?: string
  annullato_da?: string
  motivo_annullamento?: string
  completato_at?: string
  esito?: string
  ip_prenotazione?: string
  user_agent?: string
  contatto?: BookingContatto
  slot?: BookingSlot
  campagna?: BookingCampagna
  created_at: string
  updated_at: string
}

export interface BookingStats {
  totale_prenotazioni: number
  prenotazioni_oggi: number
  prenotazioni_settimana: number
  per_stato: Record<string, number>
  per_tipo_appuntamento: Record<string, number>
  per_sede: Record<string, number>
}

// Request/Response types for API
export interface PrenotazioneCreatePublic {
  slot_id: number
  campagna_id?: number
  nome: string
  cognome: string
  email: string
  telefono?: string
  codice_fiscale?: string
  tipologia_contratto?: string
  scuola_attuale?: string
  note?: string
  motivo?: string
  privacy_accettata: boolean
}

export interface PrenotazioneResponse {
  prenotazione: BookingPrenotazione
  token: string
  message: string
}

export interface SlotDisponibiliParams {
  campagna_id?: number
  sede_id?: number
  tipo_appuntamento_id?: number
  data_da?: string
  data_a?: string
}
