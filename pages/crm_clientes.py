import streamlit as st
from crm.clientes import listar_clientes

st.title("CRM - Clientes")

clientes = listar_clientes()
st.write(clientes)

