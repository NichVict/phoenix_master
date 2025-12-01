import sys
import os
import streamlit as st

# ===========================
# ADICIONA A PASTA /pages AO PYTHONPATH
# ===========================
PAGES_DIR = os.path.join(os.path.dirname(__file__), "pages")

if PAGES_DIR not in sys.path:
    sys.path.insert(0, PAGES_DIR)

# ===========================
# IMPORTA DASH_Acoes DE DENTRO DE /pages
# ===========================
try:
    import Dash_Acoes as dash
except Exception as e:
    st.error(f"Erro ao importar Dash_Acoes: {e}")
    raise e

# ===========================
# REEXPORTA FUNÇÕES E STATES
# ===========================
curto_state           = dash.curto_state
loss_state            = dash.loss_state
get_indice_ativo      = dash.get_indice_ativo
render_pendentes_cards = dash.render_pendentes_cards
render_andamento_cards = dash.render_andamento_cards
render_resumo_30d     = dash.render_resumo_30d
