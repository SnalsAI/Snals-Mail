"""
Modulo Prenotazioni - Router principale

Struttura:
- /api/booking/public/  → Endpoint pubblici (utenti esterni, token-based)
- /api/booking/staff/   → Endpoint staff (richiede auth quando attivata)
- /api/booking/admin/   → Endpoint admin (richiede auth quando attivata)

L'autenticazione è PREPARATA ma NON ATTIVA.
Per attivarla, modificare le dipendenze in deps.py
"""

from fastapi import APIRouter

from .public import router as public_router
from .staff import router as staff_router
from .admin import router as admin_router

# Router principale del modulo booking
router = APIRouter(prefix="/booking", tags=["booking"])

# Include sub-routers
router.include_router(public_router, prefix="/public", tags=["booking-public"])
router.include_router(staff_router, prefix="/staff", tags=["booking-staff"])
router.include_router(admin_router, prefix="/admin", tags=["booking-admin"])
