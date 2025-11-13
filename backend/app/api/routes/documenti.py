"""
API Routes per gestione Documenti e RAG.

FASE 9: RAG System
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
import shutil
from pathlib import Path

from app.database import get_db
from app.models.documento import Documento, TipoDocumento, StatoDocumento
from app.services.rag_service import RAGService
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/documenti", tags=["documenti"])


class DocumentoCreate(BaseModel):
    """Schema creazione documento."""
    titolo: str
    descrizione: Optional[str] = None
    tipo: TipoDocumento
    url_sorgente: Optional[str] = None
    embedding_abilitato: bool = True
    priorita: int = 10
    versione: Optional[str] = None


class DocumentoUpdate(BaseModel):
    """Schema aggiornamento documento."""
    titolo: Optional[str] = None
    descrizione: Optional[str] = None
    embedding_abilitato: Optional[bool] = None
    priorita: Optional[int] = None
    attivo: Optional[bool] = None


class RAGQueryRequest(BaseModel):
    """Schema richiesta RAG."""
    query: str
    context: Optional[str] = None
    tipo_filter: Optional[List[TipoDocumento]] = None
    n_docs: int = 3


@router.get("/")
def list_documenti(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tipo: Optional[str] = None,
    stato: Optional[str] = None,
    attivo: Optional[bool] = None,
    embedding_abilitato: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Lista documenti con filtri.

    - **skip**: Offset paginazione
    - **limit**: Numero risultati
    - **tipo**: Filtra per tipo documento
    - **stato**: Filtra per stato
    - **attivo**: Filtra per attivo/disattivo
    - **embedding_abilitato**: Filtra per embedding abilitato
    """
    query = db.query(Documento)

    if tipo:
        try:
            tipo_enum = TipoDocumento(tipo)
            query = query.filter(Documento.tipo == tipo_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Tipo non valido: {tipo}")

    if stato:
        try:
            stato_enum = StatoDocumento(stato)
            query = query.filter(Documento.stato == stato_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Stato non valido: {stato}")

    if attivo is not None:
        query = query.filter(Documento.attivo == attivo)

    if embedding_abilitato is not None:
        query = query.filter(Documento.embedding_abilitato == embedding_abilitato)

    total = query.count()
    documenti = query.order_by(Documento.priorita.desc(), Documento.caricato_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "documenti": documenti
    }


@router.get("/{documento_id}")
def get_documento(documento_id: int, db: Session = Depends(get_db)):
    """Recupera dettagli documento."""
    documento = db.query(Documento).filter(Documento.id == documento_id).first()

    if not documento:
        raise HTTPException(status_code=404, detail="Documento non trovato")

    return documento


@router.post("/upload")
async def upload_documento(
    file: UploadFile = File(...),
    titolo: str = Body(...),
    descrizione: Optional[str] = Body(None),
    tipo: str = Body(...),
    embedding_abilitato: bool = Body(True),
    priorita: int = Body(10),
    db: Session = Depends(get_db)
):
    """
    Carica un nuovo documento.

    Supporta: PDF, DOCX, TXT, HTML, MD

    Esempio:
    ```bash
    curl -X POST "http://localhost:8001/api/documenti/upload" \
      -F "file=@documento.pdf" \
      -F "titolo=Circolare SNALS 2025" \
      -F "tipo=snals_centrale" \
      -F "embedding_abilitato=true"
    ```
    """
    try:
        # Valida tipo
        try:
            tipo_enum = TipoDocumento(tipo)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Tipo non valido: {tipo}")

        # Salva file
        upload_dir = Path(settings.STORAGE_PATH) / "documenti"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / f"{documento.id}_{file.filename}"

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Crea documento nel DB
        documento = Documento(
            titolo=titolo,
            descrizione=descrizione,
            tipo=tipo_enum,
            file_path=str(file_path),
            embedding_abilitato=embedding_abilitato,
            priorita=priorita,
            stato=StatoDocumento.CARICATO,
            attivo=True
        )

        db.add(documento)
        db.commit()
        db.refresh(documento)

        # Se embedding abilitato, processa subito
        if embedding_abilitato:
            rag_service = RAGService(db)
            success = rag_service.embed_documento(documento.id)

            if not success:
                return {
                    "message": "Documento caricato ma embedding fallito",
                    "documento": documento,
                    "warning": "Embedding non riuscito"
                }

        return {
            "message": "Documento caricato con successo",
            "documento": documento
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore upload: {str(e)}")


@router.post("/{documento_id}/embed")
def embed_documento(documento_id: int, db: Session = Depends(get_db)):
    """
    Embedda (o riembedda) un documento.

    Crea embedding e lo aggiunge al vector store.
    """
    rag_service = RAGService(db)

    try:
        success = rag_service.embed_documento(documento_id)

        if success:
            return {
                "message": "Documento embeddato con successo",
                "documento_id": documento_id
            }
        else:
            raise HTTPException(status_code=500, detail="Embedding fallito")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore embedding: {str(e)}")


@router.post("/rag/query")
def rag_query(
    request: RAGQueryRequest,
    db: Session = Depends(get_db)
):
    """
    Esegue query RAG.

    Cerca documenti rilevanti e genera risposta informata.

    Esempio:
    ```json
    {
      "query": "Quali sono le procedure per il tesseramento?",
      "tipo_filter": ["snals_centrale", "faq"],
      "n_docs": 5
    }
    ```
    """
    rag_service = RAGService(db)

    try:
        result = rag_service.generate_rag_response(
            query=request.query,
            context=request.context,
            tipo_filter=request.tipo_filter,
            n_docs=request.n_docs
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore RAG query: {str(e)}")


@router.get("/rag/stats")
def rag_stats(db: Session = Depends(get_db)):
    """
    Statistiche RAG system.

    Ritorna info su documenti embeddati, vector store, etc.
    """
    try:
        # Stats documenti DB
        total_docs = db.query(Documento).count()
        docs_embeddati = db.query(Documento).filter(Documento.stato == StatoDocumento.EMBEDDATO).count()
        docs_attivi = db.query(Documento).filter(Documento.attivo == True).count()

        # Stats per tipo
        stats_per_tipo = {}
        for tipo in TipoDocumento:
            count = db.query(Documento).filter(Documento.tipo == tipo).count()
            stats_per_tipo[tipo.value] = count

        # Stats vector store
        rag_service = RAGService(db)
        vs_stats = rag_service.vector_store.get_stats()

        return {
            "database": {
                "total_documenti": total_docs,
                "embeddati": docs_embeddati,
                "attivi": docs_attivi,
                "per_tipo": stats_per_tipo
            },
            "vector_store": vs_stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore stats: {str(e)}")


@router.put("/{documento_id}")
def update_documento(
    documento_id: int,
    update_data: DocumentoUpdate,
    db: Session = Depends(get_db)
):
    """Aggiorna documento."""
    documento = db.query(Documento).filter(Documento.id == documento_id).first()

    if not documento:
        raise HTTPException(status_code=404, detail="Documento non trovato")

    if update_data.titolo is not None:
        documento.titolo = update_data.titolo

    if update_data.descrizione is not None:
        documento.descrizione = update_data.descrizione

    if update_data.embedding_abilitato is not None:
        documento.embedding_abilitato = update_data.embedding_abilitato

    if update_data.priorita is not None:
        documento.priorita = update_data.priorita

    if update_data.attivo is not None:
        documento.attivo = update_data.attivo

    db.commit()
    db.refresh(documento)

    return {"message": "Documento aggiornato", "documento": documento}


@router.delete("/{documento_id}")
def delete_documento(documento_id: int, db: Session = Depends(get_db)):
    """
    Elimina documento.

    Rimuove sia dal database che dal vector store.
    """
    documento = db.query(Documento).filter(Documento.id == documento_id).first()

    if not documento:
        raise HTTPException(status_code=404, detail="Documento non trovato")

    try:
        # Rimuovi dal vector store se embeddato
        if documento.stato == StatoDocumento.EMBEDDATO and documento.num_chunks > 0:
            rag_service = RAGService(db)
            ids_to_delete = [f"doc_{documento.id}_chunk_{i}" for i in range(documento.num_chunks)]
            rag_service.vector_store.delete_documents(ids_to_delete)

        # Rimuovi file se esiste
        if documento.file_path:
            try:
                Path(documento.file_path).unlink()
            except:
                pass

        # Rimuovi da DB
        db.delete(documento)
        db.commit()

        return {"message": "Documento eliminato"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore eliminazione: {str(e)}")
