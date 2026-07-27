import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from lib.database import get_db
from lib.logger import get_logger


def send_email(recipient, subject, body, attachment_path=None):
    db = get_db()
    settings = db.settings_get_all()
    logger = get_logger()
    smtp_host = settings.get("smtp_host", "")
    smtp_port = settings.get("smtp_port", "465")
    smtp_user = settings.get("smtp_user", "")
    smtp_pass = settings.get("smtp_pass", "")
    smtp_sender = settings.get("smtp_sender", "")
    smtp_encryption = settings.get("smtp_encryption", "SSL/TLS")
    if not smtp_host or not smtp_user or not smtp_pass:
        logger.error("SMTP nicht konfiguriert")
        return False, "SMTP nicht konfiguriert. Bitte in Einstellungen hinterlegen."
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
                msg.attach(part)
        port = int(smtp_port)
        if smtp_encryption == "SSL/TLS":
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, port, timeout=30)
            if smtp_encryption == "STARTTLS":
                server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_sender, recipient, msg.as_string())
        server.quit()
        logger.info(f"E-Mail gesendet an {recipient}: {subject}")
        return True, "E-Mail erfolgreich gesendet!"
    except Exception as ex:
        logger.error(f"E-Mail-Fehler: {ex}")
        return False, f"Fehler beim Senden: {ex}"
