import streamlit as st

# ------------------------------------------------------------
# Card do critério
# ------------------------------------------------------------
def criteria_block(label, status, detail):
    """
    Cria um card visual para mostrar o critério:
    - label: nome do critério
    - status: True/False
    - detail: explicação textual
    """

    # Cores conforme status
    bg = "#0F9D58" if status else "#DB4437"    # verde / vermelho
    icon = "✔️" if status else "❌"

    st.markdown(
        f"""
        <div style="
            background-color: {bg};
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            color: white;
            box-shadow: 0 0 8px rgba(0,0,0,0.3);
        ">
            <h3 style="margin:0; font-size:20px;">{icon} {label}</h3>
            <p style="font-size:14px; margin-top:6px;">{detail}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

