import streamlit as st
from auth.supabase_client import supabase


# -----------------------------------------------------------
# 1) PEGAR SESSÃO ATUAL DO SUPABASE
# -----------------------------------------------------------
def get_supabase_session():
    try:
        session = supabase.auth.get_session()
        return session
    except Exception:
        return None


# -----------------------------------------------------------
# 2) SALVAR SESSÃO DO USUÁRIO NO STREAMLIT
# -----------------------------------------------------------
def save_user_session(session):
    if session and session.user:
        st.session_state["user"] = {
            "email": session.user.email,
            "id": session.user.id,
        }
    else:
        st.session_state["user"] = None


# -----------------------------------------------------------
# 3) CHECAR SE ESTÁ LOGADO
# -----------------------------------------------------------
def is_logged():
    session = get_supabase_session()
    if session and session.user:
        save_user_session(session)
        return True
    return False


# -----------------------------------------------------------
# 4) PROTEGER PÁGINAS INTERNAS
# -----------------------------------------------------------
def require_login():
    if not is_logged():
        st.warning("Você precisa fazer login para acessar esta página.")
        st.stop()


# -----------------------------------------------------------
# 5) LOGOUT
# -----------------------------------------------------------
def logout():
    supabase.auth.sign_out()
    st.session_state.clear()
    st.experimental_rerun()
