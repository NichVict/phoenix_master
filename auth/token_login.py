import streamlit as st
import pandas as pd
from supabase import create_client


SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_client_by_token(token: str):
    try:
        res = (
            supabase.table("clientes")
            .select("*")
            .eq("token", token)
            .execute()
        )
        if res.data:
            return res.data[0]
        return None

    except Exception as e:
        st.error(f"Erro ao validar token: {e}")
        return None


def authenticate_from_token():
    query_params = st.query_params

    if "token" not in query_params:
        return False

    token = query_params["token"]

    # sessão já válida
    if "usuario" in st.session_state and st.session_state.usuario.get("token") == token:
        return True

    cliente = get_client_by_token(token)

    if not cliente:
        st.error("❌ Token inválido.")
        st.stop()

    carteiras = cliente.get("carteiras", [])
    if isinstance(carteiras, str):
        carteiras = [
            c.strip().strip("'").strip('"')
            for c in carteiras.strip("[]").split(",")
            if c.strip()
        ]

    data_inicio = pd.to_datetime(cliente["data_inicio"]).date()
    data_fim = pd.to_datetime(cliente["data_fim"]).date()

    st.session_state.usuario = {
        "id": cliente["id"],
        "nome": cliente["nome"],
        "email": cliente["email"],
        "token": token,
        "carteiras": carteiras,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    }

    return True


def require_token():
    ok = authenticate_from_token()

    if not ok:
        st.error("Você precisa acessar pelo link enviado no e-mail.")
        st.stop()

    return True
