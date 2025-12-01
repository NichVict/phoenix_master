import streamlit as st
from carteiras_bridge import (
    curto_state,
    loss_state,
    get_indice_ativo
)

# ============================================
# 🎨 ESTILO GLOBAL (CSS PREMIUM)
# ============================================
st.markdown("""
<style>

.dashboard-title {
    font-size: 32px;
    font-weight: 800;
    color: #fbbf24;
    text-shadow: 0px 0px 12px rgba(251,191,36,0.5);
}

.card-container {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
}

.fenix-card {
    background: linear-gradient(145deg, #0f172a, #1e293b);
    border: 1px solid rgba(148,163,184,0.25);
    border-radius: 18px;
    padding: 26px;
    width: 100%;
    max-width: 420px;
    box-shadow: 0 0 12px rgba(0,0,0,0.55);
    transition: transform 0.2s ease, box-shadow 0.25s ease;
}

.fenix-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 0 22px rgba(255,255,255,0.18);
    border-color: rgba(255,255,255,0.35);
}

.card-title {
    font-size: 26px;
    font-weight: 800;
    margin-bottom: 8px;
}

.card-sub {
    font-size: 13px;
    color: #9ca3af;
    margin-bottom: 18px;
}

.metric-line {
    padding: 7px 0;
    font-size: 15px;
    color: #e5e7eb;
    border-bottom: 1px dashed rgba(148,163,184,0.25);
}

.metric-value {
    font-weight: 700;
    font-size: 17px;
}

.btn-assinar {
    margin-top: 20px;
    background: linear-gradient(90deg, #f59e0b, #ef4444);
    padding: 10px 16px;
    color: white !important;
    font-weight: 900;
    border-radius: 12px;
    display: inline-block;
    text-align: center;
    text-decoration: none;
    transition: all 0.2s ease;
}

.btn-assinar:hover {
    transform: scale(1.05);
    box-shadow: 0 0 14px rgba(249,115,22,0.7);
}

</style>
""", unsafe_allow_html=True)

# ============================================
# 🦅 TÍTULO
# ============================================
st.markdown("<div class='dashboard-title'>🦅 Dashboard Geral — Phoenix Premium</div>", unsafe_allow_html=True)

st.markdown("""
<p style="color:#9ca3af;font-size:14px;">
Visualização geral das carteiras monitoradas pelo Phoenix. 
Cada card apresenta uma visão rápida da situação atual e um botão para assinar o serviço completo.
</p>
""", unsafe_allow_html=True)

# ============================================
# 🔍 FUNÇÃO PARA RESUMIR CADA CARTEIRA
# ============================================
def resumo_carteira(indice: str):
    pend = [a for a in curto_state.ativos if get_indice_ativo(a) == indice]
    andamento = [a for a in loss_state.ativos if get_indice_ativo(a) == indice]

    return {
        "pendentes": len(pend),
        "andamento": len(andamento),
        "total": len(pend) + len(andamento)
    }

# ============================================
# 📦 RESUMO DAS 4 CARTEIRAS
# ============================================
res_ibov = resumo_carteira("IBOV")
res_bdr  = resumo_carteira("BDR")
res_small = resumo_carteira("SMLL")
res_opts = resumo_carteira("OPCOES")  # depende do índice que você usa no código original

# ============================================
# 🎁 LINK DE ASSINATURA
# ============================================
LINK_ASSINAR = "https://app.infinitepay.io/products"

# ============================================
# 🟦 FUNÇÃO PARA DESENHAR UM CARD
# ============================================
def render_card(nome, cor_icone, resumo_dict, pagina):
    st.markdown(f"""
    <div class='fenix-card'>
        <div class='card-title'>{cor_icone} {nome}</div>
        <div class='card-sub'>Resumo rápido das operações monitoradas</div>

        <div class='metric-line'>Trades Pendentes: 
            <span class='metric-value'>{resumo_dict['pendentes']}</span>
        </div>
        <div class='metric-line'>Trades em Andamento: 
            <span class='metric-value'>{resumo_dict['andamento']}</span>
        </div>
        <div class='metric-line'>Total Monitorado: 
            <span class='metric-value'>{resumo_dict['total']}</span>
        </div>

        <a href="{LINK_ASSINAR}" target="_blank" class="btn-assinar">
            ASSINAR AGORA!
        </a>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# 📂 RENDERIZA OS 4 CARDS
# ============================================
col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

with col1:
    render_card("Carteira IBOV", "🟦", res_ibov, "carteira_ibov.py")

with col2:
    render_card("Carteira BDR", "🟨", res_bdr, "carteira_bdr.py")

with col3:
    render_card("Small Caps", "🟩", res_small, "carteira_small.py")

with col4:
    render_card("Carteira de Opções", "🟪", res_opts, "carteira_opcoes.py")

