
import os
import time
import requests
from datetime import datetime

# ============================================================
# CONFIGURAÇÕES
# ============================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")          # coloque no Render
SUPABASE_URL   = os.getenv("SUPABASE_URL")            # coloque no Render
SUPABASE_KEY   = os.getenv("SUPABASE_KEY")            # coloque no Render

# IDs dos grupos — você já me passou
# NOVOS GRUPOS PHOENIX — links de convite oficiais
GRUPOS = {
    "Carteira de Ações IBOV": "https://t.me/+Rkvw9CfJBkowMTg0",
    "Carteira de BDRs": "https://t.me/+-Io0aAFaGJ0yN2Rk",
    "Carteira de Opções": "https://t.me/+3YzTJqBi-xYxNjNk",
}




BASE_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


# ============================================================
# FUNÇÕES DE SUPABASE
# ============================================================
def supabase_get_client(cliente_id):
    """Busca cliente no Supabase pelo ID"""
    url = f"{SUPABASE_URL}/rest/v1/clientes?id=eq.{cliente_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    r = requests.get(url, headers=headers)
    try:
        return r.json()[0]
    except:
        return None


# ============================================================
# FUNÇÕES TELEGRAM
# ============================================================
def tg_get_updates(offset=None):
    """Pega mensagens novas do Telegram"""
    url = BASE_API + "/getUpdates"
    if offset:
        url += f"?offset={offset}"
    return requests.get(url).json()


def tg_send_message(chat_id, text, reply_markup=None):
    """Envia mensagem simples"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(BASE_API + "/sendMessage", json=payload)


def tg_kick_user(group_id, user_id):
    """Expulsa usuário do grupo - usado mais tarde"""
    url = BASE_API + "/kickChatMember"
    payload = {"chat_id": group_id, "user_id": user_id}
    requests.post(url, json=payload)


# ============================================================
# PROCESSAMENTO DO /start
# ============================================================
def process_start(message):
    chat_id = message["chat"]["id"]
    text = message["text"]

    parts = text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        tg_send_message(chat_id, "❌ Link inválido ou expirado. Peça um novo ao suporte.")
        return

    cliente_id = parts[1]

    cliente = supabase_get_client(cliente_id)
    if not cliente:
        tg_send_message(chat_id, "❌ Cliente não encontrado. Peça um novo link ao suporte.")
        return

    nome = cliente["nome"]

    teclado = {
        "inline_keyboard": [
            [
                {
                    "text": "🔓 VALIDAR ACESSO",
                    "callback_data": f"validar:{cliente_id}"
                }
            ]
        ]
    }

    tg_send_message(
        chat_id,
        f"👋 Olá <b>{nome}</b>!\n\nClique abaixo para validar seu acesso.",
        reply_markup=teclado
    )



# ============================================================
# PROCESSAMENTO DE CALLBACK (quando clica VALIDAR ACESSO)
# ============================================================
def process_callback(callback):
    data = callback["data"]            # ex: validar:939
    user_id = callback["from"]["id"]
    chat_id = callback["message"]["chat"]["id"]

    _, cliente_id = data.split(":")

    cliente = supabase_get_client(cliente_id)
    if not cliente:
        tg_send_message(chat_id, "❌ Cliente não encontrado.")
        return

    nome = cliente["nome"]
    carteiras = cliente["carteiras"]

    resposta = [f"🎉 <b>Acesso Validado, {nome}!</b>\n"]

    # percorre as carteiras novas
    for c in carteiras:
        if c in GRUPOS:
            link = GRUPOS[c]
            resposta.append(f"➡️ <b>{c}</b>: {link}")
        else:
            resposta.append(f"⚠️ Nenhum grupo configurado para: {c}")

    tg_send_message(chat_id, "\n".join(resposta))



# ============================================================
# LOOP PRINCIPAL
# ============================================================
def main():
    print("🤖 Bot do Telegram rodando no Render…")
    last_update = None

    while True:
        try:
            updates = tg_get_updates(last_update)
            if "result" in updates:
                for u in updates["result"]:
                    last_update = u["update_id"] + 1

                    # mensagem normal
                    if "message" in u and "text" in u["message"]:
                        texto = u["message"]["text"]
                        if texto.startswith("/start"):
                            process_start(u["message"])

                    # callback
                    if "callback_query" in u:
                        process_callback(u["callback_query"])

        except Exception as e:
            print("Erro no bot:", e)

        time.sleep(1)


if __name__ == "__main__":
    main()
