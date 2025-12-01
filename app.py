import streamlit as st
from auth.token_login import require_token
from bp.ui.streamlit_dashboard import render_dashboard


# ----------------------------------------------------------
# 1) PROTEGER O APP COM TOKEN
# ----------------------------------------------------------
require_token()


# ----------------------------------------------------------
# 2) CONFIGURAÇÕES DO APP
# ----------------------------------------------------------
st.set_page_config(
    page_title="Fênix Premium",
    page_icon="🦅",
    layout="wide"
)


# ----------------------------------------------------------
# 3) DASHBOARD PRINCIPAL
# ----------------------------------------------------------
def main():
    render_dashboard()


if __name__ == "__main__":
    main()
