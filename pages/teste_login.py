import streamlit as st
import requests

# =================================================
# CONFIG BÁSICA
# =================================================
st.set_page_config(page_title="Login Phoenix", layout="wide")

st.title("🔑 Login Phoenix – Acesso via Token (REST)")
st.write("Versão simplificada para validar autenticação e permissões.")


# =================================================
# 🔗 CREDENCIAIS
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
def buscar_cliente(token: str):
    url = REST_URL + f"?token=eq.{token}&select=*"
    st.write("DEBUG → URL:", url)

    resp = requests.get(url, headers=HEADERS)

    st.write("DEBUG → Status:", resp.status_code)
    st.write("DEBUG → Conteúdo bruto:", resp.text)

    if resp.status_code != 200:
        return None

    try:
        data = resp.json()
    except Exception as e:
        st.write("DEBUG → Erro ao fazer resp.json():", e)
        return None

    if not data:
        return None

    return data[0]


# =================================================
# CAPTURAR TOKEN DA URL
# =================================================
params = st.query_params
token = params.get("token", None)

st.write("DEBUG → Token recebido:", token)

if not token:
    st.error("❌ Nenhum token encontrado na URL.")
    st.info("Acesse usando o link mágico enviado ao seu e-mail.")
    st.stop()


# =================================================
# BUSCAR CLIENTE
# =================================================
cliente = buscar_cliente(token)

if not cliente:
    st.error("❌ Token inválido ou cliente não encontrado.")
    st.stop()


# =================================================
# SALVAR NA SESSÃO (ESSENCIAL!)
# =================================================
st.session_state["token"] = token
st.session_state["cliente"] = cliente

st.write("DEBUG → session_state.token =", st.session_state.get("token"))
st.write("DEBUG → session_state.cliente.nome =", st.session_state["cliente"].get("nome"))


# =================================================
# MOSTRAR INFO DO CLIENTE
# =================================================
st.success(f"🔓 Login reconhecido! Bem-vindo, **{cliente['nome']}**.")

st.write("### 🗂 Suas carteiras:")
carteiras = cliente.get("carteiras", []) or []
if not carteiras:
    st.warning("Nenhuma carteira ativa para este cliente.")
else:
    for c in carteiras:
        st.write(f"✔️ {c}")

st.markdown("---")
st.write("### 🔍 Dados completos do cliente (debug):")
st.json(cliente)

st.markdown("---")

# =================================================
# 🔗 LINKS PARA PÁGINAS PROTEGIDAS
# =================================================
MAPA = {
    "Carteira de Ações IBOV": "carteira_ibov",
    "Carteira de BDRs": "carteira_bdr",
    "Carteira de Small Caps": "carteira_small",
    "Carteira de Opções": "carteira_opcoes",
}

st.write("### 📁 Acessar Carteiras Liberadas:")

for cart in carteiras:
    page = MAPA.get(cart)
    if page:
        # nome do arquivo na pasta pages
        st.page_link(page + ".py", label=f"➡️ {cart}", icon="📊")

# Dashboard geral sempre liberado
st.page_link("dashboard_geral.py", label="🌐 Dashboard Geral (Livre)", icon="🌍")
