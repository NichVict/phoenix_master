import streamlit as st
import requests

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
def buscar_cliente(token):
    url = REST_URL + f"?token=eq.{token}&select=*"
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
# CAPTURAR TOKEN DA URL
# =================================================
params = st.query_params
token = params.get("token", None)

st.write("DEBUG → Token recebido:", token)

if not token:
    st.error("❌ Nenhum token encontrado na URL.")
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


# =================================================
# MOSTRAR INFO DO CLIENTE
# =================================================
st.success(f"🔓 Login reconhecido! Bem-vindo, **{cliente['nome']}**.")

st.write("### 🗂 Suas carteiras:")
for c in cliente["carteiras"]:
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
for cart in cliente["carteiras"]:
    page = MAPA.get(cart)
    if page:
        st.page_link(page + ".py", label=f"➡️ {cart}", icon="📊")

st.page_link("dashboard_geral.py", label="🌐 Dashboard Geral (Livre)", icon="🌍")
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
