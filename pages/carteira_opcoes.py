import os
import tempfile
import datetime
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

import os
import tempfile
import datetime
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# ==== PROTEÇÃO DA PÁGINA (ADICIONE AQUI) ====
from auth.token_login import require_token, require_carteira

# 🔐 Autenticação + permissão
user = require_token()
require_carteira("Carteira de Opções")
# ============================================

# ==== REPORTLAB PARA PDF ====
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet


# ==== REPORTLAB PARA PDF ====
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet

# ==== MÓDULO DO SUPABASE DAS OPÇÕES (MESMO DO SCANNER) ====
import fenix_opcoes.supabase_ops as supabase_ops_mod


REST_ENDPOINT = getattr(supabase_ops_mod, "REST_ENDPOINT", None)
HEADERS = getattr(supabase_ops_mod, "HEADERS", None)

# ---------------------------
# TEMA BÁSICO PARA O PDF
# ---------------------------
THEMES = {
    "dark": {
        "bg": colors.HexColor("#111827"),
        "fg": colors.white,
        "accent": colors.HexColor("#f97316"),
        "rule": colors.HexColor("#4b5563"),
        "table_header_bg": colors.HexColor("#1f2937"),
        "table_header_fg": colors.white,
    },
    "white": {
        "bg": colors.white,
        "fg": colors.HexColor("#111827"),
        "accent": colors.HexColor("#f97316"),
        "rule": colors.HexColor("#9ca3af"),
        "table_header_bg": colors.HexColor("#e5e7eb"),
        "table_header_fg": colors.HexColor("#111827"),
    },
}


# ============================================
# 🔌 FUNÇÕES DE CARGA – OPERAÇÕES DE OPÇÕES
# ============================================

