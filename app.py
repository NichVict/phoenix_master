import streamlit as st
from auth.token_login import require_token

# ---- Autenticação ----
user = require_token()   # funciona para cliente e para admin via bypass
carteiras = user.get("carteiras", [])

st.set_page_config(
    page_title="Fênix Premium",
    page_icon="🦅",
    layout="wide"
)

# -----------------------
#   SIDEBAR
# -----------------------
st.sidebar.title("📊 Fênix Premium")

# Scanner sempre disponível (admin ou cliente)
st.sidebar.page_link("pages/bp_dashboard.py", label="Scanner Fênix")

# ---- Carteiras do cliente ou admin ----
if "Carteira de Ações IBOV" in carteiras:
    st.sidebar.page_link("pages/carteira_ibov.py", label="Carteira IBOV")

if "Carteira de BDRs" in carteiras:
    st.sidebar.page_link("pages/carteira_bdr.py", label="Carteira BDR")

if "Carteira de Small Caps" in carteiras:
    st.sidebar.page_link("pages/carteira_small.py", label="Carteira Small Caps")

if "Carteira de Opções" in carteiras:
    st.sidebar.page_link("pages/carteira_opcoes.py", label="Carteira de Opções")

# ---- Dashboard geral (opcional futuro) ----
if "Dashboard Geral" in carteiras:
    st.sidebar.page_link("pages/dashboard_geral.py", label="Dashboard Geral")

# -----------------------
#   HOME
# -----------------------
st.title("🦅 Fênix Premium")
st.info("Use o menu lateral para navegar.")

