import streamlit as st
import time
import pandas as pd
import os
import requests

from bp.core.data_loader import get_ticker_data, validate_data
from bp.core.indicators import apply_all_indicators
from bp.core.criteria_engine import evaluate_all_criteria
from bp.core.scoring import calculate_score
from bp.core.selectors import select_top_assets
from bp.ui.visual_blocks import criteria_block
from bp.ui.radar_chart import plot_radar


# ------------------------------------------------------------
# 🔐 SUPABASE – compatível com Render + Streamlit local
# ------------------------------------------------------------

def getenv(key: str) -> str:
    """
    Fallback automático:
    1) Tenta pegar do ambiente (Render via .env)
    2) Tenta pegar do st.secrets (local ou Cloud)
    3) Retorna string vazia para evitar crash
    """
    if key in os.environ:
        return os.environ[key]

    try:
        return st.secrets[key]
    except Exception:
        return ""


# → AGORA FUNCIONA EM QUALQUER AMBIENTE
SUPABASE_URL = getenv("supabase_url_curto")
SUPABASE_KEY = getenv("supabase_key_curto")

SUPABASE_TABLE = "kv_state_curto"
STATE_KEY = "curto_przo_v1"


st.markdown("""
<style>

div.streamlit-expanderContent {
    overflow: hidden;
    transition: max-height 0.35s ease-out;
}

details[open] > div.streamlit-expanderContent {
    max-height: 500px;
}

details:not([open]) > div.streamlit-expanderContent {
    max-height: 0px;
}

</style>
""", unsafe_allow_html=True)







def _sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def inserir_ativo_na_supabase(
    ticker: str,
    operacao: str,
    preco_entrada: float,
    stop_loss: float,
    stop_gain: float,
    indice: str
):
    """
    Adiciona OU atualiza apenas 1 ativo na tabela do Supabase,
    preservando 100% do resto da estrutura v.
    Agora envia também o índice (IBOV / SMLL / BBR).
    """
    try:
        # 1) Ler estado atual existente
        url_get = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?k=eq.{STATE_KEY}&select=v"
        r = requests.get(url_get, headers=_sb_headers(), timeout=15)
        r.raise_for_status()

        data = r.json()
        estado_antigo = data[0].get("v", {}) if data else {}

        # Lista atual de ativos
        ativos = estado_antigo.get("ativos", [])

        # Limpar ticker
        ticker_limpo = ticker.replace(".SA", "").upper()

        # 2) Remover ativo antigo caso exista
        ativos = [a for a in ativos if a.get("ticker") != ticker_limpo]

        # 3) Criar o novo ativo
        novo = {
            "ticker": ticker_limpo,
            "operacao": operacao.lower().strip(),
            "preco": round(float(preco_entrada), 2),
            "stop_loss": round(float(stop_loss), 2),
            "stop_gain": round(float(stop_gain), 2),
            "indice": indice.upper(),     # <<====== NEW FIELD
        }

        ativos.append(novo)

        # 4) Construir novo estado preservando tudo
        novo_estado = {
            **estado_antigo,
            "ativos": ativos
        }

        # 5) Enviar patch consolidado
        url_patch = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?k=eq.{STATE_KEY}"
        payload = {"v": novo_estado}

        r2 = requests.patch(url_patch, headers=_sb_headers(), json=payload, timeout=15)
        r2.raise_for_status()

        return True, None

    except Exception as e:
        return False, str(e)



