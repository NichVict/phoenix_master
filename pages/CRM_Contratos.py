import streamlit as st

st.title("📜 CRM – Contratos")

try:
    with open("crm/contrato_Aurinvest.pdf", "rb") as f:
        st.download_button("Baixar Contrato Aurinvest", f, file_name="contrato_Aurinvest.pdf")
except:
    st.warning("Contrato não encontrado no diretório crm/.")
