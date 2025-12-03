# login.py
import streamlit as st
from urllib.parse import urlencode
from auth import buscar_cliente_por_token, login_user, user_logged

st.set_page_config(page_title="Phoenix Login", page_icon="🦅")

# ============================================
# 🌐 CAPTURA O TOKEN DA URL
# ============================================
query_params = st.query_params
token = query_params.get("token", [None])
token = token[0] if isinstance(token, list) else token


# ============================================
# 🔄 SE JÁ ESTÁ LOGADO, ENVIA PARA DASHBOARD
# ============================================
if user_logged():
    st.switch_page("dashboard_geral.py")


# ============================================
# ❗ SE NÃO TEM TOKEN → EXIBE AVISO
# ============================================
if not token:
    st.markdown(
        """
        <h2>🔐 Phoenix Premium — Login</h2>
        <p style="color:#aaa;font-size:15px;">
            Acesse através do link enviado ao seu e-mail. 
            O link contém seu token de acesso seguro.
        </p>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ============================================
# 🔎 BUSCA CLIENTE PELO TOKEN
# ============================================
cliente = buscar_cliente_por_token(token)

if not cliente:
    st.markdown(
        """
        <h2 style='color:#ef4444;'>⚠️ Token inválido ou expirado</h2>
        <p style="color:#aaa;font-size:15px;">
            O link pode ter expirado ou está incorreto.<br>
            Solicite um novo acesso ao suporte.
        </p>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ============================================
# 🔐 LOGIN BEM-SUCEDIDO
# ============================================
login_user(cliente)

# Redireciona imediatamente para dashboard geral
st.switch_page("dashboard_geral.py")
