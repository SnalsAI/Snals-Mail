"""
Dipendenze per autenticazione modulo Booking

STATO ATTUALE: Auth NON ATTIVA
Le funzioni restituiscono sempre None/True per permettere accesso.

PER ATTIVARE L'AUTH:
1. Implementare sistema JWT in auth_service.py
2. Modificare le funzioni qui sotto per verificare i token
3. Le route che usano queste dipendenze saranno automaticamente protette
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import BookingStaff

# Security scheme (preparato ma non usato attivamente)
security = HTTPBearer(auto_error=False)


async def get_current_staff(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[BookingStaff]:
    """
    Ottiene lo staff autenticato dal token JWT.

    STATO ATTUALE: Restituisce None (auth disabilitata)

    Quando auth attiva:
    1. Estrae token da header Authorization
    2. Decodifica JWT
    3. Cerca staff nel DB
    4. Ritorna BookingStaff o solleva 401

    Returns:
        BookingStaff se autenticato, None se auth disabilitata
    """
    # =========================================
    # AUTH DISABILITATA - Ritorna sempre None
    # =========================================
    return None

    # =========================================
    # CODICE PER QUANDO AUTH SARÀ ATTIVA:
    # =========================================
    # if not credentials:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Token mancante",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    #
    # try:
    #     # Decodifica token (implementare in auth_service)
    #     from app.services.booking.auth_service import decode_token
    #     payload = decode_token(credentials.credentials)
    #     staff_id = payload.get("staff_id")
    #
    #     if not staff_id:
    #         raise HTTPException(status_code=401, detail="Token non valido")
    #
    #     staff = db.query(BookingStaff).filter(
    #         BookingStaff.id == staff_id,
    #         BookingStaff.attivo == True
    #     ).first()
    #
    #     if not staff:
    #         raise HTTPException(status_code=401, detail="Staff non trovato")
    #
    #     return staff
    #
    # except Exception as e:
    #     raise HTTPException(status_code=401, detail=str(e))


async def get_current_admin(
    staff: Optional[BookingStaff] = Depends(get_current_staff),
) -> Optional[BookingStaff]:
    """
    Verifica che lo staff sia un admin.

    STATO ATTUALE: Restituisce None (auth disabilitata)

    Quando auth attiva:
    - Verifica ruolo admin dello staff
    - Solleva 403 se non autorizzato
    """
    # =========================================
    # AUTH DISABILITATA - Ritorna sempre None
    # =========================================
    return None

    # =========================================
    # CODICE PER QUANDO AUTH SARÀ ATTIVA:
    # =========================================
    # if not staff:
    #     raise HTTPException(status_code=401, detail="Non autenticato")
    #
    # # Verifica ruolo (es. controlla campo ruolo o tabella permessi)
    # if staff.ruolo != "admin":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Accesso riservato agli amministratori"
    #     )
    #
    # return staff


async def require_staff_auth(
    staff: Optional[BookingStaff] = Depends(get_current_staff),
) -> bool:
    """
    Dipendenza che richiede autenticazione staff.

    STATO ATTUALE: Restituisce sempre True (auth disabilitata)

    Uso:
        @router.get("/protected")
        async def protected_route(auth: bool = Depends(require_staff_auth)):
            ...
    """
    # =========================================
    # AUTH DISABILITATA
    # =========================================
    return True

    # =========================================
    # CODICE PER QUANDO AUTH SARÀ ATTIVA:
    # =========================================
    # if not staff:
    #     raise HTTPException(status_code=401, detail="Autenticazione richiesta")
    # return True


async def require_admin_auth(
    admin: Optional[BookingStaff] = Depends(get_current_admin),
) -> bool:
    """
    Dipendenza che richiede autenticazione admin.

    STATO ATTUALE: Restituisce sempre True (auth disabilitata)
    """
    # =========================================
    # AUTH DISABILITATA
    # =========================================
    return True

    # =========================================
    # CODICE PER QUANDO AUTH SARÀ ATTIVA:
    # =========================================
    # if not admin:
    #     raise HTTPException(status_code=403, detail="Accesso admin richiesto")
    # return True


def get_client_ip(request: Request) -> str:
    """
    Estrae IP client dalla request (per audit log).
    Gestisce proxy/load balancer.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Estrae User-Agent dalla request (per audit log)."""
    return request.headers.get("User-Agent", "unknown")
