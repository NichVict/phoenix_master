from datetime import date
from typing import Dict, List, Any, Tuple

from fenix_opcoes.supabase_ops import (
    carregar_operacoes_abertas,
    atualizar_operacao,
    encerrar_operacao
)
from fenix_opcoes.operacoes import (
    processar_operacao,
    OperacaoOpcao
)

import requests
import os


# ==========================================================
# CONFIGURAÇÃO DA OPLAB
# ==========================================================

OPLAB_API_KEY = os.getenv("OPLAB_API_KEY", "")
OPLAB_BASE_URL = os.getenv("OPLAB_BASE_URL", "https://api.oplab.com.br/v3/")


def _headers():
    return {"Access-Token": OPLAB_API_KEY, "accept": "application/json"}


# ==========================================================
# BUSCAR PREÇO DA OPÇÃO NA OPLAB
# ==========================================================

def obter_preco_opcao(symbol: str) -> float:
    """
    Busca last/mid da opção (BID/ASK) via Oplab.
    Toma a decisão correta caso faltarem campos.
    """

    url = f"{OPLAB_BASE_URL}/market/options/{symbol}"

    try:
        r = requests.get(url, headers=_headers(), timeout=20)
        r.raise_for_status()
        data = r.json()

        if isinstance(data, list):
            d = data[0] if data else None
        else:
            d = data.get("data", [{}])[0]

        if not d:
            return None

        bid = d.get("bid")
        ask = d.get("ask")
        last = d.get("last")
        close = d.get("close")

        # Estratégia de fallback
        if last and last > 0:
            return last

        if bid and ask and bid > 0 and ask > 0:
            return (bid + ask) / 2

        if close and close > 0:
            return close

        return None

    except Exception:
        return None


# ==========================================================
# PROCESSAR TODAS AS OPERAÇÕES ABERTAS
# ==========================================================

def processar_todas_operacoes() -> List[Dict[str, Any]]:
    """
    - Carrega operações abertas
    - Busca preço atual
    - Processa lógica (stop, milestones, encerramento)
    - Atualiza banco
    - Encerra se necessário

    Retorna uma lista com o resultado de cada operação.
    """

    hoje = date.today()
    abertas: List[OperacaoOpcao] = carregar_operacoes_abertas()

    resultados: List[Dict[str, Any]] = []

    for op in abertas:

        preco_atual = obter_preco_opcao(op.symbol)

        if preco_atual is None:
            resultados.append({
                "id": op.id,
                "symbol": op.symbol,
                "erro": "Não foi possível obter preço da opção."
            })
            continue

        # Processamento central (stop, milestones, encerramento)
        r = processar_operacao(
            op=op,
            preco_atual=preco_atual,
            hoje=hoje
        )

        # Atualizar ou encerrar no Supabase
        if r["encerrar"]:
            encerrar_operacao(op, preco_atual, r["motivo_saida"])
        else:
            atualizar_operacao(op)

        resultados.append({
            "id": op.id,
            "symbol": op.symbol,
            "preco_atual": preco_atual,
            "retorno_pct": r["retorno_pct"],
            "stop_pct": r["stop_pct"],
            "alvo_pct": r["alvo_pct"],
            "encerrar": r["encerrar"],
            "motivo": r["motivo_saida"],
        })

    return resultados


# ==========================================================
# FUNÇÃO PARA O BOTÃO CHECAR (MONITORAMENTO COMPULSÓRIO)
# ==========================================================

def checar_manual() -> List[Dict[str, Any]]:
    """
    Exatamente igual ao monitoramento automático.
    Só muda que será chamado manualmente via botão.
    """
    return processar_todas_operacoes()


# ==========================================================
# FUNÇÕES DE MONITORAMENTO AUTOMÁTICO (3x ao dia)
# ==========================================================

def monitorar_1h():
    """Monitoramento realizado +1h após abertura."""
    return processar_todas_operacoes()


def monitorar_4h():
    """Monitoramento realizado +4h após abertura."""
    return processar_todas_operacoes()


def monitorar_final():
    """Monitoramento realizado -1h antes do fechamento."""
    return processar_todas_operacoes()
