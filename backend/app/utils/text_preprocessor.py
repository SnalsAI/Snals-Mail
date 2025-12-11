"""
Text Preprocessor per LLM - Troncamento intelligente del testo.

Ottimizza il testo prima di inviarlo a LLM:
1. Estrae e preserva informazioni chiave (date, codici, contatti)
2. Rimuove rumore (firme, disclaimer, quote)
3. Mantiene il testo entro limiti di token sicuri
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Limite caratteri (circa 3000 token per llama3.2)
MAX_CHARS_DEFAULT = 10000
MAX_CHARS_OLLAMA = 8000  # Più conservativo per Ollama

# Pattern per informazioni chiave da preservare
KEY_PATTERNS = {
    'classe_concorso': [
        r'[A-Z]{1,4}[-–]?\d{1,3}',  # A-26, A26, ADSS, B017
        r'classe\s+(?:di\s+)?concorso[:\s]+([A-Z0-9\-]+)',
    ],
    'meccanografico': [
        r'\b[A-Z]{2}[A-Z]{2}\d{5,6}[A-Z]?\b',  # TAIC824001, TAPC070005
    ],
    'date': [
        r'\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b',  # 04/12/2025, 4-12-25
        r'\b\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4}\b',
    ],
    'orari': [
        r'\b(?:ore\s+)?(\d{1,2})[:\.](\d{2})\b',  # ore 10:00, 10.30
        r'\balle\s+(?:ore\s+)?(\d{1,2})[:\.]?(\d{2})?\b',
    ],
    'email': [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    ],
    'telefono': [
        r'\b(?:\+39\s?)?(?:0\d{1,4}[-.\s]?)?\d{6,10}\b',
    ],
    'ore_settimanali': [
        r'\b(\d{1,2})\s*(?:ore|h|/h)\b',
        r'\bore\s*(?:settimanali)?[:\s]+(\d{1,2})\b',
    ],
}

# Pattern per rumore da rimuovere
NOISE_PATTERNS = [
    # Email signatures
    r'(?:^|\n)[-_=]{3,}.*?(?:$|\n)',
    r'(?:^|\n)Cordiali saluti.*?(?:$|\n)',
    r'(?:^|\n)Distinti saluti.*?(?:$|\n)',
    r'(?:^|\n)Best regards.*?(?:$|\n)',
    r'(?:^|\n)Inviato da.*?(?:$|\n)',
    r'(?:^|\n)Sent from.*?(?:$|\n)',

    # Disclaimers
    r'(?i)questa\s+(?:e-?mail|comunicazione|messaggio).*?(?:riservat|confidenzial).*?(?:\n|$)',
    r'(?i)this\s+(?:e-?mail|message).*?(?:confidential|privileged).*?(?:\n|$)',
    r'(?i)ai\s+sensi\s+del\s+(?:D\.?Lgs|decreto|regolamento).*?(?:\n|$)',
    r'(?i)informativa\s+(?:sulla\s+)?privacy.*?(?:\n|$)',

    # Quote headers
    r'(?:^|\n)Il\s+\d+/\d+/\d+.*?ha\s+scritto:.*?(?:\n|$)',
    r'(?:^|\n)On\s+\d+/\d+/\d+.*?wrote:.*?(?:\n|$)',
    r'(?:^|\n)>+\s*.*?(?:\n|$)',

    # Repeated whitespace
    r'\n{3,}',
    r'[ \t]{3,}',
]

# Pattern per sezioni importanti
IMPORTANT_SECTIONS = [
    r'(?:oggetto|subject)[:\s]+.*?(?:\n|$)',
    r'(?:convocazione|convoca)[:\s]+.*?(?:\n|$)',
    r'(?:ordine\s+del\s+giorno)[:\s]+.*?(?:\n|$)',
    r'(?:luogo|sede|presso)[:\s]+.*?(?:\n|$)',
    r'(?:data|giorno)[:\s]+.*?(?:\n|$)',
    r'(?:ora|orario)[:\s]+.*?(?:\n|$)',
    r'(?:classe\s+(?:di\s+)?concorso)[:\s]+.*?(?:\n|$)',
    r'(?:ore\s+settimanali)[:\s]+.*?(?:\n|$)',
    r'(?:scadenza)[:\s]+.*?(?:\n|$)',
    r'(?:codice\s+meccanografico)[:\s]+.*?(?:\n|$)',
    r'(?:contatti?|riferimento|email|tel)[:\s]+.*?(?:\n|$)',
]


def extract_key_info(text: str) -> Dict[str, List[str]]:
    """
    Estrae informazioni chiave dal testo.

    Returns:
        Dict con tipo -> lista di valori trovati
    """
    found = {}
    for key, patterns in KEY_PATTERNS.items():
        matches = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(0) if match.lastindex is None else match.group(1)
                if value and value not in matches:
                    matches.append(value)
        if matches:
            found[key] = matches
    return found


def remove_noise(text: str) -> str:
    """Rimuove rumore dal testo (firme, disclaimer, quote)."""
    result = text
    for pattern in NOISE_PATTERNS:
        result = re.sub(pattern, '\n', result, flags=re.MULTILINE | re.IGNORECASE)
    return result.strip()


def extract_important_sections(text: str) -> str:
    """Estrae sezioni importanti dal testo."""
    sections = []
    for pattern in IMPORTANT_SECTIONS:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            section = match.group(0).strip()
            if section and section not in sections:
                sections.append(section)
    return '\n'.join(sections)


def smart_truncate(
    text: str,
    max_chars: int = MAX_CHARS_DEFAULT,
    tipo: str = None,
    preserve_key_info: bool = True
) -> Tuple[str, Dict]:
    """
    Tronca il testo in modo intelligente per LLM.

    Args:
        text: Testo da troncare
        max_chars: Limite caratteri
        tipo: "interpello", "calendario", o None
        preserve_key_info: Se True, estrae info chiave e le prepende

    Returns:
        Tuple (testo_troncato, metadata)
    """
    if not text:
        return "", {"truncated": False}

    original_len = len(text)
    metadata = {
        "original_length": original_len,
        "truncated": False,
        "key_info_extracted": {}
    }

    # Se già sotto il limite, ritorna così com'è
    if original_len <= max_chars:
        return text, metadata

    # Step 1: Rimuovi rumore
    cleaned = remove_noise(text)

    # Step 2: Estrai informazioni chiave
    key_info = {}
    if preserve_key_info:
        key_info = extract_key_info(text)
        metadata["key_info_extracted"] = key_info

    # Step 3: Costruisci testo ottimizzato
    parts = []

    # 3a. Prependi info chiave estratte
    if key_info:
        key_summary = "[INFO CHIAVE ESTRATTE]\n"
        for k, values in key_info.items():
            key_summary += f"- {k}: {', '.join(str(v) for v in values[:3])}\n"
        parts.append(key_summary)

    # 3b. Estrai sezioni importanti
    important = extract_important_sections(text)
    if important:
        parts.append(f"[SEZIONI IMPORTANTI]\n{important[:1500]}")

    # 3c. Aggiungi corpo principale (primi N caratteri)
    remaining_space = max_chars - sum(len(p) for p in parts) - 200  # Buffer
    if remaining_space > 500:
        # Prendi inizio + fine del corpo
        corpo_inizio = cleaned[:remaining_space // 2]
        corpo_fine = cleaned[-(remaining_space // 4):] if len(cleaned) > remaining_space else ""

        if corpo_fine:
            parts.append(f"[CORPO INIZIO]\n{corpo_inizio}")
            parts.append(f"[CORPO FINE]\n{corpo_fine}")
        else:
            parts.append(f"[CORPO]\n{cleaned[:remaining_space]}")

    result = "\n\n".join(parts)

    # Tronca se ancora troppo lungo
    if len(result) > max_chars:
        result = result[:max_chars]
        metadata["hard_truncated"] = True

    metadata["truncated"] = True
    metadata["final_length"] = len(result)
    metadata["reduction_pct"] = round((1 - len(result) / original_len) * 100, 1)

    logger.debug(
        f"📝 Smart truncate: {original_len} -> {len(result)} chars "
        f"({metadata['reduction_pct']}% riduzione)"
    )

    return result, metadata


def preprocess_for_llm(
    text: str,
    tipo: str = None,
    provider: str = "ollama",
    include_subject: str = None
) -> str:
    """
    Preprocessa testo per invio a LLM.

    Args:
        text: Testo da preprocessare
        tipo: "interpello", "calendario", o None
        provider: "ollama" o "openai"
        include_subject: Oggetto email da includere sempre

    Returns:
        Testo preprocessato
    """
    max_chars = MAX_CHARS_OLLAMA if provider == "ollama" else MAX_CHARS_DEFAULT

    # Costruisci testo completo
    full_text = ""
    if include_subject:
        full_text = f"Oggetto: {include_subject}\n\n"
    full_text += text

    # Tronca intelligentemente
    processed, meta = smart_truncate(full_text, max_chars=max_chars, tipo=tipo)

    if meta.get("truncated"):
        logger.info(
            f"✂️ Testo preprocessato: {meta['original_length']} -> {meta['final_length']} chars "
            f"(key info: {list(meta.get('key_info_extracted', {}).keys())})"
        )

    return processed


def preprocess_allegati(
    allegati_testo: Dict[str, str],
    max_chars_per_file: int = 2000,
    max_total_chars: int = 5000
) -> str:
    """
    Preprocessa testo degli allegati in modo intelligente.

    Args:
        allegati_testo: Dict {nome_file: contenuto}
        max_chars_per_file: Max caratteri per singolo allegato
        max_total_chars: Max caratteri totale allegati

    Returns:
        Testo allegati preprocessato
    """
    if not allegati_testo:
        return ""

    processed_parts = []
    total_chars = 0

    for filename, content in allegati_testo.items():
        if not content:
            continue

        # Estrai info chiave dall'allegato
        key_info = extract_key_info(content)

        if key_info:
            # Se ci sono info chiave, crea sommario
            summary = f"[{filename}] "
            for k, values in key_info.items():
                summary += f"{k}: {', '.join(str(v) for v in values[:2])}; "
            processed_parts.append(summary.strip())
            total_chars += len(summary)
        else:
            # Altrimenti prendi primi N caratteri
            truncated = content[:max_chars_per_file]
            processed_parts.append(f"[{filename}]\n{truncated}")
            total_chars += len(truncated) + len(filename) + 3

        if total_chars >= max_total_chars:
            break

    return "\n\n".join(processed_parts)
