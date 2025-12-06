# pages/login.py
import streamlit as st
from auth import buscar_cliente_por_token, login_user, user_logged

# 🔹 Caminho correto relativo ao app.py (como era antes)
DASHBOARD_GERAL_PAGE = "pages/dashboard_geral.py"

st.set_page_config(
    page_title="Phoenix Login",
    page_icon="🦅"
)

# ============================================================
# 1️⃣ SE O USUÁRIO JÁ ESTÁ LOGADO → REDIRECIONA PARA DASHBOARD
# ============================================================
if user_logged():
    st.switch_page(DASHBOARD_GERAL_PAGE)

# ============================================================
# 2️⃣ CAPTURA O TOKEN DA URL
# ============================================================
query_params = st.query_params
token = query_params.get("token", None)

# ============================================================
# 3️⃣ SE NÃO TEM TOKEN → EXIBE PÁGINA SIMPLES (SEM BLOQUEAR SITE)
# ============================================================
if not token:
    st.markdown(
        """
        <h2>🔐 Área de Login do Phoenix</h2>
        <p style="color:#aaa; font-size:15px;">
            Para acessar suas carteiras premium, utilize o <b>link mágico</b> 
            enviado ao seu e-mail.
        </p>
        <p style="color:#888; font-size:14px;">
            Caso você seja um visitante, pode voltar ao <b>Dashboard Geral</b> 
            pelo menu lateral ou acessando diretamente.
        </p>
        """,
        unsafe_allow_html=True
    )
    st.stop()

# ============================================================
# 4️⃣ VALIDA TOKEN DO CLIENTE
# ============================================================
cliente = buscar_cliente_por_token(token)

if not cliente:
    st.markdown(
        """
        <h2 style='color:#ef4444;'>⚠️ Token inválido ou expirado</h2>
        <p style="color:#aaa; font-size:15px;">
            O link pode ter expirado ou estar incorreto.<br>
            Solicite um novo acesso ao suporte.
        </p>
        """,
        unsafe_allow_html=True
    )
    st.stop()

# ============================================================
# 5️⃣ LOGIN OK → SALVA CLIENTE NA SESSÃO
# ============================================================
login_user(cliente)

# ============================================================
# 6️⃣ REDIRECIONA PARA O DASHBOARD GERAL
# ============================================================
st.switch_page(DASHBOARD_GERAL_PAGE)
