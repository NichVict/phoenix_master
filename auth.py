# auth.py
import os
from typing import Optional, Dict, Any, Set

import streamlit as st
from supabase import create_client, ClientOptions

# ============================================
# 🔧 FUNÇÃO AUXILIAR PARA LER VARIÁVEIS
# ============================================
def getenv(key: str) -> str:
    if key in os.environ and os.environ[key].strip() != "":
        return os.environ[key].strip()

    try:
        v = st.secrets.get(key, "")
        if v:
            return str(v).strip()
    except Exception:
        pass

    return ""


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
# 🔌 SUPABASE – CLIENTE PARA TABELA DE CLIENTES
# ============================================
SUPABASE_CLIENTES_TABLE = "clientes"

def get_supabase_client_clientes():
    url = getenv("supabase_url_clientes")
    key = getenv("supabase_key_clientes")

    if not url or not key:
        raise RuntimeError(
            "Erro: supabase_url_clientes ou supabase_key_clientes não encontrados."
        )

    options = ClientOptions().copy(update={"http2": False})
    return create_client(url, key, options=options)


# ============================================
# 🔍 BUSCA CLIENTE PELO TOKEN
# ============================================
def buscar_cliente_por_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Busca o cliente na tabela 'clientes' pelo token.
    Campo esperado:
        - token
        - nome
        - carteiras (string ou lista)
    """

    if not token:
        return None

    try:
        sb = get_supabase_client_clientes()
    except Exception as e:
        st.error(f"[AUTH] Erro ao conectar ao Supabase CLIENTES: {e}")
        return None

    try:
        # busca APENAS pelo token
        resp = (
            sb.table(SUPABASE_CLIENTES_TABLE)
            .select("*")
            .eq("token", token)
            .limit(1)
            .execute()
        )
    except Exception as e:
        st.error(f"[AUTH] Erro ao consultar token no Supabase: {e}")
        return None

    rows = getattr(resp, "data", None) or []
    if not rows:
        return None  # token não existe

    row = rows[0]

    # Extrair nome
    nome = row.get("nome") or "Cliente"

    # Extrair carteiras
    carteiras = row.get("carteiras", [])
    if isinstance(carteiras, str):
        # Aceita tanto "IBOV,BDR" quanto "['IBOV','BDR']"
        if "," in carteiras:
            carteiras = [c.strip() for c in carteiras.split(",")]
        elif carteiras.startswith("["):
            try:
                carteiras = eval(carteiras)
            except:
                carteiras = [carteiras]

    return {
        "nome": nome,
        "carteiras_crm": carteiras
    }




# ============================================
# 🔁 TRADUZ CARTEIRAS DO CRM → PAGE IDs INTERNAS
# ============================================
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

    # Dashboard Geral é sempre liberado para todos
    page_ids.add("dashboard_geral")

    return page_ids


# ============================================
# 🔐 CONTROLE DE SESSÃO
# ============================================
def login_user(cliente: Dict[str, Any]) -> None:
    page_ids = extrair_page_ids_do_cliente(cliente)

    st.session_state["logged"] = True
    st.session_state["cliente"] = {
        "email": cliente.get("email"),
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
