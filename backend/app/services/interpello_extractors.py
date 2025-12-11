"""
Strategie di estrazione per interpelli scolastici.
Supporta multiple strategie: OpenAI API, Ollama (local LLM), Regex-based.
"""

import re
import os
import json
import logging
from typing import Dict, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class InterpelloExtractor(ABC):
    """Classe base astratta per estrattori di interpelli."""

    @abstractmethod
    def extract(self, testo: str) -> Optional[Dict[str, Any]]:
        """
        Estrae dati strutturati dal testo dell'interpello.

        Args:
            testo: Testo completo dell'interpello (corpo + allegati)

        Returns:
            Dict con i dati estratti, o None se fallisce
        """
        pass


class RegexExtractor(InterpelloExtractor):
    """Estrazione basata su pattern regex - veloce, affidabile per dati strutturati."""

    # Mappatura codici provincia -> nome provincia
    PROVINCE_CODE_MAP = {
        'AG': 'Agrigento', 'AL': 'Alessandria', 'AN': 'Ancona', 'AO': 'Aosta',
        'AP': 'Ascoli Piceno', 'AQ': "L'Aquila", 'AR': 'Arezzo', 'AT': 'Asti',
        'AV': 'Avellino', 'BA': 'Bari', 'BG': 'Bergamo', 'BI': 'Biella',
        'BL': 'Belluno', 'BN': 'Benevento', 'BO': 'Bologna', 'BR': 'Brindisi',
        'BS': 'Brescia', 'BT': 'Barletta-Andria-Trani', 'BZ': 'Bolzano', 'CA': 'Cagliari',
        'CB': 'Campobasso', 'CE': 'Caserta', 'CH': 'Chieti', 'CL': 'Caltanissetta',
        'CN': 'Cuneo', 'CO': 'Como', 'CR': 'Cremona', 'CS': 'Cosenza',
        'CT': 'Catania', 'CZ': 'Catanzaro', 'EN': 'Enna', 'FC': 'Forlì-Cesena',
        'FE': 'Ferrara', 'FG': 'Foggia', 'FI': 'Firenze', 'FM': 'Fermo',
        'FR': 'Frosinone', 'GE': 'Genova', 'GO': 'Gorizia', 'GR': 'Grosseto',
        'IM': 'Imperia', 'IS': 'Isernia', 'KR': 'Crotone', 'LC': 'Lecco',
        'LE': 'Lecce', 'LI': 'Livorno', 'LO': 'Lodi', 'LT': 'Latina',
        'LU': 'Lucca', 'MB': 'Monza e Brianza', 'MC': 'Macerata', 'ME': 'Messina',
        'MI': 'Milano', 'MN': 'Mantova', 'MO': 'Modena', 'MS': 'Massa-Carrara',
        'MT': 'Matera', 'NA': 'Napoli', 'NO': 'Novara', 'NU': 'Nuoro',
        'OR': 'Oristano', 'PA': 'Palermo', 'PC': 'Piacenza', 'PD': 'Padova',
        'PE': 'Pescara', 'PG': 'Perugia', 'PI': 'Pisa', 'PN': 'Pordenone',
        'PO': 'Prato', 'PR': 'Parma', 'PT': 'Pistoia', 'PU': 'Pesaro e Urbino',
        'PV': 'Pavia', 'PZ': 'Potenza', 'RA': 'Ravenna', 'RC': 'Reggio Calabria',
        'RE': 'Reggio Emilia', 'RG': 'Ragusa', 'RI': 'Rieti', 'RM': 'Roma',
        'RN': 'Rimini', 'RO': 'Rovigo', 'SA': 'Salerno', 'SI': 'Siena',
        'SO': 'Sondrio', 'SP': 'La Spezia', 'SR': 'Siracusa', 'SS': 'Sassari',
        'SU': 'Sud Sardegna', 'SV': 'Savona', 'TA': 'Taranto', 'TE': 'Teramo',
        'TN': 'Trento', 'TO': 'Torino', 'TP': 'Trapani', 'TR': 'Terni',
        'TS': 'Trieste', 'TV': 'Treviso', 'UD': 'Udine', 'VA': 'Varese',
        'VB': 'Verbano-Cusio-Ossola', 'VC': 'Vercelli', 'VE': 'Venezia', 'VI': 'Vicenza',
        'VR': 'Verona', 'VT': 'Viterbo', 'VV': 'Vibo Valentia'
    }

    # Pattern per classe di concorso
    # Le classi valide iniziano con: A, B, C, AA, AB, AC, AD, AN, BB, BC, BD, BI, CS, etc.
    # Escludiamo articoli italiani (il, lo, la, le, un, una, del, per, di, da, su, in, al)
    # e altre parole comuni che matchano il pattern
    CLASSE_PATTERN = re.compile(
        r'(?:classe\s+(?:di\s+)?concorso\s+)?(?<!ALLEGATO\s)(?<!ALLEGATI\s)(?<!AVVISO\s)(?<!N\.\s)(?<!N°\s)\b(A[A-Z]?|B[A-Z]?|C[A-Z]?|D[A-Z]?|E[A-Z]?)[- ]?(\d{2,3})\b',
        re.IGNORECASE
    )

    # Pattern per codice scuola in email inoltrate
    # Supporta: RNTF010004, fiic82700r (minuscolo), con/senza trattino dopo
    # Formato: 2 lettere provincia + 2 lettere tipo + 5-6 cifre + opzionale lettera controllo
    SCHOOL_CODE_PATTERN = re.compile(
        r'(?:Da:|From:)\s*([A-Za-z]{2}[A-Za-z]{2}\d{5}[A-Za-z0-9]?)\s*[-\s]+([^<\n]+?)(?:\s*<|$)',
        re.MULTILINE | re.IGNORECASE
    )

    # Pattern per data scadenza
    DATA_SCADENZA_PATTERN = re.compile(
        r'(?:scadenza|entro|entro il)[^\d]*?(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})',
        re.IGNORECASE
    )

    # Pattern per ore settimanali - cerca sia "ore 17" che "17 ore" che "da 17 ore"
    # NOTA: Il numero deve essere ragionevole (1-40 ore)
    ORE_PATTERN_BEFORE = re.compile(
        r'(?:ore|h\.?)\s*(\d{1,2})(?:/\d{1,2})?\s*(?:settimanali?)?',
        re.IGNORECASE
    )
    ORE_PATTERN_AFTER = re.compile(
        r'(?:da\s+)?(\d{1,2})\s*(?:ore|h\.?)(?:\s*settimanali?)?',
        re.IGNORECASE
    )

    # Pattern per numero posti
    POSTI_PATTERN = re.compile(
        r'(?:n\.|numero|nr\.?)\s*(\d+)\s*posti?',
        re.IGNORECASE
    )

    # Pattern per provincia (fallback se non trovato da codice scuola)
    PROVINCIA_PATTERN = re.compile(
        r'(?:provincia|prov\.)\s*(?:di\s+)?([A-Z][a-z]+)',
        re.IGNORECASE
    )

    # Pattern per date contratto
    DATA_INIZIO_PATTERN = re.compile(
        r'(?:inizio|dal|a decorrere dal)[^\d]*?(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})',
        re.IGNORECASE
    )

    DATA_FINE_PATTERN = re.compile(
        r'(?:fino al|termine|al|fino a)[^\d]*?(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})',
        re.IGNORECASE
    )

    # Pattern per email di contatto
    EMAIL_CONTATTO_PATTERN = re.compile(
        r'(?:inviare|candidatura|domanda|istanza|manifestazione|interesse)[^@\n]*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        re.IGNORECASE
    )

    # Pattern per telefono di contatto - più preciso, max 15 cifre consecutive
    TELEFONO_PATTERN = re.compile(
        r'(?:telefono|tel\.?|cell\.?)[:\s]*(\+?[0-9]{2,4}[\s\-./]?[0-9]{3,4}[\s\-./]?[0-9]{3,7})',
        re.IGNORECASE
    )

    # Pattern per referente di contatto
    REFERENTE_PATTERN = re.compile(
        r'(?:referente|contattare|rivolgersi)[:\s]+(?:sig\.?|dott\.?|prof\.?)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        re.IGNORECASE
    )

    # Pattern per città - cerca "(XX)" dove XX è codice provincia, estrai città precedente
    CITTA_PATTERN = re.compile(
        r'([A-Z][a-zàèéìòù]+(?:\s+[A-Z][a-zàèéìòù]+)*)\s*\(([A-Z]{2})\)',
        re.UNICODE
    )

    # Pattern per istituto - cerca nomi scuola comuni
    ISTITUTO_PATTERNS = [
        # Pattern specifici per tipo scuola
        re.compile(r'((?:Istituto\s+)?(?:Comprensivo|Tecnico|Professionale|Superiore)\s+(?:Statale\s+)?["\']?[A-Z][^"\'\n,]{3,50}["\']?)', re.IGNORECASE),
        re.compile(r'(I\.?[ITC]\.?[AS]?\.?\s+["\']?[A-Z][^"\'\n,]{3,40}["\']?)', re.IGNORECASE),  # IIS, ITC, ITAS
        re.compile(r'(Liceo\s+(?:Scientifico|Classico|Artistico|Linguistico|Musicale)?\s*["\']?[A-Z][^"\'\n,]{3,40}["\']?)', re.IGNORECASE),
        re.compile(r'(I\.?P\.?S\.?[IAC]\.?[AR]?\.?\s+["\']?[A-Z][^"\'\n,]{3,40}["\']?)', re.IGNORECASE),  # IPSIA, IPSIAR
        re.compile(r'(Scuola\s+(?:Secondaria|Primaria|Media)\s+["\']?[A-Z][^"\'\n,]{3,40}["\']?)', re.IGNORECASE),
    ]

    # Pattern per indirizzo - escludi "corso" se seguito da codice classe (A044, etc)
    INDIRIZZO_PATTERN = re.compile(
        r'((?:Via|Viale|Piazza|Largo|Vicolo|Contrada|Loc\.?|Località)\s+[A-Z][^,\n]{5,60})',
        re.IGNORECASE
    )
    # Pattern separato per "Corso" per evitare "classe di concorso"
    INDIRIZZO_CORSO_PATTERN = re.compile(
        r'(Corso\s+(?!di\s+concorso|A[A-Z]?\d|B[A-Z]?\d)[A-Z][^,\n]{5,60})',
        re.IGNORECASE
    )

    # Pattern per CAP + Città
    CAP_CITTA_PATTERN = re.compile(
        r'(\d{5})\s+([A-Z][a-zàèéìòù]+(?:\s+[A-Z][a-zàèéìòù]+)?)\s*(?:\(([A-Z]{2})\))?',
        re.UNICODE
    )

    def _get_context(self, testo: str, match, chars_before: int = 50, chars_after: int = 50) -> str:
        """Estrae il contesto intorno a un match per validazione."""
        start = max(0, match.start() - chars_before)
        end = min(len(testo), match.end() + chars_after)
        return testo[start:end]

    def extract(self, testo: str) -> Optional[Dict[str, Any]]:
        """Estrae dati usando pattern regex."""
        try:
            dati = {}

            # Estrai classe di concorso (PRIORITÀ MASSIMA)
            classe_match = self.CLASSE_PATTERN.search(testo)
            if classe_match:
                # Normalizza: rimuovi spazi/trattini
                lettere = classe_match.group(1).upper()
                numeri = classe_match.group(2)
                dati['classe_concorso'] = f"{lettere}{numeri}"
                logger.info(f"✅ Regex trovato classe_concorso: {dati['classe_concorso']}")

            # Estrai ore settimanali - prova AFTER prima (più specifico: "da 17 ore")
            # poi BEFORE come fallback, ma escludi orari (es: ore 12:30)
            ore_match = None
            ore_value = None

            # 1. Prova pattern AFTER (es: "da 17 ore", "17 ore", "17h")
            for match in self.ORE_PATTERN_AFTER.finditer(testo):
                ore_candidate = int(match.group(1))
                # Verifica che non sia seguito da ":" (orario tipo 12:30)
                match_end = match.end()
                if match_end < len(testo) and testo[match_end:match_end+1] == ':':
                    continue  # Skip, è un orario
                if 1 <= ore_candidate <= 40:
                    ore_value = ore_candidate
                    ore_match = match
                    break

            # 2. Se non trovato, prova BEFORE ma escludi orari
            if not ore_value:
                for match in self.ORE_PATTERN_BEFORE.finditer(testo):
                    ore_candidate = int(match.group(1))
                    # Verifica che non sia "ore HH:MM" (orario)
                    context = testo[match.start():min(len(testo), match.end()+3)]
                    if re.search(r':\d{2}', context):
                        continue  # Skip, è un orario
                    if 1 <= ore_candidate <= 40:
                        ore_value = ore_candidate
                        ore_match = match
                        break

            if ore_value:
                dati['ore_settimanali'] = ore_value
                logger.info(f"✅ Regex trovato ore_settimanali: {dati['ore_settimanali']}")

            # Estrai numero posti
            posti_match = self.POSTI_PATTERN.search(testo)
            if posti_match:
                dati['numero_posti'] = int(posti_match.group(1))
                logger.info(f"✅ Regex trovato numero_posti: {dati['numero_posti']}")

            # Estrai provincia e istituto da codice scuola (PRIORITÀ 1 - più affidabile per email inoltrate)
            # IMPORTANTE: cerca TUTTI i match e prendi l'ULTIMO (scuola origine, non USP che inoltra)
            school_matches = list(self.SCHOOL_CODE_PATTERN.finditer(testo))

            # Se non trovato con pattern standard, prova pattern alternativo per email scuola
            if not school_matches:
                # Pattern alternativo: cerca email scuola nel testo (es: psri02000b@istruzione.it)
                alt_pattern = re.compile(
                    r'([A-Za-z]{4}\d{5}[A-Za-z0-9]?)@(?:pec\.)?istruzione\.it',
                    re.IGNORECASE
                )
                alt_matches = list(alt_pattern.finditer(testo))
                if alt_matches:
                    # Prendi l'ultimo codice trovato (più probabile essere la scuola origine)
                    school_code = alt_matches[-1].group(1).upper()
                    province_code = school_code[:2].upper()
                    if province_code in self.PROVINCE_CODE_MAP:
                        dati['provincia'] = self.PROVINCE_CODE_MAP[province_code]
                        logger.info(f"✅ Regex trovato provincia da email scuola {school_code}: {dati['provincia']}")

            if school_matches:
                # Prendi l'ULTIMO match (scuola origine nelle email inoltrate multiple volte)
                school_match = school_matches[-1]
                school_code = school_match.group(1).upper()  # es: RNTF010004
                school_name = school_match.group(2).strip()  # es: LEONARDO DA VINCI DISTRETTO 046

                # Estrai codice provincia (primi 2 caratteri)
                province_code = school_code[:2].upper()
                if province_code in self.PROVINCE_CODE_MAP:
                    dati['provincia'] = self.PROVINCE_CODE_MAP[province_code]
                    logger.info(f"✅ Regex trovato provincia da codice scuola {school_code}: {dati['provincia']}")

                # Salva nome istituto (pulito da "DISTRETTO XXX" etc)
                school_name_clean = re.sub(r'\s+DISTRETTO\s+\d+', '', school_name, flags=re.IGNORECASE).strip()
                dati['istituto'] = school_name_clean
                logger.info(f"✅ Regex trovato istituto da codice scuola: {dati['istituto']}")

            # Se non trovato da codice scuola, prova pattern generico provincia (FALLBACK)
            if 'provincia' not in dati:
                provincia_match = self.PROVINCIA_PATTERN.search(testo)
                if provincia_match:
                    dati['provincia'] = provincia_match.group(1).title()
                    logger.info(f"✅ Regex trovato provincia (fallback generico): {dati['provincia']}")

            # Estrai data scadenza
            scadenza_match = self.DATA_SCADENZA_PATTERN.search(testo)
            if scadenza_match:
                giorno, mese, anno = scadenza_match.groups()
                if len(anno) == 2:
                    anno = f"20{anno}"
                try:
                    data_scadenza = datetime(int(anno), int(mese), int(giorno))
                    dati['data_scadenza'] = data_scadenza.isoformat()
                    logger.info(f"✅ Regex trovato data_scadenza: {dati['data_scadenza']}")
                except ValueError:
                    pass

            # Estrai data inizio servizio
            inizio_match = self.DATA_INIZIO_PATTERN.search(testo)
            if inizio_match:
                giorno, mese, anno = inizio_match.groups()
                if len(anno) == 2:
                    anno = f"20{anno}"
                try:
                    data_inizio = datetime(int(anno), int(mese), int(giorno))
                    dati['data_inizio_servizio'] = data_inizio.date().isoformat()
                    logger.info(f"✅ Regex trovato data_inizio_servizio: {dati['data_inizio_servizio']}")
                except ValueError:
                    pass

            # Estrai data fine contratto
            fine_match = self.DATA_FINE_PATTERN.search(testo)
            if fine_match:
                giorno, mese, anno = fine_match.groups()
                if len(anno) == 2:
                    anno = f"20{anno}"
                try:
                    data_fine = datetime(int(anno), int(mese), int(giorno))
                    dati['data_fine_contratto'] = data_fine.date().isoformat()
                    logger.info(f"✅ Regex trovato data_fine_contratto: {dati['data_fine_contratto']}")
                except ValueError:
                    pass

            # Estrai email di contatto
            email_match = self.EMAIL_CONTATTO_PATTERN.search(testo)
            if email_match:
                dati['email_contatto'] = email_match.group(1).lower()
                logger.info(f"✅ Regex trovato email_contatto: {dati['email_contatto']}")

            # Estrai telefono di contatto
            telefono_match = self.TELEFONO_PATTERN.search(testo)
            if telefono_match:
                # Pulisci numero: rimuovi spazi e trattini extra
                telefono = re.sub(r'[\s\-./]+', '', telefono_match.group(1))
                # Se troppo lungo, prendi solo primi 15 caratteri
                if len(telefono) > 15:
                    telefono = telefono[:15]
                dati['telefono_contatto'] = telefono
                logger.info(f"✅ Regex trovato telefono_contatto: {dati['telefono_contatto']}")

            # Estrai referente di contatto
            referente_match = self.REFERENTE_PATTERN.search(testo)
            if referente_match:
                dati['referente_contatto'] = referente_match.group(1).strip()
                logger.info(f"✅ Regex trovato referente_contatto: {dati['referente_contatto']}")

            # Estrai città da pattern "Città (XX)" dove XX è codice provincia
            if 'citta' not in dati:
                citta_matches = list(self.CITTA_PATTERN.finditer(testo))
                if citta_matches:
                    # Prendi l'ultimo match (più probabile essere la scuola, non USP)
                    for match in reversed(citta_matches):
                        citta_candidate = match.group(1).strip()
                        prov_code = match.group(2).upper()
                        # Valida che sia una provincia reale
                        if prov_code in self.PROVINCE_CODE_MAP:
                            # Evita falsi positivi (parole comuni che matchano)
                            if citta_candidate.lower() not in ['il', 'la', 'lo', 'le', 'un', 'una', 'del', 'della']:
                                dati['citta'] = citta_candidate.title()
                                # Se non abbiamo ancora la provincia, la otteniamo da qui
                                if 'provincia' not in dati:
                                    dati['provincia'] = self.PROVINCE_CODE_MAP[prov_code]
                                context = self._get_context(testo, match)
                                dati['_context_citta'] = context
                                logger.info(f"✅ Regex trovato città: {dati['citta']} ({prov_code})")
                                break

            # Estrai città da CAP + Città pattern (es: "74023 Grottaglie")
            if 'citta' not in dati:
                cap_match = self.CAP_CITTA_PATTERN.search(testo)
                if cap_match:
                    cap = cap_match.group(1)
                    citta = cap_match.group(2).strip()
                    prov_code = cap_match.group(3) if cap_match.group(3) else None
                    if citta and len(citta) > 2:
                        dati['citta'] = citta.title()
                        dati['cap'] = cap
                        if prov_code and prov_code in self.PROVINCE_CODE_MAP and 'provincia' not in dati:
                            dati['provincia'] = self.PROVINCE_CODE_MAP[prov_code]
                        logger.info(f"✅ Regex trovato città da CAP: {dati['citta']}")

            # Estrai istituto da pattern nel testo (se non già trovato da header)
            if 'istituto' not in dati:
                for pattern in self.ISTITUTO_PATTERNS:
                    match = pattern.search(testo)
                    if match:
                        istituto = match.group(1).strip()
                        # Pulisci caratteri extra
                        istituto = re.sub(r'["\']', '', istituto)
                        istituto = re.sub(r'\s+', ' ', istituto)
                        # Evita match troppo corti o troppo lunghi
                        if 10 < len(istituto) < 80:
                            dati['istituto'] = istituto
                            context = self._get_context(testo, match)
                            dati['_context_istituto'] = context
                            logger.info(f"✅ Regex trovato istituto: {dati['istituto']}")
                            break

            # Estrai indirizzo
            if 'indirizzo' not in dati:
                indirizzo_match = self.INDIRIZZO_PATTERN.search(testo)
                if indirizzo_match:
                    indirizzo = indirizzo_match.group(1).strip()
                    # Pulisci e normalizza
                    indirizzo = re.sub(r'\s+', ' ', indirizzo)
                    if len(indirizzo) > 10:
                        dati['indirizzo'] = indirizzo
                        context = self._get_context(testo, indirizzo_match)
                        dati['_context_indirizzo'] = context
                        logger.info(f"✅ Regex trovato indirizzo: {dati['indirizzo']}")

            # Ritorna dati solo se abbiamo almeno la classe di concorso
            if 'classe_concorso' in dati:
                logger.info(f"✅ Regex extraction completata: {len(dati)} campi estratti")
                return dati
            else:
                logger.warning("⚠️ Regex: classe_concorso non trovata")
                return None

        except Exception as e:
            logger.error(f"❌ Errore Regex extraction: {e}")
            return None


