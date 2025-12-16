"""
Models per il modulo Prenotazioni Appuntamenti SNALS

Questo modulo è COMPLETAMENTE SEPARATO dal calendario esistente (eventi_calendario).
Utilizza tabelle dedicate con prefisso 'booking_' per evitare conflitti.

Entità:
- BookingSede: Sedi fisiche per appuntamenti
- BookingStaff: Operatori che gestiscono appuntamenti
- BookingTipoAppuntamento: Tipologie di servizi offerti
- BookingStaffCompetenza: Competenze staff con durata personalizzata
- BookingServizio: Campagne/eventi (es. GPS 2025)
- BookingDisponibilita: Disponibilità settimanale staff
- BookingSlot: Slot prenotabili generati
- BookingContatto: Utenti esterni (anagrafica)
- BookingPrenotazione: Prenotazioni effettuate
- BookingNotifica: Log notifiche email
- BookingAuditLog: Tracciamento modifiche GDPR
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, Time,
    Boolean, ForeignKey, Enum, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import enum
import uuid

from app.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class StatoSlot(str, enum.Enum):
    """Stati possibili di uno slot"""
    LIBERO = "libero"
    PRENOTATO = "prenotato"
    BLOCCATO = "bloccato"  # Bloccato manualmente dallo staff


class StatoPrenotazione(str, enum.Enum):
    """Stati possibili di una prenotazione"""
    CONFERMATA = "confermata"
    ANNULLATA_UTENTE = "annullata_utente"
    ANNULLATA_UFFICIO = "annullata_ufficio"
    NO_SHOW = "no_show"  # Utente non si è presentato
    COMPLETATA = "completata"  # Appuntamento avvenuto


class TipoNotifica(str, enum.Enum):
    """Tipi di notifiche email"""
    CONFERMA = "conferma"
    PROMEMORIA_24H = "promemoria_24h"
    PROMEMORIA_48H = "promemoria_48h"
    PROMEMORIA_DOCUMENTI = "promemoria_documenti"
    ANNULLAMENTO = "annullamento"
    MODIFICA = "modifica"
    SPOSTAMENTO = "spostamento"


class StatoNotifica(str, enum.Enum):
    """Stati invio notifica"""
    PENDING = "pending"
    INVIATA = "inviata"
    FALLITA = "fallita"


class AzioneAudit(str, enum.Enum):
    """Azioni tracciabili per audit"""
    CREATED = "created"
    MODIFIED = "modified"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"  # Spostamento
    NO_SHOW = "no_show"
    COMPLETED = "completed"


class TipoUtenteAudit(str, enum.Enum):
    """Chi ha eseguito l'azione"""
    ESTERNO = "esterno"  # Utente che prenota
    STAFF = "staff"
    ADMIN = "admin"
    SISTEMA = "sistema"  # Azioni automatiche


# ============================================================================
# MODELLI
# ============================================================================

class BookingSede(Base):
    """
    Sedi fisiche dove si svolgono gli appuntamenti.

    Esempio: "Sede SNALS Taranto Centro", "Sede SNALS Martina Franca"
    """
    __tablename__ = "booking_sedi"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    indirizzo = Column(String(300))
    citta = Column(String(100))
    cap = Column(String(10))
    provincia = Column(String(100))
    telefono = Column(String(20))
    email = Column(String(255))
    note = Column(Text)  # Indicazioni parcheggio, come arrivare, ecc.

    # Coordinate per mappe (opzionale)
    latitudine = Column(String(20))
    longitudine = Column(String(20))

    attivo = Column(Boolean, default=True, index=True)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    staff = relationship("BookingStaff", back_populates="sede")
    disponibilita = relationship("BookingDisponibilita", back_populates="sede")
    slots = relationship("BookingSlot", back_populates="sede")

    def __repr__(self):
        return f"<BookingSede {self.id}: {self.nome}>"


