import streamlit as st
from supabase import create_client
import os

# ============================
# CONFIG
# ============================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================
# LOGIN POR TOKEN
# ============================
def require_token():
    token = st.experimental_get_query_params().get("token", [None])[0]

    if not token:
        st.error("Você precisa acessar através do link enviado por e-mail.")
        st.stop()

    user = (
        supabase.table("clientes")
        .select("*")
        .eq("token", token)
        .execute()
    ).data

    if not user:
        st.error("Token inválido. Solicite um novo link de acesso.")
        st.stop()

    user = user[0]  # registro único

    # salvar sessão
    st.session_state["user"] = {
        "id": user["id"],
        "email": user["email"],
        "carteiras": user.get("carteiras", []),
    }

    return st.session_state["user"]

# ============================
# PROTEÇÃO POR CARTEIRA
# ============================
def require_carteira(nome_carteira: str):
    user = st.session_state.get("user", None)

    if not user:
        st.error("Sessão expirada. Acesse novamente pelo link enviado por e-mail.")
        st.stop()

    if nome_carteira not in user["carteiras"]:
        st.error("🚫 Você não tem acesso a esta carteira.")
        st.stop()
