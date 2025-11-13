"""
Document Processor per estrarre testo e creare embeddings.

FASE 9: RAG System
"""
import logging
import os
from typing import List, Dict, Tuple
from pathlib import Path
import PyPDF2
import docx
from bs4 import BeautifulSoup

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Processore per estrarre testo da vari formati."""

    def __init__(self):
        """Inizializza processor."""
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP

    def extract_text_from_file(self, file_path: str) -> str:
        """
        Estrae testo da un file.

        Supporta: PDF, DOCX, TXT, HTML, MD

        Args:
            file_path: Path al file

        Returns:
            str: Testo estratto
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File non trovato: {file_path}")

        extension = file_path.suffix.lower()

        try:
            if extension == '.pdf':
                return self._extract_pdf(file_path)
            elif extension in ['.docx', '.doc']:
                return self._extract_docx(file_path)
            elif extension in ['.txt', '.md']:
                return self._extract_text(file_path)
            elif extension in ['.html', '.htm']:
                return self._extract_html(file_path)
            else:
                logger.warning(f"Formato non supportato: {extension}")
                return ""

        except Exception as e:
            logger.error(f"❌ Errore estrazione testo da {file_path}: {e}")
            return ""

    def _extract_pdf(self, file_path: Path) -> str:
        """Estrae testo da PDF."""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"

            logger.info(f"✅ Estratto testo da PDF: {len(text)} caratteri")
            return text.strip()

        except Exception as e:
            logger.error(f"❌ Errore estrazione PDF: {e}")
            return ""

    def _extract_docx(self, file_path: Path) -> str:
        """Estrae testo da DOCX."""
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

            logger.info(f"✅ Estratto testo da DOCX: {len(text)} caratteri")
            return text.strip()

        except Exception as e:
            logger.error(f"❌ Errore estrazione DOCX: {e}")
            return ""

    def _extract_text(self, file_path: Path) -> str:
        """Estrae testo da file TXT/MD."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()

            logger.info(f"✅ Estratto testo: {len(text)} caratteri")
            return text.strip()

        except Exception as e:
            logger.error(f"❌ Errore estrazione testo: {e}")
            return ""

    def _extract_html(self, file_path: Path) -> str:
        """Estrae testo da HTML."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file, 'html.parser')
                text = soup.get_text(separator='\n', strip=True)

            logger.info(f"✅ Estratto testo da HTML: {len(text)} caratteri")
            return text.strip()

        except Exception as e:
            logger.error(f"❌ Errore estrazione HTML: {e}")
            return ""

    def chunk_text(self, text: str) -> List[str]:
        """
        Divide il testo in chunk per embedding.

        Args:
            text: Testo da dividere

        Returns:
            List[str]: Lista di chunk
        """
        if not text:
            return []

        # Split per paragrafi
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Se il paragrafo da solo è troppo grande, dividilo
            if len(para) > self.chunk_size:
                # Divide per frasi
                sentences = para.split('. ')
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) < self.chunk_size:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + ". "
            else:
                # Aggiungi al chunk corrente
                if len(current_chunk) + len(para) < self.chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"

        # Aggiungi ultimo chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        logger.info(f"✅ Testo diviso in {len(chunks)} chunk (size={self.chunk_size}, overlap={self.chunk_overlap})")
        return chunks

    def create_chunk_metadata(
        self,
        documento_id: int,
        chunk_index: int,
        total_chunks: int,
        documento_metadata: Dict
    ) -> Dict:
        """
        Crea metadata per un chunk.

        Args:
            documento_id: ID documento
            chunk_index: Indice chunk
            total_chunks: Totale chunk
            documento_metadata: Metadata documento originale

        Returns:
            Dict: Metadata chunk
        """
        return {
            'documento_id': documento_id,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'tipo': documento_metadata.get('tipo', 'altro'),
            'titolo': documento_metadata.get('titolo', ''),
            'data_documento': documento_metadata.get('data_documento', ''),
            'priorita': documento_metadata.get('priorita', 10),
        }

    def process_document_for_embedding(
        self,
        file_path: str,
        documento_id: int,
        documento_metadata: Dict
    ) -> Tuple[List[str], List[Dict], List[str]]:
        """
        Processa un documento completo per embedding.

        Args:
            file_path: Path al file
            documento_id: ID documento
            documento_metadata: Metadata documento

        Returns:
            Tuple: (chunks, metadatas, ids)
        """
        # Estrai testo
        text = self.extract_text_from_file(file_path)

        if not text:
            logger.warning(f"Nessun testo estratto da {file_path}")
            return [], [], []

        # Crea chunks
        chunks = self.chunk_text(text)

        # Crea metadata e IDs
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            metadata = self.create_chunk_metadata(
                documento_id, i, len(chunks), documento_metadata
            )
            metadatas.append(metadata)
            ids.append(f"doc_{documento_id}_chunk_{i}")

        logger.info(f"✅ Documento {documento_id} processato: {len(chunks)} chunks")
        return chunks, metadatas, ids