class BookingStaff(Base):
    """
    Operatori che gestiscono appuntamenti.

    Ogni operatore ha una sede principale ma può avere disponibilità in altre sedi.
    """
    __tablename__ = "booking_staff"

    id = Column(Integer, primary_key=True, index=True)
    sede_id = Column(Integer, ForeignKey("booking_sedi.id"), nullable=False, index=True)

    nome = Column(String(100), nullable=False)
    cognome = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)  # Per notifiche interne
    telefono = Column(String(20))
    ruolo = Column(String(100))  # es. "Operatore patronato", "Responsabile GPS"

    # Collegamento opzionale con tabella utenti esistente
    utente_id = Column(Integer, ForeignKey("utenti.id"), nullable=True)

    attivo = Column(Boolean, default=True, index=True)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    sede = relationship("BookingSede", back_populates="staff")
    competenze = relationship("BookingStaffCompetenza", back_populates="staff", cascade="all, delete-orphan")
    disponibilita = relationship("BookingDisponibilita", back_populates="staff", cascade="all, delete-orphan")
    slots = relationship("BookingSlot", back_populates="staff")
    utente = relationship("Utente", foreign_keys=[utente_id])

    @property
    def nome_completo(self) -> str:
        return f"{self.nome} {self.cognome}"

    def __repr__(self):
        return f"<BookingStaff {self.id}: {self.nome_completo}>"


class BookingTipoAppuntamento(Base):
    """
    Tipologie di servizi/appuntamenti offerti.

    Esempio: "Domanda GPS", "Pensioni", "Ricostruzione carriera", "Consulenza generale"
    """
    __tablename__ = "booking_tipi_appuntamento"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    descrizione = Column(Text)

    # Durata di default (può essere sovrascritta per staff specifico)
    durata_default_minuti = Column(Integer, nullable=False, default=30)

    # Istruzioni per l'utente (documenti da portare, ecc.)
    istruzioni = Column(Text)

    # Colore per UI calendario (hex)
    colore = Column(String(7), default="#3B82F6")  # Tailwind blue-500

    # Ordine visualizzazione
    ordine = Column(Integer, default=0)

    attivo = Column(Boolean, default=True, index=True)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    competenze = relationship("BookingStaffCompetenza", back_populates="tipo_appuntamento")
    servizi = relationship(
        "BookingServizio",
        secondary="booking_servizio_tipo_appuntamento",
        back_populates="tipi_appuntamento"
    )
    slots = relationship("BookingSlot", back_populates="tipo_appuntamento")
    disponibilita = relationship(
        "BookingDisponibilita",
        secondary="booking_disponibilita_tipi",
        back_populates="tipi_appuntamento"
    )

    def __repr__(self):
        return f"<BookingTipoAppuntamento {self.id}: {self.nome}>"


class BookingStaffCompetenza(Base):
    """
    Tabella ponte: competenze staff per tipo appuntamento.

    Permette di:
    1. Definire quali tipi di appuntamento può gestire ogni staff
    2. Override della durata per combinazione staff+tipo

    Esempio:
    - Staff "Mario Rossi" + Tipo "Domanda GPS" → durata 45 minuti (invece di 30 default)
    - Staff "Luigi Verdi" + Tipo "Domanda GPS" → durata 30 minuti (usa default)
    """
    __tablename__ = "booking_staff_competenze"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("booking_staff.id", ondelete="CASCADE"), nullable=False)
    tipo_appuntamento_id = Column(Integer, ForeignKey("booking_tipi_appuntamento.id", ondelete="CASCADE"), nullable=False)

    # Override durata (NULL = usa default del tipo)
    durata_minuti = Column(Integer, nullable=True)

    attivo = Column(Boolean, default=True)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazioni
    staff = relationship("BookingStaff", back_populates="competenze")
    tipo_appuntamento = relationship("BookingTipoAppuntamento", back_populates="competenze")

    # Vincolo unicità
    __table_args__ = (
        UniqueConstraint('staff_id', 'tipo_appuntamento_id', name='uq_staff_tipo_appuntamento'),
    )

    @property
    def durata_effettiva(self) -> int:
        """Restituisce la durata effettiva (override o default)"""
        return self.durata_minuti or self.tipo_appuntamento.durata_default_minuti

    def __repr__(self):
        return f"<BookingStaffCompetenza {self.staff_id}-{self.tipo_appuntamento_id}>"


class BookingServizio(Base):
    """
    Campagne/eventi che raggruppano prenotazioni.

    Esempio: "GPS 2025", "Pensioni Quota 103", "Scelta 150 preferenze"
    """
    __tablename__ = "booking_servizi"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    descrizione = Column(Text)

    # Periodo di validità prenotazioni
    data_inizio = Column(Date, nullable=False)  # Da quando si può prenotare
    data_fine = Column(Date, nullable=False)    # Fino a quando si può prenotare

    # Slug per URL pubblico (es. "gps-2025")
    slug = Column(String(100), unique=True, index=True)

    attivo = Column(Boolean, default=True, index=True)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    tipi_appuntamento = relationship(
        "BookingTipoAppuntamento",
        secondary="booking_servizio_tipo_appuntamento",
        back_populates="servizi"
    )
    prenotazioni = relationship("BookingPrenotazione", back_populates="servizio")
    disponibilita = relationship("BookingDisponibilita", back_populates="servizio")

    def __repr__(self):
        return f"<BookingServizio {self.id}: {self.nome}>"


