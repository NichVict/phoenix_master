import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Teste de Login", layout="centered")

st.title("🔎 Teste de Login via Token")
st.write("Página simples para testar a leitura do cliente exatamente igual ao CRM.")


# ======================================================
# 🔗 CREDENCIAIS — Exatamente como no CRM
# ======================================================
SUPABASE_URL = st.secrets["SUPABASE_URL_CLIENTES"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY_CLIENTES"]

st.write("DEBUG → URL:", SUPABASE_URL)
st.write("DEBUG → KEY prefix:", SUPABASE_KEY[:5])


# ======================================================
# 🔗 Criar client Supabase usando a versão estável (CRM)
# ======================================================
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    st.success("Supabase conectado com sucesso! (Modo CRM)")
except Exception as e:
    st.error("❌ ERRO ao criar cliente Supabase.")
    st.exception(e)
    st.stop()


# ======================================================
# 🔐 Função para buscar cliente pelo token
# ======================================================
def carregar_cliente():
    st.write("DEBUG → Iniciando leitura do token...")

    params = st.query_params
    token = params.get("token", None)

    st.write("DEBUG → Token recebido:", token)

    if not token:
        st.warning("Nenhum token na URL.")
        return None

    try:
        resp = (
            supabase
            .table("clientes")
            .select("*")
            .eq("token", token)
            .single()
            .execute()
        )
        cliente = resp.data
        st.write("DEBUG → Supabase resposta:", resp)
    except Exception as e:
        st.error("Erro Supabase ao buscar cliente.")
        st.exception(e)
        return None

    return cliente


# ======================================================
# 🔐 Executar leitura
# ======================================================
cliente = carregar_cliente()

st.markdown("---")

# ======================================================
# 📌 EXIBIR RESULTADO
# ======================================================
if not cliente:
    st.error("❌ Nenhum cliente encontrado para esse token.")
    st.info("Use um link mágico válido enviado pelo CRM.")
else:
    st.success("Cliente encontrado!")

    st.write("### 👤 Dados do Cliente:")
    st.json(cliente)

    st.write("### 🗂 Carteiras Ativas:")
    carteiras = cliente.get("carteiras", [])

    if not carteiras:
        st.warning("Cliente não possui carteiras registradas.")
    else:
        for c in carteiras:
            st.write(f"- {c}")
