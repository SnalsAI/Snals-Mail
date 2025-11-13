"""
Script interattivo per setup Google OAuth
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/calendar'
]

def setup_oauth():
    """Setup OAuth interattivo"""

    print("\n=== Setup Google OAuth ===\n")

    # Verifica credentials file
    creds_file = input("Path al file credentials.json di Google (default: config/google_credentials.json): ").strip()
    if not creds_file:
        creds_file = "config/google_credentials.json"

    if not os.path.exists(creds_file):
        print(f"\n✗ File non trovato: {creds_file}")
        print("\nPer ottenere le credenziali:")
        print("1. Vai su https://console.cloud.google.com")
        print("2. Crea un nuovo progetto (o usa esistente)")
        print("3. Abilita Google Drive API e Google Calendar API")
        print("4. Crea credenziali OAuth 2.0 (tipo 'Desktop app')")
        print("5. Scarica il JSON e salvalo come google_credentials.json")
        return

    print(f"\n✓ Credenziali trovate: {creds_file}")

    # Avvia flow
    print("\nAvvio autenticazione...")
    print("Si aprirà una finestra del browser per autorizzare l'applicazione.")

    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
    creds = flow.run_local_server(port=8080)

    # Salva token
    token_file = "config/google_token.json"
    with open(token_file, 'wb') as token:
        pickle.dump(creds, token)

    print(f"\n✓ Autenticazione completata!")
    print(f"✓ Token salvato in: {token_file}")
    print("\nL'applicazione ora può accedere a Google Drive e Calendar.")

if __name__ == "__main__":
    setup_oauth()
