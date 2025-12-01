import streamlit as st
from crm.assinaturas import *  # backend

st.set_page_config(page_title="CRM – Assinaturas", layout="wide")

st.title("📄 CRM – Assinaturas")

st.subheader("Gestão das Assinaturas por Cliente")

try:
    assinaturas = listar_assinaturas() if 'listar_assinaturas' in globals() else []
    st.table(assinaturas)
except Exception as e:
    st.error(f"Erro ao carregar assinaturas: {e}")


