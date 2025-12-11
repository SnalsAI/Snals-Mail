"""
Servizio NLP per migliorare la categorizzazione email.

Funzionalità:
1. NER per validazione mittente - riconosce scuole/enti nel corpo email
2. Keyword expansion con embeddings - similarity semantica per varianti
3. Confidence boost - aumenta confidence quando NLP conferma categoria

Integra spaCy + sentence-transformers per categorizzazione intelligente.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Lazy loading per modelli pesanti
_sentence_model = None
_nlp_extractor = None


def get_sentence_model():
    """Carica sentence-transformers per embeddings semantici (lazy loading)."""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("🔄 Caricamento sentence-transformers italiano...")
            # Modello multilingue ottimizzato per italiano
            _sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("✅ Sentence-transformers caricato")
        except Exception as e:
            logger.warning(f"⚠️ sentence-transformers non disponibile: {e}")
            _sentence_model = None
    return _sentence_model


def get_nlp_extractor():
    """Ottiene l'estrattore NLP esistente (lazy loading)."""
    global _nlp_extractor
    if _nlp_extractor is None:
        try:
            from app.services.nlp_service import NLPExtractor
            _nlp_extractor = NLPExtractor()
            logger.info("✅ NLPExtractor inizializzato per categorizzazione")
        except Exception as e:
            logger.warning(f"⚠️ NLPExtractor non disponibile: {e}")
            _nlp_extractor = None
    return _nlp_extractor