# Tabella ponte Servizio <-> TipoAppuntamento (N:M)
class BookingServizioTipoAppuntamento(Base):
    """Associazione N:M tra servizi e tipi appuntamento"""
    __tablename__ = "booking_servizio_tipo_appuntamento"

    servizio_id = Column(
        Integer,
        ForeignKey("booking_servizi.id", ondelete="CASCADE"),
        primary_key=True
    )
    tipo_appuntamento_id = Column(
        Integer,
        ForeignKey("booking_tipi_appuntamento.id", ondelete="CASCADE"),
        primary_key=True
    )

    created_at = Column(DateTime, default=datetime.utcnow)


class BookingDisponibilita(Base):
    """
    Disponibilità dello staff per appuntamenti.

    Definisce fasce orarie in cui lo staff è disponibile.
    Gli slot vengono generati automaticamente da queste disponibilità.
    """
    __tablename__ = "booking_disponibilita"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("booking_staff.id", ondelete="CASCADE"), nullable=False, index=True)
    sede_id = Column(Integer, ForeignKey("booking_sedi.id"), nullable=False, index=True)
    servizio_id = Column(Integer, ForeignKey("booking_servizi.id", ondelete="CASCADE"), nullable=True, index=True)

    # Giorno specifico
    data = Column(Date, nullable=False, index=True)

    # Fascia oraria
    ora_inizio = Column(Time, nullable=False)
    ora_fine = Column(Time, nullable=False)

    # Ricorrenza opzionale (per generazione automatica futura)
    # Formato: "weekly:mon,tue,wed" o "biweekly:mon,fri" o NULL per singolo giorno
    ricorrenza = Column(String(100), nullable=True)

    # Durata personalizzata slot (sovrascrive la durata default del tipo appuntamento)
    # Se NULL, usa la durata dalla competenza staff o dal tipo appuntamento
    durata_slot_minuti = Column(Integer, nullable=True)

    # Note interne
    note = Column(Text)

    attivo = Column(Boolean, default=True)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    staff = relationship("BookingStaff", back_populates="disponibilita")
    sede = relationship("BookingSede", back_populates="disponibilita")
    servizio = relationship("BookingServizio", back_populates="disponibilita")
    slots = relationship("BookingSlot", back_populates="disponibilita")
    tipi_appuntamento = relationship(
        "BookingTipoAppuntamento",
        secondary="booking_disponibilita_tipi",
        back_populates="disponibilita"
    )

    # Indice composto per ricerche
    __table_args__ = (
        Index('ix_booking_disponibilita_staff_data', 'staff_id', 'data'),
        Index('ix_booking_disponibilita_servizio', 'servizio_id'),
    )

    def __repr__(self):
        return f"<BookingDisponibilita {self.id}: {self.data} {self.ora_inizio}-{self.ora_fine}>"


# Tabella ponte Disponibilita <-> TipoAppuntamento (N:M)
class BookingDisponibilitaTipi(Base):
    """Associazione N:M tra disponibilità e tipi appuntamento (quali tipi sono possibili in questa fascia)"""
    __tablename__ = "booking_disponibilita_tipi"

    disponibilita_id = Column(
        Integer,
        ForeignKey("booking_disponibilita.id", ondelete="CASCADE"),
        primary_key=True
    )
    tipo_appuntamento_id = Column(
        Integer,
        ForeignKey("booking_tipi_appuntamento.id", ondelete="CASCADE"),
        primary_key=True
    )

    created_at = Column(DateTime, default=datetime.utcnow)


