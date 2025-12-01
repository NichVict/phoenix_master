import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from carteiras_bridge import (
    curto_state,
    loss_state,
    get_indice_ativo,
    supabase_select,
)

LINK_ASSINAR = "https://app.infinitepay.io/products"

# ===========================
# 🎨 CSS – ESTILO PREMIUM
# ===========================
st.markdown(
    """
<style>
.dashboard-title {
font-size: 32px;
font-weight: 800;
color: #fbbf24;
text-shadow: 0px 0px 12px rgba(251,191,36,0.5);
}

.card-wrapper {
background: radial-gradient(circle at top left, #1f2937, #020617);
border-radius: 18px;
border: 1px solid rgba(148,163,184,0.45);
padding: 22px 22px 18px 22px;
box-shadow: 0 0 18px rgba(0,0,0,0.65);
margin-bottom: 22px;
}

.card-header {
display:flex;
justify-content:space-between;
align-items:flex-start;
margin-bottom:16px;
}

.card-title-left {
display:flex;
flex-direction:column;
gap:4px;
}

.card-title-main {
font-size: 22px;
font-weight: 800;
color:#e5e7eb;
}

.card-tag {
font-size: 12px;
text-transform: uppercase;
letter-spacing: .08em;
color:#9ca3af;
}

.score-badge {
min-width:110px;
text-align:right;
}

.score-label {
font-size:11px;
color:#9ca3af;
text-transform:uppercase;
}

.score-value {
font-size:26px;
font-weight:900;
}

.score-bar-outer {
margin-top:6px;
width:100%;
height:7px;
border-radius:999px;
background:rgba(31,41,55,0.9);
overflow:hidden;
}

.score-bar-inner {
height:100%;
border-radius:999px;
}

.metrics-grid {
display:grid;
grid-template-columns: repeat(3, minmax(0,1fr));
gap:10px;
margin-top:6px;
margin-bottom:10px;
}

.metric-box {
background: rgba(15,23,42,0.95);
border-radius:10px;
padding:7px 10px;
border:1px solid rgba(55,65,81,0.8);
}

.metric-label {
font-size:11px;
color:#9ca3af;
text-transform:uppercase;
}

.metric-value {
font-size:17px;
font-weight:700;
}

.metric-sub {
font-size:11px;
color:#6b7280;
}

.card-desc {
margin-top:6px;
font-size:12px;
color:#d1d5db;
}

.btn-assinar {
margin-top:10px;
display:inline-block;
padding:8px 16px;
border-radius:999px;
background:linear-gradient(90deg,#f59e0b,#ef4444);
color:white !important;
font-size:12px;
font-weight:900;
text-transform:uppercase;
letter-spacing:.09em;
text-decoration:none;
transition:all .18s ease-out;
}

.btn-assinar:hover {
transform:translateY(-1px) scale(1.03);
box-shadow:0 0 14px rgba(248,113,113,0.8);
}

.charts-row {
display:grid;
grid-template-columns: 1.2fr .8fr;
gap:12px;
margin-top:10px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ===========================
# 🦅 TÍTULO
# ===========================
st.markdown(
    "<div class='dashboard-title'>🦅 Dashboard Geral — Phoenix Premium</div>",
    unsafe_allow_html=True,
)
st.markdown(
    """
<p style="color:#9ca3af;font-size:14px;">
Visão consolidada das carteiras monitoradas pelo Phoenix: performance recente, 
distribuição de trades e um <b>Phoenix Score</b> para cada estratégia.
</p>
""",
    unsafe_allow_html=True,
)

# ===========================
# 🔍 RESUMO DE CARTEIRA (PENDENTES / ANDAMENTO)
# ===========================
def resumo_carteira_estado(indice: str):
    pend = [a for a in curto_state.ativos if get_indice_ativo(a) == indice]
    andamento = [a for a in loss_state.ativos if get_indice_ativo(a) == indice]
    return {
        "pendentes": len(pend),
        "andamento": len(andamento),
        "total": len(pend) + len(andamento),
    }

# ===========================
# 📊 CARREGA MÉTRICAS 30 DIAS DO SUPABASE
# ===========================
def load_stats_30d(indice_atual: str):
    """
    Replica a lógica principal do render_resumo_30d, mas retornando os dados
    em vez de desenhar a UI.
    """
    # Opções ainda não estão em operacoes_encerradas -> devolve sem dados
    if indice_atual == "OPCOES":
        return {
            "has_data": False,
            "lucro_total_pct": 0.0,
            "media_pct": 0.0,
            "winrate": 0.0,
            "qtd_trades": 0,
            "sparkline": [],
        }

    hoje = datetime.date.today()
    inicio_30d = hoje - datetime.timedelta(days=30)

    dados_30d = supabase_select(
        "operacoes_encerradas",
        f"?select=*"
        f"&data_fechamento=gte.{inicio_30d}T00:00:00"
        f"&data_fechamento=lte.{hoje}T23:59:59",
    ) or []

    # --- filtro por carteira (mesma ideia do Dash_Acoes)
    def filtrar_por_indice(lista, indice):
        if indice == "TOTAL":
            return lista
        out = []
        for x in lista:
            idx = (
                x.get("indice")
                or x.get("carteira")
                or x.get("index")
                or x.get("indice_ticker")
            )
            idx_norm = get_indice_ativo({"indice": idx})
            if idx_norm == indice:
                out.append(x)
        return out

    dados_30d_filtrado = filtrar_por_indice(dados_30d, indice_atual)

    # converter datas
    for x in dados_30d_filtrado:
        try:
            x["data_fechamento"] = datetime.datetime.fromisoformat(
                x["data_fechamento"]
            )
        except Exception:
            pass

    pontos_pct = []
    for x in dados_30d_filtrado:
        pnl = x.get("pnl")
        preco_abertura = x.get("preco_abertura")
        if pnl is not None and preco_abertura:
            pct = (pnl / preco_abertura) * 100.0
            pontos_pct.append(
                {
                    "data": x.get("data_fechamento"),
                    "pct": pct,
                }
            )

    if not pontos_pct:
        return {
            "has_data": False,
            "lucro_total_pct": 0.0,
            "media_pct": 0.0,
            "winrate": 0.0,
            "qtd_trades": 0,
            "sparkline": [],
        }

    # ordena por data
    pontos_pct = sorted(
        pontos_pct,
        key=lambda d: d["data"] or datetime.datetime.min,
    )

    valores = [p["pct"] for p in pontos_pct]
    lucro_total_pct = sum(valores)
    media_pct = sum(valores) / len(valores)
    qtd_trades = len(valores)
    wins = [v for v in valores if v > 0]
    winrate = len(wins) / qtd_trades if qtd_trades else 0.0

    return {
        "has_data": True,
        "lucro_total_pct": lucro_total_pct,
        "media_pct": media_pct,
        "winrate": winrate,
        "qtd_trades": qtd_trades,
        "sparkline": pontos_pct,
    }

# ===========================
# 🔥 PHOENIX SCORE
# ===========================
def phoenix_score(stats, resumo_estado):
    """
    Score 0–100 baseado em:
      - lucro_total_pct
      - média pct por trade
      - winrate
      - quantidade de trades recentes
      - atividade atual (pendentes/andamento)
    """
    if not stats["has_data"]:
        # sem histórico recente -> score moderado, depende da atividade
        base = 40.0
        bonus_atividade = min(resumo_estado["total"] * 2.5, 20.0)
        score = base + bonus_atividade
    else:
        lt = stats["lucro_total_pct"]
        media = stats["media_pct"]
        win = stats["winrate"]
        trades = stats["qtd_trades"]
        ativos = resumo_estado["total"]

        comp_lucro = max(min(lt / 5.0, 30.0), -20.0)
        comp_media = max(min(media * 0.8, 25.0), -15.0)
        comp_win = (win - 0.5) * 80.0  # -40 a +40 aproximadamente
        comp_trades = min(trades * 2.0, 20.0)
        comp_ativos = min(ativos * 1.5, 15.0)

        score = 50.0 + comp_lucro + comp_media + comp_win + comp_trades + comp_ativos

    score = max(0.0, min(100.0, score))
    return round(score, 1)

def score_color(score: float):
    if score >= 80:
        return "#22c55e"
    if score >= 60:
        return "#eab308"
    if score >= 40:
        return "#f97316"
    return "#ef4444"

def tendencia_text(stats):
    if not stats["has_data"]:
        return "Sem histórico recente suficiente."
    m = stats["media_pct"]
    if m > 2.0:
        return "Tendência forte de ganhos nas últimas operações."
    if m > 0.5:
        return "Tendência levemente positiva, com ganhos consistentes."
    if m > -0.5:
        return "Carteira estável, sem viés forte de ganho ou perda."
    if m > -2.0:
        return "Pressão vendedora moderada nas últimas operações."
    return "Perdas relevantes recentemente — exige maior disciplina de risco."

# ===========================
# 📊 CRIADORES DE GRÁFICOS
# ===========================
def sparkline_figure(stats):
    if not stats["has_data"] or not stats["sparkline"]:
        return None

    df = pd.DataFrame(stats["sparkline"])
    df = df.sort_values("data")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["data"],
            y=df["pct"],
            mode="lines+markers",
            line=dict(width=2),
            marker=dict(size=5),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=20, b=20),
        height=190,
        showlegend=False,
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="Retorno (%)", showgrid=True),
    )
    return fig

def barras_pend_andamento(resumo_estado):
    pend = resumo_estado["pendentes"]
    andam = resumo_estado["andamento"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=["Pendentes", "Andamento"],
            y=[pend, andam],
            text=[pend, andam],
            textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=20, b=20),
        height=190,
        showlegend=False,
        xaxis=dict(title=""),
        yaxis=dict(title="Qtde trades"),
    )
    return fig

# ===========================
# 🧱 RENDERIZA UM BLOCO COMPLETO DE CARTEIRA
# ===========================
def render_carteira(nome, emoji_cor, indice_key, tag_extra):
    resumo_estado = resumo_carteira_estado(indice_key)
    stats = load_stats_30d(indice_key)
    score = phoenix_score(stats, resumo_estado)
    cor_score = score_color(score)

    if stats["has_data"]:
        winrate_pct = stats["winrate"] * 100.0
        media_pct = stats["media_pct"]
        lucro_total_pct = stats["lucro_total_pct"]
        qtd_trades = stats["qtd_trades"]
    else:
        winrate_pct = 0.0
        media_pct = 0.0
        lucro_total_pct = 0.0
        qtd_trades = 0

    desc = tendencia_text(stats)

    st.markdown(
        f"""<div class="card-wrapper">
<div class="card-header">
  <div class="card-title-left">
    <div class="card-title-main">{emoji_cor} {nome}</div>
    <div class="card-tag">Phoenix Strategy · {tag_extra}</div>
  </div>
  <div class="score-badge">
    <div class="score-label">Phoenix Score</div>
    <div class="score-value" style="color:{cor_score};">{score}</div>
    <div class="score-bar-outer">
      <div class="score-bar-inner" style="width:{score}%;background:{cor_score};"></div>
    </div>
  </div>
</div>

<div class="metrics-grid">
  <div class="metric-box">
    <div class="metric-label">Lucro total 30d</div>
    <div class="metric-value" style="color:{('#22c55e' if lucro_total_pct>=0 else '#ef4444')};">
      {lucro_total_pct:.1f}%
    </div>
    <div class="metric-sub">soma dos trades fechados</div>
  </div>

  <div class="metric-box">
    <div class="metric-label">Winrate 30d</div>
    <div class="metric-value">{winrate_pct:.1f}%</div>
    <div class="metric-sub">{qtd_trades} operações fechadas</div>
  </div>

  <div class="metric-box">
    <div class="metric-label">Média por trade</div>
    <div class="metric-value" style="color:{('#22c55e' if media_pct>=0 else '#ef4444')};">
      {media_pct:.2f}%
    </div>
    <div class="metric-sub">últimos 30 dias</div>
  </div>

  <div class="metric-box">
    <div class="metric-label">Pendentes</div>
    <div class="metric-value">{resumo_estado['pendentes']}</div>
    <div class="metric-sub">aguardando gatilho</div>
  </div>

  <div class="metric-box">
    <div class="metric-label">Em andamento</div>
    <div class="metric-value">{resumo_estado['andamento']}</div>
    <div class="metric-sub">posições abertas</div>
  </div>

  <div class="metric-box">
    <div class="metric-label">Total monitorado</div>
    <div class="metric-value">{resumo_estado['total']}</div>
    <div class="metric-sub">ativos sob vigilância</div>
  </div>
</div>

<div class="card-desc">{desc}</div>

<a href="{LINK_ASSINAR}" target="_blank" class="btn-assinar">
ASSINAR AGORA!
</a>
</div>
""",
        unsafe_allow_html=True,
    )

    # ---- linha com dois gráficos ----
    charts = st.container()
    with charts:
        c1, c2 = st.columns([1.3, 0.7])
        with c1:
            fig_spark = sparkline_figure(stats)
            if fig_spark:
                st.markdown("##### 📈 Performance recente (30d)")
                st.plotly_chart(fig_spark, use_container_width=True)
            else:
                st.markdown("##### 📈 Performance recente (30d)")
                st.info("Ainda não há operações encerradas suficientes para esta carteira.")
        with c2:
            fig_bar = barras_pend_andamento(resumo_estado)
            st.markdown("##### 📊 Trades ativos")
            st.plotly_chart(fig_bar, use_container_width=True)

# ===========================
# 🧱 LAYOUT 2x2 — 4 CARTEIRAS
# ===========================
col1, col2 = st.columns(2)

with col1:
    render_carteira("Carteira IBOV", "🟦", "IBOV", "Large Caps Brasil")

with col2:
    render_carteira("Carteira BDR", "🟨", "BDR", "Exposição Internacional")

col3, col4 = st.columns(2)

with col3:
    render_carteira("Small Caps", "🟩", "SMLL", "Agressiva / Crescimento")

with col4:
    render_carteira("Carteira de Opções", "🟪", "OPCOES", "Estratégias Assimétricas")
