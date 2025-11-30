import streamlit as st
import pandas as pd
from datetime import date, timedelta
from supabase import create_client
import os

st.set_page_config(page_title="MRR Analytics", layout="wide")

# --------- SUPABASE CONFIG ---------
def get_secret(name, default=None):
    if name in st.secrets:
        return st.secrets[name]
    return os.getenv(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------- LOAD CLIENT DATA ---------
query = supabase.table("clientes").select("*").execute()
dados = query.data or []
df = pd.DataFrame(dados)

if df.empty:
    st.warning("Nenhum cliente cadastrado ainda.")
    st.stop()

df["data_inicio"] = pd.to_datetime(df["data_inicio"], errors="coerce")
df["data_fim"] = pd.to_datetime(df["data_fim"], errors="coerce")

today = date.today()

# --------- METRICS CALC ---------
df["ativo"] = df["data_fim"] >= pd.to_datetime(today)
df_ativos = df[df["ativo"] == True]

# MRR (soma dos valores mensais)
df_ativos["valor_mensal"] = df_ativos["valor"] / 3  # contratos trimestrais
MRR = df_ativos["valor_mensal"].sum()

# churn last 30 days
df_cancelados = df[df["data_fim"] < pd.to_datetime(today)]
df_cancelados_30 = df_cancelados[df_cancelados["data_fim"] >= pd.to_datetime(today - timedelta(days=30))]

churn = 0
if len(df_ativos) + len(df_cancelados_30) > 0:
    churn = len(df_cancelados_30) / (len(df_ativos) + len(df_cancelados_30))

# LTV simples: ticket médio x 3 meses (pra melhorar depois)
ticket_medio = df_ativos["valor_mensal"].mean() if not df_ativos.empty else 0
LTV = ticket_medio * 3

# --------- KPIs ---------
c1, c2, c3, c4 = st.columns(4)

c1.metric("MRR Atual", f"R$ {MRR:,.2f}")
c2.metric("Assinantes Ativos", len(df_ativos))
c3.metric("Churn 30 dias", f"{(churn*100):.2f}%")
c4.metric("LTV Estimado", f"R$ {LTV:,.2f}")

st.divider()

# --------- CHART ---------
st.subheader("📈 Evolução do número de clientes por mês")

df["mes"] = df["data_inicio"].dt.to_period("M").astype(str)
growth = df.groupby("mes")["id"].count().reset_index()
growth = growth.rename(columns={"id": "novos_clientes"})

st.line_chart(growth, x="mes", y="novos_clientes")

# --------- EXPLICACAO DOS METRICOS ---------
with st.expander("📘 Conceitos — entenda os indicadores"):
    st.markdown("""
### 💰 MRR — Monthly Recurring Revenue
Receita recorrente mensal.  
É quanto o seu negócio gera por mês com assinaturas ativas.

> **Fórmula simplificada:** soma de todos os valores mensais dos assinantes ativos

---

### 🔁 Churn Rate
Percentual de clientes que cancelam / deixam de renovar dentro de um período.

> **Fórmula:** clientes perdidos ÷ clientes totais do início do período

Quanto menor o churn, melhor.  
Churn alto = alerta de retenção!

---

### 🧠 LTV — Lifetime Value
Valor total que um cliente gera durante o tempo em que permanece ativo.

> **Fórmula simplificada:** ticket mensal médio × tempo médio na base

LTV alto = base fiel e receita mais previsível ✅
""")