class OpenAIExtractor(InterpelloExtractor):
    """Estrazione usando OpenAI API (GPT-4, GPT-3.5, etc.)."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.client = None

        if not api_key:
            raise ValueError("OpenAI API key is required")

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            logger.info(f"✅ OpenAI client inizializzato con modello {model}")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    EXTRACTION_PROMPT = """Estrai informazioni strutturate da questo interpello scolastico.

ATTENZIONE AL CONTESTO SEMANTICO:
- Gli interpelli sono spesso INOLTRATI da USP/USR (Uffici Scolastici)
- La scuola ORIGINALE che pubblica l'interpello è nell'email più interna
- Cerca pattern "Da: [CODICE_SCUOLA]" per identificare la scuola origine
- IGNORA province/città degli USP/USR che inoltrano
- Valida provincia con indicatori: "(FI)" = Firenze, "(CA)" = Cagliari, "(RM)" = Roma
- Se trovi nome città (es: "Calenzano", "Muravera", "Rieti"), inferisci la provincia corretta
- Priorità: informazioni dalla scuola origine > informazioni USP inoltro

PRIORITÀ ASSOLUTA: trova la classe di concorso (es: A042, AB24, AC55, ADSS).

Cerca codici formato: A042, A-42, AB24, AC-55, ADSS
Normalizza rimuovendo spazi e trattini: "A-42" → "A042"

