import streamlit as st
from bp.ui.streamlit_dashboard import render_dashboard

# ---- DAQUI PRA BAIXO É A LÓGICA NORMAL DA PÁGINA ----

# Se chegou aqui → ADMIN OK (liberado)
st.set_page_config(page_title="BP Fênix", layout="wide")

render_dashboard()
