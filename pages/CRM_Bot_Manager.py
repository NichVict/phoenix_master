import streamlit as st
from crm.07_Telegram_Bot_Manager import *

st.title("🤖 CRM – Bot Manager")

st.info("Gerencie aqui seu bot de Telegram. Funções carregadas do backend.")

try:
    st.write("Funções disponíveis:")
    for nome in dir():
        if nome.startswith("bot") or nome.startswith("send") or nome.startswith("manage"):
            st.write(f"- {nome}")
except Exception as e:
    st.error(f"Erro ao carregar funções do Bot Manager: {e}")
