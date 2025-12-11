"""
Model per email ricevute
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class AccountType(enum.Enum):
    """Tipo account email"""
    NORMALE = "normale"
    PEC = "pec"


class EmailCategory(enum.Enum):
    """
    Categorie email.

    Struttura sottocategorie:
    - comunicazione_scuola: Convocazione, Contrattazione Integrativa, Comunicazione
    - comunicazione_ust_usr: Interpello, Circolare, Comunicazione
    - comunicazione_snals_centrale: Comunicazione, Circolare
    - ricevuta_pec: Accettazione, Consegna, Ricevuta di lettura
    """
    # Comunicazioni da scuole (convocazioni, contrattazione, info)
    COMUNICAZIONE_SCUOLA = "comunicazione_scuola"

    # Comunicazioni UST/USR (interpelli, circolari)
    COMUNICAZIONE_UST_USR = "comunicazione_ust_usr"

    # Comunicazioni SNALS centrale
    COMUNICAZIONE_SNALS_CENTRALE = "comunicazione_snals_centrale"

    # Richieste iscritti
    RICHIESTA_APPUNTAMENTO = "richiesta_appuntamento"
    RICHIESTA_TESSERAMENTO = "richiesta_tesseramento"
    REVOCA_SINDACALE = "revoca_sindacale"

    # Ricevute e notifiche
    RICEVUTA_PEC = "ricevuta_pec"

    # Fatture elettroniche (Sistema di Interscambio - SDI)
    FATTURA = "fattura"

    # Errori di invio (bounce, undelivered mail)
    ERRORE_INVIO = "errore_invio"

    # Spam e pubblicità
    SPAM = "spam"

    # Altro
    INFO_GENERICHE = "info_generiche"
    VARIE = "varie"
    DA_CATEGORIZZARE = "da_categorizzare"


class EmailStatus(enum.Enum):
    """Stato elaborazione email"""
    RICEVUTA = "ricevuta"
    IN_ELABORAZIONE = "in_elaborazione"
    CATEGORIZZATA = "categorizzata"
    INTERPRETATA = "interpretata"
    AZIONE_ESEGUITA = "azione_eseguita"
    ERRORE = "errore"
    COMPLETATA = "completata"


class Email(Base):
    """Email ricevuta"""
    
    __tablename__ = "emails"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Account origine
    account_type = Column(Enum(AccountType), nullable=False)
    
    # Metadati base
    mittente = Column(Text, nullable=False, index=True)
    destinatario = Column(Text, nullable=False)
    oggetto = Column(Text)
    corpo = Column(Text)  # Corpo originale (deprecato, usare corpo_testo)
    corpo_testo = Column(Text)  # Corpo in plain text
    corpo_html = Column(Text)  # Corpo in HTML
    note = Column(Text)  # Note utente
    
    # Timestamp
    data_ricezione = Column(DateTime, nullable=False, index=True)
    data_elaborazione = Column(DateTime)
    
    # Allegati
    allegati_path = Column(JSON)
    allegati_nomi = Column(JSON)
    allegati_testo = Column(JSON)  # Testo estratto dai PDF: {"filename.pdf": "testo estratto", ...}
    
    # Categorizzazione
    # Usa String invece di Enum per evitare problemi di sincronizzazione con PostgreSQL
    categoria = Column(String(50), index=True)
    categoria_confidence = Column(Float)
    sottocategoria = Column(String(100))  # Sotto-livello: es. "GPS", "Convocazione RSU", "Interpello"
    sottocategoria_proposta = Column(String(100))  # Sottocategoria proposta dal sistema (richiede approvazione)
    motivo_proposta = Column(Text)  # Motivo per cui il sistema propone una nuova sottocategoria

    # Scuola mittente (codice meccanografico estratto)
    codice_scuola = Column(String(10), index=True)  # Es: TAIC853001

    # Stato
    stato = Column(Enum(EmailStatus), default=EmailStatus.RICEVUTA, index=True)

    # Flag speciali
    richiede_revisione = Column(Boolean, default=False)  # True se richiede revisione (es. nuova sottocategoria)
    revisionata = Column(Boolean, default=False)
    letto = Column(Boolean, default=False)  # Email letta dall'utente
    priorita = Column(Integer, default=0)
    eliminata_dal_server = Column(Boolean, default=False)  # Per spam: True se eliminata dal server ma conservata in DB
    data_eliminazione = Column(DateTime)  # Data eliminazione dal server
    
    # Relazioni
    interpretazione = relationship("Interpretazione", back_populates="email", uselist=False)
    azioni = relationship("Azione", back_populates="email")
    interpello = relationship("Interpello", back_populates="email", uselist=False)
    
    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def confidence_score(self) -> float:
        """Return categoria_confidence for API compatibility"""
        return self.categoria_confidence or 0.0

    def get_categoria_value(self) -> str:
        """
        Ottiene il valore della categoria in modo sicuro.
        Gestisce sia il caso in cui categoria sia una String che un Enum (legacy).

        Returns:
            str: Valore della categoria (es. 'convocazione_scuola')
        """
        if self.categoria is None:
            return None
        # Se è un Enum (legacy), usa .value
        if hasattr(self.categoria, 'value'):
            return self.categoria.value
        # Altrimenti è già una stringa
        return str(self.categoria)

    @property
    def allegati(self) -> list:
        """
        Restituisce lista allegati combinando path, nomi e content_type.

        Returns:
            Lista di dict: [{'filename': '...', 'path': '...', 'content_type': '...'}, ...]
        """
        if not self.allegati_nomi:
            return []

        import mimetypes
        allegati_list = []
        nomi = self.allegati_nomi if isinstance(self.allegati_nomi, list) else []
        paths = self.allegati_path if isinstance(self.allegati_path, list) else []

        for i, nome in enumerate(nomi):
            # Estrai content_type dall'estensione
            content_type, _ = mimetypes.guess_type(nome)
            if not content_type:
                content_type = 'application/octet-stream'

            allegati_list.append({
                'filename': nome,
                'path': paths[i] if i < len(paths) else None,
                'content_type': content_type
            })

        return allegati_list

    def to_dict(self):
        """Serialize email to dict for API"""
        from app.utils.datetime_utils import make_aware, get_timezone

        # Convert naive datetime to timezone-aware
        data_ricezione = self.data_ricezione
        if data_ricezione and data_ricezione.tzinfo is None:
            data_ricezione = make_aware(data_ricezione)

        return {
            'id': self.id,
            'message_id': self.message_id,
            'mittente': self.mittente,
            'destinatario': self.destinatario,
            'oggetto': self.oggetto,
            'corpo': self.corpo,
            'corpo_testo': self.corpo_testo,
            'corpo_html': self.corpo_html,
            'data_ricezione': data_ricezione.isoformat() if data_ricezione else None,
            'account_type': self.account_type.value if hasattr(self.account_type, 'value') else str(self.account_type),
            'categoria': self.categoria,  # Ora è String, non più Enum
            'sottocategoria': self.sottocategoria,
            'codice_scuola': self.codice_scuola,
            'sottocategoria_proposta': self.sottocategoria_proposta,
            'motivo_proposta': self.motivo_proposta,
            'stato': self.stato.value if hasattr(self.stato, 'value') else str(self.stato),
            'letto': self.letto or False,
            'confidence_score': self.confidence_score,
            'allegati_nomi': self.allegati_nomi,
            'allegati_path': self.allegati_path,
            'allegati_testo': self.allegati_testo,
            'note': self.note,
            'richiede_revisione': self.richiede_revisione,
            'revisionata': self.revisionata,
            'interpretazione': self.interpretazione.interpretazione_json if self.interpretazione else None,
            'azioni': [
                {
                    'id': a.id,
                    'tipo': a.tipo.value if hasattr(a.tipo, 'value') else str(a.tipo),
                    'descrizione': a.dettagli.get('descrizione', '') if a.dettagli else '',
                    'stato': a.stato.value if hasattr(a.stato, 'value') else str(a.stato)
                }
                for a in self.azioni
            ] if self.azioni else []
        }

    def __repr__(self):
        return f"<Email {self.id}: {self.oggetto[:50] if self.oggetto else 'No subject'}>"
