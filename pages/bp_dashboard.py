import streamlit as st
from bp.ui.streamlit_dashboard import render_dashboard
# ============================
# 🔐 PROTEÇÃO PARA ADMIN
# ============================

# Se não há sessão → bloqueia
if "user" not in st.session_state:
    st.error("Sessão expirada. Acesse novamente.")
    st.stop()

# Se ADMIN_BYPASS está OFF → bloqueia
if str(st.secrets.get("ADMIN_BYPASS", "FALSE")).upper() != "TRUE":
    st.error("🚫 Acesso restrito ao administrador.")
    st.stop()

# Se chegou aqui → ADMIN OK (liberado)
st.set_page_config(page_title="BP Fênix", layout="wide")

render_dashboard()
