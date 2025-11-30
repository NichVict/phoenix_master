# bp/core/trade_engine.py
# -*- coding: utf-8 -*-

"""
Engine de geração de setups do Projeto Fênix (MODELO C).

Função principal:
    generate_trade_setup(df, fs_score)

- df: DataFrame com candles + indicadores (inclui ATR real).
- fs_score: Fênix Strength (0 a 5).

Retorna:
    dict com:
        - operacao: "LONG" ou "SHORT"
        - entrada: preço de entrada (swing de resistência/suporte ou fallback)
        - stop: preço do stop loss
        - alvo: preço do take profit
        - stop_dist_atr: distância do stop em múltiplos de ATR
        - target_dist_atr: distância do alvo em múltiplos de ATR
        - rr: risco / retorno
"""

import numpy as np

# ============================================================
# 🔧 PARÂMETROS GERAIS
# ============================================================

MAX_LOOKBACK_SWINGS = 80  # máx. de candles para trás ao procurar o último swing
RR_MAX = 3.0              # risco/retorno máximo permitido (ex.: 3:1)

# ============================================================
# 🔍 DETECÇÃO DE SWING HIGH / SWING LOW (5 candles)
# ============================================================

def _find_last_swing_high(df, max_lookback: int = MAX_LOOKBACK_SWINGS, min_price: float | None = None):
    """
    Procura o último swing de resistência (Swing High clássico de 5 candles):

        High[i-2] < High[i-1] < High[i] > High[i+1] > High[i+2]

    Se min_price for informado, só aceita swings com High[i] >= min_price.

    Retorna:
        float(preço do swing) ou None se não encontrar.
    """
    if df is None or len(df) < 5:
        return None

    highs = df["High"].to_numpy(dtype="float64")
    n = len(highs)

    # índice i deve permitir i-2, i-1, i, i+1, i+2 → i ∈ [2, n-3]
    start = n - 3
    min_i = max(2, n - max_lookback - 1)

    for i in range(start, min_i - 1, -1):
        h_m2 = highs[i - 2]
        h_m1 = highs[i - 1]
        h_0  = highs[i]
        h_p1 = highs[i + 1]
        h_p2 = highs[i + 2]

        if h_m2 < h_m1 < h_0 > h_p1 > h_p2:
            if (min_price is None) or (h_0 >= min_price):
                return float(h_0)

    return None


def _find_last_swing_low(df, max_lookback: int = MAX_LOOKBACK_SWINGS, max_price: float | None = None):
    """
    Procura o último swing de suporte (Swing Low clássico de 5 candles):

        Low[i-2] > Low[i-1] > Low[i] < Low[i+1] < Low[i+2]

    Se max_price for informado, só aceita swings com Low[i] <= max_price.

    Retorna:
        float(preço do swing) ou None se não encontrar.
    """
    if df is None or len(df) < 5:
        return None

    lows = df["Low"].to_numpy(dtype="float64")
    n = len(lows)

    start = n - 3
    min_i = max(2, n - max_lookback - 1)

    for i in range(start, min_i - 1, -1):
        l_m2 = lows[i - 2]
        l_m1 = lows[i - 1]
        l_0  = lows[i]
        l_p1 = lows[i + 1]
        l_p2 = lows[i + 2]

        if l_m2 > l_m1 > l_0 < l_p1 < l_p2:
            if (max_price is None) or (l_0 <= max_price):
                return float(l_0)

    return None


# ============================================================
# ⚙️ MODELO C – Setup Profissional Adaptativo Fênix
# ============================================================

