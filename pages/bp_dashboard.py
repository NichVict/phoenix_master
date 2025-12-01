import streamlit as st
from bp.ui.streamlit_dashboard import render_dashboard
from auth.token_login import require_token

user = require_token()

st.set_page_config(page_title="BP Fênix", layout="wide")

render_dashboard()