class BookingSlot(Base):
    """
    Slot prenotabili generati dalle disponibilità.

    Ogni slot rappresenta un singolo appuntamento prenotabile.
    La durata dipende dalla combinazione staff+tipo_appuntamento.
    """
    __tablename__ = "booking_slots"

    id = Column(Integer, primary_key=True, index=True)

    # Origine (opzionale, per tracciabilità)
    disponibilita_id = Column(Integer, ForeignKey("booking_disponibilita.id", ondelete="SET NULL"), nullable=True)

    # Assegnazione
    staff_id = Column(Integer, ForeignKey("booking_staff.id"), nullable=False, index=True)
    sede_id = Column(Integer, ForeignKey("booking_sedi.id"), nullable=False, index=True)
    tipo_appuntamento_id = Column(Integer, ForeignKey("booking_tipi_appuntamento.id"), nullable=False, index=True)

    # Timing
    data_ora_inizio = Column(DateTime, nullable=False, index=True)
    data_ora_fine = Column(DateTime, nullable=False)

    # Stato
    stato = Column(
        Enum(StatoSlot, name='stato_slot_enum', create_type=False),
        default=StatoSlot.LIBERO,
        nullable=False,
        index=True
    )

    # Note interne (es. motivo blocco)
    note = Column(Text)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    disponibilita = relationship("BookingDisponibilita", back_populates="slots")
    staff = relationship("BookingStaff", back_populates="slots")
    sede = relationship("BookingSede", back_populates="slots")
    tipo_appuntamento = relationship("BookingTipoAppuntamento", back_populates="slots")
    prenotazione = relationship("BookingPrenotazione", foreign_keys="[BookingPrenotazione.slot_id]", back_populates="slot", uselist=False)

    # Indici composti per ricerche comuni
    __table_args__ = (
        Index('ix_booking_slots_data_stato', 'data_ora_inizio', 'stato'),
        Index('ix_booking_slots_sede_tipo_data', 'sede_id', 'tipo_appuntamento_id', 'data_ora_inizio'),
    )

    @property
    def durata_minuti(self) -> int:
        """Calcola durata slot in minuti"""
        delta = self.data_ora_fine - self.data_ora_inizio
        return int(delta.total_seconds() / 60)

    @property
    def is_disponibile(self) -> bool:
        """Verifica se lo slot è prenotabile"""
        return self.stato == StatoSlot.LIBERO and self.data_ora_inizio > datetime.utcnow()

    def __repr__(self):
        return f"<BookingSlot {self.id}: {self.data_ora_inizio.strftime('%Y-%m-%d %H:%M')} ({self.stato.value})>"


# ============================================================================
# SCUOLE (Anagrafica scuole per selezione)
# ============================================================================

class Scuola(Base):
    """
    Anagrafica scuole per la selezione nel form di prenotazione.

    Permette di selezionare prima il comune e poi la scuola.
    I dati possono essere importati da fonti ufficiali MIUR.
    """
    __tablename__ = "scuole"

    id = Column(Integer, primary_key=True, index=True)

    # Identificativi
    codice_meccanografico = Column(String(20), unique=True, index=True)  # Es. RMIS00900E

    # Dati scuola
    nome = Column(String(255), nullable=False, index=True)
    tipo = Column(String(100))  # Es. "ISTITUTO COMPRENSIVO", "LICEO SCIENTIFICO", etc.
    ordine = Column(String(50))  # Es. "INFANZIA", "PRIMARIA", "SEC. I GRADO", "SEC. II GRADO"

    # Localizzazione
    comune = Column(String(100), nullable=False, index=True)
    provincia = Column(String(2), index=True)  # Sigla provincia (es. RM, MI)
    cap = Column(String(10))
    indirizzo = Column(String(255))

    # Contatti
    telefono = Column(String(30))
    email = Column(String(255))
    pec = Column(String(255))

    # Stato
    attivo = Column(Boolean, default=True)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indici per ricerca efficiente
    __table_args__ = (
        Index('ix_scuole_comune_nome', 'comune', 'nome'),
        Index('ix_scuole_provincia_comune', 'provincia', 'comune'),
    )

    def __repr__(self):
        return f"<Scuola {self.codice_meccanografico}: {self.nome} ({self.comune})>"


