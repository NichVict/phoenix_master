import streamlit as st
from auth.token_login import require_token

# --- Autenticação ---
user = require_token()
carteiras = user.get("carteiras", [])
is_admin = (user["email"] == st.secrets.get("ADMIN_EMAIL"))

st.set_page_config(
    page_title="Fênix Premium",
    page_icon="🦅",
    layout="wide"
)

# ============================
# SIDEBAR BLINDADO
# ============================
st.sidebar.title("📊 Fênix Premium")

# 🔹 CARTEIRAS
if "Carteira de Ações IBOV" in carteiras or is_admin:
    st.sidebar.page_link("pages/carteira_ibov.py", label="📈 Carteira IBOV")

if "Carteira de BDRs" in carteiras or is_admin:
    st.sidebar.page_link("pages/carteira_bdr.py", label="🌎 Carteira BDRs")

if "Carteira de Small Caps" in carteiras or is_admin:
    st.sidebar.page_link("pages/carteira_small.py", label="📉 Small Caps")

if "Carteira de Opções" in carteiras or is_admin:
    st.sidebar.page_link("pages/carteira_opcoes.py", label="🟪 Carteira de Opções")

# 🔹 DASHBOARD GERAL (todos)
st.sidebar.markdown("---")
st.sidebar.page_link("pages/dashboard_geral.py", label="📊 Dashboard Geral")

# 🔒 ÁREA DO ADMIN
if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔒 Área do Administrador")
    st.sidebar.page_link("pages/Scanner.py", label="🧠 Scanner Fênix")
    st.sidebar.page_link("pages/Dash_Ações.py", label="📈 Dash Ações (Admin)")
    st.sidebar.page_link("pages/bp_dashboard.py", label="🛠 Motor BP Admin")

st.title("🦅 Fênix Premium")
st.info("Use o menu lateral para navegar entre suas carteiras e ferramentas.")
