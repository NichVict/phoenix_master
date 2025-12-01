import streamlit as st
from auth.token_login import require_token

# Autenticar
user = require_token()  
# user contém: {"email": "...", "carteiras": [...]}

st.set_page_config(
    page_title="Fênix Premium",
    page_icon="🦅",
    layout="wide"
)

# -----------------------
#   SIDEBAR DINÂMICO
# -----------------------
st.sidebar.title("📊 Fênix Premium")

st.sidebar.page_link("app.py", label="Dashboard Geral")

carteiras = user.get("carteiras", [])

if "Carteira de Ações IBOV" in carteiras:
    st.sidebar.page_link("pages/_hidden_carteira_ibov.py", label="Carteira IBOV")

if "Carteira de BDRs" in carteiras:
    st.sidebar.page_link("pages/_hidden_carteira_bdr.py", label="Carteira BDR")

if "Carteira de Small Caps" in carteiras:
    st.sidebar.page_link("pages/_hidden_carteira_small.py", label="Carteira Small Caps")

if "Carteira de Opções" in carteiras:
    st.sidebar.page_link("pages/_hidden_carteira_opcoes.py", label="Carteira de Opções")

# — Você pode deixar aqui espaço para upgrades ou assinaturas futuras —


# -----------------------
#   DASHBOARD PRINCIPAL
# -----------------------
st.title("🦅 Fênix Premium")
st.subheader("Bem-vindo ao seu painel de investimentos premium!")
st.info("Use o menu lateral para acessar suas carteiras.")
