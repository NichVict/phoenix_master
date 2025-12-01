import streamlit as st
from auth.token_login import require_token, require_carteira

# 🔐 Autenticação + permissão
user = require_token()
require_carteira("Carteira de Ações IBOV")
