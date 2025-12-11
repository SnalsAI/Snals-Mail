"""
Classificatore rule-based per email SNALS
Usa regex e logica deterministica per identificare sender type e categoria
"""

import re
from typing import Tuple, Optional, Dict, List
from datetime import datetime
import logging
from difflib import get_close_matches
import json
from pathlib import Path
from app.services.school_identifier import get_school_identifier

logger = logging.getLogger(__name__)

# Path al file di configurazione categorie
CATEGORIES_CONFIG_PATH = Path("/app/config/categories.json")


class RuleBasedClassifier:
    """Classificatore deterministico basato su regex e logica"""

    # Regex per identificare scuole (codice meccanografico)
    # Formato: 4 lettere + 6 caratteri alfanumerici (6 cifre o 5 cifre + 1 lettera)
    SCUOLA_PATTERN = re.compile(r'[a-z]{4}[a-z0-9]{6}@(pec\.)?istruzione\.it', re.IGNORECASE)

    def _load_predefined_subcategories(self) -> Dict[str, List[str]]:
        """
        Carica le sottocategorie predefinite dal file di configurazione.

        Returns:
            Dict con categoria -> lista sottocategorie
        """
        try:
            if CATEGORIES_CONFIG_PATH.exists():
                with open(CATEGORIES_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {
                        cat_key: cat_data.get('subcategories', [])
                        for cat_key, cat_data in config.items()
                    }
        except Exception as e:
            logger.warning(f"Impossibile caricare sottocategorie predefinite: {e}")

        # Fallback: sottocategorie hardcoded (corrispondono ai default)
        return {
            "comunicazione_scuola": ["Convocazione", "Rinvio", "Contrattazione Integrativa", "Comunicazione"],
            "comunicazione_ust_usr": ["Interpello", "GPS", "Convocazioni supplenze", "Utilizzazioni", "Assegnazioni provvisorie", "Graduatorie", "Circolare"],
            "comunicazione_snals_centrale": ["Circolare", "Comunicazione", "Aggiornamento normativo"],
            "ricevuta_pec": ["Accettazione", "Consegna", "Ricevuta di lettura"],
            "spam": [],
            "varie": []
        }

    def _find_best_subcategory_match(
        self,
        candidate: str,
        categoria: str,
        cutoff: float = 0.6
    ) -> Tuple[Optional[str], bool, Optional[str]]:
        """
        Trova la migliore corrispondenza tra le sottocategorie predefinite.

        Args:
            candidate: Sottocategoria candidata
            categoria: Categoria principale
            cutoff: Soglia di similarità (0-1)

        Returns:
            (sottocategoria_migliore, is_exact_match, proposta)
            - sottocategoria_migliore: La migliore tra quelle predefinite
            - is_exact_match: True se è una match esatta
            - proposta: La sottocategoria proposta se non esiste (None se match esatta)
        """
        predefined = self._predefined_subcategories.get(categoria, [])

        if not predefined:
            # Nessuna sottocategoria predefinita per questa categoria
            return None, False, None

        # Check exact match (case insensitive)
        for subcat in predefined:
            if subcat.lower() == candidate.lower():
                return subcat, True, None

        # Trova le migliori matches usando similarità di stringa
        matches = get_close_matches(candidate, predefined, n=1, cutoff=cutoff)

        if matches:
            best_match = matches[0]
            # Proponi la nuova sottocategoria se la similarità non è perfetta
            return best_match, False, candidate

        # Nessuna match: usa la prima predefinita come default e proponi la nuova
        default = predefined[0] if predefined else None
        return default, False, candidate

    # Pattern UST/USR
    UST_PATTERNS = [
        r'uspta@',
        r'usprpu@',
        r'usp\.ta@',
        r'usr\.puglia@',
        r'aoouspta@',
        r'aoousr@',
    ]

    # Pattern PEC busta
    PEC_BUSTA_PATTERNS = [
        r'posta-certificata@legalmail\.it',
        r'postacert@',
    ]

    # Keywords convocazione FORTI (richiedono solo keyword per alta confidence)
    CONVOCAZIONE_KEYWORDS_STRONG = [
        r'\bconvocazione\b',
        r'\bè convocata\b',
        r'\bsono convocati\b',
        r'\bsi convoca\b',
        r'\briunione RSU\b',
        r'\briunione OO\.SS\b',
        r'\bassemblea sindacale\b',
        r'\btavolo di contrattazione\b',
        r'\bincontro OO\.SS\b',
        r'\bincontro sindacale\b',
        # Variazioni di convocazioni esistenti
        r'\bvariazione\s+orario\s+convocazione\b',
        r'\bmodifica\s+orario\s+convocazione\b',
        r'\brinvio\s+convocazione\b',
        r'\bannullamento\s+convocazione\b',
        r'\brettifica\s+convocazione\b',
    ]

    # Keywords convocazione DEBOLI (richiedono data+ora per conferma)
    CONVOCAZIONE_KEYWORDS_WEAK = [
        r'\binvito\b',
        r'\bsi invitano\b',
        r'\briunione\b',
        r'\bincontro\b',
        r'\btavolo\b',
        r'\bconfronto\b',
        r'\bassemblea\b',
        r'\bincontro con\b',
        r'\bOO\.SS\.\b',
        r'\bRSU\b',
    ]

    # Keywords che NON sono convocazioni se non c'è data/ora
    COMUNICAZIONE_CONTRACT_KEYWORDS = [
        r'\binvito sottoscrizione\b',
        r'\bsottoscrizione contratto\b',
        r'\bfirma contratto\b',
        r'\bpubblicazione contratto\b',
    ]

    # Regex per date
    DATE_PATTERNS = [
        r'\b(\d{1,2}/\d{1,2}/\d{4})\b',
        r'\b(\d{1,2}-\d{1,2}-\d{4})\b',
        r'\b(\d{1,2}\s+[A-Za-zàèéìòù]+\s+\d{4})\b',
    ]

    # Regex per ore
    TIME_PATTERNS = [
        r'\b(ore\s+)?\d{1,2}[:.]\d{2}\b',
    ]

    # Pattern per luoghi
    PLACE_KEYWORDS = [
        r'\bpresso\b',
        r'\bAula Magna\b',
        r'\bSala riunioni\b',
        r'\bUfficio del Dirigente\b',
        r'\bsede centrale\b',
        r'\bplesso\b',
        r'\bsuccursale\b',
    ]

    # Pattern per modalità
    MODALITY_KEYWORDS = [
        r'\bin modalità\b',
        r'\bmodalità a distanza\b',
        r'\bin presenza\b',
        r'\bda remoto\b',
        r'\bmista\b',
    ]

    # Pattern per piattaforme
    PLATFORM_KEYWORDS = [
        r'\bGoogle Meet\b',
        r'\bMicrosoft Teams\b',
        r'\bZoom\b',
        r'\bTeams\b',
        r'\bMeet\b',
        r'https://.*meet',
        r'https://.*zoom',
        r'https://.*teams',
    ]

    # Keywords comunicazione (non convocazione)
    COMUNICAZIONE_KEYWORDS = [
        r'\bdecreto\b',
        r'\bprovvedimento\b',
        r'\bdisposizione\b',
        r'\bcomunicazione\b',
        r'\btrasmissione\b',
        r'\binvio di\b',
        r'\bsi trasmette\b',
        r'\bpubblicazione\b',
        r'\bsi pubblicano\b',
        r'\bsi rende noto\b',
        r'\bgraduatoria\b',
        r'\belenco\b',
        r'\bbollettino\b',
        r'\bdisponibilità\b',
        r'\borganico\b',
        r'\bcontrattazione\b',
        r'\bcontrattazione integrativa\b',
        r'\bcontratto integrativo\b',
        r'\bdecreto di nomina\b',
        r'\bpresa d\'atto\b',
        r'\brettifica\b',
        r'\bintegrazione\b',
        r'\bconferimento supplenze\b',
        r'\bindividuazioni\b',
        r'\bassegnazioni\b',
        r'\binterpello\b',
    ]

    def __init__(self):
        """Inizializza il classificatore e carica le sottocategorie predefinite"""
        # Load predefined subcategories
        self._predefined_subcategories = self._load_predefined_subcategories()

        # Compile regex patterns for efficiency
        self.convocazione_strong_regex = re.compile('|'.join(self.CONVOCAZIONE_KEYWORDS_STRONG), re.IGNORECASE)
        self.convocazione_weak_regex = re.compile('|'.join(self.CONVOCAZIONE_KEYWORDS_WEAK), re.IGNORECASE)
        self.contract_keywords_regex = re.compile('|'.join(self.COMUNICAZIONE_CONTRACT_KEYWORDS), re.IGNORECASE)
        self.date_regex = re.compile('|'.join(self.DATE_PATTERNS), re.IGNORECASE)
        self.time_regex = re.compile('|'.join(self.TIME_PATTERNS), re.IGNORECASE)
        self.place_regex = re.compile('|'.join(self.PLACE_KEYWORDS), re.IGNORECASE)
        self.modality_regex = re.compile('|'.join(self.MODALITY_KEYWORDS), re.IGNORECASE)
        self.platform_regex = re.compile('|'.join(self.PLATFORM_KEYWORDS), re.IGNORECASE)
        self.comunicazione_regex = re.compile('|'.join(self.COMUNICAZIONE_KEYWORDS), re.IGNORECASE)

    def identify_sender_type(self, mittente: str, oggetto: str) -> str:
        """
        Identifica il tipo di mittente
        Returns: "USP_UST", "SCUOLA", "PEC_BUSTA", "SNALS_CENTRALE", "ALTRO"
        """
        mittente_lower = mittente.lower()
        oggetto_lower = oggetto.lower()

        # ============================================================
        # PRIORITÀ 1: Estrai mittente reale da "Per conto di:" nelle PEC
        # Pattern: "Per conto di: xxx@pec.istruzione.it" <posta-certificata@legalmail.it>
        # ============================================================
        per_conto_match = re.search(r'per conto di:\s*([^\s<>"]+@[^\s<>"]+)', mittente_lower)
        if per_conto_match:
            real_sender = per_conto_match.group(1)
            logger.info(f"📧 Estratto mittente reale da 'Per conto di:': {real_sender}")

            # Check se il mittente reale è una scuola
            if self.SCUOLA_PATTERN.search(real_sender):
                logger.info(f"✅ Identificato SCUOLA (da 'Per conto di:'): {real_sender}")
                return "SCUOLA"

            # Check se il mittente reale è UST/USR
            for pattern in self.UST_PATTERNS:
                if re.search(pattern, real_sender):
                    logger.info(f"✅ Identificato USP_UST (da 'Per conto di:'): {real_sender}")
                    return "USP_UST"

            # Generic @istruzione.it
            if '@pec.istruzione.it' in real_sender or '@istruzione.it' in real_sender:
                logger.info(f"✅ Identificato SCUOLA (da 'Per conto di:' - dominio istruzione): {real_sender}")
                return "SCUOLA"

        # ============================================================
        # PRIORITÀ 2: Check PEC busta (senza "Per conto di:")
        # ============================================================
        for pattern in self.PEC_BUSTA_PATTERNS:
            if re.search(pattern, mittente_lower):
                # Verifica anche subject
                if oggetto_lower.startswith('posta certificata'):
                    logger.info(f"Identificato PEC_BUSTA: {mittente}")
                    return "PEC_BUSTA"

        # Check SNALS (centrale e territoriali)
        # Pattern per strutture SNALS: snals.ta@, snalsmilano@, snalstaranto@, etc.
        snals_patterns = [
            r'info@snals\.it',
            r'@snalsconfsal\.it',
            r'snals[a-z]*@',           # snalsmilano@, snalstaranto@, etc.
            r'snals\.[a-z]{2,}@',      # snals.ta@, snals.mi@, etc.
            r'@snals[a-z]*\.it',       # @snalsmilano.it, etc.
            r'ufficio.*snals',         # ufficioscuolasnalsmilano@
        ]
        for pattern in snals_patterns:
            if re.search(pattern, mittente_lower):
                logger.info(f"Identificato SNALS (struttura): {mittente}")
                return "SNALS_CENTRALE"

        # Check UST/USR
        for pattern in self.UST_PATTERNS:
            if re.search(pattern, mittente_lower):
                logger.info(f"Identificato USP_UST: {mittente}")
                return "USP_UST"

        # Check if contains ministerial keywords in sender name
        if any(keyword in oggetto_lower for keyword in ['ufficio scolastico', 'ambito territoriale', 'aoouspta', 'aoousr']):
            if '@istruzione.it' in mittente_lower or '@postacert.istruzione.it' in mittente_lower:
                logger.info(f"Identificato USP_UST (da oggetto): {mittente}")
                return "USP_UST"

        # Check scuola (codice meccanografico)
        if self.SCUOLA_PATTERN.search(mittente_lower):
            logger.info(f"Identificato SCUOLA: {mittente}")
            return "SCUOLA"

        # Generic @istruzione.it (fallback)
        if '@istruzione.it' in mittente_lower or '@postacert.istruzione.it' in mittente_lower:
            logger.warning(f"Dominio @istruzione.it ma non identificato specificamente: {mittente}")
            return "SCUOLA"  # Default to scuola if not UST

        return "ALTRO"

    def detect_convocazione_signals(self, text: str) -> Dict[str, bool]:
        """
        Rileva i segnali di convocazione in un testo
        Returns dict con flag per ogni segnale
        """
        signals = {
            'has_convocazione_strong': bool(self.convocazione_strong_regex.search(text)),
            'has_convocazione_weak': bool(self.convocazione_weak_regex.search(text)),
            'has_contract_keyword': bool(self.contract_keywords_regex.search(text)),
            'has_date': bool(self.date_regex.search(text)),
            'has_time': bool(self.time_regex.search(text)),
            'has_place': bool(self.place_regex.search(text)),
            'has_modality': bool(self.modality_regex.search(text)),
            'has_platform': bool(self.platform_regex.search(text)),
            'has_comunicazione_keyword': bool(self.comunicazione_regex.search(text)),
        }
        return signals

    def extract_subcategory(
        self,
        categoria: str,
        mittente: str,
        oggetto: str,
        corpo: str
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Estrae la sottocategoria in base alla categoria e al contenuto dell'email.
        Valida la sottocategoria estratta contro quelle predefinite.

        Args:
            categoria: Categoria principale dell'email
            mittente: Email del mittente
            oggetto: Oggetto dell'email
            corpo: Corpo dell'email

        Returns:
            Tuple (sottocategoria_da_usare, proposta_info)
            - sottocategoria_da_usare: La sottocategoria validata da usare
            - proposta_info: Dict con informazioni sulla proposta (None se match esatta)
                {
                    'proposta': str,  # La sottocategoria proposta
                    'candidata': str,  # La sottocategoria candidata originale
                    'motivo': str,    # Motivo della proposta
                }
        """
        full_text = f"{oggetto} {corpo}".lower()

        # Try to identify school if sender is from school domain
        school_info = None
        if categoria == "comunicazione_scuola":
            try:
                school_identifier = get_school_identifier()
                school_info = school_identifier.identify_from_email(mittente)
            except Exception as e:
                logger.warning(f"Errore identificazione scuola: {e}")

        # Genera sottocategoria candidata in base ai pattern
        candidate_subcat = None

        if categoria == "comunicazione_ust_usr":
            # Pattern per sottocategorie UST/USR
            if re.search(r'\bGPS\b', full_text, re.IGNORECASE):
                # Check for year
                year_match = re.search(r'\bGPS.*?(\d{2}/\d{2})\b', full_text, re.IGNORECASE)
                if year_match:
                    candidate_subcat = f"GPS {year_match.group(1)}"
                else:
                    candidate_subcat = "GPS"
            elif re.search(r'\bconvocazion[ei].*?supplenz[ae]', full_text, re.IGNORECASE):
                candidate_subcat = "Convocazioni supplenze"
            elif re.search(r'\butilizzazion[ei]', full_text, re.IGNORECASE):
                candidate_subcat = "Utilizzazioni"
            elif re.search(r'\bassegnazion[ei]\s+provvisor[ie]', full_text, re.IGNORECASE):
                candidate_subcat = "Assegnazioni provvisorie"
            elif re.search(r'\bgraduatori[ae]', full_text, re.IGNORECASE):
                candidate_subcat = "Graduatorie"
            elif re.search(r'\binterpello', full_text, re.IGNORECASE):
                candidate_subcat = "Interpello"

        elif categoria == "comunicazione_scuola":
            # Pattern per sottocategorie comunicazioni scuola
            oggetto_lower = oggetto.lower()

            # PRIORITÀ 0: Se oggetto inizia con "Comunicazione" → è una comunicazione informativa
            # Queste NON sono convocazioni anche se contengono keyword come "contrattazione"
            is_comunicazione_informativa = (
                oggetto_lower.startswith('comunicazione ') or
                oggetto_lower.startswith('trasmissione ') or
                oggetto_lower.startswith('invio ') or
                oggetto_lower.startswith('si trasmette') or
                re.search(r'\bintegrazione\s+finanziament', full_text, re.IGNORECASE) or
                re.search(r'\bpubblicazione\s+(contratto|accordo)', full_text, re.IGNORECASE)
            )

            # PRIORITÀ 1: Rinvio/annullamento
            if re.search(r'\brinvio\b|\brinviata?\b|\bannullat[aoi]?\b|\bsospesa?\b|\bposticipat[aoi]?\b', full_text, re.IGNORECASE):
                candidate_subcat = "Rinvio"

            # PRIORITÀ 2: Comunicazione informativa (senza evento)
            elif is_comunicazione_informativa:
                # Verifica se contiene anche info su contrattazione integrativa
                if re.search(r'\bcontrattazione\s+integrativa|\bMOF\b|\bFIS\b', full_text, re.IGNORECASE):
                    candidate_subcat = "Contrattazione Integrativa"
                else:
                    candidate_subcat = "Comunicazione"

            # PRIORITÀ 3: Convocazione (richiede keyword esplicite)
            elif re.search(r'\bconvocazion[ei]\b|\bconvocat[aoi]\b|\bsi\s+convoca\b', full_text, re.IGNORECASE):
                candidate_subcat = "Convocazione"
            elif re.search(r'\bRSU\b|\bassemblea\s+sindacale', full_text, re.IGNORECASE):
                # RSU/assemblea sono convocazioni solo se c'è anche data+ora
                if self.date_regex.search(full_text) and self.time_regex.search(full_text):
                    candidate_subcat = "Convocazione"
                else:
                    candidate_subcat = "Comunicazione"

            # PRIORITÀ 4: Contrattazione integrativa
            elif re.search(r'\bcontrattazione\s+integrativa|\btavolo.*?contrattazione|\bfondo.*?miglioramento.*?offerta|\bfondo\s+MOF\b|\bMOF\s+\d{4}|\bFIS\b.*?\d{4}', full_text, re.IGNORECASE):
                candidate_subcat = "Contrattazione Integrativa"

            # DEFAULT: Comunicazione
            else:
                candidate_subcat = "Comunicazione"

            # Non aggiungere nome scuola - il mittente identifica già la scuola
            # La sottocategoria deve essere pulita e normalizzata

        elif categoria == "comunicazione_snals_centrale":
            # Pattern per sottocategorie SNALS centrale
            if re.search(r'\bcircolare', full_text, re.IGNORECASE):
                candidate_subcat = "Circolare"
            elif re.search(r'\baggiornamento\s+normativ[oi]', full_text, re.IGNORECASE):
                candidate_subcat = "Aggiornamento normativo"
            else:
                candidate_subcat = "Comunicazione"

        # Se non abbiamo una sottocategoria candidata, restituisci None
        if not candidate_subcat:
            return None, None

        # Valida la sottocategoria candidata contro quelle predefinite
        best_match, is_exact, proposta = self._find_best_subcategory_match(
            candidate_subcat, categoria
        )

        # Se è una match esatta, nessuna proposta
        if is_exact:
            logger.info(f"✅ Sottocategoria '{candidate_subcat}' match esatta per {categoria}")
            return best_match, None

        # Se c'è una proposta, prepara le informazioni
        if proposta:
            proposta_info = {
                'proposta': proposta,
                'candidata': candidate_subcat,
                'motivo': f"La sottocategoria '{proposta}' non è tra quelle predefinite per '{categoria}'. "
                         f"Viene usata temporaneamente '{best_match}' (migliore match disponibile)."
            }
            logger.warning(f"⚠️ Proposta nuova sottocategoria per {categoria}: '{proposta}' → usando '{best_match}'")
            return best_match, proposta_info

        # Nessuna proposta (usata sottocategoria predefinita simile)
        logger.info(f"✅ Sottocategoria '{candidate_subcat}' → '{best_match}' (fuzzy match)")
        return best_match, None

    def classify_email(
        self,
        mittente: str,
        oggetto: str,
        corpo: str
    ) -> Tuple[str, float, str, Optional[str], Optional[Dict]]:
        """
        Classifica email usando regole deterministiche

        Returns:
            (categoria, confidence, motivazione, sottocategoria, proposta_info)
            - categoria: Categoria principale
            - confidence: Livello di confidenza (0-1)
            - motivazione: Spiegazione della classificazione
            - sottocategoria: Sottocategoria assegnata (validata)
            - proposta_info: Informazioni sulla proposta di nuova sottocategoria (None se non c'è proposta)
        """
        # PRIORITÀ 0: Rileva email bounce/errore invio (Undelivered Mail)
        if self._is_bounce_email(mittente, oggetto, corpo):
            return "errore_invio", 0.98, "Email bounce/errore consegna", None, None

        # PRIORITÀ MASSIMA: Rileva ricevute di lettura (Read receipts)
        # Classificate come ricevuta_pec con sottocategoria "Ricevuta di lettura"
        if self._is_read_receipt(oggetto, corpo):
            return "ricevuta_pec", 0.98, "Ricevuta di lettura", "Ricevuta di lettura", None

        # PRIORITÀ ALTA: Rileva ricevute/buste PEC dal corpo
        # Il corpo inizia con "Messaggio di posta certificata" = è solo la busta, non il contenuto
        corpo_lower = corpo.lower().strip() if corpo else ""
        if corpo_lower.startswith("messaggio di posta certificata"):
            return "ricevuta_pec", 0.95, "Busta PEC (corpo inizia con 'Messaggio di posta certificata')", "Consegna", None

        # PRIORITÀ ALTA: Rileva risposte personali (Re: con contenuto breve tipo "non posso partecipare")
        oggetto_lower = oggetto.lower() if oggetto else ""
        if oggetto_lower.startswith("re:") or oggetto_lower.startswith("r:"):
            # Check se è una risposta di assenza/indisponibilità
            assenza_keywords = ['impossibilit', 'non potr', 'assenza', 'non partecip', 'sarò assente', 'non sarò presente']
            if any(kw in corpo_lower for kw in assenza_keywords):
                return "altro", 0.90, "Risposta personale (comunicazione assenza)", "Risposta personale", None

        # Identify sender type
        sender_type = self.identify_sender_type(mittente, oggetto)

        # Caso speciale: PEC busta - try to identify real sender from subject/body
        if sender_type == "PEC_BUSTA":
            # Check if subject contains UST/USR indicators
            if any(pattern in oggetto.lower() for pattern in ['aoouspta', 'aoousr', 'usp.ta', 'usr.puglia']):
                # It's from UST/USR wrapped in PEC
                sottocategoria, proposta_info = self.extract_subcategory("comunicazione_ust_usr", mittente, oggetto, corpo)
                return "comunicazione_ust_usr", 0.85, "PEC busta da UST/USR (rilevato da subject)", sottocategoria, proposta_info

            # PRIORITÀ: Check revoca sindacale PRIMA di restituire "varie"
            # Le revoche spesso arrivano via PEC con oggetto chiaro
            if self._is_revoca_sindacale(oggetto, corpo):
                return "revoca_sindacale", 0.95, "Revoca delega sindacale rilevata (da PEC)", None, None

            # MIGLIORIA: Se il corpo contiene testo estratto da allegati, analizzalo
            # prima di restituire "varie"
            if len(corpo.strip()) > 200:  # Il corpo ha contenuto sostanziale (probabilmente da PDF)
                logger.info("📧 PEC busta con corpo > 200 caratteri - analizzo contenuto prima di restituire 'varie'")
                # Continua con l'analisi normale invece di restituire subito "varie"
                pass
            else:
                # Default: richiede parsing EML per identificazione corretta
                return "varie", 0.5, "PEC busta - richiede parsing EML allegato", None, None

        # Caso speciale: SNALS centrale
        if sender_type == "SNALS_CENTRALE":
            sottocategoria, proposta_info = self.extract_subcategory("comunicazione_snals_centrale", mittente, oggetto, corpo)
            return "comunicazione_snals_centrale", 0.95, "Mittente info@snals.it", sottocategoria, proposta_info

        # Combine text for analysis
        full_text = f"{oggetto} {corpo}"

        # Detect signals
        signals = self.detect_convocazione_signals(full_text)

        # Check se è "invito sottoscrizione contratto" → NON è convocazione
        if signals['has_contract_keyword'] and not (signals['has_date'] and signals['has_time']):
            # È un invito a firmare/sottoscrivere contratto senza data/ora riunione
            categoria_base = "comunicazione"
            confidence = 0.90
            motivazione = "Invito sottoscrizione/firma contratto (non convocazione riunione)"

        # Check se è "trasmissione documenti" (corpo breve tipo "Si invia in allegato...")
        # Queste NON sono convocazioni anche se l'oggetto contiene "Invito" o "Contrattazione"
        elif self._is_trasmissione_documenti(corpo_lower):
            categoria_base = "comunicazione"
            confidence = 0.90
            motivazione = "Trasmissione documenti (non convocazione)"

        # Decision tree per convocazione con keywords FORTI
        elif signals['has_convocazione_strong']:
            if signals['has_date'] and signals['has_time']:
                categoria_base = "convocazione"
                confidence = 0.95
                motivazione = "Keyword convocazione FORTE + data + ora"
            elif signals['has_date'] or signals['has_time']:
                categoria_base = "convocazione"
                confidence = 0.90
                motivazione = "Keyword convocazione FORTE + data o ora"
            else:
                categoria_base = "convocazione_da_allegato"
                confidence = 0.85
                motivazione = "Keyword convocazione FORTE senza data/ora (probabile in allegato)"

        # Keywords DEBOLI richiedono data+ora per conferma
        elif signals['has_convocazione_weak']:
            if signals['has_date'] and signals['has_time']:
                categoria_base = "convocazione"
                confidence = 0.85
                motivazione = "Keyword convocazione debole + data + ora"
            else:
                # Keyword debole senza data/ora → probabilmente comunicazione
                categoria_base = "comunicazione"
                confidence = 0.75
                motivazione = "Keyword convocazione debole senza data/ora → comunicazione"

        else:
            # Non è convocazione
            # Check se è una revoca sindacale
            if self._is_revoca_sindacale(oggetto, corpo):
                return "revoca_sindacale", 0.95, "Revoca delega sindacale rilevata", None, None

            if signals['has_comunicazione_keyword']:
                categoria_base = "comunicazione"
                confidence = 0.90
                motivazione = "Keywords di comunicazione ufficiale"
            else:
                # Check se è spam
                if self._is_spam(mittente, oggetto, corpo):
                    return "spam", 0.95, "Pattern spam/pubblicità rilevato", None, None

                categoria_base = "comunicazione"
                confidence = 0.70
                motivazione = "Nessun segnale forte - default a comunicazione"

        # Map to final category based on sender type
        if categoria_base == "convocazione" or categoria_base == "convocazione_da_allegato":
            if sender_type == "USP_UST":
                final_category = "comunicazione_scuola"  # Le convocazioni vanno in comunicazione_scuola
                motivazione = f"{motivazione} | Mittente: USP/UST"
            elif sender_type == "SCUOLA":
                final_category = "comunicazione_scuola"
                motivazione = f"{motivazione} | Mittente: Scuola"
            else:
                final_category = "comunicazione_scuola"
                motivazione = f"{motivazione} | Tipo mittente: {sender_type}"

        elif categoria_base == "comunicazione":
            if sender_type == "USP_UST":
                final_category = "comunicazione_ust_usr"
                motivazione = f"{motivazione} | Mittente: USP/UST"
            elif sender_type == "SCUOLA":
                final_category = "comunicazione_scuola"
                motivazione = f"{motivazione} | Mittente: Scuola"
            else:
                # Mittente ALTRO (privato) - verifica se è una richiesta utente
                user_request = self._detect_user_request(mittente, oggetto, corpo)
                if user_request:
                    final_category = user_request['categoria']
                    confidence = user_request['confidence']
                    motivazione = user_request['motivazione']
                else:
                    final_category = "varie"
                    motivazione = f"{motivazione} | Tipo mittente: {sender_type}"

        else:
            # Non è convocazione né comunicazione - verifica richieste utente
            if sender_type == "ALTRO":
                user_request = self._detect_user_request(mittente, oggetto, corpo)
                if user_request:
                    final_category = user_request['categoria']
                    confidence = user_request['confidence']
                    motivazione = user_request['motivazione']
                else:
                    final_category = "varie"
                    motivazione = "Non classificabile con regole deterministiche"
                    confidence = 0.5
            else:
                final_category = "varie"
                motivazione = "Non classificabile con regole deterministiche"
                confidence = 0.5

        # Extract subcategory based on final category
        sottocategoria, proposta_info = self.extract_subcategory(final_category, mittente, oggetto, corpo)

        logger.info(f"Classificazione rule-based: {final_category} (conf: {confidence}) - {motivazione} | Sottocategoria: {sottocategoria}")
        return final_category, confidence, motivazione, sottocategoria, proposta_info

    def _is_read_receipt(self, oggetto: str, corpo: str) -> bool:
        """
        Rileva ricevute di lettura (Read Receipts)

        Indicatori:
        - Oggetto inizia con "Read:" o "Letta:" o "Reading:"
        - Corpo contiene "Il tuo messaggio" e "stato letto"
        - Microsoft Exchange Generator nel corpo
        - Corpo contiene "Your message" e "was read"

        Returns:
            True se è una ricevuta di lettura
        """
        oggetto_lower = oggetto.lower().strip()
        corpo_lower = corpo.lower() if corpo else ""

        # Check oggetto
        read_prefixes = ['read:', 'letta:', 'reading:', 'lettura:', 're: read:']
        has_read_prefix = any(oggetto_lower.startswith(prefix) for prefix in read_prefixes)

        # Check corpo per indicatori italiani
        has_italian_receipt = (
            'il tuo messaggio' in corpo_lower and
            'stato lett' in corpo_lower
        )

        # Check corpo per indicatori inglesi
        has_english_receipt = (
            'your message' in corpo_lower and
            'was read' in corpo_lower
        )

        # Microsoft Exchange generator
        has_exchange_generator = 'microsoft exchange server' in corpo_lower

        # Ritorna True se abbiamo forte evidenza di read receipt
        return has_read_prefix or has_italian_receipt or has_english_receipt or (
            has_exchange_generator and ('read' in oggetto_lower or 'lett' in oggetto_lower)
        )

    def _is_trasmissione_documenti(self, corpo_lower: str) -> bool:
        """
        Rileva email di semplice trasmissione documenti (non convocazioni).

        Queste email hanno corpo breve tipo:
        - "Si invia in allegato..."
        - "Si trasmette quanto in oggetto..."
        - "In allegato..."

        NON sono convocazioni anche se l'oggetto contiene "Invito" o "Contrattazione".

        Returns:
            True se è una trasmissione documenti
        """
        if not corpo_lower:
            return False

        # Rimuovi HTML tags per analisi
        import re
        corpo_pulito = re.sub(r'<[^>]+>', ' ', corpo_lower)
        corpo_pulito = re.sub(r'\s+', ' ', corpo_pulito).strip()

        # Pattern di trasmissione documenti
        trasmissione_patterns = [
            r'^si invia in allegato',
            r'^si trasmette',
            r'^in allegato',
            r'^si inviano',
            r'^si allega',
            r'si invia quanto in oggetto',
            r'si trasmette quanto in oggetto',
        ]

        for pattern in trasmissione_patterns:
            if re.search(pattern, corpo_pulito):
                # Verifica che il corpo sia breve (< 500 caratteri senza firma)
                # Le convocazioni vere hanno corpo più lungo con dettagli
                corpo_senza_firma = re.split(r'cordiali saluti|distinti saluti|nota di riservatezza', corpo_pulito)[0]
                if len(corpo_senza_firma) < 500:
                    return True

        return False

    def _is_spam(self, mittente: str, oggetto: str, corpo: str = "") -> bool:
        """Rileva pattern spam e pubblicità commerciale"""
        mittente_lower = mittente.lower()
        oggetto_lower = oggetto.lower()
        corpo_lower = corpo.lower() if corpo else ""

        # SOFT HYPHEN DETECTION - tecnica di evasione spam
        # I soft hyphen (U+00AD) vengono usati per spezzare le parole e evadere i filtri
        soft_hyphen = '\u00ad'
        if soft_hyphen in oggetto or soft_hyphen in mittente:
            logger.info(f"🚫 Spam rilevato - soft hyphen (tecnica evasione) in oggetto/mittente")
            return True

        # PHISHING: display name vs email domain mismatch
        # Es: "Aruba-spa" <fake@otherdomain.com>
        phishing_names = ['aruba', 'amazon', 'paypal', 'poste', 'intesa', 'unicredit',
                         'microsoft', 'apple', 'google', 'netflix', 'dhl', 'ups', 'brt',
                         'register', 'godaddy', 'ovh', 'ionos', 'hostinger']
        for name in phishing_names:
            if name in mittente_lower:
                # Verifica che il dominio email corrisponda
                email_match = re.search(r'<([^>]+)>', mittente)
                if email_match:
                    email_domain = email_match.group(1).split('@')[-1].lower()
                    if name not in email_domain:
                        logger.info(f"🚫 Phishing rilevato - display name '{name}' ma dominio '{email_domain}'")
                        return True

        # Domini e pattern marketing/pubblicità
        spam_domains = [
            'finsubitoonline.net',
            'marketing.com',
            'promo.',
            'offerte.',
            'prestiti.',
            'pubblicit',  # europubblicita, etc
            'mailchimp',
            'list-manage.com',
            '@musvc.com',  # marketing service
            'newsletter',
            'info.web@',
            'noreply@',
            'no-reply@',
            'marketing@',
            'promo@',
            'infomailing@',  # infomailing@blumatica.it, etc
            'mailing@',
            'newsletter@',
            'info@newsletter',
            'comunicazioni@',
            # Tech/web development spam
            'webtech',
            'affiwebtech',
            'techsolutions',
            'appdevelop',
            'softwaredev',
            'abordeaux',
            # Operatori telefonici - promo commerciali
            'clientibusiness.tim.it',
            'business.vodafone.it',
            'wind.it/promo',
            'fastweb.it/promo',
            # Enti formazione - marketing corsi
            'cfiscuola.it',
            'orizzontescuola.it/promo',
            'tecnicadellascuola.it/promo',
        ]

        for domain in spam_domains:
            if domain in mittente_lower:
                logger.info(f"🚫 Spam rilevato - dominio marketing: {domain} in {mittente}")
                return True

        # Pattern spam/pubblicità in oggetto
        spam_patterns = [
            r'💰', r'🚀', r'🎯', r'⚡', r'🔥', r'✨',  # Emoji promozionali
            r'€€€',
            r'!!!',
            r'\bOFFERTA\b',
            r'\bGRATIS\b',
            r'\bVINCI\b',
            r'\bSCONTO\b',
            r'\bPRESTITO\b',
            r'\bFINANZIAMENTO\b',
            r'#FINSUBITO',
            r'\bnuovi prodotti\b',
            r'\bcomunicazione aziendale\b',
            r'\bcampagna marketing\b',
            r'\bnuove collezioni\b',
            r'\bpromozione\b',
            r'\bofferta speciale\b',
            r'\blancio\b.*\bprodott',  # "lancio prodotti"
            r'\bcatalogo\b',
            r'\blistino prezzi\b',
            r'\bè il momento\b',
            r'\banticipa\b.*\btempo\b',
            r'\binnovare\b',
            r'\bnon perdere\b',
            r'\bultima chance\b',
            # Truffe rinnovo dominio/hosting
            r'\brinnov.*dominio\b',
            r'\bdominio.*scad\b',
            r'\bservizi.*dominio\b',
            r'\barea clienti\b',
            r'\bproseguimento.*servizio\b',
            # Promo operatori telefonici
            r'\d+\s*giga\b',  # "300 Giga", "100 giga"
            r'\b\d+\s*€/mese\b',  # "10 €/mese"
            r'\bper te\b.*\b€\b',  # "Per te ... €"
            r'\battiva\b.*\bofferta\b',
            # Tech spam / solicitation
            r'\bapp developer\b',
            r'\bweb developer\b',
            r'\bsoftware developer\b',
            r'\bhiring\b',
            r'\boutsourc',
            r'\.{3,}\?+',  # "....??" pattern
            r'\?{2,}',  # Multiple question marks
            # Oggetti vaghi/sospetti (tipici di spam SEO)
            r'^re:\s*yes',           # "Re: yes..?"
            r'^re:\s*hi\b',          # "Re: hi"
            r'^re:\s*hello\b',       # "Re: hello"
            r'^re:\s*\?\s*$',        # "Re: ?"
            r'^re:\s*\.\.\.',        # "Re: ..."
            r'^hi\s*$',              # Solo "hi"
            r'^hello\s*$',           # Solo "hello"
        ]

        for pattern in spam_patterns:
            if re.search(pattern, oggetto_lower, re.IGNORECASE):
                logger.info(f"🚫 Spam rilevato - pattern oggetto: {pattern}")
                return True

        # Pattern nel corpo (solo se corpo fornito)
        if corpo_lower:
            corpo_spam_patterns = [
                r'mailchi\.mp/',
                r'list-manage\.com',
                r'unsubscribe',
                r'disiscriv',
                r'visualizza.*nel browser',
                r'view.*in.*browser',
                r'ricevi questa comunicazione',
                r'ti sei registrato',
                r'hai partecipato.*evento',
                r'newsletter',
                r'se non vuoi ricevere',
                r'clicca qui per cancellarti',
                r'ingresso gratuito',
                r'consulta il programma',
                r'iscriviti.*evento',
                # SEO/Marketing spam
                r'online presence',
                r'google ranking',
                r'seo\s*(service|optimization|specialist)',
                r'website traffic',
                r'search engine',
                r'price list',
                r'send you.*details',
                r'interested\?',
                r'may i send',
                r'could i email',
                r'boost your',
                r'increase your.*traffic',
                r'digital marketing',
                r'lead generation',
                r'backlink',
                r'domain authority',
            ]

            for pattern in corpo_spam_patterns:
                if re.search(pattern, corpo_lower, re.IGNORECASE):
                    logger.info(f"🚫 Spam rilevato - pattern corpo: {pattern}")
                    return True

        return False

    def _is_revoca_sindacale(self, oggetto: str, corpo: str = "") -> bool:
        """Rileva revoche deleghe sindacali"""
        oggetto_lower = oggetto.lower()
        corpo_lower = corpo.lower() if corpo else ""
        full_text = f"{oggetto_lower} {corpo_lower}"

        # Pattern per revoche
        revoca_patterns = [
            r'\brevoca\b.*\b(sindacal|delega|snals|trattenut)',
            r'\brevoca\b.*\b(iscrizione|adesione)\b',
            r'\b(delega|trattenut).*\brevoca\b',
            r'\bmodello\s+revoca\b',
            r'\brevoca\s+delega\b',
            r'\bdisdetta\b.*\b(sindacal|iscrizione)\b',
            r'\brecesso\b.*\b(sindacal|iscrizione)\b',
            r'\brinuncia\b.*\b(iscrizione|delega)\b',
        ]

        for pattern in revoca_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                logger.info(f"📋 Revoca sindacale rilevata - pattern: {pattern}")
                return True

        return False

    def _detect_user_request(self, mittente: str, oggetto: str, corpo: str = "") -> Optional[Dict]:
        """
        Rileva richieste da utenti privati (info_generiche, richiesta_tesseramento, richiesta_appuntamento).

        Args:
            mittente: Email del mittente
            oggetto: Oggetto email
            corpo: Corpo email

        Returns:
            Dict con categoria, confidence, motivazione se rilevato, None altrimenti
        """
        oggetto_lower = oggetto.lower() if oggetto else ""
        corpo_lower = corpo.lower() if corpo else ""
        full_text = f"{oggetto_lower} {corpo_lower}"

        # ============================================================
        # PRIORITÀ 1: Richiesta tesseramento
        # ============================================================
        tesseramento_patterns = [
            r'\b(iscri[vz]ermi|iscrizione|tesserament|tesserar|aderire|adesione)\b.*\b(sindaca|snals)\b',
            r'\b(sindaca|snals)\b.*\b(iscri[vz]ermi|iscrizione|tesserament|tesserar)\b',
            r'\bmodulo\s+(di\s+)?iscrizione\b',
            r'\bquota\s+sindacale\b',
            r'\bdiventare\s+(iscritto|socio|tesserato)\b',
            r'\b(vorrei|desidero|voglio)\s+(iscrivermi|tesserarmi|aderire)\b',
            r'\bcome\s+(ci\s+)?si\s+iscrive\b',
            r'\bcome\s+(fare|posso)\s+per\s+iscrivermi\b',
        ]

        for pattern in tesseramento_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                logger.info(f"📝 Richiesta tesseramento rilevata - pattern: {pattern}")
                return {
                    'categoria': 'richiesta_tesseramento',
                    'confidence': 0.90,
                    'motivazione': 'Richiesta iscrizione/tesseramento al sindacato'
                }

        # ============================================================
        # PRIORITÀ 2: Richiesta appuntamento
        # ============================================================
        appuntamento_patterns = [
            r'\b(appuntament|incontro|riceviment)\b',
            r'\b(venire|passare|recarmi)\s+(in\s+)?sede\b',
            r'\b(fissare|prendere|prenotare)\s+(un\s+)?(appuntament|incontro)\b',
            r'\bdisponibilit[àa]\s+(per\s+)?(un\s+)?(incontro|appuntament|colloquio)\b',
            r'\b(quando|orario|giorni)\s+(posso|potrei|è possibile)\s+(venire|passare)\b',
            r'\b(vorrei|desidero)\s+(parlare|incontrar|un\s+colloquio)\b',
            r'\borari[oi]\s+(di\s+)?ricevimento\b',
            r'\bquando\s+(siete|sei|è)\s+disponibil[ei]\b',
        ]

        for pattern in appuntamento_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                logger.info(f"📅 Richiesta appuntamento rilevata - pattern: {pattern}")
                return {
                    'categoria': 'richiesta_appuntamento',
                    'confidence': 0.88,
                    'motivazione': 'Richiesta appuntamento/incontro in sede'
                }

        # ============================================================
        # PRIORITÀ 3: Richiesta informazioni generiche
        # ============================================================
        info_patterns = [
            # Pattern diretti di richiesta informazioni
            r'\b(informazion[ei]|chiariment[oi]|delucidazion[ei])\b',
            r'\b(vorrei|desidero|avrei\s+bisogno)\s+(sapere|chiedere|informazion)\b',
            r'\b(potete|potreste|puoi|può)\s+(darmi|fornirmi|indicarmi)\b',
            r'\b(chiedo|richiedo|domando)\b.*\b(informazion|chiariment)\b',
            r'\bho\s+(una|delle)\s+(domand[ae]|richiest[ae])\b',
            r'\b(come|cosa)\s+(funziona|devo\s+fare|bisogna\s+fare)\b',

            # Argomenti tipici di richieste info
            r'\b(graduatori[ae]|punteggi[oi]|supplenz[ae])\b',
            r'\b(permess[oi]|aspettativ[ae]|congedo|ferie)\b',
            r'\b(contratt[oi]|stipendi[oi]|retribuzion[ei])\b',
            r'\b(trasferiment[oi]|mobilit[àa]|assegnazion[ei])\b',
            r'\b(pensione|tfr|buonuscita|liquidazione)\b',
            r'\b(diritti|doveri|normativ[ae])\b',
            r'\b(incaric[oi]|nomina|ruolo)\b',
            r'\b(maternit[àa]|paternit[àa]|104|handicap)\b',
            r'\b(ricostruzione\s+carriera|riconoscimento\s+servizio)\b',
            r'\b(scatti|anzianit[àa]|progressione)\b',
        ]

        for pattern in info_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                logger.info(f"ℹ️ Richiesta informazioni rilevata - pattern: {pattern}")
                return {
                    'categoria': 'info_generiche',
                    'confidence': 0.85,
                    'motivazione': 'Richiesta informazioni da utente privato'
                }

        # ============================================================
        # FALLBACK: Verifica se mittente è da dominio personale
        # e l'email sembra una richiesta (anche senza pattern specifico)
        # ============================================================
        personal_domains = ['gmail.com', 'libero.it', 'yahoo.', 'hotmail.', 'outlook.',
                          'live.', 'icloud.', 'tiscali.it', 'virgilio.it', 'alice.it',
                          'fastwebnet.it', 'tin.it', 'email.it', 'pec.it']

        mittente_lower = mittente.lower() if mittente else ""
        is_personal = any(domain in mittente_lower for domain in personal_domains)

        if is_personal:
            # Se è un'email personale con tono interrogativo, probabilmente è info_generiche
            question_indicators = [
                r'\?',  # Punto interrogativo
                r'\b(come|cosa|quando|dove|perch[eé]|quale|chi|quanto)\b',
                r'\b(potete|potreste|è possibile|si pu[oò])\b',
                r'\b(vorrei|desidero|avrei bisogno|mi serve)\b',
                r'\b(aiut|assist|support)\b',
            ]

            question_count = sum(1 for p in question_indicators if re.search(p, full_text, re.IGNORECASE))

            if question_count >= 2:
                logger.info(f"ℹ️ Email personale con tono interrogativo ({question_count} indicatori) → info_generiche")
                return {
                    'categoria': 'info_generiche',
                    'confidence': 0.75,
                    'motivazione': 'Email da dominio personale con tono interrogativo'
                }

        return None

    def _is_bounce_email(self, mittente: str, oggetto: str, corpo: str = "") -> bool:
        """
        Rileva email bounce/errore consegna (Undelivered Mail, Mail Delivery System, etc.)
        Queste email devono essere categorizzate come 'varie' e non come info_generiche.
        """
        mittente_lower = mittente.lower() if mittente else ""
        oggetto_lower = oggetto.lower() if oggetto else ""
        corpo_lower = corpo.lower() if corpo else ""

        # Pattern mittente bounce
        bounce_senders = [
            'mailer-daemon',
            'mail delivery',
            'postmaster',
            'mail-daemon',
            'daemon@',
            'noreply@',
            'no-reply@',
            'bounce@',
            'returned_mail',
            'mail delivery system',
            'mail delivery subsystem',
        ]

        for sender in bounce_senders:
            if sender in mittente_lower:
                logger.info(f"📧 Email bounce rilevata - mittente: {sender}")
                return True

        # Pattern oggetto bounce
        bounce_subject_patterns = [
            r'undelivered mail',
            r'mail delivery failed',
            r'delivery status notification',
            r'failure notice',
            r'returned mail',
            r'undeliverable',
            r'delivery failure',
            r'mail delivery system',
            r'non.*deliver',
            r'could not be delivered',
            r'impossibile recapitare',
            r'consegna non riuscita',
            r'mancato recapito',
            r'errore.*consegna',
            r'messaggio non.*consegnato',
        ]

        for pattern in bounce_subject_patterns:
            if re.search(pattern, oggetto_lower, re.IGNORECASE):
                logger.info(f"📧 Email bounce rilevata - oggetto: {pattern}")
                return True

        # Pattern corpo bounce (se oggetto e mittente non sono chiari)
        if corpo_lower:
            bounce_body_patterns = [
                r'message could not be delivered',
                r'delivery to the following recipient failed',
                r'the email account.*does not exist',
                r'address rejected',
                r'user unknown',
                r'mailbox not found',
                r'recipient rejected',
                r'remote server returned',
                r'550.*user.*unknown',
                r'550.*mailbox.*unavailable',
                r'554.*delivery error',
            ]

            for pattern in bounce_body_patterns:
                if re.search(pattern, corpo_lower, re.IGNORECASE):
                    logger.info(f"📧 Email bounce rilevata - corpo: {pattern}")
                    return True

        return False
