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
import requests
import fenix_opcoes.supabase_ops as supabase_ops_mod

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
text-decoration:none;
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
    Usa o mesmo endpoint de opções do Scanner (fenix_opcoes.supabase_ops)
    para montar as estatísticas de 30 dias: lucro total, média, winrate, sparkline.
    """
    if not REST_ENDPOINT_OP or not HEADERS_OP:
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

    params = {
        "select": """
            id,
            symbol,
            preco_entrada,
            preco_saida,
            retorno_final_pct,
            timestamp_saida,
            created_at,
            status,
            indice
        """,
        "indice": "eq.OPCOES",
        "status": "eq.encerrada",
        "order": "timestamp_saida.desc",
    }

    try:
        resp = requests.get(REST_ENDPOINT_OP, headers=HEADERS_OP, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {
            "has_data": False,
            "lucro_total_pct": 0.0,
            "media_pct": 0.0,
            "winrate": 0.0,
            "qtd_trades": 0,
            "sparkline": [],
        }

    if not data:
        return {
            "has_data": False,
            "lucro_total_pct": 0.0,
            "media_pct": 0.0,
            "winrate": 0.0,
            "qtd_trades": 0,
            "sparkline": [],
        }

    df = pd.DataFrame(data)

    # converte datas
    for col in ["timestamp_saida", "created_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # filtra últimos 30 dias
    if "timestamp_saida" not in df.columns:
        return {
            "has_data": False,
            "lucro_total_pct": 0.0,
            "media_pct": 0.0,
            "winrate": 0.0,
            "qtd_trades": 0,
            "sparkline": [],
        }

    df = df.dropna(subset=["timestamp_saida"]).copy()
    df["data_saida"] = df["timestamp_saida"].dt.date
    df_30d = df[
        (df["data_saida"] >= inicio_30d) &
        (df["data_saida"] <= hoje)
    ].copy()

    if df_30d.empty:
        return {
            "has_data": False,
            "lucro_total_pct": 0.0,
            "media_pct": 0.0,
            "winrate": 0.0,
            "qtd_trades": 0,
            "sparkline": [],
        }

    # PnL %: usa retorno_final_pct se existir; senão, calcula pelo preço
    if "retorno_final_pct" in df_30d.columns:
        df_30d["pnl_pct"] = pd.to_numeric(df_30d["retorno_final_pct"], errors="coerce").fillna(0.0)
    else:
        df_30d["preco_entrada"] = pd.to_numeric(df_30d["preco_entrada"], errors="coerce")
        df_30d["preco_saida"] = pd.to_numeric(df_30d["preco_saida"], errors="coerce")
        df_30d["pnl_pct"] = (
            (df_30d["preco_saida"] - df_30d["preco_entrada"]) /
            df_30d["preco_entrada"]
        ).fillna(0.0) * 100.0

    valores = df_30d["pnl_pct"].dropna().tolist()
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

    sparkline = [
        {"data": row["timestamp_saida"], "pct": row["pnl_pct"]}
        for _, row in df_30d.sort_values("timestamp_saida").iterrows()
    ]

    return {
        "has_data": True,
        "lucro_total_pct": lucro_total_pct,
        "media_pct": media_pct,
        "winrate": winrate,
        "qtd_trades": qtd_trades,
        "sparkline": sparkline,
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

        comp_lucro = max(min(lt / 5.0, 30.0), -20.0)
        comp_media = max(min(media * 0.8, 25.0), -15.0)
        comp_win = (win - 0.5) * 80.0
        comp_trades = min(trades * 2.0, 20.0)
        comp_ativos = min(ativos * 1.5, 15.0)

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

    st.markdown(
        f"""<div class="card-wrapper">
<div class="card-header">
  <div class="card-title-left">
    <div class="card-title-main">{emoji} {nome}</div>
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

    c1, c2 = st.columns([1.35, 0.65])
    with c1:
        fig_spark = sparkline_figure(stats)
        st.markdown("##### 📈 Performance recente (30d)")
        if fig_spark:
            st.plotly_chart(fig_spark, use_container_width=True)
        else:
            st.info("Ainda não há operações encerradas suficientes para esta carteira.")
    with c2:
        st.markdown("##### 📊 Trades ativos")
        fig_bar = barras_pend_andamento(resumo_estado)
        st.plotly_chart(fig_bar, use_container_width=True)

