import streamlit as st

st.set_page_config(
    page_title="Fênix Premium",
    page_icon="🦅",
    layout="wide"
)

from auth.token_login import require_token
from bp.ui.streamlit_dashboard import render_dashboard

# Autenticar pelo token
require_token()

def main():
    render_dashboard()

if __name__ == "__main__":
    main()
