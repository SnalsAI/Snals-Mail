"""
NLP Training Data - Dati per addestrare spaCy con entità specifiche del dominio scolastico.

Genera pattern per EntityRuler di spaCy con:
- Classi di concorso (A-01, A012, AA24, etc.)
- Codici meccanografici scuole (TAIC824001, BAIC123456, etc.)
- Nomi scuole
- Province italiane
"""

import json
import logging
import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Province italiane con codici
PROVINCE_ITALIANE = {
    # Nord-Ovest
    "TO": "TORINO", "VC": "VERCELLI", "NO": "NOVARA", "CN": "CUNEO",
    "AT": "ASTI", "AL": "ALESSANDRIA", "BI": "BIELLA", "VB": "VERBANIA",
    "AO": "AOSTA",
    "IM": "IMPERIA", "SV": "SAVONA", "GE": "GENOVA", "SP": "LA SPEZIA",
    "VA": "VARESE", "CO": "COMO", "SO": "SONDRIO", "MI": "MILANO",
    "BG": "BERGAMO", "BS": "BRESCIA", "PV": "PAVIA", "CR": "CREMONA",
    "MN": "MANTOVA", "LC": "LECCO", "LO": "LODI", "MB": "MONZA",
    # Nord-Est
    "BZ": "BOLZANO", "TN": "TRENTO",
    "VR": "VERONA", "VI": "VICENZA", "BL": "BELLUNO", "TV": "TREVISO",
    "VE": "VENEZIA", "PD": "PADOVA", "RO": "ROVIGO",
    "UD": "UDINE", "GO": "GORIZIA", "TS": "TRIESTE", "PN": "PORDENONE",
    # Emilia-Romagna
    "PC": "PIACENZA", "PR": "PARMA", "RE": "REGGIO EMILIA", "MO": "MODENA",
    "BO": "BOLOGNA", "FE": "FERRARA", "RA": "RAVENNA", "FC": "FORLI-CESENA",
    "RN": "RIMINI",
    # Centro
    "MS": "MASSA-CARRARA", "LU": "LUCCA", "PT": "PISTOIA", "FI": "FIRENZE",
    "LI": "LIVORNO", "PI": "PISA", "AR": "AREZZO", "SI": "SIENA",
    "GR": "GROSSETO", "PO": "PRATO",
    "PG": "PERUGIA", "TR": "TERNI",
    "VT": "VITERBO", "RI": "RIETI", "RM": "ROMA", "LT": "LATINA", "FR": "FROSINONE",
    # Marche
    "PU": "PESARO-URBINO", "AN": "ANCONA", "MC": "MACERATA", "AP": "ASCOLI PICENO", "FM": "FERMO",
    # Abruzzo-Molise
    "AQ": "L'AQUILA", "TE": "TERAMO", "PE": "PESCARA", "CH": "CHIETI",
    "CB": "CAMPOBASSO", "IS": "ISERNIA",
    # Sud
    "NA": "NAPOLI", "AV": "AVELLINO", "BN": "BENEVENTO", "CE": "CASERTA", "SA": "SALERNO",
    "FG": "FOGGIA", "BA": "BARI", "TA": "TARANTO", "BR": "BRINDISI", "LE": "LECCE", "BT": "BARLETTA-ANDRIA-TRANI",
    "PZ": "POTENZA", "MT": "MATERA",
    "CS": "COSENZA", "CZ": "CATANZARO", "RC": "REGGIO CALABRIA", "KR": "CROTONE", "VV": "VIBO VALENTIA",
    # Isole
    "TP": "TRAPANI", "PA": "PALERMO", "ME": "MESSINA", "AG": "AGRIGENTO",
    "CL": "CALTANISSETTA", "EN": "ENNA", "CT": "CATANIA", "RG": "RAGUSA", "SR": "SIRACUSA",
    "SS": "SASSARI", "NU": "NUORO", "CA": "CAGLIARI", "OR": "ORISTANO", "SU": "SUD SARDEGNA",
}

# Prefissi meccanografici per provincia
PREFISSI_MECCANOGRAFICI = {
    "BA": "BA",  # Bari
    "TA": "TA",  # Taranto
    "BR": "BR",  # Brindisi
    "LE": "LE",  # Lecce
    "FG": "FG",  # Foggia
    "BT": "BT",  # Barletta-Andria-Trani
    "RM": "RM",  # Roma
    "MI": "MI",  # Milano
    "NA": "NA",  # Napoli
    "TO": "TO",  # Torino
    "PA": "PA",  # Palermo
    "CT": "CT",  # Catania
    "FI": "FI",  # Firenze
    "BO": "BO",  # Bologna
    "GE": "GE",  # Genova
    "VE": "VE",  # Venezia
    # Aggiungi altre province secondo necessità
}


