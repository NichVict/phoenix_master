import streamlit as st
from auth.token_login import require_token, require_carteira

# 1) Carrega o usuário pelo token da URL
user = require_token()

# 2) Verifica permissão da carteira específica
require_carteira("Carteira de Ações IBOV")

# ---- DAQUI PRA BAIXO É O CÓDIGO NORMAL DA PÁGINA ----
