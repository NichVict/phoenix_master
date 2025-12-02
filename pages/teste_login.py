import streamlit as st
import requests

SUPABASE_URL = st.secrets["SUPABASE_URL_CLIENTES"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY_CLIENTES"]

REST_URL = f"{SUPABASE_URL}/rest/v1/clientes"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

def buscar_cliente(token):
    url = f"{REST_URL}?token=eq.{token}&select=*"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return None
    data = r.json()
    return data[0] if data else None

params = st.query_params
token = params.get("token")

if not token:
    st.error("❌ Acesso bloqueado. Token ausente.")
    st.stop()

cliente = buscar_cliente(token)

if not cliente:
    st.error("❌ Token inválido ou expirado.")
    st.stop()

if "Carteira de BDRs" not in cliente.get("carteiras", []):
    st.error("❌ Você não possui acesso à Carteira de BDRs.")
    st.markdown(f"[Voltar ao login](./teste_login?token={token})")
    st.stop()

st.success(f"🔓 Acesso autorizado — Bem-vindo, {cliente['nome']}!")
