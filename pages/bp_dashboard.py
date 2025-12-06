# =========================================================
# 📄 TEMPLATE PADRÃO PARA PÁGINAS ADMIN — FÊNIX
# =========================================================

import streamlit as st
from auth import user_logged

# ⚠️ IDENTIFICAÇÃO DA PÁGINA ADMIN
PAGE_ID = "admin_page_2"            # nome único para esta página admin
PAGE_NAME = "Painel Administrativo" # Ex: "Gestão de Clientes", "Relatórios", etc.

# =========================================================
# 🔐 BLOQUEIO DE EXECUÇÃO INDEVIDA (PRELOAD / DASHBOARD)
# =========================================================

# 1️⃣ Marca que esta página está sendo aberta **pelo usuário**
st.session_state["current_page"] = PAGE_ID

# 2️⃣ Se esta página estiver sendo executada sem ser a ativa (ex: preload)
if st.session_state.get("current_page") != PAGE_ID:
    st.stop()

# =========================================================
# 🚫 BLOQUEIO DE ACESSO (continua igual)
# =========================================================

# 1️⃣ Se não está logado → bloquear
if not user_logged():
    st.error("⚠ Você não está autenticado.")
    if st.button("🔐 Ir para Login"):
        st.switch_page("pages/login.py")
    st.stop()

# 2️⃣ Se não é admin → bloquear
cliente = st.session_state.get("cliente", {})
if not cliente.get("admin", False):
    st.error("🚫 Acesso restrito")

    st.markdown(
        f"""
        <p style="color:#aaa;font-size:15px;">
            A página <strong>{PAGE_NAME}</strong> é exclusiva para administradores do sistema.
            Entre em contato com o suporte caso precise de acesso.
        </p>
        """,
        unsafe_allow_html=True
    )

    if st.button("🏠 Voltar ao Dashboard Geral"):
        st.switch_page("pages/dashboard_geral.py")

    st.stop()

# =========================================================
# ✅ ACESSO LIBERADO — CONTEÚDO ADMIN
# =========================================================

st.title(f"🛠️ {PAGE_NAME}")

st.success("Você está no Modo Administrador (Master). Acesso total liberado.")

st.markdown("---")

st.subheader("📂 Ferramentas Administrativas")
st.info("📌 Aqui você insere relatórios, tabelas, gráficos ou controles internos.")

st.write("Área administrativa em construção...")

st.markdown("---")

if st.button("⬅️ Voltar ao Dashboard Geral"):
    st.switch_page("pages/dashboard_geral.py")





from bp.ui.streamlit_dashboard import render_dashboard

# ---- DAQUI PRA BAIXO É A LÓGICA NORMAL DA PÁGINA ----

# Se chegou aqui → ADMIN OK (liberado)
st.set_page_config(page_title="BP Fênix", layout="wide")

render_dashboard()
