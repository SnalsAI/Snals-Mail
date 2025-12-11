"""
School Database Updater Service.

Aggiorna il database delle scuole usando LLM e ricerca su internet
per mantenere le informazioni aggiornate.
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests

from app.integrations.llm_client import LLMClient

logger = logging.getLogger(__name__)


class SchoolDatabaseUpdater:
    """Servizio per aggiornare il database delle scuole."""

    def __init__(self):
        """Inizializza l'updater."""
        self.llm_client = LLMClient()
        self.db_path = Path(__file__).parent.parent / "data" / "scuole_taranto.json"
        self.backup_path = Path(__file__).parent.parent / "data" / "scuole_taranto_backup.json"
        self.pending_path = Path(__file__).parent.parent / "data" / "scuole_pending.json"

    def load_pending_schools(self) -> Dict[str, Dict[str, Any]]:
        """Carica le scuole in attesa di approvazione."""
        if self.pending_path.exists():
            with open(self.pending_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_pending_schools(self, pending: Dict[str, Dict[str, Any]]):
        """Salva le scuole in attesa di approvazione."""
        with open(self.pending_path, 'w', encoding='utf-8') as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)

    def add_pending_school(self, school_code: str, proposal: Dict[str, Any]) -> bool:
        """
        Aggiunge una scuola alle proposte in attesa.

        Args:
            school_code: Codice meccanografico
            proposal: Info proposte per la scuola

        Returns:
            True se aggiunta, False se già presente
        """
        # Verifica se già nel DB principale
        if school_code in self.load_current_db():
            return False

        pending = self.load_pending_schools()
        if school_code not in pending:
            pending[school_code] = {
                **proposal,
                "created_at": datetime.now().isoformat()
            }
            self.save_pending_schools(pending)
            logger.info(f"📋 Proposta scuola {school_code} aggiunta alla coda")
            return True
        return False

    def approve_pending_school(self, school_code: str,
                               nome: Optional[str] = None,
                               comune: Optional[str] = None,
                               indirizzo: Optional[str] = None,
                               tipo: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Approva una scuola pendente e la aggiunge al database.

        L'utente può modificare i dati proposti prima dell'approvazione.

        Args:
            school_code: Codice meccanografico
            nome: Nome (usa proposta se None)
            comune: Comune (usa proposta se None)
            indirizzo: Indirizzo (usa proposta se None)
            tipo: Tipo istituto (usa proposta se None)

        Returns:
            Info scuola aggiunta o None
        """
        pending = self.load_pending_schools()
        proposal = pending.get(school_code)

        if not proposal:
            logger.warning(f"⚠️ Scuola {school_code} non trovata nelle proposte")
            return None

        # Usa i valori forniti o quelli proposti
        school_info = {
            "nome": nome or proposal.get('nome_proposto', ''),
            "comune": (comune or proposal.get('comune_proposto', '')).upper(),
            "indirizzo": indirizzo or proposal.get('indirizzo_proposto', ''),
            "tipo": tipo or proposal.get('tipo_proposto', 'Istituto Comprensivo'),
            "distretto": "",
            "source": proposal.get('source', 'manual'),
            "last_verified": datetime.now().strftime('%Y-%m-%d')
        }

        # Aggiungi al database principale
        schools_db = self.load_current_db()
        schools_db[school_code] = school_info
        self.save_db(schools_db)

        # Rimuovi dalla coda pendenti
        del pending[school_code]
        self.save_pending_schools(pending)

        logger.info(f"✅ Scuola {school_code} approvata e aggiunta: {school_info['nome']}")
        return school_info

    def reject_pending_school(self, school_code: str) -> bool:
        """
        Rifiuta una proposta di scuola.

        Args:
            school_code: Codice meccanografico

        Returns:
            True se rimossa, False altrimenti
        """
        pending = self.load_pending_schools()
        if school_code in pending:
            del pending[school_code]
            self.save_pending_schools(pending)
            logger.info(f"❌ Proposta scuola {school_code} rifiutata")
            return True
        return False

    def load_current_db(self) -> Dict[str, Dict[str, Any]]:
        """Carica il database corrente."""
        if self.db_path.exists():
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_db(self, schools_db: Dict[str, Dict[str, Any]]):
        """Salva il database aggiornato."""
        # Backup del database corrente
        if self.db_path.exists():
            with open(self.backup_path, 'w', encoding='utf-8') as f:
                current = self.load_current_db()
                json.dump(current, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Backup creato: {self.backup_path}")

        # Salva nuovo database
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(schools_db, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Database aggiornato: {self.db_path}")

    def search_school_online(self, school_code: str, school_name: str) -> Optional[Dict[str, Any]]:
        """
        Cerca informazioni aggiornate su una scuola online.

        Args:
            school_code: Codice meccanografico della scuola
            school_name: Nome della scuola

        Returns:
            Dizionario con informazioni aggiornate o None
        """
        prompt = f"""Cerca informazioni aggiornate per la scuola italiana con:
- Codice meccanografico: {school_code}
- Nome: {school_name}

Cerca sul web e verifica:
1. Il nome ufficiale corrente della scuola
2. Il comune dove si trova
3. L'indirizzo completo
4. Il tipo di istituto (es: "Istituto Comprensivo")
5. Se la scuola esiste ancora o è stata accorpata/soppressa

Rispondi in formato JSON:
{{
  "exists": true/false,
  "nome": "nome ufficiale",
  "comune": "COMUNE IN MAIUSCOLO",
  "indirizzo": "indirizzo completo",
  "tipo": "tipo istituto",
  "distretto": "numero distretto se disponibile",
  "note": "eventuali note (accorpamento, cambio nome, ecc.)",
  "last_verified": "data odierna in formato YYYY-MM-DD"
}}

Se la scuola non esiste più o non trovi informazioni, imposta exists: false."""

        try:
            response = self.llm_client.generate(prompt, max_tokens=500)

            # Estrai JSON dalla risposta
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                school_info = json.loads(json_match.group())
                logger.info(f"🔍 Informazioni trovate per {school_code}: {school_info.get('nome', 'N/A')}")
                return school_info
            else:
                logger.warning(f"⚠️ Risposta LLM non contiene JSON valido per {school_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Errore ricerca online per {school_code}: {e}")
            return None

    def verify_school_with_llm(self, school_code: str, current_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifica informazioni di una scuola usando LLM.

        Args:
            school_code: Codice meccanografico
            current_info: Informazioni correnti nel database

        Returns:
            Informazioni verificate/aggiornate
        """
        prompt = f"""Verifica le informazioni di questa scuola italiana:

Codice meccanografico: {school_code}
Nome attuale nel DB: {current_info.get('nome', 'N/A')}
Comune attuale nel DB: {current_info.get('comune', 'N/A')}
Indirizzo attuale nel DB: {current_info.get('indirizzo', 'N/A')}
Tipo: {current_info.get('tipo', 'N/A')}

Verifica se queste informazioni sono corrette e aggiornate.
Controlla anche se:
- La scuola ha cambiato nome
- La scuola è stata accorpata ad un'altra
- L'indirizzo è cambiato
- La scuola è stata soppressa

Rispondi in formato JSON con le informazioni verificate:
{{
  "verified": true/false,
  "nome": "nome verificato",
  "comune": "COMUNE IN MAIUSCOLO",
  "indirizzo": "indirizzo verificato",
  "tipo": "tipo istituto",
  "distretto": "{current_info.get('distretto', '')}",
  "changes": ["lista di eventuali cambiamenti rilevati"],
  "confidence": 0.0-1.0,
  "last_verified": "{datetime.now().strftime('%Y-%m-%d')}"
}}"""

        try:
            response = self.llm_client.generate(prompt, max_tokens=400)

            # Estrai JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                verified_info = json.loads(json_match.group())

                # Merge con info correnti
                updated_info = {**current_info, **verified_info}

                if verified_info.get('changes'):
                    logger.info(f"📝 Cambiamenti rilevati per {school_code}: {verified_info['changes']}")

                return updated_info
            else:
                logger.warning(f"⚠️ Risposta LLM non contiene JSON per {school_code}")
                return current_info

        except Exception as e:
            logger.error(f"❌ Errore verifica LLM per {school_code}: {e}")
            return current_info

    def update_school(self, school_code: str, current_info: Dict[str, Any],
                     force_online_search: bool = False) -> Dict[str, Any]:
        """
        Aggiorna informazioni di una singola scuola.

        Args:
            school_code: Codice meccanografico
            current_info: Informazioni correnti
            force_online_search: Se forzare ricerca online

        Returns:
            Informazioni aggiornate
        """
        logger.info(f"🔄 Aggiornamento scuola {school_code}...")

        # Verifica con LLM se non è stata verificata di recente
        last_verified = current_info.get('last_verified')
        needs_verification = True

        if last_verified and not force_online_search:
            try:
                verified_date = datetime.strptime(last_verified, '%Y-%m-%d')
                days_since_verification = (datetime.now() - verified_date).days
                if days_since_verification < 90:  # 3 mesi
                    needs_verification = False
                    logger.info(f"✓ {school_code} verificata {days_since_verification} giorni fa, skip")
            except Exception:
                pass

        if needs_verification or force_online_search:
            # Cerca informazioni aggiornate
            if force_online_search:
                online_info = self.search_school_online(school_code, current_info.get('nome', ''))
                if online_info and online_info.get('exists', False):
                    return online_info

            # Verifica con LLM
            verified_info = self.verify_school_with_llm(school_code, current_info)
            return verified_info

        return current_info

    def update_all_schools(self, force_online_search: bool = False,
                          limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Aggiorna tutte le scuole nel database.

        Args:
            force_online_search: Se forzare ricerca online per tutte
            limit: Limita numero di scuole da aggiornare (per test)

        Returns:
            Statistiche aggiornamento
        """
        logger.info("🚀 Inizio aggiornamento database scuole...")

        schools_db = self.load_current_db()
        total = len(schools_db)

        if limit:
            logger.info(f"📊 Limitato a {limit} scuole per test")
            schools_to_update = list(schools_db.items())[:limit]
        else:
            schools_to_update = list(schools_db.items())

        updated_count = 0
        changed_count = 0
        error_count = 0

        updated_db = {}

        for code, info in schools_to_update:
            try:
                updated_info = self.update_school(code, info, force_online_search)
                updated_db[code] = updated_info
                updated_count += 1

                # Verifica se ci sono stati cambiamenti
                if updated_info.get('changes'):
                    changed_count += 1

                # Log progressivo
                if updated_count % 10 == 0:
                    logger.info(f"📈 Progresso: {updated_count}/{len(schools_to_update)} scuole elaborate")

            except Exception as e:
                logger.error(f"❌ Errore aggiornamento {code}: {e}")
                updated_db[code] = info  # Mantieni info correnti
                error_count += 1

        # Aggiungi scuole non elaborate (se limit applicato)
        if limit:
            remaining = {k: v for k, v in schools_db.items() if k not in updated_db}
            updated_db.update(remaining)

        # Salva database aggiornato
        self.save_db(updated_db)

        stats = {
            "total_schools": total,
            "updated": updated_count,
            "changed": changed_count,
            "errors": error_count,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"✅ Aggiornamento completato: {stats}")
        return stats

    def extract_school_from_attachments(self, school_code: str, allegati_testo: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Estrae informazioni sulla scuola dal testo degli allegati.

        Cerca nell'intestazione/piè di pagina dei documenti:
        - Nome dell'istituto
        - Comune
        - Indirizzo

        Args:
            school_code: Codice meccanografico da cercare
            allegati_testo: Dict {filename: testo_estratto}

        Returns:
            Dizionario con info scuola o None
        """
        if not allegati_testo:
            return None

        # Combina tutto il testo degli allegati (primi 3000 caratteri di ciascuno)
        combined_text = ""
        for filename, testo in allegati_testo.items():
            if testo:
                # Prendi intestazione (primi 1500 char) e piè di pagina (ultimi 1500 char)
                combined_text += testo[:1500] + "\n" + testo[-1500:] + "\n\n"

        if not combined_text.strip():
            return None

        prompt = f"""Analizza questo testo estratto da documenti scolastici e trova le informazioni sulla scuola con codice {school_code}.

TESTO DA ANALIZZARE:
{combined_text[:4000]}

Cerca nei documenti:
1. Il nome ufficiale dell'istituto (es: "ISTITUTO COMPRENSIVO GIOVANNI XXIII", "I.C. SAN GIOVANNI BOSCO")
2. Il comune dove si trova
3. L'indirizzo se presente
4. Il tipo di istituto (IC = Istituto Comprensivo, LS = Liceo Scientifico, ecc.)

Il codice meccanografico {school_code} corrisponde alla provincia di Taranto (TA).

Rispondi SOLO con JSON valido:
{{
  "found": true/false,
  "nome": "NOME COMPLETO ISTITUTO",
  "comune": "COMUNE IN MAIUSCOLO",
  "indirizzo": "indirizzo se trovato, altrimenti stringa vuota",
  "tipo": "tipo istituto (es: Istituto Comprensivo)"
}}

Se non trovi informazioni chiare sulla scuola, rispondi con {{"found": false}}"""

        try:
            response = self.llm_client.generate(prompt, max_tokens=300)

            # Estrai JSON dalla risposta
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                school_info = json.loads(json_match.group())
                if school_info.get('found') and school_info.get('nome'):
                    logger.info(f"📄 Scuola estratta da allegati: {school_info['nome']}")
                    return school_info

        except Exception as e:
            logger.warning(f"⚠️ Errore estrazione scuola da allegati: {e}")

        return None

    def add_new_school(self, school_code: str, force_search: bool = True,
                       allegati_testo: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """
        Aggiunge una nuova scuola al database.

        Processo:
        1. Verifica se già presente nel DB
        2. Prova ad estrarre info dagli allegati email
        3. Se non trova, cerca online
        4. Aggiunge al database

        Args:
            school_code: Codice meccanografico della nuova scuola
            force_search: Se forzare ricerca online
            allegati_testo: Testo estratto dagli allegati (opzionale)

        Returns:
            Informazioni della scuola aggiunta o None
        """
        logger.info(f"➕ Aggiunta nuova scuola: {school_code}")

        schools_db = self.load_current_db()

        if school_code in schools_db:
            logger.info(f"✓ Scuola {school_code} già presente nel database")
            return schools_db[school_code]

        school_info = None
        source = None

        # STEP 1: Prova ad estrarre info dagli allegati
        if allegati_testo:
            logger.info(f"📄 Tentativo estrazione info da allegati per {school_code}...")
            extracted = self.extract_school_from_attachments(school_code, allegati_testo)
            if extracted and extracted.get('found'):
                school_info = extracted
                source = "allegati"
                logger.info(f"✅ Info estratte da allegati: {school_info.get('nome')}")

        # STEP 2: Se non trovato, cerca online
        if not school_info and force_search:
            logger.info(f"🌐 Ricerca online per {school_code}...")
            online_info = self.search_school_online(school_code, "")
            if online_info and online_info.get('exists', False):
                school_info = online_info
                source = "online"
                logger.info(f"✅ Info trovate online: {school_info.get('nome')}")

        if school_info:
            # Pulisci e normalizza le informazioni
            clean_info = {
                "nome": school_info.get('nome', '').strip(),
                "comune": school_info.get('comune', '').upper().strip(),
                "indirizzo": school_info.get('indirizzo', '').strip(),
                "tipo": school_info.get('tipo', 'Istituto Comprensivo'),
                "distretto": school_info.get('distretto', ''),
                "source": source,
                "last_verified": datetime.now().strftime('%Y-%m-%d')
            }

            # Aggiungi al database
            schools_db[school_code] = clean_info
            self.save_db(schools_db)

            logger.info(f"✅ Scuola {school_code} aggiunta da {source}: {clean_info['nome']}")
            return clean_info

        logger.warning(f"❌ Impossibile aggiungere scuola {school_code}")
        return None

    def remove_school(self, school_code: str) -> bool:
        """
        Rimuove una scuola dal database (es: scuola soppressa).

        Args:
            school_code: Codice meccanografico da rimuovere

        Returns:
            True se rimossa, False altrimenti
        """
        schools_db = self.load_current_db()

        if school_code in schools_db:
            school_name = schools_db[school_code].get('nome', school_code)
            del schools_db[school_code]
            self.save_db(schools_db)
            logger.info(f"🗑️ Scuola rimossa: {school_code} - {school_name}")
            return True

        logger.warning(f"⚠️ Scuola {school_code} non trovata nel database")
        return False


# Singleton instance
_school_updater = None


def get_school_updater() -> SchoolDatabaseUpdater:
    """Recupera istanza singleton del school updater."""
    global _school_updater
    if _school_updater is None:
        _school_updater = SchoolDatabaseUpdater()
    return _school_updater
