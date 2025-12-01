import streamlit as st
from auth.token_login import require_token, require_carteira

# 1) Carrega o usuário pelo token da URL
user = require_token()



require_carteira("Carteira de BDRs")

