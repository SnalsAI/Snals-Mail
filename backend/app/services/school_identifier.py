"""
School Identification Service.

Identifica scuole dai codici meccanografici presenti nelle email
e fornisce dettagli (nome, comune, distretto).
"""
import json
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SchoolIdentifier:
    """Servizio per identificare scuole dai codici meccanografici."""

    def __init__(self):
        """Inizializza il servizio caricando il database scuole."""
        self.schools_db: Dict[str, Dict[str, Any]] = {}
        self._load_schools_db()

    def _load_schools_db(self):
        """Carica il database delle scuole da JSON."""
        db_path = Path(__file__).parent.parent / "data" / "scuole_taranto.json"

        try:
            if db_path.exists():
                with open(db_path, 'r', encoding='utf-8') as f:
                    self.schools_db = json.load(f)
                logger.info(f"📚 Caricato database con {len(self.schools_db)} scuole")
            else:
                logger.warning(f"⚠️ Database scuole non trovato: {db_path}")
        except Exception as e:
            logger.error(f"❌ Errore caricamento database scuole: {e}")

    def extract_school_code(self, email_address: str) -> Optional[str]:
        """
        Estrae il codice meccanografico da un indirizzo email.

        Pattern comuni:
        - taic824001@istruzione.it
        - taic824001@pec.istruzione.it
        - segreteria.taic824001@scuola.it

        Args:
            email_address: Indirizzo email da analizzare

        Returns:
            Codice meccanografico se trovato, None altrimenti
        """
        if not email_address:
            return None

        # Pattern per codici meccanografici (es: TAIC824001, TAIC84300A)
        # Formato: 4 lettere + 6 caratteri alfanumerici (6 cifre o 5 cifre + 1 lettera)
        patterns = [
            r'([A-Z]{4}[A-Z0-9]{6})',  # Codice completo
            r'([a-z]{4}[a-z0-9]{6})',  # Codice minuscolo
        ]

        for pattern in patterns:
            match = re.search(pattern, email_address, re.IGNORECASE)
            if match:
                code = match.group(1).upper()
                return code

        return None

    def get_school_info(self, school_code: str) -> Optional[Dict[str, Any]]:
        """
        Recupera informazioni su una scuola dal codice meccanografico.

        Args:
            school_code: Codice meccanografico della scuola

        Returns:
            Dizionario con info scuola o None se non trovata
        """
        if not school_code:
            return None

        # Normalizza il codice (uppercase)
        code = school_code.upper()

        # Cerca nel database
        school_info = self.schools_db.get(code)

        if school_info:
            return {
                "codice": code,
                **school_info
            }

        return None

    def identify_from_email(self, sender_email: str,
                            allegati_testo: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """
        Identifica scuola completa da indirizzo email mittente.

        Args:
            sender_email: Email del mittente
            allegati_testo: Testo estratto dagli allegati (usato per proporre scuole sconosciute)

        Returns:
            Dizionario completo con info scuola o None
            Se scuola sconosciuta, restituisce dict con "pending": True e info proposte
        """
        code = self.extract_school_code(sender_email)
        if code:
            school_info = self.get_school_info(code)
            if school_info:
                logger.info(f"🏫 Scuola identificata: {school_info['nome']} ({school_info['comune']})")
                return school_info
            else:
                logger.warning(f"⚠️ Codice scuola {code} non trovato nel database")
                # Restituisce solo il codice - la proposta verrà gestita separatamente
                return {
                    "codice": code,
                    "pending": True,
                    "nome": None,
                    "comune": None
                }

        return None

    def propose_new_school(self, school_code: str,
                          allegati_testo: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """
        Propone informazioni per una nuova scuola da aggiungere.

        NON aggiunge automaticamente - restituisce solo la proposta
        che deve essere approvata dall'utente.

        Args:
            school_code: Codice meccanografico della scuola
            allegati_testo: Testo estratto dagli allegati

        Returns:
            Dizionario con proposta info scuola o None
        """
        # Verifica se già presente
        if self.get_school_info(school_code):
            return None

        logger.info(f"🔍 Generazione proposta per scuola {school_code}...")

        try:
            from app.services.school_updater import get_school_updater
            updater = get_school_updater()

            proposal = None
            source = None

            # STEP 1: Prova ad estrarre info dagli allegati
            if allegati_testo:
                extracted = updater.extract_school_from_attachments(school_code, allegati_testo)
                if extracted and extracted.get('found'):
                    proposal = extracted
                    source = "allegati"
                    logger.info(f"📄 Proposta estratta da allegati: {proposal.get('nome')}")

            # STEP 2: Se non trovato negli allegati, cerca online
            if not proposal:
                online_info = updater.search_school_online(school_code, "")
                if online_info and online_info.get('exists', False):
                    proposal = online_info
                    source = "online"
                    logger.info(f"🌐 Proposta trovata online: {proposal.get('nome')}")

            if proposal:
                return {
                    "codice": school_code,
                    "nome_proposto": proposal.get('nome', ''),
                    "comune_proposto": proposal.get('comune', '').upper(),
                    "indirizzo_proposto": proposal.get('indirizzo', ''),
                    "tipo_proposto": proposal.get('tipo', 'Istituto Comprensivo'),
                    "source": source,
                    "pending": True
                }

        except Exception as e:
            logger.error(f"❌ Errore generazione proposta scuola {school_code}: {e}")

        # Nessuna info trovata - proposta vuota
        return {
            "codice": school_code,
            "nome_proposto": None,
            "comune_proposto": None,
            "indirizzo_proposto": None,
            "tipo_proposto": None,
            "source": None,
            "pending": True
        }

    def format_school_label(self, school_info: Dict[str, Any], include_comune: bool = True) -> str:
        """
        Formatta un'etichetta leggibile per la scuola.

        Args:
            school_info: Dizionario con info scuola
            include_comune: Se includere il comune nell'etichetta

        Returns:
            Etichetta formattata (es: "IC SAN G. BOSCO (Massafra)")
        """
        if not school_info:
            return ""

        nome = school_info.get("nome", "")
        comune = school_info.get("comune", "")

        if include_comune and comune:
            return f"{nome} ({comune.title()})"

        return nome

    def get_schools_by_comune(self, comune: str) -> list[Dict[str, Any]]:
        """
        Recupera tutte le scuole di un comune specifico.

        Args:
            comune: Nome del comune

        Returns:
            Lista di scuole nel comune
        """
        comune_normalized = comune.upper().strip()

        schools = []
        for code, info in self.schools_db.items():
            if info.get("comune", "").upper() == comune_normalized:
                schools.append({
                    "codice": code,
                    **info
                })

        return schools

    def get_schools_by_district(self, district: str) -> list[Dict[str, Any]]:
        """
        Recupera tutte le scuole di un distretto specifico.

        Args:
            district: Numero distretto (es: "049")

        Returns:
            Lista di scuole nel distretto
        """
        schools = []
        for code, info in self.schools_db.items():
            if info.get("distretto") == district:
                schools.append({
                    "codice": code,
                    **info
                })

        return schools

    def search_schools(self, query: str) -> list[Dict[str, Any]]:
        """
        Cerca scuole per nome parziale o comune.

        Args:
            query: Testo da cercare

        Returns:
            Lista di scuole corrispondenti
        """
        query_normalized = query.upper().strip()

        schools = []
        for code, info in self.schools_db.items():
            nome = info.get("nome", "").upper()
            comune = info.get("comune", "").upper()

            if query_normalized in nome or query_normalized in comune:
                schools.append({
                    "codice": code,
                    **info
                })

        return schools


# Singleton instance
_school_identifier = None


def get_school_identifier() -> SchoolIdentifier:
    """Recupera istanza singleton del school identifier."""
    global _school_identifier
    if _school_identifier is None:
        _school_identifier = SchoolIdentifier()
    return _school_identifier