class BookingContatto(Base):
    """
    Utenti esterni che prenotano appuntamenti (anagrafica centralizzata).

    Questa tabella mantiene i dati anagrafici separati dalle prenotazioni,
    permettendo di:
    1. Vedere storico appuntamenti per utente
    2. Collegare con email esistenti (via campo email)
    3. Gestire consensi GDPR
    4. Inviare comunicazioni mirate future
    """
    __tablename__ = "booking_contatti"

    id = Column(Integer, primary_key=True, index=True)

    # Anagrafica base
    nome = Column(String(100), nullable=False)
    cognome = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)  # Chiave per collegamento email
    telefono = Column(String(20))

    # Iscrizione SNALS
    iscritto_snals = Column(Boolean, default=False)

    # Dati lavorativi
    ruolo_scuola = Column(String(100))  # es. "Docente", "ATA", "DSGA"
    ordine_scuola = Column(String(100))  # es. "Infanzia", "Primaria", "Secondaria I grado"
    tipologia_contratto = Column(String(100))  # es. "Tempo indeterminato", "Tempo determinato", "Supplente"

    # Scuola attuale (riferimento a tabella scuole)
    scuola_id = Column(Integer, ForeignKey("scuole.id"), nullable=True, index=True)
    scuola_attuale = Column(String(255))  # Nome scuola (legacy/backup se non in anagrafica)
    provincia = Column(String(100))

    # Consensi GDPR
    consenso_privacy = Column(Boolean, default=False, nullable=False)
    consenso_marketing = Column(Boolean, default=False)
    privacy_version = Column(String(20))  # Versione informativa accettata (es. "2025.1")
    data_consenso = Column(DateTime)

    # Note
    note = Column(Text)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    scuola = relationship("Scuola", backref="contatti")
    prenotazioni = relationship("BookingPrenotazione", back_populates="contatto", cascade="all, delete-orphan")

    @property
    def nome_completo(self) -> str:
        return f"{self.nome} {self.cognome}"

    def __repr__(self):
        return f"<BookingContatto {self.id}: {self.nome_completo}>"


class BookingPrenotazione(Base):
    """
    Prenotazioni effettuate.

    Ogni prenotazione collega un contatto a uno slot.
    Include token pubblico per modifica/annullamento senza login.
    """
    __tablename__ = "booking_prenotazioni"

    id = Column(Integer, primary_key=True, index=True)

    # Riferimenti
    contatto_id = Column(Integer, ForeignKey("booking_contatti.id"), nullable=False, index=True)
    slot_id = Column(Integer, ForeignKey("booking_slots.id"), nullable=False, unique=True, index=True)  # 1:1 con slot
    servizio_id = Column(Integer, ForeignKey("booking_servizi.id"), nullable=True, index=True)

    # Token pubblico per gestione senza login
    token_pubblico = Column(
        String(36),  # UUID format
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
        index=True
    )

    # Stato
    stato = Column(
        Enum(StatoPrenotazione, name='stato_prenotazione_enum', create_type=False),
        default=StatoPrenotazione.CONFERMATA,
        nullable=False,
        index=True
    )

    # Note
    note_utente = Column(Text)  # Note inserite dall'utente
    note_admin = Column(Text)   # Note interne staff/admin

    # Conferma
    data_conferma = Column(DateTime)  # Quando è stata confermata

    # Annullamento
    annullato_da = Column(String(20))  # 'utente', 'staff', 'admin', 'sistema'
    annullato_at = Column(DateTime)
    motivo_annullamento = Column(Text)

    # Spostamento (se la prenotazione è stata spostata)
    slot_precedente_id = Column(Integer, ForeignKey("booking_slots.id"), nullable=True)
    spostato_at = Column(DateTime)

    # Completamento
    completato_at = Column(DateTime)
    esito = Column(Text)  # Note sull'esito dell'appuntamento

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    contatto = relationship("BookingContatto", back_populates="prenotazioni")
    slot = relationship("BookingSlot", foreign_keys=[slot_id], back_populates="prenotazione")
    slot_precedente = relationship("BookingSlot", foreign_keys=[slot_precedente_id])
    servizio = relationship("BookingServizio", back_populates="prenotazioni")
    notifiche = relationship("BookingNotifica", back_populates="prenotazione", cascade="all, delete-orphan")
    audit_logs = relationship("BookingAuditLog", back_populates="prenotazione", cascade="all, delete-orphan")

    # Indici
    __table_args__ = (
        Index('ix_booking_prenotazioni_stato_data', 'stato', 'created_at'),
    )

    def __repr__(self):
        return f"<BookingPrenotazione {self.id}: {self.stato.value}>"


