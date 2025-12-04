import streamlit as st
from auth import user_logged

PAGE_ID = "dashboard_geral"

st.set_page_config(page_title="Dashboard Geral", page_icon="📊")

# ======================================================
# 👤 IDENTIDADE DO CLIENTE (logado OU visitante)
# ======================================================
cliente = st.session_state.get("cliente", {})

if user_logged():
    nome = cliente.get("nome", "Investidor")
    carteiras = cliente.get("page_ids", [])
else:
    nome = None
    carteiras = []

# ======================================================
# 🏷️ CABEÇALHO
# ======================================================
#st.title("🦅 Dashboard Geral — Fênix Premium")

if nome:
    st.success(f"Bem-vindo, **{nome}**! 👋")
else:
    st.info("Bem-vindo ao Phoenix Strategy! Faça login pelo link mágico para ver suas carteiras.")

# ======================================================
# 📂 CARTEIRAS DISPONÍVEIS
# ======================================================
st.markdown("### 📁 Suas assinaturas / carteiras:")

if not user_logged():
    st.warning("Faça login para ver suas carteiras personalizadas.")
else:
    if len(carteiras) <= 1:  # só tem dashboard_geral
        st.warning(
            """
            **Você ainda não possui nenhuma assinatura ativa.**  
            Explore nossas carteiras no menu lateral e conheça nossos produtos.
            """
        )
    else:
        for c in carteiras:
            if c != "dashboard_geral":
                st.markdown(f"- **{c.replace('_', ' ').title()}**")

# ======================================================
# 📣 SEÇÃO DE CHAMADA / OFERTA
# ======================================================
st.divider()
#st.markdown("""
### 💼 Conheça nossas carteiras premium
#Nossas carteiras exclusivas oferecem recomendações, análises atualizadas e performance comprovada.
#Use o menu lateral para explorar as opções disponíveis.
#""")



import datetime
import pandas as pd
import plotly.graph_objects as go


from carteiras_bridge import (
    curto_state,
    loss_state,
    get_indice_ativo,
    supabase_select,
)



import requests
import fenix_opcoes.supabase_ops as supabase_ops_mod

# ===== IMPORT PARA TABELA SQL DE OPÇÕES =====
def supabase_select_opcoes(query_string: str):
    """
    Wrapper igual ao supabase_select, mas apontando para a tabela opcoes_operacoes.
    """
    return supabase_select("opcoes_operacoes", query_string)

REST_ENDPOINT_OP = getattr(supabase_ops_mod, "REST_ENDPOINT", None)
HEADERS_OP = getattr(supabase_ops_mod, "HEADERS", None)

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
margin-bottom: 28px;
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
text-decoration:none !important;   /* 👈 FORÇA O NÃO-SUBLINHADO */
transition:all .18s ease-out;
}


.btn-assinar:hover {
transform:translateY(-1px) scale(1.03);
box-shadow:0 0 14px rgba(248,113,113,0.8);
}

.charts-row {
display:grid;
grid-template-columns: 1.3fr .7fr;
gap:12px;
margin-top:10px;
}

.rank-box {
background: rgba(15,23,42,0.95);
border-radius:14px;
padding:16px 18px;
border:1px solid rgba(75,85,99,0.9);
margin-top:6px;
}

.rank-title {
font-size:18px;
font-weight:700;
color:#e5e7eb;
margin-bottom:8px;
}

.rank-line {
font-size:13px;
color:#d1d5db;
margin:2px 0;
}

.rank-tag {
font-size:11px;
text-transform:uppercase;
color:#9ca3af;
}

