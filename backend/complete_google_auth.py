#!/usr/bin/env python3
"""
Script per completare l'autenticazione Google OAuth2 con il codice.

Uso:
docker exec snals-backend python /app/complete_google_auth.py <CODICE_AUTORIZZAZIONE>
"""
import os
import sys
from pathlib import Path
import pickle

# Aggiungi il path dell'app
sys.path.insert(0, '/app')

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes necessari
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.file'
]

CREDENTIALS_FILE = '/app/config/google_credentials.json'
TOKEN_FILE = '/app/config/google_credentials_token.json'


def main():
    """Completa autenticazione con il codice."""

    if len(sys.argv) < 2:
        print("❌ Errore: Codice di autorizzazione mancante")
        print()
        print("Uso:")
        print(f"  docker exec snals-backend python /app/complete_google_auth.py <CODICE>")
        print()
        print("Esempio:")
        print(f"  docker exec snals-backend python /app/complete_google_auth.py 4/0AanRRrv...")
        return False

    auth_code = sys.argv[1].strip()

    print("=" * 60)
    print("COMPLETAMENTO AUTENTICAZIONE GOOGLE")
    print("=" * 60)
    print()

    if not Path(CREDENTIALS_FILE).exists():
        print(f"❌ File credentials non trovato: {CREDENTIALS_FILE}")
        return False

    try:
        # Ricrea il flow
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )

        print("🔄 Scambio codice con token...")

        # Scambia il codice con il token
        flow.fetch_token(code=auth_code)

        creds = flow.credentials

        # Salva il token
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

        print()
        print("=" * 60)
        print("✅ AUTENTICAZIONE COMPLETATA CON SUCCESSO!")
        print("=" * 60)
        print(f"Token salvato in: {TOKEN_FILE}")
        print()
        print("Ora puoi testare la connessione dalla pagina Settings del frontend.")
        print("Oppure riavvia i servizi:")
        print("  docker-compose restart backend celery-worker celery-beat")
        print()

        return True

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERRORE DURANTE COMPLETAMENTO AUTENTICAZIONE")
        print("=" * 60)
        print(f"Errore: {e}")
        print()
        print("Possibili cause:")
        print("- Codice non valido o scaduto")
        print("- Codice già utilizzato")
        print("- Errore di connessione")
        print()
        print("Prova a rieseguire:")
        print("  docker exec snals-backend python /app/authenticate_google.py")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