class BookingNotifica(Base):
    """
    Log notifiche email inviate per le prenotazioni.

    Traccia tutte le email inviate: conferma, promemoria, annullamento, ecc.
    Usa il sistema email esistente per l'invio effettivo.
    """
    __tablename__ = "booking_notifiche"

    id = Column(Integer, primary_key=True, index=True)
    prenotazione_id = Column(Integer, ForeignKey("booking_prenotazioni.id", ondelete="CASCADE"), nullable=False, index=True)

    # Tipo notifica
    tipo = Column(
        Enum(TipoNotifica, name='tipo_notifica_enum', create_type=False),
        nullable=False
    )

    # Template usato
    template = Column(String(100))

    # Destinatario (per storico, anche se cambia email contatto)
    destinatario = Column(String(255), nullable=False)

    # Stato invio
    stato = Column(
        Enum(StatoNotifica, name='stato_notifica_enum', create_type=False),
        default=StatoNotifica.PENDING,
        nullable=False,
        index=True
    )

    # Scheduling
    programmata_per = Column(DateTime)  # Quando deve essere inviata (per promemoria)
    inviata_at = Column(DateTime)

    # Errore (se fallita)
    errore = Column(Text)
    tentativi = Column(Integer, default=0)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazioni
    prenotazione = relationship("BookingPrenotazione", back_populates="notifiche")

    def __repr__(self):
        return f"<BookingNotifica {self.id}: {self.tipo.value} ({self.stato.value})>"


class BookingAuditLog(Base):
    """
    Tracciamento completo delle modifiche per compliance GDPR.

    Registra chi, quando, cosa per ogni modifica alle prenotazioni.
    """
    __tablename__ = "booking_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    prenotazione_id = Column(Integer, ForeignKey("booking_prenotazioni.id", ondelete="SET NULL"), nullable=True, index=True)

    # Azione
    azione = Column(
        Enum(AzioneAudit, name='azione_audit_enum', create_type=False),
        nullable=False
    )

    # Chi ha eseguito
    utente_tipo = Column(
        Enum(TipoUtenteAudit, name='tipo_utente_audit_enum', create_type=False),
        nullable=False
    )
    utente_id = Column(Integer)  # ID staff/admin se applicabile
    utente_email = Column(String(255))  # Per identificazione

    # Dati modifica (JSONB per query efficienti)
    dati_precedenti = Column(JSONB, nullable=True)
    dati_nuovi = Column(JSONB, nullable=True)
    descrizione = Column(Text)  # Descrizione leggibile della modifica

    # Tracciamento tecnico
    ip_address = Column(String(45))  # IPv6 max length
    user_agent = Column(Text)

    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relazioni
    prenotazione = relationship("BookingPrenotazione", back_populates="audit_logs")

    # Indice per ricerche storiche
    __table_args__ = (
        Index('ix_booking_audit_created', 'created_at'),
    )

    def __repr__(self):
        return f"<BookingAuditLog {self.id}: {self.azione.value}>"


# ============================================================================
# CONFIGURAZIONE SISTEMA
# ============================================================================

class BookingConfig(Base):
    """
    Configurazioni del modulo prenotazioni.

    Permette di personalizzare comportamenti senza modificare codice:
    - Ore minime per annullamento/modifica
    - Testi email
    - Limiti sistema
    """
    __tablename__ = "booking_config"

    id = Column(Integer, primary_key=True)
    chiave = Column(String(100), unique=True, nullable=False, index=True)
    valore = Column(Text, nullable=False)
    tipo = Column(String(20), default="string")  # string, int, bool, json
    descrizione = Column(Text)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<BookingConfig {self.chiave}={self.valore}>"


# ============================================================================
# VALORI DEFAULT CONFIGURAZIONE
# ============================================================================

DEFAULT_BOOKING_CONFIG = {
    "ore_minime_annullamento": {
        "valore": "24",
        "tipo": "int",
        "descrizione": "Ore minime di anticipo per annullare una prenotazione"
    },
    "ore_minime_modifica": {
        "valore": "24",
        "tipo": "int",
        "descrizione": "Ore minime di anticipo per modificare una prenotazione"
    },
    "promemoria_ore_prima": {
        "valore": "24",
        "tipo": "int",
        "descrizione": "Ore prima dell'appuntamento per inviare promemoria"
    },
    "privacy_version": {
        "valore": "2025.1",
        "tipo": "string",
        "descrizione": "Versione attuale dell'informativa privacy"
    },
    "email_mittente": {
        "valore": "prenotazioni@snals.it",
        "tipo": "string",
        "descrizione": "Indirizzo email mittente per notifiche"
    },
    "max_prenotazioni_utente_giorno": {
        "valore": "2",
        "tipo": "int",
        "descrizione": "Max prenotazioni per utente nello stesso giorno"
    },
}
