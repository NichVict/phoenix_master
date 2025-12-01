import streamlit as st
from bp.ui.streamlit_dashboard import render_dashboard
from auth.token_login import require_token

# 🔐 Autenticação obrigatória
user = require_token()

# 🔐 Apenas Admin pode acessar este painel
if user["email"] != st.secrets.get("ADMIN_EMAIL"):
    st.error("🚫 Acesso restrito ao administrador.")
    st.stop()

st.set_page_config(page_title="BP Fênix", layout="wide")

render_dashboard()
