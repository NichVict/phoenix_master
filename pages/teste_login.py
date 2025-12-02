import streamlit as st
import requests

# =================================================
# 🔧 CONFIGURAÇÃO
# =================================================
st.set_page_config(page_title="Login - Phoenix", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL_CLIENTES"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY_CLIENTES"]

TABLE = "clientes"
REST_URL = f"{SUPABASE_URL}/rest/v1/{TABLE}"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

# =================================================
# 🔍 FUNÇÃO DE BUSCA VIA REST
# =================================================
def buscar_cliente(token):
    url = f"{REST_URL}?token=eq.{token}&select=*"
    resp = requests.get(url, headers=HEADERS)

    st.write("DEBUG → URL:", url)
    st.write("DEBUG → STATUS:", resp.status_code)
    st.write("DEBUG → RAW:", resp.text)

    if resp.status_code != 200:
        return None

    data = resp.json()
    if not data:
        return None

    return data[0]

# =================================================
# 🔐 TOKEN DA URL
# =================================================
params = st.query_params
token = params.get("token", None)

st.title("🔐 Login – Phoenix Premium")
st.write("Página dedicada apenas à autenticação via token REST.")

st.write("DEBUG → Token:", token)

if not token:
    st.error("Nenhum token encontrado na URL.")
    st.info("Use o link mágico enviado para o seu e-mail.")
    st.stop()

# =================================================
# 🔐 BUSCA DO CLIENTE
# =================================================
cliente = buscar_cliente(token)

if not cliente:
    st.error("❌ Token inválido ou cliente não encontrado.")
    st.markdown("---")
    st.markdown("### 📊 Acesso livre ao dashboard geral")
    st.markdown(
        f"➡️ [Ir para o Dashboard Geral](./dashboard_geral?token={token})"
    )
    st.stop()

# =================================================
# 👤 DADOS DO CLIENTE
# =================================================
nome = cliente.get("nome", "Investidor")
carteiras = cliente.get("carteiras", [])

st.success(f"🔓 Bem-vindo, **{nome}**!")

st.markdown("## 🗂 Suas carteiras ativas:")
if not carteiras:
    st.warning("Nenhuma carteira ativa atribuída.")
else:
    for c in carteiras:
        st.write(f"- {c}")

# =================================================
# 🔗 MAPA DAS PÁGINAS
# =================================================
MAPA_PAGINAS = {
    "Carteira de Ações IBOV": "carteira_ibov",
    "Carteira de Opções": "carteira_opcoes",
    "Carteira de Small Caps": "carteira_small",
    "Carteira de BDRs": "carteira_bdr",
}

st.markdown("---")
st.markdown("## 📁 Acessar carteiras")

for cart in carteiras:
    page = MAPA_PAGINAS.get(cart)
    if page:
        st.markdown(
            f"➡️ [{cart}](./{page}?token={token})",
            unsafe_allow_html=True,
        )
    else:
        st.warning(f"Carteira não mapeada: {cart}")

# =================================================
# 📊 ACESSO LIVRE AO DASHBOARD (sempre liberado)
# =================================================
st.markdown("---")
st.markdown("## 📊 Acesso ao Dashboard Geral")
st.markdown(
    f"➡️ [Dashboard Geral](./dashboard_geral?token={token})"
)

# =================================================
# 🔍 DEBUG
# =================================================
st.markdown("---")
st.markdown("### 🔍 Debug – Dados completos do cliente")
st.json(cliente)
