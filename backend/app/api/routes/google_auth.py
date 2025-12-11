"""
Route per autenticazione Google OAuth2.
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
import logging
from pathlib import Path

from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

router = APIRouter()

# Scopes necessari
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.file'
]

CREDENTIALS_FILE = '/app/config/google_credentials.json'
TOKEN_FILE = '/app/config/google_credentials_token.json'


@router.get("/google/auth/start")
async def start_google_auth(request: Request):
    """Avvia il flow OAuth2 con Google."""

    if not Path(CREDENTIALS_FILE).exists():
        raise HTTPException(status_code=500, detail="Google credentials non configurate")

    # Crea flow con redirect URI del backend
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=str(request.base_url) + "api/auth/google/callback"
    )

    # Genera URL di autorizzazione
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )

    # Salva lo state per verificarlo dopo
    # In produzione dovresti salvarlo in Redis/DB
    with open('/tmp/google_oauth_state.txt', 'w') as f:
        f.write(state)

    # Reindirizza a Google
    return {
        "authorization_url": authorization_url,
        "message": "Apri questo URL nel browser per autorizzare l'applicazione"
    }


@router.get("/google/callback", response_class=HTMLResponse)
async def google_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Callback da Google dopo autorizzazione."""

    if error:
        logger.error(f"Errore OAuth2: {error}")
        return f"""
        <html>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h1 style="color: #dc2626;">❌ Errore Autenticazione</h1>
                <p>Errore: {error}</p>
                <p><a href="/settings">Torna alle impostazioni</a></p>
            </body>
        </html>
        """

    if not code:
        return """
        <html>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h1 style="color: #dc2626;">❌ Codice mancante</h1>
                <p>Nessun codice di autorizzazione ricevuto</p>
                <p><a href="/settings">Torna alle impostazioni</a></p>
            </body>
        </html>
        """

    try:
        # Verifica state (in produzione controlla con quello salvato)
        # saved_state = open('/tmp/google_oauth_state.txt').read().strip()
        # if state != saved_state:
        #     raise HTTPException(status_code=400, detail="State mismatch")

        # Ricrea il flow
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=str(request.base_url) + "api/auth/google/callback"
        )

        # Scambia il code con il token
        flow.fetch_token(code=code)

        credentials = flow.credentials

        # Salva il token
        with open(TOKEN_FILE, 'w') as token_file:
            token_file.write(credentials.to_json())

        logger.info("✅ Autenticazione Google completata con successo")

        return """
        <html>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h1 style="color: #10b981;">✅ Autenticazione Completata!</h1>
                <p style="font-size: 18px;">Google Calendar e Drive sono ora configurati correttamente.</p>
                <p style="margin-top: 30px;">
                    <a href="/settings" style="background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
                        Torna alle Impostazioni
                    </a>
                </p>
                <p style="margin-top: 20px; color: #666;">
                    Puoi chiudere questa finestra
                </p>
            </body>
        </html>
        """

    except Exception as e:
        logger.error(f"Errore durante callback OAuth2: {e}")
        import traceback
        traceback.print_exc()

        return f"""
        <html>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h1 style="color: #dc2626;">❌ Errore</h1>
                <p>Errore durante l'autenticazione: {str(e)}</p>
                <p><a href="/settings">Torna alle impostazioni</a></p>
            </body>
        </html>
        """
