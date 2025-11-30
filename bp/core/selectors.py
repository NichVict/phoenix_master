# bp/core/selectors.py
# -*- coding: utf-8 -*-

from bp.core.trade_engine import generate_trade_setup

def select_top_assets(results, score_min=3, top_n=5):
    """
    Seleciona os melhores ativos usando o FS (com Volume PESO 2)
    e gera o Setup Operacional (Modelo C).
    """

    scored_assets = []

    for ticker, info in results.items():

        # filtro por score binário mínimo
        if info.get("score", 0) < score_min:
            continue

        details = info.get("details", {})
        if not details:
            continue

        df = details.get("df")
        if df is None or df.empty:
            continue

        # Norms individuais
        n_tend = details["tendencia"]["norm"]
        n_mom  = details["momentum"]["norm"]
        n_vol  = details["volatilidade"]["norm"]
        n_sig  = details["sinal_tecnico"]["norm"]
        n_volu = details["volume"]["norm"]

        # 🔥 FS já vem do SCORING (com Volume PESO 2)
        fs = info.get("fs", 0)

        # Monta setup operacional
        trade_setup = generate_trade_setup(df, fs)
        if trade_setup is None:
            continue

        scored_assets.append({
            "ticker": ticker,
            "score": info["score"],
            "fs": fs,
            "tendencia_norm": n_tend,
            "momentum_norm": n_mom,
            "volatilidade_norm": n_vol,
            "sinal_norm": n_sig,
            "volume_norm": n_volu,
            "details": details,
            "trade": trade_setup,
        })

    # Ranking final oficial
    scored_assets.sort(
        key=lambda x: (
            -x["fs"],
            -x["momentum_norm"],
            -x["tendencia_norm"],
            -x["volume_norm"],
        )
    )

    return scored_assets[:top_n]
