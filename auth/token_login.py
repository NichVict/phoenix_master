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
# REQUIRE TOKEN OU ADMIN BYPASS
# ============================
def require_token():

    # ---- ADMIN BYPASS ----
    bypass = str(st.secrets.get("ADMIN_BYPASS", "FALSE")).upper() == "TRUE"
    admin_email = st.secrets.get("ADMIN_EMAIL", "")

    if bypass and admin_email:
        st.session_state["user"] = {
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
        return st.session_state["user"]

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

    user = res.data
    if not user:
        st.error("Token inválido.")
        st.stop()

    user = user[0]

    # ======================================
    # CORREÇÃO: transformar carteiras em lista
    # ======================================
    carteiras_raw = user.get("carteiras", "[]")

    # Garantir que é sempre uma lista válida
    try:
        # Se vier como JSON string → converte
        if isinstance(carteiras_raw, str):
            carteiras = json.loads(carteiras_raw)
        # Se já vier como lista (menos comum) → usa direto
        elif isinstance(carteiras_raw, list):
            carteiras = carteiras_raw
        else:
            carteiras = []
    except:
        carteiras = []

    # ======================================

    st.session_state["user"] = {
        "id": user["id"],
        "email": user["email"],
        "carteiras": carteiras,
    }

    return st.session_state["user"]


# ============================
# REQUIRE CARTEIRA
# ============================
def require_carteira(nome_carteira):
    user = st.session_state.get("user")

    if not user:
        st.error("Sessão expirada. Acesse novamente pelo link do e-mail.")
        st.stop()

    # Admin vê tudo
    if user["email"] == st.secrets.get("ADMIN_EMAIL"):
        return True

    # Validação real: agora funciona corretamente
    if nome_carteira not in user["carteiras"]:
        st.error("🚫 Você não tem acesso a esta carteira.")
        st.stop()

    return True
