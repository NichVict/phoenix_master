import streamlit as st

# IMPORTA FUNÇÕES E ESTADOS DO DASH PRINCIPAL
from carteiras_bridge import (
    curto_state,
    loss_state,
    get_indice_ativo,
    render_pendentes_cards,
    render_andamento_cards,
    render_resumo_30d
)


# ============================================
# 📄 PÁGINA DA CARTEIRA BDR — PROJETO PHOENIX
# ============================================

st.markdown("## 🟨 Carteira BDR — Projeto Phoenix")

st.markdown(
    """
<p style="color:#9ca3af;font-size:13px;">
Abaixo você encontra os Trades Pendentes, Trades em Andamento e o Resumo 
de Performance dos últimos 30 dias referentes à Carteira de BDRs monitorada pelo Phoenix.
</p>
""",
    unsafe_allow_html=True,
)

# ============================================
# 🔍 1. FILTRA ATIVOS DA CARTEIRA BDR
# ============================================

pend_bdr = [a for a in curto_state.ativos if get_indice_ativo(a) == "BDR"]
and_bdr  = [a for a in loss_state.ativos  if get_indice_ativo(a) == "BDR"]


# ============================================
# ⚡ 2. TRADES PENDENTES — BDR
# ============================================

st.markdown("### ⚡ Trades Pendentes (BDR)")

if not pend_bdr:
    st.info("Nenhum trade pendente na carteira de BDR no momento.")
else:
    render_pendentes_cards(pend_bdr)


# ============================================
# ⭐ 3. TRADES EM ANDAMENTO — BDR
# ============================================

st.markdown("---")
st.markdown("### ⭐ Trades em Andamento (BDR)")

if not and_bdr:
    st.info("Nenhum trade em andamento para BDR no momento.")
else:
    render_andamento_cards(and_bdr)


# ============================================
# 📊 4. RESUMO DE DESEMPENHO — 30 DIAS
# ============================================

st.markdown("---")
st.markdown("### 🦅 Resumo de Desempenho — Últimos 30 dias (BDR)")

render_resumo_30d("BDR")
