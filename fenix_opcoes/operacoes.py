from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple, Dict, Any


# ==========================================================
# DATACLASS PRINCIPAL – Representa uma operação de opção
# ==========================================================

@dataclass
class OperacaoOpcao:
    id: str
    symbol: str
    underlying: str
    tipo: str            # CALL / PUT
    strike: float
    vencimento: date

    lado_entrada: str    # COMPRA / VENDA
    preco_entrada: float

    # Estado dinâmico (atual)
    preco_atual: Optional[float] = None
    retorno_atual_pct: Optional[float] = None
    stop_protecao_pct: float = -25      # começa com -25%
    alvo_atual_pct: float = 0           # 0 / 25 / 50 / 75 / 100
    status: str = "aberta"              # aberta / encerrada

    # Saída
    lado_saida: Optional[str] = None
    preco_saida: Optional[float] = None
    timestamp_saida: Optional[str] = None
    retorno_final_pct: Optional[float] = None
    motivo_saida: Optional[str] = None


# ==========================================================
# CÁLCULO DE RETORNO % – COMPRA E VENDA
# ==========================================================

def calcular_retorno_pct(preco_atual: float, preco_entrada: float, lado_entrada: str) -> float:
    """
    Calcula o retorno em % ajustado pelo lado (COMPRA ou VENDA).
    """
    if preco_atual is None or preco_entrada <= 0:
        return 0.0

    if lado_entrada.upper() == "COMPRA":
        return (preco_atual / preco_entrada - 1.0) * 100.0

    if lado_entrada.upper() == "VENDA":
        return (preco_entrada / preco_atual - 1.0) * 100.0

    return 0.0


# ==========================================================
# ATUALIZAÇÃO DO STOP MÓVEL (MILESTONES)
# ==========================================================

def atualizar_stop_e_alvo(op: OperacaoOpcao, retorno_pct: float) -> None:
    """
    Atualiza o alvo atingido e o stop móvel da operação.
    """

    # Gatilhos de milestones – na ordem crescente
    if retorno_pct >= 100 and op.alvo_atual_pct < 100:
        op.alvo_atual_pct = 100
        op.stop_protecao_pct = 75
        return

    if retorno_pct >= 75 and op.alvo_atual_pct < 75:
        op.alvo_atual_pct = 75
        op.stop_protecao_pct = 50
        return

    if retorno_pct >= 50 and op.alvo_atual_pct < 50:
        op.alvo_atual_pct = 50
        op.stop_protecao_pct = 25
        return

    if retorno_pct >= 25 and op.alvo_atual_pct < 25:
        op.alvo_atual_pct = 25
        op.stop_protecao_pct = 5
        return


# ==========================================================
# DECISÃO DE ENCERRAMENTO
# ==========================================================

def decidir_encerramento(op: OperacaoOpcao, retorno_pct: float, hoje: date) -> Tuple[bool, Optional[str]]:
    """
    Retorna (encerrar, motivo_saida)
    """

    dias_para_venc = (op.vencimento - hoje).days

    # 1) Encerramento por D-3
    if dias_para_venc <= 3:
        return True, "d_menos_3"

    # 2) Stop inicial de -25% (se operação nunca pegou +25)
    if op.alvo_atual_pct == 0:
        if retorno_pct <= -25:
            return True, "stop_inicial"

    # 3) Stop móvel (ajustado pelas milestones)
    stop = op.stop_protecao_pct
    if retorno_pct <= stop:
        return True, "stop_protecao"

    return False, None


# ==========================================================
# PROCESSAMENTO COMPLETO DE UMA OPERAÇÃO
# ==========================================================

def processar_operacao(
    op: OperacaoOpcao,
    preco_atual: float,
    hoje: date
) -> Dict[str, Any]:
    """
    Executa TODA a lógica de processamento da operação:
    - calcula retorno
    - atualiza stop e milestone
    - decide encerramento
    """

    # 1) Cálculo de retorno
    retorno_pct = calcular_retorno_pct(
        preco_atual,
        op.preco_entrada,
        op.lado_entrada
    )

    op.preco_atual = preco_atual
    op.retorno_atual_pct = retorno_pct

    # 2) Atualizar stop móvel + alvo
    atualizar_stop_e_alvo(op, retorno_pct)

    # 3) Verificar encerramento
    encerrar, motivo = decidir_encerramento(op, retorno_pct, hoje)

    return {
        "operacao": op,
        "encerrar": encerrar,
        "motivo_saida": motivo,
        "retorno_pct": retorno_pct,
        "stop_pct": op.stop_protecao_pct,
        "alvo_pct": op.alvo_atual_pct,
    }


# ==========================================================
# LADO DE SAÍDA (sempre o oposto da entrada)
# ==========================================================

def definir_lado_saida(lado_entrada: str) -> str:
    if lado_entrada.upper() == "COMPRA":
        return "VENDA"
    if lado_entrada.upper() == "VENDA":
        return "COMPRA"
    return "VENDA"
