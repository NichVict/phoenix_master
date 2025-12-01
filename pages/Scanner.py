# -*- coding: utf-8 -*-
"""
Buscador de Opções — Oplab v3 + Yahoo (fallback) + IV/Greeks locais
Versão 2025-10-28

Recursos:
- Interface Streamlit (sidebar completa, filtros, um único botão "Rodar buscador")
- Baixa OHLCV do ativo (Oplab -> fallback Yahoo)
- Snapshot de opções (Oplab /market/options/{symbol})
- IV e gregas locais (Black–Scholes + Brent)
- Filtros: CALL/PUT, janela de vencimento, delta, IV %, volume, spread, e
  "exigir volume do ativo acima da MM20" (volume financeiro > MM20 do dia mais recente)
- Gráfico: candles + barras de volume financeiro + MM20 branca

Requer .env com:
  OPLAB_API_KEY="seu_token"
  (opcional) OPLAB_BASE_URL="https://api.oplab.com.br/v3/"
"""

from __future__ import annotations
import os, math
from datetime import datetime, timedelta, date

import numpy as np
import pandas as pd
import requests, yfinance as yf
import streamlit as st
#from dotenv import load_dotenv, find_dotenv
import plotly.graph_objects as go
from scipy.stats import norm
from scipy.optimize import brentq
from fenix_opcoes.supabase_ops import inserir_operacao
from fenix_opcoes.notificacoes import enviar_email, enviar_telegram
import fenix_opcoes.supabase_ops as supabase_ops_mod




# ===============================

# Config inicial e layout responsivo
# ===============================
st.set_page_config(
    page_title="Scanner de Opções",
    layout="wide",
    initial_sidebar_state="expanded"
)


# CSS — Reduzir tamanho da fonte da sidebar
# ===============================
st.markdown("""
<style>
/* 🔹 Sidebar: fonte geral menor e mais compacta */
section[data-testid="stSidebar"] {
    font-size: 0.85rem !important;      /* reduz o texto geral */
}

/* 🔹 Ajusta inputs, sliders, radios e checkboxes */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stNumberInput label,
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label,
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stCheckbox label {
    font-size: 0.82rem !important;
}

/* 🔹 Sliders e valores numéricos */
section[data-testid="stSidebar"] .stSlider {
    font-size: 0.8rem !important;
}

/* 🔹 Botões */
section[data-testid="stSidebar"] button {
    font-size: 0.85rem !important;
    padding: 0.4rem 0.6rem !important;
}

/* 🔹 Título da sidebar (ex: "⚙️ Parâmetros do Scanner") */
section[data-testid="stSidebar"] h1, 
section[data-testid="stSidebar"] h2, 
section[data-testid="stSidebar"] h3 {
    font-size: 1rem !important;
}
</style>
""", unsafe_allow_html=True)





#load_dotenv(find_dotenv(), override=True)
OPLAB_API_KEY  = os.getenv("OPLAB_API_KEY", "")
OPLAB_BASE_URL = os.getenv("OPLAB_BASE_URL", "https://api.oplab.com.br/v3/").rstrip("/")

def _headers():
    return {"Access-Token": OPLAB_API_KEY, "accept": "application/json"}

def _to_num(x): 
    return pd.to_numeric(x, errors="coerce")

def err(msg: str):
    st.error(f"❌ {msg}")

def warn(msg: str):
    st.warning(f"⚠️ {msg}")

# ===============================
# Yahoo helper
# ===============================
def _yf_download_one(ticker_sa: str, start: datetime, end: datetime) -> pd.DataFrame:
    data = yf.download(ticker_sa, start=start, end=end, progress=False, auto_adjust=False)
    if data is None or data.empty:
        raise ValueError("Yahoo sem dados")
    data = data.reset_index().rename(columns={
        "Date":"date","Open":"open","High":"high","Low":"low","Close":"close",
        "Adj Close":"adj_close","Volume":"volume"
    })
    for c in ["open","high","low","close","volume"]:
        data[c] = _to_num(data[c])
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    return data[["date","open","high","low","close","volume"]]

# ===============================
# Fetch candles (Oplab -> Yahoo)
# ===============================
@st.cache_data(ttl=600, show_spinner=True)
def fetch_candles(symbol: str, days: int = 180) -> pd.DataFrame:
    symbol = str(symbol).strip().upper()
    end = datetime.today()
    start = end - timedelta(days=days)

    # Corrige ticker para o formato do Yahoo (".SA" apenas se for brasileiro)
    ticker_yf = f"{symbol}.SA" if not symbol.endswith(".SA") else symbol

    try:
        df = yf.download([ticker_yf], start=start, end=end, progress=False, auto_adjust=False)
        if df.empty:
            raise RuntimeError("Yahoo sem dados")

        # Se vier MultiIndex (caso da lista), "aplana" o DataFrame
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index().rename(columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        })
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["underlying_symbol"] = symbol
        df = df[["underlying_symbol", "date", "open", "high", "low", "close", "volume"]]
        return df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    except Exception as e:
        err(f"Yahoo falhou ({symbol}): {e}")
        cols = ["underlying_symbol", "date", "open", "high", "low", "close", "volume"]
        return pd.DataFrame(columns=cols)


# ===============================
# Fetch opções (Oplab)
# ===============================
@st.cache_data(ttl=300, show_spinner=True)
def fetch_options_snapshot(symbol: str) -> pd.DataFrame:
    url = f"{OPLAB_BASE_URL}/market/options/{symbol}"
    try:
        r = requests.get(url, headers=_headers(), timeout=45)
        r.raise_for_status()
        raw = r.json()
        data = raw if isinstance(raw, list) else raw.get("data", [])
        df = pd.DataFrame(data)
        if df.empty:
            raise RuntimeError("Snapshot vazio")

        rename = {
            "parent_symbol": "underlying_symbol",
            "underlying": "underlying_symbol",
            "due_date": "expiration",
            "expiration_date": "expiration",
            "strike_price": "strike",
            "last_price": "last",
            "spot_price": "ref_price",
            "option_symbol": "symbol",
        }
        for k, v in rename.items():
            if k in df.columns and v != k:
                df.rename(columns={k: v}, inplace=True)

        # Campos essenciais
        needed = ["symbol","underlying_symbol","expiration","type","category","strike",
                  "bid","ask","last","close","volume","open_interest",
                  "ref_price"]
        for c in needed:
            if c not in df.columns:
                df[c] = np.nan

        # Normalizações
        df["expiration"] = pd.to_datetime(df["expiration"], errors="coerce")
        for c in ["strike","bid","ask","last","close","volume","open_interest","ref_price"]:
            df[c] = _to_num(df[c])

        # Tipagem CALL/PUT (type pode vir em 'category')
        if "type" not in df or df["type"].isna().all():
            df["type"] = df["category"]
        df["type"] = df["type"].astype(str).str.upper().replace({"C":"CALL","P":"PUT"})

        # Garantir que não fique 'nan' / 'NAN' como texto
        df["underlying_symbol"] = df["underlying_symbol"].where(df["underlying_symbol"].notna(), symbol)
        df["underlying_symbol"] = df["underlying_symbol"].astype(str).str.upper()
        df.loc[df["underlying_symbol"].isin(["NAN", "NONE", "NULL"]), "underlying_symbol"] = symbol


        return df.dropna(subset=["symbol"]).reset_index(drop=True)

    except Exception as e:
        warn(f"Falha ao buscar opções de {symbol}: {e}")
        cols = ["symbol","underlying_symbol","expiration","type","strike","bid","ask","last","close","volume","open_interest","ref_price"]
        return pd.DataFrame(columns=cols)

