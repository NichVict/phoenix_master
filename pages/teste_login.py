import streamlit as st
import requests

st.set_page_config(page_title="Teste Login REST", layout="centered")

# =================================================
# CONFIG (iguais ao CRM)
# =================================================
SUPABASE_URL = st.secrets["SUPABASE_URL_CLIENTES"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY_CLIENTES"]

TABLE = "clientes"

REST_URL = f"{SUPABASE_URL}/rest/v1/{TABLE}"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}


st.title("🔎 Teste Login via REST (sem supabase-py)")
st.write("Usando a API REST nativa do Supabase")


# =================================================
# FUNÇÃO → Buscar cliente pelo token
# =================================================
def buscar_cliente(token):
    query = f"?token=eq.{token}&select=*"

    url = REST_URL + query
    st.write("DEBUG → URL:", url)

    resp = requests.get(url, headers=HEADERS)

    st.write("DEBUG → Status:", resp.status_code)
    st.write("DEBUG → Conteúdo bruto:", resp.text)

    if resp.status_code != 200:
        return None

    data = resp.json()

    if not data:
        return None

    return data[0]  # único registro


# =================================================
# Capturar token da URL
# =================================================
params = st.query_params
token = params.get("token", None)

st.write("DEBUG → Token:", token)

if not token:
    st.warning("Nenhum token encontrado.")
    st.stop()


# =================================================
# Buscar cliente
# =================================================
cliente = buscar_cliente(token)

st.markdown("---")

if not cliente:
    st.error("❌ Nenhum cliente encontrado para esse token.")
else:
    st.success("Cliente encontrado!")
    st.json(cliente)

    carteiras = cliente.get("carteiras", [])
    st.write("### Carteiras:")
    for c in carteiras:
        st.write(f"- {c}")
