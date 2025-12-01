import streamlit as st
from supabase import create_client
import json

# ============================
# CLIENT DO SUPABASE
# ============================
def get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ============================
# LOGIN ADMINISTRADOR
# ============================
def admin_login():
    st.title("🔐 Login Administrador")

    user_input = st.text_input("Usuário")
    pwd_input = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        admin_user = st.secrets.get("ADMIN_LOGIN", "")
        admin_pass = st.secrets.get("ADMIN_PASSWORD", "")

        if user_input == admin_user and pwd_input == admin_pass:
            st.session_state["user"] = {
                "id": "admin",
                "email": st.secrets.get("ADMIN_EMAIL", ""),
                "carteiras": [
                    "Carteira de Ações IBOV",
                    "Carteira de BDRs",
                    "Carteira de Small Caps",
                    "Carteira de Opções",
                    "Scanner Fênix",
                    "Dashboard Geral",
                ],
            }
            st.success("Login realizado com sucesso!")
            st.experimental_rerun()
        else:
            st.error("Credenciais inválidas.")


# ============================
# LOGIN POR TOKEN (CLIENTE)
# ============================
def require_token():
    params = st.experimental_get_query_params()
    token = params.get("token", [None])[0]

    # ============================
    # SEM TOKEN → LOGIN ADMIN
    # ============================
    if not token:
        return admin_login()

    # ============================
    # LOGIN CLIENTE POR TOKEN
    # ============================
    supabase = get_client()

    res = (
        supabase.table("clientes")
        .select("*")
        .eq("token", token)
        .execute()
    )

    user = res.data
    if not user:
        st.error("Token inválido.")
        st.stop()

    user = user[0]

    # Conversão segura
    raw = user.get("carteiras", "[]")

    try:
        if isinstance(raw, str):
            carteiras = json.loads(raw)
        elif isinstance(raw, list):
            carteiras = raw
        else:
            carteiras = []
    except:
        carteiras = []

    # Salva usuário na sessão
    st.session_state["user"] = {
        "id": user["id"],
        "email": user["email"],
        "carteiras": carteiras,
    }

    return st.session_state["user"]


# ============================
# VERIFICAR SE O USUÁRIO EXISTE (PÁGINAS)
# ============================
def require_session_user():
    user = st.session_state.get("user")
    if not user:
        st.error("Sessão expirada. Volte para a página inicial.")
        st.stop()
    return user


# ============================
# PROTEÇÃO POR CARTEIRA
# ============================
def require_carteira(nome_carteira):
    user = require_session_user()

    # Admin sempre tem acesso
    if user["email"] == st.secrets.get("ADMIN_EMAIL"):
        return True

    if nome_carteira not in user["carteiras"]:
        st.error("🚫 Você não tem acesso a esta carteira.")
        st.stop()

    return True