# ===============================
# Black-Scholes + IV local
# ===============================
def _bs_price_greeks(S: float, K: float, T: float, r: float, sigma: float, call_put: str):
    """Retorna (price, delta, gamma, vega, theta, rho). r e sigma anuais (decimais)."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return (np.nan,)*6
    cp = 1 if str(call_put).upper() == "CALL" else -1
    try:
        sqrtT = math.sqrt(T)
        d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*sqrtT)
        d2 = d1 - sigma*sqrtT

        price = cp*(S*norm.cdf(cp*d1) - K*math.exp(-r*T)*norm.cdf(cp*d2))
        delta = cp*norm.cdf(cp*d1)
        gamma = norm.pdf(d1) / (S*sigma*sqrtT)
        vega  = S*norm.pdf(d1)*sqrtT
        theta = (-(S*norm.pdf(d1)*sigma)/(2*sqrtT) - cp*r*K*math.exp(-r*T)*norm.cdf(cp*d2))
        rho   = cp*K*T*math.exp(-r*T)*norm.cdf(cp*d2)
        return price, delta, gamma, vega, theta, rho
    except Exception:
        return (np.nan,)*6

def _implied_vol(S, K, T, r, premium, call_put):
    """IV via Brent. Retorna sigma (decimal)."""
    if not all(pd.notna([S, K, T, r, premium])) or S <= 0 or K <= 0 or T <= 0 or premium <= 0:
        return np.nan
    try:
        return brentq(lambda s: _bs_price_greeks(S, K, T, r, s, call_put)[0] - premium,
                      1e-3, 5.0, maxiter=100, disp=False)
    except Exception:
        return np.nan

# ===============================
# Contexto de volume do ativo (volume financeiro + MM20)
# ===============================
def preparar_contexto_ativos(df_at: pd.DataFrame, ma: int = 20) -> pd.DataFrame:
    """
    Calcula, por ativo, o último registro com:
      - volume_fin: close * volume
      - volfin_ma: MM20 de volume financeiro
      - vol_acima_ma: 1 se volume_fin > volfin_ma (no último dia), senão 0
      - last_close
    """
    if df_at is None or df_at.empty:
        return pd.DataFrame(columns=["underlying_symbol","volume_fin","volfin_ma","vol_acima_ma","last_close"])

    d = df_at.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d.sort_values(["underlying_symbol","date"], inplace=True)

    d["volume"] = _to_num(d.get("volume"))
    d["close"]  = _to_num(d.get("close"))

    d["volume_fin"] = d["close"] * d["volume"]
    d["volfin_ma"] = (
        d.groupby("underlying_symbol", group_keys=False)["volume_fin"]
         .transform(lambda s: pd.Series(s).rolling(ma, min_periods=1).mean().values)
    )
    d["vol_acima_ma"] = (d["volume_fin"] > d["volfin_ma"]).astype(int)

    last = (
        d.groupby("underlying_symbol", as_index=False)
         .tail(1)[["underlying_symbol","volume_fin","volfin_ma","vol_acima_ma","close"]]
         .rename(columns={"close":"last_close"})
         .reset_index(drop=True)
    )
    return last

# ===============================
# Enriquecimento: mid/spread, DTE/tempo, IV/greeks, percentis
# ===============================
def add_features_and_iv(df_opts: pd.DataFrame, price_lookup: dict[str, float] | None, r_annual: float) -> pd.DataFrame:
    if df_opts is None or df_opts.empty:
        return df_opts

    d = df_opts.copy()

    # Mid / spread
    for c in ["bid","ask","last","close","strike","volume","open_interest","ref_price"]:
        d[c] = _to_num(d.get(c))

    d["mid"] = np.where(
        pd.notna(d["bid"]) & pd.notna(d["ask"]) & (d["bid"]>0) & (d["ask"]>0),
        (d["bid"] + d["ask"]) / 2.0,
        np.where(pd.notna(d["last"]) & (d["last"]>0), d["last"], d["close"])
    )
    # Spread REAL — só existe se bid > 0 e ask > 0
    d["spread"] = np.where(
        (d["bid"] > 0) & (d["ask"] > 0),
        d["ask"] - d["bid"],
        np.nan
    )
    
    # Spread relativo REAL — calculado sobre LAST
    d["spread_rel"] = np.where(
        d["spread"].notna() & (d["last"] > 0),
        d["spread"] / d["last"],
        np.nan
    )


    # Datas e tempo (T)
    # Datas e tempo (T) — corrigido para evitar erro de conversão timedelta64[D]
    hoje = date.today()
    d["expiration"] = pd.to_datetime(d.get("expiration"), errors="coerce")

    # calcula dias até o vencimento de forma robusta
    d["dte_calendar"] = (d["expiration"].dt.date - hoje).apply(
        lambda x: x.days if pd.notna(x) else np.nan
    )

    d["dte_bus"] = d["dte_calendar"].clip(lower=1)  # úteis aproximados
    d["T"] = (d["dte_bus"] / 252.0).clip(lower=1 / 365.0)

    # Preço de referência do subjacente
    if "ref_price" not in d.columns:
        d["ref_price"] = np.nan
    if price_lookup:
        mask_na = d["ref_price"].isna()
        if mask_na.any():
            d.loc[mask_na, "ref_price"] = d.loc[mask_na, "underlying_symbol"].map(price_lookup)

    # Premium a usar
    d["premium_used"] = np.where(d["last"]>0, d["last"], np.where(d["mid"]>0, d["mid"], d["close"]))

    # Tipagem
    d["type"] = d["type"].astype(str).str.upper().replace({"C":"CALL","P":"PUT"})
    d["option_type"] = np.where(d["type"].isin(["CALL","PUT"]), d["type"], "CALL")

    # IV
    d["iv_local"] = d.apply(lambda r: _implied_vol(r["ref_price"], r["strike"], r["T"], r_annual, r["premium_used"], r["option_type"]), axis=1)
    d["iv_local_pct"] = d["iv_local"] * 100.0

    # Greeks
    greeks = d.apply(lambda r: pd.Series(_bs_price_greeks(r["ref_price"], r["strike"], r["T"], r_annual,
                                                         r["iv_local"] if pd.notna(r["iv_local"]) and r["iv_local"]>0 else np.nan,
                                                         r["option_type"]),
                                         index=["bs_price","delta","gamma","vega","theta","rho"]), axis=1)
    d = pd.concat([d, greeks], axis=1)
    d["delta_abs"] = d["delta"].abs()

    # Percentil local de IV por ativo+vencimento
    d["iv_pct_local"] = (
        d.groupby(["underlying_symbol","expiration"])["iv_local_pct"]
         .transform(lambda s: 100*s.rank(pct=True, method="average"))
    )

    # Limpeza
    d["spread_rel"] = d["spread_rel"].fillna(1.0).clip(0, 5)

    return d

# ===============================
# Filtros e ranking
# ===============================
def aplicar_filtros(
    d: pd.DataFrame,
    tipo_opcao: str,
    venc_ini: date,
    venc_fim: date,
    delta_min: float,
    delta_max: float,
    iv_pct_max: float,
    min_volume_opt: float,
    max_spread_rel: float,
    exigir_vol_acima: bool
) -> pd.DataFrame:

    if d is None or d.empty:
        return d

    # ===============================
    # CÓPIA CORRETA DO DATAFRAME
    # ===============================
    x = d.copy()

    # ===============================
    # Filtrar apenas spreads reais (bid>0 e ask>0)
    # ===============================
    x = x[(x["bid"] > 0) & (x["ask"] > 0)]

    # ===============================
    # Janela de vencimento
    # ===============================
    x = x[x["expiration"].between(pd.to_datetime(venc_ini), pd.to_datetime(venc_fim))]

    # ===============================
    # Tipo CALL/PUT
    # ===============================
    if tipo_opcao in ("CALL", "PUT"):
        x = x[x["type"] == tipo_opcao]

    # ===============================
    # Garantir volume
    # ===============================
    if "volume" not in x.columns:
        if "volume_x" in x.columns: 
            x["volume"] = x["volume_x"]
        elif "volume_y" in x.columns: 
            x["volume"] = x["volume_y"]
        else: 
            x["volume"] = np.nan

    x["volume"] = _to_num(x["volume"])

    # ===============================
    # Condições finais
    # ===============================
    cond = (
        x["delta_abs"].between(delta_min, delta_max, inclusive="both")
        & (x["iv_pct_local"] <= iv_pct_max)
        & (x["volume"].fillna(0) >= min_volume_opt)
        & (x["spread_rel"].fillna(1.0) <= max_spread_rel)
        & x["T"].gt(0)
    )

    return x.loc[cond.fillna(False)].copy()



def _norm01(s: pd.Series, invert: bool = False) -> pd.Series:
    s = _to_num(s)
    if s.nunique(dropna=True) <= 1:
        n = pd.Series(0.5, index=s.index)
    else:
        n = (s - s.min()) / (s.max() - s.min() + 1e-12)
    n = n.fillna(0.5)
    return (1 - n) if invert else n

def rankear(d: pd.DataFrame, delta_target=0.45, exigir_vol_acima=False) -> pd.DataFrame:
    if d is None or d.empty:
        return d

    x = d.copy().reset_index(drop=True)

    # Normalizações auxiliares
    def _norm01(s: pd.Series, invert: bool = False) -> pd.Series:
        s = _to_num(s)
        if s.nunique(dropna=True) <= 1:
            n = pd.Series(0.5, index=s.index)
        else:
            n = (s - s.min()) / (s.max() - s.min() + 1e-12)
        n = n.fillna(0.5)
        return (1 - n) if invert else n

    # Score base (sem volume acima da MM20 ainda)
    x["score_base"] = (
        0.40 * _norm01(x["iv_pct_local"], invert=True) +     # preferir IV % local baixo
        0.30 * _norm01(x["volume"]) +                        # preferir volume alto
        0.20 * _norm01((x["delta_abs"] - delta_target).abs(), invert=True) +  # delta próximo
        0.10 * _norm01(x["spread_rel"], invert=True)          # preferir spread pequeno
    )

    # 💡 Bônus proporcional baseado no volume relativo ao MM20
    if exigir_vol_acima and {"volume_fin", "volfin_ma"}.issubset(x.columns):
        ratio = (x["volume_fin"] / x["volfin_ma"]).replace([np.inf, -np.inf], np.nan)
        ratio = ratio.clip(lower=0.5, upper=2.0)  # evita distorções
        bonus = (ratio - 1.0) * 0.25              # até ±25%
        x["score"] = np.clip(x["score_base"] * (1 + bonus), 0, None)
    else:
        x["score"] = x["score_base"]

    return x.sort_values("score", ascending=False)


def top_por_venc(d: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    if d is None or d.empty:
        return d
    return (
        d.sort_values(["expiration","score"], ascending=[True, False])
         .groupby("expiration", as_index=False)
         .head(n)
    )

# ===============================
# UI — Sidebar
# ===============================
with st.sidebar:
    st.title("⚙️ Parâmetros do Scanner")

    symbols = st.multiselect(
        "Ativos (subjacentes)",
        ["PETR4","BOVA11","VALE3","ITUB4","WEGE3","ABEV3","BBDC4","BBAS3","EMBR3","MGLU3"],
        default=["BOVA11"]
    )
    days = st.number_input("Dias de histórico (candles)", min_value=30, max_value=365, value=180, step=5)

    st.markdown("---")
    taxa_juros = st.number_input("Taxa de juros anual (%)", min_value=0.0, max_value=50.0, value=14.90, step=0.10) / 100.0

    st.markdown("---")
    tipo_opcao = st.radio("Tipo de opção", options=["Ambas","CALL","PUT"], index=0, horizontal=True)

    col_v1, col_v2 = st.columns(2)
    # ===============================
    # 🗓️ Cálculo automático do vencimento mais próximo
    # ===============================

    import calendar
    
    def proximo_vencimento_opcoes(base: date | None = None) -> date:
        """Retorna a 3ª sexta-feira do mês atual (se ainda não passou) ou a do mês seguinte."""
        if base is None:
            base = datetime.today().date()
    
        ano, mes = base.year, base.month
        c = calendar.Calendar(firstweekday=calendar.MONDAY)
    
        # Lista todas as sextas-feiras do mês
        sextas = [d for d in c.itermonthdates(ano, mes) if d.weekday() == 4 and d.month == mes]
    
        # Se a 3ª sexta ainda não passou neste mês, usa ela
        if len(sextas) >= 3 and base <= sextas[2]:
            return sextas[2]
        else:
            # Caso já tenha passado, pega a 3ª sexta do mês seguinte
            mes = 1 if mes == 12 else mes + 1
            ano = ano + 1 if mes == 1 else ano
            sextas = [d for d in c.itermonthdates(ano, mes) if d.weekday() == 4 and d.month == mes]
            return sextas[2] if len(sextas) >= 3 else base + timedelta(days=30)
    
    # ===== Sidebar =====
    prox_venc = proximo_vencimento_opcoes()
    
    with col_v1:
        venc_ini = st.date_input("Venc. inicial", prox_venc)
    with col_v2:
        venc_fim = st.date_input("Venc. final", prox_venc)



    st.markdown("---")
    delta_min = st.slider("Delta mínimo (abs)", 0.0, 1.0, 0.30, 0.01)
    delta_max = st.slider("Delta máximo (abs)", 0.0, 1.0, 0.60, 0.01)
    iv_pct_max = st.slider("IV percentil local máx. (%)", 0, 100, 60, 1)
    min_vol_opt = st.number_input("Volume mínimo (opção)", 0, 200000, 0, 100)
    max_spread_rel = st.slider("Spread relativo máx.", 0.0, 5.0, 1.0, 0.05)
    exigir_vol_acima = st.checkbox("Exigir volume do ativo acima da MM20 (volume financeiro)", value=False)

    st.markdown("---")
    delta_target = st.slider("Delta alvo p/ score", 0.0, 1.0, 0.45, 0.01)
    top_n = st.number_input("Top por vencimento", 1, 10, 5)

    st.markdown("---")
    btn_run = st.button("🌀 Rodar Scanner", type="primary", use_container_width=True)

# ===============================
# UI — Main
# ===============================
st.title("🧠Scanner de Opções")

# ===============================
# Explicação — Score de Oportunidade (posicionado logo abaixo do título)
# ===============================
st.markdown("""
<style>
.expander-dark {
    background-color: #1A1D23 !important;
    border: 1px solid #2B2F36 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.5);
}
.expander-dark div[role='button'] {
    color: #00C896 !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
}
.expander-dark p, .expander-dark li {
    color: #E0E0E0 !important;
    font-size: 0.9rem !important;
    line-height: 1.5em;
}
</style>
""", unsafe_allow_html=True)

with st.expander("📘 Entendendo o Score de Oportunidade", expanded=False):
    st.markdown("""
