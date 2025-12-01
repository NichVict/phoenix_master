import streamlit as st
from supabase import create_client
import json

# ============================
# CLIENT DO SUPABASE (CLIENTES)
# ============================
def get_client():
    # tenta primeiro os CLIENTES, depois o padrão
    url = (
        st.secrets.get("SUPABASE_URL_CLIENTES")
        or st.secrets.get("SUPABASE_URL")
    )
    key = (
        st.secrets.get("SUPABASE_KEY_CLIENTES")
        or st.secrets.get("SUPABASE_KEY")
    )

    if not url or not key:
        st.error("Configuração do Supabase ausente. Verifique SUPABASE_URL_CLIENTES / SUPABASE_KEY_CLIENTES.")
        st.stop()

    return create_client(url, key)


# ============================
# LOGIN POR TOKEN (CLIENTE / ADMIN)
# ============================
def require_token():
    # 🔧 BYPASS só pra manutenção (DEIXE FALSE pra testar cliente)
    bypass = str(st.secrets.get("ADMIN_BYPASS", "FALSE")).upper() == "TRUE"
    admin_email = st.secrets.get("ADMIN_EMAIL", "")

    if bypass and admin_email:
        user = {
            "id": "admin",
            "email": admin_email,
            "carteiras": [
                "Carteira de Ações IBOV",
                "Carteira de BDRs",
                "Carteira de Small Caps",
                "Carteira de Opções",
                "Scanner Fênix",
                "Dashboard Geral",
            ],
        }
        st.session_state["user"] = user
        return user

    # ---- TOKEN NORMAL ----
    token = st.experimental_get_query_params().get("token", [None])[0]

    if not token:
        st.error("Você precisa acessar pelo link enviado por e-mail.")
        st.stop()

    supabase = get_client()

    res = (
        supabase.table("clientes")
        .select("*")
        .eq("token", token)
        .execute()
    )

    data = res.data
    if not data:
        st.error("Token inválido.")
        st.stop()

    user = data[0]

    # ======================================
    # CORREÇÃO: transformar carteiras em lista
    # ======================================
    raw = user.get("carteiras", "[]")

    try:
        if isinstance(raw, str):
            carteiras = json.loads(raw)
        elif isinstance(raw, list):
            carteiras = raw
        else:
            carteiras = []
    except Exception:
        carteiras = []

    st_user = {
        "id": user["id"],
        "email": user["email"],
        "carteiras": carteiras,
    }

    st.session_state["user"] = st_user
    return st_user


# ============================
# GARANTE QUE HÁ USUÁRIO NA SESSÃO
# ============================
def require_session_user():
    user = st.session_state.get("user")
    if not user:
        st.error("Sessão expirada. Acesse novamente pelo link do e-mail.")
        st.stop()
    return user


# ============================
# REQUIRE CARTEIRA ESPECÍFICA
# ============================
def require_carteira(nome_carteira):
    user = require_session_user()
    admin_email = st.secrets.get("ADMIN_EMAIL", "")

    # Admin vê tudo
    if admin_email and user["email"] == admin_email:
        return True

    if nome_carteira not in user.get("carteiras", []):
        st.error("🚫 Você não tem acesso a esta carteira.")
        st.stop()

    return True
