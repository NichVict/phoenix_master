import streamlit as st
from supabase import create_client


# ============================
# FUNÇÃO QUE CRIA CLIENTE SÓ NA HORA
# ============================
def get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ============================
# LOGIN POR TOKEN
# ============================
def require_token():
    token = st.experimental_get_query_params().get("token", [None])[0]

    if not token:
        st.error("Você precisa acessar pelo link enviado por e-mail.")
        st.stop()

    supabase = get_client()  # <<< CLIENTE CRIADO NA HORA

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

    if nome_carteira not in user["carteiras"] and user["email"] not in ADMINS:
        st.error("🚫 Você não tem acesso a esta carteira.")
        st.stop()