Estrai questi campi (solo se presenti e semanticamente corretti):
- classe_concorso: codice normalizzato (OBBLIGATORIO)
- numero_posti: numero intero
- ore_settimanali: numero intero
- data_scadenza: formato ISO "YYYY-MM-DDTHH:MM:SS"
- data_inizio_servizio: formato "YYYY-MM-DD"
- data_fine_contratto: formato "YYYY-MM-DD"
- provincia: nome provincia DELLA SCUOLA ORIGINE (es. "Firenze" non "Taranto" se USP Taranto inoltra)
- citta: nome città della scuola origine
- istituto: nome completo scuola origine
- indirizzo: indirizzo completo scuola origine
- tipo_contratto: es. "supplenza", "spezzone orario"
- email_contatto: email a cui inviare candidatura/domanda
- telefono_contatto: telefono per informazioni
- referente_contatto: nome del referente da contattare
- modalita_candidatura: descrizione testuale di come candidarsi

ESEMPIO CORRETTO:
Email: "Da: USP di Taranto" → "Da: fiic82700r Calenzano" → "Istituto... (FI)"
Estrazione corretta: {{"provincia": "Firenze", "citta": "Calenzano", "istituto": "Istituto..."}}
Estrazione ERRATA: {{"provincia": "Taranto"}}  ← SBAGLIATO! Taranto è solo l'USP che inoltra

