import streamlit as st
from supabase import create_client


def get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ============================
# REQUIRE TOKEN OU ADMIN
# ============================
def require_token():
    # ---- ADMIN BYPASS ----
    bypass = st.secrets.get("ADMIN_BYPASS", "FALSE")
    admin_email = st.secrets.get("ADMIN_EMAIL", "")

    if bypass.upper() == "TRUE" and admin_email:
        st.session_state["user"] = {
            "id": "admin",
            "email": admin_email,
            "carteiras": [
                "Carteira de Ações IBOV",
                "Carteira de BDRs",
                "Carteira de Small Caps",
                "Carteira de Opções",
                "Dash Ações",
                "dashboard geral",
                "Scanner"
            ]
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

    st.session_state["user"] = {
        "id": user["id"],
        "email": user["email"],
        "carteiras": user.get("carteiras", []),
    }

    return st.session_state["user"]


# ============================
# PROTEÇÃO POR CARTEIRA
# ============================
def require_carteira(nome_carteira):
    user = st.session_state.get("user")

    if not user:
        st.error("Sessão expirada. Acesse novamente pelo link do e-mail.")
        st.stop()

    # Admin sempre libera tudo
    if user["email"] == st.secrets.get("ADMIN_EMAIL"):
        return True

    if nome_carteira not in user["carteiras"]:
        st.error("🚫 Você não tem acesso a esta carteira.")
        st.stop()
