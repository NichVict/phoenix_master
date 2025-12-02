import streamlit as st
import requests

st.set_page_config(page_title="Login • Phoenix", layout="wide")

st.title("🔐 Login Phoenix Premium")
st.write("Autenticação via token de acesso (link mágico).")
st.markdown("---")

# =================================================
# 🔗 CREDENCIAIS DO SUPABASE
# =================================================
SUPABASE_URL = st.secrets["SUPABASE_URL_CLIENTES"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY_CLIENTES"]

TABLE = "clientes"
REST_URL = f"{SUPABASE_URL}/rest/v1/{TABLE}"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}


# =================================================
# FUNÇÃO: Buscar cliente pelo token (REST)
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

    return data[0]


# =================================================
# 🔐 CAPTURAR TOKEN DA URL
# =================================================
params = st.query_params
token = params.get("token", None)

st.write("DEBUG → Token recebido:", token)

if not token:
    st.error("❌ Nenhum token encontrado na URL.")
    st.info("Acesse usando o link mágico enviado ao seu e-mail.")
    st.stop()


# =================================================
# 🔐 BUSCAR CLIENTE
# =================================================
cliente = buscar_cliente(token)

if not cliente:
    st.error("❌ Token inválido ou cliente não encontrado.")
    st.stop()

# Salva na sessão
st.session_state["cliente"] = cliente

st.markdown("---")

# =================================================
# 👤 EXIBIR INFO DO CLIENTE
# =================================================
nome = cliente.get("nome", "Investidor")
carteiras = cliente.get("carteiras", [])

st.success(f"🔓 Login reconhecido! Bem-vindo, **{nome}**.")

st.subheader("🗂 Suas carteiras disponíveis:")

if not carteiras:
    st.warning("Nenhuma carteira ativa no momento.")

else:
    MAPA_CARTEIRAS = {
        "Carteira de Ações IBOV": "carteira_ibov.py",
        "Carteira de Opções": "carteira_opcoes.py",
        "Carteira de Small Caps": "carteira_small.py",
        "Carteira de BDRs": "carteira_bdr.py",
    }

    for cart in carteiras:
        page = MAPA_CARTEIRAS.get(cart)
        if page:
            st.page_link(f"{page}", label=f"➡️ {cart}", icon="📁")
        else:
            st.warning(f"⚠️ Carteira sem página configurada: {cart}")

st.markdown("---")

st.subheader("📄 Dados completos do cliente (debug):")
st.json(cliente)

st.info("Login concluído. Você já pode acessar suas carteiras acima.")
