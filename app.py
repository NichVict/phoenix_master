import streamlit as st
from auth.login import require_login_page
from bp.ui.streamlit_dashboard import render_dashboard

# 1) Protege o app – se não estiver logado → mostra tela de login
require_login_page()

# 2) Conteúdo do sistema após login
def main():
    st.set_page_config(
        page_title="Fênix Premium",
        page_icon="🦅",
        layout="wide"
    )

    # Exibir o dashboard
    render_dashboard()


if __name__ == "__main__":
    main()
