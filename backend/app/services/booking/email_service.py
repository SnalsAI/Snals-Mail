"""
Servizio per l'invio email relative alle prenotazioni.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Nomi italiani per giorni e mesi
GIORNI_IT = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
MESI_IT = ['', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
           'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']


def formatta_data_italiana(dt: datetime) -> str:
    """Formatta una data in italiano (es: Lunedì 15 Gennaio 2025 alle ore 10:30)"""
    giorno = GIORNI_IT[dt.weekday()]
    mese = MESI_IT[dt.month]
    return f"{giorno} {dt.day} {mese} {dt.year} alle ore {dt.strftime('%H:%M')}"


def invia_email_conferma_prenotazione(
    destinatario: str,
    nome: str,
    cognome: str,
    data_ora: datetime,
    sede_nome: str,
    sede_indirizzo: Optional[str],
    tipo_appuntamento: str,
    token: str,
    istruzioni: Optional[str] = None
) -> bool:
    """
    Invia email di conferma prenotazione.

    Args:
        destinatario: Email del destinatario
        nome: Nome del prenotante
        cognome: Cognome del prenotante
        data_ora: Data e ora dell'appuntamento
        sede_nome: Nome della sede
        sede_indirizzo: Indirizzo della sede
        tipo_appuntamento: Tipo di appuntamento
        token: Token pubblico per gestire la prenotazione
        istruzioni: Eventuali istruzioni aggiuntive

    Returns:
        True se l'invio è riuscito, False altrimenti
    """
    try:
        # Formatta data/ora in italiano
        data_formattata = formatta_data_italiana(data_ora)

        # URL per gestire la prenotazione
        base_url = "http://51.83.33.167:3001"  # TODO: da config
        link_prenotazione = f"{base_url}/prenotazioni/{token}"

        # Costruisci HTML email
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #0056b3; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
        .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .details table {{ width: 100%; border-collapse: collapse; }}
        .details td {{ padding: 10px 0; border-bottom: 1px solid #eee; }}
        .details td:first-child {{ font-weight: bold; color: #666; width: 40%; }}
        .btn {{ display: inline-block; background: #0056b3; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
        .btn:hover {{ background: #004494; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .warning {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .instructions {{ background: #e7f3ff; border: 1px solid #b6d4fe; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Prenotazione Confermata</h1>
            <p>SNALS Taranto - Segreteria Provinciale</p>
        </div>

        <div class="content">
            <p>Gentile <strong>{nome} {cognome}</strong>,</p>

            <p>La tua prenotazione è stata <strong>confermata</strong> con successo.</p>

            <div class="details">
                <table>
                    <tr>
                        <td>Data e Ora:</td>
                        <td><strong>{data_formattata}</strong></td>
                    </tr>
                    <tr>
                        <td>Tipo Appuntamento:</td>
                        <td>{tipo_appuntamento}</td>
                    </tr>
                    <tr>
                        <td>Sede:</td>
                        <td>{sede_nome}</td>
                    </tr>
                    {"<tr><td>Indirizzo:</td><td>" + sede_indirizzo + "</td></tr>" if sede_indirizzo else ""}
                </table>
            </div>

            {f'<div class="instructions"><strong>Istruzioni:</strong><br>{istruzioni}</div>' if istruzioni else ''}

            <div class="warning">
                <strong>Importante:</strong> Se non puoi presentarti all'appuntamento,
                ti preghiamo di annullare o spostare la prenotazione utilizzando il link sottostante.
            </div>

            <p style="text-align: center;">
                <a href="{link_prenotazione}" style="display: inline-block; background-color: #0056b3; color: #ffffff !important; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Gestisci Prenotazione</a>
            </p>

            <p>Conserva questa email come promemoria.</p>
        </div>

        <div class="footer">
            <p>SNALS Taranto - Segreteria Provinciale</p>
            <p>Questa email è stata generata automaticamente. Non rispondere a questo messaggio.</p>
        </div>
    </div>
</body>
</html>
"""

        # Versione testo plain
        text_body = f"""
Prenotazione Confermata - SNALS Taranto

Gentile {nome} {cognome},

La tua prenotazione è stata confermata con successo.

DETTAGLI APPUNTAMENTO:
- Data e Ora: {data_formattata}
- Tipo: {tipo_appuntamento}
- Sede: {sede_nome}
{f'- Indirizzo: {sede_indirizzo}' if sede_indirizzo else ''}

{f'ISTRUZIONI: {istruzioni}' if istruzioni else ''}

Per gestire la tua prenotazione (modifica/annullamento):
{link_prenotazione}

IMPORTANTE: Se non puoi presentarti, ti preghiamo di annullare o spostare la prenotazione.

---
SNALS Taranto - Segreteria Provinciale
Email generata automaticamente.
"""

        # Crea messaggio
        msg = MIMEMultipart('alternative')
        msg['From'] = f"SNALS Taranto Prenotazioni <{settings.EMAIL_NORMAL_SMTP_USER}>"
        msg['To'] = destinatario
        msg['Subject'] = f"Conferma Prenotazione - {data_ora.strftime('%d/%m/%Y %H:%M')}"

        # Aggiungi parti (text prima, html dopo - il client mostrerà l'ultima che supporta)
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # Invia via SMTP
        smtp_host = settings.EMAIL_NORMAL_SMTP_HOST
        smtp_port = settings.EMAIL_NORMAL_SMTP_PORT
        smtp_user = settings.EMAIL_NORMAL_SMTP_USER
        smtp_password = settings.EMAIL_NORMAL_SMTP_PASSWORD

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.starttls()

        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, destinatario, msg.as_string())
        server.quit()

        logger.info(f"✅ Email conferma prenotazione inviata a: {destinatario}")
        return True

    except Exception as e:
        logger.error(f"❌ Errore invio email conferma a {destinatario}: {e}")
        return False


