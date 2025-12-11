"""
API endpoints per RAG (Retrieval-Augmented Generation)
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

from app.database import get_db
from app.services.rag_service import get_rag_service
from app.models.email import Email

router = APIRouter(prefix="/rag", tags=["rag"])


# Schema request/response
class QueryRequest(BaseModel):
    query: str
    n_results: int = 5
    filter_categoria: Optional[str] = None
    filter_sottocategoria: Optional[str] = None
    filter_mittente: Optional[str] = None


class QueryResponse(BaseModel):
    query: str
    results_count: int
    documents: List[Dict[str, Any]]


class ChatRequest(BaseModel):
    query: str
    n_results: int = 5
    filter_categoria: Optional[str] = None
    filter_sottocategoria: Optional[str] = None
    filter_mittente: Optional[str] = None
    use_openai: bool = False
    max_context_docs: int = 4
    max_doc_length: int = 1500


class ChatResponse(BaseModel):
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    sources_count: int
    llm_model: Optional[str] = None
    cached: bool = False

    class Config:
        populate_by_name = True


class IndexEmailRequest(BaseModel):
    email_id: int


class IndexEmailResponse(BaseModel):
    indexed: bool
    email_id: int
    documents_indexed: int
    total_documents: int
    errors: List[str]


class StatisticsResponse(BaseModel):
    total_documents: int
    collection_name: str
    persist_directory: str


class DocumentMetadata(BaseModel):
    categoria: Optional[str] = None
    sottocategoria: Optional[str] = None
    mittente: Optional[str] = None
    argomento: Optional[str] = None
    scuola: Optional[str] = None


class UpdateMetadataRequest(BaseModel):
    document_id: str
    metadata: Dict[str, Any]


@router.get("/documents")
def list_documents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    filter_categoria: Optional[str] = None,
    filter_sottocategoria: Optional[str] = None,
    filter_mittente: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista tutti i documenti nel RAG con paginazione.

    Parametri:
    - limit: Numero massimo documenti (default: 50, max: 200)
    - offset: Offset per paginazione (default: 0)
    - filter_categoria: Filtra per categoria (opzionale)
    - filter_sottocategoria: Filtra per sottocategoria (opzionale)
    - filter_mittente: Filtra per mittente (opzionale)

    Returns:
        Lista documenti con metadati
    """
    rag_service = get_rag_service()

    # Costruisci filtri
    filter_metadata = {}
    if filter_categoria:
        filter_metadata['categoria'] = filter_categoria
    if filter_sottocategoria:
        filter_metadata['sottocategoria'] = filter_sottocategoria
    if filter_mittente:
        filter_metadata['mittente'] = filter_mittente

    result = rag_service.list_documents(
        limit=limit,
        offset=offset,
        filter_metadata=filter_metadata if filter_metadata else None
    )

    return result


@router.put("/document/{document_id}/metadata")
def update_document_metadata(
    document_id: str,
    request: UpdateMetadataRequest,
    db: Session = Depends(get_db)
):
    """
    Aggiorna i metadati di un documento.

    Parametri:
    - document_id: ID del documento
    - metadata: Nuovi metadati

    Returns:
        Esito operazione
    """
    rag_service = get_rag_service()

    success = rag_service.update_document_metadata(
        document_id=request.document_id,
        new_metadata=request.metadata
    )

    if success:
        return {
            "success": True,
            "document_id": request.document_id,
            "message": "Metadati aggiornati con successo"
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Documento {request.document_id} non trovato"
        )


