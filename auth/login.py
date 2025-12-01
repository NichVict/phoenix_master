import streamlit as st
from auth.supabase_client import supabase
from auth.session import is_logged


# -----------------------------------------------------------
# 1) TELA DE LOGIN
# -----------------------------------------------------------
def login_page():
    st.title("🔐 Login – Fênix Premium")
    st.write("Entre usando Google ou E-mail.")

    # Se já estiver logado → redireciona
    if is_logged():
        st.success("Login realizado com sucesso!")
        st.experimental_rerun()


    # -------------------------------------------------------
    # LOGIN COM GOOGLE
    # -------------------------------------------------------
    st.subheader("Entrar com Google")
    if st.button("✨ Entrar com Google", use_container_width=True):
        redirect_url = st.secrets.get("LOGIN_REDIRECT_URL", "/")
        res = supabase.auth.sign_in_with_oauth(
            {
                "provider": "google",
                "options": {
                    "redirect_to": redirect_url
                }
            }
        )
        st.markdown("Se o navegador não abrir automaticamente, clique abaixo:")
        st.markdown(f"[Clique para entrar com Google]({res.url})")


    st.markdown("---")

    # -------------------------------------------------------
    # LOGIN COM MAGIC LINK
    # -------------------------------------------------------
    st.subheader("Entrar com E-mail")
    email = st.text_input("Seu e-mail:", placeholder="email@exemplo.com")

    if st.button("Enviar link mágico", use_container_width=True):
        if not email:
            st.error("Digite um e-mail válido.")
        else:
            supabase.auth.sign_in_with_otp({"email": email})
            st.success("Link enviado! Verifique seu e-mail.")
            st.info("Após clicar no link, volte para este aplicativo.")


# -----------------------------------------------------------
# 2) FUNÇÃO PARA SER USADA NO APP PRINCIPAL
# -----------------------------------------------------------
def require_login_page():
    if is_logged():
        return True
    else:
        login_page()
        st.stop()
