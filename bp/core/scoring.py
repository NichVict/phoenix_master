# bp/core/scoring.py
# -*- coding: utf-8 -*-

def calculate_score(criteria_dict):
    """
    Calcula o score binário + o Fênix Strength (FS)
    com Volume valendo PESO 2.
    """

    score = 0
    passed = []
    failed = []

    # extrair norm de cada critério
    tendencia_norm     = criteria_dict["tendencia"]["norm"]
    momentum_norm      = criteria_dict["momentum"]["norm"]
    volatilidade_norm  = criteria_dict["volatilidade"]["norm"]
    sinal_norm         = criteria_dict["sinal_tecnico"]["norm"]
    volume_norm        = criteria_dict["volume"]["norm"]

    # score binário tradicional (0–5)
    for name, info in criteria_dict.items():
        if info["status"]:
            score += 1
            passed.append(name)
        else:
            failed.append(name)

    # 🔥 FS PESO 2 para volume
    fs = (
        tendencia_norm +
        momentum_norm +
        volatilidade_norm +
        sinal_norm +
        (2 * volume_norm)      # <<<<<< PESO 2
    )

    return {
        "score": score,
        "fs": fs,
        "passed": passed,
        "failed": failed,
        "tendencia_norm": tendencia_norm,
        "momentum_norm": momentum_norm,
        "volatilidade_norm": volatilidade_norm,
        "sinal_norm": sinal_norm,
        "volume_norm": volume_norm,
        "details": criteria_dict,
    }
