import numpy as np

VOLUME_TOLERANCIA = 0.02  # 2% abaixo da MM14 permitido


# ------------------------------------------------------------
# HELPER — conversão segura
# ------------------------------------------------------------
def to_float(x):
    try:
        return float(x)
    except:
        return np.nan


# ------------------------------------------------------------
# NORMALIZAÇÃO INSTITUCIONAL DO VOLUME
# ------------------------------------------------------------
def normalize_volume(vol, mm14):
    """
    Normalização:
    - 2x MM14 => 1.00
    - 1x MM14 => 0.70
    - 0.5x MM14 => 0.35
    - 0.25x MM14 => 0.00
    """
    if mm14 <= 0:
        return 0.1  # nunca zero

    ratio = vol / mm14

    if ratio >= 2:
        return 1.0

    norm = (ratio - 0.25) / (2 - 0.25)

    return float(max(0.10, min(norm, 1.0)))  # garante piso 0.10


# ------------------------------------------------------------
# CRITÉRIO 1 — TENDÊNCIA
# ------------------------------------------------------------
def check_trend(df):
    if df is None or len(df) == 0:
        return False, "Dados insuficientes", 0.10

    last = df.iloc[-1]

    close = to_float(last["Close"])
    ma9   = to_float(last["MA9"])
    ma21  = to_float(last["MA21"])
    ma200 = to_float(last["MA200"])

    if any(np.isnan(v) for v in [close, ma9, ma21, ma200]):
        return False, "Valores inválidos para tendência", 0.10

    cond1 = close > ma9
    cond2 = close > ma21
    cond3 = close > ma200
    status = cond1 and cond2 and cond3

    # tendência norm = distância relativa para a MA200
    try:
        norm = (close - ma200) / ma200
        norm = float(max(0.10, min(norm, 1.0)))
    except:
        norm = 0.10

    detail = f"Close={close:.2f}, MA9={ma9:.2f}, MA21={ma21:.2f}, MA200={ma200:.2f}"

    return status, detail, norm


# ------------------------------------------------------------
# CRITÉRIO 2 — MOMENTUM
# ------------------------------------------------------------
def check_momentum(df):
    if len(df) < 6:
        return False, "Dados insuficientes", 0.10

    last = df.iloc[-1]
    rsi  = to_float(last["RSI14"])

    if np.isnan(rsi):
        return False, "RSI inválido", 0.10

    obv_up = df["OBV"].diff().tail(5).sum() > 0
    ad_up  = df["AD"].diff().tail(5).sum()  > 0

    cond1 = rsi > 50
    cond2 = obv_up
    cond3 = ad_up

    status = cond1 and cond2 and cond3

    # normalização do RSI (faixa 30–100)
    norm = (rsi - 30) / 70
    norm = float(max(0.10, min(norm, 1.0)))

    detail = f"RSI14={rsi:.2f} | OBV_up={obv_up} | AD_up={ad_up}"

    return status, detail, norm


# ------------------------------------------------------------
# CRITÉRIO 3 — VOLATILIDADE (SEM ZERO)
# ------------------------------------------------------------
def check_volatility(df):
    last = df.iloc[-1]

    atr_pct = to_float(last["ATR_pct"])
    if np.isnan(atr_pct):
        return False, "ATR% inválido", 0.10

    # critério binário continua igual
    status = atr_pct <= 6

    # normalização com teto realista (25%) + piso 0.10
    max_atr = 25
    norm_raw = 1 - (atr_pct / max_atr)

    norm = float(max(0.10, min(norm_raw, 1.0)))

    detail = f"ATR%={atr_pct:.2f}"

    return status, detail, norm


# ------------------------------------------------------------
# CRITÉRIO 4 — SINAL TÉCNICO
# ------------------------------------------------------------
def check_technical_signal(df):
    last = df.iloc[-1]

    close = to_float(last["Close"])
    ma9   = to_float(last["MA9"])
    vwap  = to_float(last["VWAP"])

    if any(np.isnan(v) for v in [close, ma9, vwap]):
        return False, "Valores inválidos para sinal técnico", 0.10

    cond1 = close > ma9
    cond2 = close > vwap
    status = cond1 and cond2

    # normalização pela distância do VWAP
    try:
        diff = close - vwap
        norm = diff / vwap
        norm = float(max(0.10, min(norm, 1.0)))
    except:
        norm = 0.10

    detail = f"Close={close:.2f} | MA9={ma9:.2f} | VWAP={vwap:.2f}"

    return status, detail, norm


# ------------------------------------------------------------
# CRITÉRIO 5 — VOLUME
# ------------------------------------------------------------
def check_volume(df):
    last = df.iloc[-1]

    vol  = to_float(last["Volume"])
    mm14 = to_float(last["Volume_MM14"])

    if np.isnan(vol) or np.isnan(mm14) or mm14 == 0:
        return False, "MM14 inválida", 0.10

    deviation = (vol - mm14) / mm14

    status = deviation >= -VOLUME_TOLERANCIA

    norm = normalize_volume(vol, mm14)

    detail = f"Volume={vol:.0f} | MM14={mm14:.0f} | Dev={deviation*100:.2f}%"

    return status, detail, norm


# ------------------------------------------------------------
# FUNÇÃO PRINCIPAL
# ------------------------------------------------------------
def evaluate_all_criteria(df):
    c1, d1, n1 = check_trend(df)
    c2, d2, n2 = check_momentum(df)
    c3, d3, n3 = check_volatility(df)
    c4, d4, n4 = check_technical_signal(df)
    c5, d5, n5 = check_volume(df)

    return {
        "tendencia":     {"status": c1, "detail": d1, "norm": n1},
        "momentum":      {"status": c2, "detail": d2, "norm": n2},
        "volatilidade":  {"status": c3, "detail": d3, "norm": n3},
        "sinal_tecnico": {"status": c4, "detail": d4, "norm": n4},
        "volume":        {"status": c5, "detail": d5, "norm": n5},
    }