def generate_trade_setup(df, fs_score):
    """
    MODELO C — Setup Profissional Adaptativo Fênix

    Entradas:
        df        → dataframe completo com indicadores (inclui ATR real)
        fs_score  → Fênix Strength (0 a 5)

    Retorna:
        dict com operação, entrada, SL, TP, R/R e métricas auxiliares.
    """

    # -------------------------
    #  Verificações básicas
    # -------------------------
    if df is None or len(df) == 0:
        return None

    last = df.iloc[-1]

    # ===============================
    #  Captura de valores básicos
    # ===============================
    close     = float(last["Close"])
    high_last = float(last["High"])
    low_last  = float(last["Low"])

    # ATR REAL — não ATR%
    atr = float(last.get("ATR", 0.0))

    # Fallback seguro caso não haja ATR válido
    if atr <= 0:
        # 1,5% do preço como fallback (no mínimo 0,10)
        atr = max(abs(close) * 0.015, 0.10)

    # Tendência / Momentum normalizados (se existirem)
    tendencia_norm_candle = float(last.get("tendencia_norm", 0.5))
    momentum_norm_candle  = float(last.get("momentum_norm", 0.5))

    # ===============================
    #  Direção LONG / SHORT (profissional)
    # ===============================
    if tendencia_norm_candle >= 0.50 and momentum_norm_candle >= 0.50:
        operacao = "LONG"
    elif tendencia_norm_candle < 0.50 and momentum_norm_candle < 0.50:
        operacao = "SHORT"
    else:
        # Tendência e momentum discordam → sem operação válida
        return None

    # ===============================
    #  Fênix Strength normalizado (0–1)
    # ===============================
    fs_norm = float(fs_score) / 5.0 if fs_score is not None else 0.5
    fs_norm = max(0.0, min(fs_norm, 1.0))  # clamp defensivo

    # ===============================
    #  PREÇO DE ENTRADA (NOVO MODELO)
    # ===============================
    # LONG  → entrada = último Swing High (resistência) >= close
    # SHORT → entrada = último Swing Low  (suporte)    <= close
    #
    # Se NÃO houver swing recente (dentro de MAX_LOOKBACK_SWINGS),
    # fallback:
    #   LONG  → max(High último candle, Close)
    #   SHORT → min(Low  último candle, Close)

    if operacao == "LONG":
        entrada = _find_last_swing_high(df, min_price=close)
        if entrada is None:
            entrada = max(high_last, close)
    else:
        entrada = _find_last_swing_low(df, max_price=close)
        if entrada is None:
            entrada = min(low_last, close)

    entrada = float(entrada)

    # Trava de segurança adicional
    if operacao == "LONG" and entrada < close:
        entrada = close
    elif operacao == "SHORT" and entrada > close:
        entrada = close

    # ===============================
    #  Stop Loss Adaptativo (ATR)
    # ===============================
    # Fórmula MODELO C:
    #   StopDist = ATR * (1.2 + (1 - fs_norm) * 1.8)
    #
    # Intuição:
    #   - FS alto  → stop mais apertado (confiança maior)
    #   - FS baixo → stop mais largo (mercado mais "sujo")

    stop_mult = 1.2 + (1.0 - fs_norm) * 1.8
    stop_dist = atr * stop_mult

    if operacao == "LONG":
        stop = entrada - stop_dist
    else:
        stop = entrada + stop_dist

    # ===============================
    #  Take Profit Adaptativo (ATR)
    # ===============================
    # Fórmula MODELO C:
    #   TargetDist = ATR * (2 + FS_norm * 3)
    #
    # Intuição:
    #   - FS alto  → alvo bem mais longo (tendência forte)
    #   - FS baixo → alvo mais curto (mercado frágil)

    target_mult = 2.0 + fs_norm * 3.0
    target_dist = atr * target_mult

    # 🔒 Cap de Risco/Retorno máximo
    if stop_dist > 0:
        rr_teorico = target_dist / stop_dist
        if rr_teorico > RR_MAX:
            target_dist = stop_dist * RR_MAX

    if operacao == "LONG":
        target = entrada + target_dist
    else:
        target = entrada - target_dist

    # ===============================
    #  Risco x Retorno (R/R)
    # ===============================
    try:
        rr = abs(target - entrada) / max(abs(entrada - stop), 1e-8)
    except Exception:
        rr = np.nan

    # ===============================
    #  Retorno final
    # ===============================
    return {
        "operacao": operacao,          # "LONG" ou "SHORT"
        "entrada": entrada,            # preço de entrada (swing ou fallback)
        "stop": stop,                  # preço do stop
        "alvo": target,                # preço do alvo
        "stop_dist_atr": stop_dist / atr if atr else np.nan,
        "target_dist_atr": target_dist / atr if atr else np.nan,
        "rr": rr,                      # risco / retorno
        # Campos opcionais de debug se quiser:
        # "tendencia_norm_candle": tendencia_norm_candle,
        # "momentum_norm_candle": momentum_norm_candle,
        # "fs_norm": fs_norm,
    }
