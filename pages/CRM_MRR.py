import streamlit as st
from crm.MRR_Analytics import *  # backend

st.set_page_config(page_title="CRM – MRR Analytics", layout="wide")

st.title("💰 CRM – MRR Analytics")

st.subheader("Relatórios Financeiros e Receita Recorrente")

try:
    resultado = gerar_relatorio_mrr() if 'gerar_relatorio_mrr' in globals() else "Função não encontrada."
    st.write(resultado)
except Exception as e:
    st.error(f"Erro ao carregar MRR: {e}")

