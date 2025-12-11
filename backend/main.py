"""
SNALS Email Agent - Main Application
Entry point FastAPI
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema automatizzazione gestione email SNALS"
)

# CORS - Permetti tutte le origini per sviluppo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione, specificare gli host esatti
    allow_credentials=False,  # Deve essere False con allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "not_checked",
        "redis": "not_checked"
    }

# Include API routers
from app.api.routes import emails, azioni, regole, calendario, google_auth, schools, system_settings, delegati, rag, spam, interpelli, classi_concorso, knowledge, debug, ricevute_pec, verification, training, bug_reports
from app.api.routes import settings as settings_routes

app.include_router(emails.router, prefix="/api")
app.include_router(azioni.router, prefix="/api")
app.include_router(regole.router, prefix="/api")
app.include_router(calendario.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(spam.router, prefix="/api")
app.include_router(ricevute_pec.router, prefix="/api")
app.include_router(system_settings.router, prefix="/api")
app.include_router(delegati.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(interpelli.router, prefix="/api")
app.include_router(classi_concorso.router, prefix="/api")
app.include_router(google_auth.router, prefix="/api/auth")
app.include_router(schools.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(debug.router, prefix="/api")  # Debug/monitoring endpoints
app.include_router(verification.router, prefix="/api")  # OpenAI verification endpoints
app.include_router(training.router, prefix="/api")  # NLP Training with ChatGPT
app.include_router(bug_reports.router, prefix="/api")  # Bug reporting system

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
