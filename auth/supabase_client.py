import os
import streamlit as st
from supabase import create_client, Client

def get_client() -> Client:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("❌ SUPABASE_URL e SUPABASE_KEY não configurados.")
        st.stop()

    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_client()
