import streamlit as st
from auth.token_login import require_token, require_carteira


require_carteira("Carteira de Small Caps")