def limpar_tabela_supabase():
    """
    Zera v['ativos'] igual à interface CURTO original.
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?k=eq.{STATE_KEY}"
        payload = {"v": {"ativos": []}}

        r = requests.patch(url, headers=_sb_headers(), json=payload, timeout=15)
        r.raise_for_status()
        return True, None
    except Exception as e:
        return False, str(e)


# ------------------------------------------------------------
# LOCALIZAÇÃO DO CSV
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "tickers_ibov.csv")


# ------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------------------------------------
def setup_page():
    st.set_page_config(
        page_title="BP Fênix – Busca Primordial",
        layout="wide",
        page_icon="🦅"
    )
    st.title("🦅 Projeto Fênix")
    #st.markdown(
        #"<h6 style='color:#27e062;'>Escolha o índice na sidebar e clique abaixo</h6>",
        #unsafe_allow_html=True
    #)



# ------------------------------------------------------------
# CICLO PRINCIPAL
# ------------------------------------------------------------
def run_full_cycle_with_logs(tickers):

    st.info(f"🔍 Total de ativos carregados: **{len(tickers)}**")

    progress = st.progress(0)
    status_box = st.status("🚀 Iniciando varredura do BP-Fênix...", expanded=False)

    results = {}
    total = len(tickers)

    with status_box:
        st.write("### 📡 LOG DA EXECUÇÃO")

        for i, ticker in enumerate(tickers):
            ticker_api = ticker + ".SA"

            st.write(f"🔵 **Processando {ticker}...**")

            df = get_ticker_data(ticker_api)
            if not validate_data(df):
                st.write(f"⚠️ Dados inválidos para {ticker}. Pulando...")
                continue

            df = apply_all_indicators(df)
            if df is None or df.empty:
                st.write(f"⚠️ Indicadores retornaram dataframe vazio para {ticker}.")
                continue

            criteria = evaluate_all_criteria(df)
            score_info = calculate_score(criteria)

            score_info["details"]["df"] = df
            results[ticker] = score_info

            st.write(f"✔️ Score de {ticker}: **{score_info['score']} / 5**")
            st.write("—")

            progress.progress((i + 1) / total)
            time.sleep(0.10)

        st.success("🟩 Varredura concluída!")

    return {
        "raw_results": results,
        "top_assets": select_top_assets(results)
    }


# ------------------------------------------------------------
# DETALHES POR ATIVO
# ------------------------------------------------------------
def show_asset_details(ticker, details, fs_components=None, trade=None, indice_ticker=None):

    # se não vier nada, evita quebrar
    if indice_ticker is None:
        indice_ticker = "DESCONHECIDO"

    # --- FS EXPLAINER ---
    if fs_components:
        with st.expander("📊 Detalhamento do Fênix Strength (FS)"):

            st.markdown("""
O **Fênix Strength (FS)** é a média normalizada dos 5 pilares:

- **Tendência**
- **Momentum**
- **Volatilidade**
- **Sinal Técnico**
- **Volume**
""")

            st.write({
                "Tendência (norm)": round(fs_components.get("tendencia_norm", 0), 3),
                "Momentum (norm)": round(fs_components.get("momentum_norm", 0), 3),
                "Volatilidade (norm)": round(fs_components.get("volatilidade_norm", 0), 3),
                "Sinal Técnico (norm)": round(fs_components.get("sinal_norm", 0), 3),
                "Volume (norm)": round(fs_components.get("volume_norm", 0), 3),
                "FS Total": round(fs_components.get("fs", 0), 3),
            })

    # --- RADAR ---
    radar = plot_radar(details)
    st.plotly_chart(
        radar,
        use_container_width=True,
        config={"displayModeBar": False},
        key=f"radar_{ticker}"
    )

    # (resto da função continua igual até o card...)


    # --- CRITÉRIOS ---
    st.subheader("Critérios Avaliados")
    
    with st.expander("📈 Tendência"):
        criteria_block(
            "Tendência",
            details["tendencia"]["status"],
            details["tendencia"]["detail"]
        )
    
    with st.expander("⚡ Momentum"):
        criteria_block(
            "Momentum",
            details["momentum"]["status"],
            details["momentum"]["detail"]
        )
    
    with st.expander("🌪️ Volatilidade"):
        criteria_block(
            "Volatilidade",
            details["volatilidade"]["status"],
            details["volatilidade"]["detail"]
        )
    
    with st.expander("🎯 Sinal Técnico"):
        criteria_block(
            "Sinal Técnico",
            details["sinal_tecnico"]["status"],
            details["sinal_tecnico"]["detail"]
        )
    
    with st.expander("📊 Volume"):
        criteria_block(
            "Volume",
            details["volume"]["status"],
            details["volume"]["detail"]
        )


    # --- CARD SIMPLES ---
    if trade:
        bg_color = "#0E3D1D" if trade["operacao"] == "LONG" else "#3D0E0E"
        border_color = "#27E062" if trade["operacao"] == "LONG" else "#FF4D4D"
        label = "COMPRA (LONG)" if trade["operacao"] == "LONG" else "VENDA (SHORT)"

        card_html = f"""