# ===========================
# 🔢 MONTAGEM DOS DADOS DAS CARTEIRAS
# ===========================
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
st.markdown("## 🏆 Ranking Phoenix — Últimos 30 dias")

# ranking por score
rank_score = sorted(cards_data, key=lambda c: c["score"], reverse=True)

best_score = rank_score[0]
st.markdown(
    f"<div class='rank-box'><div class='rank-title'>🥇 Melhor carteira geral: {best_score['emoji']} {best_score['nome']}</div>"
    f"<div class='rank-line'><span class='rank-tag'>Phoenix Score</span> {best_score['score']}</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# ranking por lucro total
rank_lucro = sorted(
    cards_data,
    key=lambda c: c["stats"]["lucro_total_pct"],
    reverse=True,
)

best_lucro = rank_lucro[0]
st.markdown(
    f"<div class='rank-box'>"
    f"<div class='rank-title'>📈 Carteira com maior lucro 30d: {best_lucro['emoji']} {best_lucro['nome']}</div>"
    f"<div class='rank-line'><span class='rank-tag'>Lucro total 30d</span> {best_lucro['stats']['lucro_total_pct']:.1f}%</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# ranking por winrate
rank_win = sorted(
    cards_data,
    key=lambda c: c['stats']['winrate'],
    reverse=True,
)

best_win = rank_win[0]
st.markdown(
    f"<div class='rank-box'>"
    f"<div class='rank-title'>🎯 Melhor winrate 30d: {best_win['emoji']} {best_win['nome']}</div>"
    f"<div class='rank-line'><span class='rank-tag'>Winrate</span> {(best_win['stats']['winrate']*100.0):.1f}%</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# ===========================
# 💹 TOP TRADES 30d
# ===========================
st.markdown("### 🔝 Top Trades (30 dias)")

def enrich_ops_with_pct(dados):
    out = []
    for x in dados:
        pnl = x.get("pnl")
        preco_abertura = x.get("preco_abertura")
        if pnl is None or not preco_abertura:
            continue
        try:
            pct = (float(pnl) / float(preco_abertura)) * 100.0
        except Exception:
            pct = 0.0
        out.append(
            {
                "ticker": x.get("ticker"),
                "indice": x.get("indice"),
                "pnl_pct": pct,
                "pnl": x.get("pnl"),
                "data_fechamento": x.get("data_fechamento"),
            }
        )
    return out

enriched = enrich_ops_with_pct(dados_30d_geral)

if not enriched:
    st.info("Ainda não há operações encerradas suficientes para montar o ranking de trades.")
else:
    melhores = sorted(enriched, key=lambda x: x["pnl_pct"], reverse=True)[:3]
    piores = sorted(enriched, key=lambda x: x["pnl_pct"])[:3]

    col_melhor, col_pior = st.columns(2)

    with col_melhor:
        st.markdown("#### 🥇 Top 3 trades mais lucrativos")
        df_best = pd.DataFrame(
            [
                {
                    "Ticker": t["ticker"],
                    "Carteira": t["indice"],
                    "Retorno (%)": round(t["pnl_pct"], 2),
                    "PnL (R$)": round(float(t["pnl"] or 0.0), 2),
                }
                for t in melhores
            ]
        )
        st.dataframe(df_best, use_container_width=True, hide_index=True)

    with col_pior:
        st.markdown("#### ⚠️ Top 3 trades com maior perda")
        df_worst = pd.DataFrame(
            [
                {
                    "Ticker": t["ticker"],
                    "Carteira": t["indice"],
                    "Retorno (%)": round(t["pnl_pct"], 2),
                    "PnL (R$)": round(float(t["pnl"] or 0.0), 2),
                }
                for t in piores
            ]
        )
        st.dataframe(df_worst, use_container_width=True, hide_index=True)

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
    f"<div class='rank-line'>Score ponderado pelas operações fechadas de todas as carteiras.</div>"
    f"</div>",
    unsafe_allow_html=True,
)