def carregar_df_operacoes_opcoes(status: Optional[str] = None) -> pd.DataFrame:
    """
    Lê as operações de OPÇÕES diretamente da tabela usada pelo Scanner (indice='OPCOES').
    """
    if not REST_ENDPOINT or not HEADERS:
        return pd.DataFrame()

    params = {
        "select": """
            id,
            symbol,
            underlying,
            tipo,
            strike,
            vencimento,
            preco_entrada,
            preco_atual,
            preco_saida,
            retorno_atual_pct,
            retorno_final_pct,
            stop_protecao_pct,
            lado_saida,
            motivo_saida,
            timestamp_saida,
            created_at,
            updated_at,
            status,
            indice
        """,
        "indice": "eq.OPCOES",
        "order": "created_at.desc",
    }

    if status:
        params["status"] = f"eq.{status}"

    try:
        resp = requests.get(REST_ENDPOINT, headers=HEADERS, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"Erro ao carregar operações de opções: {e}")
        return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # Conversões básicas
    for col in ["strike", "preco_entrada", "preco_atual", "preco_saida",
                "retorno_atual_pct", "retorno_final_pct", "stop_protecao_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["created_at", "updated_at", "timestamp_saida"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def carregar_df_encerradas_30d_opcoes() -> pd.DataFrame:
    """
    Filtra as operações de opções encerradas nos últimos 30 dias.
    """
    df = carregar_df_operacoes_opcoes(status="encerrada")
    if df.empty:
        return df

    hoje = datetime.date.today()
    inicio_30d = hoje - datetime.timedelta(days=30)

    if "timestamp_saida" not in df.columns:
        return pd.DataFrame()

    df = df.dropna(subset=["timestamp_saida"]).copy()
    df["data_saida"] = df["timestamp_saida"].dt.date

    df_30d = df[(df["data_saida"] >= inicio_30d) & (df["data_saida"] <= hoje)].copy()
    if df_30d.empty:
        return df_30d

    # PnL em R$ e %
    if "preco_saida" in df_30d.columns and "preco_entrada" in df_30d.columns:
        df_30d["pnl_reais"] = (df_30d["preco_saida"] - df_30d["preco_entrada"]).fillna(0.0)
    else:
        df_30d["pnl_reais"] = 0.0

    if "retorno_final_pct" in df_30d.columns:
        df_30d["pnl_pct"] = df_30d["retorno_final_pct"].fillna(0.0)
    else:
        df_30d["pnl_pct"] = 0.0

    # Dias na operação
    if "created_at" in df_30d.columns:
        df_30d["dias"] = (df_30d["timestamp_saida"] - df_30d["created_at"]).dt.days
    else:
        df_30d["dias"] = 0

    return df_30d


# ============================================
# 🎨 CARDS – TRADES EM ANDAMENTO (OPÇÕES)
# ============================================

CARD_CSS = """
<style>
.card-fenix-op {
    background: rgba(15,23,42,0.96);
    border-radius: 14px;
    border: 1px solid rgba(148,163,184,0.45);
    padding: 14px 16px;
    margin-bottom: 12px;
    box-shadow: 0 0 8px rgba(0,0,0,0.55);
}
.badge-op {
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}
</style>
"""

st.markdown(CARD_CSS, unsafe_allow_html=True)


def render_cards_andamento_opcoes(df_abertas: pd.DataFrame):
    """
    Renderiza cards estilo Phoenix para as operações de opções em andamento.
    """
    if df_abertas.empty:
        st.info("Nenhuma operação de opções em andamento.")
        return

    # Ordena por updated_at mais recente
    if "updated_at" in df_abertas.columns:
        df_abertas = df_abertas.sort_values("updated_at", ascending=False)

    # Limita para não explodir visual
    df_abertas = df_abertas.head(30)

    cols = st.columns(3)

    for idx, (_, row) in enumerate(df_abertas.iterrows()):
        col = cols[idx % 3]

        symbol = row.get("symbol", "—")
        underlying = row.get("underlying", "—")
        tipo = row.get("tipo", "CALL/PUT")
        strike = row.get("strike", 0)
        venc = row.get("vencimento", "")
        preco_ent = row.get("preco_entrada", 0.0) or 0.0
        preco_at = row.get("preco_atual", 0.0) or 0.0
        ret_pct = row.get("retorno_atual_pct", 0.0) or 0.0
        stop_pct = row.get("stop_protecao_pct", 0.0) or 0.0

        cor_ret = "#22c55e" if ret_pct >= 0 else "#ef4444"
        cor_stop = "#f97316"



        with col:
            html = f"""
            <div class="card-fenix-op">
                <div style="font-size:12px;color:#9ca3af;margin-bottom:4px;">
                    <b>{underlying}</b> · <b style="color:{'#38BDF8' if tipo.upper()=='CALL' else '#FCA5A5'};">{tipo}</b>
                </div>
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                    <span style="background:#6D28D9;color:white;padding:4px 12px;border-radius:999px;font-weight:700;">{symbol}</span>                        
                    </span>
                    <span class="badge-op" style="background:#0ea5e9;color:white;">
                        Strike {strike:.2f} · Venc. {venc}
                    </span>
                    <span class="badge-op" style="background:{cor_ret};color:white;">
                        {ret_pct:+.2f}%
                    </span>
                </div>
                <div style="color:#e5e7eb;font-size:14px;">
                    Preço atual: <b>{preco_at:.3f}</b> · Entrada: <b>{preco_ent:.3f}</b>
                </div>
                <div style="color:#9ca3af;font-size:12px;margin-top:4px;">
                    Stop dinâmico: <span style="color:{cor_stop};font-weight:bold;">{stop_pct:.1f}%</span>
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)



# ============================================
# 📊 GRÁFICO PARA PDF (OPÇÕES)
# ============================================

def build_chart_png_opcoes(dados_enc: List[Dict[str, Any]], theme_key: str) -> Optional[str]:
    """
    Gera um gráfico PNG de PnL% por ticker para ser usado no PDF.
    """
    if not dados_enc:
        return None

    df = pd.DataFrame(dados_enc)
    if "ticker" not in df.columns or "pnl_pct" not in df.columns:
        return None

    df_chart = (
        df.groupby("ticker", as_index=False)["pnl_pct"]
        .mean()
        .sort_values("pnl_pct", ascending=False)
    )

    if df_chart.empty:
        return None

    # Cores por sinal
    colors_bar = ["#22c55e" if v > 0 else "#ef4444" for v in df_chart["pnl_pct"]]

    fig, ax = plt.subplots(figsize=(8, 3))

    bars = ax.bar(df_chart["ticker"], df_chart["pnl_pct"], color=colors_bar)
    ax.set_ylabel("PnL (%)")
    ax.set_xlabel("Ticker")

    for bar, val in zip(bars, df_chart["pnl_pct"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{val:.1f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.savefig(tmp.name, bbox_inches="tight", dpi=160)
    plt.close(fig)
    return tmp.name


# ============================================
# 📄 EXPORTAÇÃO DE PDF — OPÇÕES
# ============================================

def export_pdf_landscape_opcoes(
    theme_key: str,
    df_ops: pd.DataFrame,
    dados_enc: List[Dict[str, Any]],
    lucro_total_pct: float,
    media_pct_vencedoras: float,
    qtd_lucro: int,
    qtd_preju: int,
    qtd_neutras: int,
    media_dias: float,
    media_stop_loss_pct: float,
    rent_fluxo_capital: float,
    op_mais_lucr: Optional[Dict[str, Any]],
    data_inicio: str,
    data_fim: str,
) -> str:
    """
    Gera um PDF em formato paisagem com resumo das operações de opções.
    """
    theme = THEMES[theme_key]
    pdf_path = f"Relatorio_Opcoes_{theme_key}.pdf"

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # ===== CAPA =====
    titulo = "Relatório de Operações com Opções — Projeto Phoenix"
    subt = f"Período: {data_inicio} a {data_fim}"

    elements.append(Spacer(1, 3 * cm))
    elements.append(
        Paragraph(
            f"<para align='center'><font size=24 color='{theme['accent'].hexval()}'><b>{titulo}</b></font></para>",
            styles["Title"],
        )
    )
    elements.append(Spacer(1, 0.6 * cm))
    elements.append(
        Paragraph(
            f"<para align='center'><font size=14 color='{theme['fg'].hexval()}'>{subt}</font></para>",
            styles["Normal"],
        )
    )
    elements.append(PageBreak())

    # ===== CARDS RESUMO =====
    cards_cfg = [
        ("Lucro total (%)", lucro_total_pct),
        ("Média lucro (vencedoras)", media_pct_vencedoras),
        ("Operações com lucro", qtd_lucro),
        ("Operações com prejuízo", qtd_preju),
        ("Operações neutras", qtd_neutras),
        ("Média de dias por operação", media_dias),
        ("Média Stop Loss", media_stop_loss_pct),
        ("Rentab. por Fluxo Capital", rent_fluxo_capital),
    ]

    if op_mais_lucr:
        try:
            pct_mais = float(op_mais_lucr.get("pnl_pct", 0))
        except:
            pct_mais = 0.0
        cards_cfg.append(("Op. mais lucrativa (%)", pct_mais))

    elements.append(
        Paragraph(
            f"<para align='center'><font size=18 color='{theme['fg'].hexval()}'><b>Resumo de Performance</b></font></para>",
            styles["Title"],
        )
    )
    elements.append(Spacer(1, 0.5 * cm))

    card_rows = []
    row = []
    for i, (label, val) in enumerate(cards_cfg, start=1):
        if isinstance(val, float):
            txt_val = f"{val:.2f}"
        else:
            txt_val = str(val)

        cell = Paragraph(
            f"<b>{label}</b><br/><font size=14>{txt_val}</font>", styles["Normal"]
        )
        row.append(cell)
        if i % 3 == 0:
            card_rows.append(row)
            row = []
    if row:
        while len(row) < 3:
            row.append(Paragraph("", styles["Normal"]))
        card_rows.append(row)

    tbl = Table(card_rows, colWidths=[8 * cm, 8 * cm, 8 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), theme["table_header_bg"]),
                ("TEXTCOLOR", (0, 0), (-1, -1), theme["table_header_fg"]),
                ("BOX", (0, 0), (-1, -1), 0.5, theme["rule"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, theme["rule"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
            ]
        )
    )
    elements.append(tbl)
    elements.append(PageBreak())

    # ===== TABELA DETALHADA =====
    if not df_ops.empty:
        elements.append(
            Paragraph(
                f"<para align='center'><font size=18 color='{theme['fg'].hexval()}'><b>Operações Encerradas (Detalhe)</b></font></para>",
                styles["Title"],
            )
        )
        elements.append(Spacer(1, 0.5 * cm))

        data_tbl = [list(df_ops.columns)] + df_ops.values.tolist()
        tbl_ops = Table(data_tbl, repeatRows=1)
        tbl_ops.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), theme["table_header_bg"]),
                    ("TEXTCOLOR", (0, 0), (-1, 0), theme["table_header_fg"]),
                    ("GRID", (0, 0), (-1, -1), 0.25, theme["rule"]),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(tbl_ops)
        elements.append(PageBreak())

    # ===== GRÁFICO =====
    chart_path = build_chart_png_opcoes(dados_enc, theme_key)
    if chart_path and os.path.exists(chart_path):
        elements.append(
            Paragraph(
                f"<para align='center'><font size=18 color='{theme['fg'].hexval()}'><b>Gráfico de Performance por Ativo</b></font></para>",
                styles["Title"],
            )
        )
        elements.append(Spacer(1, 0.8 * cm))

        img = RLImage(chart_path, width=22 * cm, height=8 * cm)
        img.hAlign = "CENTER"
        elements.append(img)
        elements.append(PageBreak())

    doc.build(elements)
    return pdf_path


# ============================================
# 🧠 LAYOUT PRINCIPAL DA PÁGINA
# ============================================

st.markdown("## 🟪 Carteira de Opções — Projeto Phoenix")

st.markdown(
    """
<p style="color:#9ca3af;font-size:13px;">
Esta página mostra apenas as operações com opções monitoradas pelo Scanner Fênix:
trades em andamento e desempenho consolidado dos últimos 30 dias.
</p>
""",
    unsafe_allow_html=True,
)

# ---------- CARREGAR DADOS ----------
df_abertas = carregar_df_operacoes_opcoes(status="aberta")
df_30d = carregar_df_encerradas_30d_opcoes()

# ============================================
# ⭐ TRADES EM ANDAMENTO (OPÇÕES)
# ============================================
st.markdown("### ⭐ Trades em Andamento (Opções)")

if df_abertas.empty:
    st.info("Nenhuma operação de opções em andamento.")
else:
    render_cards_andamento_opcoes(df_abertas)






# ============================================
# 🦅 RESUMO POR PERÍODO (OPÇÕES)
# ============================================
st.markdown("---")
st.markdown("### 🦅 Resumo de Desempenho — Opções (Período Selecionado)")

# -------------------------------------------------
# 1. FILTRO DE DATA (calendário)
# -------------------------------------------------
col_f1, col_f2, _ = st.columns([1, 1, 2])

with col_f1:
    data_inicio_filtro = st.date_input(
        "📅 Data início",
        value=(datetime.date.today() - datetime.timedelta(days=30))
    )
with col_f2:
    data_fim_filtro = st.date_input(
        "📅 Data fim",
        value=datetime.date.today()
    )

# -------------------------------------------------
# 2. APLICAR FILTRO AO DATAFRAME
# -------------------------------------------------
if df_30d.empty or ("timestamp_saida" not in df_30d.columns):
    st.info("Nenhuma operação encerrada no período selecionado.")
    df_base = pd.DataFrame()
else:
    df_base = df_30d[
        (df_30d["timestamp_saida"].dt.date >= data_inicio_filtro) &
        (df_30d["timestamp_saida"].dt.date <= data_fim_filtro)
    ].copy()

if df_base.empty:
    st.info("Sem operações encerradas no período escolhido.")
else:
    # -------------------------------------------------
    # 3. TABELA BASE PARA EXIBIÇÃO
    # -------------------------------------------------
    df_ops = pd.DataFrame([
        {
            "Ticker": row.get("symbol"),
            "Tipo": row.get("tipo"),
            "Strike": row.get("strike"),
            "Vencimento": row.get("vencimento"),
            "Preço Entrada": row.get("preco_entrada"),
            "Preço Saída": row.get("preco_saida"),
            "PnL (R$)": row.get("pnl_reais"),
            "PnL (%)": row.get("pnl_pct"),
            "Dias": row.get("dias"),
            "Data Fechamento": row["timestamp_saida"].date() if pd.notna(row["timestamp_saida"]) else None,
        }
        for _, row in df_base.iterrows()
    ])

    # Formatação visual
    df_ops_view = df_ops.copy()
    df_ops_view["Preço Entrada"] = df_ops_view["Preço Entrada"].apply(
        lambda v: f"R$ {v:,.2f}" if pd.notna(v) else "—"
    )
    df_ops_view["Preço Saída"] = df_ops_view["Preço Saída"].apply(
        lambda v: f"R$ {v:,.2f}" if pd.notna(v) else "—"
    )
    df_ops_view["PnL (R$)"] = df_ops_view["PnL (R$)"].apply(
        lambda v: f"R$ {v:,.2f}" if pd.notna(v) else "—"
    )
    df_ops_view["PnL (%)"] = df_ops_view["PnL (%)"].apply(
        lambda v: f"{v:.2f}%" if pd.notna(v) else "—"
    )

    st.dataframe(df_ops_view, use_container_width=True, hide_index=True)

    # -------------------------------------------------
    # 4. RESUMO ESTATÍSTICO
    # -------------------------------------------------
    pnls_pct = df_base["pnl_pct"].dropna().tolist()
    lucros = [p for p in pnls_pct if p > 0]
    preju = [p for p in pnls_pct if p < 0]
    neutras = [p for p in pnls_pct if p == 0]

    lucro_total_pct = sum(pnls_pct) if pnls_pct else 0.0
    media_pct_vencedoras = sum(lucros) / len(lucros) if lucros else 0.0
    qtd_lucro = len(lucros)
    qtd_preju = len(preju)
    qtd_neutras = len(neutras)

    media_dias = df_base["dias"].mean() if not df_base["dias"].isna().all() else 0.0

    perdas_pct = preju
    media_stop_loss_pct = sum(perdas_pct) / len(perdas_pct) if perdas_pct else 0.0
    rent_fluxo_capital = lucro_total_pct / 4 if lucro_total_pct else 0.0

    op_mais_lucr = None
    try:
        idx_max = df_base["pnl_pct"].idxmax()
        row_max = df_base.loc[idx_max]
        op_mais_lucr = {
            "ticker": row_max.get("symbol"),
            "pnl_pct": row_max.get("pnl_pct", 0.0),
        }
    except:
        op_mais_lucr = None

    # -------------------------------------------------
    # 5. CARDS RESUMO
    # -------------------------------------------------
    def card_cor_valor(v: float) -> str:
        if v > 0: return "#22c55e"
        if v < 0: return "#ef4444"
        return "#e5e7eb"

    def render_card_resumo(titulo: str, valor: float, sufixo="%", casas=2):
        cor = card_cor_valor(valor)
        try:
            txt = f"{valor:.{casas}f}{sufixo}"
        except:
            txt = str(valor)

        st.markdown(
            f"""
            <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                        background-color:rgba(17,24,39,0.85);
                        border-left:6px solid {cor};
                        color:white;">
                <b style="color:#9ca3af;">{titulo}</b><br>
                <span style="font-size:1.9em;color:{cor};font-weight:bold;">{txt}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        render_card_resumo("Lucro total (%)", lucro_total_pct)
        render_card_resumo("Operações com lucro", float(qtd_lucro), sufixo="", casas=0)
    with c2:
        render_card_resumo("Média lucro (vencedoras)", media_pct_vencedoras)
        render_card_resumo("Operações com prejuízo", float(qtd_preju), sufixo="", casas=0)
    with c3:
        render_card_resumo("Operações neutras", float(qtd_neutras), sufixo="", casas=0)
        render_card_resumo("Média de dias por operação", media_dias, sufixo="", casas=2)

    c4, c5, c6 = st.columns(3)
    with c4:
        render_card_resumo("Média de Stop Loss (%)", media_stop_loss_pct)
    with c5:
        render_card_resumo("Rentabilidade por Fluxo de Capital (%)", rent_fluxo_capital)
    with c6:
        if op_mais_lucr:
            v = float(op_mais_lucr.get("pnl_pct", 0.0))
            cor = card_cor_valor(v)
            st.markdown(
                f"""
                <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                            background-color:rgba(17,24,39,0.85);
                            border-left:6px solid {cor};
                            color:white;">
                    <b style="color:#9ca3af;">Operação mais lucrativa</b><br>
                    <span style="font-size:1.7em;color:white;font-weight:bold;">
                        {op_mais_lucr.get("ticker","—")}
                    </span>
                    <span style="font-size:1.9em;color:{cor};font-weight:bold;">
                        &nbsp;{v:.2f}%
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -------------------------------------------------
    # 6. GRÁFICO
    # -------------------------------------------------
    st.markdown("---")
    st.markdown("#### ⭐ Gráfico dos Resultados (Período Filtrado)")

    df_chart = (
        df_base.groupby("symbol", as_index=False)["pnl_pct"]
        .mean()
        .sort_values("pnl_pct", ascending=False)
    )
    if df_chart.empty:
        st.info("Sem dados para exibir no gráfico.")
    else:
        import plotly.graph_objects as go

        colors_bar = ["#22c55e" if v > 0 else "#ef4444" for v in df_chart["pnl_pct"]]

        fig = go.Figure()
        fig.add_bar(
            x=df_chart["symbol"],
            y=df_chart["pnl_pct"],
            marker_color=colors_bar,
            text=[f"{v:.2f}%" for v in df_chart["pnl_pct"]],
            textposition="outside",
        )
        fig.update_layout(
            template="plotly_dark",
            height=380,
            margin=dict(l=20, r=20, t=30, b=60),
            xaxis=dict(title="", tickangle=-40),
            yaxis=dict(title="PnL (%)"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------
    # 7. PDF (DARK / WHITE)
    # -------------------------------------------------
    dados_enc_pdf = [
        {
            "ticker": row.get("symbol"),
            "pnl": row.get("pnl_reais", 0.0),
            "preco_abertura": row.get("preco_entrada", 0.0),
            "pnl_pct": row.get("pnl_pct", 0.0),
            "dur_days": row.get("dias", 0),
        }
        for _, row in df_base.iterrows()
    ]

    data_inicio_str = data_inicio_filtro.strftime("%Y/%m/%d")
    data_fim_str = data_fim_filtro.strftime("%Y/%m/%d")

    st.markdown("---")
    st.markdown("### 📄 Relatório em PDF — Opções (Período Filtrado)")

    col_pdf1, col_pdf2 = st.columns(2)

    with col_pdf1:
        if st.button("📄 Exportar PDF — Dark (Opções)"):
            try:
                pdf_file = export_pdf_landscape_opcoes(
                    "dark",
                    df_ops=df_ops,
                    dados_enc=dados_enc_pdf,
                    lucro_total_pct=lucro_total_pct,
                    media_pct_vencedoras=media_pct_vencedoras,
                    qtd_lucro=qtd_lucro,
                    qtd_preju=qtd_preju,
                    qtd_neutras=qtd_neutras,
                    media_dias=media_dias,
                    media_stop_loss_pct=media_stop_loss_pct,
                    rent_fluxo_capital=rent_fluxo_capital,
                    op_mais_lucr=op_mais_lucr,
                    data_inicio=data_inicio_str,
                    data_fim=data_fim_str,
                )
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        "⬇️ Baixar PDF (Dark)",
                        f,
                        file_name="Relatorio_Opcoes_Dark.pdf",
                        mime="application/pdf",
                    )
                st.success("✅ PDF (Dark) gerado com sucesso!")
            except Exception as e:
                import traceback
                st.error(f"Erro ao gerar PDF Dark: {e}")
                st.code(traceback.format_exc())

    with col_pdf2:
        if st.button("📄 Exportar PDF — White (Opções)"):
            try:
                pdf_file = export_pdf_landscape_opcoes(
                    "white",
                    df_ops=df_ops,
                    dados_enc=dados_enc_pdf,
                    lucro_total_pct=lucro_total_pct,
                    media_pct_vencedoras=media_pct_vencedoras,
                    qtd_lucro=qtd_lucro,
                    qtd_preju=qtd_preju,
                    qtd_neutras=qtd_neutras,
                    media_dias=media_dias,
                    media_stop_loss_pct=media_stop_loss_pct,
                    rent_fluxo_capital=rent_fluxo_capital,
                    op_mais_lucr=op_mais_lucr,
                    data_inicio=data_inicio_str,
                    data_fim=data_fim_str,
                )
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        "⬇️ Baixar PDF (White)",
                        f,
                        file_name="Relatorio_Opcoes_White.pdf",
                        mime="application/pdf",
                    )
                st.success("✅ PDF (White) gerado com sucesso!")
            except Exception as e:
                import traceback
                st.error(f"Erro ao gerar PDF White: {e}")
                st.code(traceback.format_exc())