<div style="background-color:{bg_color};
            border-left:6px solid {border_color};
            padding:18px;
            border-radius:10px;
            margin-top:22px;
            margin-bottom:10px;
            color:white;
            font-family:'Segoe UI',sans-serif;">
  <div style="font-size:20px;font-weight:700;margin-bottom:4px;">
    {label} — {ticker}
  </div>
  <div style="font-size:13px;opacity:0.8;margin-bottom:10px;">
    Modelo C — Setup Profissional Adaptativo Fênix
  </div>
  <div style="font-size:13px;opacity:0.8;margin-bottom:10px;">
    Índice: <b>{indice_ticker}</b>
  </div>
  <div style="font-size:16px;line-height:1.6;">
    <b>🎯 Entrada:</b> {trade["entrada"]:.2f}<br>
    <b>🛑 Stop Loss:</b> {trade["stop"]:.2f}<br>
    <b>🎯 Take Profit:</b> {trade["alvo"]:.2f}<br>
    <b>📊 Risco/Retorno:</b> {trade["rr"]:.2f}
  </div>
  <div style="font-size:12px;opacity:0.7;margin-top:8px;">
    Stops: {trade["stop_dist_atr"]:.2f} ATR — Alvo: {trade["target_dist_atr"]:.2f} ATR
  </div>
