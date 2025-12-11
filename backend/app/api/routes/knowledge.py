"""
API endpoints per Knowledge Base - Upload e gestione documenti manuali
"""
import os
import logging
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.database import get_db
from app.models.knowledge_document import KnowledgeDocument, TipoDocumento
from app.services.rag_service import get_rag_service
from app.services.attachment_extractor import get_attachment_extractor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload")
async def upload_knowledge_document(
    file: UploadFile = File(...),
    titolo: str = Form(...),
    descrizione: Optional[str] = Form(None),
    tipo_documento: str = Form(...),
    categoria_email: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated
    ente_emittente: Optional[str] = Form(None),
    data_emissione: Optional[str] = Form(None),  # YYYY-MM-DD
    numero_protocollo: Optional[str] = Form(None),
    anno_riferimento: Optional[str] = Form(None),
    caricato_da: Optional[str] = Form("admin"),
    note_interne: Optional[str] = Form(None),
    indicizza_subito: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Upload un documento nella Knowledge Base.

    Il documento viene:
    1. Salvato su disco in storage/knowledge/
    2. Elaborato per estrarre il testo
    3. Inserito nel database
    4. Opzionalmente indicizzato nel RAG
    """
    try:
        logger.info(f"📤 Upload documento knowledge: {titolo}")

        # === SECURITY VALIDATIONS ===
        # 1. Validate file size (max 50MB)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        file_size = len(file_content)
        await file.seek(0)  # Reset file pointer

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File troppo grande: {file_size / 1024 / 1024:.1f}MB (max 50MB)"
            )

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File vuoto non ammesso"
            )

        # 2. Validate file extension
        ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.rtf', '.odt', '.eml', '.msg'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Estensione file non ammessa: {file_extension}. Ammesse: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # 3. Validate content type
        ALLOWED_CONTENT_TYPES = {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'application/rtf',
            'application/vnd.oasis.opendocument.text',
            'message/rfc822',
            'application/vnd.ms-outlook'
        }
        if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
            logger.warning(f"Content type non standard: {file.content_type}")
            # Non blocchiamo, ma logghiamo

        # 4. Validate filename (no path traversal)
        if '..' in file.filename or '/' in file.filename or '\\' in file.filename:
            raise HTTPException(
                status_code=400,
                detail="Nome file non valido"
            )

        # 5. Validate titolo length
        if len(titolo) < 3:
            raise HTTPException(
                status_code=400,
                detail="Titolo troppo corto (minimo 3 caratteri)"
            )
        if len(titolo) > 500:
            raise HTTPException(
                status_code=400,
                detail="Titolo troppo lungo (massimo 500 caratteri)"
            )

        # === END SECURITY VALIDATIONS ===

        # Valida tipo documento
        try:
            tipo_doc = TipoDocumento(tipo_documento)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo documento non valido: {tipo_documento}"
            )

        # Crea directory storage se non esiste
        storage_dir = "storage/knowledge"
        os.makedirs(storage_dir, exist_ok=True)

        # Genera nome file univoco
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(storage_dir, safe_filename)

        # Salva file su disco
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)
        logger.info(f"✅ File salvato: {file_path} ({file_size} bytes)")

        # Estrai testo dal documento
        extractor = get_attachment_extractor()
        testo_estratto = None
        try:
            testo_estratto = extractor.extract_text(file_path)
            if testo_estratto:
                logger.info(f"✅ Testo estratto: {len(testo_estratto)} caratteri")
        except Exception as e:
            logger.warning(f"⚠️ Impossibile estrarre testo: {e}")

        # Parse tags
        tags_list = []
        if tags:
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]

        # Parse data emissione
        data_emissione_obj = None
        if data_emissione:
            try:
                data_emissione_obj = datetime.strptime(data_emissione, "%Y-%m-%d").date()
            except:
                logger.warning(f"⚠️ Data emissione non valida: {data_emissione}")

        # Crea record database
        documento = KnowledgeDocument(
            titolo=titolo,
            descrizione=descrizione,
            file_path=file_path,
            file_name=file.filename,
            file_size=file_size,
            file_type=file.content_type,
            tipo_documento=tipo_doc,
            categoria_email=categoria_email,
            tags=tags_list,
            ente_emittente=ente_emittente,
            data_emissione=data_emissione_obj,
            numero_protocollo=numero_protocollo,
            anno_riferimento=anno_riferimento,
            testo_estratto=testo_estratto,
            testo_length=len(testo_estratto) if testo_estratto else 0,
            caricato_da=caricato_da,
            note_interne=note_interne,
            attivo=True,
            verificato=False
        )

        db.add(documento)
        db.commit()
        db.refresh(documento)

        logger.info(f"✅ Documento salvato nel database: ID {documento.id}")

        # Indicizza nel RAG se richiesto
        if indicizza_subito and testo_estratto:
            try:
                rag_service = get_rag_service()
                result = rag_service.index_knowledge_document(documento)

                if result.get('indexed'):
                    documento.indexed_in_rag = True
                    documento.rag_document_ids = result.get('document_ids', [])
                    documento.rag_indexed_at = datetime.now()
                    db.commit()
                    logger.info(f"✅ Documento indicizzato nel RAG: {len(result.get('document_ids', []))} chunks")

            except Exception as e:
                logger.error(f"❌ Errore indicizzazione RAG: {e}")
                # Non fail hard, documento già salvato

        return {
            "status": "success",
            "message": "Documento caricato con successo",
            "documento": {
                "id": documento.id,
                "titolo": documento.titolo,
                "file_name": documento.file_name,
                "tipo_documento": documento.tipo_documento.value,
                "tags": documento.tags,
                "indexed_in_rag": documento.indexed_in_rag,
                "testo_length": documento.testo_length
            }
        }

    except Exception as e:
        logger.error(f"❌ Errore upload documento: {e}", exc_info=True)

        # Cleanup file se errore
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

        raise HTTPException(
            status_code=500,
            detail=f"Errore upload documento: {str(e)}"
        )


@router.get("/documents")
def list_knowledge_documents(
    tipo_documento: Optional[str] = Query(None),
    categoria_email: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    ente_emittente: Optional[str] = Query(None),
    solo_attivi: bool = Query(True),
    skip: int = Query(0),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    """Lista documenti knowledge base con filtri"""
    query = db.query(KnowledgeDocument)

    if solo_attivi:
        query = query.filter(KnowledgeDocument.attivo == True)

    if tipo_documento:
        query = query.filter(KnowledgeDocument.tipo_documento == tipo_documento)

    if categoria_email:
        query = query.filter(KnowledgeDocument.categoria_email == categoria_email)

    if ente_emittente:
        query = query.filter(KnowledgeDocument.ente_emittente.ilike(f"%{ente_emittente}%"))

    # Filtro tags (cerca nei JSON)
    if tags:
        # TODO: Implementare ricerca JSON tags
        pass

    total = query.count()
    documenti = query.order_by(KnowledgeDocument.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "documenti": [
            {
                "id": doc.id,
                "titolo": doc.titolo,
                "tipo_documento": doc.tipo_documento.value,
                "categoria_email": doc.categoria_email,
                "tags": doc.tags,
                "ente_emittente": doc.ente_emittente,
                "data_emissione": doc.data_emissione.isoformat() if doc.data_emissione else None,
                "file_name": doc.file_name,
                "file_size_mb": doc.file_size_mb,
                "indexed_in_rag": doc.indexed_in_rag,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "caricato_da": doc.caricato_da,
                "verificato": doc.verificato,
                "attivo": doc.attivo
            }
            for doc in documenti
        ]
    }


@router.get("/documents/{documento_id}")
def get_knowledge_document(
    documento_id: int,
    db: Session = Depends(get_db)
):
    """Ottieni dettagli documento singolo"""
    documento = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.id == documento_id
    ).first()

    if not documento:
        raise HTTPException(status_code=404, detail="Documento non trovato")

    return {
        "id": documento.id,
        "titolo": documento.titolo,
        "descrizione": documento.descrizione,
        "tipo_documento": documento.tipo_documento.value,
        "categoria_email": documento.categoria_email,
        "tags": documento.tags,
        "ente_emittente": documento.ente_emittente,
        "data_emissione": documento.data_emissione.isoformat() if documento.data_emissione else None,
        "numero_protocollo": documento.numero_protocollo,
        "anno_riferimento": documento.anno_riferimento,
        "file_name": documento.file_name,
        "file_path": documento.file_path,
        "file_size": documento.file_size,
        "file_size_mb": documento.file_size_mb,
        "file_type": documento.file_type,
        "testo_length": documento.testo_length,
        "indexed_in_rag": documento.indexed_in_rag,
        "rag_document_ids": documento.rag_document_ids,
        "rag_indexed_at": documento.rag_indexed_at.isoformat() if documento.rag_indexed_at else None,
        "created_at": documento.created_at.isoformat() if documento.created_at else None,
        "updated_at": documento.updated_at.isoformat() if documento.updated_at else None,
        "caricato_da": documento.caricato_da,
        "note_interne": documento.note_interne,
        "attivo": documento.attivo,
        "verificato": documento.verificato
    }


@router.delete("/documents/{documento_id}")
def delete_knowledge_document(
    documento_id: int,
    db: Session = Depends(get_db)
):
    """Elimina documento knowledge (soft delete)"""
    documento = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.id == documento_id
    ).first()

    if not documento:
        raise HTTPException(status_code=404, detail="Documento non trovato")

    # Soft delete
    documento.attivo = False
    db.commit()

    logger.info(f"🗑️ Documento {documento_id} disattivato")

    return {
        "status": "success",
        "message": "Documento disattivato"
    }


@router.post("/documents/{documento_id}/index")
def index_document_in_rag(
    documento_id: int,
    db: Session = Depends(get_db)
):
    """Indicizza/reindicizza documento nel RAG"""
    documento = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.id == documento_id
    ).first()

    if not documento:
        raise HTTPException(status_code=404, detail="Documento non trovato")

    if not documento.testo_estratto:
        raise HTTPException(status_code=400, detail="Nessun testo estratto da indicizzare")

    try:
        rag_service = get_rag_service()
        result = rag_service.index_knowledge_document(documento)

        if result.get('indexed'):
            documento.indexed_in_rag = True
            documento.rag_document_ids = result.get('document_ids', [])
            documento.rag_indexed_at = datetime.now()
            db.commit()

            logger.info(f"✅ Documento {documento_id} indicizzato: {len(result.get('document_ids', []))} chunks")

            return {
                "status": "success",
                "message": "Documento indicizzato con successo",
                "chunks_indexed": len(result.get('document_ids', []))
            }
        else:
            raise HTTPException(status_code=500, detail="Indicizzazione fallita")

    except Exception as e:
        logger.error(f"❌ Errore indicizzazione: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def get_knowledge_stats(db: Session = Depends(get_db)):
    """Statistiche knowledge base"""
    total_docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.attivo == True).count()
    total_indexed = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.attivo == True,
        KnowledgeDocument.indexed_in_rag == True
    ).count()

    # Count by tipo
    by_tipo = {}
    for tipo in TipoDocumento:
        count = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tipo_documento == tipo,
            KnowledgeDocument.attivo == True
        ).count()
        by_tipo[tipo.value] = count

    return {
        "total_documenti": total_docs,
        "indicizzati_in_rag": total_indexed,
        "by_tipo": by_tipo
    }