class NLPCategorizationEnhancer:
    """
    Migliora la categorizzazione email usando NLP avanzato.

    Combina:
    - NER (spaCy + BERT) per identificare enti/scuole nel testo
    - Embeddings semantici per keyword expansion
    - Logica di confidence boost basata su conferme NLP
    """

    # Categorie e keyword semantiche per matching
    CATEGORY_KEYWORDS = {
        'comunicazione_scuola': {
            'strong': [
                'convocazione', 'riunione RSU', 'assemblea sindacale',
                'contrattazione integrativa', 'tavolo contrattazione',
                'OO.SS.', 'organizzazioni sindacali', 'incontro sindacale',
                'collegio docenti', 'consiglio istituto'
            ],
            'weak': [
                'riunione', 'incontro', 'comunicazione', 'circolare',
                'avviso', 'nota', 'disposizione', 'decreto'
            ]
        },
        'comunicazione_ust_usr': {
            'strong': [
                'interpello', 'graduatoria', 'supplenze', 'GPS',
                'convocazioni supplenze', 'utilizzazioni',
                'assegnazioni provvisorie', 'ambito territoriale',
                'ufficio scolastico', 'protocollo AOOUSPTA'
            ],
            'weak': [
                'decreto', 'provvedimento', 'circolare', 'nota',
                'disponibilità', 'organico', 'personale docente'
            ]
        },
        'richiesta_tesseramento': {
            'strong': [
                'iscrizione sindacato', 'tesseramento', 'aderire SNALS',
                'modulo iscrizione', 'quota sindacale', 'tessera SNALS',
                'voglio iscrivermi', 'vorrei aderire'
            ],
            'weak': [
                'informazioni iscrizione', 'costo tessera', 'come iscriversi'
            ]
        },
        'richiesta_appuntamento': {
            'strong': [
                'appuntamento', 'fissare incontro', 'venire in sede',
                'parlare con voi', 'incontrare', 'ricevimento',
                'prendere appuntamento', 'disponibilità orario'
            ],
            'weak': [
                'quando siete aperti', 'orari sede', 'dove vi trovo'
            ]
        },
        'revoca_sindacale': {
            'strong': [
                'revoca delega', 'revoca iscrizione', 'disdetta sindacale',
                'recesso sindacato', 'rinuncia iscrizione', 'revoca trattenuta'
            ],
            'weak': [
                'revoca', 'disdetta', 'recesso', 'rinuncia'
            ]
        },
        'spam': {
            'strong': [
                'offerta speciale', 'sconto esclusivo', 'promozione',
                'prestito', 'finanziamento', 'investimento sicuro',
                'guadagna da casa', 'lavoro online'
            ],
            'weak': [
                'gratis', 'vincita', 'premio', 'clicca qui'
            ]
        }
    }

    # Pattern per identificare enti/scuole nel testo
    SCHOOL_PATTERNS = [
        # Nomi istituti comuni
        r'\b(?:I\.?C\.?|I\.?I\.?S\.?S?\.?|I\.?T\.?I\.?S?\.?|I\.?P\.?S\.?S?\.?|Liceo|Istituto)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
        # Scuola primaria/secondaria
        r'\bScuola\s+(?:Primaria|Secondaria|Media|Elementare)\s+[A-Z][a-z]+',
        # Plesso
        r'\bplesso\s+[A-Z][a-z]+',
    ]

    UST_USR_PATTERNS = [
        r'\bUSP\s+(?:di\s+)?[A-Z][a-z]+',
        r'\bUSR\s+(?:per\s+la\s+)?[A-Z][a-z]+',
        r'\bUfficio\s+Scolastico\s+(?:Provinciale|Regionale)',
        r'\bAmbito\s+Territoriale',
        r'\bAOOUSPTA\b',
        r'\bAOOUSR[A-Z]*\b',
    ]

    def __init__(self):
        """Inizializza l'enhancer."""
        self._sentence_model = None
        self._nlp_extractor = None
        self._embeddings_cache = {}
        self._initialized = False

    def _ensure_initialized(self):
        """Inizializza i modelli al primo utilizzo."""
        if not self._initialized:
            self._sentence_model = get_sentence_model()
            self._nlp_extractor = get_nlp_extractor()
            self._precompute_keyword_embeddings()
            self._initialized = True

    def _precompute_keyword_embeddings(self):
        """Pre-calcola embeddings per le keyword di categoria."""
        if self._sentence_model is None:
            return

        try:
            for categoria, keywords_dict in self.CATEGORY_KEYWORDS.items():
                all_keywords = keywords_dict.get('strong', []) + keywords_dict.get('weak', [])
                if all_keywords:
                    embeddings = self._sentence_model.encode(all_keywords)
                    self._embeddings_cache[categoria] = {
                        'keywords': all_keywords,
                        'embeddings': embeddings,
                        'strong_count': len(keywords_dict.get('strong', []))
                    }
            logger.info(f"✅ Pre-calcolati embeddings per {len(self._embeddings_cache)} categorie")
        except Exception as e:
            logger.warning(f"⚠️ Errore pre-calcolo embeddings: {e}")

    def identify_entities_in_body(self, corpo: str) -> Dict[str, Any]:
        """
        Identifica scuole, enti e organizzazioni nel corpo email usando NER.

        Args:
            corpo: Corpo dell'email

        Returns:
            Dict con entità trovate:
            - schools: Lista di scuole identificate
            - ust_usr: Lista di riferimenti a UST/USR
            - organizations: Altre organizzazioni
            - has_institutional_reference: True se ci sono riferimenti istituzionali
        """
        self._ensure_initialized()

        result = {
            'schools': [],
            'ust_usr': [],
            'organizations': [],
            'meccanografici': [],
            'has_institutional_reference': False,
            'sender_type_hint': None  # Suggerimento sul tipo di mittente
        }

        if not corpo or len(corpo) < 20:
            return result

        # 1. Usa NLP Extractor per NER
        if self._nlp_extractor:
            try:
                entities = self._nlp_extractor.extract_entities(corpo[:3000])

                # Organizzazioni (potenziali scuole)
                for org in entities.get('organizations', []):
                    org_text = org.get('text', '')
                    # Verifica se è una scuola
                    if self._is_school_name(org_text):
                        result['schools'].append(org_text)
                    elif self._is_ust_usr(org_text):
                        result['ust_usr'].append(org_text)
                    else:
                        result['organizations'].append(org_text)

                # Istituti (da EntityRuler)
                for istituto in entities.get('istituti', []):
                    result['schools'].append(istituto.get('text', ''))

                # Codici meccanografici
                for mecca in entities.get('meccanografici', []):
                    result['meccanografici'].append(mecca.get('text', ''))

            except Exception as e:
                logger.warning(f"Errore NER: {e}")

        # 2. Pattern matching aggiuntivo
        # Scuole via pattern
        for pattern in self.SCHOOL_PATTERNS:
            matches = re.findall(pattern, corpo, re.IGNORECASE)
            for match in matches:
                if match not in result['schools']:
                    result['schools'].append(match)

        # UST/USR via pattern
        for pattern in self.UST_USR_PATTERNS:
            matches = re.findall(pattern, corpo, re.IGNORECASE)
            for match in matches:
                if match not in result['ust_usr']:
                    result['ust_usr'].append(match)

        # 3. Determina se ci sono riferimenti istituzionali
        result['has_institutional_reference'] = bool(
            result['schools'] or
            result['ust_usr'] or
            result['meccanografici']
        )

        # 4. Suggerisci tipo mittente basato su entità trovate
        if result['ust_usr']:
            result['sender_type_hint'] = 'USP_UST'
        elif result['schools'] or result['meccanografici']:
            result['sender_type_hint'] = 'SCUOLA'

        logger.debug(f"🔍 NER body: {len(result['schools'])} scuole, "
                    f"{len(result['ust_usr'])} UST/USR, "
                    f"{len(result['meccanografici'])} meccanografici")

        return result

    def _is_school_name(self, text: str) -> bool:
        """Verifica se il testo sembra essere un nome di scuola."""
        text_lower = text.lower()
        school_indicators = [
            'istituto', 'liceo', 'scuola', 'i.c.', 'i.i.s.', 'i.t.i.',
            'i.p.s.', 'comprensivo', 'secondaria', 'primaria', 'plesso'
        ]
        return any(ind in text_lower for ind in school_indicators)

    def _is_ust_usr(self, text: str) -> bool:
        """Verifica se il testo si riferisce a UST/USR."""
        text_lower = text.lower()
        ust_indicators = [
            'usp', 'usr', 'ufficio scolastico', 'ambito territoriale',
            'aoouspta', 'aoousr', 'ministero'
        ]
        return any(ind in text_lower for ind in ust_indicators)

    def compute_semantic_similarity(
        self,
        text: str,
        target_category: str = None
    ) -> Dict[str, float]:
        """
        Calcola similarità semantica tra testo e keyword delle categorie.

        Args:
            text: Testo da analizzare (oggetto + corpo)
            target_category: Se specificato, calcola solo per quella categoria

        Returns:
            Dict categoria -> score di similarità (0-1)
        """
        self._ensure_initialized()

        if not self._sentence_model or not text:
            return {}

        try:
            import numpy as np

            # Encode il testo
            text_embedding = self._sentence_model.encode([text[:1000]])[0]

            similarities = {}
            categories_to_check = [target_category] if target_category else self._embeddings_cache.keys()

            for categoria in categories_to_check:
                if categoria not in self._embeddings_cache:
                    continue

                cache = self._embeddings_cache[categoria]
                keyword_embeddings = cache['embeddings']
                strong_count = cache['strong_count']

                # Calcola cosine similarity con ogni keyword
                from numpy.linalg import norm
                scores = []
                for i, kw_emb in enumerate(keyword_embeddings):
                    cos_sim = np.dot(text_embedding, kw_emb) / (norm(text_embedding) * norm(kw_emb) + 1e-8)
                    # Peso maggiore per keyword strong
                    weight = 1.5 if i < strong_count else 1.0
                    scores.append(cos_sim * weight)

                # Score finale: media pesata dei top-3 match
                top_scores = sorted(scores, reverse=True)[:3]
                if top_scores:
                    similarities[categoria] = float(np.mean(top_scores))

            return similarities

        except Exception as e:
            logger.warning(f"Errore calcolo similarità: {e}")
            return {}

    def get_category_confidence_boost(
        self,
        categoria: str,
        mittente: str,
        oggetto: str,
        corpo: str,
        current_confidence: float
    ) -> Tuple[float, str]:
        """
        Calcola boost di confidence basato su conferme NLP.

        Args:
            categoria: Categoria proposta
            mittente: Email mittente
            oggetto: Oggetto email
            corpo: Corpo email
            current_confidence: Confidence attuale

        Returns:
            Tuple (new_confidence, motivazione)
        """
        self._ensure_initialized()

        boost = 0.0
        motivazioni = []

        # 1. NER: verifica riferimenti istituzionali nel corpo
        body_entities = self.identify_entities_in_body(corpo[:2000] if corpo else "")

        if body_entities['has_institutional_reference']:
            # Se la categoria corrisponde al tipo di entità trovate
            if categoria == 'comunicazione_scuola' and (body_entities['schools'] or body_entities['meccanografici']):
                boost += 0.05
                motivazioni.append(f"NER conferma scuola: {body_entities['schools'][:2]}")
            elif categoria == 'comunicazione_ust_usr' and body_entities['ust_usr']:
                boost += 0.05
                motivazioni.append(f"NER conferma UST/USR: {body_entities['ust_usr'][:2]}")

        # 2. Similarità semantica
        full_text = f"{oggetto or ''} {corpo[:500] if corpo else ''}"
        similarities = self.compute_semantic_similarity(full_text, categoria)

        if categoria in similarities:
            sim_score = similarities[categoria]
            if sim_score > 0.7:
                boost += 0.08
                motivazioni.append(f"Alta similarità semantica: {sim_score:.2f}")
            elif sim_score > 0.5:
                boost += 0.04
                motivazioni.append(f"Media similarità semantica: {sim_score:.2f}")

        # 3. Cross-validation: se NER suggerisce stesso tipo mittente
        if body_entities['sender_type_hint']:
            category_sender_map = {
                'comunicazione_scuola': 'SCUOLA',
                'comunicazione_ust_usr': 'USP_UST',
            }
            expected_sender = category_sender_map.get(categoria)
            if expected_sender == body_entities['sender_type_hint']:
                boost += 0.03
                motivazioni.append("NER conferma tipo mittente")

        # Calcola nuova confidence (max 0.98)
        new_confidence = min(current_confidence + boost, 0.98)

        motivazione = " | ".join(motivazioni) if motivazioni else "Nessun boost NLP"

        if boost > 0:
            logger.info(f"📈 NLP boost +{boost:.2f} per {categoria}: {motivazione}")

        return new_confidence, motivazione

    def suggest_category_from_content(
        self,
        oggetto: str,
        corpo: str,
        threshold: float = 0.6
    ) -> Optional[Tuple[str, float, str]]:
        """
        Suggerisce una categoria basandosi solo sul contenuto (senza mittente).

        Utile quando il mittente è ambiguo o sconosciuto.

        Args:
            oggetto: Oggetto email
            corpo: Corpo email
            threshold: Soglia minima di similarità

        Returns:
            Tuple (categoria, confidence, motivazione) o None se sotto soglia
        """
        self._ensure_initialized()

        full_text = f"{oggetto or ''} {corpo[:1000] if corpo else ''}"

        if len(full_text.strip()) < 20:
            return None

        # Calcola similarità con tutte le categorie
        similarities = self.compute_semantic_similarity(full_text)

        if not similarities:
            return None

        # Trova categoria con score più alto
        best_category = max(similarities.items(), key=lambda x: x[1])
        categoria, score = best_category

        if score >= threshold:
            # Boost extra se NER conferma
            body_entities = self.identify_entities_in_body(corpo[:1500] if corpo else "")

            if body_entities['has_institutional_reference']:
                if categoria in ['comunicazione_scuola', 'comunicazione_ust_usr']:
                    score = min(score + 0.05, 0.95)

            confidence = min(score * 0.9, 0.90)  # Non superare 0.90 senza mittente
            motivazione = f"Similarità semantica {score:.2f}"

            if body_entities['schools']:
                motivazione += f" + NER scuole: {body_entities['schools'][:1]}"

            logger.info(f"🎯 NLP suggerisce: {categoria} (conf: {confidence:.2f})")
            return categoria, confidence, motivazione

        return None

    def validate_category_with_nlp(
        self,
        categoria: str,
        oggetto: str,
        corpo: str
    ) -> Tuple[bool, float, str]:
        """
        Valida se una categoria ha senso per il contenuto usando NLP.

        Args:
            categoria: Categoria da validare
            oggetto: Oggetto email
            corpo: Corpo email

        Returns:
            Tuple (is_valid, confidence, motivazione)
        """
        self._ensure_initialized()

        full_text = f"{oggetto or ''} {corpo[:1000] if corpo else ''}"

        # 1. Calcola similarità semantica per la categoria
        similarities = self.compute_semantic_similarity(full_text, categoria)

        if categoria in similarities:
            sim_score = similarities[categoria]

            # 2. Verifica se altre categorie hanno score molto più alto
            all_similarities = self.compute_semantic_similarity(full_text)
            best_other = max(
                (s for c, s in all_similarities.items() if c != categoria),
                default=0
            )

            # Valido se:
            # - Similarità >= 0.4 E
            # - Non c'è un'altra categoria con score molto più alto
            if sim_score >= 0.4 and (sim_score >= best_other - 0.15):
                return True, sim_score, f"NLP conferma ({sim_score:.2f})"
            elif sim_score < 0.3:
                return False, sim_score, f"Bassa similarità NLP ({sim_score:.2f})"
            elif best_other > sim_score + 0.2:
                # Altra categoria sembra più appropriata
                best_cat = max(all_similarities.items(), key=lambda x: x[1])[0]
                return False, sim_score, f"NLP suggerisce {best_cat} ({best_other:.2f})"

        # Fallback: valido con confidence bassa
        return True, 0.5, "NLP non determinante"


# Singleton
_nlp_categorization_enhancer = None


def get_nlp_categorization_enhancer() -> NLPCategorizationEnhancer:
    """Ottiene l'istanza singleton dell'enhancer NLP per categorizzazione."""
    global _nlp_categorization_enhancer
    if _nlp_categorization_enhancer is None:
        _nlp_categorization_enhancer = NLPCategorizationEnhancer()
    return _nlp_categorization_enhancer
