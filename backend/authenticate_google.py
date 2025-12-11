#!/usr/bin/env python3
"""
Script per autenticare Google OAuth2 la prima volta.

Esegui questo script DENTRO il container backend:
docker exec -it snals-backend python authenticate_google.py

Seguirà un processo interattivo per ottenere il token.
"""
import os
import sys
from pathlib import Path

# Aggiungi il path dell'app
sys.path.insert(0, '/app')

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes necessari
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.file'
]

CREDENTIALS_FILE = '/app/config/google_credentials.json'
TOKEN_FILE = '/app/config/google_credentials_token.json'


def main():
    """Autentica con Google OAuth2."""

    print("=" * 60)
    print("AUTENTICAZIONE GOOGLE OAUTH2")
    print("=" * 60)
    print()

    if not Path(CREDENTIALS_FILE).exists():
        print(f"❌ File credentials non trovato: {CREDENTIALS_FILE}")
        print("Assicurati di aver creato il file google_credentials.json")
        return False

    creds = None

    # Controlla se esiste già un token valido
    if Path(TOKEN_FILE).exists():
        print("📝 Token esistente trovato, verifico validità...")
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

            if creds and creds.valid:
                print("✅ Token valido! Autenticazione già completata.")
                print(f"Token salvato in: {TOKEN_FILE}")
                return True

            # Token scaduto, prova a rinnovarlo
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Token scaduto, rinnovo...")
                creds.refresh(Request())

                # Salva token rinnovato
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())

                print("✅ Token rinnovato con successo!")
                return True

        except Exception as e:
            print(f"⚠️  Token esistente non valido: {e}")
            print("Procedo con nuova autenticazione...")

    # Avvia flow OAuth2
    print()
    print("🔐 Avvio autenticazione OAuth2...")
    print()

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )

        # Genera URL di autorizzazione
        auth_url, _ = flow.authorization_url(prompt='consent')

        print("📋 ISTRUZIONI:")
        print("1. Copia l'URL qui sotto")
        print("2. Incollalo nel browser del tuo PC")
        print("3. Fai login con il tuo account Google")
        print("4. Autorizza l'applicazione")
        print("5. Google ti mostrerà un CODICE - copialo")
        print()
        print("-" * 60)
        print("URL DI AUTORIZZAZIONE:")
        print()
        print(auth_url)
        print()
        print("-" * 60)
        print()

        # In modalità non-interattiva, salva l'URL in un file
        with open('/app/config/google_auth_url.txt', 'w') as f:
            f.write(auth_url)

        print("✅ URL salvato in: /app/config/google_auth_url.txt")
        print()
        print("⚠️  PROSSIMO PASSO:")
        print("Dopo aver autorizzato, copia il codice e esegui:")
        print("docker exec snals-backend python /app/complete_google_auth.py <CODICE>")
        print()

        return False  # Non completato ancora

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
        print()

        return True

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERRORE DURANTE AUTENTICAZIONE")
        print("=" * 60)
        print(f"Errore: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
