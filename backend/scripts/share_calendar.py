"""
Script per condividere il calendario del Service Account con un utente
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.integrations.google_calendar_client import GoogleCalendarClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Crea un calendario dedicato e lo condivide con l'utente"""
    # Email dell'utente con cui condividere
    USER_EMAIL = "snalstaranto@gmail.com"
    CALENDAR_NAME = "SNALS Taranto - Convocazioni"
    CALENDAR_DESCRIPTION = "Calendario convocazioni e appuntamenti SNALS Taranto"

    logger.info(f"📅 Creazione e condivisione calendario '{CALENDAR_NAME}'...")

    # Inizializza client
    client = GoogleCalendarClient()

    # Autentica
    if not client.authenticate():
        logger.error("❌ Autenticazione fallita")
        return False

    # Verifica se il calendario esiste già
    try:
        calendars = client.get_calendar_list()
        existing_calendar = None

        for cal in calendars:
            if cal.get('summary') == CALENDAR_NAME:
                existing_calendar = cal
                logger.info(f"📋 Calendario esistente trovato: {cal['id']}")
                break

        if existing_calendar:
            calendar_id = existing_calendar['id']
        else:
            # Crea nuovo calendario
            logger.info(f"📝 Creazione nuovo calendario '{CALENDAR_NAME}'...")
            calendar = {
                'summary': CALENDAR_NAME,
                'description': CALENDAR_DESCRIPTION,
                'timeZone': 'Europe/Rome'
            }

            created_calendar = client.service.calendars().insert(body=calendar).execute()
            calendar_id = created_calendar['id']
            logger.info(f"✅ Calendario creato: {calendar_id}")

    except Exception as e:
        logger.error(f"❌ Errore gestione calendario: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    # Condividi calendario (ruolo: writer = può modificare eventi)
    logger.info(f"🔗 Condivisione calendario con {USER_EMAIL}...")
    success = client.share_calendar(
        email=USER_EMAIL,
        role='writer',  # 'reader' = solo lettura, 'writer' = lettura e scrittura
        calendar_id=calendar_id
    )

    if success:
        logger.info(f"✅ Calendario condiviso con successo!")
        logger.info(f"📧 {USER_EMAIL} può ora vedere e modificare gli eventi")
        logger.info(f"🔗 Il calendario '{CALENDAR_NAME}' dovrebbe apparire automaticamente in Google Calendar")
        logger.info(f"📋 ID calendario: {calendar_id}")

        # Salva l'ID del calendario in un file per riferimento futuro
        with open('/app/config/snals_calendar_id.txt', 'w') as f:
            f.write(calendar_id)
        logger.info(f"💾 ID calendario salvato in config/snals_calendar_id.txt")
    else:
        logger.error(f"❌ Errore durante la condivisione")

    return success

if __name__ == '__main__':
    main()
