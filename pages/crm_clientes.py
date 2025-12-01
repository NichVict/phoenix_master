import streamlit as st


st.set_page_config(page_title="CRM – Clientes", layout="wide")

st.title("👥 CRM – Clientes")

st.subheader("Lista de Clientes")

try:
    clientes = listar_clientes() if 'listar_clientes' in globals() else []
    st.table(clientes)
except Exception as e:
    st.error(f"Erro ao carregar clientes: {e}")

