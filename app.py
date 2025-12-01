import streamlit as st

st.set_page_config(
    page_title="Fênix Premium",
    page_icon="🦅",
    layout="wide"
)

# --------------------------
# SIDEBAR – CRM ORIGINAL
# --------------------------
with st.sidebar:
    st.page_link("pages/CRM.py", label="📁 CRM Aurinvest")  # <-- APENAS 1 LINK

# --------------------------
# SIDEBAR – CARTEIRAS
# --------------------------
with st.sidebar.expander("💼 Carteiras"):
    st.page_link("pages/dashboard_geral.py", label="Dashboard Geral")
    st.page_link("pages/carteira_ibov.py", label="Carteira IBOV")
    st.page_link("pages/carteira_bdr.py", label="Carteira BDR")
    st.page_link("pages/carteira_small.py", label="Carteira Small Caps")
    st.page_link("pages/carteira_opcoes.py", label="Carteira de Opções")

# --------------------------
# HOME
# --------------------------
st.title("🦅 Fênix Premium")
st.info("Selecione uma opção no menu ao lado.")
