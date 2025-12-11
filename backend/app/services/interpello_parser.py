"""
Servizio per parsing e estrazione dati dagli interpelli scolastici
"""

from typing import Dict, Optional, List
import logging
import json
import re
import os
from datetime import datetime, date
import requests
from bs4 import BeautifulSoup

from app.integrations.llm_client import LLMClient
from app.services.attachment_extractor import get_attachment_extractor
from app.services.interpello_extractors import ExtractorFactory, InterpelloExtractor
from app.services.smart_extractor import SmartInterpelloExtractor
from app.data.classi_concorso import normalizza_classe_concorso, get_info_classe

logger = logging.getLogger(__name__)


class InterpelloParser:
    """Parser AI per estrarre informazioni strutturate dagli interpelli"""

    EXTRACTION_PROMPT = """Estrai informazioni da questo interpello scolastico.

PRIORITÀ ASSOLUTA - CLASSE DI CONCORSO:
Cerca codici come: A042, A-42, AB24, AC55, ADSS
Posizioni comuni: oggetto email, corpo testo, allegati PDF
Formati: "classe di concorso A042", "classe A-42", "codice A042"
Normalizza: rimuovi spazi/trattini → "A-42" diventa "A042"

CAMPI DA ESTRARRE (solo se presenti):
- classe_concorso: codice classe (FONDAMENTALE!)
- numero_posti: numero intero
- ore_settimanali: numero intero
- data_scadenza: formato "2025-11-28T11:00:00"
- data_inizio_servizio: formato "2025-12-01"
- data_fine_contratto: formato "2026-06-30"
- provincia: es. "Taranto"
- citta: es. "Taranto"
- istituto: nome completo scuola
- indirizzo: indirizzo completo
- tipo_contratto: es. "supplenza", "spezzone orario"
- orario_giorni: giorni di servizio
- link_candidatura: URL completo
- data_pubblicazione: data ISO

ESEMPI:

Input: "Interpello A042 - Musica, 12 ore, scadenza 28/11/2025"
Output: {{"classe_concorso": "A042", "ore_settimanali": 12, "data_scadenza": "2025-11-28"}}

Input: "Supplenza classe di concorso AC-55 Clarinetto fino 30/06/2026"
Output: {{"classe_concorso": "AC55", "data_fine_contratto": "2026-06-30"}}

TESTO:
{testo}

Rispondi SOLO con JSON valido."""

    def __init__(self, strategy: str = None, db_session = None):
        """
        Inizializza il parser con una strategia di estrazione.

        Args:
            strategy: Strategia di estrazione (openai, ollama, regex, smart).
                     Se None, usa la configurazione da variabili d'ambiente.
                     'smart' usa il nuovo estrattore ibrido intelligente.
            db_session: Sessione database per validazione semantica (opzionale)
        """
        self.llm = LLMClient()
        self.attachment_extractor = get_attachment_extractor()
        self.db_session = db_session

        # Usa Settings se strategy non è fornito
        if strategy is None:
            from app.config import get_settings
            settings = get_settings()
            self.strategy = settings.INTERPELLO_PARSER_STRATEGY
        else:
            self.strategy = strategy

        # Usa SmartInterpelloExtractor per strategia 'smart'
        if self.strategy.lower() == 'smart':
            from app.config import get_settings
            settings = get_settings()
            openai_key = getattr(settings, 'OPENAI_API_KEY', None)
            openai_model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

            self.extractor = SmartInterpelloExtractor(
                openai_api_key=openai_key,
                openai_model=openai_model,
                db_session=db_session  # Passa DB session per validazione semantica
            )
            logger.info(f"📋 InterpelloParser inizializzato con strategia SMART (Regex → Semantic validation → LLM validate → Ollama → OpenAI)")
        else:
            self.extractor = ExtractorFactory.create(self.strategy)
            logger.info(f"📋 InterpelloParser inizializzato con strategia: {self.strategy}")

    def extract_from_email(
        self,
        corpo: str,
        allegati_path: Optional[List[str]] = None,
        allegati_nomi: Optional[List[str]] = None,
        allegati_testo: Optional[dict] = None,
        strategy_override: str = None,
        oggetto: str = None
    ) -> Optional[Dict]:
        """
        Estrae informazioni interpello da email

        Args:
            corpo: Corpo email
            allegati_path: Path allegati
            allegati_nomi: Nomi allegati
            allegati_testo: Testo pre-estratto dai PDF
            strategy_override: Strategia da usare per questa specifica estrazione
            oggetto: Oggetto/subject dell'email (per estrarre date scadenza)

        Returns:
            Dict con informazioni estratte o None
        """
        # Estrai testo completo (corpo + allegati)
        testo_completo = self._extract_full_text(corpo, allegati_path, allegati_nomi, allegati_testo)

        # Aggiungi l'oggetto all'inizio del testo per l'analisi
        if oggetto:
            testo_completo = f"OGGETTO EMAIL: {oggetto}\n\n{testo_completo}"

        if not testo_completo or len(testo_completo.strip()) < 100:
            logger.warning("Testo interpello troppo breve per l'estrazione")
            return None

        # Scegli l'estrattore da usare
        extractor = self.extractor
        if strategy_override:
            logger.info(f"🔄 Override strategia: {self.strategy} → {strategy_override}")
            extractor = ExtractorFactory.create(strategy_override)

        # Usa la strategia di estrazione scelta
        try:
            logger.info(f"🚀 Avvio estrazione con strategia: {strategy_override or self.strategy}")
            extracted_data = extractor.extract(testo_completo)

            if extracted_data:
                # Salva anche il testo completo
                extracted_data['testo_completo'] = testo_completo

                # Aggiungi metadata sulla strategia usata
                if 'metadata_estrazione' not in extracted_data:
                    extracted_data['metadata_estrazione'] = {}
                extracted_data['metadata_estrazione']['strategy'] = strategy_override or self.strategy

                # Valida e normalizza la classe di concorso
                extracted_data = self._validate_classe_concorso(extracted_data)

                # Converti stringhe ISO in datetime/date
                extracted_data = self._convert_dates(extracted_data)

                # Se la scadenza non è stata estratta, prova a estrarla dall'oggetto
                if not extracted_data.get('data_scadenza') and oggetto:
                    scadenza_da_oggetto = self._extract_date_from_subject(oggetto)
                    if scadenza_da_oggetto:
                        extracted_data['data_scadenza'] = scadenza_da_oggetto
                        if 'metadata_estrazione' not in extracted_data:
                            extracted_data['metadata_estrazione'] = {}
                        extracted_data['metadata_estrazione']['scadenza_da_oggetto'] = True
                        logger.info(f"📅 Scadenza {scadenza_da_oggetto.strftime('%d/%m/%Y')} estratta dall'oggetto email")

                logger.info(f"✅ Estrazione interpello completata: {extracted_data.get('classe_concorso', 'N/A')}")
                return extracted_data
            else:
                logger.warning("⚠️ Estrattore non ha restituito dati validi")
                return None

        except Exception as e:
            logger.error(f"❌ Errore durante estrazione interpello: {e}")
            return None

    def _extract_date_from_subject(self, oggetto: str) -> Optional[datetime]:
        """
        Estrae data di scadenza dall'oggetto dell'email.

        Patterns supportati:
        - "fino al 05/12/2025"
        - "scadenza 05/12/2025"
        - "entro il 05-12-2025"
        - "termine 5 dicembre 2025"

        Args:
            oggetto: Oggetto/subject dell'email

        Returns:
            datetime della scadenza o None
        """
        if not oggetto:
            return None

        # Pattern per date in formato gg/mm/aaaa o gg-mm-aaaa
        date_patterns = [
            # "fino al 05/12/2025" o "fino al 05-12-2025"
            r'fino\s+al?\s*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
            # "scadenza 05/12/2025"
            r'scadenza\s*[:\s]*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
            # "entro il 05/12/2025"
            r'entro\s+il?\s*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
            # "termine 05/12/2025"
            r'termine\s*[:\s]*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
            # Generica data nel formato gg/mm/aaaa
            r'(\d{1,2})[/\-](\d{1,2})[/\-](202[4-9])',
        ]

        oggetto_lower = oggetto.lower()

        for pattern in date_patterns:
            match = re.search(pattern, oggetto_lower)
            if match:
                try:
                    giorno, mese, anno = match.groups()
                    data = datetime(int(anno), int(mese), int(giorno))
                    logger.info(f"📅 Scadenza estratta dall'oggetto: {data.strftime('%d/%m/%Y')}")
                    return data
                except (ValueError, TypeError) as e:
                    logger.warning(f"Data non valida nell'oggetto: {e}")
                    continue

        # Pattern per date testuali (es. "5 dicembre 2025")
        mesi = {
            'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
            'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
            'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
        }

        text_pattern = r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(202[4-9])'
        match = re.search(text_pattern, oggetto_lower)
        if match:
            try:
                giorno, mese_nome, anno = match.groups()
                data = datetime(int(anno), mesi[mese_nome], int(giorno))
                logger.info(f"📅 Scadenza testuale estratta dall'oggetto: {data.strftime('%d/%m/%Y')}")
                return data
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Data testuale non valida nell'oggetto: {e}")

        return None

    def _extract_content_from_url(self, url: str) -> Optional[str]:
        """
        Estrae il contenuto testuale da un URL (pagina web con interpello).

        Args:
            url: URL della pagina da cui estrarre il contenuto

        Returns:
            Testo estratto dalla pagina o None in caso di errore
        """
        try:
            # Headers per simulare un browser normale
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Rimuovi elementi non utili
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()

            # Cerca il contenuto principale
            content = None

            # Pattern comuni per contenitori di contenuto
            content_selectors = [
                'article', '.entry-content', '.post-content', '.content',
                '#content', 'main', '.main-content', '.single-content'
            ]

            for selector in content_selectors:
                found = soup.select_one(selector)
                if found:
                    content = found
                    break

            if not content:
                content = soup.body if soup.body else soup

            # Estrai testo pulito
            text = content.get_text(separator='\n', strip=True)

            # Pulisci spazi multipli e righe vuote
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)

            if len(text) > 100:
                logger.info(f"🌐 Estratti {len(text)} caratteri da URL: {url[:50]}...")
                return text
            else:
                logger.warning(f"⚠️ Contenuto troppo breve da URL: {url[:50]}...")
                return None

        except requests.Timeout:
            logger.warning(f"⏱️ Timeout raggiunto per URL: {url[:50]}...")
            return None
        except requests.RequestException as e:
            logger.warning(f"⚠️ Errore HTTP fetching URL {url[:50]}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Errore estrazione contenuto da URL: {e}")
            return None

    def _extract_urls_from_text(self, text: str) -> List[str]:
        """
        Estrae URL rilevanti dal testo dell'email.

        Args:
            text: Testo in cui cercare URL

        Returns:
            Lista di URL trovati (filtrati per escludere quelli non utili)
        """
        if not text:
            return []

        # Pattern per URL http/https
        url_pattern = r'https?://[^\s<>\[\]"\']+[^\s<>\[\]"\',.]'
        urls = re.findall(url_pattern, text)

        # Pulisci URL
        cleaned_urls = []
        for url in urls:
            # Rimuovi caratteri trailing non validi
            url = re.sub(r'[>)\]]+$', '', url)

            # Escludi URL non utili
            exclude_patterns = [
                'mailto:',
                '.gif', '.jpg', '.jpeg', '.png', '.ico', '.svg',
                'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
                'unsubscribe', 'privacy', 'cookie',
            ]

            if not any(pattern in url.lower() for pattern in exclude_patterns):
                # Includi solo URL che potrebbero contenere interpelli
                include_patterns = [
                    'usp', 'usr', 'istruzione', 'interpello',
                    'supplenz', 'scuola', 'docent', 'news'
                ]
                if any(pattern in url.lower() for pattern in include_patterns):
                    cleaned_urls.append(url)

        # Rimuovi duplicati mantenendo ordine
        seen = set()
        unique_urls = []
        for url in cleaned_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls[:3]  # Limita a 3 URL per evitare troppi fetch

    def _extract_full_text(
        self,
        corpo: str,
        allegati_path: Optional[List[str]],
        allegati_nomi: Optional[List[str]],
        allegati_testo: Optional[dict] = None
    ) -> str:
        """Estrae testo completo da corpo + allegati + contenuti URL"""
        parts = [corpo] if corpo else []

        # Usa testo pre-estratto dai PDF se disponibile
        if allegati_testo:
            for filename, testo in allegati_testo.items():
                if testo:
                    parts.append(f"\n\n=== ALLEGATO: {filename} ===\n{testo}")
            logger.info(f"📎 Usato testo pre-estratto da {len(allegati_testo)} PDF per parsing interpello")

        # Estrai testo da allegati non-PDF (es. DOCX) se presenti
        if allegati_path and allegati_nomi:
            for path, nome in zip(allegati_path, allegati_nomi):
                if nome.lower().endswith('.docx'):
                    try:
                        testo_allegato = self.attachment_extractor.extract_text(path)
                        if testo_allegato:
                            parts.append(f"\n\n=== ALLEGATO: {nome} ===\n{testo_allegato}")
                    except Exception as e:
                        logger.warning(f"Errore estrazione testo da {nome}: {e}")

        # NUOVO: Estrai contenuto da URL presenti nel corpo email
        if corpo:
            urls = self._extract_urls_from_text(corpo)
            for url in urls:
                logger.info(f"🔗 Tentativo estrazione contenuto da: {url[:60]}...")
                url_content = self._extract_content_from_url(url)
                if url_content:
                    parts.append(f"\n\n=== CONTENUTO URL: {url[:60]}... ===\n{url_content}")

        return "\n".join(parts)

    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        """Parse risposta LLM cercando JSON valido"""
        try:
            # Cerca blocco JSON nella risposta
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)

            # Prova a parsare direttamente
            return json.loads(response)

        except json.JSONDecodeError as e:
            logger.error(f"Errore parsing JSON dalla risposta LLM: {e}\nRisposta: {response[:500]}")
            return None

    def _validate_classe_concorso(self, data: Dict) -> Dict:
        """
        Valida e normalizza la classe di concorso estratta.
        Aggiunge metadati di validazione.
        """
        classe_raw = data.get('classe_concorso')

        if not classe_raw:
            # Nessuna classe estratta
            if 'metadata_estrazione' not in data:
                data['metadata_estrazione'] = {}
            data['metadata_estrazione']['classe_validazione'] = {
                'raw': None,
                'normalizzata': None,
                'valida': False,
                'motivo': 'non_estratta'
            }
            logger.warning("⚠️ Classe di concorso non estratta dall'LLM")
            return data

        # Normalizza la classe
        classe_normalizzata = normalizza_classe_concorso(classe_raw)

        if not classe_normalizzata:
            # Classe non valida/riconosciuta
            if 'metadata_estrazione' not in data:
                data['metadata_estrazione'] = {}
            data['metadata_estrazione']['classe_validazione'] = {
                'raw': classe_raw,
                'normalizzata': None,
                'valida': False,
                'motivo': 'non_riconosciuta'
            }
            logger.warning(f"⚠️ Classe di concorso '{classe_raw}' non riconosciuta nel database ufficiale")
            # Mantieni comunque il valore raw
            return data

        # Classe valida - aggiorna con formato normalizzato
        info_classe = get_info_classe(classe_normalizzata)
        data['classe_concorso'] = classe_normalizzata

        if 'metadata_estrazione' not in data:
            data['metadata_estrazione'] = {}

        data['metadata_estrazione']['classe_validazione'] = {
            'raw': classe_raw,
            'normalizzata': classe_normalizzata,
            'valida': True,
            'info': info_classe
        }

        if classe_raw != classe_normalizzata:
            logger.info(f"✅ Classe normalizzata: '{classe_raw}' → '{classe_normalizzata}' ({info_classe['denominazione']})")
        else:
            logger.info(f"✅ Classe valida: '{classe_normalizzata}' ({info_classe['denominazione']})")

        return data

    def _convert_dates(self, data: Dict) -> Dict:
        """Converte stringhe ISO in oggetti datetime/date"""
        date_fields = {
            'data_scadenza': 'datetime',
            'data_inizio_servizio': 'date',
            'data_fine_contratto': 'date',
            'data_pubblicazione': 'datetime'
        }

        for field, field_type in date_fields.items():
            if field in data and isinstance(data[field], str):
                try:
                    if field_type == 'datetime':
                        # Supporta sia con che senza timezone
                        if 'T' in data[field]:
                            data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                        else:
                            data[field] = datetime.fromisoformat(data[field])
                    else:  # date
                        data[field] = date.fromisoformat(data[field].split('T')[0])
                except Exception as e:
                    logger.warning(f"Errore conversione data {field}: {e}")
                    # Rimuovi il campo se non può essere convertito
                    del data[field]

        return data

    def is_interpello(self, oggetto: str, corpo: str, categoria: str = None) -> bool:
        """
        Verifica se un'email è un interpello

        Args:
            oggetto: Oggetto email
            corpo: Corpo email
            categoria: Categoria email (se già categorizzata)

        Returns:
            True se è un interpello
        """
        # Se ha sottocategoria "Interpello", è sicuramente un interpello
        if categoria and 'interpello' in categoria.lower():
            return True

        # Cerca parole chiave nell'oggetto
        keywords = [
            'interpello',
            'supplenza',
            'classe di concorso',
            'mad',
            'graduatorie esaurite',
            'reclutamento personale docente'
        ]

        testo = (oggetto + ' ' + corpo).lower()

        # Deve contenere almeno 2 keyword
        matches = sum(1 for kw in keywords if kw in testo)

        return matches >= 2
