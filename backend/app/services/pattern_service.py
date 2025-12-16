"""
Pattern Service - Gestione pattern per spaCy EntityRuler.

Gestisce tre tipi di pattern:
1. Base: Pattern predefiniti (classi concorso, province, scuole note)
2. Trained: Pattern generati automaticamente da sample approvati
3. Manual: Pattern aggiunti manualmente dall'utente

Fornisce:
- CRUD per pattern manuali
- Preview pattern su testo
- Export pattern per EntityRuler
"""

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Directory per dati training
TRAINING_DATA_DIR = Path(__file__).parent.parent / "data" / "training"
TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)


class PatternService:
    """Servizio per gestione pattern spaCy."""

    # Label valide per pattern
    VALID_LABELS = [
        "CLASSE_CONCORSO",
        "MECCANOGRAFICO",
        "ISTITUTO",
        "PROVINCIA",
        "MOTIVO",
        "EMAIL",
        "PHONE",
        "DATE",
        "LOC",
        "ORG",
        "PER"
    ]

    def __init__(self):
        self._manual_patterns_file = TRAINING_DATA_DIR / "manual_patterns.json"
        self._trained_patterns_file = TRAINING_DATA_DIR / "trained_patterns.json"
        self._pattern_history_file = TRAINING_DATA_DIR / "pattern_versions.json"
        self._load_patterns()

    def _load_patterns(self):
        """Carica pattern manuali da file."""
        self.manual_patterns: List[Dict[str, Any]] = []
        if self._manual_patterns_file.exists():
            try:
                with open(self._manual_patterns_file, 'r', encoding='utf-8') as f:
                    self.manual_patterns = json.load(f)
                logger.info(f"✅ Caricati {len(self.manual_patterns)} pattern manuali")
            except Exception as e:
                logger.warning(f"⚠️ Errore caricamento pattern manuali: {e}")

    def _save_manual_patterns(self):
        """Salva pattern manuali su file."""
        try:
            with open(self._manual_patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.manual_patterns, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Salvati {len(self.manual_patterns)} pattern manuali")
        except Exception as e:
            logger.error(f"❌ Errore salvataggio pattern manuali: {e}")
            raise

    def _add_to_history(self, action: str, pattern_id: str, label: str, pattern_text: str):
        """Aggiunge entry allo storico versioni."""
        history = []
        if self._pattern_history_file.exists():
            try:
                with open(self._pattern_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                pass

        history.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,  # 'add', 'edit', 'delete'
            "pattern_id": pattern_id,
            "label": label,
            "pattern": pattern_text,
            "source": "manual"
        })

        # Mantieni solo ultime 100 entry
        history = history[-100:]

        with open(self._pattern_history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def get_base_patterns(self) -> List[Dict[str, Any]]:
        """
        Restituisce pattern base predefiniti.
        Questi sono caricati da nlp_training_data.py
        """
        try:
            from app.services.nlp_training_data import NLPTrainingData
            training_data = NLPTrainingData()
            patterns = training_data.get_entity_ruler_patterns()
            # Aggiungi source a ogni pattern
            for p in patterns:
                p["source"] = "base"
            return patterns
        except Exception as e:
            logger.error(f"❌ Errore caricamento pattern base: {e}")
            return []

    def get_trained_patterns(self) -> List[Dict[str, Any]]:
        """
        Restituisce pattern generati da training automatico.
        """
        patterns = []
        if self._trained_patterns_file.exists():
            try:
                with open(self._trained_patterns_file, 'r', encoding='utf-8') as f:
                    patterns = json.load(f)
                # Aggiungi source a ogni pattern
                for p in patterns:
                    p["source"] = "trained"
            except Exception as e:
                logger.error(f"❌ Errore caricamento pattern trained: {e}")
        return patterns

    def get_manual_patterns(self) -> List[Dict[str, Any]]:
        """
        Restituisce pattern aggiunti manualmente.
        """
        # Assicurati che ogni pattern abbia source
        for p in self.manual_patterns:
            p["source"] = "manual"
        return self.manual_patterns.copy()

    def get_all_patterns(
        self,
        source: Optional[str] = None,
        label: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Restituisce tutti i pattern filtrati per source e/o label.

        Args:
            source: 'base', 'trained', 'manual', o None per tutti
            label: Label specifica da filtrare, o None per tutte

        Returns:
            Lista di pattern
        """
        patterns = []

        if source is None or source == "all":
            patterns.extend(self.get_base_patterns())
            patterns.extend(self.get_trained_patterns())
            patterns.extend(self.get_manual_patterns())
        elif source == "base":
            patterns = self.get_base_patterns()
        elif source == "trained":
            patterns = self.get_trained_patterns()
        elif source == "manual":
            patterns = self.get_manual_patterns()

        # Filtra per label se specificato
        if label:
            patterns = [p for p in patterns if p.get("label") == label]

        return patterns

    def add_manual_pattern(
        self,
        label: str,
        pattern: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggiunge un nuovo pattern manuale.

        Args:
            label: Tipo di entità (CLASSE_CONCORSO, MECCANOGRAFICO, etc.)
            pattern: Testo del pattern
            description: Descrizione opzionale

        Returns:
            Pattern creato

        Raises:
            ValueError: Se label non valido o pattern duplicato
        """
        # Valida label
        if label not in self.VALID_LABELS:
            raise ValueError(f"Label non valido: {label}. Valori ammessi: {self.VALID_LABELS}")

        # Controlla duplicati
        pattern_lower = pattern.lower().strip()
        for existing in self.manual_patterns:
            if existing.get("pattern", "").lower().strip() == pattern_lower and existing.get("label") == label:
                raise ValueError(f"Pattern già esistente: {pattern}")

        # Genera ID univoco
        pattern_id = f"manual_{label.lower()[:4]}_{uuid.uuid4().hex[:8]}"

        new_pattern = {
            "id": pattern_id,
            "label": label,
            "pattern": pattern.strip(),
            "source": "manual",
            "created_at": datetime.now().isoformat(),
            "description": description
        }

        self.manual_patterns.append(new_pattern)
        self._save_manual_patterns()
        self._add_to_history("add", pattern_id, label, pattern)

        logger.info(f"✅ Aggiunto pattern manuale: {label} = '{pattern}'")
        return new_pattern

    def update_manual_pattern(
        self,
        pattern_id: str,
        label: Optional[str] = None,
        pattern: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Modifica un pattern manuale esistente.

        Args:
            pattern_id: ID del pattern da modificare
            label: Nuovo label (opzionale)
            pattern: Nuovo testo pattern (opzionale)
            description: Nuova descrizione (opzionale)

        Returns:
            Pattern aggiornato

        Raises:
            ValueError: Se pattern non trovato o non manuale
        """
        # Trova pattern
        target_idx = None
        for idx, p in enumerate(self.manual_patterns):
            if p.get("id") == pattern_id:
                target_idx = idx
                break

        if target_idx is None:
            raise ValueError(f"Pattern non trovato: {pattern_id}")

        target = self.manual_patterns[target_idx]

        # Aggiorna campi
        if label is not None:
            if label not in self.VALID_LABELS:
                raise ValueError(f"Label non valido: {label}")
            target["label"] = label

        if pattern is not None:
            target["pattern"] = pattern.strip()

        if description is not None:
            target["description"] = description

        target["updated_at"] = datetime.now().isoformat()

        self._save_manual_patterns()
        self._add_to_history("edit", pattern_id, target["label"], target["pattern"])

        logger.info(f"✅ Aggiornato pattern manuale: {pattern_id}")
        return target

    def delete_manual_pattern(self, pattern_id: str) -> bool:
        """
        Elimina un pattern manuale.

        Args:
            pattern_id: ID del pattern da eliminare

        Returns:
            True se eliminato

        Raises:
            ValueError: Se pattern non trovato
        """
        # Trova pattern
        target_idx = None
        target = None
        for idx, p in enumerate(self.manual_patterns):
            if p.get("id") == pattern_id:
                target_idx = idx
                target = p
                break

        if target_idx is None:
            raise ValueError(f"Pattern non trovato: {pattern_id}")

        # Rimuovi
        del self.manual_patterns[target_idx]
        self._save_manual_patterns()
        self._add_to_history("delete", pattern_id, target["label"], target["pattern"])

        logger.info(f"✅ Eliminato pattern manuale: {pattern_id}")
        return True

    def preview_pattern(
        self,
        pattern: str,
        label: str,
        text: str
    ) -> List[Dict[str, Any]]:
        """
        Testa un pattern su un testo e restituisce le corrispondenze.

        Args:
            pattern: Testo del pattern da testare
            label: Label del pattern
            text: Testo su cui testare

        Returns:
            Lista di match con start, end, text
        """
        matches = []

        try:
            # Cerca pattern case-insensitive
            pattern_escaped = re.escape(pattern)
            for match in re.finditer(pattern_escaped, text, re.IGNORECASE):
                matches.append({
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "label": label
                })
        except re.error as e:
            logger.warning(f"⚠️ Errore regex in preview: {e}")

        return matches

    def export_for_entity_ruler(self) -> List[Dict[str, Any]]:
        """
        Esporta tutti i pattern in formato EntityRuler di spaCy.

        Returns:
            Lista pattern in formato {"label": ..., "pattern": ...}
        """
        all_patterns = []

        # Pattern base
        all_patterns.extend(self.get_base_patterns())

        # Pattern trained
        all_patterns.extend(self.get_trained_patterns())

        # Pattern manuali
        all_patterns.extend(self.get_manual_patterns())

        # Rimuovi duplicati basandosi su (label, pattern)
        seen = set()
        unique_patterns = []
        for p in all_patterns:
            key = (p.get("label"), p.get("pattern", "").lower())
            if key not in seen:
                seen.add(key)
                # Formato EntityRuler richiede solo label e pattern
                unique_patterns.append({
                    "label": p.get("label"),
                    "pattern": p.get("pattern"),
                    "id": p.get("id", f"p_{len(unique_patterns)}")
                })

        return unique_patterns

    def get_pattern_stats(self) -> Dict[str, Any]:
        """
        Restituisce statistiche sui pattern.

        Returns:
            Dict con conteggi per source e label
        """
        base = self.get_base_patterns()
        trained = self.get_trained_patterns()
        manual = self.get_manual_patterns()

        # Conta per label
        label_counts = {}
        for p in base + trained + manual:
            label = p.get("label", "UNKNOWN")
            label_counts[label] = label_counts.get(label, 0) + 1

        return {
            "total": len(base) + len(trained) + len(manual),
            "by_source": {
                "base": len(base),
                "trained": len(trained),
                "manual": len(manual)
            },
            "by_label": label_counts
        }

    def get_pattern_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Restituisce lo storico modifiche pattern manuali.

        Args:
            limit: Numero massimo di entry da restituire

        Returns:
            Lista entry storico (più recenti prima)
        """
        history = []
        if self._pattern_history_file.exists():
            try:
                with open(self._pattern_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                pass

        # Ordina per timestamp decrescente e limita
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return history[:limit]


# Singleton instance
_pattern_service: Optional[PatternService] = None


def get_pattern_service() -> PatternService:
    """Restituisce istanza singleton di PatternService."""
    global _pattern_service
    if _pattern_service is None:
        _pattern_service = PatternService()
    return _pattern_service
