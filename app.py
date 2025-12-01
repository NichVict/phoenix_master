import streamlit as st
from auth.token_login import require_token, require_carteira

# ==========================
# AUTENTICAÇÃO
# ==========================
user = require_token()  
# user = {"email": "...", "carteiras": [...]}

st.set_page_config(
    page_title="Fênix Premium",
    page_icon="🦅",
    layout="wide"
)

# ==========================
# SIDEBAR DINÂMICO
# ==========================
st.sidebar.title("📊 Fênix Premium")

# Dashboard principal
st.sidebar.page_link("app.py", label="Dashboard Geral")

carteiras = user.get("carteiras", [])

# Carteira IBOV
if "Carteira de Ações IBOV" in carteiras:
    st.sidebar.page_link("pages/_hidden_carteira_ibov.py", label="Carteira IBOV")

# BDR
if "Carteira de BDRs" in carteiras:
    st.sidebar.page_link("pages/_hidden_carteira_bdr.py", label="Carteira BDR")

# Small Caps
if "Carteira de Small Caps" in carteiras:
    st.sidebar.page_link("pages/_hidden_carteira_small.py", label="Carteira Small Caps")

# Opções
if "Carteira de Opções" in carteiras:
    st.sidebar.page_link("pages/_hidden_carteira_opcoes.py", label="Carteira de Opções")

# ==========================
# DASHBOARD PRINCIPAL
# ==========================
st.title("🦅 Fênix Premium")
st.subheader("Bem-vindo ao seu painel de investimentos premium!")
st.info("Use o menu lateral para acessar suas carteiras.")
