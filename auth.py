# auth.py
import os
from typing import Optional, Dict, Any, Set

import streamlit as st
import requests

# ============================================
# 🔧 LEITURA DAS VARIÁVEIS DO SUPABASE (CLIENTES)
# ============================================
SUPABASE_URL_CLIENTES = st.secrets["SUPABASE_URL_CLIENTES"]
SUPABASE_KEY_CLIENTES = st.secrets["SUPABASE_KEY_CLIENTES"]

CLIENTES_TABLE = "clientes"
CLIENTES_REST_URL = f"{SUPABASE_URL_CLIENTES}/rest/v1/{CLIENTES_TABLE}"

CLIENTES_HEADERS = {
    "apikey": SUPABASE_KEY_CLIENTES,
    "Authorization": f"Bearer {SUPABASE_KEY_CLIENTES}",
}


# ============================================
# 🔗 MAPEAMENTO CRM → PAGE IDs INTERNAS
# ============================================
CRM_TO_PAGE_IDS: Dict[str, list[str]] = {
    "Carteira de Ações IBOV": ["carteira_ibov"],
    "Carteira de BDRs": ["carteira_bdr"],
    "Carteira de Small Caps": ["carteira_small"],
    "Carteira de Opções": ["carteira_opcoes"],
}


# ============================================
# 🔍 BUSCA CLIENTE PELO TOKEN (REST OFICIAL)
# ============================================
def buscar_cliente_por_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Versão oficial — usa a API REST do Supabase, 100% compatível com o CRM.
    """

    if not token:
        return None

    query = f"?token=eq.{token}&select=*"
    url = CLIENTES_REST_URL + query

    try:
        resp = requests.get(url, headers=CLIENTES_HEADERS)
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    data = resp.json()
    if not data:
        return None

    row = data[0]

    # Normaliza o formato das carteiras (string, lista, etc.)
    carteiras_raw = row.get("carteiras", [])

    if isinstance(carteiras_raw, str):
        if "," in carteiras_raw:
            carteiras = [c.strip() for c in carteiras_raw.split(",")]
        else:
            carteiras = [carteiras_raw]
    elif isinstance(carteiras_raw, list):
        carteiras = carteiras_raw
    else:
        carteiras = []

    return {
        "nome": row.get("nome", "Cliente"),
        "carteiras_crm": carteiras,
    }


# ============================================
# 🔁 TRADUZ CARTEIRAS DO CRM → PAGE IDs INTERNAS
# ============================================
def extrair_page_ids_do_cliente(cliente: Dict[str, Any]) -> Set[str]:
    raw = cliente.get("carteiras_crm", [])

    carteiras_crm = []
    if isinstance(raw, list):
        carteiras_crm = raw
    elif isinstance(raw, str):
        carteiras_crm = [c.strip() for c in raw.split(",") if c.strip()]

    page_ids: Set[str] = set()

    for nome_crm in carteiras_crm:
        ids = CRM_TO_PAGE_IDS.get(nome_crm, [])
        for pid in ids:
            page_ids.add(pid)

    # Dashboard geral SEMPRE liberado
    page_ids.add("dashboard_geral")

    return page_ids


# ============================================
# 🔐 CONTROLE DE SESSÃO
# ============================================
def login_user(cliente: Dict[str, Any]) -> None:
    page_ids = extrair_page_ids_do_cliente(cliente)

    st.session_state["logged"] = True
    st.session_state["cliente"] = {
        "nome": cliente.get("nome", "Cliente"),
        "page_ids": list(page_ids),
    }


def logout_user() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def user_logged() -> bool:
    return bool(st.session_state.get("logged", False))


def get_session_user() -> Optional[Dict[str, Any]]:
    return st.session_state.get("cliente")


def user_has_access(page_id: str) -> bool:
    if page_id == "dashboard_geral":
        return True

    if not user_logged():
        return False

    cliente = st.session_state.get("cliente", {})
    page_ids = {p.lower() for p in cliente.get("page_ids", [])}

    return page_id.lower() in page_ids