O **Score de Oportunidade** classifica as opções conforme sua **atratividade relativa**, 
combinando **preço justo, liquidez e eficiência de volatilidade**.  
Ele é calculado com base em quatro fatores principais:

- 📉 **Volatilidade implícita (IV%) local:** prioriza opções com IV mais baixa dentro do vencimento (menor sobrepreço);  
- ⚡ **Volume de negociação:** valoriza contratos com maior liquidez;  
- 🎯 **Delta:** favorece deltas próximos do alvo definido (ex: 0,45);  
- 💸 **Spread relativo:** penaliza opções com diferença grande entre bid e ask.

O resultado é um **Score entre 0 e 1**, onde valores mais altos indicam melhor equilíbrio entre **risco, liquidez e eficiência**.
""")

    import plotly.graph_objects as go
    fatores = ["IV% (baixa)", "Volume", "Delta (alvo)", "Spread (baixo)"]
    pesos = [0.40, 0.30, 0.20, 0.10]

    fig_score = go.Figure(
        go.Bar(
            x=pesos,
            y=fatores,
            orientation='h',
            text=[f"{p*100:.0f}%" for p in pesos],
            textposition='outside',
            marker=dict(
                color=['#00E6A8', '#00C896', '#009F80', '#007B66'],
                line=dict(color='#0E1117', width=1)
            )
        )
    )
    fig_score.update_layout(
        template='plotly_dark',
        height=300,
        margin=dict(l=40, r=40, t=20, b=20),
        xaxis=dict(title="Peso (%)", range=[0, 0.5]),
        yaxis=dict(title=""),
        showlegend=False,
        plot_bgcolor='#0E1117',
        paper_bgcolor='#0E1117',
        font=dict(color='#FFFFFF', size=12)
    )

    st.plotly_chart(fig_score, use_container_width=True)


# Estado
if "ativos" not in st.session_state:  st.session_state["ativos"] = pd.DataFrame()
if "opcoes" not in st.session_state:  st.session_state["opcoes"] = pd.DataFrame()

# ===============================
# Estado e execução automática
# ===============================
if "primeira_execucao" not in st.session_state:
    st.session_state["primeira_execucao"] = True
else:
    st.session_state["primeira_execucao"] = False


# Executa automaticamente na primeira abertura da página
if btn_run or st.session_state["primeira_execucao"]:

    if not symbols:
        err("Selecione ao menos um ativo.")
        st.stop()

    with st.status("Baixando e preparando dados...", expanded=True) as status:
        try:
            # 1) Download
            dfs_at, dfs_op = [], []
            for sym in symbols:
                with st.spinner(f"Baixando dados de {sym}..."):
                    dfs_at.append(fetch_candles(sym, int(days)))
                    dfs_op.append(fetch_options_snapshot(sym))


            at = pd.concat(dfs_at, ignore_index=True) if dfs_at else pd.DataFrame()
            op = pd.concat(dfs_op, ignore_index=True) if dfs_op else pd.DataFrame()

            if at.empty or op.empty:
                err("Sem dados suficientes (ativos ou opções).")
                st.stop()

            # 2) Contexto volume (financeiro) e merge
            ctx = preparar_contexto_ativos(at, ma=20)
            last_close_map = dict(zip(ctx["underlying_symbol"], ctx["last_close"]))

            # injeta flag no book
            book_raw = op.merge(
                ctx.rename(columns={"volume_fin":"volume_fin_acao","volfin_ma":"volfin_ma_acao"}),
                on="underlying_symbol", how="left"
            )

            # 3) Enriquecer com IV/greeks etc.
            book = add_features_and_iv(book_raw, price_lookup=last_close_map, r_annual=taxa_juros)

            # 4) Aplicar filtros
            flt = aplicar_filtros(
                book,
                tipo_opcao=tipo_opcao,
                venc_ini=venc_ini, venc_fim=venc_fim,
                delta_min=delta_min, delta_max=delta_max,
                iv_pct_max=float(iv_pct_max),
                min_volume_opt=float(min_vol_opt),
                max_spread_rel=float(max_spread_rel),
                exigir_vol_acima=bool(exigir_vol_acima)
            )

            # 5) Ranking e top por vencimento
            ranked = rankear(flt, delta_target=delta_target, exigir_vol_acima=exigir_vol_acima)
            top = top_por_venc(ranked, n=int(top_n))

            status.update(label="Concluído", state="complete")

            # ====== Saída principal ======
            # ====== Saída principal ======
            # ====== Saída principal ======
            # ====== Saída principal ======


          
        
            st.subheader("🏆 Top Oportunidades por Vencimento 💎")

            


            if top.empty:
                warn("Nenhuma oportunidade encontrada com os critérios atuais. Afrouxe IV %, delta ou spread.")
            else:
                # 🔢 Ordena por score decrescente
                top = top.sort_values("score", ascending=False).reset_index(drop=True)

                # 🧾 Ajustes visuais
                top["expiration"] = pd.to_datetime(top["expiration"], errors="coerce").dt.date  # só data
                num_cols = top.select_dtypes(include=["float", "float64", "int", "int64"]).columns
                top[num_cols] = top[num_cols].apply(lambda x: np.round(x, 2))  # arredonda 2 casas

                # Coloca 'score' na 1ª coluna
                cols = ["score"] + [c for c in top.columns if c != "score"]

                # 💎 Destaques — Top 5 Cards com gradiente dinâmico
               
                #st.markdown("### 💎 Destaques (Top 5 Scores Globais)")#

                # 🔹 Garante que o número de cards nunca passe de 10, mesmo que o usuário altere o código
                num_cards = min(int(top_n), 10)
                top5 = top.head(num_cards).copy()
                # SALVA NO SESSION_STATE PARA USAR FORA DO LOOP
                st.session_state["top5"] = top5





                def get_card_gradient(score, tipo):
                    """Gradiente dinâmico de cor baseado no score e tipo (CALL/PUT)."""
                    s = float(score)
                    if tipo == "CALL":
                        start, end = "#004d00", "#66ff66"  # verde escuro → verde claro
                    else:
                        start, end = "#7f0000", "#ff6666"  # vermelho escuro → vermelho claro
                    return f"linear-gradient(135deg, {start} {(s*100):.0f}%, {end})"

                # 🟢 inicializa a variável antes do loop               


                
                card_html = ""  # ainda usado para o container final

                for _, row in top5.iterrows():                  

                  grad = get_card_gradient(row["score"], row["type"])
                  delta_color = "lime" if row["type"] == "CALL" else "salmon"
              
                  card_html += f"""
                  <div class="card" style="background-image: {grad};">
                      <div class="symbol">{row['symbol']} ({row['type']})</div>
                      <div class="score-label">Score</div>
                      <div class="score">{row['score']:.2f}</div>
                      <div class="details">Strike {row['strike']:.2f} • Venc. {row['expiration']}</div>
                      <div class="delta-line">
                          <span style='color:{delta_color}; font-weight:600;'>Δ {row['delta']:.2f}</span>
                      </div>
                  </div>
                  """
                



                st.markdown(
                    f"""
                    <style>
                    .card {{
                        display: inline-block;
                        border-radius: 16px;
                        padding: 16px 18px;
                        margin: 8px;
                        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                        color: white;
                        transition: all 0.25s ease;
                        width: 16.5%; /* 🔹 menor largura — garante 5 por linha */
                        text-align: center;
                        min-height: 180px;
                    }}
                    .card:hover {{
                        transform: translateY(-4px) scale(1.03);
                        box-shadow: 0 6px 14px rgba(0,0,0,0.6);
                        cursor: pointer;
                    }}
                    .symbol {{
                        font-weight: 600;
                        font-size: 1rem;
                        margin-bottom: 6px;
                    }}
                    .score-label {{
                        font-size: 0.8rem;
                        color: rgba(255,255,255,0.9);
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}
                    .score {{
                        font-size: 1.8rem;
                        font-weight: 700;
                        margin-bottom: 6px;
                        color: #fff;
                        text-shadow: 0 0 10px rgba(255,255,255,0.5);
                    }}
                    .details {{
                        font-size: 0.85rem;
                        color: rgba(255,255,255,0.85);
                    }}
                    .delta-line {{
                        margin-top: 4px;
                    }}
                
                    /* 🔹 Responsividade — ajustado */
                    @media (max-width: 1800px) {{
                        .card {{ width: 17%; }}
                    }}
                    @media (max-width: 1300px) {{
                        .card {{ width: 22%; }} /* 4 por linha */
                    }}
                    @media (max-width: 1000px) {{
                        .card {{ width: 45%; }} /* 2 por linha */
                    }}
                    @media (max-width: 600px) {{
                        .card {{
                            width: 90%;
                            padding: 14px 16px;
                        }}
                        .symbol {{ font-size: 0.95rem; }}
                        .score-label {{ font-size: 0.7rem; }}
                        .score {{ font-size: 1.5rem; }}
                        .details {{ font-size: 0.8rem; }}
                    }}
                    @media (max-width: 400px) {{
                        .card {{
                            width: 95%;
                            padding: 12px 14px;
                        }}
                        .symbol {{ font-size: 0.9rem; }}
                        .score {{ font-size: 1.3rem; }}
                        .details {{ font-size: 0.75rem; }}
                    }}
                
                    /* 🔹 Container flexível centralizado e alinhamento perfeito */
                    .cards-container {{
                        display: flex;
                        flex-wrap: wrap;
                        justify-content: center;
                        align-items: stretch;
                        gap: 10px;
                    }}
                    </style>
                
                    <div class="cards-container">
                        {card_html}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("---")

                # 🧠 Coloração condicional da tabela com gradiente idêntico
                # 🧠 Coloração condicional da tabela com gradiente idêntico
                def score_color(val, tipo):
                    if pd.isna(val):
                        return ""
                    s = float(val)
                    s = max(0, min(s, 1))
                    if tipo == "CALL":
                        dark = np.array([0, 77, 0])      # #004d00
                        light = np.array([102, 255, 102])  # #66ff66
                    else:
                        dark = np.array([127, 0, 0])     # #7f0000
                        light = np.array([255, 102, 102])  # #ff6666
                    rgb = (dark * s + light * (1 - s)).astype(int)
                    color = f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"
                    return f"background-color: {color}; color: black; font-weight: 700;"

                # Determina colunas financeiras
                financial_cols = [
                    c for c in top.columns if any(k in c.lower() for k in ["price", "premium", "strike", "ref_", "volfin", "volume"])
                ]

                # Formata todas as colunas numéricas para 2 casas e adiciona R$ em valores financeiros
                fmt = {}
                for c in top.columns:
                    if c in financial_cols:
                        fmt[c] = "R$ {:,.2f}".format
                    elif top[c].dtype.kind in "fi":
                        fmt[c] = "{:.2f}".format

                styled_df = (
                    top[cols]
                    .style
                    .format(fmt)
                    .apply(
                        lambda r: [score_color(r["score"], r["type"])] + ["" for _ in range(len(r) - 1)],
                        axis=1
                    )
                )

                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True
                )





            # ====== Gráficos de candles ======
            # ====== Gráficos de candles ======
            st.markdown("---")
            st.subheader("📈 Candles (últimos dias) — OHLCV")
            st.caption("OHLCV = Open, High, Low, Close, Volume. Volume abaixo é financeiro (Close × Volume) com MM20 branca.")

            if at.empty:
                warn("Candles indisponíveis.")
            else:
                for sym in sorted(set(at["underlying_symbol"])):
                    d = at[at["underlying_symbol"] == sym].sort_values("date").tail(180)
                    if d.empty:
                        continue

                    # Volume financeiro + MM20
                    d["vol_fin"] = _to_num(d["close"]) * _to_num(d["volume"])
                    d["volfin_ma20"] = d["vol_fin"].rolling(20, min_periods=1).mean()

                    fig = go.Figure()

                    # 📊 Candles (eixo Y principal)
                    fig.add_trace(go.Candlestick(
                        x=d["date"],
                        open=d["open"], high=d["high"], low=d["low"], close=d["close"],
                        name=f"{sym} OHLC",
                        increasing_line_color="lime",
                        decreasing_line_color="red",
                        yaxis="y1"
                    ))

                    # 💙 Volume financeiro — barras azuis sólidas
                    fig.add_trace(go.Bar(
                        x=d["date"],
                        y=d["vol_fin"],
                        name="Volume financeiro",
                        marker_color="deepskyblue",
                        yaxis="y2",
                        opacity=0.6
                    ))

                    # 💬 (opcional) Volume verde/vermelho conforme variação:
                    # colors = np.where(d["close"] >= d["open"], "limegreen", "crimson")
                    # fig.add_trace(go.Bar(
                    #     x=d["date"], y=d["vol_fin"],
                    #     name="Volume financeiro",
                    #     marker_color=colors,
                    #     yaxis="y2", opacity=0.6
                    # ))

                    # Linha da MM20 branca
                    fig.add_trace(go.Scatter(
                        x=d["date"],
                        y=d["volfin_ma20"],
                        name="MM20 Vol (R$)",
                        mode="lines",
                        line=dict(color="white", width=1.5),
                        yaxis="y2"
                    ))

                    fig.update_layout(
                        title=f"{sym}",
                        height=550,
                        template="plotly_dark",
                        xaxis=dict(
                            domain=[0.0, 1.0],
                            rangeslider=dict(visible=False),
                            showline=True,
                            linecolor="#555",
                            mirror=True
                        ),
                        # Preço (candles) — painel superior
                        yaxis=dict(
                            title="Preço",
                            domain=[0.35, 1.0],   # 65% do topo
                            side="left",
                            showgrid=True
                        ),
                        # Volume — painel inferior (separado dos candles)
                        yaxis2=dict(
                            title="Volume (R$)",
                            domain=[0.0, 0.30],   # 30% da parte inferior
                            showgrid=False
                            # (sem overlaying!)
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        margin=dict(l=40, r=40, t=50, b=20)
                    )


                    st.plotly_chart(fig, use_container_width=True)


            # ====== Dados brutos (opcional para debug) ======
            with st.expander("📦 Dados brutos (opcional)"):
                st.caption("Ativos (OHLCV)")
                st.dataframe(at, use_container_width=True, hide_index=True)

                st.caption("Opções (processadas com IV/greeks)")
                show_cols = [
                    "symbol","underlying_symbol","type","expiration","strike",
                    "bid","ask","last","close","premium_used",
                    "ref_price","T","dte_bus",
                    "iv_local_pct","iv_pct_local",
                    "delta","gamma","vega","theta","rho",
                    "volume","open_interest","spread","spread_rel","moneyness",
                    "vol_acima_ma","score"
                ]
                show_cols = [c for c in show_cols if c in book.columns]
                st.dataframe(book[show_cols], use_container_width=True, hide_index=True)

        except Exception as e:
            status.update(label="Erro no processamento", state="error")
            err(str(e))




def obter_underlying_opcao(symbol: str) -> str:
    """
    Busca o underlying real da opção via endpoint de detalhes.
    Usa parent_symbol como fonte oficial.
    """
    url = f"{OPLAB_BASE_URL}/market/options/details/{symbol}"
    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        r.raise_for_status()
        data = r.json()

        parent = data.get("parent_symbol")
        if parent:
            return str(parent).upper()
        return "N/D"

    except Exception:
        return "N/D"



# ============================================
# BOTÕES DE ENVIO DE OPERAÇÃO
# ============================================
# ============================================
# BOTÕES DE ENVIO DE OPERAÇÃO
# ============================================
st.markdown("### 📩 Enviar operações para o Supabase")

top5 = st.session_state.get("top5", pd.DataFrame())

required_cols = [
    "symbol","type","strike","expiration","underlying_symbol",
    "last","mid","close"
]

missing = [c for c in required_cols if c not in top5.columns]

if missing:
    st.error(f"❌ top5 sem colunas essenciais: {missing}")

else:
    for idx, row in top5.iterrows():

        symbol = row["symbol"]

        if st.button(f"Enviar {symbol}", key=f"send_{idx}"):

            # ============================
            # PREÇO DE ENTRADA — LAST AO VIVO
            # ============================
            last_snap = float(row.get("last", 0) or 0)

            if last_snap <= 0:
                # Buscar LAST do endpoint correto /details
                try:
                    url = f"{OPLAB_BASE_URL}/market/options/details/{symbol}"
                    r = requests.get(url, headers=_headers(), timeout=10)
                    r.raise_for_status()
                    d = r.json()
                    last_snap = float(d.get("close", 0) or 0)
                except:
                    last_snap = 0

            if last_snap > 0:
                preco_entrada = last_snap
            else:
                preco_entrada = float(row.get("close", 0) or 0.01)

            venc_str = row["expiration"].strftime("%Y-%m-%d")

            # ============================
            # REGISTRO NO SUPABASE
            # ============================
            nova_op = {
                "source": "scanner",
                "indice": "OPCOES",
                "symbol": symbol,
                "underlying": obter_underlying_opcao(symbol),
                "tipo": row["type"],
                "strike": float(row["strike"]),
                "vencimento": venc_str,
                "lado_entrada": "COMPRA",
                "preco_entrada": preco_entrada,
                "status": "aberta",
                "stop_protecao_pct": -25,
                "alvo_atual_pct": 0,
                "retorno_atual_pct": 0,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            try:
                op_id = inserir_operacao(nova_op)

                # ====================================
                # CRIAÇÃO DA MENSAGEM DO TELEGRAM (HTML CERTINHO)
                # ====================================
                msg_telegram = (
                    "💥 <b>NOVA OPERAÇÃO — SCANNER FÊNIX</b>\n\n"
                    f"<b>Opção:</b> {symbol} ({row['type']})\n"
                    f"<b>Strike:</b> {row['strike']}\n"
                    f"<b>Vencimento:</b> {venc_str}\n"
                    f"<b>Preço entrada:</b> {preco_entrada}\n\n"
                    "______________________________\n\n"
                    "<i>COMPLIANCE: mensagem baseada em nossa carteira e não constitui "
                    "recomendação formal. A decisão de compra ou venda é exclusiva do "
                    "destinatário. Conteúdo confidencial, uso restrito ao destinatário "
                    "autorizado. © Aurinvest.</i>\n\n"
                    "🤖 Robot Aurinvest"
                )


                # ====================================
                # EMAIL (HTML)
                # ====================================
                msg_email = f"""
                <h2>💥 Nova Operação — Scanner Fênix</h2>
                <b>Opção:</b> {symbol} ({row['type']})<br>
                <b>Strike:</b> {row['strike']}<br>
                <b>Vencimento:</b> {venc_str}<br>
                <b>Preço Entrada:</b> {preco_entrada}<br>
                <br><hr>
                <p style="font-size:11px; color:#888;">
                COMPLIANCE: mensagem baseada em nossa carteira e não constitui recomendação formal.
                A decisão de compra ou venda é exclusiva do destinatário.
                Conteúdo confidencial, uso restrito ao destinatário autorizado. © Aurinvest.<br>
                🤖 Robot Aurinvest
                </p>
                """

                # ====================================
                # ENVIOS
                # ====================================
                enviar_telegram(msg_telegram)
                enviar_email("💥 Nova Operação — Scanner Phoenix", msg_email)

                st.success(f"Operação enviada com sucesso! (ID: {op_id})")

            except Exception as e:
                st.error(f"Erro ao enviar operação: {e}")
                raise



# ============================================
# 🔍 BOTÃO CHECAR – MONITORAMENTO DAS OPERAÇÕES
# ============================================
# ============================================
# 🔍 BOTÃO CHECAR – MONITORAMENTO DAS OPERAÇÕES
# ============================================

REST_ENDPOINT = getattr(supabase_ops_mod, "REST_ENDPOINT", None)
HEADERS = getattr(supabase_ops_mod, "HEADERS", None)


def _carregar_operacoes_abertas():
    """Busca no Supabase todas as operações de opções em status 'aberta'."""
    if not REST_ENDPOINT or not HEADERS:
        return []

    params = {
        "select": "id,symbol,underlying,tipo,strike,vencimento,"
                  "preco_entrada,preco_atual,retorno_atual_pct,"
                  "stop_protecao_pct,status",
        "status": "eq.aberta",
        "indice": "eq.OPCOES",
    }

    resp = requests.get(REST_ENDPOINT, headers=HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()



def _atualizar_operacao_supabase(op_id: str, dados: dict):
    """Atualiza uma operação específica no Supabase."""
    if not REST_ENDPOINT or not HEADERS:
        return

    params = {"id": f"eq.{op_id}"}
    resp = requests.patch(
        REST_ENDPOINT,
        headers=HEADERS,
        params=params,
        json=dados,
        timeout=20
    )
    resp.raise_for_status()


def obter_preco_opcao(symbol: str) -> float | None:
    """
    PREÇO REAL da opção — usando o campo 'close' do endpoint /details,
    que na documentação do Oplab está descrito como 'Último preço'.
    """
    url = f"{OPLAB_BASE_URL}/market/options/details/{symbol}"

    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        r.raise_for_status()
        data = r.json()

        preco = float(data.get("close", 0) or 0)  # close = Último preço
        return preco if preco > 0 else None

    except Exception as e:
        print("Erro ao buscar preço da opção:", e)
        return None



def _ajustar_stop_dinamico(retorno_pct: float, stop_atual: float) -> float:
    """
    Stop dinâmico infinito, mantendo a lógica original:
    """
    if retorno_pct < 25:
        novo_stop = stop_atual
    elif retorno_pct < 50:
        novo_stop = 5.0
    elif retorno_pct < 75:
        novo_stop = 25.0
    elif retorno_pct < 100:
        novo_stop = 50.0
    else:
        acima_100 = retorno_pct - 100
        blocos_extra = int(acima_100 // 50)
        novo_stop = 75.0 + blocos_extra * 25.0

    return max(stop_atual, novo_stop)


def checar_operacoes_scanner():
    """Executa o monitoramento manual das operações abertas."""
    try:
        ops = _carregar_operacoes_abertas()
    except Exception as e:
        st.error(f"Erro ao carregar operações abertas: {e}")
        return 0, 0

    if not ops:
        st.info("Nenhuma operação aberta encontrada no Supabase.")
        return 0, 0

    hoje = date.today()
    encerradas = 0

    with st.status("Checando operações abertas...", expanded=False) as status:
        for op in ops:

            op_id = op["id"]
            symbol = op["symbol"]
            preco_entrada = float(op["preco_entrada"])
            stop_atual = float(op.get("stop_protecao_pct", -25))

            # ============================
            # PREÇO ATUAL — sempre LAST real
            # ============================
            preco_atual = obter_preco_opcao(symbol)

            # ❗ Se NÃO conseguir obter preço, NÃO inventa nada
            #    Não copia preco_entrada, não zera retorno.
            if preco_atual is None or preco_atual <= 0:
                dados_update = {
                    "updated_at": datetime.utcnow().isoformat(),
                }
                _atualizar_operacao_supabase(op_id, dados_update)
                continue

            # Recalcula retorno %
            retorno_pct = ((preco_atual / preco_entrada) - 1.0) * 100.0

            # Ajusta stop
            novo_stop = _ajustar_stop_dinamico(retorno_pct, stop_atual)

            # Dias até vencimento
            try:
                venc_date = datetime.strptime(op["vencimento"], "%Y-%m-%d").date()
                dias_para_venc = (venc_date - hoje).days
            except:
                dias_para_venc = 999

            motivo_saida = None

            if dias_para_venc <= 3:
                motivo_saida = "Vencimento (D-3)"
            elif retorno_pct <= novo_stop:
                motivo_saida = f"Stop {novo_stop:.1f}%"

            # ============================
            # SE ENCERRA
            # ============================
            if motivo_saida:

                # Preço de saída = LAST no momento do encerramento
                preco_saida = obter_preco_opcao(symbol)

                dados_update = {
                    "status": "encerrada",
                    "preco_saida": preco_saida,
                    "retorno_final_pct": round(retorno_pct, 2),
                    "motivo_saida": motivo_saida,
                    "lado_saida": "VENDA",
                    "timestamp_saida": datetime.utcnow().isoformat(),
                    "preco_atual": preco_atual,
                    "retorno_atual_pct": round(retorno_pct, 2),
                    "stop_protecao_pct": round(novo_stop, 2),
                    "updated_at": datetime.utcnow().isoformat(),
                }

                _atualizar_operacao_supabase(op_id, dados_update)
                encerradas += 1

                # Notificações
                msg_tel = (
                    "🔔 <b>OPERAÇÃO ENCERRADA — SCANNER FÊNIX</b>\n\n"
                    f"<b>Opção:</b> {symbol} ({op['tipo']})\n"
                    f"<b>Strike:</b> {op['strike']}\n"
                    f"<b>Vencimento:</b> {op['vencimento']}\n"
                    f"<b>Motivo:</b> {motivo_saida}\n"
                    f"<b>Retorno Final:</b> {retorno_pct:.1f}%\n"
                    f"<b>Preço Entrada:</b> {preco_entrada}\n"
                    f"<b>Preço Saída:</b> {preco_atual}\n\n"
                    "______________________________\n\n"
                    "<i>COMPLIANCE: mensagem baseada em nossa carteira e não constitui "
                    "recomendação formal. A decisão de compra ou venda é exclusiva do "
                    "destinatário. Conteúdo confidencial, uso restrito ao destinatário "
                    "autorizado. © Aurinvest.</i>\n\n"
                    "🤖 Robot Aurinvest"
                )

                msg_mail = f"""
                <h2>🔔 Operação Encerrada — Scanner Fênix</h2>
                
                <b>Opção:</b> {symbol} ({op['tipo']})<br>
                <b>Strike:</b> {op['strike']}<br>
                <b>Vencimento:</b> {op['vencimento']}<br>
                <b>Motivo:</b> {motivo_saida}<br>
                <b>Retorno Final:</b> {retorno_pct:.1f}%<br>
                <b>Preço Entrada:</b> {preco_entrada}<br>
                <b>Preço Saída:</b> {preco_atual}<br>
                
                <br><hr>
                
                <p style="font-size:11px; color:#888;">
                COMPLIANCE: mensagem baseada em nossa carteira e não constitui recomendação formal.
                A decisão de compra ou venda é exclusiva do destinatário.
                Conteúdo confidencial, uso restrito ao destinatário autorizado. © Aurinvest.<br>
                🤖 Robot Aurinvest
                </p>
                """

                try:
                    enviar_telegram(msg_tel)
                    enviar_email("🔔 Operação encerrada — Scanner Phoenix", msg_mail)
                except Exception as e_notif:
                    print("Erro ao enviar notificações:", e_notif)

            else:
                # Mantém aberta — ATUALIZA SEMPRE COM PREÇO REAL (LAST)
                dados_update = {
                    "preco_atual": preco_atual,
                    "retorno_atual_pct": round(retorno_pct, 2),
                    "stop_protecao_pct": round(novo_stop, 2),
                    "updated_at": datetime.utcnow().isoformat()
                }
                _atualizar_operacao_supabase(op_id, dados_update)

        status.update(label="Checagem concluída.", state="complete")

    return len(ops), encerradas


# ============================================
# UI – BOTÃO CHECAR
# ============================================
st.markdown("##### ✅ Checar operações abertas (Scanner Fênix)")

if st.button("🔍 CHECAR OPERAÇÕES AGORA", type="secondary", use_container_width=True):
    total, fechadas = checar_operacoes_scanner()
    st.success(f"{total} operações avaliadas, {fechadas} encerradas.")


# ============================================
# 📊 DATAFRAMES DE OPERAÇÕES — Abertas & Encerradas
# ============================================

def carregar_df_operacoes(status: str) -> pd.DataFrame:
    """
    Carrega operações abertas ou encerradas do Supabase.
    """
    try:
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
                status
            """,
            "status": f"eq.{status}",
            "indice": "eq.OPCOES",
            "order": "created_at.desc",
        }

        resp = requests.get(REST_ENDPOINT, headers=HEADERS, params=params, timeout=20)
        resp.raise_for_status()

        df = pd.DataFrame(resp.json())

        if df.empty:
            return df

        # Conversões
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["updated_at"] = pd.to_datetime(df["updated_at"])
        df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
        df["preco_entrada"] = pd.to_numeric(df["preco_entrada"], errors="coerce")
        df["preco_atual"] = pd.to_numeric(df["preco_atual"], errors="coerce")
        df["preco_saida"] = pd.to_numeric(df["preco_saida"], errors="coerce")

        df["retorno_atual_pct"] = pd.to_numeric(df["retorno_atual_pct"], errors="coerce")
        df["retorno_final_pct"] = pd.to_numeric(df["retorno_final_pct"], errors="coerce")
        df["stop_protecao_pct"] = pd.to_numeric(df["stop_protecao_pct"], errors="coerce")

        # PnL monetário — se encerrada, usar preco_saida
        if status == "encerrada":
            df["pnl_reais"] = (df["preco_saida"] - df["preco_entrada"]).round(2)
        else:
            df["pnl_reais"] = (df["preco_atual"] - df["preco_entrada"]).round(2)

        return df

    except Exception as e:
        st.error(f"Erro ao carregar operações ({status}): {e}")
        return pd.DataFrame()


df_abertas = carregar_df_operacoes("aberta")
df_encerradas = carregar_df_operacoes("encerrada")


# ============================================
# 📘 EXPANDER — OPERAÇÕES ABERTAS

# ============================================

#st.markdown("## 📘 Operações Abertas — Scanner Fênix")

with st.expander("📘 Ver operações abertas", expanded=False):
    if df_abertas.empty:
        st.info("Nenhuma operação aberta.")
    else:
        st.dataframe(
            df_abertas[
                [
                    "symbol", "tipo", "underlying",
                    "strike", "vencimento",
                    "preco_entrada", "preco_atual",
                    "pnl_reais", "retorno_atual_pct",
                    "stop_protecao_pct",
                    "created_at", "updated_at"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


        # ===================================================
        # 🔵 RESUMO VISUAL — OPERAÇÕES ABERTAS (CARDS)
        # ===================================================
        st.markdown("### 🔍 Indicadores – Operações Abertas")

        df = df_abertas.copy()

        total_abertas = len(df)
        pnl_total = round(df["pnl_reais"].sum(), 2)
        retorno_medio = round(df["retorno_atual_pct"].mean(), 2)

        maior_ganho = df.loc[df["retorno_atual_pct"].idxmax()] if total_abertas > 0 else None
        maior_perda = df.loc[df["retorno_atual_pct"].idxmin()] if total_abertas > 0 else None

        # função de card visual
        def card_open(label, value, color="#00E676"):
            st.markdown(
                f"""
                <div style="
                    width: 100%;
                    height: 110px;
                    background-color:#11141A;
                    padding: 18px 20px;
                    border-radius:12px;
                    border:1px solid #222831;
                    display:flex;
                    flex-direction:column;
                    justify-content:center;
                ">
                    <div style="color:#9EA6B7; font-size:0.85rem; margin-bottom:6px;">
                        {label}
                    </div>
                    <div style="color:{color}; font-weight:700; font-size:1.6rem;">
                        {value}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # ----------- CARDS LINHA 1 -------------
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            card_open("Operações Abertas", total_abertas, "#00E676")

        with col2:
            card_open("PnL Total (R$)",
                      f"{pnl_total:.2f}",
                      "#00E676" if pnl_total >= 0 else "#FF5252")

        with col3:
            card_open("Retorno Médio (%)",
                      f"{retorno_medio:.2f}%",
                      "#00E676" if retorno_medio >= 0 else "#FF5252")

        with col4:
            if maior_ganho is not None:
                card_open("Maior Ganho (%)",
                          f"{maior_ganho['symbol']} {maior_ganho['retorno_atual_pct']:.2f}%",
                          "#00E676")

        # espaço entre linhas
        st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)

        # ----------- CARDS LINHA 2 -------------
        col5, col6, _, _ = st.columns(4)

        with col5:
            if maior_perda is not None:
                card_open("Maior Perda (%)",
                          f"{maior_perda['symbol']} {maior_perda['retorno_atual_pct']:.2f}%",
                          "#FF5252")

        # ===================================================
        # 📊 GRÁFICO DE RETORNOS DAS OPERAÇÕES ABERTAS
        # ===================================================
        st.markdown("### 📈 Gráfico – Retorno Atual das Operações")

        import plotly.graph_objects as go

        df_sorted = df.sort_values("retorno_atual_pct", ascending=False)
        colors = ["#00E676" if x >= 0 else "#FF5252" for x in df_sorted["retorno_atual_pct"]]

        fig = go.Figure([
            go.Bar(
                x=df_sorted["symbol"],
                y=df_sorted["retorno_atual_pct"],
                marker_color=colors,
                text=[f"{v:.2f}%" for v in df_sorted["retorno_atual_pct"]],
                textposition="outside"
            )
        ])

        fig.update_layout(
            template="plotly_dark",
            height=350,
            margin=dict(l=20, r=20, t=20, b=50),
            xaxis=dict(title="", tickangle=-40),
            yaxis=dict(title="Retorno (%)"),
            plot_bgcolor="#0E1117",
            paper_bgcolor="#0E1117",
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)



# ============================================
# 📕 EXPANDER — OPERAÇÕES ENCERRADAS
# ============================================
#st.markdown("#### 📕 Operações Encerradas — Scanner Fênix")

with st.expander("📕 Ver operações encerradas", expanded=False):
    if df_encerradas.empty:
        st.info("Nenhuma operação encerrada ainda.")
    else:
        st.dataframe(
            df_encerradas[
                [
                    "symbol","tipo","underlying",
                    "strike","vencimento",
                    "preco_entrada","preco_atual",
                    "pnl_reais","retorno_atual_pct",
                    "stop_protecao_pct",
                    "created_at","updated_at"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )



# ============================================
# 📊 RESUMO VISUAL — OPERAÇÕES ENCERRADAS (FÊNIX)
# ============================================

st.markdown("#### 🦅 Resumo de Desempenho")

if df_encerradas.empty:
    st.info("Nenhuma operação encerrada ainda.")
else:

    df = df_encerradas.copy()

    # Cálculos principais
    total_ops = len(df)
    total_lucro = round(df["retorno_final_pct"].sum(), 2)

    vencedoras = df[df["retorno_final_pct"] > 0]
    perdedoras = df[df["retorno_final_pct"] < 0]

    media_win = round(vencedoras["retorno_final_pct"].mean(), 2) if not vencedoras.empty else 0
    media_loss = round(perdedoras["retorno_final_pct"].mean(), 2) if not perdedoras.empty else 0

    maior_lucro = df.loc[df["retorno_final_pct"].idxmax()] if not df.empty else None
    maior_preju = df.loc[df["retorno_final_pct"].idxmin()] if not df.empty else None

    df["timestamp_saida"] = pd.to_datetime(df["timestamp_saida"], errors="coerce")
    df["dias"] = (df["timestamp_saida"] - df["created_at"]).dt.days
    df["dias"] = df["dias"].fillna(0).astype(int)
    media_dias = round(df["dias"].mean(), 2)


    media_dias = round(df["dias"].mean(), 2)

    winrate = round((len(vencedoras) / total_ops) * 100, 2) if total_ops > 0 else 0

    fluxo_cap = round(vencedoras["retorno_final_pct"].sum(), 2)

    # CARD COMPONENT
    def card(label, value, color="#00E676"):
        st.markdown(
            f"""
            <div style="
                width: 100%;
                height: 110px;
                background-color:#11141A;
                padding: 18px 20px;
                border-radius:12px;
                border:1px solid #222831;
                box-shadow:0 0 8px rgba(0,255,150,0.12);
                display:flex;
                flex-direction:column;
                justify-content:center;
            ">
                <div style="color:#9EA6B7; font-size:0.85rem; text-transform:uppercase; margin-bottom:6px;">
                    {label}
                </div>
                <div style="color:{color}; font-weight:700; font-size:1.6rem;">
                    {value}
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )


    # ROW 1
    st.markdown("##### 🔥 Indicadores")
    col1, col2, col3, col4 = st.columns(4)
    with col1: card("Lucro Total (%)", f"{total_lucro:.2f}%", "#00E676")
    with col2: card("Operações", f"{total_ops}", "#00E676")
    with col3: card("Winrate", f"{winrate:.1f}%", "#00E676")
    with col4: card("Média Dias", f"{media_dias}", "#00E676")

    # ESPAÇAMENTO BONITO
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

  

    # ROW 2
    col5, col6, col7, col8 = st.columns(4)
    with col5: card("Média Vencedoras", f"{media_win:.2f}%", "#00E676")
    with col6: card("Média Perdedoras", f"{media_loss:.2f}%", "#FF5252")
    with col7:
        if maior_lucro is not None:
            card("Maior Lucro", f"{maior_lucro['symbol']} {maior_lucro['retorno_final_pct']:.2f}%", "#00E676")
    with col8:
        if maior_preju is not None:
            card("Maior Prejuízo", f"{maior_preju['symbol']} {maior_preju['retorno_final_pct']:.2f}%", "#FF5252")

    st.markdown("---")


    # ============================================
    # 📈 GRÁFICO — BARRAS DE RESULTADOS
    # ============================================
    st.markdown("### ⭐ Gráfico dos Resultados (Operações Encerradas)")

    df_sorted = df.sort_values("retorno_final_pct", ascending=False)
    colors = ["#00E676" if x >= 0 else "#FF5252" for x in df_sorted["retorno_final_pct"]]

    fig = go.Figure([
        go.Bar(
            x=df_sorted["symbol"],
            y=df_sorted["retorno_final_pct"],
            marker_color=colors,
            text=[f"{v:.2f}%" for v in df_sorted["retorno_final_pct"]],
            textposition="outside"
        )
    ])

    fig.update_layout(
        template="plotly_dark",
        height=400,
        margin=dict(l=20, r=20, t=20, b=40),
        xaxis=dict(title="", tickangle=-40),
        yaxis=dict(title="Retorno (%)"),
        showlegend=False,
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font=dict(color="#FFFFFF")
    )

    st.plotly_chart(fig, use_container_width=True)