Rispondi SOLO con JSON valido, esempio:
{{
  "classe_concorso": "A042",
  "ore_settimanali": 12,
  "provincia": "Rimini",
  "istituto": "LEONARDO DA VINCI"
}}

TESTO:
{testo}"""

    def extract(self, testo: str) -> Optional[Dict[str, Any]]:
        """Estrae dati usando OpenAI API."""
        try:
            prompt = self.EXTRACTION_PROMPT.format(testo=testo[:10000])

            logger.info(f"🤖 Chiamata OpenAI API ({self.model})...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Sei un assistente che estrae dati strutturati da documenti italiani."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            logger.debug(f"OpenAI response: {result_text}")

            dati = json.loads(result_text)

            if 'classe_concorso' in dati:
                logger.info(f"✅ OpenAI extraction completata: {len(dati)} campi estratti")
                return dati
            else:
                logger.warning("⚠️ OpenAI: classe_concorso non trovata nella risposta")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"❌ Errore parsing JSON da OpenAI: {e}")
            logger.error(f"Response text: {result_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"❌ Errore OpenAI API: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None


class OllamaExtractor(InterpelloExtractor):
    """Estrazione usando modelli locali Ollama (Llama, Gemma, etc.)."""

    def __init__(self, base_url: str, model: str, timeout: float = 300.0):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        logger.info(f"✅ Ollama extractor inizializzato: {model} @ {base_url}")

    EXTRACTION_PROMPT = """Estrai informazioni da questo interpello scolastico.

