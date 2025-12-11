"""
API Routes per gestione Azioni.

FASE 6: API Complete per Frontend
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.azione import Azione, TipoAzione, StatoAzione
from app.services.action_executor import ActionExecutor
from app.services.email_processor import EmailProcessorService

router = APIRouter(prefix="/azioni", tags=["azioni"])


@router.get("/")
def list_azioni(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    email_id: Optional[int] = None,
    tipo_azione: Optional[str] = None,
    stato: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista azioni con filtri e paginazione.

    - **skip**: Numero azioni da saltare
    - **limit**: Numero massimo azioni da restituire
    - **email_id**: Filtra per email specifica
    - **tipo_azione**: Filtra per tipo azione
    - **stato**: Filtra per stato
    """
    query = db.query(Azione)

    if email_id:
        query = query.filter(Azione.email_id == email_id)

    if tipo_azione:
        try:
            tipo_enum = TipoAzione(tipo_azione)
            query = query.filter(Azione.tipo == tipo_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Tipo azione non valido: {tipo_azione}")

    if stato:
        try:
            stato_enum = StatoAzione(stato)
            query = query.filter(Azione.stato == stato_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Stato non valido: {stato}")

    total = query.count()
    azioni = query.order_by(desc(Azione.timestamp_inizio)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "azioni": azioni
    }


@router.get("/{azione_id}")
def get_azione(azione_id: int, db: Session = Depends(get_db)):
    """Recupera dettagli azione singola."""
    azione = db.query(Azione).filter(Azione.id == azione_id).first()

    if not azione:
        raise HTTPException(status_code=404, detail="Azione non trovata")

    return azione


@router.post("/{azione_id}/execute")
def execute_azione(azione_id: int, db: Session = Depends(get_db)):
    """
    Esegue manualmente un'azione.

    Utile per eseguire azioni pending o ritentare azioni fallite.
    """
    executor = ActionExecutor(db)

    try:
        success = executor.execute_action(azione_id)

        if success:
            return {"message": "Azione eseguita con successo", "azione_id": azione_id}
        else:
            raise HTTPException(status_code=500, detail="Esecuzione azione fallita")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore esecuzione: {str(e)}")


@router.post("/{azione_id}/retry")
def retry_azione(azione_id: int, db: Session = Depends(get_db)):
    """
    Ritenta un'azione fallita.

    Resetta lo stato a PENDING e la reinserisce nella coda.
    """
    azione = db.query(Azione).filter(Azione.id == azione_id).first()

    if not azione:
        raise HTTPException(status_code=404, detail="Azione non trovata")

    if azione.stato != StatoAzione.FALLITA:
        raise HTTPException(status_code=400, detail="Solo azioni fallite possono essere ritentate")

    # Resetta stato
    azione.stato = StatoAzione.IN_CODA
    azione.errore = None
    db.commit()

    return {"message": "Azione reinserita in coda", "azione_id": azione_id}


@router.delete("/{azione_id}")
def delete_azione(azione_id: int, db: Session = Depends(get_db)):
    """Elimina azione."""
    azione = db.query(Azione).filter(Azione.id == azione_id).first()

    if not azione:
        raise HTTPException(status_code=404, detail="Azione non trovata")

    db.delete(azione)
    db.commit()

    return {"message": "Azione eliminata"}


@router.get("/stats/summary")
def get_azioni_stats(db: Session = Depends(get_db)):
    """
    Statistiche azioni.

    Restituisce conteggi per stato e tipo.
    """
    from sqlalchemy import func

    # Conta per stato
    stati = db.query(
        Azione.stato,
        func.count(Azione.id).label('count')
    ).group_by(Azione.stato).all()

    # Conta per tipo
    tipi = db.query(
        Azione.tipo,
        func.count(Azione.id).label('count')
    ).group_by(Azione.tipo).all()

    return {
        "stati": [{"stato": s.stato.value, "count": s.count} for s in stati],
        "tipi": [{"tipo": t.tipo.value, "count": t.count} for t in tipi],
        "total": db.query(Azione).count()
    }


@router.post("/process-email/{email_id}")
def process_email(email_id: int, db: Session = Depends(get_db)):
    """
    Processa manualmente un'email: applica regole e crea azioni.

    Restituisce un log dettagliato di tutto il processo per debug.

    USAGE: Usare questo endpoint per testare il processamento delle email.
    Il log contiene tutti gli step del ragionamento.
    """
    processor = EmailProcessorService(db)
    result = processor.process_email(email_id)

    if not result['success']:
        raise HTTPException(status_code=400, detail={
            "error": result.get('error'),
            "log": result.get('log', [])
        })

    return result


@router.get("/reports/daily")
def get_daily_reports(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Report giornalieri delle attività.

    Restituisce un riepilogo giornaliero di:
    - Email processate
    - Azioni eseguite per tipo
    - Eventi calendario creati
    """
    from sqlalchemy import func, cast, Date
    from datetime import datetime, timedelta
    from app.models.email import Email
    from app.models.evento import EventoCalendario

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Raggruppa azioni per giorno
    azioni_per_giorno = db.query(
        func.date(Azione.timestamp_inizio).label('data'),
        Azione.tipo,
        Azione.stato,
        func.count(Azione.id).label('count')
    ).filter(
        Azione.timestamp_inizio >= start_date
    ).group_by(
        func.date(Azione.timestamp_inizio),
        Azione.tipo,
        Azione.stato
    ).all()

    # Raggruppa email per giorno
    email_per_giorno = db.query(
        func.date(Email.data_ricezione).label('data'),
        func.count(Email.id).label('count')
    ).filter(
        Email.data_ricezione >= start_date
    ).group_by(
        func.date(Email.data_ricezione)
    ).all()

    # Raggruppa eventi creati per giorno
    eventi_per_giorno = db.query(
        func.date(EventoCalendario.created_at).label('data'),
        func.count(EventoCalendario.id).label('count')
    ).filter(
        EventoCalendario.created_at >= start_date
    ).group_by(
        func.date(EventoCalendario.created_at)
    ).all()

    # Costruisci report strutturato per giorno
    reports = {}

    for row in azioni_per_giorno:
        data_str = str(row.data)
        if data_str not in reports:
            reports[data_str] = {
                'data': data_str,
                'email_ricevute': 0,
                'eventi_creati': 0,
                'azioni': {},
                'totale_azioni': 0,
                'azioni_completate': 0,
                'azioni_fallite': 0
            }

        tipo = row.tipo.value if hasattr(row.tipo, 'value') else str(row.tipo)
        stato = row.stato.value if hasattr(row.stato, 'value') else str(row.stato)

        if tipo not in reports[data_str]['azioni']:
            reports[data_str]['azioni'][tipo] = {'completate': 0, 'fallite': 0, 'in_coda': 0, 'totale': 0}

        reports[data_str]['azioni'][tipo]['totale'] += row.count
        reports[data_str]['totale_azioni'] += row.count

        if stato == 'COMPLETATA':
            reports[data_str]['azioni'][tipo]['completate'] += row.count
            reports[data_str]['azioni_completate'] += row.count
        elif stato == 'FALLITA':
            reports[data_str]['azioni'][tipo]['fallite'] += row.count
            reports[data_str]['azioni_fallite'] += row.count
        elif stato == 'IN_CODA':
            reports[data_str]['azioni'][tipo]['in_coda'] += row.count

    for row in email_per_giorno:
        data_str = str(row.data)
        if data_str not in reports:
            reports[data_str] = {
                'data': data_str,
                'email_ricevute': 0,
                'eventi_creati': 0,
                'azioni': {},
                'totale_azioni': 0,
                'azioni_completate': 0,
                'azioni_fallite': 0
            }
        reports[data_str]['email_ricevute'] = row.count

    for row in eventi_per_giorno:
        data_str = str(row.data)
        if data_str not in reports:
            reports[data_str] = {
                'data': data_str,
                'email_ricevute': 0,
                'eventi_creati': 0,
                'azioni': {},
                'totale_azioni': 0,
                'azioni_completate': 0,
                'azioni_fallite': 0
            }
        reports[data_str]['eventi_creati'] = row.count

    # Ordina per data decrescente
    sorted_reports = sorted(reports.values(), key=lambda x: x['data'], reverse=True)

    return {
        'reports': sorted_reports,
        'periodo': {
            'inizio': start_date.isoformat(),
            'fine': end_date.isoformat(),
            'giorni': days
        }
    }


@router.get("/reports/summaries")
def get_email_summaries(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Lista delle sintesi email generate.

    Restituisce le azioni SINTESI completate con il testo generato.
    """
    from datetime import datetime, timedelta
    from app.models.email import Email

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Query sintesi completate
    sintesi_azioni = db.query(Azione).filter(
        Azione.tipo == TipoAzione.SINTESI,
        Azione.stato == StatoAzione.COMPLETATA,
        Azione.timestamp_inizio >= start_date
    ).order_by(desc(Azione.timestamp_inizio)).limit(limit).all()

    result = []
    for azione in sintesi_azioni:
        email = db.query(Email).filter(Email.id == azione.email_id).first()
        if email:
            sintesi_testo = None
            if azione.risultato and isinstance(azione.risultato, dict):
                sintesi_testo = azione.risultato.get('sintesi')

            result.append({
                'id': azione.id,
                'email_id': email.id,
                'email_oggetto': email.oggetto,
                'email_mittente': email.mittente,
                'email_data': email.data_ricezione.isoformat() if email.data_ricezione else None,
                'sintesi': sintesi_testo or email.note,
                'created_at': azione.timestamp_inizio.isoformat() if azione.timestamp_inizio else None
            })

    return {
        'summaries': result,
        'total': len(result),
        'periodo': {
            'inizio': start_date.isoformat(),
            'fine': end_date.isoformat(),
            'giorni': days
        }
    }


@router.get("/reports/forwards")
def get_forwarding_report(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Report degli inoltri effettuati.

    Mostra email inoltrate ai delegati con dettagli su destinatari e stato.
    """
    from datetime import datetime, timedelta
    from app.models.email import Email

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Query inoltri
    inoltri = db.query(Azione).filter(
        Azione.tipo.in_([TipoAzione.INOLTRA, TipoAzione.INOLTRA_DELEGATI_ZONA]),
        Azione.timestamp_inizio >= start_date
    ).order_by(desc(Azione.timestamp_inizio)).all()

    result = []
    for azione in inoltri:
        email = db.query(Email).filter(Email.id == azione.email_id).first()
        if not email:
            continue

        # Estrai info dal risultato
        risultato = azione.risultato or {}
        delegati_lista = risultato.get('delegati_lista', [])
        zona = risultato.get('zona', '')
        scuola = risultato.get('scuola', '')
        status = risultato.get('status', 'unknown')
        error = risultato.get('error', azione.errore)

        result.append({
            'id': azione.id,
            'email_id': email.id,
            'email_oggetto': email.oggetto,
            'email_mittente': email.mittente,
            'email_data': email.data_ricezione.isoformat() if email.data_ricezione else None,
            'stato': azione.stato.value,
            'status': status,
            'zona': zona,
            'scuola': scuola,
            'delegati': delegati_lista,
            'delegati_count': len(delegati_lista),
            'error': error,
            'requires_attention': status == 'manual_intervention_required' or azione.stato == StatoAzione.FALLITA,
            'timestamp': azione.timestamp_inizio.isoformat() if azione.timestamp_inizio else None
        })

    # Statistiche
    completati = sum(1 for r in result if r['stato'] == 'COMPLETATA')
    falliti = sum(1 for r in result if r['stato'] == 'FALLITA')
    richiede_attenzione = sum(1 for r in result if r['requires_attention'])

    return {
        'forwards': result,
        'stats': {
            'totale': len(result),
            'completati': completati,
            'falliti': falliti,
            'richiede_attenzione': richiede_attenzione
        },
        'periodo': {
            'inizio': start_date.isoformat(),
            'fine': end_date.isoformat(),
            'giorni': days
        }
    }


@router.get("/reports/issues")
def get_issues_report(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Report anomalie e problemi che richiedono attenzione.

    Include:
    - Azioni fallite
    - Inoltri che richiedono intervento manuale
    - Email non processate
    """
    from datetime import datetime, timedelta
    from app.models.email import Email

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    issues = []

    # 1. Azioni fallite
    azioni_fallite = db.query(Azione).filter(
        Azione.stato == StatoAzione.FALLITA,
        Azione.timestamp_inizio >= start_date
    ).order_by(desc(Azione.timestamp_inizio)).all()

    for azione in azioni_fallite:
        email = db.query(Email).filter(Email.id == azione.email_id).first()
        risultato = azione.risultato or {}

        issues.append({
            'tipo': 'azione_fallita',
            'severity': 'error',
            'azione_id': azione.id,
            'azione_tipo': azione.tipo.value,
            'email_id': email.id if email else None,
            'email_oggetto': email.oggetto if email else None,
            'email_mittente': email.mittente if email else None,
            'errore': azione.errore or risultato.get('error'),
            'messaggio': risultato.get('message'),
            'timestamp': azione.timestamp_inizio.isoformat() if azione.timestamp_inizio else None,
            'dettagli': risultato
        })

    # 2. Inoltri che richiedono intervento manuale
    inoltri_manuali = db.query(Azione).filter(
        Azione.tipo.in_([TipoAzione.INOLTRA, TipoAzione.INOLTRA_DELEGATI_ZONA]),
        Azione.timestamp_inizio >= start_date
    ).all()

    for azione in inoltri_manuali:
        risultato = azione.risultato or {}
        if risultato.get('status') == 'manual_intervention_required':
            email = db.query(Email).filter(Email.id == azione.email_id).first()
            issues.append({
                'tipo': 'intervento_richiesto',
                'severity': 'warning',
                'azione_id': azione.id,
                'azione_tipo': azione.tipo.value,
                'email_id': email.id if email else None,
                'email_oggetto': email.oggetto if email else None,
                'email_mittente': email.mittente if email else None,
                'errore': risultato.get('error'),
                'messaggio': risultato.get('message'),
                'timestamp': azione.timestamp_inizio.isoformat() if azione.timestamp_inizio else None,
                'dettagli': risultato.get('school_info', {})
            })

    # Ordina per timestamp (più recenti prima)
    issues.sort(key=lambda x: x.get('timestamp') or '', reverse=True)

    return {
        'issues': issues,
        'stats': {
            'totale': len(issues),
            'errori': sum(1 for i in issues if i['severity'] == 'error'),
            'warning': sum(1 for i in issues if i['severity'] == 'warning')
        },
        'periodo': {
            'inizio': start_date.isoformat(),
            'fine': end_date.isoformat(),
            'giorni': days
        }
    }


@router.get("/reports/summaries-by-sender")
def get_summaries_by_sender(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Sintesi email raggruppate per mittente.
    """
    from datetime import datetime, timedelta
    from app.models.email import Email
    from collections import defaultdict
    import json
    import re

    # Carica database scuole per tradurre codici in nomi
    scuole_db = {}
    try:
        with open('/app/app/data/scuole_taranto.json', 'r') as f:
            scuole_db = json.load(f)
    except Exception:
        pass

    def get_school_name(codice: str) -> str:
        """Restituisce il nome della scuola dal codice meccanografico."""
        codice_upper = codice.upper()
        if codice_upper in scuole_db:
            return scuole_db[codice_upper].get('nome', codice)
        return codice

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Query email con sintesi
    emails = db.query(Email).filter(
        Email.data_ricezione >= start_date,
        Email.note.isnot(None),
        Email.note != ''
    ).order_by(desc(Email.data_ricezione)).all()

    # Raggruppa per mittente
    by_sender = defaultdict(list)
    for email in emails:
        # Normalizza mittente (estrai nome/dominio)
        mittente = email.mittente or 'Sconosciuto'
        # Semplifica il mittente per raggruppamento
        if '@' in mittente:
            # Estrai dominio o nome
            if '<' in mittente:
                nome = mittente.split('<')[0].strip().strip('"')
                if nome:
                    mittente_key = nome
                else:
                    mittente_key = mittente.split('<')[1].split('>')[0].split('@')[0]
            else:
                mittente_key = mittente.split('@')[0]
        else:
            mittente_key = mittente

        # Se sembra un codice meccanografico (es. taic845002, tapc070005), converti in nome scuola
        if re.match(r'^ta[a-z]{2}\d{5,6}[a-z]?$', mittente_key.lower()):
            mittente_key = get_school_name(mittente_key)
        # Gestisci anche "Per conto di: codice@pec.istruzione.it"
        elif mittente_key.startswith('Per conto di:'):
            match = re.search(r'(ta[a-z]{2}\d{5,6}[a-z]?)@', mittente_key.lower())
            if match:
                codice = match.group(1)
                nome_scuola = get_school_name(codice)
                mittente_key = f"Per conto di: {nome_scuola}"

        by_sender[mittente_key].append({
            'email_id': email.id,
            'oggetto': email.oggetto,
            'data': email.data_ricezione.isoformat() if email.data_ricezione else None,
            'sintesi': email.note,
            'categoria': email.get_categoria_value(),
            'mittente_completo': email.mittente
        })

    # Converti in lista ordinata per numero di email
    result = []
    for mittente, emails_list in sorted(by_sender.items(), key=lambda x: -len(x[1])):
        result.append({
            'mittente': mittente,
            'mittente_completo': emails_list[0]['mittente_completo'] if emails_list else '',
            'count': len(emails_list),
            'emails': emails_list
        })

    return {
        'senders': result,
        'stats': {
            'totale_mittenti': len(result),
            'totale_email': sum(s['count'] for s in result)
        },
        'periodo': {
            'inizio': start_date.isoformat(),
            'fine': end_date.isoformat(),
            'giorni': days
        }
    }


# ==============================================================================
# WORKFLOW RISOLUZIONE ANOMALIE
# ==============================================================================

@router.get("/issues/{azione_id}/details")
def get_issue_details(azione_id: int, db: Session = Depends(get_db)):
    """
    Ottiene dettagli completi di un'anomalia per la risoluzione.

    Restituisce:
    - Info azione (tipo, stato, errore)
    - Email completa (corpo, allegati)
    - Dati estratti automaticamente
    - Schema dei campi richiesti per risolvere
    """
    from app.models.email import Email

    azione = db.query(Azione).filter(Azione.id == azione_id).first()
    if not azione:
        raise HTTPException(status_code=404, detail="Azione non trovata")

    email = db.query(Email).filter(Email.id == azione.email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email associata non trovata")

    # Costruisci dati estratti dal risultato/dettagli dell'azione
    risultato = azione.risultato or {}
    dettagli = azione.dettagli or {}

    # Dati già estratti dal sistema
    dati_estratti = {}
    campi_richiesti = []

    if azione.tipo == TipoAzione.EVENTO_CALENDARIO:
        # Per eventi calendario, estrai dati parsati
        dati_estratti = {
            'titolo': risultato.get('titolo') or dettagli.get('parametri', {}).get('titolo'),
            'data_inizio': risultato.get('data_inizio') or dettagli.get('parametri', {}).get('data_inizio'),
            'ora_inizio': risultato.get('ora_inizio') or dettagli.get('parametri', {}).get('ora_inizio'),
            'ora_fine': risultato.get('ora_fine') or dettagli.get('parametri', {}).get('ora_fine'),
            'luogo': risultato.get('luogo') or dettagli.get('parametri', {}).get('luogo'),
            'scuola': risultato.get('scuola') or dettagli.get('parametri', {}).get('scuola') or email.codice_scuola,
            'descrizione': risultato.get('descrizione') or email.oggetto,
        }

        # Determina quali campi mancano
        campi_richiesti = [
            {'campo': 'titolo', 'label': 'Titolo evento', 'tipo': 'text', 'obbligatorio': True,
             'mancante': not dati_estratti.get('titolo')},
            {'campo': 'data_inizio', 'label': 'Data', 'tipo': 'date', 'obbligatorio': True,
             'mancante': not dati_estratti.get('data_inizio')},
            {'campo': 'ora_inizio', 'label': 'Ora inizio', 'tipo': 'time', 'obbligatorio': True,
             'mancante': not dati_estratti.get('ora_inizio')},
            {'campo': 'ora_fine', 'label': 'Ora fine', 'tipo': 'time', 'obbligatorio': False,
             'mancante': not dati_estratti.get('ora_fine')},
            {'campo': 'luogo', 'label': 'Luogo', 'tipo': 'text', 'obbligatorio': False,
             'mancante': not dati_estratti.get('luogo')},
            {'campo': 'scuola', 'label': 'Scuola', 'tipo': 'text', 'obbligatorio': False,
             'mancante': not dati_estratti.get('scuola')},
        ]

    elif azione.tipo in [TipoAzione.INOLTRA, TipoAzione.INOLTRA_DELEGATI_ZONA]:
        # Per inoltri, mostra info zona/delegati
        dati_estratti = {
            'zona': risultato.get('zona'),
            'scuola': risultato.get('scuola'),
            'delegati_trovati': risultato.get('delegati_lista', []),
            'motivo_fallimento': risultato.get('error') or azione.errore,
        }
        campi_richiesti = [
            {'campo': 'destinatari', 'label': 'Destinatari email', 'tipo': 'email_list', 'obbligatorio': True,
             'mancante': len(risultato.get('delegati_lista', [])) == 0},
        ]

    elif azione.tipo == TipoAzione.BOZZA_RISPOSTA:
        dati_estratti = {
            'bozza_generata': risultato.get('draft'),
            'errore': risultato.get('error') or azione.errore,
        }
        campi_richiesti = []  # Per bozza si può solo rigenerare

    # Prepara allegati
    allegati_info = []
    if email.allegati_nomi:
        for i, nome in enumerate(email.allegati_nomi):
            path = email.allegati_path[i] if email.allegati_path and i < len(email.allegati_path) else None
            testo = None
            if email.allegati_testo and isinstance(email.allegati_testo, dict):
                testo = email.allegati_testo.get(nome)

            allegati_info.append({
                'filename': nome,
                'path': path,
                'testo_estratto': testo[:2000] if testo else None,  # Limita a 2000 caratteri
                'has_text': bool(testo)
            })

    return {
        'azione': {
            'id': azione.id,
            'tipo': azione.tipo.value,
            'stato': azione.stato.value,
            'errore': azione.errore,
            'messaggio': risultato.get('message'),
            'timestamp': azione.timestamp_inizio.isoformat() if azione.timestamp_inizio else None,
        },
        'email': {
            'id': email.id,
            'mittente': email.mittente,
            'oggetto': email.oggetto,
            'data': email.data_ricezione.isoformat() if email.data_ricezione else None,
            'corpo': email.corpo_testo or email.corpo,
            'corpo_html': email.corpo_html,
            'categoria': email.get_categoria_value(),
            'codice_scuola': email.codice_scuola,
        },
        'allegati': allegati_info,
        'dati_estratti': dati_estratti,
        'campi_richiesti': campi_richiesti,
        'risoluzione_disponibile': len(campi_richiesti) > 0 or azione.tipo == TipoAzione.BOZZA_RISPOSTA,
    }


@router.post("/issues/{azione_id}/resolve")
def resolve_issue(
    azione_id: int,
    dati: dict,
    db: Session = Depends(get_db)
):
    """
    Risolve un'anomalia con i dati forniti dall'utente.

    Body:
    - Per EVENTO_CALENDARIO: {titolo, data_inizio, ora_inizio, ora_fine?, luogo?, scuola?}
    - Per INOLTRA: {destinatari: ["email1", "email2"]}
    - Per BOZZA_RISPOSTA: {azione: "retry" | "skip"}
    """
    from datetime import datetime
    from app.models.email import Email
    from app.models.evento import EventoCalendario

    azione = db.query(Azione).filter(Azione.id == azione_id).first()
    if not azione:
        raise HTTPException(status_code=404, detail="Azione non trovata")

    email = db.query(Email).filter(Email.id == azione.email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email associata non trovata")

    # Handle diversi tipi di azione
    if azione.tipo == TipoAzione.EVENTO_CALENDARIO:
        return _resolve_evento_calendario(azione, email, dati, db)

    elif azione.tipo in [TipoAzione.INOLTRA, TipoAzione.INOLTRA_DELEGATI_ZONA]:
        return _resolve_inoltro(azione, email, dati, db)

    elif azione.tipo == TipoAzione.BOZZA_RISPOSTA:
        return _resolve_bozza(azione, email, dati, db)

    else:
        # Per altri tipi, prova retry generico
        if dati.get('azione') == 'retry':
            azione.stato = StatoAzione.IN_CODA
            azione.errore = None
            db.commit()
            return {"success": True, "message": "Azione reinserita in coda"}
        elif dati.get('azione') == 'skip':
            azione.stato = StatoAzione.COMPLETATA
            azione.risultato = azione.risultato or {}
            azione.risultato['skipped'] = True
            azione.risultato['skipped_at'] = datetime.now().isoformat()
            db.commit()
            return {"success": True, "message": "Azione saltata"}

        raise HTTPException(status_code=400, detail=f"Risoluzione non supportata per tipo {azione.tipo.value}")


def _resolve_evento_calendario(azione: Azione, email, dati: dict, db: Session):
    """Risolve un'azione EVENTO_CALENDARIO creando l'evento con i dati utente."""
    from datetime import datetime, timedelta
    from app.models.evento import EventoCalendario

    # Valida dati obbligatori
    if not dati.get('titolo'):
        raise HTTPException(status_code=400, detail="Titolo evento obbligatorio")
    if not dati.get('data_inizio'):
        raise HTTPException(status_code=400, detail="Data evento obbligatoria")
    if not dati.get('ora_inizio'):
        raise HTTPException(status_code=400, detail="Ora inizio obbligatoria")

    # Costruisci datetime
    try:
        data_str = dati['data_inizio']
        ora_str = dati['ora_inizio']

        # Parse data (formato YYYY-MM-DD o DD/MM/YYYY)
        if '-' in data_str:
            data_parts = data_str.split('-')
            if len(data_parts[0]) == 4:  # YYYY-MM-DD
                anno, mese, giorno = int(data_parts[0]), int(data_parts[1]), int(data_parts[2])
            else:  # DD-MM-YYYY
                giorno, mese, anno = int(data_parts[0]), int(data_parts[1]), int(data_parts[2])
        elif '/' in data_str:
            giorno, mese, anno = map(int, data_str.split('/'))
        else:
            raise ValueError(f"Formato data non riconosciuto: {data_str}")

        # Parse ora
        ora_parts = ora_str.replace('.', ':').split(':')
        ora = int(ora_parts[0])
        minuti = int(ora_parts[1]) if len(ora_parts) > 1 else 0

        data_inizio = datetime(anno, mese, giorno, ora, minuti)

        # Ora fine (default: +2 ore)
        if dati.get('ora_fine'):
            fine_parts = dati['ora_fine'].replace('.', ':').split(':')
            ora_fine = int(fine_parts[0])
            minuti_fine = int(fine_parts[1]) if len(fine_parts) > 1 else 0
            data_fine = datetime(anno, mese, giorno, ora_fine, minuti_fine)
        else:
            data_fine = data_inizio + timedelta(hours=2)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Errore parsing data/ora: {str(e)}")

    # Crea evento
    evento = EventoCalendario(
        email_id=email.id,
        titolo=dati['titolo'],
        descrizione=dati.get('descrizione') or email.oggetto,
        data_inizio=data_inizio,
        data_fine=data_fine,
        luogo=dati.get('luogo'),
        scuola=dati.get('scuola') or email.codice_scuola,
    )

    db.add(evento)

    # Aggiorna azione come completata
    azione.stato = StatoAzione.COMPLETATA
    azione.risultato = azione.risultato or {}
    azione.risultato['resolved_manually'] = True
    azione.risultato['resolved_at'] = datetime.now().isoformat()
    azione.risultato['evento_id'] = None  # Sarà aggiornato dopo commit

    db.commit()
    db.refresh(evento)

    # Aggiorna risultato con evento_id
    azione.risultato['evento_id'] = evento.id
    db.commit()

    return {
        "success": True,
        "message": f"Evento '{evento.titolo}' creato per {data_inizio.strftime('%d/%m/%Y %H:%M')}",
        "evento_id": evento.id
    }


def _resolve_inoltro(azione: Azione, email, dati: dict, db: Session):
    """Risolve un'azione INOLTRA con destinatari manuali."""
    from datetime import datetime

    destinatari = dati.get('destinatari', [])
    if not destinatari:
        if dati.get('azione') == 'skip':
            azione.stato = StatoAzione.COMPLETATA
            azione.risultato = azione.risultato or {}
            azione.risultato['skipped'] = True
            db.commit()
            return {"success": True, "message": "Inoltro saltato"}
        raise HTTPException(status_code=400, detail="Destinatari obbligatori per l'inoltro")

    # Esegui inoltro manuale
    try:
        from app.services.email_service import EmailService
        email_service = EmailService()

        # Prepara email di inoltro
        subject = f"Fwd: {email.oggetto}"
        body = f"""
<p>Email inoltrata dalla segreteria SNALS Taranto.</p>
<hr>
<p><strong>Da:</strong> {email.mittente}<br>
<strong>Data:</strong> {email.data_ricezione.strftime('%d/%m/%Y %H:%M') if email.data_ricezione else 'N/D'}<br>
<strong>Oggetto:</strong> {email.oggetto}</p>
<hr>
{email.corpo_html or email.corpo_testo or email.corpo or ''}
"""

        # Invia a tutti i destinatari
        for dest in destinatari:
            email_service.send_email(
                to=dest,
                subject=subject,
                body=body,
                html=True
            )

        azione.stato = StatoAzione.COMPLETATA
        azione.risultato = azione.risultato or {}
        azione.risultato['resolved_manually'] = True
        azione.risultato['manual_recipients'] = destinatari
        azione.risultato['resolved_at'] = datetime.now().isoformat()
        db.commit()

        return {
            "success": True,
            "message": f"Email inoltrata a {len(destinatari)} destinatari",
            "destinatari": destinatari
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore invio email: {str(e)}")


def _resolve_bozza(azione: Azione, email, dati: dict, db: Session):
    """Risolve un'azione BOZZA_RISPOSTA."""
    from datetime import datetime

    if dati.get('azione') == 'retry':
        # Reinserisci in coda per rigenerazione
        azione.stato = StatoAzione.IN_CODA
        azione.errore = None
        db.commit()
        return {"success": True, "message": "Bozza reinserita in coda per rigenerazione"}

    elif dati.get('azione') == 'skip':
        azione.stato = StatoAzione.COMPLETATA
        azione.risultato = azione.risultato or {}
        azione.risultato['skipped'] = True
        db.commit()
        return {"success": True, "message": "Generazione bozza saltata"}

    raise HTTPException(status_code=400, detail="Specificare azione: 'retry' o 'skip'")