@router.delete("/document/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Elimina un documento dal RAG.

    Parametri:
    - document_id: ID del documento

    Returns:
        Esito operazione
    """
    rag_service = get_rag_service()

    success = rag_service.delete_document(document_id)

    if success:
        return {
            "success": True,
            "document_id": document_id,
            "message": "Documento eliminato con successo"
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Documento {document_id} non trovato o errore eliminazione"
        )


@router.post("/query", response_model=QueryResponse)
def query_rag(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Esegue una query sul RAG.

    Parametri:
    - query: Testo della query
    - n_results: Numero risultati (default: 5)
    - filter_categoria: Filtra per categoria (opzionale)
    - filter_sottocategoria: Filtra per sottocategoria (opzionale)
    - filter_mittente: Filtra per mittente (opzionale)

    Returns:
        Risultati query con documenti e metadati
    """
    rag_service = get_rag_service()

    # Costruisci filtri metadati
    filter_metadata = {}
    if request.filter_categoria:
        filter_metadata['categoria'] = request.filter_categoria
    if request.filter_sottocategoria:
        filter_metadata['sottocategoria'] = request.filter_sottocategoria
    if request.filter_mittente:
        filter_metadata['mittente'] = request.filter_mittente

    # Esegui query
    result = rag_service.query(
        query_text=request.query,
        n_results=request.n_results,
        filter_metadata=filter_metadata if filter_metadata else None
    )

    return QueryResponse(**result)


@router.post("/chat", response_model=ChatResponse)
def chat_rag(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Esegue una query conversazionale sul RAG con generazione risposta LLM.

    Parametri:
    - query: Domanda dell'utente
    - n_results: Numero documenti da recuperare (default: 5)
    - filter_categoria: Filtra per categoria (opzionale)
    - filter_sottocategoria: Filtra per sottocategoria (opzionale)
    - filter_mittente: Filtra per mittente (opzionale)
    - use_openai: Se True, usa OpenAI invece di Ollama
    - max_context_docs: Numero max documenti nel contesto (default: 4)
    - max_doc_length: Lunghezza max per documento nel contesto (default: 1500)

    Returns:
        Risposta generata dal LLM con fonti
    """
    rag_service = get_rag_service()

    # Costruisci filtri metadati
    filter_metadata = {}
    if request.filter_categoria:
        filter_metadata['categoria'] = request.filter_categoria
    if request.filter_sottocategoria:
        filter_metadata['sottocategoria'] = request.filter_sottocategoria
    if request.filter_mittente:
        filter_metadata['mittente'] = request.filter_mittente

    # Esegui chat con RAG
    result = rag_service.chat(
        query_text=request.query,
        n_results=request.n_results,
        filter_metadata=filter_metadata if filter_metadata else None,
        use_openai=request.use_openai,
        max_context_docs=request.max_context_docs,
        max_doc_length=request.max_doc_length
    )

    return ChatResponse(**result)


@router.post("/index-email", response_model=IndexEmailResponse)
def index_email(
    request: IndexEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Indicizza manualmente un'email nel RAG.

    Parametri:
    - email_id: ID email da indicizzare

    Returns:
        Statistiche indicizzazione
    """
    rag_service = get_rag_service()

    # Trova email
    email = db.query(Email).filter(Email.id == request.email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail=f"Email {request.email_id} non trovata")

    # Indicizza
    result = rag_service.index_email(email, db)

    if result['indexed']:
        return IndexEmailResponse(
            indexed=True,
            email_id=request.email_id,
            documents_indexed=result['documents_indexed'],
            total_documents=result['total_documents'],
            errors=result.get('errors', [])
        )
    else:
        return IndexEmailResponse(
            indexed=False,
            email_id=request.email_id,
            documents_indexed=0,
            total_documents=result.get('total_documents', 0),
            errors=[result.get('reason', 'Unknown')]
        )


@router.delete("/email/{email_id}")
def delete_email_documents(
    email_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina tutti i documenti di un'email dal RAG.

    Parametri:
    - email_id: ID email

    Returns:
        Numero documenti eliminati
    """
    rag_service = get_rag_service()

    deleted_count = rag_service.delete_email_documents(email_id)

    return {
        "email_id": email_id,
        "deleted_count": deleted_count,
        "success": True
    }


@router.get("/statistics", response_model=StatisticsResponse)
def get_statistics(db: Session = Depends(get_db)):
    """
    Restituisce statistiche sul RAG.

    Returns:
        Statistiche collection
    """
    rag_service = get_rag_service()

    stats = rag_service.get_statistics()

    return StatisticsResponse(**stats)


@router.post("/reset")
def reset_collection(
    confirm: str = Query(..., description="Scrivi 'RESET_RAG_CONFIRM_DELETE_ALL' per confermare"),
    admin_key: str = Query(None, description="Chiave amministratore (opzionale per sicurezza aggiuntiva)"),
    db: Session = Depends(get_db)
):
    """
    Reset completo della collection RAG (elimina tutti i dati).

    ATTENZIONE: Operazione irreversibile!

    Parametri:
    - confirm: Deve essere esattamente 'RESET_RAG_CONFIRM_DELETE_ALL'
    - admin_key: Chiave opzionale per sicurezza aggiuntiva

    Returns:
        Esito operazione
    """
    import os

    REQUIRED_CONFIRM = "RESET_RAG_CONFIRM_DELETE_ALL"

    if confirm != REQUIRED_CONFIRM:
        raise HTTPException(
            status_code=400,
            detail=f"Conferma non valida. Scrivi esattamente: {REQUIRED_CONFIRM}"
        )

    # Opzionale: verifica admin key se configurata
    expected_admin_key = os.getenv('RAG_ADMIN_KEY')
    if expected_admin_key and admin_key != expected_admin_key:
        raise HTTPException(
            status_code=403,
            detail="Chiave amministratore non valida"
        )

    rag_service = get_rag_service()

    # Log dell'operazione pericolosa
    logger.warning(f"⚠️ RAG RESET richiesto. Tutti i documenti verranno eliminati!")

    success = rag_service.reset_collection()

    if success:
        logger.warning("✅ RAG collection resettata con successo")
    else:
        logger.error("❌ Errore durante reset RAG collection")

    return {
        "success": success,
        "message": "RAG collection resettata - Tutti i documenti sono stati eliminati" if success else "Errore reset collection"
    }
