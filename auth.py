# auth.py
import os
from typing import Optional, Dict, Any, Set

import streamlit as st
import requests


# =========================================================
# 🔧 FUNÇÃO AUXILIAR PARA LER VARIÁVEIS (Render + Local)
# =========================================================
def getenv(key: str) -> str:
    """Lê variáveis do ambiente OU secrets, se existirem."""
    # Render → sempre usa variáveis de ambiente
    if key in os.environ and os.environ[key].strip() != "":
        return os.environ[key].strip()

    # Localhost → fallback opcional
    try:
        v = st.secrets.get(key, "")
        if v:
            return str(v).strip()
    except Exception:
        pass

    return ""


# =========================================================
# 🔗 MAPEAMENTO DO CRM → PAGE IDs INTERNAS
# =========================================================
CRM_TO_PAGE_IDS: Dict[str, list[str]] = {
    "Carteira de Ações IBOV": ["carteira_ibov"],
    "Carteira de BDRs": ["carteira_bdr"],
    "Carteira de Small Caps": ["carteira_small"],
    "Carteira de Opções": ["carteira_opcoes"],
}


# =========================================================
# 📌 SUPABASE (CLIENTES)
# =========================================================
SUPABASE_URL_CLIENTES = getenv("SUPABASE_URL_CLIENTES")
SUPABASE_KEY_CLIENTES = getenv("SUPABASE_KEY_CLIENTES")

CLIENTES_TABLE = "clientes"

REST_URL_CLIENTES = f"{SUPABASE_URL_CLIENTES}/rest/v1/{CLIENTES_TABLE}"

HEADERS_CLIENTES = {
    "apikey": SUPABASE_KEY_CLIENTES,
    "Authorization": f"Bearer {SUPABASE_KEY_CLIENTES}",
}


# =========================================================
# 🔍 BUSCA O CLIENTE PELO TOKEN
# =========================================================
def buscar_cliente_por_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None

    query = f"?token=eq.{token}&select=*"
    url = REST_URL_CLIENTES + query

    resp = requests.get(url, headers=HEADERS_CLIENTES)

    if resp.status_code != 200:
        return None

    data = resp.json()
    if not data:
        return None

    row = data[0]

    return {
        "nome": row.get("nome", "Cliente"),
        "carteiras_crm": row.get("carteiras", []),
    }


# =========================================================
# 🔁 CONVERTE CARTEIRAS DO CRM → PAGE IDs INTERNAS
# =========================================================
def extrair_page_ids_do_cliente(cliente: Dict[str, Any]) -> Set[str]:
    raw = cliente.get("carteiras_crm") or ""

    if isinstance(raw, str):
        carteiras_crm = [c.strip() for c in raw.split(",") if c.strip()]
    elif isinstance(raw, list):
        carteiras_crm = raw
    else:
        carteiras_crm = []

    page_ids: Set[str] = set()

    for nome_crm in carteiras_crm:
        ids = CRM_TO_PAGE_IDS.get(nome_crm, [])
        for pid in ids:
            page_ids.add(pid)

    # Dashboard Geral sempre liberado
    page_ids.add("dashboard_geral")

    return page_ids


# =========================================================
# 🔐 CONTROLE DE SESSÃO
# =========================================================
def login_user(cliente: Dict[str, Any]) -> None:
    page_ids = extrair_page_ids_do_cliente(cliente)

    st.session_state["logged"] = True
    st.session_state["cliente"] = {
        "nome": cliente.get("nome"),
        "page_ids": list(page_ids),
    }


def logout_user() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def user_logged() -> bool:
    return bool(st.session_state.get("logged", False))


def user_has_access(page_id: str) -> bool:
    if page_id == "dashboard_geral":
        return True

    if not user_logged():
        return False

    cliente = st.session_state.get("cliente") or {}
    page_ids = {p.lower() for p in cliente.get("page_ids", [])}

    return page_id.lower() in page_ids
