"""
Servizio categorizzazione email con approccio ibrido:
1. Rule-based classifier (regex deterministico)
2. NLP enhancement (NER + embeddings semantici)
3. LLM fallback per casi edge
"""

from typing import Tuple, Optional, List, Dict
import logging

from app.integrations.llm_client import LLMClient
from app.models.email import EmailCategory
from app.services.rule_based_classifier import RuleBasedClassifier
from app.services.attachment_extractor import get_attachment_extractor

logger = logging.getLogger(__name__)

# Lazy loading per NLP enhancer (evita import pesanti all'avvio)
_nlp_enhancer = None


def get_nlp_enhancer():
    """Carica NLP categorization enhancer (lazy loading)."""
    global _nlp_enhancer
    if _nlp_enhancer is None:
        try:
            from app.services.nlp_categorization_service import get_nlp_categorization_enhancer
            _nlp_enhancer = get_nlp_categorization_enhancer()
            logger.info("✅ NLP Categorization Enhancer caricato")
        except Exception as e:
            logger.warning(f"⚠️ NLP Enhancer non disponibile: {e}")
            _nlp_enhancer = None
    return _nlp_enhancer


class EmailCategorizer:
    """Categorizzatore email ibrido (rule-based + LLM)"""
    
    PROMPT_TEMPLATE = """Sei un esperto nella categorizzazione di email per il sindacato scuola SNALS di Taranto.

Analizza questa email seguendo l'ORDINE DI PRIORITÀ e categorizzala in UNA categoria.

🔴 PRIORITÀ 1: COMUNICAZIONE_SCUOLA
   IDENTIFICAZIONE SCUOLE (codici meccanografici):
   - Pattern: [4 LETTERE][6 CARATTERI ALFANUMERICI]@istruzione.it
   - Esempi: taic865007@, taic851009@, baic842004@, rmic8g500r@
   - Nome scuola nel mittente: "I.C. San G. Bosco", "Liceo Archita", "ITIS Pacinotti"

   SOTTOCATEGORIE:
   - "Convocazione": se contiene "convocazione", "RSU", "assemblea sindacale", "OO.SS.", "tavolo contrattazione"
   - "Contrattazione Integrativa": se contiene "contrattazione integrativa", "contratto integrativo"
   - "Comunicazione": altre comunicazioni dalla scuola

   → Se il mittente ha codice meccanografico @istruzione.it, è SCUOLA (non UST/USR!)

🟠 PRIORITÀ 2: COMUNICAZIONE_UST_USR
   IDENTIFICAZIONE DOMINI UST/USR (NON generici @istruzione.it!):
   - uspta@postacert.istruzione.it, uspta@pec.istruzione.it
   - usprpu@postacert.istruzione.it, usprpu@pec.istruzione.it
   - usp.ta@istruzione.it, usr.puglia@istruzione.it
   - aoouspta@, aoousr@
   - "USP di Taranto", "Ufficio Scolastico", "Ambito Territoriale"
   CONTENUTI TIPICI:
   - Protocolli ufficiali (es: "Protocollo nr: 21333 - AOOUSPTA")
   - Graduatorie, supplenze, interpelli, GPS
   - Comunicazioni su personale docente/ATA
   - Normativa ministeriale
   → Categorizza come comunicazione_ust_usr SOLO se mittente è veramente UST/USR

🔵 PRIORITÀ 4: COMUNICAZIONE_SNALS_CENTRALE
   INDICATORI:
   - Mittente: info@snals.it, comunicazioni@snalsconfsal.it
   - Oggetto: circolari nazionali, direttive centrali, comunicati SNALS
   → Comunicazioni ufficiali dalla sede centrale SNALS

🟢 PRIORITÀ 5: RICHIESTE DA UTENTI
   A) richiesta_tesseramento:
      - Parole chiave: "iscrivermi", "tesseramento", "adesione", "modulo iscrizione", "quota sindacale"
      - Mittente: email personale (gmail, libero, outlook, etc.)

   B) richiesta_appuntamento:
      - Parole chiave: "appuntamento", "incontrare", "venire in sede", "disponibilità", "orario ricevimento"
      - Mittente: email personale

   C) info_generiche:
      - Domande generiche su diritti, contratti, pensioni, permessi
      - Mittente: email personale da docenti/ATA
      - Richieste informazioni non specifiche

⚫ PRIORITÀ 6: SPAM (include pubblicità)
   INDICATORI SPAM/PUBBLICITA:
   - Domini commerciali: marketing@, noreply@, promo@, info@azienda.com
   - Domini sospetti finanziari: finsubitoonline.net, prestiti@, credito-facile@
   - Corsi di formazione commerciali, software gestionali, servizi per scuole
   - Oggetto con: "OFFERTA", "SCONTO", "PROMOZIONE", "NOVITÀ", emoji commerciali
   - Contenuto: materiale promozionale, cataloghi, offerte commerciali, truffe, phishing
   - Newsletter commerciali, webinar promozionali, "vinci gratis", "€€€!!!"
   → SPAM = email promozionale, commerciale, fraudolenta o non rilevante per SNALS
   → Esempi: corsi formazione a pagamento, piattaforme digitali, prestiti, truffe

⚪ PRIORITÀ 8: VARIE
   - Tutto ciò che non rientra nelle categorie precedenti
   - Newsletter generiche, notifiche tecniche, comunicazioni non classificabili

═══════════════════════════════════════════════════════════════════════════

ESEMPI PRATICI:

Esempio 1 - CONVOCAZIONE (priorità massima):
Mittente: taic851009@istruzione.it
Oggetto: Convocazione RSU - Contrattazione integrativa 20/11/2025 ore 15:00
→ comunicazione_scuola (parola chiave "Convocazione RSU" + riferimento data/ora)
Confidence: 0.95

Esempio 2 - UST/USR:
Mittente: uspta@postacert.istruzione.it
Oggetto: Protocollo nr: 21333 - AOOUSPTA - Nono turno supplenze
→ comunicazione_ust_usr (dominio UST + protocollo ufficiale)
Confidence: 0.95

Esempio 3 - SCUOLA (NON UST!):
Mittente: taic865007@istruzione.it
Oggetto: invito sottoscrizione Contratto Collettivo Integrativo di Istituto 2025/2028
→ comunicazione_scuola (codice meccanografico TAIC865007 = scuola, non UST)
Confidence: 0.90

Esempio 4 - SNALS CENTRALE:
Mittente: info@snals.it
Oggetto: Circolare nazionale n. 45/2025 - Aggiornamenti normativi
→ comunicazione_snals_centrale (dominio snals.it ufficiale)
Confidence: 0.95

Esempio 5 - SPAM (pubblicità/promozione):
Mittente: info@corsionline.it
Oggetto: 🎓 Nuovi corsi di formazione per docenti - Sconto 30%
→ spam (materiale promozionale commerciale)
Confidence: 0.90

Esempio 6 - SPAM (truffa):
Mittente: abbinata@finsubitoonline.net
Oggetto: 💰 Finanziamento aziendale facile e veloce con #FINSUBITO 💰
→ spam (dominio fraudolento + contenuto finanziario sospetto)
Confidence: 0.95

═══════════════════════════════════════════════════════════════════════════

ANALIZZA QUESTA EMAIL:
Mittente: {mittente}
Oggetto: {oggetto}
Corpo: {corpo}

PROCEDURA DI CATEGORIZZAZIONE:
1. Controlla PRIMA se è convocazione (RSU, assemblea sindacale, tavolo contrattazione)
2. Se non è convocazione, controlla se mittente è UST/USR (uspta@, usp.ta@, aoouspta@)
3. Se mittente ha @istruzione.it ma NON è UST, controlla se ha codice meccanografico [LETTERE+CIFRE] → è SCUOLA
4. Controlla se è info@snals.it → comunicazione_snals_centrale
5. Controlla se è pubblicità (domini commerciali, offerte, promozioni)
6. Controlla se è spam fraudolento (truffe, phishing, contenuti sospetti)
7. Controlla se è richiesta tesseramento/appuntamento/info da utente privato
8. Se non rientra in nulla → varie

ATTENZIONE:
- Codici meccanografici tipo "taic865007", "baic842004" indicano SCUOLE, non UST
- Solo domini specifici (uspta@, usp.ta@, aoouspta@) sono UST/USR
- Convocazioni RSU/OO.SS. hanno SEMPRE priorità massima
- Domini commerciali legittimi (corsi, software) → pubblicita
- Domini sospetti/fraudolenti (prestiti, finanza) → spam

Confidence: 0.9-1.0 = certezza assoluta, 0.7-0.89 = molto sicuro, 0.5-0.69 = incerto

Rispondi SOLO con JSON valido:
{{
  "categoria": "nome_categoria",
  "confidence": 0.85,
  "motivazione": "Spiegazione breve degli indicatori trovati"
}}
"""

    def __init__(self, use_rules=True, use_nlp=True):
        """
        Args:
            use_rules: Se True usa rule-based classifier prima del LLM (default: True)
            use_nlp: Se True usa NLP enhancement (NER + embeddings) (default: True)
        """
        self.llm_client = LLMClient()
        self.rule_classifier = RuleBasedClassifier() if use_rules else None
        self.use_rules = use_rules
        self.use_nlp = use_nlp
        self._nlp_enhancer = None  # Lazy loading

    def categorize(
        self,
        mittente: str,
        oggetto: str,
        corpo: str,
        attachment_paths: Optional[List[str]] = None,
        allegati_testo: Optional[dict] = None
    ) -> Tuple[EmailCategory, float, Optional[str], Optional[Dict]]:
        """
        Categorizza email con approccio ibrido:
        1. Se busta PEC, parsa allegato EML e usa i dati del messaggio interno
        2. Prova rule-based classifier (veloce, deterministico)
        3. Se confidence < 0.85 o categoria è VARIE, usa LLM come fallback

        Args:
            mittente: Email del mittente
            oggetto: Oggetto dell'email
            corpo: Corpo testo dell'email
            attachment_paths: Lista path degli allegati (opzionale)
            allegati_testo: Dict con testo estratto dai PDF: {filename: testo} (opzionale)

        Returns:
            Tuple (categoria, confidence, sottocategoria, proposta_info)
            - categoria: Categoria principale
            - confidence: Livello di confidenza
            - sottocategoria: Sottocategoria assegnata
            - proposta_info: Informazioni su proposta nuova sottocategoria (None se non c'è)
        """
        # RICEVUTE PEC: Riconosci subito le ricevute di accettazione/consegna
        oggetto_upper = oggetto.upper() if oggetto else ''
        if oggetto_upper.startswith('CONSEGNA:'):
            logger.info(f"📨 Rilevata ricevuta PEC (Consegna): {oggetto[:50]}")
            return EmailCategory.RICEVUTA_PEC, 1.0, 'Consegna', None
        if oggetto_upper.startswith('ACCETTAZIONE:'):
            logger.info(f"📨 Rilevata ricevuta PEC (Accettazione): {oggetto[:50]}")
            return EmailCategory.RICEVUTA_PEC, 1.0, 'Accettazione', None

        # FATTURE ELETTRONICHE: Riconosci fatture da SDI (Sistema di Interscambio)
        mittente_lower = mittente.lower() if mittente else ''
        is_fattura = (
            'fatturapa.it' in mittente_lower or
            'sdi' in mittente_lower and '@pec' in mittente_lower or
            'sistema di interscambio' in mittente_lower or
            ('invio file' in oggetto_upper and 'posta certificata' in oggetto_upper)
        )
        if is_fattura:
            logger.info(f"🧾 Rilevata fattura elettronica (SDI): {oggetto[:50]}")
            return EmailCategory.FATTURA, 1.0, 'Fattura Elettronica', None

        # PARSING BUSTE PEC: Se è una busta PEC, estrai il messaggio reale dall'allegato EML
        # Riconosce PEC anche se arrivate su account normale
        is_pec_envelope = (
            'posta-certificata' in mittente.lower() or
            'legalmail' in mittente.lower() or
            ('POSTA CERTIFICATA' in oggetto_upper)
        )

        if attachment_paths and is_pec_envelope:
            # Cerca allegati .eml
            import os
            eml_files = [path for path in attachment_paths if path.lower().endswith('.eml')]

            if eml_files:
                logger.info(f"📧 Rilevata busta PEC con {len(eml_files)} allegati EML - parsing messaggio interno...")
                try:
                    extractor = get_attachment_extractor()
                    # Parsa il primo EML trovato
                    eml_data = extractor.parse_eml_complete(eml_files[0])

                    if eml_data:
                        # Sostituisci mittente, oggetto e corpo con quelli del messaggio interno
                        mittente = eml_data['from']
                        oggetto = eml_data['subject']
                        corpo = eml_data['body']
                        logger.info(f"✅ Dati EML estratti - Mittente reale: {mittente[:50]}, Oggetto: {oggetto[:50]}")
                    else:
                        logger.warning(f"⚠️ Parsing EML fallito, uso dati busta")
                except Exception as e:
                    logger.error(f"❌ Errore parsing busta PEC: {e}")
                    # Continua con i dati della busta se il parsing fallisce

        # Estrai testo dagli allegati
        attachments_text = ""

        # Usa testo pre-estratto dai PDF se disponibile
        if allegati_testo:
            attachments_text = "\n\n".join(allegati_testo.values())
            if attachments_text:
                logger.info(f"📎 Usato testo pre-estratto da {len(allegati_testo)} PDF ({len(attachments_text)} caratteri)")

        # Fallback: estrai da file allegati rimanenti (non-PDF)
        if attachment_paths:
            try:
                extractor = get_attachment_extractor()
                # Filtra file tecnici PEC e EML già parsati
                paths_to_extract = attachment_paths
                if is_pec_envelope:
                    # Non estrarre file tecnici: EML (già usati per parsing), .p7s (firma), .xml (daticert)
                    paths_to_extract = [
                        p for p in attachment_paths
                        if not any(p.lower().endswith(ext) for ext in ['.eml', '.p7s', '.xml'])
                    ]

                if paths_to_extract:
                    additional_text = extractor.extract_from_attachments(paths_to_extract)
                    if additional_text:
                        attachments_text = f"{attachments_text}\n\n{additional_text}" if attachments_text else additional_text
                        logger.info(f"📎 Estratto testo aggiuntivo da {len(paths_to_extract)} allegati ({len(additional_text)} caratteri)")
            except Exception as e:
                logger.warning(f"Errore estrazione testo allegati: {e}")

        # Combina corpo email + testo allegati
        full_text = corpo if corpo else ""
        if attachments_text:
            full_text = f"{full_text}\n\n{attachments_text}"

        # ========================================================
        # STEP 1: IDENTIFICA TIPO MITTENTE (prima di tutto!)
        # ========================================================
        sender_type = "ALTRO"
        if self.rule_classifier:
            sender_type = self.rule_classifier.identify_sender_type(mittente, oggetto)

        logger.info(f"📧 Mittente identificato come: {sender_type} ({mittente[:50]}...)")

        # ========================================================
        # STEP 1.5: NLP - VALIDA/MIGLIORA IDENTIFICAZIONE MITTENTE
        # Se mittente è ALTRO, usa NER per cercare riferimenti a scuole/enti nel corpo
        # ========================================================
        nlp_sender_hint = None
        nlp_entities = {}
        if self.use_nlp and sender_type == "ALTRO":
            try:
                nlp_enhancer = get_nlp_enhancer()
                if nlp_enhancer:
                    nlp_entities = nlp_enhancer.identify_entities_in_body(full_text[:2000] if full_text else "")
                    nlp_sender_hint = nlp_entities.get('sender_type_hint')

                    if nlp_sender_hint:
                        logger.info(f"🧠 NLP suggerisce mittente tipo: {nlp_sender_hint} "
                                   f"(scuole: {nlp_entities.get('schools', [])[:2]}, "
                                   f"UST: {nlp_entities.get('ust_usr', [])[:2]})")
            except Exception as e:
                logger.warning(f"⚠️ Errore NLP sender detection: {e}")

        # ========================================================
        # STEP 2: CONTROLLA SPAM (prima di qualsiasi categorizzazione)
        # ========================================================
        if self.rule_classifier and self.rule_classifier._is_spam(mittente, oggetto, full_text[:1000] if full_text else ""):
            logger.info(f"🚫 Email identificata come SPAM")
            return EmailCategory.SPAM, 0.95, None, None

        # ========================================================
        # STEP 3: RULE-BASED CLASSIFICATION
        # ========================================================
        rule_categoria = None
        rule_confidence = 0.0
        rule_sottocategoria = None
        rule_proposta_info = None

        if self.use_rules and self.rule_classifier:
            try:
                categoria_str, confidence, motivazione, sottocategoria, proposta_info = self.rule_classifier.classify_email(
                    mittente=mittente,
                    oggetto=oggetto,
                    corpo=(full_text[:2000] if full_text else "")
                )

                logger.info(f"Rule-based: {categoria_str} (conf: {confidence:.2f}) - {motivazione} | Sottocat: {sottocategoria}")

                if proposta_info:
                    logger.warning(f"⚠️ Proposta nuova sottocategoria: {proposta_info}")

                try:
                    rule_categoria = EmailCategory[categoria_str.upper()]
                    rule_confidence = confidence
                    rule_sottocategoria = sottocategoria
                    rule_proposta_info = proposta_info
                except KeyError:
                    logger.warning(f"Categoria sconosciuta da rule-based: {categoria_str}")

            except Exception as e:
                logger.error(f"Errore rule-based classifier: {e}", exc_info=True)

        # ========================================================
        # STEP 4: VALIDAZIONE E BOOST NLP (più veloce di LLM)
        # Usa embeddings semantici per validare la categoria
        # ========================================================
        nlp_validated = False
        nlp_boost_applied = False

        if rule_categoria and rule_confidence >= 0.60 and self.use_nlp:
            try:
                nlp_enhancer = get_nlp_enhancer()
                if nlp_enhancer:
                    # 4a. Valida categoria con NLP (embeddings semantici)
                    is_valid, nlp_conf, nlp_reason = nlp_enhancer.validate_category_with_nlp(
                        categoria=rule_categoria.value,
                        oggetto=oggetto,
                        corpo=full_text[:1500] if full_text else ""
                    )

                    if is_valid and nlp_conf >= 0.5:
                        nlp_validated = True
                        logger.info(f"🧠 NLP valida {rule_categoria.value}: {nlp_reason}")

                        # 4b. Applica confidence boost
                        boosted_conf, boost_reason = nlp_enhancer.get_category_confidence_boost(
                            categoria=rule_categoria.value,
                            mittente=mittente,
                            oggetto=oggetto,
                            corpo=full_text[:1500] if full_text else "",
                            current_confidence=rule_confidence
                        )

                        if boosted_conf > rule_confidence:
                            nlp_boost_applied = True
                            logger.info(f"📈 NLP boost: {rule_confidence:.2f} → {boosted_conf:.2f} ({boost_reason})")
                            rule_confidence = boosted_conf

            except Exception as e:
                logger.warning(f"⚠️ Errore validazione NLP: {e}")

        # ========================================================
        # STEP 4.5: VALIDAZIONE SEMANTICA LLM (fallback se NLP non valida)
        # Solo se NLP non ha validato e confidence è abbastanza alta
        # ========================================================
        if rule_categoria and rule_confidence >= 0.70:
            if nlp_validated:
                # NLP ha già validato - usa risultato rule-based con boost
                logger.info(f"✅ Categoria validata da NLP: {rule_categoria.value} (conf: {rule_confidence:.2f})")
                return rule_categoria, rule_confidence, rule_sottocategoria, rule_proposta_info
            else:
                # Fallback a validazione LLM
                is_valid, validation_confidence = self._validate_semantic(
                    categoria=rule_categoria,
                    sender_type=sender_type,
                    oggetto=oggetto,
                    corpo=full_text[:1500] if full_text else ""
                )

                if is_valid:
                    # Validazione LLM OK
                    final_confidence = min(rule_confidence, validation_confidence)
                    logger.info(f"✅ Validazione LLM OK: {rule_categoria.value} (conf: {final_confidence:.2f})")
                    return rule_categoria, final_confidence, rule_sottocategoria, rule_proposta_info
                else:
                    # Validazione LLM fallita - per mittenti verificati, usa rule-based
                    if sender_type in ["SCUOLA", "USP_UST", "SNALS_CENTRALE"]:
                        logger.warning(f"⚠️ Validazione LLM negativa ma mittente {sender_type} verificato → uso rule-based")
                        return rule_categoria, rule_confidence * 0.85, rule_sottocategoria, rule_proposta_info
                    # Se NLP aveva dato un hint sul mittente, considera quello
                    if nlp_sender_hint and nlp_entities.get('has_institutional_reference'):
                        logger.info(f"🧠 NLP conferma riferimento istituzionale → uso rule-based con hint NLP")
                        return rule_categoria, rule_confidence * 0.80, rule_sottocategoria, rule_proposta_info
                    logger.warning(f"⚠️ Validazione semantica FALLITA per {rule_categoria.value} - procedo con LLM")

        # ========================================================
        # STEP 5: NLP SUGGERIMENTO CATEGORIA (se rule-based incerto)
        # Prima di chiamare LLM, prova a usare NLP per suggerire categoria
        # ========================================================
        if self.use_nlp and (not rule_categoria or rule_confidence < 0.60):
            try:
                nlp_enhancer = get_nlp_enhancer()
                if nlp_enhancer:
                    nlp_suggestion = nlp_enhancer.suggest_category_from_content(
                        oggetto=oggetto,
                        corpo=full_text[:1500] if full_text else "",
                        threshold=0.55
                    )

                    if nlp_suggestion:
                        nlp_cat, nlp_conf, nlp_reason = nlp_suggestion
                        logger.info(f"🎯 NLP suggerisce categoria: {nlp_cat} (conf: {nlp_conf:.2f}) - {nlp_reason}")

                        # Usa suggerimento NLP se confidence buona
                        if nlp_conf >= 0.65:
                            try:
                                suggested_category = EmailCategory[nlp_cat.upper()]
                                # Applica regole mittente se NLP ha dato hint
                                if nlp_sender_hint:
                                    suggested_category = self._validate_category_for_sender(
                                        suggested_category, nlp_sender_hint
                                    )
                                return suggested_category, nlp_conf, None, None
                            except KeyError:
                                logger.warning(f"Categoria NLP sconosciuta: {nlp_cat}")
            except Exception as e:
                logger.warning(f"⚠️ Errore suggerimento NLP: {e}")

        # ========================================================
        # STEP 6: LLM CON PROMPT SPECIFICO PER TIPO MITTENTE
        # ========================================================
        # Usa NLP sender hint se disponibile e mittente è ALTRO
        effective_sender_type = sender_type
        if sender_type == "ALTRO" and nlp_sender_hint:
            effective_sender_type = nlp_sender_hint
            logger.info(f"🧠 Uso hint NLP per LLM: {effective_sender_type}")

        logger.info(f"🤖 Uso LLM con prompt specifico per mittente {effective_sender_type}")
        return self._categorize_with_llm(mittente, oggetto, full_text, effective_sender_type)

    # ========================================================
    # VALIDAZIONE SEMANTICA LLM
    # ========================================================
    SEMANTIC_VALIDATION_PROMPT = """Valida se questa categorizzazione è corretta.

TIPO MITTENTE: {sender_type}
CATEGORIA PROPOSTA: {categoria}
OGGETTO: {oggetto}
CONTENUTO: {corpo}

⚠️ REGOLA FONDAMENTALE:
Il TIPO MITTENTE è un indicatore FORTISSIMO già verificato dal dominio email:
- SCUOLA = email da dominio @istruzione.it con codice meccanografico (es. taic851009@istruzione.it)
- USP_UST = email da uffici scolastici provinciali/regionali
- SNALS_CENTRALE = email da snals.it

Se il mittente è SCUOLA o USP_UST, la categoria proposta è quasi certamente corretta.
Invalida SOLO se il contenuto è CHIARAMENTE incompatibile (es. phishing evidente, spam palese).
NON invalidare per dubbi minori - il mittente verificato ha priorità.

La categoria "{categoria}" è appropriata per questo contenuto?

Rispondi SOLO con JSON:
{{"valido": true/false, "confidence": 0.0-1.0, "motivo": "breve spiegazione"}}"""

    def _validate_semantic(
        self,
        categoria: EmailCategory,
        sender_type: str,
        oggetto: str,
        corpo: str
    ) -> Tuple[bool, float]:
        """
        Validazione semantica LLM: verifica se la categoria assegnata
        ha senso per il contenuto dell'email.

        Returns:
            Tuple (is_valid, confidence)
        """
        # Skip validation per categorie ovvie
        if categoria == EmailCategory.SPAM:
            return True, 0.90

        # Skip se SNALS centrale (sempre corretto per quel mittente)
        if sender_type == "SNALS_CENTRALE":
            return True, 0.95

        prompt = self.SEMANTIC_VALIDATION_PROMPT.format(
            sender_type=sender_type,
            categoria=categoria.value,
            oggetto=oggetto,
            corpo=corpo[:1000]
        )

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                model_type="validation",
                format_json=True,
                temperature=0.1
            )

            result = self.llm_client.parse_json_response(response)

            if not result:
                # Se LLM non risponde, considera valido con confidence bassa
                logger.warning("⚠️ Validazione semantica: nessuna risposta LLM, assumo valido")
                return True, 0.60

            is_valid = result.get("valido", True)
            confidence = float(result.get("confidence", 0.7))
            motivo = result.get("motivo", "")

            logger.info(f"🔍 Validazione semantica: valido={is_valid}, conf={confidence:.2f}, motivo={motivo[:50]}")
            return is_valid, confidence

        except Exception as e:
            logger.error(f"❌ Errore validazione semantica: {e}")
            # In caso di errore, considera valido per non bloccare
            return True, 0.50

    # Prompt specifici per tipo mittente - LLM sceglie SOLO tra categorie valide
    PROMPT_BY_SENDER = {
        "USP_UST": """Il mittente è stato identificato come UST/USR (Ufficio Scolastico).

CATEGORIE POSSIBILI (scegli SOLO tra queste):
- comunicazione_scuola: Se contiene convocazione a riunione con data/ora
- comunicazione_ust_usr: Comunicazioni ufficiali, graduatorie, supplenze, interpelli

Email:
Mittente: {mittente}
Oggetto: {oggetto}
Corpo: {corpo}

Rispondi SOLO con JSON: {{"categoria": "...", "confidence": 0.9, "motivazione": "..."}}""",

        "SCUOLA": """Il mittente è stato identificato come SCUOLA (istituto scolastico).

CATEGORIE POSSIBILI (scegli SOLO tra queste):
- comunicazione_scuola: Se contiene convocazione RSU, assemblea, tavolo contrattazione con data/ora
- comunicazione_scuola: Comunicazioni, circolari, contrattazione integrativa

Email:
Mittente: {mittente}
Oggetto: {oggetto}
Corpo: {corpo}

Rispondi SOLO con JSON: {{"categoria": "...", "confidence": 0.9, "motivazione": "..."}}""",

        "SNALS_CENTRALE": """Il mittente è SNALS centrale (info@snals.it).

CATEGORIA: comunicazione_snals_centrale

Email:
Mittente: {mittente}
Oggetto: {oggetto}

Rispondi con JSON: {{"categoria": "comunicazione_snals_centrale", "confidence": 0.95, "motivazione": "Mittente SNALS centrale"}}""",

        "ALTRO": """Il mittente NON è un ente istituzionale conosciuto (non è UST/USR, non è una scuola).

CATEGORIE POSSIBILI (scegli SOLO tra queste):
- richiesta_tesseramento: Richiesta iscrizione al sindacato
- richiesta_appuntamento: Richiesta di appuntamento
- info_generiche: Domande su diritti, contratti, permessi
- pubblicita: Materiale promozionale/commerciale
- spam: Email sospette, phishing, truffe
- varie: Altro non classificabile

⚠️ NON PUOI scegliere: comunicazione_ust_usr, comunicazione_scuola, comunicazione_scuola

Email:
Mittente: {mittente}
Oggetto: {oggetto}
Corpo: {corpo}

Rispondi SOLO con JSON: {{"categoria": "...", "confidence": 0.9, "motivazione": "..."}}"""
    }

    def _categorize_with_llm(
        self,
        mittente: str,
        oggetto: str,
        corpo: str,
        sender_type: str = "ALTRO"
    ) -> Tuple[EmailCategory, float, Optional[str], Optional[Dict]]:
        """
        Categorizzazione con LLM usando prompt specifico per tipo mittente.
        L'LLM può scegliere SOLO tra le categorie valide per quel tipo di mittente.

        Args:
            sender_type: Tipo mittente già identificato (USP_UST, SCUOLA, SNALS_CENTRALE, ALTRO)

        Returns:
            Tuple (categoria, confidence, sottocategoria, proposta_info)
        """
        # Usa prompt specifico per tipo mittente
        prompt_template = self.PROMPT_BY_SENDER.get(sender_type, self.PROMPT_BY_SENDER["ALTRO"])

        prompt = prompt_template.format(
            mittente=mittente,
            oggetto=oggetto,
            corpo=corpo[:2000]
        )

        logger.info(f"🤖 LLM categorizzazione per mittente tipo: {sender_type}")

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                model_type="categorization",
                format_json=True,
                temperature=0.2
            )

            result = self.llm_client.parse_json_response(response)

            if not result:
                logger.error("❌ LLM non ha restituito risultato valido")
                # Fallback sicuro in base al tipo mittente
                return self._fallback_by_sender_type(sender_type)

            categoria_str = result.get("categoria", "varie")
            confidence = float(result.get("confidence", 0.5))

            # Mapping categorie legacy/rimosse
            categoria_mapping = {
                "pubblicita": "spam",
                "convocazione_scuola": "comunicazione_scuola",
                "notifica_sistema": "ricevuta_pec",
            }
            categoria_str = categoria_mapping.get(categoria_str.lower(), categoria_str)

            try:
                categoria = EmailCategory[categoria_str.upper()]
            except KeyError:
                logger.warning(f"Categoria LLM sconosciuta: {categoria_str}")
                return self._fallback_by_sender_type(sender_type)

            # Validazione finale: assicurati che LLM non abbia scelto categoria invalida
            categoria = self._validate_category_for_sender(categoria, sender_type)

            logger.info(f"🤖 LLM: {categoria.value} (conf: {confidence}) per mittente {sender_type}")
            return categoria, confidence, None, None

        except Exception as e:
            logger.error(f"❌ Errore LLM: {e}")
            return self._fallback_by_sender_type(sender_type)

    def _fallback_by_sender_type(self, sender_type: str) -> Tuple[EmailCategory, float, Optional[str], Optional[Dict]]:
        """Categoria di fallback sicura in base al tipo mittente"""
        fallbacks = {
            "USP_UST": (EmailCategory.COMUNICAZIONE_UST_USR, 0.6, None, None),
            "SCUOLA": (EmailCategory.COMUNICAZIONE_SCUOLA, 0.6, None, None),
            "SNALS_CENTRALE": (EmailCategory.COMUNICAZIONE_SNALS_CENTRALE, 0.9, None, None),
            "ALTRO": (EmailCategory.VARIE, 0.5, None, None),
        }
        return fallbacks.get(sender_type, (EmailCategory.VARIE, 0.5, None, None))

    def _validate_category_for_sender(self, categoria: EmailCategory, sender_type: str) -> EmailCategory:
        """Valida che la categoria sia compatibile con il tipo mittente"""
        valid_categories = {
            "USP_UST": [EmailCategory.COMUNICAZIONE_UST_USR, EmailCategory.COMUNICAZIONE_SCUOLA],
            "SCUOLA": [EmailCategory.COMUNICAZIONE_SCUOLA, EmailCategory.COMUNICAZIONE_SCUOLA],
            "SNALS_CENTRALE": [EmailCategory.COMUNICAZIONE_SNALS_CENTRALE],
            "ALTRO": [EmailCategory.VARIE, EmailCategory.SPAM,
                      EmailCategory.RICHIESTA_TESSERAMENTO, EmailCategory.RICHIESTA_APPUNTAMENTO,
                      EmailCategory.INFO_GENERICHE],
        }

        allowed = valid_categories.get(sender_type, [EmailCategory.VARIE])

        if categoria not in allowed:
            logger.warning(f"⚠️ Categoria {categoria.value} non valida per {sender_type}, uso fallback")
            return self._fallback_by_sender_type(sender_type)[0]

        return categoria
