from auth.token_login import require_token

# 🔐 Autenticação obrigatória (todos clientes têm acesso)
user = require_token()