DOMANDA CHIAVE: In quale SCUOLA c'è il posto vacante?
- Cerca "Sede di servizio:" → quella è la scuola
- Cerca email tipo "xxxx12345@istruzione.it" → le prime 2 lettere = provincia (TA=Taranto, PS=Pesaro, FI=Firenze)
- IGNORA gli USP/USR che inoltrano (es: "USP di Taranto inoltra...")

ESEMPIO CRITICO:
Testo: "Da: USP Taranto ... Da: PSRI02000B G.BENELLI ... Sede: IPSIA Benelli Pesaro"
→ La scuola è a PESARO (codice PS), NON Taranto (che è solo l'USP che inoltra!)
→ provincia = "Pesaro-Urbino", istituto = "IPSIA G. BENELLI"

Campi da estrarre:
- classe_concorso: codice tipo A042, B017 (OBBLIGATORIO)
- ore_settimanali: numero
- provincia: provincia della SCUOLA (non dell'USP!)
- citta: città della scuola
- istituto: nome scuola
- data_scadenza: "YYYY-MM-DD"
- data_fine_contratto: "YYYY-MM-DD"

TESTO:
{testo}

Rispondi SOLO JSON: {{"classe_concorso": "...", "provincia": "...", ...}}"""

    def extract(self, testo: str) -> Optional[Dict[str, Any]]:
        """Estrae dati usando Ollama."""
        try:
            import httpx

            prompt = self.EXTRACTION_PROMPT.format(testo=testo[:10000])

            logger.info(f"🤖 Chiamata Ollama ({self.model})...")

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 500
                        }
                    }
                )
                response.raise_for_status()

            result = response.json()
            result_text = result.get('response', '')

            logger.debug(f"Ollama response: {result_text}")

            # Cerca JSON nella risposta
            json_match = re.search(r'\{[^}]+\}', result_text)
            if json_match:
                dati = json.loads(json_match.group(0))

                if 'classe_concorso' in dati:
                    logger.info(f"✅ Ollama extraction completata: {len(dati)} campi estratti")
                    return dati
                else:
                    logger.warning("⚠️ Ollama: classe_concorso non trovata")
                    return None
            else:
                logger.warning("⚠️ Ollama: nessun JSON trovato nella risposta")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"❌ Errore parsing JSON da Ollama: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Errore Ollama: {e}")
            return None


class HybridExtractor(InterpelloExtractor):
    """
    Estrazione ibrida: Regex + Validazione Ollama con contesto.

    Pipeline:
    1. Estrazione regex con cattura contesto (50 caratteri prima/dopo)
    2. Invio a Ollama per validazione con contesto
    3. Cross-validazione e calcolo confidence score
    4. Ritorno dati validati con score di affidabilità
    """

    VALIDATION_PROMPT = """Valida questi dati estratti da un interpello scolastico.

CONTESTO ORIGINALE per ogni campo:
{contexts}

DATI ESTRATTI DA REGEX:
{regex_data}

Per ogni campo estratto, analizza il contesto e rispondi:
1. Il valore estratto è corretto nel contesto?
2. Qual è la tua correzione se sbagliato?
3. Confidence (0.0-1.0)?

ATTENZIONE CRITICA per la PROVINCIA:
- La provincia deve essere quella della SCUOLA, NON dell'USP/USR che inoltra
- Se vedi "USP di Taranto" ma la scuola è "IPSIA Benelli di Pesaro", la provincia è Pesaro-Urbino
- Cerca codici scuola (es: PSRI02000B = Pesaro, TAIC8AA00E = Taranto)

Rispondi SOLO con JSON valido:
{{
  "validations": {{
    "classe_concorso": {{"correct": true/false, "corrected_value": "...", "confidence": 0.0-1.0}},
    "provincia": {{"correct": true/false, "corrected_value": "...", "confidence": 0.0-1.0}},
    ...
  }},
  "overall_confidence": 0.0-1.0
}}"""

    def __init__(self, ollama_base_url: str, ollama_model: str, timeout: float = 120.0):
        self.regex_extractor = RegexExtractor()
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.timeout = timeout
        logger.info(f"✅ HybridExtractor inizializzato: regex + {ollama_model}")

    def _extract_all_contexts(self, testo: str, regex_data: Dict) -> Dict[str, str]:
        """Estrae contesto per ogni campo trovato dal regex."""
        contexts = {}

        # Campi con contesto già salvato
        context_fields = ['_context_citta', '_context_istituto', '_context_indirizzo']
        for ctx_field in context_fields:
            if ctx_field in regex_data:
                field_name = ctx_field.replace('_context_', '')
                contexts[field_name] = regex_data[ctx_field]

        # Per altri campi, cerca il valore nel testo e ottieni contesto
        for field, value in regex_data.items():
            if field.startswith('_context_'):
                continue
            if field not in contexts and value:
                # Cerca il valore nel testo
                value_str = str(value)
                pos = testo.lower().find(value_str.lower())
                if pos >= 0:
                    start = max(0, pos - 80)
                    end = min(len(testo), pos + len(value_str) + 80)
                    contexts[field] = testo[start:end]

        return contexts

    def _validate_with_ollama(self, regex_data: Dict, contexts: Dict, full_text: str) -> Dict[str, Any]:
        """Invia a Ollama per validazione con contesto."""
        try:
            import httpx

            # Formatta contesti per il prompt
            contexts_str = "\n".join([
                f"- {field}: ...{ctx}..."
                for field, ctx in contexts.items()
            ])

            # Rimuovi campi _context_ dai dati regex
            clean_data = {k: v for k, v in regex_data.items() if not k.startswith('_context_')}

            prompt = self.VALIDATION_PROMPT.format(
                contexts=contexts_str,
                regex_data=json.dumps(clean_data, indent=2, ensure_ascii=False)
            )

            # Aggiungi anche un estratto del testo completo per riferimento
            prompt += f"\n\nTESTO COMPLETO (primi 3000 caratteri):\n{full_text[:3000]}"

            logger.info(f"🔍 Validazione Ollama in corso...")

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 800
                        }
                    }
                )
                response.raise_for_status()

            result = response.json()
            result_text = result.get('response', '')

            # Cerca JSON nella risposta
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                validation_result = json.loads(json_match.group(0))
                logger.info(f"✅ Validazione Ollama completata")
                return validation_result
            else:
                logger.warning("⚠️ Ollama validazione: nessun JSON trovato")
                return {}

        except Exception as e:
            logger.error(f"❌ Errore validazione Ollama: {e}")
            return {}

    def _apply_corrections(self, regex_data: Dict, validation: Dict) -> Dict[str, Any]:
        """Applica correzioni e calcola confidence finale."""
        result = {}
        validations = validation.get('validations', {})

        for field, value in regex_data.items():
            if field.startswith('_context_'):
                continue  # Skip context fields

            field_validation = validations.get(field, {})

            # Se Ollama ha corretto il valore con alta confidence, usa la correzione
            if not field_validation.get('correct', True):
                corrected = field_validation.get('corrected_value')
                correction_confidence = field_validation.get('confidence', 0)

                if corrected and correction_confidence >= 0.7:
                    result[field] = corrected
                    result[f'_confidence_{field}'] = correction_confidence
                    result[f'_corrected_{field}'] = True
                    logger.info(f"🔧 Campo '{field}' corretto: {value} → {corrected} (conf: {correction_confidence})")
                else:
                    # Mantieni valore originale ma con confidence ridotta
                    result[field] = value
                    result[f'_confidence_{field}'] = max(0.3, correction_confidence)
            else:
                # Valore confermato
                confidence = field_validation.get('confidence', 0.8)
                result[field] = value
                result[f'_confidence_{field}'] = confidence

        # Aggiungi confidence globale
        result['_overall_confidence'] = validation.get('overall_confidence', 0.7)

        return result

    def _cross_validate(self, regex_data: Dict, validated_data: Dict) -> Dict[str, Any]:
        """Cross-validazione finale tra regex e risultati validati."""
        final = validated_data.copy()

        # Controlli di coerenza
        # 1. Se abbiamo codice scuola e provincia, verifica coerenza
        if 'istituto' in regex_data and 'provincia' in final:
            # Cerca codice scuola nell'istituto
            school_code_match = re.search(r'^([A-Z]{2})[A-Z]{2}\d+', str(regex_data.get('istituto', '')))
            if school_code_match:
                code_province = school_code_match.group(1)
                expected_province = RegexExtractor.PROVINCE_CODE_MAP.get(code_province)
                if expected_province and expected_province != final.get('provincia'):
                    logger.warning(f"⚠️ Cross-validation: provincia mismatch. Codice={code_province}→{expected_province}, estratto={final.get('provincia')}")
                    final['_warning_provincia'] = f"Possibile errore: codice scuola indica {expected_province}"

        # 2. Verifica coerenza date (inizio < fine)
        if 'data_inizio_servizio' in final and 'data_fine_contratto' in final:
            try:
                inizio = datetime.fromisoformat(str(final['data_inizio_servizio']))
                fine = datetime.fromisoformat(str(final['data_fine_contratto']))
                if fine < inizio:
                    logger.warning(f"⚠️ Cross-validation: data_fine < data_inizio")
                    final['_warning_date'] = "Data fine precedente a data inizio"
                    final['_confidence_data_fine_contratto'] = 0.3
            except:
                pass

        # 3. Verifica ore settimanali ragionevoli
        if 'ore_settimanali' in final:
            ore = final['ore_settimanali']
            if isinstance(ore, (int, float)) and (ore < 1 or ore > 40):
                logger.warning(f"⚠️ Cross-validation: ore_settimanali non ragionevoli: {ore}")
                final['_warning_ore'] = f"Ore settimanali sospette: {ore}"
                final['_confidence_ore_settimanali'] = 0.4

        return final

    def extract(self, testo: str) -> Optional[Dict[str, Any]]:
        """
        Estrae dati con pipeline ibrida:
        1. Regex extraction con contesto
        2. Validazione Ollama
        3. Cross-validation
        """
        try:
            # Step 1: Estrazione regex
            logger.info("📊 Step 1: Estrazione Regex con contesto...")
            regex_data = self.regex_extractor.extract(testo)

            if not regex_data:
                logger.warning("⚠️ Regex non ha trovato classe_concorso")
                return None

            # Step 2: Estrai contesti per validazione
            contexts = self._extract_all_contexts(testo, regex_data)
            logger.info(f"📊 Contesti estratti per {len(contexts)} campi")

            # Step 3: Validazione Ollama con contesto
            logger.info("📊 Step 2: Validazione Ollama...")
            validation = self._validate_with_ollama(regex_data, contexts, testo)

            if validation:
                # Step 4: Applica correzioni
                validated_data = self._apply_corrections(regex_data, validation)

                # Step 5: Cross-validation
                logger.info("📊 Step 3: Cross-validation...")
                final_data = self._cross_validate(regex_data, validated_data)

                logger.info(f"✅ HybridExtractor completato con confidence: {final_data.get('_overall_confidence', 'N/A')}")
                return final_data
            else:
                # Fallback: ritorna dati regex con confidence media
                logger.warning("⚠️ Ollama validation fallita, uso solo regex")
                result = {k: v for k, v in regex_data.items() if not k.startswith('_context_')}
                result['_overall_confidence'] = 0.5
                result['_validation_skipped'] = True
                return result

        except Exception as e:
            logger.error(f"❌ Errore HybridExtractor: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None


class SpacyBertExtractor(InterpelloExtractor):
    """
    Estrazione usando spaCy + BERT italiano + validazione Ollama.

    Pipeline:
    1. spaCy (it_core_news_lg) per NER italiano
    2. BERT italiano per NER avanzato
    3. Pattern matching per entità specifiche scuola
    4. Merge risultati con punteggi di confidence
    5. Validazione finale con Ollama
    """

    def __init__(self, ollama_base_url: str = None, ollama_model: str = None, use_ollama_validation: bool = True):
        """
        Inizializza l'estrattore spaCy + BERT.

        Args:
            ollama_base_url: URL di Ollama per validazione (opzionale)
            ollama_model: Modello Ollama per validazione
            use_ollama_validation: Se True, usa Ollama per validare i risultati
        """
        self.use_ollama_validation = use_ollama_validation
        self.ollama_base_url = ollama_base_url or os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
        self.ollama_model = ollama_model or os.getenv('OLLAMA_MODEL_INTERPRETATION', 'llama3.1:8b')
        self.regex_extractor = RegexExtractor()  # Fallback e complemento
        logger.info(f"✅ SpacyBertExtractor inizializzato (Ollama validation: {use_ollama_validation})")

    def extract(self, testo: str) -> Optional[Dict[str, Any]]:
        """
        Estrae dati con pipeline NLP completa.

        Pipeline:
        1. Estrazione NLP (spaCy + BERT)
        2. Estrazione Regex (complemento)
        3. Merge risultati
        4. Validazione Ollama (opzionale)
        """
        try:
            from app.services.nlp_service import get_nlp_extractor

            logger.info("📊 SpacyBertExtractor: avvio pipeline NLP...")

            # Step 1: Estrazione NLP
            logger.info("🧠 Step 1: Estrazione spaCy + BERT...")
            nlp_extractor = get_nlp_extractor()
            nlp_result = nlp_extractor.extract_for_interpello(testo)

            # Step 2: Estrazione Regex come complemento
            logger.info("📝 Step 2: Estrazione Regex complementare...")
            regex_result = self.regex_extractor.extract(testo) or {}

            # Step 3: Merge risultati (NLP ha priorità se confidence alta)
            merged = self._merge_results(nlp_result, regex_result)

            # Step 4: Validazione Ollama (opzionale)
            if self.use_ollama_validation and merged.get('classe_concorso'):
                logger.info("🔍 Step 3: Validazione Ollama...")
                merged = self._validate_with_ollama(merged, testo)

            # Calcola confidence globale
            confidences = [v for k, v in merged.get('confidence_scores', {}).items() if isinstance(v, (int, float))]
            merged['_overall_confidence'] = sum(confidences) / len(confidences) if confidences else 0.5
            merged['_extraction_method'] = 'spacy_bert'

            logger.info(f"✅ SpacyBertExtractor completato: confidence={merged.get('_overall_confidence', 0):.2f}")
            return merged

        except Exception as e:
            logger.error(f"❌ Errore SpacyBertExtractor: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback a regex
            logger.warning("⚠️ Fallback a RegexExtractor")
            return self.regex_extractor.extract(testo)

    def _merge_results(self, nlp_result: Dict, regex_result: Dict) -> Dict[str, Any]:
        """
        Unisce i risultati NLP e Regex.

        Logica:
        - Se NLP ha confidence > 0.8, usa NLP
        - Altrimenti, usa Regex come fallback
        - Mantieni entrambi per cross-validation
        """
        merged = {
            'confidence_scores': {},
            '_nlp_entities': nlp_result.get('all_entities', {}),
            '_regex_raw': regex_result
        }

        # Campi da estrarre (incluso meccanografico da NLP)
        fields = ['classe_concorso', 'ore_settimanali', 'provincia', 'citta',
                  'istituto', 'meccanografico', 'email_contatto', 'telefono_contatto', 'data_scadenza']

        nlp_confidence = nlp_result.get('confidence_scores', {})

        for field in fields:
            nlp_value = nlp_result.get(field)
            regex_value = regex_result.get(field)
            nlp_conf = nlp_confidence.get(field, 0)

            # Mapping campi (NLP usa nomi leggermente diversi)
            if field == 'email_contatto' and not nlp_value:
                nlp_value = nlp_result.get('email_contatto')
            if field == 'telefono_contatto' and not nlp_value:
                nlp_value = nlp_result.get('telefono_contatto')

            # Logica di selezione
            if nlp_value and nlp_conf >= 0.8:
                merged[field] = nlp_value
                merged['confidence_scores'][field] = nlp_conf
                merged[f'_source_{field}'] = 'nlp'
            elif nlp_value and regex_value and nlp_value == regex_value:
                # Concordanza = alta confidence
                merged[field] = nlp_value
                merged['confidence_scores'][field] = max(nlp_conf, 0.9)
                merged[f'_source_{field}'] = 'both'
            elif regex_value:
                merged[field] = regex_value
                merged['confidence_scores'][field] = 0.75  # Regex ha buona confidence
                merged[f'_source_{field}'] = 'regex'
            elif nlp_value:
                merged[field] = nlp_value
                merged['confidence_scores'][field] = nlp_conf
                merged[f'_source_{field}'] = 'nlp'

        # Copia campi extra da regex che NLP non estrae
        extra_fields = ['data_inizio_servizio', 'data_fine_contratto', 'indirizzo']
        for field in extra_fields:
            if field in regex_result and regex_result[field]:
                merged[field] = regex_result[field]
                merged['confidence_scores'][field] = 0.75
                merged[f'_source_{field}'] = 'regex'

        return merged

    def _validate_with_ollama(self, data: Dict, testo: str) -> Dict[str, Any]:
        """Valida i risultati usando Ollama."""
        try:
            import httpx

            # Prepara prompt di validazione
            extracted_summary = json.dumps({
                k: v for k, v in data.items()
                if not k.startswith('_') and k != 'confidence_scores'
            }, indent=2, ensure_ascii=False)

            prompt = f"""Verifica questi dati estratti da un interpello scolastico.

DATI ESTRATTI:
{extracted_summary}

TESTO ORIGINALE (primi 3000 caratteri):
{testo[:3000]}

Per ogni campo, indica se è corretto o suggerisci la correzione.
Rispondi SOLO con JSON valido:
{{
    "validations": {{
        "classe_concorso": {{"correct": true/false, "corrected_value": "..."}},
        "provincia": {{"correct": true/false, "corrected_value": "..."}},
        ...
    }}
}}"""

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 500}
                    }
                )
                response.raise_for_status()

            result_text = response.json().get('response', '')

            # Parse JSON dalla risposta
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                validation = json.loads(json_match.group(0))
                validations = validation.get('validations', {})

                # Applica correzioni
                for field, val_data in validations.items():
                    if field in data and not val_data.get('correct', True):
                        corrected = val_data.get('corrected_value')
                        if corrected:
                            data[field] = corrected
                            data['confidence_scores'][field] = 0.85
                            data[f'_corrected_{field}'] = True
                            logger.info(f"🔧 Ollama ha corretto {field}: {corrected}")

            logger.info("✅ Validazione Ollama completata")

        except Exception as e:
            logger.warning(f"⚠️ Validazione Ollama fallita: {e}")

        return data


class UnifiedInterpelloExtractor(InterpelloExtractor):
    """
    Estrattore che usa il servizio UnifiedExtractor per interpelli.

    Pipeline: Regex → NLP (spaCy + BERT) → LLM (Ollama via coda) → ChatGPT (se autorizzato)
    Usa la coda LLM per evitare sovraccarichi e timeout.
    Legge impostazioni ChatGPT dalle system settings.
    """

    def __init__(self):
        """Inizializza l'estrattore unificato."""
        from app.services.unified_extractor import get_unified_extractor
        self._unified_extractor = get_unified_extractor()
        logger.info("✅ UnifiedInterpelloExtractor inizializzato (pipeline: Regex → NLP → LLM → ChatGPT)")

    def extract(self, testo: str) -> Optional[Dict[str, Any]]:
        """
        Estrae dati usando la pipeline unificata.

        Args:
            testo: Testo completo dell'interpello

        Returns:
            Dict con dati estratti e metadati, o None se fallisce
        """
        try:
            logger.info("📊 UnifiedInterpelloExtractor: avvio estrazione...")

            # Chiama l'estrattore unificato con tipo="interpello"
            result = self._unified_extractor.extract(
                testo=testo,
                tipo="interpello",
                use_ollama=True  # Usa LLM locale
                # use_chatgpt e chatgpt_as_fallback vengono letti dalle impostazioni di sistema
            )

            if not result:
                logger.warning("⚠️ UnifiedExtractor non ha restituito risultati")
                return None

            # Verifica che abbiamo almeno la classe di concorso
            if not result.get('classe_concorso'):
                logger.warning("⚠️ classe_concorso non trovata")
                return None

            # Log risultati
            completeness = result.get('_completeness', 0)
            confidence = result.get('_overall_confidence', 0)
            steps = [s['step'] for s in result.get('_pipeline_steps', []) if s.get('success')]

            logger.info(
                f"✅ UnifiedInterpelloExtractor completato: "
                f"pipeline={' → '.join(steps)}, "
                f"completezza={completeness:.0%}, confidence={confidence:.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Errore UnifiedInterpelloExtractor: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None


class ExtractorFactory:
    """Factory per creare l'estrattore appropriato basato sulla configurazione."""

    @staticmethod
    def create(strategy: str = None) -> InterpelloExtractor:
        """
        Crea un estrattore basato sulla strategia specificata.

        Args:
            strategy: Nome della strategia (openai, ollama, regex, gemma).
                     Se None, legge da variabile d'ambiente INTERPELLO_PARSER_STRATEGY

        Returns:
            Istanza di InterpelloExtractor
        """
        if strategy is None:
            strategy = os.getenv('INTERPELLO_PARSER_STRATEGY', 'regex')

        strategy = strategy.lower()
        logger.info(f"🔧 Creazione estrattore con strategia: {strategy}")

        if strategy == 'regex':
            return RegexExtractor()

        elif strategy == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("⚠️ OPENAI_API_KEY non configurata, fallback a regex")
                return RegexExtractor()

            model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
            return OpenAIExtractor(api_key=api_key, model=model)

        elif strategy == 'ollama':
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
            model = os.getenv('OLLAMA_MODEL_INTERPRETATION', 'llama3.1:8b')
            return OllamaExtractor(base_url=base_url, model=model, timeout=600.0)

        elif strategy == 'gemma':
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
            model = os.getenv('OLLAMA_MODEL_GEMMA', 'gemma2:2b')
            return OllamaExtractor(base_url=base_url, model=model, timeout=600.0)

        elif strategy == 'hybrid' or strategy == 'smart':
            # Strategia ibrida: regex + validazione Ollama
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
            model = os.getenv('OLLAMA_MODEL_INTERPRETATION', 'llama3.1:8b')
            return HybridExtractor(ollama_base_url=base_url, ollama_model=model)

        elif strategy == 'nlp' or strategy == 'spacy' or strategy == 'bert':
            # Strategia NLP: spaCy + BERT + validazione Ollama
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
            model = os.getenv('OLLAMA_MODEL_INTERPRETATION', 'llama3.1:8b')
            use_validation = os.getenv('NLP_USE_OLLAMA_VALIDATION', 'true').lower() == 'true'
            return SpacyBertExtractor(
                ollama_base_url=base_url,
                ollama_model=model,
                use_ollama_validation=use_validation
            )

        elif strategy == 'nlp_only' or strategy == 'spacy_only':
            # Solo NLP senza validazione Ollama
            return SpacyBertExtractor(use_ollama_validation=False)

        elif strategy == 'unified':
            # Strategia unificata: Regex → NLP → LLM → ChatGPT (se autorizzato)
            # Usa coda LLM e legge impostazioni ChatGPT da sistema
            return UnifiedInterpelloExtractor()

        else:
            logger.warning(f"⚠️ Strategia sconosciuta '{strategy}', fallback a regex")
            return RegexExtractor()
