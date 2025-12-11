"""
Semantic Validator - Validazione semantica dati estratti
Controlla:
- Classe concorso esiste nel database
- Date coerenti (non antecedenti, ordine logico)
- Altri controlli di coerenza
"""
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, date
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SemanticValidator:
    """Validatore semantico per dati interpelli."""

    def __init__(self, db: Session = None):
        """
        Inizializza validator con connessione DB opzionale.

        Args:
            db: Sessione database per validazione con DB
        """
        self.db = db

    def extract_classe_from_context(self, testo: str) -> Optional[str]:
        """
        Cerca menzioni esplicite di "classe di concorso" nel testo.

        Args:
            testo: Testo completo (oggetto + corpo + allegati)

        Returns:
            Codice classe trovato o None
        """
        if not testo:
            return None

        import re

        # Pattern per "classe di concorso A028", "Classe di Concorso: AB24", etc
        patterns = [
            r'classe\s+(?:di\s+)?concorso[:\s]+([A-Z]{1,2}[-\s]?\d{2,3})',
            r'classe[:\s]+([A-Z]{1,2}[-\s]?\d{2,3})',
            r'c\.d\.c\.[:\s]*([A-Z]{1,2}[-\s]?\d{2,3})',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, testo, re.IGNORECASE)
            for match in matches:
                codice_raw = match.group(1)
                # Normalizza (rimuovi spazi, trattini)
                codice_norm = codice_raw.upper().replace('-', '').replace(' ', '').strip()

                # Verifica formato valido
                if re.match(r'^[A-Z]{1,2}\d{2,3}$', codice_norm):
                    logger.info(f"🔍 Trovata menzione esplicita nel contesto: '{codice_raw}' → {codice_norm}")
                    return codice_norm

        return None

    def validate_classe_concorso(self, classe: str, testo_originale: str = None) -> Dict[str, Any]:
        """
        Valida che la classe di concorso esista nel database E sia coerente con il contesto.

        Args:
            classe: Codice classe estratto (es: A028, AB24, AL01)
            testo_originale: Testo completo per analisi contestuale (opzionale)

        Returns:
            {
                'valid': bool,
                'exists': bool,
                'normalized': str,
                'context_match': bool,  # True se trovata menzione esplicita e corrisponde
                'context_value': str or None,  # Classe trovata nel contesto
                'corrected': str or None,  # Classe corretta se diversa
                'info': dict or None
            }
        """
        result = {
            'valid': False,
            'exists': False,
            'normalized': None,
            'context_match': False,
            'context_value': None,
            'corrected': None,
            'reason': None
        }

        if not classe:
            result['reason'] = 'Classe concorso mancante'
            return result

        # Normalizza classe (rimuovi spazi, trattini, uppercase)
        classe_norm = classe.upper().replace('-', '').replace(' ', '').strip()

        # Controlla formato base (1-2 lettere + 2-3 cifre)
        import re
        if not re.match(r'^[A-Z]{1,2}\d{2,3}$', classe_norm):
            result['normalized'] = classe_norm
            result['reason'] = f'Formato invalido: {classe_norm}'
            return result

        result['normalized'] = classe_norm

        # ANALISI CONTESTUALE (priorità massima)
        if testo_originale:
            context_classe = self.extract_classe_from_context(testo_originale)
            result['context_value'] = context_classe

            if context_classe:
                if context_classe == classe_norm:
                    # Perfetto! Classe estratta corrisponde al contesto
                    result['context_match'] = True
                    logger.info(f"✅ Classe {classe_norm} confermata dal contesto")
                else:
                    # ERRORE: classe estratta NON corrisponde alla menzione esplicita
                    result['valid'] = False
                    result['context_match'] = False
                    result['corrected'] = context_classe
                    result['reason'] = f"Classe estratta ({classe_norm}) NON corrisponde alla menzione nel testo ({context_classe})"
                    logger.error(f"❌ CONTEXT MISMATCH: estratto={classe_norm}, contesto={context_classe}")
                    return result

        # Se abbiamo DB, controlla esistenza
        if self.db:
            try:
                from app.models.classe_concorso import ClasseConcorso
                from app.data.classi_concorso import normalizza_classe_concorso

                # Usa la funzione di normalizzazione ufficiale (restituisce formato con trattino: A-44)
                classe_ufficiale = normalizza_classe_concorso(classe)

                # Cerca sia con formato normalizzato che con formato SIDI (senza trattino)
                classe_db = self.db.query(ClasseConcorso).filter(
                    ClasseConcorso.codice == classe_ufficiale
                ).first()

                # Se non trovato, prova anche senza trattino (formato SIDI)
                if not classe_db:
                    classe_db = self.db.query(ClasseConcorso).filter(
                        ClasseConcorso.codice == classe_norm
                    ).first()

                if classe_db:
                    result['valid'] = True
                    result['exists'] = True
                    result['info'] = {
                        'codice': classe_db.codice,
                        'descrizione': classe_db.descrizione,
                        'area': classe_db.area
                    }
                    logger.info(f"✅ Classe {classe_norm} trovata in DB: {classe_db.descrizione}")
                    return result
                else:
                    # Classe non esiste nel DB
                    logger.warning(f"❌ Classe concorso {classe_norm} NON esiste nel database")
                    result['valid'] = False
                    result['exists'] = False
                    result['reason'] = f'Classe {classe_norm} non trovata nel database ufficiale'
                    return result

            except Exception as e:
                logger.error(f"Errore validazione classe concorso DB: {e}")
                # Se errore DB, valida solo formato
                result['valid'] = True  # Formato OK, ma non verificata esistenza
                result['exists'] = None  # Unknown
                result['reason'] = f'DB non disponibile: {str(e)}'
                return result
        else:
            # Senza DB, valida solo formato
            result['valid'] = True
            result['exists'] = None  # Unknown senza DB
            result['reason'] = 'Formato valido ma DB non disponibile per verifica esistenza'
            return result

    def validate_dates(self, dati: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida coerenza date.

        Controlli:
        - data_scadenza >= oggi
        - data_inizio_servizio >= oggi
        - data_fine_contratto >= data_inizio_servizio
        - date non antecedenti di più di 1 anno

        Args:
            dati: Dict con campi data

        Returns:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []
        today = date.today()

        # Estrai date
        data_scadenza = self._parse_date(dati.get('data_scadenza'))
        data_inizio = self._parse_date(dati.get('data_inizio_servizio'))
        data_fine = self._parse_date(dati.get('data_fine_contratto'))
        data_pubblicazione = self._parse_date(dati.get('data_pubblicazione'))

        # Controlla data_scadenza
        if data_scadenza:
            # Se è nel passato - per interpelli può essere normale (interpello scaduto)
            if data_scadenza < today:
                days_past = (today - data_scadenza).days
                if days_past > 60:
                    # Molto vecchio - probabilmente errore di parsing
                    warnings.append(f"data_scadenza ({data_scadenza}) è {days_past} giorni nel passato (interpello molto vecchio)")
                else:
                    # Recentemente scaduto - normale
                    warnings.append(f"data_scadenza ({data_scadenza}) è {days_past} giorni nel passato (interpello scaduto)")
            # Se è troppo lontana nel futuro (>1 anno)
            elif data_scadenza > today and (data_scadenza - today).days > 365:
                warnings.append(f"data_scadenza ({data_scadenza}) è molto lontana (>{(data_scadenza - today).days} giorni)")

        # Controlla data_inizio_servizio
        if data_inizio:
            # Se è molto nel passato (>2 mesi)
            if data_inizio < today and (today - data_inizio).days > 60:
                warnings.append(f"data_inizio_servizio ({data_inizio}) è {(today - data_inizio).days} giorni nel passato")

        # Controlla data_fine_contratto
        if data_fine:
            # Deve essere dopo data_inizio
            if data_inizio and data_fine < data_inizio:
                errors.append(f"data_fine_contratto ({data_fine}) < data_inizio_servizio ({data_inizio})")

            # Nel passato - può essere normale per interpelli vecchi
            if data_fine < today:
                days_past = (today - data_fine).days
                if days_past > 60:
                    warnings.append(f"data_fine_contratto ({data_fine}) è {days_past} giorni nel passato (contratto terminato)")
                else:
                    # Recentemente terminato - normale
                    warnings.append(f"data_fine_contratto ({data_fine}) è {days_past} giorni nel passato")

        # Controlla data_pubblicazione
        if data_pubblicazione:
            # Non deve essere nel futuro
            if data_pubblicazione > today:
                errors.append(f"data_pubblicazione ({data_pubblicazione}) è nel futuro")

            # Non deve essere troppo vecchia (>1 anno)
            if (today - data_pubblicazione).days > 365:
                warnings.append(f"data_pubblicazione ({data_pubblicazione}) è molto vecchia (>{(today - data_pubblicazione).days} giorni)")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def validate_ore_settimanali(self, ore: int, testo_originale: str = None) -> Dict[str, Any]:
        """
        Valida ore settimanali con analisi contestuale.

        Args:
            ore: Numero ore
            testo_originale: Testo per verifica contestuale

        Returns:
            {'valid': bool, 'reason': str, 'context_found': str, 'corrected': int}
        """
        import re

        result = {
            'valid': False,
            'reason': None,
            'context_found': None,
            'corrected': None
        }

        if not ore:
            result['reason'] = 'Ore mancanti'
            return result

        if not isinstance(ore, (int, float)):
            result['reason'] = f'Ore non numeriche: {ore}'
            return result

        ore = int(ore)

        if ore < 1:
            result['reason'] = f'Ore < 1: {ore}'
            return result

        if ore > 40:
            result['reason'] = f'Ore > 40 (anomalo): {ore}'
            return result

        # VALIDAZIONE CONTESTUALE: verifica che le ore estratte siano effettivamente ore di lavoro
        if testo_originale:
            # Cerca il numero nel testo con contesto
            # Pattern: cerca "N ore" o "ore N" nel contesto di supplenza/cattedra
            patterns = [
                # "da 17 ore" in contesto cattedra/supplenza
                rf'(?:da\s+)?{ore}\s*(?:ore|h\.?)(?:\s*settimanali?)?\s*[)\s,]?(?:\s*(?:cattedra|suppl|posti?))?',
                # "ore 17" in contesto
                rf'(?:ore|h\.?)\s*{ore}(?:/\d+)?\s*(?:settimanali?)?',
                # Cerca contesto più ampio
                rf'.{{0,50}}{ore}\s*(?:ore|h).{{0,50}}'
            ]

            for pattern in patterns:
                match = re.search(pattern, testo_originale, re.IGNORECASE)
                if match:
                    # Estrai contesto più ampio
                    start = max(0, match.start() - 30)
                    end = min(len(testo_originale), match.end() + 30)
                    result['context_found'] = testo_originale[start:end].strip()

                    # Verifica che il contesto sia appropriato (non es: "ore 9:30", "Art. 17")
                    context_lower = result['context_found'].lower()

                    # Esclusioni: orari (es: ore 9:30), articoli (es: Art. 17)
                    if re.search(rf'{ore}[:.]\d{{2}}', result['context_found']):
                        logger.warning(f"⚠️ Ore {ore} sembra essere un orario, non ore settimanali")
                        continue

                    if re.search(rf'(?:art\.?|articolo)\s*{ore}', context_lower):
                        logger.warning(f"⚠️ {ore} sembra riferirsi a un articolo, non ore settimanali")
                        continue

                    # Contesto valido trovato
                    result['valid'] = True
                    result['reason'] = f'Ore {ore} confermate dal contesto'
                    logger.info(f"✅ Ore {ore} validate dal contesto: '{result['context_found'][:50]}...'")
                    break

            # Se nessun contesto trovato ma ore sono in range standard, accetta con warning
            if not result['context_found']:
                if ore in [6, 9, 12, 15, 18, 24]:
                    result['valid'] = True
                    result['reason'] = f'Ore {ore} standard ma contesto non trovato'
                else:
                    result['valid'] = True  # Accetta ma con warning
                    result['reason'] = f'Ore {ore} non standard e contesto non trovato - verificare'
        else:
            # Senza testo originale, valida solo range
            if ore in [6, 9, 12, 15, 18, 24]:
                result['valid'] = True
                result['reason'] = 'OK (range standard)'
            else:
                result['valid'] = True
                result['reason'] = f'Ore {ore} non standard (tipico: 6,9,12,15,18,24) - verificare'

        return result

    def validate_numero_posti(self, posti: int) -> Dict[str, Any]:
        """Valida numero posti."""
        if not posti:
            return {'valid': True, 'reason': 'Opzionale'}

        if not isinstance(posti, (int, float)):
            return {'valid': False, 'reason': f'Posti non numerico: {posti}'}

        if posti < 1:
            return {'valid': False, 'reason': f'Posti < 1: {posti}'}

        if posti > 100:
            return {'valid': False, 'reason': f'Posti > 100 (anomalo): {posti}'}

        return {'valid': True, 'reason': 'OK'}

    def validate_provincia(self, provincia: str, testo_originale: str = None) -> Dict[str, Any]:
        """
        Valida provincia estratta confrontandola con codice meccanografico nel testo.

        Il codice meccanografico ha le prime 2 lettere = sigla provincia:
        - TAIC = Taranto
        - PSRI = Pesaro-Urbino
        - FIIC = Firenze
        - RMIC = Roma
        - etc.

        Args:
            provincia: Provincia estratta
            testo_originale: Testo per cercare codice meccanografico

        Returns:
            Dict con valid, reason, corrected (se possibile)
        """
        import re

        result = {
            'valid': True,
            'reason': None,
            'corrected': None,
            'codice_mecc_found': None
        }

        if not provincia:
            result['valid'] = False
            result['reason'] = 'Provincia mancante'
            return result

        if not testo_originale:
            result['reason'] = 'Testo originale non disponibile per verifica'
            return result

        # Mappa sigle provincia → nome provincia
        SIGLA_TO_PROVINCIA = {
            'AG': 'Agrigento', 'AL': 'Alessandria', 'AN': 'Ancona', 'AO': 'Aosta',
            'AR': 'Arezzo', 'AP': 'Ascoli Piceno', 'AT': 'Asti', 'AV': 'Avellino',
            'BA': 'Bari', 'BT': 'Barletta-Andria-Trani', 'BL': 'Belluno', 'BN': 'Benevento',
            'BG': 'Bergamo', 'BI': 'Biella', 'BO': 'Bologna', 'BZ': 'Bolzano',
            'BS': 'Brescia', 'BR': 'Brindisi', 'CA': 'Cagliari', 'CL': 'Caltanissetta',
            'CB': 'Campobasso', 'CE': 'Caserta', 'CT': 'Catania', 'CZ': 'Catanzaro',
            'CH': 'Chieti', 'CO': 'Como', 'CS': 'Cosenza', 'CR': 'Cremona',
            'KR': 'Crotone', 'CN': 'Cuneo', 'EN': 'Enna', 'FM': 'Fermo',
            'FE': 'Ferrara', 'FI': 'Firenze', 'FG': 'Foggia', 'FC': 'Forlì-Cesena',
            'FR': 'Frosinone', 'GE': 'Genova', 'GO': 'Gorizia', 'GR': 'Grosseto',
            'IM': 'Imperia', 'IS': 'Isernia', 'SP': 'La Spezia', 'AQ': "L'Aquila",
            'LT': 'Latina', 'LE': 'Lecce', 'LC': 'Lecco', 'LI': 'Livorno',
            'LO': 'Lodi', 'LU': 'Lucca', 'MC': 'Macerata', 'MN': 'Mantova',
            'MS': 'Massa-Carrara', 'MT': 'Matera', 'ME': 'Messina', 'MI': 'Milano',
            'MO': 'Modena', 'MB': 'Monza e Brianza', 'NA': 'Napoli', 'NO': 'Novara',
            'NU': 'Nuoro', 'OR': 'Oristano', 'PD': 'Padova', 'PA': 'Palermo',
            'PR': 'Parma', 'PV': 'Pavia', 'PG': 'Perugia', 'PS': 'Pesaro-Urbino',
            'PE': 'Pescara', 'PC': 'Piacenza', 'PI': 'Pisa', 'PT': 'Pistoia',
            'PN': 'Pordenone', 'PZ': 'Potenza', 'PO': 'Prato', 'RG': 'Ragusa',
            'RA': 'Ravenna', 'RC': 'Reggio Calabria', 'RE': 'Reggio Emilia',
            'RI': 'Rieti', 'RN': 'Rimini', 'RM': 'Roma', 'RO': 'Rovigo',
            'SA': 'Salerno', 'SS': 'Sassari', 'SV': 'Savona', 'SI': 'Siena',
            'SR': 'Siracusa', 'SO': 'Sondrio', 'SU': 'Sud Sardegna', 'TA': 'Taranto',
            'TE': 'Teramo', 'TR': 'Terni', 'TO': 'Torino', 'TP': 'Trapani',
            'TN': 'Trento', 'TV': 'Treviso', 'TS': 'Trieste', 'UD': 'Udine',
            'VA': 'Varese', 'VE': 'Venezia', 'VB': 'Verbano-Cusio-Ossola',
            'VC': 'Vercelli', 'VR': 'Verona', 'VV': 'Vibo Valentia', 'VI': 'Vicenza',
            'VT': 'Viterbo'
        }

        # Cerca codice meccanografico della SCUOLA nel testo
        # Formato CORRETTO: 2 lettere provincia + 2 lettere tipo + 5-6 cifre + opzionale lettera
        # Esempi validi: TAIC87700D, PSRI02000B, FIIC82700R, RMIC8GC00T
        # IMPORTANTE: deve contenere CIFRE per distinguerlo da nomi propri (es: TRIFILETTI)
        patterns = [
            r'(?:Da:|From:|mittente:?)\s*["\']?([A-Z]{2}[A-Z]{2}\d{5,6}[A-Z0-9]?)@(?:pec\.)?istruzione\.it',  # Email mittente
            r'\b([A-Z]{2}[A-Z]{2}\d{5,6}[A-Z0-9]?)@(?:pec\.)?istruzione\.it',  # Qualsiasi email scuola
            r'Codice\s+(?:meccanografico|Mecc\.?)[\s:]+([A-Z]{2}[A-Z]{2}\d{5,6}[A-Z0-9]?)',  # Codice esplicito
        ]

        codici_trovati = []
        for pattern in patterns:
            matches = re.findall(pattern, testo_originale, re.IGNORECASE)
            for match in matches:
                codice = match.upper() if isinstance(match, str) else match[0].upper()
                # Verifica che contenga almeno 4 cifre (esclude parole come TRIFILETTI)
                if sum(c.isdigit() for c in codice) >= 4:
                    # Escludi codici USP/USR (iniziano con "USPTA", "DRPU", etc)
                    if not codice.startswith(('USP', 'USR', 'DRP', 'MIM')):
                        if codice not in codici_trovati:
                            codici_trovati.append(codice)

        if not codici_trovati:
            result['reason'] = 'Nessun codice meccanografico scuola trovato nel testo'
            return result

        # Prendi il primo codice trovato (più probabile essere la scuola origine)
        codice_mecc = codici_trovati[0]
        result['codice_mecc_found'] = codice_mecc

        # Estrai sigla provincia dal codice (prime 2 lettere)
        sigla_provincia = codice_mecc[:2].upper()
        provincia_corretta = SIGLA_TO_PROVINCIA.get(sigla_provincia)

        if not provincia_corretta:
            result['reason'] = f'Sigla provincia {sigla_provincia} non riconosciuta'
            return result

        # Confronta con provincia estratta (normalizza per confronto)
        provincia_norm = provincia.upper().strip()
        provincia_corretta_norm = provincia_corretta.upper()

        # Match esatto o parziale
        if provincia_norm == provincia_corretta_norm:
            result['valid'] = True
            result['reason'] = f'Provincia corrisponde al codice {codice_mecc}'
            return result

        # Match parziale (es: "Pesaro" vs "Pesaro-Urbino")
        if provincia_norm in provincia_corretta_norm or provincia_corretta_norm in provincia_norm:
            result['valid'] = True
            result['reason'] = f'Provincia corrisponde parzialmente ({provincia} ~ {provincia_corretta})'
            return result

        # MISMATCH! La provincia estratta non corrisponde al codice meccanografico
        result['valid'] = False
        result['corrected'] = provincia_corretta
        result['reason'] = (
            f"ERRORE: Provincia '{provincia}' NON corrisponde al codice scuola {codice_mecc} "
            f"(provincia corretta: {provincia_corretta}). "
            f"Probabilmente è stata estratta la provincia dell'USP che ha inoltrato."
        )
        logger.error(f"❌ PROVINCIA MISMATCH: estratto='{provincia}', codice={codice_mecc}, corretto={provincia_corretta}")

        return result

    def validate_all(self, dati: Dict[str, Any], testo_originale: str = None) -> Dict[str, Any]:
        """
        Esegue tutte le validazioni semantiche.

        Args:
            dati: Dati estratti da validare
            testo_originale: Testo completo per analisi contestuale (opzionale)

        Returns:
            {
                'valid': bool,
                'validations': {
                    'classe_concorso': {...},
                    'dates': {...},
                    'ore_settimanali': {...},
                    'numero_posti': {...},
                    'provincia': {...}
                },
                'errors': List[str],
                'warnings': List[str],
                'corrected_data': Dict (dati corretti se possibile)
            }
        """
        validations = {}
        errors = []
        warnings = []
        corrected_data = dati.copy() if dati else {}

        # 1. Valida classe concorso CON ANALISI CONTESTUALE
        if 'classe_concorso' in dati and dati['classe_concorso']:
            classe_validation = self.validate_classe_concorso(dati['classe_concorso'], testo_originale=testo_originale)
            validations['classe_concorso'] = classe_validation

            if not classe_validation['valid']:
                errors.append(f"Classe concorso: {classe_validation.get('reason')}")

                # Se c'è una correzione dal contesto, applicala
                if classe_validation.get('corrected'):
                    corrected_data['classe_concorso'] = classe_validation['corrected']
                    logger.info(f"🔧 Correzione automatica: {dati['classe_concorso']} → {classe_validation['corrected']}")

            elif classe_validation.get('exists') == False:
                # Se DB disponibile e classe NON esiste → ERRORE (non warning)
                errors.append(f"Classe concorso {classe_validation['normalized']} NON esiste nel database ufficiale")
            elif classe_validation.get('exists') is None:
                # Se DB non disponibile → warning
                warnings.append(f"Classe concorso {classe_validation['normalized']} non verificata (DB non disponibile)")

            # Normalizza classe
            if classe_validation.get('normalized') and not classe_validation.get('corrected'):
                corrected_data['classe_concorso'] = classe_validation['normalized']

        # 2. Valida date
        dates_validation = self.validate_dates(dati)
        validations['dates'] = dates_validation

        if not dates_validation['valid']:
            errors.extend(dates_validation['errors'])

        warnings.extend(dates_validation['warnings'])

        # 3. Valida ore settimanali CON ANALISI CONTESTUALE
        if 'ore_settimanali' in dati and dati['ore_settimanali']:
            ore_validation = self.validate_ore_settimanali(dati['ore_settimanali'], testo_originale=testo_originale)
            validations['ore_settimanali'] = ore_validation

            if not ore_validation['valid']:
                errors.append(f"Ore settimanali: {ore_validation['reason']}")
            elif 'non standard' in ore_validation.get('reason', '') or 'contesto non trovato' in ore_validation.get('reason', ''):
                warnings.append(ore_validation['reason'])

        # 4. Valida numero posti
        if 'numero_posti' in dati and dati['numero_posti']:
            posti_validation = self.validate_numero_posti(dati['numero_posti'])
            validations['numero_posti'] = posti_validation

            if not posti_validation['valid']:
                errors.append(f"Numero posti: {posti_validation['reason']}")

        # 5. Valida provincia (CRITICO per interpelli inoltrati da USP)
        if 'provincia' in dati and dati['provincia'] and testo_originale:
            provincia_validation = self.validate_provincia(dati['provincia'], testo_originale=testo_originale)
            validations['provincia'] = provincia_validation

            if not provincia_validation['valid']:
                errors.append(f"Provincia: {provincia_validation['reason']}")

                # Se c'è correzione automatica, applicala
                if provincia_validation.get('corrected'):
                    corrected_data['provincia'] = provincia_validation['corrected']
                    # Aggiorna anche citta se corrisponde alla vecchia provincia
                    if corrected_data.get('citta', '').upper() == dati['provincia'].upper():
                        corrected_data['citta'] = provincia_validation['corrected']
                    logger.info(f"🔧 Correzione automatica provincia: {dati['provincia']} → {provincia_validation['corrected']}")

            elif provincia_validation.get('codice_mecc_found'):
                logger.info(f"✅ Provincia '{dati['provincia']}' validata con codice {provincia_validation['codice_mecc_found']}")

        # Risultato finale
        return {
            'valid': len(errors) == 0,
            'validations': validations,
            'errors': errors,
            'warnings': warnings,
            'corrected_data': corrected_data
        }

    def _parse_date(self, date_value: Any) -> Optional[date]:
        """Parse date from various formats."""
        if not date_value:
            return None

        if isinstance(date_value, date):
            return date_value

        if isinstance(date_value, datetime):
            return date_value.date()

        if isinstance(date_value, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(date_value.replace('Z', '+00:00')).date()
            except:
                pass

            # Try other formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    return datetime.strptime(date_value, fmt).date()
                except:
                    pass

        return None
