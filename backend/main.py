"""
FastAPI main application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.api import regole

app = FastAPI(
    title="SNALS Email Agent API",
    description="Sistema automatizzato gestione email SNALS",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione: specificare origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(regole.router, prefix="/api/regole", tags=["regole"])


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "SNALS Email Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }
