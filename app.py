import streamlit as st

st.set_page_config(
    page_title="Phoenix Strategy",
    page_icon="🦅",
    layout="wide"
)

st.title("🦅 Phoenix Strategy")
st.info("Menu lateral totalmente liberado. Todas as carteiras e ferramentas estão acessíveis.")

# ===========================
#  BOAS-VINDAS AO CLIENTE
# ===========================

if "logged" in st.session_state and st.session_state["logged"]:
    cliente = st.session_state.get("cliente", {})
    nome = cliente.get("nome", "Investidor")
    carteiras = cliente.get("page_ids", [])

    st.success(f"👋 Bem-vindo, **{nome}**!")

    st.markdown("### 💼 Suas carteiras ativas:")
    
    if carteiras:
        for c in carteiras:
            st.markdown(f"- **{c.replace('_', ' ').title()}**")
    else:
        st.warning("Nenhuma carteira ativa no momento.")

    st.info("⮘ Use o menu lateral para acessar o desempenho das suas carteiras em tempo real.")
