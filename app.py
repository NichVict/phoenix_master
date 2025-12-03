import streamlit as st
from auth import get_session_user

# =====================================
#  MENSAGEM DE BOAS-VINDAS PERSONALIZADA
# =====================================

user = get_session_user()  # retorna dict ou None

if user:
    nome = user.get("nome", "Cliente")
    carteiras = user.get("carteiras_crm", [])

    st.markdown(f"### 👋 Bem-vindo, **{nome}**!")
    st.markdown(
        "Você agora tem acesso ao seu painel premium Fênix. "
        "Abaixo estão as carteiras incluídas na sua assinatura:"
    )

    # Lista das carteiras assinadas
    for c in carteiras:
        st.markdown(f"- **{c}**")

    st.info("👉 Utilize o menu lateral (sidebar) para navegar pelas carteiras e visualizar a performance em tempo real.")