class NLPTrainingData:
    """Genera dati di training per spaCy EntityRuler."""

    def __init__(self):
        self.patterns: List[Dict[str, Any]] = []
        self._load_classi_concorso()
        self._load_scuole()
        self._load_province()

    def _load_classi_concorso(self):
        """Carica classi di concorso e genera pattern."""
        try:
            from app.data.classi_concorso import CLASSI_CONCORSO

            for codice_uff, (codice_sidi, grado, denominazione) in CLASSI_CONCORSO.items():
                # Pattern per codice ufficiale (A-01, A-12, etc.)
                self.patterns.append({
                    "label": "CLASSE_CONCORSO",
                    "pattern": codice_uff,
                    "id": f"cc_{codice_uff}"
                })

                # Pattern per codice SIDI (A001, A012, etc.)
                if codice_sidi != codice_uff:
                    self.patterns.append({
                        "label": "CLASSE_CONCORSO",
                        "pattern": codice_sidi,
                        "id": f"cc_{codice_sidi}"
                    })

                # Varianti senza trattino (A01, A12, etc.)
                senza_trattino = codice_uff.replace("-", "")
                if senza_trattino != codice_uff and senza_trattino != codice_sidi:
                    self.patterns.append({
                        "label": "CLASSE_CONCORSO",
                        "pattern": senza_trattino,
                        "id": f"cc_{senza_trattino}"
                    })

                # Pattern case-insensitive con token pattern
                # es: "classe di concorso A012" o "cdc A-12"
                self._add_token_pattern_classe(codice_uff)

            logger.info(f"✅ Caricati {len(CLASSI_CONCORSO)} classi di concorso")

        except ImportError as e:
            logger.warning(f"⚠️ Impossibile caricare classi_concorso: {e}")

    def _add_token_pattern_classe(self, codice: str):
        """Aggiunge pattern token-based per classe di concorso."""
        # Pattern: "classe di concorso A-12" o "classe concorso A012"
        base_code = codice.replace("-", "")

        # Pattern con "classe di concorso"
        self.patterns.append({
            "label": "CLASSE_CONCORSO",
            "pattern": [
                {"LOWER": "classe"},
                {"LOWER": {"IN": ["di", "del", "della"]}},
                {"LOWER": "concorso"},
                {"TEXT": {"REGEX": f"(?i){re.escape(codice)}|{re.escape(base_code)}"}}
            ],
            "id": f"cc_phrase_{codice}"
        })

        # Pattern con "cdc" abbreviato
        self.patterns.append({
            "label": "CLASSE_CONCORSO",
            "pattern": [
                {"LOWER": "cdc"},
                {"TEXT": {"REGEX": f"(?i){re.escape(codice)}|{re.escape(base_code)}"}}
            ],
            "id": f"cc_cdc_{codice}"
        })

    def _load_scuole(self):
        """Carica dati scuole e genera pattern."""
        data_dir = Path(__file__).parent.parent / "data"
        scuole_file = data_dir / "scuole_taranto.json"

        if not scuole_file.exists():
            logger.warning(f"⚠️ File scuole non trovato: {scuole_file}")
            return

        try:
            with open(scuole_file, 'r', encoding='utf-8') as f:
                scuole = json.load(f)

            for meccanografico, info in scuole.items():
                # Pattern per codice meccanografico
                self.patterns.append({
                    "label": "MECCANOGRAFICO",
                    "pattern": meccanografico.upper(),
                    "id": f"mec_{meccanografico}"
                })

                # Pattern minuscolo
                self.patterns.append({
                    "label": "MECCANOGRAFICO",
                    "pattern": meccanografico.lower(),
                    "id": f"mec_{meccanografico}_lower"
                })

                # Pattern per nome scuola
                nome = info.get("nome", "")
                if nome and len(nome) > 3:
                    self.patterns.append({
                        "label": "ISTITUTO",
                        "pattern": nome,
                        "id": f"ist_{meccanografico}"
                    })

                    # Variante con nome normalizzato
                    nome_norm = self._normalizza_nome_scuola(nome)
                    if nome_norm != nome:
                        self.patterns.append({
                            "label": "ISTITUTO",
                            "pattern": nome_norm,
                            "id": f"ist_{meccanografico}_norm"
                        })

            logger.info(f"✅ Caricate {len(scuole)} scuole")

        except Exception as e:
            logger.error(f"❌ Errore caricamento scuole: {e}")

    def _normalizza_nome_scuola(self, nome: str) -> str:
        """Normalizza nome scuola per matching."""
        # Espandi abbreviazioni comuni
        abbrev = {
            "IC": "Istituto Comprensivo",
            "IIS": "Istituto di Istruzione Superiore",
            "ITIS": "Istituto Tecnico Industriale Statale",
            "IPSIA": "Istituto Professionale Statale Industria e Artigianato",
            "LS": "Liceo Scientifico",
            "LC": "Liceo Classico",
            "ITI": "Istituto Tecnico Industriale",
            "ITC": "Istituto Tecnico Commerciale",
        }

        for ab, esteso in abbrev.items():
            if nome.upper().startswith(ab + " "):
                return nome  # Mantieni abbreviazione che è più comune

        return nome

    def _load_province(self):
        """Carica pattern per province italiane."""
        for sigla, nome in PROVINCE_ITALIANE.items():
            # Sigla provincia (MI, TA, BA, etc.)
            self.patterns.append({
                "label": "PROVINCIA",
                "pattern": sigla,
                "id": f"prov_{sigla}"
            })

            # Nome completo provincia
            self.patterns.append({
                "label": "PROVINCIA",
                "pattern": nome,
                "id": f"prov_{sigla}_nome"
            })

            # Nome con prima lettera maiuscola
            nome_title = nome.title()
            if nome_title != nome:
                self.patterns.append({
                    "label": "PROVINCIA",
                    "pattern": nome_title,
                    "id": f"prov_{sigla}_title"
                })

        logger.info(f"✅ Caricate {len(PROVINCE_ITALIANE)} province")

    def get_entity_ruler_patterns(self) -> List[Dict[str, Any]]:
        """Restituisce tutti i pattern per EntityRuler."""
        return self.patterns

    def get_meccanografico_regex(self) -> str:
        """
        Restituisce regex per codici meccanografici.

        Formato: [Provincia][Tipo][Numero][Carattere]
        - Provincia: 2 lettere (TA, BA, MI, etc.)
        - Tipo: IC, IS, PS, EE, MM, etc.
        - Numero: 5-6 cifre
        - Carattere finale opzionale

        Esempi: TAIC824001, BAIS123456, RMPS00123X
        """
        # Prefissi province (2 lettere)
        province = "|".join(PROVINCE_ITALIANE.keys())

        # Tipi istituto comuni
        tipi = "IC|IS|PS|EE|MM|PC|SD|RI|VE|CT|VC|AA|VR|SS|TD|TF|TE|TH|TL|TA|TB|RC|RA|RH|SF"

        return rf"\b({province})({tipi})\d{{5,6}}[A-Z0-9]?\b"

    def get_classe_concorso_regex(self) -> str:
        """
        Restituisce regex per classi di concorso.

        Formati:
        - A-01, A-12, A-42 (con trattino)
        - A01, A12, A42 (senza trattino)
        - A001, A012, A042 (con zero padding)
        - AA24, AB25, AC55 (lingue e strumenti)
        - B-02, B-15, B002 (laboratori)
        """
        return r"\b([AB][-]?\d{2,3}|[A-Z]{2}\d{2})\b"

    def export_training_data(self, output_file: str = None) -> Dict:
        """
        Esporta dati in formato per training spaCy.

        Returns:
            Dict con patterns e statistiche
        """
        # Conta per tipo
        counts = {}
        for p in self.patterns:
            label = p.get("label", "UNKNOWN")
            counts[label] = counts.get(label, 0) + 1

        data = {
            "version": "1.0",
            "total_patterns": len(self.patterns),
            "counts_by_label": counts,
            "patterns": self.patterns,
            "regexes": {
                "meccanografico": self.get_meccanografico_regex(),
                "classe_concorso": self.get_classe_concorso_regex()
            }
        }

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Training data esportati in {output_file}")

        return data


# Singleton per evitare ricaricamenti
_training_data: Optional[NLPTrainingData] = None


def get_training_data() -> NLPTrainingData:
    """Restituisce istanza singleton dei training data."""
    global _training_data
    if _training_data is None:
        _training_data = NLPTrainingData()
    return _training_data


def get_entity_patterns() -> List[Dict[str, Any]]:
    """Shortcut per ottenere i pattern."""
    return get_training_data().get_entity_ruler_patterns()


def get_custom_regexes() -> Dict[str, str]:
    """Restituisce regex custom per meccanografici e classi concorso."""
    td = get_training_data()
    return {
        "meccanografico": td.get_meccanografico_regex(),
        "classe_concorso": td.get_classe_concorso_regex()
    }