def invia_email_annullamento(
    destinatario: str,
    nome: str,
    cognome: str,
    data_ora: datetime,
    tipo_appuntamento: str,
    motivo: Optional[str] = None
) -> bool:
    """
    Invia email di conferma annullamento prenotazione.
    """
    try:
        data_formattata = data_ora.strftime("%d/%m/%Y alle ore %H:%M")

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #dc3545; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Prenotazione Annullata</h1>
        </div>
        <div class="content">
            <p>Gentile <strong>{nome} {cognome}</strong>,</p>
            <p>La tua prenotazione per <strong>{tipo_appuntamento}</strong> del <strong>{data_formattata}</strong>
            è stata <strong>annullata</strong>.</p>
            {f'<p><strong>Motivo:</strong> {motivo}</p>' if motivo else ''}
            <p>Per una nuova prenotazione, visita il nostro sito.</p>
        </div>
        <div class="footer">
            <p>SNALS Taranto - Segreteria Provinciale</p>
        </div>
    </div>
</body>
</html>
"""

        msg = MIMEMultipart('alternative')
        msg['From'] = f"SNALS Taranto Prenotazioni <{settings.EMAIL_NORMAL_SMTP_USER}>"
        msg['To'] = destinatario
        msg['Subject'] = f"Prenotazione Annullata - {data_formattata}"
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        smtp_host = settings.EMAIL_NORMAL_SMTP_HOST
        smtp_port = settings.EMAIL_NORMAL_SMTP_PORT
        smtp_user = settings.EMAIL_NORMAL_SMTP_USER
        smtp_password = settings.EMAIL_NORMAL_SMTP_PASSWORD

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.starttls()

        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, destinatario, msg.as_string())
        server.quit()

        logger.info(f"✅ Email annullamento inviata a: {destinatario}")
        return True

    except Exception as e:
        logger.error(f"❌ Errore invio email annullamento a {destinatario}: {e}")
        return False
