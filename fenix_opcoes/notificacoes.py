import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# -----------------------------
#  TELEGRAM
# -----------------------------



TG_TOKEN = "8237511970:AAEjrMaMm1KIO_5qNmPjvZsL0mK6dQObK2k"
TG_CHAT_ID = "-1003274356400"

def enviar_telegram(text: str):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"

    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    resp = requests.post(url, json=payload, timeout=10)

    print("=== DEBUG TELEGRAM ===")
    print("Status:", resp.status_code)
    print("Resposta:", resp.text)

    # força erro se falhar
    resp.raise_for_status()



# -----------------------------
#  EMAIL
# -----------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_SENDER = "alertaurinvest@gmail.com"
EMAIL_PASSWORD = "ipdl xomo ixxy ldtm"  # app password
EMAIL_DESTINO = "estrategiasopcoes-phoenix@googlegroups.com"

def enviar_email(assunto: str, corpo: str):

    print("=== DEBUG EMAIL ===")
    print("Assunto:", assunto)
    print("Destinatário:", EMAIL_DESTINO)

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_DESTINO
    msg["Subject"] = assunto

    msg.attach(MIMEText(corpo, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)

        print("EMAIL ENVIADO COM SUCESSO")
    except Exception as e:
        print("ERRO SMTP:", e)
        raise
