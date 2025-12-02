import streamlit as st
import requests

SUPABASE_URL = st.secrets["SUPABASE_URL_CLIENTES"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY_CLIENTES"]

REST_URL = f"{SUPABASE_URL}/rest/v1/clientes"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

def buscar_cliente(token):
    url = f"{REST_URL}?token=eq.{token}&select=*"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return None
    data = r.json()
    return data[0] if data else None

params = st.query_params
token = params.get("token")

if not token:
    st.error("❌ Acesso bloqueado. Token ausente.")
    st.stop()

cliente = buscar_cliente(token)

if not cliente:
    st.error("❌ Token inválido ou expirado.")
    st.stop()

if "Carteira de Ações IBOV" not in cliente.get("carteiras", []):
    st.error("❌ Você não possui acesso à Carteira IBOV.")
    st.markdown(f"[Voltar ao login](./teste_login?token={token})")
    st.stop()

st.success(f"🔓 Acesso autorizado — Bem-vindo, {cliente['nome']}!")


# IMPORTA FUNÇÕES E STATES A PARTIR DO BRIDGE
from carteiras_bridge import (
    curto_state,
    loss_state,
    get_indice_ativo,
    render_pendentes_cards,
    render_andamento_cards,
    render_resumo_30d
)

# ============================================
# 📄 PÁGINA DA CARTEIRA IBOV — PROJETO PHOENIX
# ============================================

st.markdown("## 🟦 Carteira IBOV — Projeto Phoenix")

st.markdown(
    """
<p style="color:#9ca3af;font-size:13px;">
Abaixo você encontra os Trades Pendentes, Trades em Andamento e o Resumo 
de Performance dos últimos 30 dias referentes à Carteira de Ações do IBOV monitorada pelo Phoenix.
</p>
""",
    unsafe_allow_html=True,
)

# ============================================
# 🔍 1. FILTRA ATIVOS DA CARTEIRA IBOV
# ============================================

pend_ibov = [a for a in curto_state.ativos if get_indice_ativo(a) == "IBOV"]
and_ibov  = [a for a in loss_state.ativos  if get_indice_ativo(a) == "IBOV"]


# ============================================
# ⚡ 2. TRADES PENDENTES — IBOV
# ============================================

st.markdown("### ⚡ Trades Pendentes (IBOV)")

if not pend_ibov:
    st.info("Nenhum trade pendente na carteira IBOV no momento.")
else:
    render_pendentes_cards(pend_ibov)


# ============================================
# ⭐ 3. TRADES EM ANDAMENTO — IBOV
# ============================================

st.markdown("---")
st.markdown("### ⭐ Trades em Andamento (IBOV)")

if not and_ibov:
    st.info("Nenhum trade em andamento para o IBOV no momento.")
else:
    render_andamento_cards(and_ibov)


# ============================================
# 📊 4. RESUMO DE DESEMPENHO — 30 DIAS
# ============================================

st.markdown("---")
st.markdown("### 🦅 Resumo de Desempenho — Últimos 30 dias (IBOV)")

render_resumo_30d("IBOV")
