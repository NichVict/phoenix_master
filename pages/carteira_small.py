import streamlit as st

# IMPORTAÇÃO DO BRIDGE (MESMO PADRÃO DE IBOV/BDR)
from carteiras_bridge import (
    curto_state,
    loss_state,
    get_indice_ativo,
    render_pendentes_cards,
    render_andamento_cards,
    render_resumo_30d
)

# ============================================
# 📄 PÁGINA DA CARTEIRA SMALL CAPS — PHOENIX
# ============================================

st.markdown("## 🟩 Carteira Small Caps — Projeto Phoenix")

st.markdown(
    """
<p style="color:#9ca3af;font-size:13px;">
Abaixo você encontra os Trades Pendentes, Trades em Andamento e o Resumo 
de Performance dos últimos 30 dias referentes à Carteira de Small Caps 
monitorada pelo Phoenix.
</p>
""",
    unsafe_allow_html=True,
)

# ============================================
# 🔍 1. FILTRA ATIVOS DA CARTEIRA SMLL
# ============================================

pend_small = [a for a in curto_state.ativos if get_indice_ativo(a) == "SMLL"]
and_small  = [a for a in loss_state.ativos  if get_indice_ativo(a) == "SMLL"]


# ============================================
# ⚡ 2. TRADES PENDENTES — SMLL
# ============================================

st.markdown("### ⚡ Trades Pendentes (Small Caps)")

if not pend_small:
    st.info("Nenhum trade pendente na carteira de Small Caps no momento.")
else:
    render_pendentes_cards(pend_small)


# ============================================
# ⭐ 3. TRADES EM ANDAMENTO — SMLL
# ============================================

st.markdown("---")
st.markdown("### ⭐ Trades em Andamento (Small Caps)")

if not and_small:
    st.info("Nenhum trade em andamento para Small Caps no momento.")
else:
    render_andamento_cards(and_small)


# ============================================
# 📊 4. RESUMO DE DESEMPENHO — 30 DIAS (SMLL)
# ============================================

st.markdown("---")
st.markdown("### 🦅 Resumo de Desempenho — Últimos 30 dias (Small Caps)")

render_resumo_30d("SMLL")
