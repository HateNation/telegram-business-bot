import smtplib
from email.message import EmailMessage

from config import config


def send_gmail_smtp(subject: str, body: str, to_email: str | None = None):
    to_email = to_email or config.GMAIL_TO
    if not to_email:
        raise RuntimeError("GMAIL_TO is not set.")
    if not config.GMAIL_SENDER:
        raise RuntimeError("GMAIL_SENDER is not set.")
    if not config.GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_APP_PASSWORD is not set.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_SENDER
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(config.GMAIL_SENDER, config.GMAIL_APP_PASSWORD)
        server.send_message(msg)
