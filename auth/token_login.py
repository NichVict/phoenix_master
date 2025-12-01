import streamlit as st
import pandas as pd
from supabase import create_client


# ------------------------------------------------------
# Carregar credenciais do Fênix
# ------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ------------------------------------------------------
# 1) Função para buscar cliente pelo token
# ------------------------------------------------------
def get_client_by_token(token: str):
    try:
        res = (
            supabase.table("clientes")
            .select("*")
            .eq("token", token)
            .execute()
        )

        if res.data and len(res.data) > 0:
            return res.data[0]

        return None

    except Exception as e:
        st.error(f"Erro ao validar token: {e}")
        return None


# ------------------------------------------------------
# 2) Processar token da URL e criar sessão
# ------------------------------------------------------
def authenticate_from_token():
    query_params = st.query_params

    if "token" not in query_params:
        return False  # nenhuma autenticação

    token = query_params["token"]

    # já autenticado?
    if "usuario" in st.session_state and st.session_state.usuario.get("token") == token:
        return True

    # buscar no Supabase
    cliente = get_client_by_token(token)

    if not cliente:
        st.error("❌ Token inválido. Peça um novo link ao suporte.")
        st.stop()

    # processar carteiras
    carteiras = cliente.get("carteiras", [])
    if isinstance(carteiras, str):
        try:
            carteiras = [c.strip().strip("'").strip('"') for c in carteiras.strip("[]").split(",") if c.strip()]
        except:
            carteiras = []

    # converter datas
    data_inicio = pd.to_datetime(cliente.get("data_inicio")).date()
    data_fim = pd.to_datetime(cliente.get("data_fim")).date()

    # salvar sessão
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


# ------------------------------------------------------
# 3) Bloquear acesso se não tiver token
# ------------------------------------------------------
def require_token():
    ok = authenticate_from_token()

    if not ok:
        st.error("Você precisa acessar através do link enviado pelo suporte.")
        st.stop()

    return True

