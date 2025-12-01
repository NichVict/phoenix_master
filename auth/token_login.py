import streamlit as st
import pandas as pd
import requests


# -----------------------------------------------
# CONFIGURAÇÃO DO SUPABASE (REST API)
# -----------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

REST_URL = f"{SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}


# -----------------------------------------------
# BUSCAR CLIENTE PELO TOKEN (REST)
# -----------------------------------------------
def get_client_by_token(token: str):
    try:
        url = f"{REST_URL}/clientes"
        params = {"token": f"eq.{token}"}

        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code != 200:
            st.error("Erro ao consultar Supabase.")
            return None

        data = response.json()
        if len(data) > 0:
            return data[0]

        return None

    except Exception as e:
        st.error(f"Erro ao validar token: {e}")
        return None


# -----------------------------------------------
# AUTENTICAR A PARTIR DO TOKEN DA URL
# -----------------------------------------------
def authenticate_from_token():
    query = st.query_params

    if "token" not in query:
        return False  # nenhum token enviado

    token = query["token"]

    # Sessão já existe e o token é o mesmo?
    if "usuario" in st.session_state:
        if st.session_state.usuario.get("token") == token:
            return True

    cliente = get_client_by_token(token)

    if not cliente:
        st.error("❌ Token inválido ou expirado.")
        st.stop()

    # Processar carteiras
    carteiras = cliente.get("carteiras", [])
    if isinstance(carteiras, str):
        carteiras = [
            c.strip().strip("'").strip('"')
            for c in carteiras.strip("[]").split(",")
            if c.strip()
        ]

    # Converter datas
    data_inicio = pd.to_datetime(cliente["data_inicio"]).date()
    data_fim = pd.to_datetime(cliente["data_fim"]).date()

    # Guardar sessão
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


# -----------------------------------------------
# BLOQUEAR ACESSO SE NÃO TIVER TOKEN
# -----------------------------------------------
def require_token():
    ok = authenticate_from_token()

    if not ok:
        st.error("Você precisa acessar através do link enviado por e-mail.")
        st.stop()

    return True