</div>
"""
        st.markdown(card_html, unsafe_allow_html=True)

    # --- BOTÃO DE ENVIO ---
    if trade:
        oper = "compra" if trade["operacao"] == "LONG" else "venda"
        preco_entrada = trade["entrada"]

        if st.button(f"📤 Enviar {ticker} para o Robô de Monitoramento", key=f"send_{ticker}"):
        
            ok, erro = inserir_ativo_na_supabase(
                ticker=ticker,
                operacao=oper,
                preco_entrada=trade["entrada"],
                stop_loss=trade["stop"],
                stop_gain=trade["alvo"],
                indice=indice_ticker
            )
        
            if ok:
                st.success(f"Ticker {ticker} ({oper.upper()}) enviado ao robô com sucesso!")
            else:
                st.error(f"Erro ao enviar para o robô: {erro}")



# ------------------------------------------------------------
# TABELA COMPLETA
# ------------------------------------------------------------
def show_results_table(results):
    rows = []
    for ticker, item in results.items():
        rows.append({
            "Ticker": ticker,
            "Score": item["score"],
            "Passaram": ", ".join(item["passed"]),
            "Falharam": ", ".join(item["failed"]),
        })
    st.dataframe(rows, use_container_width=True)


# ------------------------------------------------------------
# DASHBOARD PRINCIPAL
# ------------------------------------------------------------
def render_dashboard():

    from bp.core.trade_engine import generate_trade_setup

    setup_page()

    st.sidebar.header("📡 Filtros do Fênix")

    df_tickers = pd.read_csv(CSV_PATH, sep=";")
    # --- Opções de índice ---
    indices = df_tickers["indice"].unique().tolist()
    indices = ["TODOS"] + indices   # <<<<<< ADICIONA A OPÇÃO “TODOS”
    
    indice_escolhido = st.sidebar.selectbox(
        "Selecione o índice:",
        options=indices,
        index=0
    )
    
    # --- Seleção dos tickers ---
    if indice_escolhido == "TODOS":
        # junta todos os índices
        tickers_filtrados = (
            df_tickers["ticker"]
            .dropna()
            .unique()
            .tolist()
        )
    else:
        tickers_filtrados = (
            df_tickers[df_tickers["indice"] == indice_escolhido]["ticker"]
            .dropna()
            .unique()
            .tolist()
        )
    
    st.sidebar.markdown(f"**Ativos carregados:** {len(tickers_filtrados)}")


    # --- LIMPAR SUPABASE ---
    if st.sidebar.button("🧹 Limpar Banco de Dados (Supabase)"):
        ok, erro = limpar_tabela_supabase()
        if ok:
            st.sidebar.success("Banco de dados zerado com sucesso!")
        else:
            st.sidebar.error(f"Erro: {erro}")

    # --- BOTÃO RODAR ---
    if st.button("🌀 Rodar Varredura Agora"):
        with st.spinner("Executando ciclo do BP-Fênix..."):
            output = run_full_cycle_with_logs(tickers_filtrados)

        st.session_state["fenix_output"] = output
        st.success("Ciclo concluído!")

    # --- MOSTRAR RESULTADOS OU AVISO ---
    output = st.session_state.get("fenix_output", None)

    if not output:
        st.info("◀️ Escolha um índice no sidebar e clique no botão acima para iniciar a varredura.")
        return



    # --- TOP ASSETS ---
    st.markdown("## 🔥 Top Selecionados pelo BP-Fênix")
    
    if not output["top_assets"]:
        st.warning("Nenhum ativo atingiu o score mínimo.")
    
    else:
        for asset in output["top_assets"]:
    
            # Nome da empresa
            nome_empresa = df_tickers[df_tickers["ticker"] == asset["ticker"]]["nome"].values[0]
    
            # Valor FS
            fs_value = asset.get("fs", None)
    
            # 🟩 PEGAR ÍNDICE DO TICKER (IBOV / SMLL / BBR)
            try:
                indice_ticker = df_tickers[df_tickers["ticker"] == asset["ticker"]]["indice"].values[0]
            except Exception:
                indice_ticker = "DESCONHECIDO"
    
            # Cabeçalho do ativo
            st.markdown(
                f"### ⭐ {asset['ticker']} ({nome_empresa}) — "
                f"Score Fênix: **{fs_value:.2f} / 5.00**"
            )
    
            # Gerar trade setup
            trade = None
            try:
                df_original = asset["details"]["df"]
                trade = generate_trade_setup(df_original, fs_value)
            except Exception as e:
                st.error(f"Erro ao gerar setup de trade: {e}")
    
            # Mostrar detalhes do ativo
            show_asset_details(
                asset["ticker"],
                asset["details"],
                fs_components={
                    "tendencia_norm": asset.get("tendencia_norm"),
                    "momentum_norm": asset.get("momentum_norm"),
                    "volatilidade_norm": asset.get("volatilidade_norm"),
                    "volume_norm": asset.get("volume_norm"),
                    "sinal_norm": asset.get("sinal_norm"),
                    "fs": asset.get("fs"),
                },
                trade=trade,
                indice_ticker=indice_ticker  # <<=== AQUI ENTRA O ÍNDICE CORRETO
            )
    
            st.markdown("---")


    # --- TABELA COMPLETA ---
    with st.expander("📦 Ver Tabela Completa da Varredura"):
        show_results_table(output["raw_results"])

    # --- DEBUG ---
    with st.expander("🐞 Diagnóstico Técnico — Ver detalhes de cada ativo"):
        for ticker, data in output["raw_results"].items():
            st.markdown(f"### 🔍 {ticker}")
            st.write("Score:", data["score"])
            st.write("Passaram:", data["passed"])
            st.write("Falharam:", data["failed"])
            st.json(data.get("details", {}))
