import streamlit as st
import pandas as pd
import os
import time
import threading

import telebot
from telebot import types
from supabase import create_client, Client

# =========================================
# CONFIG - LINKS DOS GRUPOS TELEGRAM (ENTRADA)
# =========================================
LINKS_TELEGRAM = {
    "Curto Prazo": "https://t.me/+3BTqTX--W6gyNTE0",
    "Curtíssimo Prazo": "https://t.me/+BiTfqYUSiWpjN2U0",
    "Opções": "https://t.me/+1si_16NC5E8xNDhk",
    "Criptomoedas": "https://t.me/+-08kGaN0ZMsyNjJk",
    # "Leads": ""  # Leads não tem grupo
}

# =========================================
# CONFIG - CHAT_ID DOS GRUPOS (PARA EXPULSAR)
# =========================================
GROUP_CHAT_IDS = {
    "Curto Prazo": -1002046197953,
    "Curtíssimo Prazo": -1002074291817,
    "Opções": -1002001152534,
    "Criptomoedas": -1002947159530,
    # "Leads": None  # não é grupo
}

# =========================================
# SUPABASE
# =========================================
def get_secret(name: str, default=None):
    if name in st.secrets:
        return st.secrets[name]
    return os.getenv(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ SUPABASE_URL ou SUPABASE_KEY ausentes.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================
# UI PRINCIPAL
# =========================================
st.set_page_config(page_title="Telegram Manager", layout="wide")
st.title("🤖 Gerenciador do Bot do Telegram")
st.caption("Controle, sincronização e administração dos acessos ao Telegram.")
st.markdown("---")

st.subheader("👤 Clientes e Status Telegram")

# Carrega clientes
try:
    resp = supabase.table("clientes").select("*").execute()
    dados = resp.data or []
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

if not dados:
    st.info("Nenhum cliente encontrado.")
    st.stop()

df = pd.DataFrame(dados)

# Normalizar datas
if "data_fim" in df.columns:
    df["data_fim"] = pd.to_datetime(df["data_fim"], errors="coerce").dt.date

# Garantir colunas de Telegram / controle
for col in ["telegram_id", "telegram_username", "telegram_connected",
            "telegram_last_sync", "telegram_removed_at"]:
    if col not in df.columns:
        df[col] = None

st.dataframe(
    df[[
        "id", "nome", "email", "carteiras", "data_fim",
        "telegram_id", "telegram_username",
        "telegram_connected", "telegram_last_sync", "telegram_removed_at"
    ]],
    use_container_width=True
)

st.markdown("---")

# =========================================
# BOT TELEGRAM — DESATIVADO (comentado)
# =========================================
TELEGRAM_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_TOKEN:
    st.error("❌ TELEGRAM_BOT_TOKEN não foi configurado em Secrets.")
    st.stop()

# bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")   # DESATIVADO


# =========================================
# FUNÇÕES AUXILIARES
# =========================================
def carteiras_to_list(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        raw = raw.replace("[", "").replace("]", "").replace("'", "")
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


def parse_date(d):
    try:
        return pd.to_datetime(d).date()
    except Exception:
        return None


# =========================================
# /start COM ID -> DESATIVADO
# =========================================
# @bot.message_handler(commands=['start'])
# def boas_vindas(message):
#     (... INTEIRO, MANTIDO, MAS COMENTADO ...)


# =========================================
# CALLBACK VALIDAR -> DESATIVADO
# =========================================
# @bot.callback_query_handler(func=lambda call: call.data.startswith("validar_"))
# def processar_validacao(call):
#     (... INTEIRO, MANTIDO, MAS COMENTADO ...)


# =========================================
# REMOÇÃO AUTOMÁTICA — DESATIVADO
# =========================================
# def remover_cliente_dos_grupos_e_virar_lead(cli) -> bool:
#     (... INTEIRO, MANTIDO, MAS COMENTADO ...)

# def verificar_e_excluir_vencidos() -> int:
#     (... INTEIRO, MANTIDO, MAS COMENTADO ...)


# =========================================
# THREAD DO BOT — DESATIVADA
# =========================================
# def iniciar_bot():
#     bot.infinity_polling(timeout=10, long_polling_timeout=5)


# =========================================
# THREAD ROTINA — DESATIVADA
# =========================================
# def rotina_remocao_vencidos():
#     while True:
#         try:
#             verificar_e_excluir_vencidos()
#         except Exception:
#             pass
#         time.sleep(24 * 60 * 60)


# =========================================
# INICIALIZAÇÃO DAS THREADS — DESATIVADA
# =========================================
if "bot_started" not in st.session_state:
    st.session_state["bot_started"] = False

if "cleanup_started" not in st.session_state:
    st.session_state["cleanup_started"] = False

# if not st.session_state["bot_started"]:
#     thread_bot = threading.Thread(target=iniciar_bot, daemon=True)
#     thread_bot.start()
#     st.session_state["bot_started"] = True

# if not st.session_state["cleanup_started"]:
#     thread_clean = threading.Thread(target=rotina_remocao_vencidos, daemon=True)
#     thread_clean.start()
#     st.session_state["cleanup_started"] = True


# =========================================
# CONTROLES VISUAIS (STATUS) — DESATIVADOS
# =========================================
# st.subheader("📡 Status & Ações do Bot")
#
# col1, col2 = st.columns(2)
#
# with col1:
#     st.success("🤖 Bot em execução automática em background (infinity_polling).")
#
# with col2:
#     st.info("🕒 Rotina diária de remoção de assinaturas vencidas ativa (intervalo: 24h).")
#
# st.markdown("---")
#
# st.subheader("🧪 Testes manuais")
#
# if st.button("🚨 Rodar verificação de vencidos agora"):
#     qnt = verificar_e_excluir_vencidos()
#     (...)


# =========================================
# TABELA DE CLIENTES REMOVIDOS — NOVO
# =========================================
st.markdown("---")
st.subheader("🚫 Clientes Removidos do Telegram")

df_removed = df[df["telegram_removed_at"].notnull()]

if df_removed.empty:
    st.info("Nenhum cliente foi removido ainda.")
else:
    st.dataframe(
        df_removed[[
            "id", "nome", "email", "carteiras",
            "telegram_id", "telegram_username",
            "telegram_removed_at"
        ]],
        use_container_width=True
    )
