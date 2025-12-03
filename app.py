import streamlit as st

# ========================
#   CONFIGURAÇÃO DO APP
# ========================
st.set_page_config(
    page_title="Fênix Premium",
    page_icon="🦅",
    layout="wide"
)

# ========================
#   SIDEBAR LIVRE
# ========================
st.sidebar.title("📊 Fênix Premium")

# 🔹 CARTEIRAS — TODAS LIBERADAS
st.sidebar.page_link("pages/carteira_ibov.py", label="📈 Carteira IBOV")
st.sidebar.page_link("pages/carteira_bdr.py", label="🌎 Carteira BDRs")
st.sidebar.page_link("pages/carteira_small.py", label="📉 Small Caps")
st.sidebar.page_link("pages/carteira_opcoes.py", label="🟪 Carteira de Opções")

st.sidebar.markdown("---")

# 🔹 DASHBOARD GERAL — LIBERADO
st.sidebar.page_link("pages/dashboard_geral.py", label="📊 Dashboard Geral")

st.sidebar.markdown("---")

# 🔹 ÁREA ADMIN — AGORA TAMBÉM SEM RESTRIÇÃO
st.sidebar.subheader("🔧 Ferramentas do Sistema")
st.sidebar.page_link("pages/Scanner.py", label="🧠 Scanner Fênix")
st.sidebar.page_link("pages/Dash_Acoes.py", label="📈 Dash Ações")
st.sidebar.page_link("pages/bp_dashboard.py", label="🛠 Motor BP")

# ========================
#   TÍTULO DA HOME
# ========================
st.title("🦅 Fênix Premium")
st.info("Menu lateral totalmente liberado. Todas as carteiras e ferramentas estão acessíveis.")