.global-score-wrap {
background: radial-gradient(circle at top left, #111827, #020617);
border-radius:18px;
border:1px solid rgba(148,163,184,0.6);
padding:18px 20px;
margin-top:18px;
box-shadow:0 0 20px rgba(0,0,0,0.75);
}

.global-score-value {
font-size:32px;
font-weight:900;
}

.global-score-bar-outer {
margin-top:10px;
width:100%;
height:10px;
border-radius:999px;
background:#020617;
overflow:hidden;
}

.global-score-bar-inner {
height:100%;
border-radius:999px;
}

/* ===== PRIME CARDS DO RANKING ===== */
/* ===== Ranking Institucional ===== */
.rank-card {
    background: rgba(10,15,25,0.75);
    border: 1px solid rgba(120,130,150,0.22);
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 18px;
    transition: all 0.18s ease-out;
}

.rank-card:hover {
    background: rgba(14,20,30,0.90);
    border-color: rgba(150,160,180,0.30);
    transform: translateY(-1px);
}

.rank-title {
    font-size: 17px;
    font-weight: 600;
    color: #e5e7eb;
    margin-bottom: 4px;
}

.rank-sub {
    font-size: 14px;
    font-weight: 400;
    color: #9ca3af;
}

.rank-icon {
    font-size: 17px;
    opacity: 0.75;
    margin-right: 6px;
}





</style>
""",
    unsafe_allow_html=True,
)

# ===========================
# 🦅 TÍTULO
# ===========================
st.markdown(
    "<div class='dashboard-title'>🦅 Dashboard Phoenix Strategy</div>",
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
# 🔍 RESUMO ESTADO (PENDENTES / ANDAMENTO)
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
# 📊 30 DIAS – SUPABASE
# ===========================
def load_ops_30d():
    hoje = datetime.date.today()
    inicio_30d = hoje - datetime.timedelta(days=30)
    dados = supabase_select(
        "operacoes_encerradas",
        f"?select=*"
        f"&data_fechamento=gte.{inicio_30d}T00:00:00"
        f"&data_fechamento=lte.{hoje}T23:59:59",
    ) or []
    return dados

def build_stats_for_indice(dados_gerais, indice_atual: str):

    filtrados = [x for x in dados_gerais if (x.get("indice") or "").upper() == indice_atual.upper()]

    pontos_pct = []
    for x in filtrados:
        pnl = x.get("pnl")
        preco_abertura = x.get("preco_abertura")
        data_raw = x.get("data_fechamento")
        try:
            data_dt = datetime.datetime.fromisoformat(data_raw) if isinstance(data_raw, str) else data_raw
        except Exception:
            data_dt = None

        if pnl is not None and preco_abertura:
            try:
                pct = (float(pnl) / float(preco_abertura)) * 100.0
            except Exception:
                pct = 0.0
            pontos_pct.append({"data": data_dt, "pct": pct})

    if not pontos_pct:
        return {
            "has_data": False,
            "lucro_total_pct": 0.0,
            "media_pct": 0.0,
            "winrate": 0.0,
            "qtd_trades": 0,
            "sparkline": [],
        }

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

def build_stats_opcoes_30d():
    """
    Carrega operações encerradas de opções diretamente da tabela 'opcoes_operacoes'
    do Supabase, filtrando os últimos 30 dias. Calcula:
    - lucro_total_pct
    - media_pct
    - winrate
    - qtd_trades
    - sparkline (retorno por data)
    """

    hoje = datetime.date.today()
    inicio_30d = hoje - datetime.timedelta(days=30)

    q = (
        f"?select=symbol,preco_entrada,preco_saida,retorno_final_pct,"
        f"timestamp_saida,created_at,status,indice"
        f"&status=eq.encerrada"
        f"&timestamp_saida=gte.{inicio_30d}T00:00:00"
        f"&timestamp_saida=lte.{hoje}T23:59:59"
    )

    dados = supabase_select_opcoes(q) or []

    if not dados:
        return {
            "has_data": False,
            "lucro_total_pct": 0.0,
            "media_pct": 0.0,
            "winrate": 0.0,
            "qtd_trades": 0,
            "sparkline": [],
        }

    df = pd.DataFrame(dados)

    # Converte datas
    df["timestamp_saida"] = pd.to_datetime(df["timestamp_saida"], errors="coerce")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    # Se não tiver timestamp, descarta
    df = df.dropna(subset=["timestamp_saida"]).copy()

    # Calcula pnl_pct
    if "retorno_final_pct" in df.columns:
        df["pnl_pct"] = pd.to_numeric(df["retorno_final_pct"], errors="coerce").fillna(0.0)
    else:
        df["preco_entrada"] = pd.to_numeric(df.get("preco_entrada"), errors="coerce")
        df["preco_saida"] = pd.to_numeric(df.get("preco_saida"), errors="coerce")
        df["pnl_pct"] = ((df["preco_saida"] - df["preco_entrada"]) /
                         df["preco_entrada"]) * 100

    # Remove qualquer NaN restante
    df["pnl_pct"] = df["pnl_pct"].fillna(0)

    valores = df["pnl_pct"].tolist()

    if not valores:
        return {
            "has_data": False,
            "lucro_total_pct": 0.0,
            "media_pct": 0.0,
            "winrate": 0.0,
            "qtd_trades": 0,
            "sparkline": [],
        }

    lucro_total_pct = sum(valores)
    media_pct = sum(valores) / len(valores)
    qtd_trades = len(valores)
    wins = [v for v in valores if v > 0]
    winrate = len(wins) / qtd_trades if qtd_trades else 0.0

    # Sparkline
    spark = [
        {"data": row["timestamp_saida"], "pct": row["pnl_pct"]}
        for _, row in df.sort_values("timestamp_saida").iterrows()
    ]

    return {
        "has_data": True,
        "lucro_total_pct": lucro_total_pct,
        "media_pct": media_pct,
        "winrate": winrate,
        "qtd_trades": qtd_trades,
        "sparkline": spark,
    }


def assimetria(stats):
    """
    Razão ganho/perda (Gain/Loss Ratio):
    > 1 = carteira assimétrica positiva.
    < 1 = perdas maiores que ganhos.
    """
    if not stats["has_data"]:
        return 0.0

    valores = [p["pct"] for p in stats["sparkline"]]

    ganhos = [v for v in valores if v > 0]
    perdas = [-v for v in valores if v < 0]

    total_ganhos = sum(ganhos)
    total_perdas = sum(perdas)

    if total_perdas == 0:
        return float('inf')  # se não teve perda nenhuma, assimetria infinita

    return total_ganhos / total_perdas





def load_opcoes_abertas():
    """
    Retorna todas as operações de opções com status = 'aberta'
    diretamente da tabela opcoes_operacoes.
    """
    q = "?select=symbol,retorno_atual_pct,status&status=eq.aberta"
    dados = supabase_select_opcoes(q) or []
    return dados

def best_trade_opcoes(stats):
    """
    A partir do stats (que já contém sparkline + pnl_pct),
    extraímos a operação mais lucrativa.
    """
    if not stats["has_data"] or not stats["qtd_trades"]:
        return None

    # sparkline contém: {"data": ..., "pct": valor}
    # Vamos ter que pegar o ticker junto
    # Portanto refazemos a consulta com select de ticker + pnl_pct
    hoje = datetime.date.today()
    inicio_30d = hoje - datetime.timedelta(days=30)

    q = (
        f"?select=symbol,preco_entrada,preco_saida,retorno_final_pct,"
        f"timestamp_saida,status"
        f"&status=eq.encerrada"
        f"&timestamp_saida=gte.{inicio_30d}T00:00:00"
        f"&timestamp_saida=lte.{hoje}T23:59:59"
    )

    dados = supabase_select_opcoes(q) or []

    if not dados:
        return None

    # calcular corretamento pnl_pct
    df = pd.DataFrame(dados)

    if "retorno_final_pct" in df.columns:
        df["pnl_pct"] = pd.to_numeric(df["retorno_final_pct"], errors="coerce").fillna(0.0)
    else:
        df["preco_entrada"] = pd.to_numeric(df.get("preco_entrada"), errors="coerce")
        df["preco_saida"] = pd.to_numeric(df.get("preco_saida"), errors="coerce")
        df["pnl_pct"] = (
            (df["preco_saida"] - df["preco_entrada"]) /
            df["preco_entrada"]
        ).fillna(0.0) * 100.0

    df = df.dropna(subset=["pnl_pct"])

    if df.empty:
        return None

    row = df.sort_values("pnl_pct", ascending=False).iloc[0]

    return {
        "ticker": row.get("symbol"),
        "pnl_pct": float(row.get("pnl_pct", 0.0)),
    }




# ===========================
# 🔥 PHOENIX SCORE
# ===========================
def phoenix_score(stats, resumo_estado):
    if not stats["has_data"]:
        base = 40.0
        bonus_atividade = min(resumo_estado["total"] * 2.5, 20.0)
        score = base + bonus_atividade
    else:
        lt = stats["lucro_total_pct"]
        media = stats["media_pct"]
        win = stats["winrate"]
        trades = stats["qtd_trades"]
        ativos = resumo_estado["total"]

        comp_lucro = max(min(lt / 12.0, 20.0), -10.0)       # antes: /5 → agora mais difícil
        comp_media = max(min(media * 0.4, 15.0), -10.0)     # antes: *0.8 → agora metade
        comp_win = (win - 0.55) * 60.0                      # antes: -0.5 e 80pts → mais exigente
        comp_trades = min(trades * 1.0, 10.0)               # antes: *2 → agora menos impacto
        comp_ativos = min(ativos * 1.0, 10.0)               # antes: 1.5 → menor peso
        
        score = 50.0 + comp_lucro + comp_media + comp_win + comp_trades + comp_ativos


    return max(0.0, min(100.0, round(score, 1)))

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
        return "Sem histórico recente suficiente. A carteira está em construção."
    m = stats["media_pct"]
    if m > 2.0:
        return "Tendência forte de ganhos nas últimas operações, com alta assimetria positiva."
    if m > 0.5:
        return "Tendência levemente positiva, com ganhos consistentes e risco controlado."
    if m > -0.5:
        return "Carteira estável, sem viés forte de ganho ou perda, ideal para quem busca equilíbrio."
    if m > -2.0:
        return "Pressão vendedora moderada nas últimas operações — gestão de risco é essencial."
    return "Perdas relevantes recentemente — exige disciplina absoluta e uso rigoroso de stops."

# ===========================
# 📊 GRÁFICOS
# ===========================
def sparkline_figure(stats):
    if not stats["has_data"] or not stats["sparkline"]:
        return None

    df = pd.DataFrame(stats["sparkline"])
    df = df.sort_values("data")

    # ===== CÁLCULO DO RETORNO ACUMULADO =====
    df["acumulado"] = df["pct"].cumsum()

    # ===== SUAVIZAÇÃO DA LINHA =====
    df["acumulado_smooth"] = (
        df["acumulado"].rolling(window=3, min_periods=1).mean()
    ).interpolate(method="linear")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["data"],
            y=df["acumulado_smooth"],
            mode="lines",
            line=dict(width=4),  # mais robusta
        )
    )

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=20, b=20),
        height=190,
        showlegend=False,
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="Retorno acumulado (%)", showgrid=True),
    )
    return fig




def barras_lucro_prejuizo(stats):
    if not stats["has_data"] or not stats["sparkline"]:
        valores = []
    else:
        valores = [p["pct"] for p in stats["sparkline"]]

    prejuizos = [-v for v in valores if v < 0]
    lucros = [v for v in valores if v > 0]

    qtd_prej = len(prejuizos)
    qtd_lucro = len(lucros)

    media_prejuizo = (sum(prejuizos) / qtd_prej) if qtd_prej else 0
    media_lucro = (sum(lucros) / qtd_lucro) if qtd_lucro else 0

    # ===== PESO (ponderação por número de operações) =====
    bar_prejuizo = -(abs(media_prejuizo) * qtd_prej)
    bar_lucro = media_lucro * qtd_lucro

    # ===== TEXTOS EXIBIDOS (somente resultado final) =====
    label_preju = f"{bar_prejuizo:.2f}%"
    label_lucro = f"{bar_lucro:.2f}%"

    fig = go.Figure()

    # ===== BARRA DE PREJUÍZO (LARANJA/VERMELHA) =====
    fig.add_trace(
        go.Bar(
            x=[""],    # remove label dos eixos
            y=[bar_prejuizo],
            text=[label_preju],
            marker=dict(color="#f97316"),   # laranja
            textposition="outside",
            cliponaxis=False,
            name="",
        )
    )

    # ===== BARRA DE LUCRO (VERDE) =====
    fig.add_trace(
        go.Bar(
            x=[""],    # mesmo eixo
            y=[bar_lucro],
            text=[label_lucro],
            marker=dict(color="#22c55e"),   # verde
            textposition="outside",
            cliponaxis=False,
            name="",
        )
    )

    fig.update_layout(
        barmode="group",        # coloca lado a lado
        template="plotly_dark",
        margin=dict(l=10, r=10, t=20, b=40),
        height=240,
        showlegend=False,
        xaxis=dict(
            title="",
            showticklabels=False,  # remove nomes "Média Prejuízo / Lucro"
            zeroline=False,
        ),
        yaxis=dict(
            title="Retorno ponderado (%)",
            zeroline=True,
        ),
    )

    return fig





# ===========================
# 🧱 SUPER CARD DE CARTEIRA (1 COLUNA)
# ===========================
def render_carteira(card_data):
    nome = card_data["nome"]
    emoji = card_data["emoji"]
    tag_extra = card_data["tag"]
    resumo_estado = card_data["resumo"]
    stats = card_data["stats"]
    score = card_data["score"]
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

    # MÉTRICAS PRINCIPAIS
    m1 = f"""<div class='metric-box'>
<div class='metric-label'>Lucro total 30d</div>
<div class='metric-value' style='color:{'#22c55e' if lucro_total_pct>=0 else '#ef4444'};'>{lucro_total_pct:.1f}%</div>
<div class='metric-sub'>soma dos trades fechados</div>
</div>"""

    m2 = f"""<div class='metric-box'>
<div class='metric-label'>Winrate 30d</div>
<div class='metric-value'>{winrate_pct:.1f}%</div>
<div class='metric-sub'>{qtd_trades} operações fechadas</div>
</div>"""

    m3 = f"""<div class='metric-box'>
<div class='metric-label'>Média por trade</div>
<div class='metric-value' style='color:{'#22c55e' if media_pct>=0 else '#ef4444'};'>{media_pct:.2f}%</div>
<div class='metric-sub'>últimos 30 dias</div>
</div>"""

    # MÉTRICAS ESPECIAIS OPÇÕES
    if card_data["id"] == "OPCOES":
        total_operacoes = qtd_trades
        abertas = load_opcoes_abertas()
        qtd_abertas = len(abertas)
        melhor_op = best_trade_opcoes(stats)
        melhor_label = f"{melhor_op['ticker']} ({melhor_op['pnl_pct']:.1f}%)" if melhor_op else "—"

        m4 = f"""<div class='metric-box'>
<div class='metric-label'>TOTAL DE OPERAÇÕES</div>
<div class='metric-value'>{total_operacoes}</div>
<div class='metric-sub'>últimos 30 dias</div>
</div>"""

        m5 = f"""<div class='metric-box'>
<div class='metric-label'>EM ANDAMENTO</div>
<div class='metric-value'>{qtd_abertas}</div>
<div class='metric-sub'>posições abertas</div>
</div>"""

        m6 = f"""<div class='metric-box'>
<div class='metric-label'>OP. MAIS LUCRATIVA</div>
<div class='metric-value'>{melhor_label}</div>
<div class='metric-sub'>últimos 30 dias</div>
</div>"""

    # MÉTRICAS AÇÕES
    else:
        m4 = f"""<div class='metric-box'>
<div class='metric-label'>Pendentes</div>
<div class='metric-value'>{resumo_estado['pendentes']}</div>
<div class='metric-sub'>aguardando gatilho</div>
</div>"""

        m5 = f"""<div class='metric-box'>
<div class='metric-label'>Em andamento</div>
<div class='metric-value'>{resumo_estado['andamento']}</div>
<div class='metric-sub'>posições abertas</div>
</div>"""

        m6 = f"""<div class='metric-box'>
<div class='metric-label'>Total monitorado</div>
<div class='metric-value'>{resumo_estado['total']}</div>
<div class='metric-sub'>ativos sob vigilância</div>
</div>"""

    # CARD COMPLETO EM UM ÚNICO HTML
    card_html = f"""
<div class='card-wrapper'>

<div class='card-header'>
  <div class='card-title-left'>
    <div class='card-title-main'>{emoji} {nome}</div>
    <div class='card-tag'>Phoenix Strategy · {tag_extra}</div>
  </div>

  <div class='score-badge'>
    <div class='score-label'>Phoenix Score</div>
    <div class='score-value' style='color:{cor_score};'>{score}</div>
    <div class='score-bar-outer'>
      <div class='score-bar-inner' style='width:{score}%;background:{cor_score};'></div>
    </div>
  </div>
</div>

<div class='metrics-grid'>
  {m1}{m2}{m3}
</div>

<div class='metrics-grid'>
  {m4}{m5}{m6}
</div>

<div class='card-desc'>{desc}</div>

</div>
"""

    st.markdown(card_html, unsafe_allow_html=True)

    # BOTÃO FORA
    st.markdown(
        f"""<a href='{LINK_ASSINAR}' target='_blank' class='btn-assinar'>ASSINAR AGORA!</a>""",
        unsafe_allow_html=True,
    )

    # GRÁFICOS
    #c1, c2 = st.columns([1.35, 0.65])
    #with c1:
        #st.markdown("##### 📈 Performance recente (30d)")
        #fig_spark = sparkline_figure(stats)
        #if fig_spark:
            #st.plotly_chart(fig_spark, use_container_width=True)
    #with c2:
        #st.markdown("###### 📊 Assimetria Positiva")
        #fig_bar = barras_lucro_prejuizo(stats)
        #st.plotly_chart(fig_bar, use_container_width=True)



# ===========================
# 🔢 MONTAGEM DOS DADOS DAS CARTEIRAS
# ===========================

# ===========================
# 📊 CARREGA DADOS DE AÇÕES (30 DIAS)
# ===========================
dados_30d_geral = load_ops_30d()

# ===========================
# 🔢 CONFIGURAÇÃO DAS CARTEIRAS
# ===========================
carteiras_cfg = [
    {
        "id": "IBOV",
        "nome": "Carteira IBOV",
        "emoji": "🟦",
        "tag": "Large Caps Brasil",
    },
    {
        "id": "BDR",
        "nome": "Carteira BDR",
        "emoji": "🟨",
        "tag": "Exposição Internacional",
    },
    {
        "id": "SMLL",
        "nome": "Small Caps",
        "emoji": "🟩",
        "tag": "Agressiva · Crescimento",
    },
    {
        "id": "OPCOES",
        "nome": "Carteira de Opções",
        "emoji": "🟪",
        "tag": "Estratégias Assimétricas",
    },
]

cards_data = []
for cfg in carteiras_cfg:
    resumo = resumo_carteira_estado(cfg["id"])

    if cfg["id"] == "OPCOES":
        stats = build_stats_opcoes_30d()
    else:
        stats = build_stats_for_indice(dados_30d_geral, cfg["id"])

    score = phoenix_score(stats, resumo)
    cards_data.append(
        {
            "id": cfg["id"],
            "nome": cfg["nome"],
            "emoji": cfg["emoji"],
            "tag": cfg["tag"],
            "resumo": resumo,
            "stats": stats,
            "score": score,
        }
    )


# ===========================
# 📦 RENDERIZA CADA CARTEIRA (1 COLUNA)
# ===========================
for card in cards_data:
    render_carteira(card)

# ===========================
# 🏆 RANKING + TOP TRADES + SCORE GLOBAL (RODAPÉ)
# ===========================
st.markdown("---")
# ===========================
# ===========================
# 🏆 Ranking Phoenix — Institucional (sem emojis)
# ===========================

st.markdown("## Ranking Phoenix — Últimos 30 dias")

# --- MÉTRICAS ---
rank_score = sorted(cards_data, key=lambda c: c["score"], reverse=True)[0]
rank_lucro = sorted(cards_data, key=lambda c: c["stats"]["lucro_total_pct"], reverse=True)[0]
rank_win = sorted(cards_data, key=lambda c: c["stats"]["winrate"], reverse=True)[0]
rank_assim = sorted(cards_data, key=lambda c: assimetria(c["stats"]), reverse=True)[0]

# ------------ 1. Melhor Score -------------
st.markdown(f"""
<div class='rank-card'>
  <div class='rank-title'>
    {rank_score['emoji']} {rank_score['nome']}
  </div>
  <div class='rank-sub'>
    Melhor carteira geral<br>
    Phoenix Score: {rank_score['score']}
  </div>
</div>
""", unsafe_allow_html=True)

# ------------ 2. Maior Lucro 30d -------------
st.markdown(f"""
<div class='rank-card'>
  <div class='rank-title'>
    {rank_lucro['emoji']} {rank_lucro['nome']}
  </div>
  <div class='rank-sub'>
    Maior retorno em 30 dias<br>
    Retorno acumulado: {rank_lucro['stats']['lucro_total_pct']:.1f}%
  </div>
</div>
""", unsafe_allow_html=True)

# ------------ 3. Melhor Winrate -------------
st.markdown(f"""
<div class='rank-card'>
  <div class='rank-title'>
    {rank_win['emoji']} {rank_win['nome']}
  </div>
  <div class='rank-sub'>
    Maior consistência (winrate)<br>
    Winrate: {(rank_win['stats']['winrate']*100):.1f}%
  </div>
</div>
""", unsafe_allow_html=True)

# ------------ 4. Melhor Assimetria -------------
assim_val = assimetria(rank_assim["stats"])
assim_str = "∞" if assim_val == float("inf") else f"{assim_val:.2f}x"

st.markdown(f"""
<div class='rank-card'>
  <div class='rank-title'>
    {rank_assim['emoji']} {rank_assim['nome']}
  </div>
  <div class='rank-sub'>
    Melhor assimetria<br>
    Razão ganho/perda: {assim_str}
  </div>
</div>
""", unsafe_allow_html=True)





# ===========================
# 🦅 PHOENIX SCORE GLOBAL — RODAPÉ
# ===========================
st.markdown("## 🦅 Phoenix Score Global")

def compute_global_score(cards):
    pesos = []
    valores = []
    for c in cards:
        trades = c["stats"]["qtd_trades"]
        if trades <= 0:
            continue
        pesos.append(trades)
        valores.append(c["score"])
    if not pesos:
        # fallback: média simples
        if not cards:
            return 50.0
        return sum(c["score"] for c in cards) / len(cards)
    total_peso = sum(pesos)
    score = sum(v * p for v, p in zip(valores, pesos)) / total_peso
    return round(score, 1)

global_score = compute_global_score(cards_data)
cor_global = score_color(global_score)

st.markdown(
    f"<div class='global-score-wrap'>"
    f"<div class='rank-title'>Força consolidada do Phoenix nos últimos 30 dias</div>"
    f"<div class='global-score-value' style='color:{cor_global};'>{global_score}</div>"
    f"<div class='global-score-bar-outer'>"
    f"<div class='global-score-bar-inner' style='width:{global_score}%;background:{cor_global};'></div>"
    f"</div>"
    f"<div class='rank-line'>O Phoenix Score é um indicador proprietário que pondera retorno, estabilidade e qualidade operacional para oferecer uma medida objetiva da força da estratégia.</div>"
    f"</div>",
    unsafe_allow_html=True,
)
