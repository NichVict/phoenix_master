import requests
from datetime import datetime
from typing import Dict, Any, List

from fenix_opcoes.operacoes import OperacaoOpcao, definir_lado_saida


# ==========================================================
# CONFIGURAÇÃO DO SUPABASE (REST API)
# ==========================================================

SUPABASE_URL = "https://kflwifvrkcqmrzgpvhqe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmbHdpZnZya2NxbXJ6Z3B2aHFlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MDA5NTU0NywiZXhwIjoyMDc1NjcxNTQ3fQ.U0x6Jh1Cd1ksVRfUP8rokmZcbHh3YRZ67YXFsQmv_g4"

REST_ENDPOINT = f"{SUPABASE_URL}/rest/v1/opcoes_operacoes"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


# ==========================================================
# CONVERSOR DE LINHA → OBJETO
# ==========================================================

def _row_to_operacao(row: Dict[str, Any]) -> OperacaoOpcao:
    return OperacaoOpcao(
        id=row["id"],
        symbol=row["symbol"],
        underlying=row["underlying"],
        tipo=row["tipo"],
        strike=row["strike"],
        vencimento=row["vencimento"],
        lado_entrada=row["lado_entrada"],
        preco_entrada=row["preco_entrada"],

        preco_atual=row.get("preco_atual"),
        retorno_atual_pct=row.get("retorno_atual_pct"),
        stop_protecao_pct=row.get("stop_protecao_pct", -25),
        alvo_atual_pct=row.get("alvo_atual_pct", 0),
        status=row.get("status", "aberta"),

        lado_saida=row.get("lado_saida"),
        preco_saida=row.get("preco_saida"),
        timestamp_saida=row.get("timestamp_saida"),
        retorno_final_pct=row.get("retorno_final_pct"),
        motivo_saida=row.get("motivo_saida"),
    )


# ==========================================================
# CARREGAR OPERAÇÕES ABERTAS (GET)
# ==========================================================

def carregar_operacoes_abertas() -> List[OperacaoOpcao]:
    params = {"status": "eq.aberta"}

    resp = requests.get(REST_ENDPOINT, headers=HEADERS, params=params).json()

    if not resp:
        return []

    return [_row_to_operacao(row) for row in resp]


# ==========================================================
# INSERIR NOVA OPERAÇÃO (POST)
# ==========================================================

def inserir_operacao(data: Dict[str, Any]) -> str:
    import json

    # Garantir header correto
    headers = HEADERS.copy()
    headers["Prefer"] = "return=representation"

    resp = requests.post(REST_ENDPOINT, headers=headers, json=data)

    # DEBUG
    print("==== SUPABASE DEBUG (INSERT) ====")
    print("STATUS:", resp.status_code)
    print("BODY:", resp.text)

    # caso erro HTTP, explode aqui
    resp.raise_for_status()

    # Algumas respostas podem vir vazias mesmo com 201
    if not resp.text.strip():
        raise ValueError("Supabase retornou corpo vazio (verifique políticas RLS).")

    dados = resp.json()

    # Espera retorno como array
    if isinstance(dados, list) and len(dados) > 0 and "id" in dados[0]:
        return dados[0]["id"]

    raise ValueError(f"Resposta inesperada do Supabase: {dados}")




# ==========================================================
# ATUALIZAR OPERAÇÃO (PATCH)
# ==========================================================

def atualizar_operacao(op: OperacaoOpcao) -> None:
    update_data = {
        "preco_atual": op.preco_atual,
        "retorno_atual_pct": op.retorno_atual_pct,
        "stop_protecao_pct": op.stop_protecao_pct,
        "alvo_atual_pct": op.alvo_atual_pct,
        "updated_at": datetime.utcnow().isoformat()
    }

    url = f"{REST_ENDPOINT}?id=eq.{op.id}"
    requests.patch(url, headers=HEADERS, json=update_data)


# ==========================================================
# ENCERRAR OPERAÇÃO (PATCH)
# ==========================================================

def encerrar_operacao(op: OperacaoOpcao, preco_saida: float, motivo: str) -> None:
    lado_saida = definir_lado_saida(op.lado_entrada)

    if op.lado_entrada.upper() == "COMPRA":
        retorno_final = (preco_saida / op.preco_entrada - 1) * 100
    else:
        retorno_final = (op.preco_entrada / preco_saida - 1) * 100

    update_data = {
        "status": "encerrada",
        "preco_saida": preco_saida,
        "lado_saida": lado_saida,
        "timestamp_saida": datetime.utcnow().isoformat(),
        "retorno_final_pct": retorno_final,
        "motivo_saida": motivo,
    }

    url = f"{REST_ENDPOINT}?id=eq.{op.id}"
    requests.patch(url, headers=HEADERS, json=update_data)
