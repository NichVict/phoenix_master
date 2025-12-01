import streamlit as st
from bp.ui.streamlit_dashboard import render_dashboard
from auth.login import require_login_page

require_login_page()



def main():
    render_dashboard()


if __name__ == "__main__":
    main()
