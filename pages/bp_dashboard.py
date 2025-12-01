import streamlit as st
from bp.ui.streamlit_dashboard import render_dashboard
# ============================
# 🔐 PROTEÇÃO PARA ADMIN
# ============================


# Se não há usuário carregado → bloqueia
if "user" not in st.session_state:
    st.error("Sessão expirada. Faça login como administrador.")
    st.stop()

# Se o e-mail do usuário NÃO é o do admin → bloqueia
if st.session_state["user"]["email"] != st.secrets.get("ADMIN_EMAIL"):
    st.error("🚫 Acesso restrito ao administrador.")
    st.stop()

# ---- DAQUI PRA BAIXO É A LÓGICA NORMAL DA PÁGINA ----

# Se chegou aqui → ADMIN OK (liberado)
st.set_page_config(page_title="BP Fênix", layout="wide")

render_dashboard()
