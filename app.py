import streamlit as st

st.set_page_config(
    page_title="Fênix Premium",
    page_icon="🦅",
    layout="wide"
)

with st.sidebar.expander("🧩 CRM"):
    st.page_link("pages/CRM_Dashboard.py", label="Dashboard CRM")
    st.page_link("pages/CRM_Clientes.py", label="Clientes")
    st.page_link("pages/CRM_Assinaturas.py", label="Assinaturas")
    st.page_link("pages/CRM_MRR.py", label="MRR Analytics")
    st.page_link("pages/CRM_Bot_Manager.py", label="Bot Manager")
    st.page_link("pages/CRM_Contratos.py", label="Contratos")
    st.page_link("pages/CRM_Configuracoes.py", label="Configurações")

with st.sidebar.expander("💼 Carteiras"):
    st.page_link("pages/dashboard_geral.py", label="Dashboard Geral")
    st.page_link("pages/carteira_ibov.py", label="Carteira IBOV")
    st.page_link("pages/carteira_bdr.py", label="Carteira BDR")
    st.page_link("pages/carteira_small.py", label="Carteira Small Caps")
    st.page_link("pages/carteira_opcoes.py", label="Carteira de Opções")

st.title("🦅 Fênix Premium")
st.info("Selecione uma opção no menu ao lado.")
