import pandas as pd
import numpy as np

def force_1d(series):
    """
    Converte qualquer coluna para uma Series 1D REAL.
    Remove listas, tuplas, arrays, DataFrames e dtype object.
    """
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]

    cleaned = []
    for x in series:
        if isinstance(x, (list, tuple, np.ndarray)):
            cleaned.append(x[0] if len(x) > 0 else np.nan)
        else:
            cleaned.append(x)

    cleaned = pd.to_numeric(cleaned, errors="coerce")
    return pd.Series(cleaned, index=series.index)



def normalize_ohlcv(df):
    """
    Normalize OHLCV garantindo 100% que todas as colunas sejam Series 1D válidas.
    """
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = force_1d(df[col])

    return df




# ------------------------------------------------------------
# MÉDIAS MÓVEIS
# ------------------------------------------------------------
def calc_ma(df, period):
    """
    Calcula média móvel simples (SMA).
    """
    df[f"MA{period}"] = df["Close"].rolling(window=period).mean()
    return df


# ------------------------------------------------------------
# VWAP
# ------------------------------------------------------------
def calc_vwap(df):
    high = force_1d(df["High"])
    low = force_1d(df["Low"])
    close = force_1d(df["Close"])
    volume = force_1d(df["Volume"])

    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()

    df["VWAP"] = vwap
    return df



# ------------------------------------------------------------
# IFR / RSI
# ------------------------------------------------------------
def calc_rsi(df, period=14):
    """
    IFR (RSI) robusto, compatível com Streamlit Cloud e dados incompletos.
    Usa cálculos 100% baseados em pandas para evitar arrays 2D.
    """
    if df is None or df.empty:
        df["RSI14"] = np.nan
        return df

    delta = df["Close"].diff()

    # Ganho = valores positivos, Perda = negativos convertidos
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # Médias móveis simples (Wilder smoothing pode ser opção depois)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))
    df[f"RSI{period}"] = rsi

    return df



# ------------------------------------------------------------
# OBV – On Balance Volume
# ------------------------------------------------------------
def calc_obv(df):
    """
    OBV blindado para o Streamlit Cloud.
    Converte tudo para Series 1D, evita DataFrames 2D,
    e elimina qualquer ambiguidade na comparação.
    """

    if df is None or df.empty:
        df["OBV"] = np.nan
        return df

    # Garantia absoluta de que são Series 1D
    close = pd.Series(df["Close"].values.flatten(), index=df.index)
    volume = pd.Series(df["Volume"].values.flatten(), index=df.index)

    # Diferença do fechamento
    diff = close.diff()

    # Direção: 1, -1, 0
    direction = diff.apply(
        lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
    )

    obv = (direction * volume).cumsum()

    df["OBV"] = obv
    return df


# ------------------------------------------------------------
# AD LINE – Acumulação / Distribuição
# ------------------------------------------------------------
def calc_ad_line(df):
    if df is None or df.empty:
        df["AD"] = np.nan
        return df

    high = force_1d(df["High"])
    low = force_1d(df["Low"])
    close = force_1d(df["Close"])
    volume = force_1d(df["Volume"])

    spread = (high - low).replace(0, np.nan)
    clv = ((close - low) - (high - close)) / spread
    clv = clv.fillna(0)

    ad_line = (clv * volume).cumsum()
    df["AD"] = ad_line

    return df




# ------------------------------------------------------------
# ATR%
# ------------------------------------------------------------
def calc_atr_pct(df, period=14):

    # Blindagem total das colunas
    high = force_1d(df["High"])
    low = force_1d(df["Low"])
    close = force_1d(df["Close"])

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    df["ATR"] = atr
    df["ATR_pct"] = (atr / close) * 100

    return df




# ------------------------------------------------------------
# VOLUME MM14
# ------------------------------------------------------------
def calc_volume_mm14(df):
    volume = force_1d(df["Volume"])
    df["Volume_MM14"] = volume.rolling(window=14).mean()
    return df



# ------------------------------------------------------------
# DESVIO RELATIVO DO VOLUME vs MM14
# ------------------------------------------------------------
def calc_volume_deviation(df):
    """
    Calcula a diferença percentual do volume atual vs MM14.
    Blindado contra colunas 2D.
    """

    volume = force_1d(df["Volume"])
    mm14 = force_1d(df["Volume_MM14"])

    df["Volume_deviation"] = ((volume - mm14) / mm14) * 100
    return df



# ------------------------------------------------------------
# PIPELINE PRINCIPAL
# ------------------------------------------------------------
def apply_all_indicators(df):
    """
    Aplica todos os indicadores necessários para o BP-Fênix,
    com blindagem total contra dados 2D ou corrompidos do yfinance.
    Agora com:
    - indicadores calculados NO DATAFRAME COMPLETO
    - corte tail(20) somente no final
    - blindagem reforçada
    """

    # -----------------------------------------
    # BLINDAGEM INICIAL
    # -----------------------------------------
    if df is None or len(df) == 0:
        return pd.DataFrame()

    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    for col in required_columns:
        if col not in df.columns:
            return pd.DataFrame()

    # Normalização primária
    df = normalize_ohlcv(df)

    # =========================================
    # 🔥 INDICADORES NO DF COMPLETO
    # =========================================

    # ---------------------------
    # TENDÊNCIA
    # ---------------------------
    df = calc_ma(df, 9)
    df = calc_ma(df, 21)
    df = calc_ma(df, 50)      # ← adicionado
    df = calc_ma(df, 200)

    # ---------------------------
    # MOMENTUM
    # ---------------------------
    df = calc_rsi(df)
    df = calc_obv(df)
    df = calc_ad_line(df)

    # ---------------------------
    # VOLATILIDADE
    # ---------------------------
    df = calc_atr_pct(df)

    # ---------------------------
    # VOLUME
    # ---------------------------
    df = calc_volume_mm14(df)
    df = calc_volume_deviation(df)

    # ---------------------------
    # VWAP
    # ---------------------------
    df = calc_vwap(df)

    # =========================================
    # 🔥 BLINDAGEM FINAL
    # =========================================

    # Converter TODAS as colunas para Series 1D
    for col in df.columns:
        df[col] = force_1d(df[col])

    # Blindagem final do fechamento
    close = force_1d(df["Close"])

    # Se todos NaN, não presta
    if close.isna().all():
        return pd.DataFrame()

    df["Close"] = close

    # Limpar infinitos
    df = df.replace([np.inf, -np.inf], np.nan)

    # Remover linhas sem fechamento
    df = df[df["Close"].notna()]

    # =========================================
    # 🔥 SÓ AGORA cortamos para as últimas 20
    # =========================================
    df = df.tail(20)

    if len(df) == 0:
        return pd.DataFrame()

    return df




    




