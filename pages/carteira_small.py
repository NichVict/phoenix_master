# -*- coding: utf-8 -*-


import os
import json
import datetime
from typing import Dict, Any, Optional, Tuple
import streamlit as st
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from zoneinfo import ZoneInfo
import base64
import pandas as pd
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, Frame, PageTemplate
)

import matplotlib
matplotlib.use("Agg")

import yfinance as yf
import mplfinance as mpf



# ===== BLOCO IMPORTADO DO ROBÔ CURTO =====

from dataclasses import dataclass
from typing import List, Dict, Any, Literal, Optional
import datetime as dt
import yfinance as yf
import logging

import os
import streamlit as st

def getenv(key: str) -> str:
    """
    1) Tenta os.environ  (Render, terminal)
    2) Tenta st.secrets  (Streamlit local)
    3) Se nada existir, retorna ''
    """
    if key in os.environ and os.environ[key].strip() != "":
        return os.environ[key].strip()

    try:
        val = st.secrets.get(key, "")
        if val:
            return str(val).strip()
    except:
        pass

    return ""






def salvar_lead_dashboard(nome: str, email: str, telefone: str) -> tuple[bool, str]:
    """
    Insere um LEAD na tabela 'clientes' do CRM,
    marcado com carteira 'Leads' e observação de origem.
    """
    if not SUPABASE_URL_CLIENTES or not SUPABASE_KEY_CLIENTES:
        return False, "URL/KEY do Supabase (clientes) não configurados."

    url = f"{SUPABASE_URL_CLIENTES}/rest/v1/clientes"
    headers = {
        "apikey": SUPABASE_KEY_CLIENTES,
        "Authorization": f"Bearer {SUPABASE_KEY_CLIENTES}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    hoje = datetime.date.today()
    fim = hoje + datetime.timedelta(days=30)

    payload = {
        "nome": nome,
        "email": email,
        "telefone": telefone,
        "carteiras": ["Leads"],  # o CRM já trata "Leads" como lead
        "data_inicio": str(hoje),
        "data_fim": str(fim),
        "pagamento": None,
        "valor": 0.0,
        "observacao": "Lead - Dashboard 30 dias Projeto Phoenix",
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code in (200, 201, 204):
            return True, "OK"
        else:
            return False, f"HTTP {r.status_code} - {r.text}"
    except Exception as e:
        return False, str(e)



PALETTE = [
    "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
    "#06b6d4", "#84cc16", "#f97316", "#ec4899", "#22c55e",
]
TICKER_COLORS: Dict[str, str] = {}

def get_ticker_color(ticker: str) -> str:
    t = ticker.upper()
    if t not in TICKER_COLORS:
        idx = len(TICKER_COLORS) % len(PALETTE)
        TICKER_COLORS[t] = PALETTE[idx]
    return TICKER_COLORS[t]

Operacao = Literal["compra", "venda"]
DirecaoSignal = Literal["compra", "venda", "zerar"]

@dataclass
class AtivoConfig:
    ticker: str
    operacao: Operacao
    preco: float

@dataclass
class Signal:
    ticker: str
    direcao: DirecaoSignal
    preco_ref: float
    preco_mercado: float
    motivo: str
    timestamp: str

@dataclass
class RoboState:
    ativos: List[AtivoConfig]
    params: Dict[str, Any]
    last_run: Optional[str]
    last_signals: List[Signal]
    raw: Dict[str, Any]

@dataclass
class AtivoLoss:
    ticker: str
    operacao: Operacao
    preco_entrada: float
    stop_gain: float
    stop_loss: float
    data_abertura: str

# =========================================================
# Função oficial — Coletar operações abertas (LOSS CURTO)
# =========================================================
def coletar_operacoes_abertas_loss_curto():
    """
    Retorna lista de operações abertas do robô LOSS CURTO,
    exatamente como usadas no módulo Stop Trading.
    """
    state = load_state_loss_curto()
    ativos = state.ativos

    # Obter preços atuais
    tickers = [a.ticker for a in ativos]
    quotes = fetch_quotes_yf(tickers) if tickers else {}

    agora = datetime.datetime.now()
    abertas = []

    for a in ativos:
        preco_atual = quotes.get(a.ticker, 0.0)
        pnl = (preco_atual - a.preco_entrada) if preco_atual else 0
        pct = (pnl / a.preco_entrada) * 100 if a.preco_entrada else 0

        try:
            dias = (agora - a.data_abertura).total_seconds() / 86400
        except:
            dias = None

        abertas.append({
            "ticker": a.ticker,
            "operacao": a.operacao,
            "preco_abertura": a.preco_entrada,
            "preco_atual": preco_atual,
            "pnl": pnl,
            "pnl_pct": pct,
            "stop_gain": a.stop_gain,
            "stop_loss": a.stop_loss,
            "data_abertura": a.data_abertura,
            "dur_days": dias,
            "robo_nome_base": "LOSS CURTO",
        })

    return abertas


# =========================================================
# Função oficial — Enriquecer operações (estado igual Stop Trading)
# =========================================================
def enriquecer_operacoes_abertas(abertas):
    enriched = []

    for a in abertas:
        preco = a["preco_atual"] or 0

        # === Lógica de estado idêntica ao Stop Trading ===
        estado = "monitorando"
        if preco > 0:
            if a["operacao"] == "compra":
                if preco >= a["stop_gain"] or preco <= a["stop_loss"]:
                    estado = "contagem"
            else:  # venda
                if preco <= a["stop_gain"] or preco >= a["stop_loss"]:
                    estado = "contagem"

        e = {**a, "estado": estado}
        enriched.append(e)

    return enriched



# ======== LER ESTADO DO ROBÔ CURTO (SOMENTE LEITURA) ========

# ============================================================
# FUNÇÃO NECESSÁRIA PARA LER O SUPABASE (PARA load_state_curto)
# ============================================================


def get_supabase_client():
    """
    Cria um cliente Supabase seguro usando os secrets
    supabase_url_curto e supabase_key_curto.
    Necessário para load_state_curto().
    """
    url = st.secrets.get("supabase_url_curto", "")
    key = st.secrets.get("supabase_key_curto", "")

    if not url or not key:
        raise RuntimeError("Supabase URL/Key do Curto não encontradas no st.secrets.")

    # http2 desabilitado resolve erros de upload/gzip no Streamlit Cloud
    options = ClientOptions().copy(update={"http2": False})

    return create_client(url, key, options=options)


# ========= PARAMETROS PADRÃO DO ROBÔ CURTO =========
DEFAULT_PARAMS = {
    "gatilho_perc": 0.01,   # 1%
    "stop_perc": 0.02,      # 2%
    "timeframe_min": 5,     # minutos (informativo)
}

# ========= FUNÇÃO FINAL PARA LER O ROBÔ CURTO VIA REST =========
def load_state_curto() -> RoboState:
    url = st.secrets.get("supabase_url_curto", "")
    key = st.secrets.get("supabase_key_curto", "")
    tabela = "kv_state_curto"
    chave_k = "curto_przo_v1"

    if not url or not key:
        return RoboState([], DEFAULT_PARAMS.copy(), None, [], {})

    try:
        endpoint = f"{url}/rest/v1/{tabela}?select=v&k=eq.{chave_k}"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        r = requests.get(endpoint, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        raw = (data[0].get("v", {}) if data else {}) or {}
    except:
        raw = {}

    # --------- NORMALIZAÇÃO CORRIGIDA ---------
    raw.setdefault("ativos", [])
    raw.setdefault("params", DEFAULT_PARAMS.copy())
    raw.setdefault("last_run", "-")         # <---- LINHA QUE FALTAVA!

    # Ativos
    ativos_cfg = []
    for it in raw["ativos"]:
        try:
            ativos_cfg.append(
                AtivoConfig(
                    ticker=str(it.get("ticker","")).upper(),
                    operacao=str(it.get("operacao","")).lower(),
                    preco=float(it.get("preco", 0.0)),
                )
            )
        except:
            pass

    params = DEFAULT_PARAMS.copy()
    params.update(raw.get("params", {}))

    last_signals = []
    for s in raw.get("last_signals", []):
        try:
            last_signals.append(
                Signal(
                    ticker=s["ticker"],
                    direcao=s["direcao"],
                    preco_ref=float(s["preco_ref"]),
                    preco_mercado=float(s["preco_mercado"]),
                    motivo=s.get("motivo", ""),
                    timestamp=s["timestamp"],
                )
            )
        except:
            pass

    return RoboState(
        ativos=ativos_cfg,
        params=params,
        last_run=raw.get("_last_writer_ts") or raw.get("last_run"),
        last_signals=last_signals,
        raw=raw,
    )



def load_state_loss_curto() -> RoboState:
    url = st.secrets.get("supabase_url_losscurto", "")
    key = st.secrets.get("supabase_key_losscurto", "")
    tabela = "kv_state_losscurto"
    chave_k = "loss_curto_przo_v1"

    if not url or not key:
        return RoboState([], {}, None, [], {})

    try:
        endpoint = f"{url}/rest/v1/{tabela}?select=v&k=eq.{chave_k}"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        r = requests.get(endpoint, headers=headers, timeout=10)
        r.raise_for_status()

        data = r.json()
        raw = (data[0].get("v", {}) if data else {}) or {}

    except Exception as e:
        print("Erro ao ler estado loss curto:", e)
        raw = {}

    # Normalização
    if "ativos" not in raw:
        raw["ativos"] = []

    ativos_cfg = []
    for it in raw.get("ativos", []):
        try:
            ativos_cfg.append(
                AtivoLoss(
                    ticker=str(it.get("ticker", "")).upper(),
                    operacao=str(it.get("operacao", "")).lower(),
                    preco_entrada=float(it.get("preco_entrada", 0)),
                    stop_gain=float(it.get("stop_gain", 0)),
                    stop_loss=float(it.get("stop_loss", 0)),
                    data_abertura=str(it.get("data_abertura", "-")),
                )
            )
        except:
            pass

    # Parse últimos sinais
    last_signals = []
    for s in raw.get("last_signals", []):
        try:
            last_signals.append(
                Signal(
                    ticker=s["ticker"],
                    direcao=s["direcao"],
                    preco_ref=float(s["preco_ref"]),
                    preco_mercado=float(s["preco_mercado"]),
                    motivo=s.get("motivo", ""),
                    timestamp=s["timestamp"],
                )
            )
        except:
            pass

    return RoboState(
        ativos=ativos_cfg,
        params=raw.get("params", {}),
        last_run=raw.get("last_run"),
        last_signals=last_signals,
        raw=raw,
    )









def fetch_quotes_yf(tickers: List[str]) -> Dict[str, float]:
    """
    Busca preço intraday. Se não existir, usa preço diário.
    """
    if not tickers:
        return {}

    yf_symbols = [t.upper() + ".SA" for t in tickers]
    quotes = {}

    # 1) tenta intraday 1m
    try:
        data = yf.download(
            tickers=yf_symbols,
            period="1d",
            interval="1m",
            auto_adjust=True,
            progress=False,
        )
    except:
        data = None

    for t, y in zip(tickers, yf_symbols):
        px = None

        # tenta pegar intraday
        try:
            if isinstance(data.columns, pd.MultiIndex):
                px = float(data["Close"][y].dropna().iloc[-1])
            else:
                px = float(data["Close"].dropna().iloc[-1])
        except:
            px = None

        # fallback: usa close diário se intraday falhar
        if px is None or px == 0:
            try:
                d = yf.download(y, period="5d", interval="1d", auto_adjust=True, progress=False)
                px = float(d["Close"].dropna().iloc[-1])
            except:
                px = 0.0

        quotes[t] = px

    return quotes



# -------------------------------------------------
# CONFIG PÁGINA
# -------------------------------------------------
# -------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -------------------------------------------------------------
st.set_page_config(page_title="Painel Visual Carteira Small Caps", layout="wide", page_icon="⭐")



# -------------------------------------------------
# NAVEGAÇÃO GERAL (PAINEL x RELATÓRIOS)
# -------------------------------------------------
secao = st.sidebar.radio(
    "📁 Seção",
    ["Painel", "Relatórios"],
    index=0,
    key="secao_principal"
)


# ====================================================
# VARIÁVEIS DEFAULT PARA EVITAR NameError
# (serão preenchidas no Painel quando secao == "Painel")
# ====================================================
historico_local = None
dados_enc = []
abertas_enriquecidas = []
dados_30d = []
df_oper = None
df_ops_total = None
dados_filtrados = []      # <<== ESSA É A NOVA QUE ESTÁ FALTANDO


# -------------------------------------------------------------


# =====================================================================










# -------------------------------------------------
# VARIÁVEIS GERAIS
# -------------------------------------------------
TZ = ZoneInfo("Europe/Lisbon")
REFRESH_SECONDS = 300
SPARK_MAX_POINTS = 1500
PALETTE = [
    "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
    "#06b6d4", "#84cc16", "#f97316", "#ec4899", "#22c55e"
]
HORARIO_INICIO_PREGAO = datetime.time(13, 0)
HORARIO_FIM_PREGAO    = datetime.time(21, 0)

def agora_lx():
    return datetime.datetime.now(TZ)



def dentro_pregao() -> bool:
    t = agora_lx().time()
    return HORARIO_INICIO_PREGAO <= t <= HORARIO_FIM_PREGAO


# -------------------------------------------------
# HISTÓRICO LOCAL — FUNÇÕES
# -------------------------------------------------
HIST_FILE = "disparos_historico.json"

def carregar_historico() -> list:
    if os.path.exists(HIST_FILE):
        try:
            with open(HIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_historico(data: list):
    try:
        with open(HIST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def contar_disparos_por_robo(historico: list) -> dict:
    contagem = {}
    for r in historico:
        key = r.get("robo")
        if not key:
            continue
        contagem[key] = contagem.get(key, 0) + 1
    return contagem


OPERACOES_FILE = "operacoes_encerradas.json"

def carregar_operacoes_encerradas():
    try:
        with open(OPERACOES_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def salvar_operacoes_encerradas(ops):
    with open(OPERACOES_FILE, "w") as f:
        json.dump(ops, f, indent=4)

# -------------------------------------------------
# SUPABASE — leitura estado de robôs (KV)
# -------------------------------------------------
def ler_estado_supabase(url: str, key: str, tabela: str, chave_k: str) -> Dict[str, Any]:
    if not url or not key:
        return {}
    try:
        endpoint = f"{url}/rest/v1/{tabela}?select=v&k=eq.{chave_k}"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        r = requests.get(endpoint, headers=headers, timeout=12)
        r.raise_for_status()
        data = r.json()
        v = (data[0].get("v", {}) if data else {}) or {}
        return v if isinstance(v, dict) else {}
    except:
        return {}

# -------------------------------------------------
# SUPABASE — REST API (para anon key no Streamlit Cloud)
# -------------------------------------------------
SUPABASE_URL = getenv["supabase_url_operacoes"]
SUPABASE_KEY = getenv["supabase_key_operacoes"]

def supabase_insert(table: str, data: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    return requests.post(url, headers=headers, json=data)

def supabase_select(table: str, filters: str = ""):
    url = f"{SUPABASE_URL}/rest/v1/{table}{filters}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    r = requests.get(url, headers=headers)
    try:
        return r.json()
    except:
        return []

def salvar_operacao_supabase(op):
    data = {
        "robo_base": op["robo_base"],
        "robo_nome_base": op["robo_nome_base"],
        "robo_loss": op["robo_loss"],
        "robo_nome_loss": op["robo_nome_loss"],
        "ticker": op["ticker"],
        "op_abertura": op["op_abertura"],
        "preco_abertura": op["preco_abertura"],
        "data_abertura": op["data_abertura"].isoformat(),
        "op_fechamento_real": op["op_fechamento_real"],
        "preco_fechamento": op["preco_fechamento"],
        "data_fechamento": op["data_fechamento"].isoformat(),
        "pnl": op["pnl"],
        "dur_days": op["dur_days"],
    }
    supabase_insert("operacoes_encerradas", data)


# -------------------------------------------------
# MAPEAMENTO DOS ROBÔS
# -------------------------------------------------
ROBOS = [
    { "key": "curto", "title": "TRADES PENDENTES", "emoji": "⚡",
      "files": ["session_data/visual_state_curto.json"],
      "sb_table": "kv_state_curto", "sb_key": "curto_przo_v1",
      "sb_url_secret": "supabase_url_curto", "sb_key_secret": "supabase_key_curto" },

    { "key": "loss_curto", "title": "TRADES EM ANDAMENTO", "emoji": "⭐",
      "files": ["session_data/visual_state_losscurto.json", "session_data/visual_state_loss_curto.json"],
      "sb_table": "kv_state_losscurto", "sb_key": "loss_curto_przo_v1",
      "sb_url_secret": "supabase_url_losscurto", "sb_key_secret": "supabase_key_losscurto" },

    #{ "key": "curtissimo", "title": "CURTÍSSIMO PRAZO", "emoji": "⚡",
      #"files": ["session_data/visual_state_curtissimo.json"],
      #"sb_table": "kv_state_curtissimo", "sb_key": "curtissimo_przo_v1",
      #"sb_url_secret": "supabase_url_curtissimo", "sb_key_secret": "supabase_key_curtissimo" },

    #{ "key": "loss_curtissimo", "title": "LOSS CURTÍSSIMO", "emoji": "🛑",
      #"files": ["session_data/visual_state_losscurtissimo.json", "session_data/visual_state_loss_curtissimo.json"],
      #"sb_table": "kv_state_losscurtissimo", "sb_key": "loss_curtissimo_przo_v1",
      #"sb_url_secret": "supabase_url_loss_curtissimo", "sb_key_secret": "supabase_key_loss_curtissimo" },

    #{ "key": "clube", "title": "CLUBE", "emoji": "🏛️",
      #"files": ["session_data/visual_state_clube.json"],
      #"sb_table": "kv_state_clube", "sb_key": "clube_przo_v1",
      #"sb_url_secret": "supabase_url_clube", "sb_key_secret": "supabase_key_clube" },

    #{ "key": "loss_clube", "title": "LOSS CLUBE", "emoji": "🏛️🛑",
      #"files": ["session_data/visual_state_lossclube.json", "session_data/visual_state_loss_clube.json"],
      #"sb_table": "kv_state_lossclube", "sb_key": "loss_clube_przo_v1",
      #"sb_url_secret": "supabase_url_loss_clube", "sb_key_secret": "supabase_key_loss_clube" },
]


# -------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------
def try_load_state(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def nice_dt(dt: Optional[datetime.datetime]) -> str:
    if not dt:
        return "—"
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S %Z")

def extract_last_update_from_visual(state: Dict[str, Any]) -> Optional[datetime.datetime]:
    precos = state.get("precos_historicos", {})
    last_dt = None
    if isinstance(precos, dict):
        for pts in precos.values():
            if isinstance(pts, list) and pts:
                ts = pts[-1][0]
                try:
                    dt = datetime.datetime.fromisoformat(str(ts))
                    if not last_dt or dt > last_dt:
                        last_dt = dt
                except Exception:
                    continue
    if not last_dt:
        ts = state.get("_last_writer_ts")
        if ts:
            try:
                last_dt = datetime.datetime.fromisoformat(str(ts))
            except Exception:
                pass
    return last_dt

def summarize_visual_state(state: Dict[str, Any]) -> Dict[str, Any]:
    precos = state.get("precos_historicos", {}) or {}
    disparos = state.get("disparos", {}) or {}
    tickers = list(precos.keys())
    total_disparos = sum(len(v) for v in disparos.values()) if isinstance(disparos, dict) else 0
    last_update = extract_last_update_from_visual(state)
    return {
        "ativos_monitorados": len(tickers),
        "tickers": tickers,
        "total_disparos": total_disparos,
        "last_update": last_update,
        "alertas": [],
    }

def summarize_supabase_state(sb_v: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(sb_v, dict):
        return {"ativos_monitorados": 0, "tickers": [], "total_disparos": 0, "last_update": None, "alertas": []}
    ativos = sb_v.get("ativos", []) or []
    tickers = []
    for a in ativos:
        if isinstance(a, dict):
            t = (a.get("ticker") or "").upper().strip()
            if t:
                tickers.append(t)
        elif isinstance(a, str):
            tickers.append(a.upper().strip())
    historico = sb_v.get("historico_alertas") or []
    disparos_list = sb_v.get("disparos") or []
    eventos_enviados = sb_v.get("eventos_enviados") or []
    total_disparos = 0
    for grupo in [historico, disparos_list, eventos_enviados]:
        if isinstance(grupo, list):
            total_disparos += len(grupo)
    last = None
    for grupo in [historico, disparos_list, eventos_enviados]:
        if not isinstance(grupo, list):
            continue
        for h in grupo:
            if isinstance(h, dict) and h.get("hora"):
                try:
                    dt = datetime.datetime.fromisoformat(str(h["hora"]))
                    if not last or dt > last:
                        last = dt
                except Exception:
                    continue
    if not last:
        ts = sb_v.get("_last_writer_ts")
        if ts:
            try:
                last = datetime.datetime.fromisoformat(str(ts))
            except Exception:
                pass
    return {
        "ativos_monitorados": len(set(tickers)),
        "tickers": list(dict.fromkeys(tickers)),
        "total_disparos": total_disparos,
        "last_update": last,
        "alertas": historico or disparos_list or eventos_enviados,
    }

def badge_status_tempo(last_dt: Optional[Any]) -> Tuple[str, str]:
    """Avalia o tempo da última atualização e retorna texto + cor."""
    if not dentro_pregao():
        return ("Fora do pregão", "#ef4444")

    if last_dt is None:
        return ("⚪ Sem atualização recente", "#9ca3af")

    # Converte string ISO
    if isinstance(last_dt, str):
        try:
            last_dt = datetime.datetime.fromisoformat(last_dt)
        except Exception:
            return ("⚠️ Data inválida", "#f97316")

    if not isinstance(last_dt, datetime.datetime):
        return ("⚠️ Tipo de data desconhecido", "#f97316")

    try:
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=TZ)
        agora = agora_lx()
        delta_min = abs((agora - last_dt).total_seconds()) / 60.0
    except Exception as e:
        return (f"⚠️ Erro ao calcular tempo — {type(e).__name__}", "#f97316")

    if delta_min < 60:
        return (" Atualizado recentemente", "#22c55e")
    elif delta_min < 180:
        return (" Atualizado há pouco", "#facc15")
    else:
        return (" Atualização passada", "#f97316")








# -------------------------------------------------
# TOPO / STATUS
# -------------------------------------------------


st.title("Painel Visual 🦅  Estratégia Phoenix")

if secao == "Painel":

    st.caption(f"Atualiza automaticamente a cada {REFRESH_SECONDS}s")
    st_autorefresh(interval=REFRESH_SECONDS * 1000, key="painel-visual-refresh")
    st.markdown("---")
    
    
    
    
    # -------------------------------------------------
    # -------------------------------------------------
    # STATUS DO PREGÃO + RELÓGIO (Lisboa x São Paulo)
    # -------------------------------------------------
    import pytz
    
    TZ_BR = pytz.timezone("America/Sao_Paulo")
    TZ_PT = pytz.timezone("Europe/Lisbon")
    TZ_NY = pytz.timezone("America/New_York")   # ← NOVO
        
    
    agora_pt = datetime.datetime.now(TZ_PT)
    agora_br = agora_pt.astimezone(TZ_BR)
    agora_ny = agora_pt.astimezone(TZ_NY)       # ← E ESTA TAMBÉM
    # Verifica se é final de semana (sábado=5, domingo=6)
    dia_semana = agora_pt.weekday()
    if dia_semana >= 5:
        pregao_aberto = False
    else:
        pregao_aberto = HORARIO_INICIO_PREGAO <= agora_pt.time() <= HORARIO_FIM_PREGAO
    
    
    cor_status = "#22c55e" if pregao_aberto else "#ef4444"
    emoji_status = f"<span class='pulse-dot' style='background:{cor_status};'></span>"
    texto_status = "Pregão ABERTO" if pregao_aberto else "Pregão FECHADO"
    
    col_a, col_b, col_c = st.columns([2, 3, 2])
    
    
    import streamlit.components.v1 as components
    
    with col_a:
    
        emoji_status = f"<span class='pulse-dot' style='background:{cor_status};margin-right:6px;'></span>"
    
        html_cabecalho = f"""
    <div style="padding:12px;border-radius:12px;background-color:rgba(17,24,39,0.75);border-left:6px solid {cor_status};color:white;">
    
    <h4 style="margin:0;display:flex;align-items:center;gap:6px;">
        {emoji_status} {texto_status}
    </h4>
    
    <small>
        <span style="color:white;">Horário do pregão: 10:00–18:00 (São Paulo)</span><br>
        <span style="color:#9ca3af;">13:00–21:00 (Lisboa) | 08:00–16:00 (New York)</span>
    </small>
    
    </div>
    """
    
        st.markdown(html_cabecalho, unsafe_allow_html=True)
    
    
    
    
    
    
    
    with col_b:
        st.markdown(
            f"""
            <div style="text-align:center;padding:8px 12px;color:#e5e7eb; line-height: 1.6;">
    
    
            <b>São Paulo:</b> {agora_br.strftime("%H:%M:%S")}
            <img src="https://flagcdn.com/w20/br.png"
                 style="vertical-align:middle;margin-left:4px;"><br>
    
            <b>Lisboa:</b> {agora_pt.strftime("%H:%M:%S")}
            <img src="https://flagcdn.com/w20/pt.png"
                 style="vertical-align:middle;margin-left:4px;"><br>      
    
            <b>New York:</b> {agora_ny.strftime("%H:%M:%S")}
            <img src="https://flagcdn.com/w20/us.png"
                 style="vertical-align:middle;margin-left:4px;">
    
            </div>
            """,
            unsafe_allow_html=True
        )
    
    
    
    with col_c:
        st.markdown(
            f"""
            <div style="text-align:right;padding:8px 12px;color:#9ca3af;">
                Última atualização: <b>{agora_pt.strftime("%d/%m %H:%M")}</b><br>
                <small>Fuso horário: {agora_pt.tzinfo}</small>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    
    # -------------------------------------------------
    # RESUMO GERAL
    # -------------------------------------------------
    total_apps = len(ROBOS)
    apps_ok = 0
    total_ativos = 0
    total_disparos = 0
    loaded_visual = {}
    sb_cache = {}
    
    historico_local = carregar_historico()
    disparos_por_robo = contar_disparos_por_robo(historico_local)
    
    for robo in ROBOS:
        state = None
        for f in robo["files"]:
            state = try_load_state(f)
            if state:
                break
        if state:
            loaded_visual[robo["key"]] = state
            s = summarize_visual_state(state)
        else:
            sb_url = st.secrets.get(robo["sb_url_secret"], "")
            sb_key = st.secrets.get(robo["sb_key_secret"], "")
            sb_v = ler_estado_supabase(sb_url, sb_key, robo["sb_table"], robo["sb_key"])
            sb_cache[robo["key"]] = sb_v
            s = summarize_supabase_state(sb_v)
        s["total_disparos"] = disparos_por_robo.get(robo["key"], 0)
        if s["ativos_monitorados"] or s["last_update"]:
            apps_ok += 1
        total_ativos += s["ativos_monitorados"]
        total_disparos += s.get("total_disparos", 0)
    
    #col1, col2, col3 = st.columns(3)
    #col1.metric("Robôs com dados", f"{apps_ok}/{total_apps}")
    #col2.metric("Ativos monitorados", total_ativos)
    #col3.metric("Disparos Recentes", total_disparos)
    #st.markdown("---")
    # -------------------------------------------------
    # ATUALIZAÇÃO DO HISTÓRICO LOCAL (busca no Supabase)
    # -------------------------------------------------
    #st.markdown("### 🛰️ Atualizando dados do Supabase...")
    
    # Recarrega sempre os dados mais recentes de todos os robôs
    novos_registros = 0
    for robo in ROBOS:
        robo_key = robo["key"]
        robo_nome = robo["title"]
    
        # leitura direta do Supabase (sem usar cache antigo)
        sb_url = st.secrets.get(robo["sb_url_secret"], "")
        sb_key = st.secrets.get(robo["sb_key_secret"], "")
        sb_v = ler_estado_supabase(sb_url, sb_key, robo["sb_table"], robo["sb_key"])
        if not sb_v or not isinstance(sb_v, dict):
            continue
    
        # tenta encontrar lista de disparos (ordem de prioridade)
        disparos = (
            sb_v.get("disparos")
            or sb_v.get("historico_alertas")
            or sb_v.get("eventos_enviados")
            or []
        )
        if not isinstance(disparos, list):
            continue
    
        # adiciona cada disparo ao histórico local, se ainda não existir
        for d in disparos:
            if not isinstance(d, dict):
                continue
            registro = {
                "robo": robo_key,
                "robo_nome": robo_nome,
                "ticker": d.get("ticker") or d.get("ativo") or "—",
                "operacao": d.get("operacao") or d.get("tipo") or "—",
                "alvo": d.get("preco_alvo") or d.get("alvo") or "—",
                "hora": d.get("hora") or datetime.datetime.now(TZ).isoformat(timespec="seconds"),
            }
    
            # evita duplicar (usa robo + ticker + hora como chave)
            if not any(
                r["robo"] == registro["robo"]
                and r["ticker"] == registro["ticker"]
                and r["hora"] == registro["hora"]
                for r in historico_local
            ):
                historico_local.append(registro)
                novos_registros += 1
    
    # salva novamente o histórico consolidado
    if novos_registros > 0:
        salvar_historico(historico_local)
        st.success(f"✅ {novos_registros} novos disparos adicionados ao histórico.")
    else:
        st.info("Nenhum novo disparo encontrado. Monitorando ...")
    
    
    # -------------------------------------------------
    # 🔁 Recalcula os disparos por robô após atualizar o histórico
    # -------------------------------------------------
    disparos_por_robo = contar_disparos_por_robo(historico_local)
    
    
    st.markdown("""
    <style>
    .pulse-dot {
        display:inline-block;
        width:10px;
        height:10px;
        border-radius:50%;
        animation:pulse 1.2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.6); opacity: 0.45; }
        100% { transform: scale(1); opacity: 1; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    
    # -------------------------------------------------
    # RENDERIZAÇÃO DOS CARDS
    # -------------------------------------------------
    def render_robot_card(robo, container):
        from datetime import datetime
        import dateutil.parser
    
        key = robo["key"]
        title = robo["title"]
        emoji = robo["emoji"]
    
        with container:
            visual = loaded_visual.get(key)
            sb_v = sb_cache.get(key)
    
            if sb_v is None and not visual:
                sb_url = st.secrets.get(robo["sb_url_secret"], "")
                sb_key = st.secrets.get(robo["sb_key_secret"], "")
                sb_v = ler_estado_supabase(sb_url, sb_key, robo["sb_table"], robo["sb_key"])
    
            # ---- resumo base ----
            summary = (
                summarize_visual_state(visual)
                if visual
                else summarize_supabase_state(sb_v or {})
            )
    
            # ------------------------------------------------------------
            # PATCH FINAL 🔥🔥🔥
            # Se TRADES PENDENTES não tiver last_update → usa agora()
            # ------------------------------------------------------------
            if summary.get("last_update") in (None, "", "-") and key == ROBOS[0]["key"]:
                summary["last_update"] = datetime.now()
    
            # ------------------------------------------------------------
            # Garantir que last_update seja datetime
            # ------------------------------------------------------------
            last_update = summary.get("last_update")
    
            if isinstance(last_update, str):
                try:
                    last_update = dateutil.parser.parse(last_update)
                except:
                    last_update = None
    
            summary["last_update"] = last_update
    
            summary["total_disparos"] = disparos_por_robo.get(key, 0)
    
            status_txt, color = badge_status_tempo(last_update)
    
            # ---- renderização visual ----
            st.markdown(
                f"""
                <div style="border-left:8px solid {color}; padding-left:12px; border-radius:8px;">
                  <h3>{emoji} {title}</h3>
                  <p>
                    <span class="pulse-dot" style="background:{color};margin-right:6px;"></span>
                    {status_txt} — Última atualização: <b>{nice_dt(summary['last_update'])}</b>
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    
            c1, c2 = st.columns(2)
            c1.metric("Ativos monitorados", summary["ativos_monitorados"])
            c2.metric("Disparos", summary.get("total_disparos", 0))
    
            tickers = summary["tickers"]
            if tickers:
                st.caption("Tickers: " + ", ".join(tickers))
    
    
            
    
    
    
    # =====================================================
    # 🟦 LAYOUT NOVO — UMA COLUNA (ORDEM FIXA)
    # =====================================================
    
    # =====================================================
    # 🟦 LAYOUT NOVO — UMA COLUNA COM ABAS POR CARTEIRA
    # =====================================================

    # ================================
    # 0) ESTADOS E PREÇOS (CURTO / LOSS CURTO)
    # ================================
    # 1) Carrega estado do Curto
    curto_state = load_state_curto()
    curto_tickers = [a.ticker for a in curto_state.ativos]

    # -----------------------------
    # INJETAR INDICE NOS OBJETOS DO CURTO
    # -----------------------------
    try:
        estado_supabase = sb_cache.get(ROBOS[0]["key"])
        if estado_supabase:
            mapa_indices = {
                item["ticker"].replace(".SA", "").upper(): item.get("indice", "").upper()
                for item in estado_supabase.get("ativos", [])
            }
            for a in curto_state.ativos:
                setattr(a, "indice", mapa_indices.get(a.ticker.upper(), ""))
    except Exception as e:
        print("Erro índice curto:", e)


    # 2) Preços do Curto
    quotes_curto = {}
    if curto_tickers:
        quotes_curto = fetch_quotes_yf(curto_tickers)

    # 3) Últimos sinais
    sinais = curto_state.last_signals or []
    ultimo_sinal = {s.ticker: s for s in sinais}

    # 4) Estado LOSS CURTO
    loss_state = load_state_loss_curto()
    loss_tickers = [a.ticker for a in loss_state.ativos]

    # -----------------------------
    # INJETAR INDICE NOS OBJETOS DO LOSS CURTO
    # -----------------------------
    try:
        estado_supabase = sb_cache.get(ROBOS[1]["key"])
        if estado_supabase:
            mapa_indices = {
                item["ticker"].replace(".SA", "").upper(): item.get("indice", "").upper()
                for item in estado_supabase.get("ativos", [])
            }
            for a in loss_state.ativos:
                setattr(a, "indice", mapa_indices.get(a.ticker.upper(), ""))
    except Exception as e:
        print("Erro índice loss:", e)


    

    loss_quotes = {}
    if loss_tickers:
        loss_quotes = fetch_quotes_yf(loss_tickers)

    # ================================
    # 0.1) Função de classificação do estado (Curto)
    # ================================
    def classificar_estado(a, preco_atual):
        if preco_atual <= 0:
            return "monitorando"
        preco_ref = a.preco
        s = ultimo_sinal.get(a.ticker)
        if s and s.direcao in ("compra", "venda"):
            return "ativada"
        if a.operacao == "compra" and preco_atual >= preco_ref:
            return "contagem"
        if a.operacao == "venda" and preco_atual <= preco_ref:
            return "contagem"
        return "monitorando"

    # ================================
    # 0.2) CSS dos cards
    # ================================
    st.markdown("""
    <style>
    .card-fenix {
        padding: 15px 18px;
        background: #0e1117;
        border: 1px solid #1f2937;
        border-radius: 10px;
        margin-bottom: 14px;
        min-height: 165px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .badge {
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 13px;
        font-weight:600;
        color:white;
    }
    @keyframes pulse {
        0% { transform:scale(1); opacity:1; }
        50% { transform:scale(1.5); opacity:0.5; }
        100% { transform:scale(1); opacity:1; }
    }
    .pulse-dot {
        display:inline-block;
        width:10px;
        height:10px;
        border-radius:50%;
        animation:pulse 1s infinite;
    }
    .pulse-yellow { background:#facc15; }
    .pulse-green { background:#22c55e; }
    </style>
    """, unsafe_allow_html=True)

    # ================================
    # CORES OFICIAIS DAS CARTEIRAS
    # ================================
    carteira_colors = {
        "IBOV": "#3B82F6",   # azul
        "SMLL": "#22C55E",   # verde
        "BDR":  "#EAB308",   # amarelo
        "": "#6B7280"        # fallback cinza
    }


    # ================================
    # 0.3) Helpers para renderizar cards
    # ================================

        # ================================
    # 0.3) Helper para descobrir o índice de cada ativo
    # ================================
    def get_indice_ativo(a) -> str:
        """
        Tenta extrair o índice/carteira do ativo em vários formatos possíveis
        e normaliza BBR -> BDR.
        """
        valor = None

        # caso seja um objeto (dataclass, etc.)
        for attr in ("indice", "indice_ticker", "index", "carteira"):
            if hasattr(a, attr):
                v = getattr(a, attr)
                if v:
                    valor = v
                    break

        # caso seja dict
        if valor is None and isinstance(a, dict):
            for k in ("indice", "indice_ticker", "index", "carteira"):
                if k in a and a[k]:
                    valor = a[k]
                    break

        if not valor:
            return ""

        val = str(valor).upper().strip()


        # ---------------------------
        # NORMALIZAÇÕES
        # ---------------------------
    
        # BDR
        if val in ("BBR", "BDR", "BDRX", "BDR11"):
            return "BDR"
    
        # IBOV
        if val in ("IBOV", "IBV", "IBX", "IBOV11"):
            return "IBOV"
    
        # SMLL
        if val in (
            "SMLL",
            "SMALL", 
            "SMAL", 
            "SML",
            "SMALL CAPS",
            "SMALLCAPS",
            "SMALL-CAPS",
            "SMALLCAP",
            "SMALLCAP11",
            "SMLL11"
        ):
            return "SMLL"
    
        return val  

    




    # ------------------------------------------------ #
    
    
    def render_pendentes_cards(ativos):
        if not ativos:
            st.info("Nenhum trade pendente nesta carteira.")
            return
    
        for a in ativos:
            ticker = a.ticker
            preco = quotes_curto.get(ticker, 0.0)
            estado = classificar_estado(a, preco)
            cor_ticker = get_ticker_color(ticker)
    
            # ----------------------------------------------------
            # NOVO: índice + cor da carteira (AQUI NÃO FALHA MAIS)
            # ----------------------------------------------------
            indice = get_indice_ativo(a)                  # IBOV / SMLL / BDR
            cor_indice = carteira_colors.get(indice, "#9ca3af")
    
            # Estado visual do robô (seu código original)
            if estado == "monitorando":
                badge = "#3b82f6"
                pulse = "<span class='pulse-dot pulse-yellow'></span>"
                txt = "MONITORANDO"
            elif estado == "contagem":
                badge = "#f59e0b"
                pulse = "<span class='pulse-dot pulse-green'></span>"
                txt = "EM CONTAGEM"
            else:
                badge = "#22c55e" if a.operacao == "compra" else "#ef4444"
                pulse = ""
                txt = "COMPRA ATIVADA" if a.operacao == "compra" else "VENDA ATIVADA"
    
            preco_fmt = f"R$ {preco:.2f}".replace(".", ",")
    
            # ----------------------------------------------------
            # HTML ORIGINAL — apenas trocamos o texto do topo
            # ----------------------------------------------------
            html = f"""
            <div class="card-fenix">
                <div style="color:{cor_indice};font-size:13px;margin-bottom:8px;font-weight:bold;">
                    {indice}
                </div>
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
                    <span style="background:{cor_ticker};color:white;padding:4px 12px;border-radius:8px;font-weight:bold;">
                        {ticker}
                    </span>
                    <span class="badge" style="background:{badge};">{txt}</span>
                    {pulse}
                </div>
                <div style="color:#e5e7eb;font-size:15px;">
                    Preço atual: <b>{preco_fmt}</b>
                </div>
                <div style="color:#9ca3af;font-size:13px;margin-top:4px;">
                    Operação: <b>{a.operacao.upper()}</b> ·
                    Preço Alvo: <b>{a.preco:.2f}</b>
                </div>
            </div>
            """
    
            st.markdown(html, unsafe_allow_html=True)






    # --------------------------------------------- #

    def render_andamento_cards(ativos_loss):
        """Renderiza cards do robô LOSS CURTO para uma lista de ativos."""
        if not ativos_loss:
            st.info("Nenhum trade em andamento nesta carteira.")
            return

        for a in ativos_loss:
            ticker = a.ticker
            preco_atual = loss_quotes.get(ticker, 0.0)
            cor_ticker = get_ticker_color(ticker)
            # ----------------------------------------------------
            # NOVO: índice + cor da carteira
            # ----------------------------------------------------
            indice = get_indice_ativo(a)                  # IBOV / SMLL / BDR
            cor_indice = carteira_colors.get(indice, "#9ca3af")

            # Estado do ativo
            estado = "monitorando"
            if preco_atual > 0:
                if a.operacao == "compra":
                    if preco_atual >= a.stop_gain or preco_atual <= a.stop_loss:
                        estado = "contagem"
                else:
                    if preco_atual <= a.stop_gain or preco_atual >= a.stop_loss:
                        estado = "contagem"

            if estado == "monitorando":
                estado_txt = "MONITORANDO"
                badge_cor = "#3b82f6"
                anima_html = "<span class='pulse-dot pulse-yellow'></span>"
            elif estado == "contagem":
                estado_txt = "EM CONTAGEM"
                badge_cor = "#f59e0b"
                anima_html = "<span class='pulse-dot pulse-green'></span>"
            else:
                estado_txt = "ATIVADO"
                badge_cor = "#ef4444"
                anima_html = ""

            preco_fmt = f"R$ {preco_atual:.2f}".replace(".", ",") if preco_atual > 0 else "-"

            # LUCRO / PREJUÍZO ATUAL (%)
            if preco_atual > 0 and a.preco_entrada > 0:
                lucro_pct = ((preco_atual / a.preco_entrada) - 1) * 100
            else:
                lucro_pct = 0.0

            if lucro_pct > 0:
                lucro_cor = "#10b981"  # verde
            elif lucro_pct < 0:
                lucro_cor = "#ef4444"  # vermelho
            else:
                lucro_cor = "#6b7280"  # cinza

            html = f"""
            <div class="card-fenix">
                <div style="color:{cor_indice};font-size:13px;margin-bottom:8px;font-weight:bold;">
                    {indice}
                </div>
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
                    <span style="background:{cor_ticker};color:white;padding:4px 12px;border-radius:8px;font-weight:bold;">
                        {ticker}
                    </span>
                    <span class="badge" style="background:{badge_cor}">{estado_txt}</span>
                    {anima_html}
                    <span style="background:{lucro_cor};color:white;padding:4px 10px;border-radius:8px;font-size:12px;font-weight:bold;">
                        {lucro_pct:+.2f}%
                    </span>
                </div>
                <div style="color:#e5e7eb;font-size:15px;">
                    Preço atual: <b>{preco_fmt}</b>
                </div>
                <div style="color:#9ca3af;font-size:13px;margin-top:6px;">
                    Entrada: <b>{a.preco_entrada:.2f}</b> · 
                    Stop Gain: <b>{a.stop_gain:.2f}</b> · 
                    Stop Loss: <b>{a.stop_loss:.2f}</b>
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)



    # _____________ #

    # --------------------------------------------- #
    
    def render_resumo_30d(indice_atual):
    
        st.markdown("---")
        st.markdown(f"### 🦅 Resumo de Desempenho — Últimos 30 dias ({indice_atual})")
    
        hoje = datetime.date.today()
        inicio_30d = hoje - datetime.timedelta(days=30)
    
        dados_30d = supabase_select(
            "operacoes_encerradas",
            f"?select=*"
            f"&data_fechamento=gte.{inicio_30d}T00:00:00"
            f"&data_fechamento=lte.{hoje}T23:59:59"
        )
    
        # -------- FILTRO POR CARTEIRA --------
        def filtrar_por_indice(lista, indice):
            if indice == "TOTAL":
                return lista
            out = []
            for x in lista:
                idx = (
                    x.get("indice") or
                    x.get("carteira") or
                    x.get("index") or
                    x.get("indice_ticker")
                )
                idx_norm = get_indice_ativo({"indice": idx})
                if idx_norm == indice:
                    out.append(x)
            return out
    
        dados_30d_filtrado = filtrar_por_indice(dados_30d, indice_atual)
    
        # converter datas
        for x in dados_30d_filtrado:
            try:
                x["data_abertura"] = datetime.datetime.fromisoformat(x["data_abertura"])
                x["data_fechamento"] = datetime.datetime.fromisoformat(x["data_fechamento"])
            except:
                pass
    
        if not dados_30d_filtrado:
            st.info("Nenhuma operação encerrada nos últimos 30 dias.")
            return
    
        pnls = [x["pnl"] for x in dados_30d_filtrado if x["pnl"] is not None]
        lucros = [p for p in pnls if p > 0]
        preju = [p for p in pnls if p < 0]
        neutras = [p for p in pnls if p == 0]
    
        lucro_total_pct = 0
        pct_lucros = []
    
        for x in dados_30d_filtrado:
            if x["pnl"] and x["preco_abertura"]:
                pct = (x["pnl"] / x["preco_abertura"]) * 100
                lucro_total_pct += pct
                if pct > 0:
                    pct_lucros.append(pct)
    
        media_pct_vencedoras = sum(pct_lucros) / len(pct_lucros) if pct_lucros else 0
    
        dur_list = [x.get("dur_days") for x in dados_30d_filtrado if x.get("dur_days") is not None]
        media_dias = sum(dur_list) / len(dur_list) if dur_list else 0
    
        def card_cor(v):
            if v > 0: return "#22c55e"
            if v < 0: return "#ef4444"
            return "#e5e7eb"
    
        def card(titulo, valor, sufixo="%", casas=2, cor_forcada=None):
            cor = cor_forcada if cor_forcada else card_cor(valor)
            st.markdown(
                f"""
                <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                            background-color:rgba(17,24,39,0.9);
                            border-left:6px solid {cor};color:white;">
                    <b style="color:#9ca3af;">{titulo}</b><br>
                    <span style="font-size:1.9em;color:{cor};font-weight:bold;">
                        {valor:.{casas}f}{sufixo}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
    
        colA, colB, colC = st.columns(3)
        with colA:
            card("Lucro total",  lucro_total_pct)
            card("Lucros", len(lucros), sufixo="", casas=0)
        with colB:
            card("Média vencedoras", media_pct_vencedoras)
            card("Prejuízos", len(preju), sufixo="", casas=0, cor_forcada="#ef4444")
        with colC:
            card("Operações neutras", len(neutras), sufixo="", casas=0, cor_forcada="#ffffff")
            card("Média dias", media_dias, sufixo="", casas=2)

        # ========================
        # ========================
        # CARDS 7, 8 e 9 — ADICIONADOS LOGO ABAIXO DOS 6 ORIGINAIS
        # ========================
        
        # Stop Loss médio (somente perdas)
        pnl_percentuais = [
            (x["pnl"] / x["preco_abertura"]) * 100
            for x in dados_30d_filtrado
            if x["pnl"] and x["preco_abertura"]
        ]
        
        perdas_pct = [p for p in pnl_percentuais if p < 0]
        media_stop_loss_pct = (sum(perdas_pct) / len(perdas_pct)) if perdas_pct else 0.0
        
        # Rentabilidade por fluxo de capital
        rent_fluxo_capital = lucro_total_pct / 4 if lucro_total_pct else 0.0
        
        # Operação mais lucrativa (estrutura mantida)
        op_mais_lucr = None
        if dados_30d_filtrado:
            op_mais_lucr = max(
                (x for x in dados_30d_filtrado if x["pnl"] and x["preco_abertura"]),
                key=lambda x: (x["pnl"] / x["preco_abertura"]),
                default=None
            )
        
        # ========================
        # CARDS ESPECIAIS CORRIGIDOS
        # ========================
        c7, c8, c9 = st.columns(3)
        
        # -----------------------------
        # CARD 7 – Média de Stop Loss
        # -----------------------------
        with c7:
            card("Média de Stop Loss", media_stop_loss_pct)
        
        
        # -----------------------------
        # CARD 8 – Rentabilidade por Fluxo
        # -----------------------------
        with c8:
            card("Rentabilidade por Fluxo de Capital", rent_fluxo_capital)
        
        
        # -----------------------------
        # CARD 9 – Operação mais lucrativa (COM TICKER)
        # -----------------------------
        with c9:
            if op_mais_lucr:
        
                pct_op = (op_mais_lucr["pnl"] / op_mais_lucr["preco_abertura"]) * 100
                ticker = op_mais_lucr["ticker"]
        
                # estilo preserve a borda e lógica do card(), mas substitui o conteúdo interno
                cor_op = card_cor(pct_op)
        
                st.markdown(
                    f"""
                    <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                                background-color:rgba(17,24,39,0.9);
                                border-left:6px solid {cor_op};color:white;">
                        <b style="color:#9ca3af;">Operação mais lucrativa</b><br>
                        <span style="color:white;font-weight:bold;font-size:1.7em;">{ticker}</span>
                        <span style="font-size:1.9em;color:{cor_op};font-weight:bold;">
                            &nbsp;{pct_op:.2f}%
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                card("Operação mais lucrativa", 0)



    
        # ========================
        # GRÁFICO
        # ========================
        st.markdown("---")
        st.markdown("#### ⭐ Gráfico dos Resultados dos últimos 30 dias")
    
        df_chart = []
        for x in dados_30d_filtrado:
            if x["pnl"] and x["preco_abertura"]:
                df_chart.append({
                    "Ticker": x["ticker"],
                    "PnL_pct": (x["pnl"] / x["preco_abertura"]) * 100
                })
    
        if df_chart:
            df_chart = (
                pd.DataFrame(df_chart)
                .groupby("Ticker", as_index=False)["PnL_pct"]
                .mean()
                .sort_values("PnL_pct", ascending=False)
            )
    
            colors = [
                "rgba(34,197,94,0.85)" if v > 0 else "rgba(239,68,68,0.85)"
                for v in df_chart["PnL_pct"]
            ]
    
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_chart["Ticker"],
                y=df_chart["PnL_pct"],
                marker=dict(color=colors),
                text=[f"{v:.2f}%" for v in df_chart["PnL_pct"]],
                textposition="outside"
            ))
    
            fig.update_layout(template="plotly_dark", height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para exibir no gráfico.")
    
        # -------------- RESUMO POR CARTEIRA --------------
        # ---------------- RESUMO POR CARTEIRA (somente TOTAL) --------------
        if indice_atual == "TOTAL":
        
            # 🔥 Título aprimorado
            st.markdown("""
            <div style="
                font-size:22px;
                font-weight:700;
                margin-top:25px;
                margin-bottom:10px;
                display:flex;
                align-items:center;
                gap:10px;
                color:#e5e7eb;
            ">
                <span style="font-size:26px;">🔥</span>
                Resumo por Carteira <small style="color:#9ca3af;"></small>
            </div>
            """, unsafe_allow_html=True)
        
            # Cores oficiais igual às abas
            cores = {
                "IBOV": "#3B82F6",
                "SMLL": "#22C55E",
                "BDR":  "#EAB308"
            }
        
            indices = ["IBOV", "SMLL", "BDR"]
        
            for idx in indices:
        
                subset = [
                    x for x in dados_30d_filtrado
                    if get_indice_ativo({"indice": x.get("indice")}) == idx
                ]
        
                if not subset:
                    continue
        
                # ---- métricas ----
                lucro_total_pct = sum(
                    (x["pnl"] / x["preco_abertura"]) * 100
                    for x in subset if x["pnl"] and x["preco_abertura"]
                )
        
                ops_lucro = [
                    x for x in subset
                    if x["pnl"] and x["pnl"] > 0
                ]
        
                dias = [x.get("dur_days") for x in subset if x.get("dur_days")]
        
                # operação mais lucrativa
                op_melhor = None
                if subset:
                    op_melhor = max(
                        (x for x in subset if x["pnl"] and x["preco_abertura"]),
                        key=lambda x: (x["pnl"] / x["preco_abertura"]),
                        default=None
                    )
        
                # ---- Cabeçalho (com quadradinho colorido) ----
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:10px;
                                margin-top:18px;margin-bottom:5px;">
                        <span style="display:inline-block;width:14px;height:14px;
                                     border-radius:3px;background:{cores[idx]};"></span>
                        <span style="font-size:18px;font-weight:600;color:#e5e7eb;">
                            Carteira {idx}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        
                # ---- Cards ----
                # ---- Cards ----
                c1, c2, c3 = st.columns(3)
                
                # ==========================
                # COR DA BORDA POR CARTEIRA
                # ==========================
                cores_borda = {
                    "IBOV": "#3B82F6",   # azul
                    "SMLL": "#22C55E",   # verde
                    "BDR":  "#EAB308",   # amarelo
                }
                cor_borda = cores_borda.get(idx, "#3B82F6")  # fallback azul
                # ==========================
                
                
                # ---------- CARD 1 ----------
                with c1:
                    st.markdown(
                        f"""
                        <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                                    background-color:rgba(17,24,39,0.9);
                                    border-left:6px solid {cor_borda};color:white;">
                            <b style="color:#9ca3af;">{idx} — Lucro total</b><br>
                            <span style="font-size:1.9em;color:{card_cor(lucro_total_pct)};font-weight:bold;">
                                {lucro_total_pct:.2f}%
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                
                # ---------- CARD 2 ----------
                with c2:
                    st.markdown(
                        f"""
                        <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                                    background-color:rgba(17,24,39,0.9);
                                    border-left:6px solid {cor_borda};color:white;">
                            <b style="color:#9ca3af;">{idx} — Operações com lucro</b><br>
                            <span style="font-size:1.9em;color:{card_cor(len(ops_lucro))};font-weight:bold;">
                                {len(ops_lucro)}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                
                # ---------- CARD 3 (OPERAÇÃO MAIS LUCRATIVA) ----------
                with c3:
                    if op_melhor:
                
                        pct_op = (op_melhor["pnl"] / op_melhor["preco_abertura"]) * 100
                        ticker = op_melhor["ticker"]
                        cor_valor = card_cor(pct_op)
                
                        st.markdown(
                            f"""
                            <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                                        background-color:rgba(17,24,39,0.9);
                                        border-left:6px solid {cor_borda};color:white;">
                                <b style="color:#9ca3af;">Operação mais lucrativa</b><br>
                                <span style="color:white;font-weight:bold;font-size:1.4em;">
                                    {ticker}
                                </span>
                                <span style="font-size:1.9em;color:{cor_valor};font-weight:bold;">
                                    &nbsp;{pct_op:.2f}%
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                
                    else:
                        st.markdown(
                            f"""
                            <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                                        background-color:rgba(17,24,39,0.9);
                                        border-left:6px solid {cor_borda};color:white;">
                                <b style="color:#9ca3af;">Operação mais lucrativa</b><br>
                                <span style="font-size:1.9em;color:white;font-weight:bold;">
                                    0%
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )




    # ---------------- GRÁFICO ----------------


    

    # =====================================================================
    # ABAS POR CARTEIRA (TOTAL, IBOV, SMLL, BDR)
# =====================================================================
# PAINEL EXCLUSIVO – CARTEIRA SMLL (Small Caps)
# =====================================================================

aba_smll, = st.tabs(["🟩 SMLL"])

with aba_smll:
    st.session_state["active_tab"] = "SMLL"

    st.markdown("### 🟩 Carteira SMLL")

    # Apenas ativos com índice == SMLL
    pend_smll = [a for a in curto_state.ativos if get_indice_ativo(a) == "SMLL"]
    and_smll  = [a for a in loss_state.ativos  if get_indice_ativo(a) == "SMLL"]

    st.markdown("#### ⚡ Trades Pendentes (SMLL)")
    render_pendentes_cards(pend_smll)

    st.markdown("---")
    st.markdown("#### ⭐ Trades em Andamento (SMLL)")
    render_andamento_cards(and_smll)

    # 🔥 RESUMO 30 DIAS — SMLL
    render_resumo_30d("SMLL")



    
    
    
    
    # ============================================================
    #  RESUMO CONSOLIDADO — CÓPIA (ÚLTIMOS 30 DIAS AUTOMÁTICO)
    
    # ================================
    # Função para filtrar resultados por carteira
    # ================================
    def filtrar_por_indice(lista, indice):
        if indice == "TOTAL":
            return lista
        return [x for x in lista if get_indice_ativo(x) == indice or x.get("indice") == indice]



    # ============================================================

    st.markdown("---")
    
    # Card + botão dentro do card
    st.markdown("""
    <style>
    /* ===== Animação da Águia ===== */
    @keyframes flap {
        0%   { transform: scale(1) translateY(0); }
        50%  { transform: scale(1.08) translateY(-3px); }
        100% { transform: scale(1) translateY(0); }
    }
    
    .eagle-anim {
        display:inline-block;
        animation: flap 1.4s ease-in-out infinite;
    }
    
    /* ===== Texto com gradiente ===== */
    .gradient-text {
        background: linear-gradient(90deg, #fbbf24, #f97316, #ef4444);
        -webkit-background-clip: text;
        color: transparent;
        font-weight: 900;
    }
    
    /* ===== Card com borda brilhando ===== */
    .phoenix-box {
        padding:20px;
        background-color:#111827;
        border-radius:12px;
        margin-bottom:22px;
        border:2px solid #f97316;
        box-shadow:0 0 10px rgba(249,115,22,0.8), 0 0 25px rgba(249,115,22,0.5);
    }
    
    /* ===== Texto interno ===== */
    .phoenix-subtext {
        color:#d1d5db;
        font-size:25px;
        line-height:1.55;
    
        /* CENTRALIZAÇÃO */
        display:block;
        width:100%;
        text-align:center;
        margin-left:auto;
        margin-right:auto;
    }
    </style>
    
    <div class="phoenix-box">
    
      <h1 style="
          margin:0;
          text-align:center;
          font-size:34px;
          display:flex;
          justify-content:center;
          align-items:center;
          gap:12px;
      ">
        <span class="eagle-anim">🦅</span>
        <span class="gradient-text">Estratégia Phoenix</span>
        <span class="eagle-anim">🦅</span>
      </h1>
    
      <p class="phoenix-subtext">
        A Estratégia Phoenix é um modelo quantitativo de seleção de ações baseado em cinco pilares:
        <b>tendência</b>, <b>momentum</b>, <b>volatilidade</b>, <b>força relativa</b> e <b>fluxo/volume</b>.
        Esses fatores compõem o <b>Score Phoenix</b>, responsável por definir a carteira oficial <b>Phoenix</b>.
      </p>
    
      <p class="phoenix-subtext" style="margin-bottom:18px;">
        Para conhecer todos os critérios, fórmulas, lógica estatística e integração com os robôs,
        baixe o <b>Whitepaper Oficial</b> abaixo.
      </p>
    
    </div>
    """, unsafe_allow_html=True)


    
    # Botão dentro do card
    pdf_path = "Whitepaper_Projeto_Fenix.pdf"
    
    try:
        with open(pdf_path, "rb") as f:
            st.download_button(
                "📄 Baixar Whitepaper Oficial – Estratégia Phoenix",
                f,
                file_name="Whitepaper_Projeto_Fenix.pdf",
                mime="application/pdf",
                key="whitepaper_fenix_inside",
            )
    except:
        st.error("❌ Arquivo 'Whitepaper_Projeto_Fenix.pdf' não encontrado.")
    
    
    # ----------- relatorios e documentos

# ============================
# BLOCO DE RELATÓRIOS (ABA LATERAL)
# ============================
if secao == "Relatórios":
      

    # 🔥 Garantir que historico_local é SEMPRE lista
    if not isinstance(historico_local, list):
        historico_local = []   
    



    st.markdown("---")
    
    
    st.markdown("""
    <div style="
        padding:18px 20px;
        border-left:6px solid #facc15;      /* 🔥 amarelo */
        background-color:#111827;
        border-radius:10px;
        margin-bottom:18px;                 /* 🔥 espaço antes do expander */
    ">
        <h2 style='margin:0; color:#e5e7eb; display:flex; align-items:center; gap:10px;'>
            📒 Relatórios e Documentos
        </h2>
        <p style='margin:0; margin-top:6px; color:#9ca3af;'>
            Acesso aos relatórios oficiais, exportações e documentos operacionais.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    
    st.markdown("---")

    # ============================================================
    # 🔄 RECUPERAR DISPAROS DIRETAMENTE DO SUPABASE (curto + loss_curto)
    # ============================================================
    
    def puxar_disparos_supabase():
        registros = []
    
        for robo in ROBOS:
            sb_url = st.secrets.get(robo["sb_url_secret"], "")
            sb_key = st.secrets.get(robo["sb_key_secret"], "")
            tabela = robo["sb_table"]
            chave = robo["sb_key"]
    
            if not sb_url or not sb_key:
                continue
    
            endpoint = f"{sb_url}/rest/v1/{tabela}?select=v&k=eq.{chave}"
            headers = {
                "apikey": sb_key,
                "Authorization": f"Bearer {sb_key}",
            }
    
            try:
                r = requests.get(endpoint, headers=headers, timeout=10)
                r.raise_for_status()
                data = r.json()
    
                if not data:
                    continue
    
                v = data[0].get("v", {})
    
                lista = (
                    v.get("disparos")
                    or v.get("historico_alertas")
                    or v.get("eventos_enviados")
                    or []
                )
    
                for item in lista:
                    if not isinstance(item, dict):
                        continue
    
                    registro = {
                        "robo": robo["key"],
                        "robo_nome": robo["title"],
                        "ticker": item.get("ticker") or item.get("ativo") or "—",
                        "operacao": item.get("operacao") or item.get("tipo") or "—",
                        "alvo": item.get("preco_alvo") or item.get("alvo") or "—",
                        "hora": item.get("hora") or
                                item.get("timestamp") or
                                item.get("data") or None,
                    }
    
                    if registro["hora"]:
                        registros.append(registro)
    
            except Exception as e:
                print("Erro ao puxar disparos do Supabase:", e)
    
        return registros
    
    
    # ============================================================
    # 🔄 CARREGA O HISTÓRICO DIRETAMENTE DO SUPABASE
    # ============================================================
    historico_local = puxar_disparos_supabase()


    
    
    
    # -------------------------------------------------
    # HISTÓRICO DE DISPAROS (EXIBIÇÃO)
    # -------------------------------------------------
    with st.expander("📜 Histórico de Disparos", expanded=False):
        #st.markdown("## 📜 Histórico de Disparos")    
        
        # cria lista de robôs a partir da definição global (todos os existentes)
        #robos_disponiveis = [r["key"] for r in ROBOS]
        #mapa_nomes = {r["key"]: r["title"] for r in ROBOS}
        #opcoes = ["Todos"] + [mapa_nomes[k] for k in robos_disponiveis]
        #robo_sel_nome = st.selectbox("Filtrar por robô", opcoes, index=0)
        
        # converte nome amigável de volta para key interna
        #if robo_sel_nome == "Todos":
            #robo_sel = "Todos"
        #else:
            #robo_sel = next((k for k, v in mapa_nomes.items() if v == robo_sel_nome), None)
        
        # -------------------------------------------------
        # FILTRO POR DATA (início e fim)
        # -------------------------------------------------
        st.markdown("### 🗓️ Filtro por Data dos Disparos")
        
        if historico_local:
            datas = []
            for r in historico_local:
                try:
                    datas.append(datetime.datetime.fromisoformat(str(r["hora"])).date())
                except Exception:
                    continue
            if datas:
                min_data, max_data = min(datas), max(datas)
            else:
                min_data, max_data = datetime.date.today(), datetime.date.today()
        else:
            min_data = max_data = datetime.date.today()
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            data_inicio = st.date_input("Data inicial", value=min_data, min_value=min_data, max_value=max_data)
        with col_d2:
            data_fim = st.date_input("Data final", value=max_data, min_value=min_data, max_value=max_data)
        
        # -------------------------------------------------
        # BOTÕES DE LIMPEZA
        # -------------------------------------------------
        col_l, col_r = st.columns([3, 1])
        with col_r:
            # 🔒 Botão desativado — comentado para evitar remoção acidental do histórico.
            # Basta remover os comentários abaixo no futuro se quiser reativar.
        
            # if st.button("🧹 Limpar histórico selecionado"):
            #     if robo_sel == "Todos":
            #         salvar_historico([])
            #         st.success("Histórico completo limpo!")
            #     else:
            #         historico_local = [r for r in historico_local if r["robo"] != robo_sel]
            #         salvar_historico(historico_local)
            #         st.success(f"Histórico do robô '{robo_sel}' limpo!")
            #     st.experimental_rerun()
        
            pass   # 👈 NECESSÁRIO — evita o IndentationError
    
    
        # -------------------------------------------------
        # FILTRAGEM DOS DADOS
        # -------------------------------------------------
        dados_filtrados = historico_local
        
        # filtro por robô
        #if robo_sel and robo_sel != "Todos":
            #dados_filtrados = [r for r in dados_filtrados if r["robo"] == robo_sel]
        
        # filtro por data
        def dentro_intervalo(r):
            try:
                data_r = datetime.datetime.fromisoformat(str(r["hora"])).date()
                return data_inicio <= data_r <= data_fim
            except Exception:
                return False
        
        dados_filtrados = [r for r in dados_filtrados if dentro_intervalo(r)]
        
        # -------------------------------------------------
        # EXIBIÇÃO FINAL DA TABELA
        # -------------------------------------------------
        if dados_filtrados:
            df = pd.DataFrame(dados_filtrados)
            df["hora_fmt"] = df["hora"].apply(
                lambda x: datetime.datetime.fromisoformat(str(x)).strftime("%d/%m %H:%M")
                if " " in str(x) or "T" in str(x) else x
            )
            df = df[["ticker", "operacao", "alvo", "hora_fmt"]]
            df.columns = ["Ticker", "Operação", "Alvo", "Hora"]
        
            st.dataframe(
                df.sort_values("Hora", ascending=False),
                use_container_width=True,
                hide_index=True,
            )
        else:
                st.info("Nenhum disparo encontrado dentro dos filtros selecionados.")
    
    
    
    
    # =================================================
    # OPERAÇÕES ENCERRADAS NO PERÍODO (ABA SEPARADA)
    # =================================================
    st.markdown("---")
    with st.expander("🌀 Relatório Consolidado de Operações Encerradas (Selecione o período desejado)", expanded=False):
    
        tabs = st.tabs(["🧾 Relatório Consolidado"])
        
        with tabs[0]:
            st.markdown("🌀 RELATÓRIO CONSOLIDADO")
    
            # ==================================
            # 🔵 FILTRO DE CARTEIRA (ÍNDICE)
            # ==================================
            opcoes_indice = ["Todas", "IBOV", "SMLL", "BDR"]
            indice_sel = st.selectbox("Filtrar por carteira (índice)", opcoes_indice, index=0)
    
        
            # -------------------------------
            # MAPEAMENTOS E FUNÇÕES AUXILIARES
            # -------------------------------
            BASE_TO_LOSS = {
                "curto": "loss_curto",
                "curtissimo": "loss_curtissimo",
                "clube": "loss_clube",
            }
            LOSS_TO_BASE = {v: k for k, v in BASE_TO_LOSS.items()}
        
            def parse_iso(dt):
                try:
                    return datetime.datetime.fromisoformat(str(dt))
                except Exception:
                    return None
        
            def parse_float(x):        
                """
                Converte string/numero em float.
                Aceita: '49.27', '49,27', ' R$ 49,27 ', '--', '—', '', None.
                Retorna None se não der pra converter.
                """
                if x is None:
                    return None
                if isinstance(x, (int, float)):
                    return float(x)
                s = str(x).strip()
                if s in {"", "-", "—", "--", "nan", "None"}:
                    return None
                s = s.replace("R$", "").replace("%", "").replace(" ", "")
                s = s.replace(",", ".")
                try:
                    return float(s)
                except Exception:
                    return None
        
        
        
            def direcao_op(op_str):
                s = (op_str or "").strip().upper()
                if "COMPRA" in s:
                    return "COMPRA"
                if "VENDA" in s:
                    return "VENDA"
                return None
        
            def pnl_from_ops(op_open, preco_open, op_close, preco_close):
                """Long: COMPRA->VENDA = close - open ; Short: VENDA->COMPRA = open - close"""
                if preco_open is None or preco_close is None:
                    return None
                if op_open == "COMPRA" and op_close == "VENDA":
                    return preco_close - preco_open
                if op_open == "VENDA" and op_close == "COMPRA":
                    return preco_open - preco_close
                # direções estranhas/iguais -> sem PnL
                return None
    
            # ================================
            # ABERTAS: Busca STOP nos robôs LOSS e monta posições abertas
            # ================================
            
            def _get_robo_cfg_by_key(robo_key: str) -> Optional[dict]:
                """Retorna metadados de um robô (inclui secrets) a partir de ROBOS."""
                cfg = next((r for r in ROBOS if r["key"] == robo_key), None)
                if not cfg:
                    return None
                return {
                    "sb_url": st.secrets.get(cfg["sb_url_secret"], ""),
                    "sb_key": st.secrets.get(cfg["sb_key_secret"], ""),
                    "sb_table": cfg["sb_table"],
                    "sb_k": cfg["sb_key"],
                    "title": cfg["title"],
                    "key": cfg["key"],
                }
            
            def _loss_state_for_base(base_key: str) -> Optional[Dict[str, Any]]:
                """Lê o estado KV do robô LOSS associado a um robô base (curto, curtissimo, clube)."""
                loss_key = BASE_TO_LOSS.get(base_key)
                if not loss_key:
                    return None
                rcfg = _get_robo_cfg_by_key(loss_key)
                if not rcfg:
                    return None
                return ler_estado_supabase(rcfg["sb_url"], rcfg["sb_key"], rcfg["sb_table"], rcfg["sb_k"])
            
            def _guess_stop_from_loss_sb(sb_v: Dict[str, Any], ticker: str) -> Optional[float]:
                """
                Procura o preço STOP dentro do KV do robô LOSS correspondente ao ticker.
                Tenta chaves comuns: 'stop', 'preco_stop', 'alvo_loss', 'preco', 'alvo'.
                """
                if not isinstance(sb_v, dict):
                    return None
                ativos = sb_v.get("ativos") or []
                t_up = (ticker or "").upper().strip()
                for a in ativos:
                    if not isinstance(a, dict):
                        continue
                    t = (a.get("ticker") or a.get("ativo") or "").upper().strip()
                    if t != t_up:
                        continue
                    for k in ("stop", "preco_stop", "alvo_loss", "preco", "alvo", "stop_loss"):
                        v = a.get(k)
                        val = parse_float(v)
                        if val is not None:
                            return val
                return None
            
    
            def _coletar_operacoes_abertas_por_base(base_sel: Optional[str] = None) -> list:
                """
                Monta as operações ABERTAS cruzando:
                  - LOSS (kv_state_loss*)  -> lista de posições vivas + STOP
                  - BASE (kv_state_*)      -> operação e PREÇO DE ABERTURA
                  - historico_local        -> DATA DE ABERTURA (último disparo do robô base)
                Retorna itens no formato esperado por _enriquecer_abertas_com_stop_e_pnl().
                """
                from datetime import datetime
            
                # mapeia nomes bonitos
                mapa_nomes = {r["key"]: r["title"] for r in ROBOS}
            
                BASE_TO_LOSS = {
                    "curto": "loss_curto",
                    "curtissimo": "loss_curtissimo",
                    "clube": "loss_clube",
                }
            
                def _cfg(key: str):
                    cfg = next((r for r in ROBOS if r["key"] == key), None)
                    if not cfg:
                        return None
                    return {
                        "sb_url": st.secrets.get(cfg["sb_url_secret"], ""),
                        "sb_key": st.secrets.get(cfg["sb_key_secret"], ""),
                        "sb_table": cfg["sb_table"],
                        "sb_k": cfg["sb_key"],
                    }
            
                bases = [base_sel] if (base_sel in BASE_TO_LOSS) else list(BASE_TO_LOSS.keys())
            
                abertas = []
                for base_key in bases:
                    loss_key = BASE_TO_LOSS[base_key]
            
                    # --- lê estados do KV (BASE e LOSS)
                    base_cfg = _cfg(base_key)
                    loss_cfg = _cfg(loss_key)
                    sb_base = ler_estado_supabase(base_cfg["sb_url"], base_cfg["sb_key"], base_cfg["sb_table"], base_cfg["sb_k"]) if base_cfg else {}
                    sb_loss = ler_estado_supabase(loss_cfg["sb_url"], loss_cfg["sb_key"], loss_cfg["sb_table"], loss_cfg["sb_k"]) if loss_cfg else {}
            
                    # normaliza dicionários por ticker
                    base_map = {}
                    for a in (sb_base.get("ativos") or []):
                        try:
                            t = (a.get("ticker") or a.get("ativo") or "").upper().strip()
                            op = (a.get("operacao") or "").upper().strip()
                            pr = parse_float(a.get("preco"))
                            if t and op in ("COMPRA", "VENDA"):
                                base_map[t] = {"operacao": op, "preco_abertura": pr}
                        except:
                            continue
            
                    loss_map = {}
                    for a in (sb_loss.get("ativos") or []):
                        try:
                            t = (a.get("ticker") or a.get("ativo") or "").upper().strip()
                            stop = parse_float(a.get("preco") or a.get("stop") or a.get("alvo"))
                            if t and stop is not None:
                                loss_map[t] = {"preco_stop": stop}
                        except:
                            continue
            
                    # universo de tickers em aberto: os que têm STOP no LOSS
                    # --------------------------------------------------------------------
                    # 🔎 BANNER INTELIGENTE — ORIGEM DOS DADOS (Supabase vs Local)
                    # --------------------------------------------------------------------
                    usou_base = len(base_map) > 0
                    usou_loss = len(loss_map) > 0
                    tem_local = bool(historico_local)
                    
                    # CASO 1 → Tudo supabase (ideal)
                    if usou_base and usou_loss:
                        st.success(f"🟢 Dados carregados 100% do Supabase para o robô **{mapa_nomes.get(base_key, base_key)}**")
                    
                    # CASO 2 → STOP do Supabase, abertura via histórico local (fallback)
                    elif (not usou_base) and usou_loss and tem_local:
                        st.warning(f"🟠 Aberturas recuperadas do histórico local (fallback). STOP do Supabase para **{mapa_nomes.get(base_key, base_key)}**")
                    
                    # CASO 3 → Dados ausentes / falha supabase
                    else:
                        st.error(f"🔴 Dados insuficientes no Supabase para o robô **{mapa_nomes.get(base_key, base_key)}**")
    
                    tickers_abertos = list(loss_map.keys())
            
                    # para cada ticker, tenta recuperar operação/entrada da BASE,
                    # e data de abertura do historico_local
                    for tk in tickers_abertos:
                        op_ab = (base_map.get(tk, {}).get("operacao") or "").upper()
                        preco_ab = base_map.get(tk, {}).get("preco_abertura")
                        # fallback: tenta extrair do histórico local (último disparo do robô base)
                        dt_ab = None
                        if historico_local:
                            candidatos = [
                                r for r in historico_local
                                if r.get("robo") == base_key and (r.get("ticker") or "").upper().strip() == tk
                            ]
                            # mais recente
                            candidatos.sort(key=lambda r: r.get("hora") or "", reverse=True)
                            for r in candidatos:
                                op_hist = direcao_op(r.get("operacao"))
                                if op_ab in ("COMPRA", "VENDA") and op_hist and op_hist != op_ab:
                                    continue
                                # data/hora
                                dt_ab = parse_iso(r.get("hora"))
                                # preço de abertura se ainda não tenho
                                if preco_ab is None:
                                    preco_ab = (
                                        parse_float(r.get("alvo"))
                                        or parse_float(r.get("preco_alvo"))
                                        or parse_float(r.get("preco"))
                                        or parse_float(r.get("valor"))
                                    )
                                # operação se faltou na BASE
                                if op_ab not in ("COMPRA", "VENDA") and op_hist:
                                    op_ab = op_hist
                                if dt_ab:
                                    break  # achou um bom candidato
            
                        # se ainda faltam campos críticos, ignora
                        if op_ab not in ("COMPRA", "VENDA") or preco_ab is None:
                            # não consigo calcular PnL sem direção + preço de abertura
                            continue
            
                        abertas.append({
                            "robo_base": base_key,
                            "robo_nome_base": mapa_nomes.get(base_key, base_key),
                            "ticker": tk,
                            "op_abertura": op_ab,
                            "preco_abertura": preco_ab,
                            # usa a melhor data encontrada; se não achou, deixa None (Dias vira None)
                            "data_abertura": dt_ab,
                            # já carregamos o STOP aqui (evita outra ida ao KV)
                            "preco_stop": loss_map[tk]["preco_stop"],
                        })
            
                return abertas
    
    
    
    
    
    
    
            
            def _enriquecer_abertas_com_stop_e_pnl(abertas: list) -> list:
                """
                Recebe abertas com: robo_base, ticker, op_abertura, preco_abertura, data_abertura, (opcional) preco_stop.
                Calcula:
                  - pnl: usando o STOP como preço de fechamento hipotético
                  - dur_days: dias corridos desde a data de abertura
                """
                out = []
                for a in abertas:
                    stop = a.get("preco_stop")
                    # se por algum motivo não veio, tenta buscar no LOSS correspondente
                    if stop is None:
                        loss_key = BASE_TO_LOSS.get(a["robo_base"])
                        if loss_key:
                            rcfg = _get_robo_cfg_by_key(loss_key)
                            sb_v = ler_estado_supabase(rcfg["sb_url"], rcfg["sb_key"], rcfg["sb_table"], rcfg["sb_k"]) if rcfg else {}
                            stop = _guess_stop_from_loss_sb(sb_v, a["ticker"])
            
                    # PnL hipotético no STOP
                    op_close = "VENDA" if a["op_abertura"] == "COMPRA" else "COMPRA"
                    pnl = pnl_from_ops(a["op_abertura"], a["preco_abertura"], op_close, stop) if stop is not None else None
            
                    # Dias desde a data de abertura
                    dt_abertura = a.get("data_abertura")
                    if isinstance(dt_abertura, str):
                        dt_abertura = parse_iso(dt_abertura)
            
                    try:
                        dur_days = (agora_lx().date() - dt_abertura.date()).days if dt_abertura else None
                    except Exception:
                        dur_days = None
            
                    out.append({
                        **a,
                        "preco_stop": stop,
                        "pnl": pnl,
                        "dur_days": dur_days,
                    })
                return out

            mapa_nomes = {r["key"]: r["title"] for r in ROBOS}
    
    
        
            # -------------------------------
            # PREPARO DOS DADOS
            # -------------------------------
            # Historico já existe: historico_local (lista de dicts)
            # Campos: robo, robo_nome, ticker, operacao, alvo, hora            
            
        
            # 1) Seletor de ROBÔ (apenas bases) – mantém o estilo dos seletores existentes
            # -----------------------------------------------
            # FILTRO POR ROBÔ (BASE) — DESATIVADO TEMPORARIAMENTE
            # -----------------------------------------------
            
            # mapa_nomes = {r["key"]: r["title"] for r in ROBOS}
            # robos_disponiveis = [r["key"] for r in ROBOS]
            # opcoes_bases = ["Todos"] + [mapa_nomes[k] for k in robos_disponiveis]
            # base_sel_nome = st.selectbox("Filtrar por robô (base)", opcoes_bases, index=0)
            
            # if base_sel_nome == "Todos":
            #     base_sel = "Todos"
            #     loss_sel = None
            # else:
            #     base_sel = next((k for k, v in mapa_nomes.items() if v == base_sel_nome), None)
            #     loss_sel = BASE_TO_LOSS.get(base_sel)
            
            # 👉 Enquanto desativado, sempre pegar TODOS os robôs base
            base_sel = "Todos"
            loss_sel = None

        
            # 2) Determina faixa de datas possíveis pelo ENCERRAMENTO (LOSS)
            # Buscar todas as datas de fechamento diretamente do Supabase
            todas_enc = supabase_select("operacoes_encerradas", "?select=data_fechamento")
            
            datas_close = []
            for r in todas_enc:
                dt = parse_iso(r.get("data_fechamento"))
                if dt:
                    datas_close.append(dt.date())
            
            if datas_close:
                min_data_close = min(datas_close)
                max_data_close = max(datas_close)
            else:
                # fallback seguro
                min_data_close = max_data_close = datetime.date.today()
    
        
            col_fd1, col_fd2 = st.columns(2)
            with col_fd1:
                data_inicio_close = st.date_input("Data inicial (encerramento)", value=min_data_close,
                                                  min_value=min_data_close, max_value=max_data_close)
            with col_fd2:
                data_fim_close = st.date_input("Data final (encerramento)", value=max_data_close,
                                               min_value=min_data_close, max_value=max_data_close)
        
            st.caption("Obs.: a filtragem por período considera **a data do encerramento (LOSS)**, como solicitado.")
        
            # -------------------------------
            # 3) Monta estrutura de aberturas por (base, ticker)
            #    e encerra com eventos do robô LOSS correspondente
            # -------------------------------
            # a) separa aberturas (robôs base) e fechamentos (robôs loss)
           # -------------------------------
        # 3) Monta estrutura de aberturas por (base, ticker)
        #    e encerra com eventos do robô LOSS correspondente
        # -------------------------------
        # a) separa aberturas (robôs base) e fechamentos (robôs loss)
        aberturas = []
        fechamentos = []
        
        for r in historico_local:
            robo_key = r.get("robo")
            if not robo_key:
                continue
            tick = (r.get("ticker") or "—").upper().strip()
            oper = direcao_op(r.get("operacao"))
            if oper is None:
                continue
            preco = (
                parse_float(r.get("alvo"))
                or parse_float(r.get("preco_alvo"))
                or parse_float(r.get("preco"))
                or parse_float(r.get("valor"))
            )
            dt = parse_iso(r.get("hora"))
            if not dt:
                continue
        
            if robo_key in BASE_TO_LOSS:
                aberturas.append({
                    "robo_base": robo_key,
                    "robo_nome_base": mapa_nomes.get(robo_key, robo_key),
                    "ticker": tick,
                    "op": oper,
                    "preco": preco,
                    "dt": dt,
                    "src": r,
                })
            elif robo_key in LOSS_TO_BASE:
                fechamentos.append({
                    "robo_loss": robo_key,
                    "robo_nome_loss": mapa_nomes.get(robo_key, robo_key),
                    "ticker": tick,
                    "op": oper,
                    "preco": preco,
                    "dt": dt,
                    "src": r,
                })
        
        aberturas.sort(key=lambda x: x["dt"])
        fechamentos.sort(key=lambda x: x["dt"])
        
        from collections import defaultdict
        stacks = defaultdict(list)
        
        for a in aberturas:
            key_stack = (a["robo_base"], a["ticker"], a["op"])
            stacks[key_stack].append(a)
        
        pareados = []
        
        for f in fechamentos:
            base_key = LOSS_TO_BASE.get(f["robo_loss"])
            if not base_key:
                continue
        
            op_close_orig = f["op"]
            if op_close_orig == "COMPRA":
                op_close_real = "VENDA"
            elif op_close_orig == "VENDA":
                op_close_real = "COMPRA"
            else:
                op_close_real = op_close_orig
        
            op_open = "COMPRA" if op_close_real == "VENDA" else "VENDA" if op_close_real == "COMPRA" else None
            if op_open is None:
                continue
        
            stack_key = (base_key, f["ticker"], op_open)
            candidatos = stacks.get(stack_key, [])
            if not candidatos:
                continue
        
            a = None
            for i in range(len(candidatos) - 1, -1, -1):
                c = candidatos[i]
                if c.get("_closed"):
                    continue
                if c["dt"] < f["dt"]:
                    a = c
                    candidatos[i]["_closed"] = True
                    break
            if a is None:
                continue
        
            pnl = pnl_from_ops(a["op"], a["preco"], op_close_real, f["preco"])
            dur_days = None
            if a["dt"] and f["dt"]:
                dur_days = (f["dt"] - a["dt"]).total_seconds() / 86400.0
                if dur_days < 0:
                    continue
        
            op = {
                "robo_base": a["robo_base"],
                "robo_nome_base": a["robo_nome_base"],
                "robo_loss": f["robo_loss"],
                "robo_nome_loss": f["robo_nome_loss"],
                "ticker": a["ticker"],
                "op_abertura": a["op"],
                "preco_abertura": a["preco"],
                "data_abertura": a["dt"],
                "op_fechamento_real": op_close_real,
                "preco_fechamento": f["preco"],
                "data_fechamento": f["dt"],
                "pnl": pnl,
                "dur_days": dur_days,
            }
        
            pareados.append(op)
        
            # ✅ salvar no Supabase se ainda não existe
            existe = supabase_select(
                "operacoes_encerradas",
                f"?select=id&ticker=eq.{op['ticker']}"
                f"&data_abertura=eq.{op['data_abertura'].isoformat()}"
                f"&data_fechamento=eq.{op['data_fechamento'].isoformat()}"
            )
        
            if not existe:
                salvar_operacao_supabase(op)
        
    
        # 4) Filtro por robô e período
        # -------------------------------
        # ✅ Buscar histórico consolidado direto do Supabase (fonte oficial)
        dados_enc = supabase_select(
            "operacoes_encerradas",
            f"?select=*"
            f"&data_fechamento=gte.{data_inicio_close}T00:00:00"
            f"&data_fechamento=lte.{data_fim_close}T23:59:59"
        )
        
        # ✅ limpar buffer de pareados local para não interferir
        pareados = []
        
        # Converter timestamps string → datetime
        for x in dados_enc:
            try:
                x["data_abertura"] = datetime.datetime.fromisoformat(x["data_abertura"])
                x["data_fechamento"] = datetime.datetime.fromisoformat(x["data_fechamento"])
            except:
                pass
        
        # ✅ Agora sim: salvar dados filtrados e convertidos no session_state
        st.session_state["dados_enc"] = dados_enc
        
        # ✅ E carregar de lá para continuar o processamento (fonte única)
        dados_enc = st.session_state.get("dados_enc", [])
    
        # ====================================
        # 🔵 FILTRO POR ÍNDICE (CARTEIRA)
        # ====================================
        if indice_sel != "Todas":
            dados_enc = [x for x in dados_enc if x.get("indice") == indice_sel]
    
        
        # se robo filtrado
        if base_sel and base_sel != "Todos":
            dados_enc = [x for x in dados_enc if x["robo_base"] == base_sel]
        
        def dentro_periodo_close(x):
            d = x.get("data_fechamento")
            if not isinstance(d, datetime.datetime):
                return False
            ddate = d.date()
            return data_inicio_close <= ddate <= data_fim_close
        
        dados_enc = [x for x in dados_enc if dentro_periodo_close(x)]
    
        
        
        # -------------------------------
        # 5) Renderização: TABELA + RESUMO + GRÁFICO
        # -------------------------------
        if not dados_enc:
            st.info("Nenhuma operação encerrada encontrada dentro dos filtros selecionados.")
        else:
            # tabela
            df_ops = pd.DataFrame([
                {
                    "Índice": x.get("indice"),
                    #"Robô (Base)": x["robo_nome_base"],
                    "Ticker": x["ticker"],
                    "Abertura": x["op_abertura"],
                    "Preço Abertura": x["preco_abertura"],
                    "Data Abertura": x["data_abertura"].strftime("%d/%m/%Y %H:%M"),
                    "Fechamento (LOSS)": x["op_fechamento_real"],
                    "Preço Fechamento": x["preco_fechamento"],
                    "Data Fechamento": x["data_fechamento"].strftime("%d/%m/%Y %H:%M"),
                    "PnL (R$)": x["pnl"],
                    "PnL (%)": (
                        (x["pnl"] / x["preco_abertura"] * 100)
                        if x["pnl"] not in (None, 0) and x["preco_abertura"]
                        else 0
                    ),
                    "Dias": round(x["dur_days"], 2) if x["dur_days"] is not None else None,
                }
                for x in dados_enc
            ])
        
            # formatar valores
            df_ops["Preço Abertura"] = df_ops["Preço Abertura"].apply(lambda v: f"R$ {v:,.2f}" if v is not None else "—")
            df_ops["Preço Fechamento"] = df_ops["Preço Fechamento"].apply(lambda v: f"R$ {v:,.2f}" if v is not None else "—")
            df_ops["PnL (R$)"] = df_ops["PnL (R$)"].apply(lambda v: f"R$ {v:,.2f}" if v is not None else "—")
            df_ops["PnL (%)"] = df_ops["PnL (%)"].apply(lambda v: f"{v:.2f}%" if v is not None else "—")
        
            # ordenar pela Data Fechamento (desc)
            df_ops = df_ops.sort_values("Data Fechamento", ascending=False)
        
            st.dataframe(df_ops, use_container_width=True, hide_index=True)
        
            # -------------------------------
            # 📊 Resumo Estatístico
            # -------------------------------
            pnls = [x["pnl"] for x in dados_enc if x["pnl"] is not None]
            lucros = [p for p in pnls if p > 0]
            preju = [p for p in pnls if p < 0]
            neutras = [p for p in pnls if p == 0]
        
            lucro_total = sum(pnls) if pnls else 0.0
            qtd_lucro = len(lucros)
            qtd_preju = len(preju)
            qtd_neutras = len(neutras)
            media_lucro_vencedoras = (sum(lucros) / len(lucros)) if lucros else 0.0
        
            # cálculo percentual
            total_pct = 0.0
            pct_lucros = []
            for x in dados_enc:
                if x["pnl"] is not None and x["preco_abertura"]:
                    pct = (x["pnl"] / x["preco_abertura"]) * 100
                    total_pct += pct
                    if pct > 0:
                        pct_lucros.append(pct)
        
            lucro_total_pct = total_pct
            media_pct_vencedoras = (sum(pct_lucros) / len(pct_lucros)) if pct_lucros else 0.0
        
            # operação mais lucrativa
            op_mais_lucr = None
            if dados_enc:          
    
                op_mais_lucr = max(
                    (x for x in dados_enc if x["pnl"] is not None and x["preco_abertura"]),
                    key=lambda x: (x["pnl"] / x["preco_abertura"]),
                    default=None
                )
    
        
            # média dias
            dur_list = [x["dur_days"] for x in dados_enc if x["dur_days"] is not None]
            media_dias = (sum(dur_list) / len(dur_list)) if dur_list else 0.0
        
            # ===============================
            # CARDS RESUMO
            # ===============================
            st.markdown("---")
            st.markdown("#### 🦅 Resumo Consolidado")
            
            def card_cor_valor(valor):
                if valor > 0: return "#22c55e"
                if valor < 0: return "#ef4444"
                return "#e5e7eb"
        
            def render_card(titulo, valor, sufixo="%", casas=2):
                cor = card_cor_valor(valor)
                try:
                    val_fmt = f"{valor:.{casas}f}{sufixo}"
                except:
                    val_fmt = str(valor)
        
                st.markdown(
                    f"""
                    <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                                background-color:rgba(17,24,39,0.85);
                                border-left:6px solid {cor};
                                color:white;">
                        <b style="color:#9ca3af;">{titulo}</b><br>
                        <span style="font-size:1.9em;color:{cor};font-weight:bold;">{val_fmt}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        
            col1, col2, col3 = st.columns(3)
            with col1:
                render_card("Lucro total", lucro_total_pct)
                render_card("Operações com lucro", qtd_lucro, sufixo="", casas=0)
            with col2:
                render_card("Média lucro (vencedoras)", media_pct_vencedoras)
                st.markdown(f"""
                <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                            background-color:rgba(17,24,39,0.85);
                            border-left:6px solid #ef4444;
                            color:white;">
                    <b style="color:#9ca3af;">Operações com prejuízo</b><br>
                    <span style="font-size:1.9em;color:#ef4444;font-weight:bold;">{qtd_preju}</span>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                render_card("Operações neutras", qtd_neutras, sufixo="", casas=0)
                render_card("Média de dias por operação", media_dias, sufixo="", casas=2)
        
            # ===============================
            # Stop loss / fluxo / op top
            # ===============================
            pnl_percentuais = [(x["pnl"] / x["preco_abertura"])*100 for x in dados_enc if x["pnl"] and x["preco_abertura"]]
            perdas_pct = [p for p in pnl_percentuais if p < 0]
            ganhos_pct = [p for p in pnl_percentuais if p > 0]
        
            media_stop_loss_pct = (sum(perdas_pct) / len(perdas_pct)) if perdas_pct else 0.0
            rent_fluxo_capital = lucro_total_pct / 4 if lucro_total_pct else 0.0
        
            colx1, colx2, colx3 = st.columns(3)
            with colx1:
                render_card("Média de Stop Loss", media_stop_loss_pct)
            with colx2:
                render_card("Rentabilidade por Fluxo de Capital", rent_fluxo_capital)
            with colx3:
                if op_mais_lucr:
                    pnl_pct_op = (op_mais_lucr["pnl"] / op_mais_lucr["preco_abertura"]) * 100
                    cor_op = card_cor_valor(pnl_pct_op)
                    st.markdown(
                        f"""
                        <div style="padding:12px 16px;margin-bottom:12px;border-radius:14px;
                                    background-color:rgba(17,24,39,0.85);
                                    border-left:6px solid {cor_op};
                                    color:white;">
                            <b style="color:#9ca3af;">Operação mais lucrativa</b><br>
                            <span style="font-size:1.9em;color:white;font-weight:bold;">{op_mais_lucr['ticker']}</span>
                            <span style="font-size:1.9em;color:{cor_op};font-weight:bold;">&nbsp;&nbsp;{pnl_pct_op:.2f}%</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    render_card("Operação mais lucrativa", 0)
        
            # ===============================
            # Gráfico
            # ===============================
            st.markdown("---")
            st.markdown("#### ⭐ Gráfico de Desempenho")
        
            df_chart = []
            for x in dados_enc:
                if x["pnl"] is not None and x["preco_abertura"]:
                    pnl_pct = (x["pnl"] / x["preco_abertura"]) * 100
                    df_chart.append({"Ticker": x["ticker"], "PnL_pct": pnl_pct})
            
            if df_chart:
                df_chart = (
                    pd.DataFrame(df_chart)
                    .groupby("Ticker", as_index=False)["PnL_pct"]
                    .mean()
                    .sort_values("PnL_pct", ascending=False)
                )
            
                # Cores elegantes dinâmicas
                colors = [
                    "rgba(34, 197, 94, 0.85)" if v > 0 else "rgba(239, 68, 68, 0.85)"
                    for v in df_chart["PnL_pct"]
                ]
                colors_hover = [
                    "rgba(34, 197, 94, 1)" if v > 0 else "rgba(239, 68, 68, 1)"
                    for v in df_chart["PnL_pct"]
                ]
            
                fig = go.Figure()
            
                fig.add_trace(
                    go.Bar(
                        x=df_chart["Ticker"],
                        y=df_chart["PnL_pct"],
                        marker=dict(
                            color=colors,
                            line=dict(width=0),
                        ),
                        hovertemplate="<b>%{x}</b><br>Retorno: %{y:.2f}%<extra></extra>",
                        text=[f"{v:.2f}%" for v in df_chart["PnL_pct"]],
                        textposition="outside",
                    )
                )
            
                # Estilo refinado
                fig.update_traces(
                    marker=dict(
                        color=colors,
                        line=dict(width=0),
                    ),
                    marker_line_width=0,
                    hoverlabel=dict(bgcolor="rgba(0,0,0,0.7)", font_size=13),
                    textfont=dict(size=12, color="#e5e7eb"),
                )
            
                fig.update_layout(
                    template="plotly_dark",
                    height=420,
                    margin=dict(l=20, r=20, t=45, b=20),
                    font=dict(color="#e5e7eb"),
                    plot_bgcolor="rgba(15, 18, 28, 0.95)",
                    paper_bgcolor="rgba(15, 18, 28, 1)",
    
                    xaxis=dict(showgrid=False),
                    yaxis=dict(
                        title="Lucro / Prejuízo (%)",
                        gridcolor="rgba(255,255,255,0.08)",
                        zeroline=False,
                    ),
                )
            
                # Animação suave (efeito premium)
                fig.update_traces(
                    marker=dict(
                        color=colors,
                    ),
                    selector=dict(type="bar")
                )
            
                fig.update_layout(transition_duration=500)
            
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado disponível para o gráfico no período selecionado.")
    
    
    
    # ===========================================
    # 📄 EXPORTAR RELATÓRIO PDF
    # ===========================================
    # ======================================================
    # 📄 EXPORTAR RELATÓRIO PDF — DARK & WHITE (Paisagem)
    # ======================================================
    # ======================================================
    # 📄 EXPORTAR RELATÓRIO PDF — DARK & WHITE (Paisagem)
    # ======================================================
    import os, tempfile
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
        PageBreak, Frame, PageTemplate  # ✅ inclui Frame e PageTemplate
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.colors import Color
    
    
    # ---------- Temas ----------
    THEMES = {
        "dark": {
            "page_bg": (0.07, 0.09, 0.15),           # #121726 aprox
            "text": colors.whitesmoke,
            "muted": "#9ca3af",
            "rule": "#334155",
            "card_bg": colors.Color(0.12, 0.15, 0.21),
            "card_border": colors.Color(0.18, 0.2, 0.28),
            "pos": "#22c55e",
            "neg": "#ef4444",
            "neutral": "#e5e7eb",
            "tbl_header_bg": "#334155",
            "tbl_body_bg": "#1e293b",
            "tbl_grid": "#475569",
            "tbl_text": colors.whitesmoke,   # ✅ dark não usa preto
            "title_color": "white",
            "footer_text": (0.65, 0.7, 0.78),
        },
        "white": {
            "page_bg": (1, 1, 1),
            "text": colors.black,            # ✅ white não usa branco
            "muted": "#4b5563",
            "rule": "#cbd5e1",
            "card_bg": colors.Color(0.96, 0.97, 0.99),
            "card_border": colors.Color(0.85, 0.88, 0.94),
            "pos": "#16a34a",
            "neg": "#dc2626",
            "neutral": "#0f172a",
            "tbl_header_bg": "#cbd5e1",
            "tbl_body_bg": "#f1f5f9",
            "tbl_grid": "#94a3b8",
            "tbl_text": colors.black,
            "title_color": "#0f172a",
            "footer_text": (0.35, 0.38, 0.45),
        },
    }
    
    # ---------- FUNÇÃO DE FUNDO ----------
    def _page_bg_factory(theme_key: str):
        theme = THEMES[theme_key]
        def _bg(canvas, doc):
            canvas.saveState()
            w, h = doc.pagesize
    
            # Fundo da página
            r,g,b = theme["page_bg"]
            canvas.setFillColorRGB(r, g, b)
            canvas.rect(0, 0, w, h, fill=1, stroke=0)
    
            # Texto do rodapé
            canvas.setFillColorRGB(*theme["footer_text"])
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(
                w - 1.25*cm, 0.9*cm,
                "Aurinvest — Relatório de Performance"
            )
    
            # ✅ Logo no rodapé (lado esquerdo)
            try:
                logo = ImageReader("logot.png")
                logo_w = 3.6*cm   # ajuste de tamanho (fixo)
                logo_h = 1.8*cm
                canvas.drawImage(
                    logo,
                    1.0*cm,        # X - margem esquerda
                    0.45*cm,       # Y - perto do rodapé
                    width=logo_w,
                    height=logo_h,
                    mask='auto'
                )
            except:
                pass
    
            canvas.restoreState()
        return _bg
    
    
    def _cover_bg(canvas, doc):
        canvas.saveState()
        w, h = doc.pagesize
    
        # --- background image
        try:
            img = ImageReader("capa2.jpeg")
            canvas.drawImage(img, 0, 0, width=w, height=h, mask='auto')
        except:
            pass
    
        # --- overlay escuro
        canvas.setFillColor(Color(0, 0, 0, alpha=0.70))
        canvas.rect(0, 0, w, h, fill=1, stroke=0)
    
        # --- vidro fosco: ANCORADO NAS MARGENS DO DOC
        pad_x = 0.6*cm   # padding extra ao redor do texto
        pad_y = 0.6*cm
    
        content_w = w - doc.leftMargin - doc.rightMargin
        rect_w = content_w * 0.62          # largura do vidro relativa à largura útil
        rect_h = 4.8*cm                    # altura suficiente p/ 3 linhas + espaçamentos
        rect_x = doc.leftMargin - pad_x
        rect_y = h - doc.topMargin - rect_h + pad_y   # encosta no topo do frame
    
        glass_color  = Color(1, 1, 1, alpha=0.18)
        glass_border = Color(1, 1, 1, alpha=0.32)
    
        canvas.setFillColor(glass_color)
        canvas.roundRect(rect_x, rect_y, rect_w, rect_h, 16, fill=1, stroke=0)
        canvas.setStrokeColor(glass_border)
        canvas.setLineWidth(1.3)
        canvas.roundRect(rect_x, rect_y, rect_w, rect_h, 16, fill=0, stroke=1)
    
        # --- rodapé do analista (inalterado)
        canvas.setFillColor(Color(1, 1, 1, alpha=0.85))
        canvas.setFont("Helvetica", 10)
        canvas.drawRightString(
            w - 1.0*cm, 0.9*cm,
            "Aurinvest — Relatório de Performance"
        )
    
        # ✅ LOGO no rodapé da capa (fixo)
        #try:
            #logo = ImageReader("logot.png")
            #logo_w = 3.6*cm
            #logo_h = 1.8*cm
            #canvas.drawImage(
                #logo,
                #1.0*cm,        # X — margem esquerda
                #0.45*cm,       # Y — posição do rodapé
                #width=logo_w,
                #height=logo_h,
                #mask='auto'
            #)
        #except:
            #pass
    
        canvas.restoreState()
    
    
    # ---------- CAPA ----------
    def _cover_page(elements, theme, data_inicio, data_fim):
    
        styles = getSampleStyleSheet()
    
        title = Paragraph(
            "<para align='center'><font size=34 color='#fbbf24'><b>Relatório de Performance</b></font></para>",
            styles["Title"]
        )
    
        subtitle = Paragraph(
            "<para align='center'><font size=20 color='white'><b>Aurinvest</b></font></para>",
            styles["Normal"]
        )
    
        period = Paragraph(
            f"<para align='center'><font size=14 color='#fbbf24'>Período: {data_inicio} → {data_fim}</font></para>",
            styles["Normal"]
        )
    
        # Espaçamento entre as linhas (posição preservada)
        elements += [
            Spacer(1, 0.4*cm),
            title,
            Spacer(1, 0.4*cm),
            subtitle,
            Spacer(1, 0.6*cm),
            period
        ]
    
        return elements
    
    
    # ---------- METODOLOGIA ----------
    def _methodology_page(elements, theme, theme_key):
        styles = getSampleStyleSheet()
        # ✅ corpo do texto sempre na cor do tema (dark: whitesmoke / white: black)
        justify = ParagraphStyle(
            "just", parent=styles["Normal"], alignment=TA_JUSTIFY,
            textColor=theme["text"], fontSize=10
        )
        # ✅ heading color conforme tema (evita preto no dark e branco no white)
        heading_color = "#ffffff" if theme_key == "dark" else "#000000"
    
        txt = """
        <b>Lucro Total</b><br/><br/>
        O cálculo de Lucro Total considera:<br/>
        • Somente estratégias encerradas no período.<br/>
        • A soma das porcentagens de ganho descontada da soma das perdas nas operações encerradas no stop no mês corrente.<br/>
        • Carteira de ativos com pesos idênticos.<br/>
        • Valor bruto, ou seja, do lucro obtido nas operações é necessário descontar impostos e taxas inerentes à classe de investimento.<br/><br/>
        
        <b>Rentabilidade sobre o Fluxo de Capital</b><br/><br/>
        A Rentabilidade sobre o Fluxo de Capital considera:<br/>
        • Somente estratégias encerradas nos períodos semanal e mensal.<br/>
        • Carteira de ativos com pesos idênticos.<br/>
        • Fluxo de Capital idêntico e reinvestido semanalmente no período mensal.<br/>
        • Rentabilidade Real Semanal dividindo-se a lucratividade global de cada semana pelo número de operações da semana.<br/>
        • Rentabilidade Real do período mensal somando-se a rentabilidade real de cada semana.<br/>
        • Lucro Real bruto, ou seja, do lucro real obtido nas operações é necessário descontar impostos e taxas inerentes à classe de investimento.<br/><br/>
        
        <b>Observação Fiscal</b><br/>
        Ao operar na Bolsa de Valores, o investidor está sujeito a ter lucros e prejuízos. 
        De acordo com a Receita Federal, o valor perdido em operações pelo acionamento do stop loss poderá ser abatido do lucro de operações futuras a fim de reduzir o imposto de renda devido, desde que tais operações sejam de mesma natureza.
        """
    
        elements += [
            Paragraph(
                f"<font color='{heading_color}'><b>Metodologia de Cálculo</b></font>",
                ParagraphStyle("center", parent=styles["Heading2"], alignment=TA_CENTER)
            ),
    
        
            pdf_rule(theme_key),     # ✅ LINHA AQUI
        
            Spacer(1,0.2*cm),
            Paragraph(txt, justify)
        ]
    
        return elements
    
    # ---------- COMPLIANCE ----------
    def _compliance_page(elements, theme, theme_key):
        styles = getSampleStyleSheet()
        justify = ParagraphStyle(
            "just", parent=styles["Normal"], alignment=TA_JUSTIFY,
            textColor=theme["text"], fontSize=10
        )
        heading_color = "#ffffff" if theme_key == "dark" else "#000000"
    
        txt = """
        <b>Compliance</b><br/><br/>
        A rentabilidade obtida no passado não representa garantia de resultados futuros.<br/>
        O investimento em ações não é garantido pelo Fundo Garantidor de Crédito (FGC).<br/>
        A rentabilidade divulgada não é líquida de impostos.<br/><br/>
        
        O analista (CNPI) responsável pelas recomendações declara que as indicações obedecem ao estabelecido na Resolução CVM nº 20/2021 e que as recomendações refletem exclusivamente suas opiniões pessoais sobre as companhias e seus valores mobiliários, produzidas de forma independente e autônoma.<br/><br/>
        
        Por se tratar de investimento em renda variável, não há qualquer garantia de que o mercado irá performar em congruência com as estratégias divulgadas.
        """
    
        elements += [
            Paragraph(
                f"<font color='{heading_color}'><b>Declarações Regulatórias</b></font>",
                ParagraphStyle("center", parent=styles["Heading2"], alignment=TA_CENTER)
            ),
    
        
            pdf_rule(theme_key),     # ✅ LINHA AQUI
        
            Spacer(1, 0.2*cm),
            Paragraph(txt, justify)
        ]
    
        return elements
    
    
    # ---------- HELPERS ----------
    def _color_to_hex(c):
        try:
            if isinstance(c, str): return c
            return "#%02x%02x%02x" % (int(c.red*255), int(c.green*255), int(c.blue*255))
        except:
            return "#FFFFFF"
    
    def _make_card(label, value, theme_key: str, kind: str = "percent"):
        theme = THEMES[theme_key]
        bg = theme["card_bg"]
    
        # ---- valor e cor do texto (padrão) ----
        if kind == "percent":
            v = float(str(value).replace("%","")) if value else 0
            val_str = f"{v:.2f}%"
            if v > 0:     vcol = colors.HexColor(theme["pos"])
            elif v < 0:   vcol = colors.HexColor(theme["neg"])
            else:         vcol = colors.HexColor(theme["neutral"])
        elif kind == "count":
            v = int(value) if value else 0
            val_str = str(v)
            vcol = colors.HexColor(theme["neutral"])
        else:
            v = float(value) if value else 0
            val_str = f"{v:.2f}"
            vcol = colors.HexColor(theme["neutral"])
    
        # ---- regras fixas por rótulo (borda e número) ----
        lab = (label or "").strip().lower()
        bcol = colors.HexColor(theme["pos"])  # default: verde
    
        def _theme(colkey):
            return colors.HexColor(theme[colkey])
    
        specials = {
            "operações com prejuízo": ("neg", "neg"),   # vermelho
            "operações neutras":      ("yellow", "yellow"),
            "média de dias por operação":          ("gray", "gray"),
            "operações com lucro":    ("pos", "pos"),   # verde
            "média stop loss":        ("neg", "neg"),   # << FIXO: vermelho
        }
    
        if lab in specials:
            bkey, vkey = specials[lab]
            if   bkey == "pos":    bcol = _theme("pos")
            elif bkey == "neg":    bcol = _theme("neg")
            elif bkey == "gray":   bcol = colors.gray
            elif bkey == "yellow": bcol = colors.yellow
    
            if   vkey == "pos":    vcol = _theme("pos")
            elif vkey == "neg":    vcol = _theme("neg")
            elif vkey == "gray":   vcol = colors.gray
            elif vkey == "yellow": vcol = colors.yellow
    
        # ---- render ----
        v_hex = _color_to_hex(vcol)
        styles = getSampleStyleSheet()
    
        label_p = Paragraph(f"<font color='{theme['muted']}'><b>{label}</b></font>", styles["BodyText"])
        val_p   = Paragraph(f"<font color='{v_hex}' size=13><b>{val_str}</b></font>", styles["BodyText"])
    
        t = Table([[label_p],[val_p]], colWidths=[8.6*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),bg),
            ("BOX",(0,0),(-1,-1),0.6,theme["card_border"]),
            ("LINEBEFORE",(0,0),(0,-1),6,bcol),
            ("LEFTPADDING",(0,0),(-1,-1),10),
            ("RIGHTPADDING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        return t
    
    
    
    
    
    def _build_chart_png(dados_enc, theme_key: str):
        theme = THEMES[theme_key]
        tickers = {}
        for x in dados_enc:
            pnl = x.get("pnl")
            preco = x.get("preco_abertura")
            t = x.get("ticker")
            if pnl is None or not preco or not t:
                continue
            pct = (pnl/preco)*100
            tickers.setdefault(t, []).append(pct)
        if not tickers:
            return None
    
        labels, vals = zip(*sorted({t:sum(v)/len(v) for t,v in tickers.items()}.items(), key=lambda z:z[1], reverse=True))
        fig, ax = plt.subplots(figsize=(10.2,4.6), dpi=160)
        bars = ax.bar(labels, vals, color=[theme["pos"] if v>0 else theme["neg"] for v in vals])
    
        tick_color = "#e5e7eb" if theme_key=="dark" else "#111827"
        spine_color = theme["tbl_grid"]
    
        if theme_key=="dark":
            ax.set_facecolor("#0f172a")
            fig.patch.set_facecolor("#0f172a")
        else:
            ax.set_facecolor("#ffffff")
            fig.patch.set_facecolor("#ffffff")
    
        ax.tick_params(colors=tick_color)
        for s in ax.spines.values(): s.set_color(spine_color)
        ax.set_ylabel("PnL (%)", color=tick_color)
        ax.set_xlabel("Ticker", color=tick_color)
    
        for r,v in zip(bars,vals):
            ax.text(r.get_x()+r.get_width()/2, r.get_height(), f"{v:.2f}%", ha="center", va="bottom", color=tick_color, fontsize=8)
    
        fig.tight_layout()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        fig.savefig(tmp.name, bbox_inches="tight", dpi=160)
        plt.close(fig)
        return tmp.name
    
    
    def cover_frame(canvas, doc):
        # Posição e dimensões do vidro (mesmas do _cover_bg)
        w, h = doc.pagesize
    
        pad_x = 0.6*cm
        pad_y = 0.6*cm
    
        content_w = w - doc.leftMargin - doc.rightMargin
        rect_w = content_w * 0.62
        rect_h = 4.8*cm
        rect_x = doc.leftMargin - pad_x
        rect_y = h - doc.topMargin - rect_h + pad_y
    
        # Frame exato dentro da moldura
        frame = Frame(
            rect_x + pad_x,
            rect_y + pad_y,
            rect_w - pad_x*2,
            rect_h - pad_y*2,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            showBoundary=0
        )
        doc.addPageTemplates([
            PageTemplate(id='cover', frames=frame, onPage=_cover_bg)
        ])
    from reportlab.platypus import HRFlowable
    
    def pdf_rule(theme_key):
        color = THEMES[theme_key]["rule"]
        return HRFlowable(width="80%", thickness=0.8, lineCap='round', color=color, spaceBefore=4, spaceAfter=8)
    
    
    # ---------- GERADOR FINAL ----------
    def export_pdf_landscape(
        theme_key: str,
        df_ops, dados_enc,
        lucro_total_pct, media_pct_vencedoras, qtd_lucro, qtd_preju, qtd_neutras,
        media_dias, media_stop_loss_pct, rent_fluxo_capital, op_mais_lucr,
        data_inicio, data_fim
    ):
        theme = THEMES[theme_key]
        pdf_path = f"Relatorio_Aurinvest_{theme_key}.pdf"
    
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            leftMargin=1.2*cm, rightMargin=1.2*cm,
            topMargin=1.2*cm, bottomMargin=1.2*cm
        )
    
        styles = getSampleStyleSheet()
        elements = []
    
        # ========= CAPA =========
        elements = _cover_page(elements, theme, data_inicio, data_fim)
    
        # ========= DEFINIÇÃO DOS CARDS =========
        cards_cfg = [
            ("Lucro total (%)",           lucro_total_pct,        "percent"),
            ("Média lucro (vencedoras)",  media_pct_vencedoras,   "percent"),
            ("Operações com lucro",       qtd_lucro,              "count"),
            ("Operações com prejuízo",    qtd_preju,              "count"),
            ("Operações neutras",         qtd_neutras,            "count"),
            ("Média de dias por operação",             media_dias,             "days"),
            ("Média Stop Loss",           media_stop_loss_pct,    "percent"),
            ("Rentab. por Fluxo Capital", rent_fluxo_capital,     "percent"),
            ("Op. mais lucrativa",        (op_mais_lucr["pnl"] / op_mais_lucr["preco_abertura"] * 100) if op_mais_lucr else 0, "percent"),
        ]
    
        # ========= PÁGINA DOS CARDS =========
        from reportlab.platypus import KeepTogether
        elements.append(PageBreak())
        heading_color = "#ffffff" if theme_key == "dark" else "#000000"
        elements.append(Spacer(1, 0.4*cm))
        elements.append(Paragraph(
            f"<para align='center'><font size=18 color='{heading_color}'><b>Resumo de Performance</b></font></para>",
            styles["Title"]
        ))
        elements.append(pdf_rule(theme_key))
        elements.append(Spacer(1, 0.8*cm))
    
        cards_block = []
        for i in range(0, len(cards_cfg), 3):
            row = [_make_card(l, v, theme_key, k) for (l, v, k) in cards_cfg[i:i+3]]
            while len(row) < 3:
                row.append("")
            cards_block.append(Table([row], colWidths=[9.0*cm]*3, hAlign="CENTER"))
            cards_block.append(Spacer(1, 0.45*cm))
    
        elements.append(Spacer(1, 2.2*cm))
        elements.append(KeepTogether(cards_block))
        elements.append(Spacer(1, 2.2*cm))
        elements.append(PageBreak())
    
        # ========= TABELA DE OPERAÇÕES =========
        elements.append(Spacer(1, 0.4*cm))
        elements.append(Paragraph(
            f"<para align='center'><font size=18 color='{heading_color}'><b>Operações Encerradas</b></font></para>",
            styles["Title"]
        ))
        elements.append(pdf_rule(theme_key))
        elements.append(Spacer(1, 0.8*cm))
    
        df_pdf = df_ops.iloc[:, 1:].copy().astype(str)  # remove "Robô (Base)" se for a 1ª coluna
        available_cm = 26.5
        col_w = (available_cm / len(df_pdf.columns)) * cm
    
        tbl = Table([df_pdf.columns.tolist()] + df_pdf.values.tolist(),
                    colWidths=[col_w]*len(df_pdf.columns))
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor(THEMES[theme_key]["tbl_header_bg"])),
            ("TEXTCOLOR",(0,0),(-1,0), THEMES[theme_key]["text"] if theme_key=="dark" else colors.black),
            ("BACKGROUND",(0,1),(-1,-1),colors.HexColor(THEMES[theme_key]["tbl_body_bg"])),
            ("TEXTCOLOR",(0,1),(-1,-1), THEMES[theme_key]["tbl_text"]),
            ("GRID",(0,0),(-1,-1),0.35,colors.HexColor(THEMES[theme_key]["tbl_grid"])),
            ("FONTSIZE",(0,0),(-1,-1),7),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("TOPPADDING",(0,0),(-1,-1),3),
        ]))
        elements.append(KeepTogether([Spacer(1, 2.2*cm), tbl, Spacer(1, 2.2*cm)]))
        elements.append(PageBreak())
    
        # ========= GRÁFICO =========
        chart_path = _build_chart_png(dados_enc, theme_key)
        if chart_path and os.path.exists(chart_path):
            elements.append(Spacer(1, 0.4*cm))
            elements.append(Paragraph(
                f"<para align='center'><font size=18 color='{heading_color}'><b>Gráfico de Performance por Ativo</b></font></para>",
                styles["Title"]
            ))
            elements.append(pdf_rule(theme_key))
            elements.append(Spacer(1, 0.8*cm))
    
            graph_block = []
            graph_block.append(Spacer(1, 2.5*cm))
            img = Image(chart_path, width=22*cm, height=8*cm)
            img.hAlign = "CENTER"
            graph_block.append(img)
            graph_block.append(Spacer(1, 2.5*cm))
            elements.append(KeepTogether(graph_block))
            elements.append(PageBreak())
    
        # ========= METODOLOGIA & COMPLIANCE =========
        elements = _methodology_page(elements, theme, theme_key)
        elements = _compliance_page(elements, theme, theme_key)
    
        # ========= BUILD =========
        onpage = _page_bg_factory(theme_key)
        cover_frame(None, doc)  # registra o template da capa
        doc.build(
            elements,
            onFirstPage=_cover_bg,     # fundo da capa
            onLaterPages=onpage        # fundo das demais páginas
        )
    
        return pdf_path
    
    
    
    # ===========================================
    # 📄 PDF — Diretrizes Diárias (Operações Abertas)
    # ===========================================
    
    def export_pdf_abertas(
        theme_key: str,
        df_ops_abertas: pd.DataFrame,
        abertas_enriquecidas: list,
        data_inicio_txt: str,
        data_fim_txt: str,
    ):
        theme = THEMES[theme_key]
        pdf_path = f"Diretrizes_Diarias_{theme_key}.pdf"
    
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            leftMargin=1.2*cm, rightMargin=1.2*cm,
            topMargin=1.2*cm, bottomMargin=1.2*cm
        )
    
        styles = getSampleStyleSheet()
        elements = []
    
        # ===============================
        # PÁGINA 1 — TÍTULO + TABELA
        # ===============================
        heading_color = "#ffffff" if theme_key == "dark" else "#000000"
        elements.append(Spacer(1, 0.4*cm))
        
        # Cabeçalho com data/hora de envio
        #data_hora_envio = agora_lx().strftime("%d/%m/%Y %H:%M")
        elements.append(Paragraph(
            f"<para align='center'><font size=18 color='{heading_color}'><b>Performance Relativa dos Trades em Andamento</b></font></para>",
            styles["Title"]
        ))
        elements.append(pdf_rule(theme_key))
        elements.append(Spacer(1, 0.8*cm))
        
        # ---- ordenar df de acordo com abertas_enriquecidas ----
        # ---- ordenar df de acordo com abertas_enriquecidas ----
        df_pdf = df_ops_abertas.copy().astype(str)
    
        # ========== NORMALIZAÇÃO DE DATA_ABERTURA ==========
        def normalizar_data(d):
            """Converte para datetime se for string ISO, ignora None."""
            if isinstance(d, datetime.datetime):
                return d
            if isinstance(d, str):
                try:
                    return datetime.datetime.fromisoformat(d)
                except:
                    return None
            return None
    
        # Normaliza todas as datas no objeto enriquecido
        for x in abertas_enriquecidas:
            x["data_abertura_norm"] = normalizar_data(x.get("data_abertura"))
    
        # Criamos um map seguro:
        ordem_map = {}
        for i, x in enumerate(abertas_enriquecidas):
            ticker = x.get("ticker")
            dnorm = x.get("data_abertura_norm")
            if isinstance(dnorm, datetime.datetime):
                chave = (ticker, dnorm.strftime("%d/%m/%Y %H:%M"))
            else:
                chave = (ticker, "—")
            ordem_map[chave] = i
    
        # cria coluna técnica de ordenação
        df_pdf["_seq"] = df_pdf.apply(
            lambda r: ordem_map.get((r["Ticker"], r["Data Abertura"]), 10**9),
            axis=1
        )
    
        # ordena e remove coluna técnica
        df_pdf = df_pdf.sort_values("_seq").drop(columns=["_seq"])
    
        
        # Remove "Robô" da tabela se existir
        if "Robô (Base)" in df_pdf.columns:
            df_pdf = df_pdf.drop(columns=["Robô (Base)"])
        
        # Largura automática
     
        available_cm = 26.5
        col_w = (available_cm / len(df_pdf.columns)) * cm
        
        # ==== corrigir identificação da coluna STOP ====
        colunas = list(df_pdf.columns)
        
        # Preferência: destacar coluna Stop Loss
        if "Stop Loss" in colunas:
            stop_col_idx = colunas.index("Stop Loss")
        # fallback: Stop Gain
        elif "Stop Gain" in colunas:
            stop_col_idx = colunas.index("Stop Gain")
        else:
            stop_col_idx = 0  # fallback definitivo
        
        tbl = Table(
            [df_pdf.columns.tolist()] + df_pdf.values.tolist(),
            colWidths=[col_w] * len(df_pdf.columns)
        )
    
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(THEMES[theme_key]["tbl_header_bg"])),
            ("TEXTCOLOR", (0,0), (-1,0), THEMES[theme_key]["text"] if theme_key=="dark" else colors.black),
            ("BACKGROUND", (0,1), (-1,-1), colors.HexColor(THEMES[theme_key]["tbl_body_bg"])),
            ("TEXTCOLOR", (0,1), (-1,-1), THEMES[theme_key]["tbl_text"]),
            ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor(THEMES[theme_key]["tbl_grid"])),
            ("FONTSIZE", (0,0), (-1,-1), 7),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 3),
        
            # 🔥 Correção: Stop Gain / Stop Loss agora têm mesma cor que o restante:
            ("BACKGROUND", (stop_col_idx,1), (stop_col_idx,-1), colors.HexColor(THEMES[theme_key]["tbl_body_bg"])),
        ]))
        # ← FECHAMENTO CORRETO DO TableStyle
        
        elements.append(tbl)
    
    
        # ===============================
        # PÁGINA 2 — RESUMO POR ATIVO
        # ===============================
    
        # Espaço após tabela antes do resumo
        elements.append(Spacer(1, 0.6*cm))
    
        # Linha cinza separadora
        elements.append(pdf_rule(theme_key))
    
        # Espaço antes do título do resumo
        elements.append(Spacer(1, 0.8*cm))
    
        # ===============================
        # Resumo por ativo (mesma página)
        # ===============================
    
        # elements.append(Paragraph(
        #     f"<para align='center'><font size=18 color='{heading_color}'><b>Resumo</b></font></para>",
        #     styles['Title']
        # ))
        # elements.append(pdf_rule(theme_key))
        # elements.append(Spacer(1, 0.5*cm))
    
        # # Ordenar para manter a mesma ordem da tabela
        # abertas_enriquecidas = sorted(
        #     abertas_enriquecidas,
        #     key=lambda x: x['data_abertura'],
        #     reverse=True
        # )
    
        # # Frases por hipótese (usando PnL%)
        # body = []
        # for x in abertas_enriquecidas:
        #     ticker = x["ticker"]
    
        #     # STOP correto para operações abertas
        #     if x["operacao"] == "compra":
        #         stop = x.get("stop_loss")
        #     else:
        #         stop = x.get("stop_gain")
    
        #     preco_ab = x.get("preco_abertura")
        #     pnl = x.get("pnl")
    
        #     pnl_pct = None
        #     if pnl is not None and preco_ab:
        #         pnl_pct = (pnl / preco_ab) * 100
    
        #     stop_txt = f"R$ {stop:,.2f}" if stop is not None else "—"
    
        #     if pnl_pct is None:
        #         frase = f"<b>{ticker}</b>: Ajustar o STOP para <b>{stop_txt}</b>."
        #     elif pnl_pct >= 0:
        #         frase = (
        #             f"<b>{ticker}</b>: Ajustar o STOP para <b>{stop_txt}</b> garantindo "
        #             f"um lucro mínimo na operação de <b>{pnl_pct:.2f}%</b>."
        #         )
        #     else:
        #         frase = (
        #             f"<b>{ticker}</b>: Ajustar o STOP para <b>{stop_txt}</b> garantindo "
        #             f"exposição máxima na operação de <b>{pnl_pct:.2f}%</b>."
        #         )
    
        #     body.append(frase)
    
        # # Estilo do texto (mantido apenas para referência futura)
        # pstyle = ParagraphStyle(
        #     "resume",
        #     parent=styles["Normal"],
        #     fontSize=11,
        #     leading=18,
        #     spaceAfter=6,
        #     textColor=theme["text"]
        # )
    
        # for line in body:
        #     elements.append(Paragraph(line, pstyle))
        #     elements.append(Spacer(1, 0.4*cm))
        #     elements.append(pdf_rule(theme_key))
        #     elements.append(Spacer(1, 0.4*cm))
    
        # Bloco de aviso + compliance (na MESMA página)
        # =========== Texto institucional + compliance compactado ===========
        
        elements.append(Spacer(1, 10))
        
        texto_institucional = """
        <para align='left'>
        <b>Sempre importante lembrar que:</b><br/><br/>
        
        Todas as ordens de compra e venda são monitoradas constantemente e disparadas pelo nosso algoritmo exclusivo.<br/>
        Os disparos nunca são no momento exato em que a ação atinge o preço.<br/><br/>
        
        Nosso algoritmo dispara as ordens apenas no momento exato em que entende que todos os critérios do nosso setup foram atingidos.<br/>
        Para quem aguarda os alertas do robot (recomendamos isso), as planilhas com recomendações e diretrizes são apenas de caráter informativo e de acompanhamento.<br/><br/>
        
        Quem quiser operar com ordens limitadas, sem aguardar os alertas do robot, deve continuar seguindo as planilhas e diretrizes diárias.<br/><br/>
        
           
        <b>COMPLIANCE:</b><br/>
        <font size="6">
        Este documento contém informação CONFIDENCIAL de propriedade de Aurinvest e de seu DESTINATÁRIO tão somente. 
        Se você NÃO for DESTINATÁRIO ou pessoa autorizada a recebê-lo, NÃO PODE usar, copiar, transmitir, retransmitir ou divulgar seu conteúdo (no todo ou em partes),
        estando sujeito às penalidades da LEI.
        </font>
        </para>
        """
        
        pstyle_texto = ParagraphStyle(
            "texto_institucional",
            parent=styles["Normal"],
            fontSize=10,         # <── diminui o tamanho
            leading=15,          # <── menos espaço entre linhas
            alignment=TA_JUSTIFY,
            textColor=theme["text"]
        )
        
        elements.append(Paragraph(texto_institucional, pstyle_texto))
        
        elements.append(Spacer(1, 8))
    
    
        # ===============================
        # BUILD (sem CAPA; fundo padrão nas páginas)
        # ===============================
        # Criar uma versão do background sem texto no rodapé
        onpage = _page_bg_factory(theme_key)
        doc.build(elements, onFirstPage=onpage, onLaterPages=onpage)
        return pdf_path  
    
    
    
       
    
    
        
        # ========= PÁGINA DOS CARDS (ISOLADA E CENTRALIZADA) =========
        from reportlab.platypus import KeepTogether
        
        # página nova após a capa
        elements.append(PageBreak())
        
        heading_color = "#ffffff" if theme_key == "dark" else "#000000"
        
        # Título da página dos cards no topo (cabeçalho)
        elements.append(Spacer(1, 0.4*cm))
        elements.append(Paragraph(
            f"<para align='center'><font size=18 color='{heading_color}'><b>Resumo de Performance</b></font></para>",
            styles["Title"]
        ))
        elements.append(pdf_rule(theme_key))
        elements.append(Spacer(1, 0.8*cm))
        
        # Monta as linhas de cards (3 por linha)
        cards_block = []
        for i in range(0, len(cards_cfg), 3):
            row = [_make_card(l, v, theme_key, k) for (l, v, k) in cards_cfg[i:i+3]]
            while len(row) < 3: row.append("")
            cards_block.append(Table([row], colWidths=[9.0*cm]*3, hAlign="CENTER"))
            cards_block.append(Spacer(1, 0.45*cm))
        
        # Centralização vertical do bloco de cards
        elements.append(Spacer(1, 2.2*cm))
        elements.append(KeepTogether(cards_block))
        elements.append(Spacer(1, 2.2*cm))
        
        elements.append(PageBreak())  # segue para a tabela
    
    
    
    
    
        
        # ========= TABELA (Isolada e Centralizada) =========
        from reportlab.platypus import KeepTogether
        
        # nova página para a tabela
        #elements.append(PageBreak())
        
        heading_color = "#ffffff" if theme_key == "dark" else "#000000"
        
        # Título fixo no topo
        elements.append(Spacer(1, 0.4*cm))
        elements.append(Paragraph(
            f"<para align='center'><font size=18 color='{heading_color}'><b>Operações Encerradas</b></font></para>",
            styles["Title"]
        ))
        elements.append(pdf_rule(theme_key))
    
        elements.append(Spacer(1, 0.8*cm))
        
        # Remover a primeira coluna (Robô)
        df_pdf = df_ops.iloc[:, 1:].copy().astype(str)
        
        available_cm = 26.5
        col_w = (available_cm / len(df_pdf.columns)) * cm
        
        tbl = Table([df_pdf.columns.tolist()] + df_pdf.values.tolist(),
                    colWidths=[col_w]*len(df_pdf.columns))
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor(THEMES[theme_key]["tbl_header_bg"])),
            ("TEXTCOLOR",(0,0),(-1,0), THEMES[theme_key]["text"] if theme_key=="dark" else colors.black),
            ("BACKGROUND",(0,1),(-1,-1),colors.HexColor(THEMES[theme_key]["tbl_body_bg"])),
            ("TEXTCOLOR",(0,1),(-1,-1), THEMES[theme_key]["tbl_text"]),
            ("GRID",(0,0),(-1,-1),0.35,colors.HexColor(THEMES[theme_key]["tbl_grid"])),
            ("FONTSIZE",(0,0),(-1,-1),7),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("TOPPADDING",(0,0),(-1,-1),3),
        ]))
        
        # Centralização vertical do bloco da tabela
        table_block = [Spacer(1, 2.2*cm), tbl, Spacer(1, 2.2*cm)]
        elements.append(KeepTogether(table_block))
        
        elements.append(PageBreak())  # segue para o gráfico
    
    
        # ========= GRÁFICO =========
       # ========= GRÁFICO =========
        chart_path = _build_chart_png(dados_enc, theme_key)
        if chart_path and os.path.exists(chart_path):
        
            # Nova página para o gráfico
            #elements.append(PageBreak())
        
            from reportlab.platypus import KeepTogether
        
            heading_color = "#ffffff" if theme_key == "dark" else "#000000"
        
            # ✅ Título fixo no topo (como nas outras páginas)
            elements.append(Spacer(1, 0.4*cm))
            elements.append(Paragraph(
                f"<para align='center'><font size=18 color='{heading_color}'><b>Gráfico de Performance por Ativo</b></font></para>",
                styles["Title"]
            ))
            elements.append(pdf_rule(theme_key))
    
            elements.append(Spacer(1, 0.8*cm))
        
            # ✅ Bloco apenas para centralizar o gráfico
            graph_block = []
            graph_block.append(Spacer(1, 2.5*cm))  # ajusta posição do gráfico verticalmente
        
            img = Image(chart_path, width=22*cm, height=8*cm)
            img.hAlign = "CENTER"
            graph_block.append(img)
        
            graph_block.append(Spacer(1, 2.5*cm))  # espaço inferior balanceado
        
            elements.append(KeepTogether(graph_block))
        
            # Nova página depois
            elements.append(PageBreak())
    
    
    
    
    
        # ========= METODOLOGIA (após gráfico) =========
        elements = _methodology_page(elements, theme, theme_key)
    
        # ========= COMPLIANCE (após gráfico) =========
        elements = _compliance_page(elements, theme, theme_key)
    
        # fundo por tema
        onpage = _page_bg_factory(theme_key)
        cover_frame(None, doc)
        doc.build(
            elements,
            onFirstPage=_cover_bg,          # fundo da capa
            onLaterPages=onpage             # fundo das demais páginas
        )
    
        return pdf_path
    
    
    # ---------- Botões ----------
    cols_btn = st.columns(2)
    with cols_btn[0]:
        if st.button("📄 Exportar PDF — Dark"):
            try:
                pdf_file = export_pdf_landscape(
                    "dark",
                    df_ops=df_ops, dados_enc=dados_enc,
                    lucro_total_pct=lucro_total_pct, media_pct_vencedoras=media_pct_vencedoras,
                    qtd_lucro=qtd_lucro, qtd_preju=qtd_preju, qtd_neutras=qtd_neutras,
                    media_dias=media_dias, media_stop_loss_pct=media_stop_loss_pct,
                    rent_fluxo_capital=rent_fluxo_capital, op_mais_lucr=op_mais_lucr,
                    data_inicio=data_inicio_close.strftime("%Y/%m/%d"),
                    data_fim=data_fim_close.strftime("%Y/%m/%d")
                )
                with open(pdf_file, "rb") as f:
                    st.download_button("⬇️ Baixar PDF (Dark)", f, file_name="Relatorio.pdf", mime="application/pdf")
                st.success("✅ PDF (Dark) gerado com sucesso!")
            except Exception as e:
                import traceback; st.error(f"Erro ao gerar PDF Dark: {e}"); st.code(traceback.format_exc())
    
    with cols_btn[1]:
        if st.button("📄 Exportar PDF — White"):
            try:
                pdf_file = export_pdf_landscape(
                    "white",
                    df_ops=df_ops, dados_enc=dados_enc,
                    lucro_total_pct=lucro_total_pct, media_pct_vencedoras=media_pct_vencedoras,
                    qtd_lucro=qtd_lucro, qtd_preju=qtd_preju, qtd_neutras=qtd_neutras,
                    media_dias=media_dias, media_stop_loss_pct=media_stop_loss_pct,
                    rent_fluxo_capital=rent_fluxo_capital, op_mais_lucr=op_mais_lucr,
                    data_inicio=data_inicio_close.strftime("%Y/%m/%d"),
                    data_fim=data_fim_close.strftime("%Y/%m/%d")
                )
                with open(pdf_file, "rb") as f:
                    st.download_button("⬇️ Baixar PDF (White)", f, file_name="Relatorio_White.pdf", mime="application/pdf")
                st.success("✅ PDF (White) gerado com sucesso!")
            except Exception as e:
                import traceback; st.error(f"Erro ao gerar PDF White: {e}"); st.code(traceback.format_exc())
    
    # =================================================
    # 🟨 OPERAÇÕES ABERTAS — DIRETRIZES DIÁRIAS
    # =================================================
    st.markdown("---")
    
    with st.expander("🟨 Performance Relativa dos Trades em Andamento", expanded=False):
    
        # ==================================
        # 🔵 FILTRO DE CARTEIRA (ÍNDICE)
        # ==================================
        opcoes_indice_open = ["Todas", "IBOV", "SMLL", "BDR"]
        indice_sel_open = st.selectbox(
            "Filtrar por carteira (índice)",
            opcoes_indice_open,
            index=0,
            key="filtro_indice_abertas"   # 🔥 chave única!
        )
    
    
    
        
    
        #st.markdown("### 🟨 Diretrizes Diárias (Operações Abertas)")
    
        # Carrega operações abertas diretamente do LOSS CURTO (fonte real)
        abertas = coletar_operacoes_abertas_loss_curto()
        abertas_enriquecidas = enriquecer_operacoes_abertas(abertas)
    
        # ==================================
        # 🔵 APLICAR FILTRO NAS OPERAÇÕES ABERTAS
        # ==================================
        if indice_sel_open != "Todas":
            abertas_enriquecidas = [
                x for x in abertas_enriquecidas
                if x.get("indice") == indice_sel_open
            ]
    
    
        # Ordena pelas mais recentes
        abertas_enriquecidas = sorted(
            abertas_enriquecidas,
            key=lambda x: x["data_abertura"],
            reverse=True
        )
    
        if not abertas_enriquecidas:
            st.info("Nenhuma operação aberta encontrada.")
        else:
    
            # Monta DataFrame
            df_open = pd.DataFrame([
                ({
                    **{
                        "Índice": x.get("indice"),
                        "Ticker": x["ticker"],
                        "Operação": x["operacao"].upper(),
                        "Preço Abertura": x["preco_abertura"],
                        "Preço Atual": x["preco_atual"],
                        "Stop Gain": x["stop_gain"],
                        "Stop Loss": x["stop_loss"],
                        "PnL (R$)": x["pnl"],
                        "PnL (%)": x["pnl_pct"],
                        "Dias": round(x["dur_days"], 2) if x["dur_days"] else None,
                        "Estado": x["estado"],
                        "_ord": x["data_abertura"],
                    }
                } | {
                    # normalização da data
                    "Data Abertura": (
                        (
                            datetime.datetime.fromisoformat(x["data_abertura"])
                            if isinstance(x["data_abertura"], str)
                            else x["data_abertura"]
                        ).strftime("%d/%m/%Y %H:%M")
                    )
                    if x["data_abertura"] else "—"
                })
                for x in abertas_enriquecidas
            ])
    
    
            df_open = df_open.sort_values("_ord", ascending=False).drop(columns=["_ord"])
    
            # Formatação
            money_cols = ["Preço Abertura", "Preço Atual", "Stop Gain", "Stop Loss", "PnL (R$)"]
            for col in money_cols:
                df_open[col] = df_open[col].apply(lambda v: f"R$ {v:,.2f}" if v not in (None, 0) else "—")
    
            df_open["PnL (%)"] = df_open["PnL (%)"].apply(lambda v: f"{v:.2f}%" if v else "—")
    
            st.dataframe(df_open, use_container_width=True, hide_index=True)
    
            # ===== Botões PDF =====
            cold, colw = st.columns(2)
    
            # ===== Normalização das datas para PDF =====
            datas_norm = []
            for x in abertas_enriquecidas:
                d = x["data_abertura"]
    
                # Converte string ISO → datetime
                if isinstance(d, str):
                    try:
                        d = datetime.datetime.fromisoformat(d)
                    except:
                        d = None
    
                # Aceita apenas datetime válidos
                if isinstance(d, datetime.datetime):
                    datas_norm.append(d)
    
            # Data início = menor data válida
            if datas_norm:
                data_inicio_txt = min(datas_norm).strftime("%Y/%m/%d")
            else:
                data_inicio_txt = "—"
    
            # Data fim = hoje (operações abertas não têm fechamento)
            data_fim_txt = agora_lx().strftime("%Y/%m/%d")
    
            with cold:
                if st.button("📄 Exportar PDF — Dark", key="export_pdf_dark_abertas"):
                    try:
                        pdf = export_pdf_abertas(
                            "dark",
                            df_ops_abertas=df_open,
                            abertas_enriquecidas=abertas_enriquecidas,
                            data_inicio_txt=data_inicio_txt,
                            data_fim_txt=data_fim_txt,
                        )
                        with open(pdf, "rb") as f:
                            st.download_button(
                                "⬇️ Baixar Relatório (Dark)", 
                                f,
                                file_name="Diretrizes_Diarias_Dark.pdf",
                                mime="application/pdf",
                                key="download_pdf_dark_abertas"
                            )
                        st.success("✅ PDF gerado com sucesso!")
                    except Exception as e:
                        import traceback
                        st.error(f"Erro ao gerar PDF (Dark): {e}")
                        st.code(traceback.format_exc())
            
            
            with colw:
                if st.button("📄 Exportar PDF — White", key="export_pdf_white_abertas"):
                    try:
                        pdf = export_pdf_abertas(
                            "white",
                            df_ops_abertas=df_open,
                            abertas_enriquecidas=abertas_enriquecidas,
                            data_inicio_txt=data_inicio_txt,
                            data_fim_txt=data_fim_txt,
                        )
                        with open(pdf, "rb") as f:
                            st.download_button(
                                "⬇️ Baixar Relatório (White)",
                                f,
                                file_name="Diretrizes_Diarias_White.pdf",
                                mime="application/pdf",
                                key="download_pdf_white_abertas"
                            )
                        st.success("✅ PDF gerado com sucesso!")
                    except Exception as e:
                        import traceback
                        st.error(f"Erro ao gerar PDF (White): {e}")
                        st.code(traceback.format_exc())
    
    
    
    # =========================
    # 📄 RELATÓRIO APIMEC — ATIVOS VIVOS (Curto / Curtíssimo)
    # =========================
    import io, os, datetime
    import pandas as pd
    import numpy as np
    import yfinance as yf
    import mplfinance as mpf
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from matplotlib.ticker import FuncFormatter
    
    # --- UTIL: pegar metadados do ROBOS
    def _get_robo_cfg(robo_key: str):
        cfg = next((r for r in ROBOS if r["key"] == robo_key), None)
        if not cfg:
            return None
        return {
            "sb_url": st.secrets.get(cfg["sb_url_secret"], ""),
            "sb_key": st.secrets.get(cfg["sb_key_secret"], ""),
            "sb_table": cfg["sb_table"],
            "sb_k": cfg["sb_key"],
            "title": cfg["title"],
        }
    
    # --- Lê ativos vivos no KV
    def ler_ativos_vivos(robo_key: str) -> list[dict]:
        cfg = _get_robo_cfg(robo_key)
        if not cfg: 
            return []
        v = ler_estado_supabase(cfg["sb_url"], cfg["sb_key"], cfg["sb_table"], cfg["sb_k"])
        ativos = v.get("ativos") or []
        norm = []
        for a in ativos:
            if isinstance(a, dict):
                t = str(a.get("ticker","")).upper().strip()
                op = str(a.get("operacao","")).lower().strip()
                pr = a.get("preco")
                if t and op in ("compra","venda") and isinstance(pr,(int,float)):
                    norm.append({"ticker":t,"operacao":op,"preco":float(pr)})
        return norm
    
    # --- Nome da empresa
    @st.cache_data(ttl=3600)
    def nome_empresa_yf(ticker_b3: str) -> str:
        try:
            tk = yf.Ticker(f"{ticker_b3}.SA")
    
            # 1) Tenta longName (preferido)
            try:
                long_name = tk.info.get("longName")
                if long_name and isinstance(long_name, str):
                    return long_name
            except:
                pass
    
            # 2) Tenta shortName
            try:
                short_name = tk.info.get("shortName")
                if short_name and isinstance(short_name, str):
                    return short_name
            except:
                pass
    
            # 3) Tenta nome via fast_info (novo Yahoo API)
            try:
                fast = tk.fast_info
                if fast and "longName" in fast and fast["longName"]:
                    return fast["longName"]
            except:
                pass
    
        except Exception:
            pass
        
        # fallback
        return ticker_b3
    
    
    # --- Indicadores
    def _ema(s, span): return s.ewm(span=span, adjust=False).mean()
    def _sma(s, w): return s.rolling(w).mean()
    def _rsi(close, period=14):
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100-(100/(1+rs))
    def _macd(close, fast=12, slow=26, signal=9):
        ef, es = _ema(close, fast), _ema(close, slow)
        line = ef-es
        sig = _ema(line, signal)
        return line, sig, line-sig
    
    def narrativa_cnpi(df, operacao, preco_alvo):
        # --- Remover último candle anômalo (volume zero ou variação extrema do Yahoo) ---
        if df["Volume"].iloc[-1] == 0 or (df["Close"].iloc[-1] < df["Close"].iloc[-2] * 0.8):
            df = df.iloc[:-1]
    
        # --- Volume financeiro = Volume * Preço ---
        vol_fin = (df["Volume"] * df["Close"]).iloc[-1]
        vol_fin_med = (df["Volume"] * df["Close"]).rolling(14).mean().iloc[-1]
        vol_rel = (vol_fin / vol_fin_med - 1) * 100 if vol_fin_med > 0 else 0
    
        # --- Demais indicadores (original preservado) ---
        close = df["Close"].iloc[-1]
        mm20 = df["Close"].rolling(20).mean().iloc[-1]
        rsi = _rsi(df["Close"]).iloc[-1]
    
        macd_l, macd_s, macd_h = _macd(df["Close"])
        macd_val = macd_l.iloc[-1]
        macd_sig = macd_s.iloc[-1]
    
        if pd.isna(mm20) or pd.isna(rsi) or pd.isna(vol_fin_med):
            return "Amostra insuficiente para leitura técnica completa. Ativo segue em monitoramento."
    
        txt_vol = (
            f"{vol_rel:.1f}% acima da média financeira de 14 períodos"
            if vol_fin > vol_fin_med else
            f"{abs(vol_rel):.1f}% abaixo da média financeira de 14 períodos"
        )
    
        # ======================
        # Narrativa COMPRA
        # ======================
       # ======================
        # Cálculos de Stop e Objetivo
        # ======================
        if operacao.lower() == "compra":
            stop = preco_alvo * 0.98   # -2%
            objetivo = preco_alvo * 1.03  # +3%
            stop_txt = f"stop técnico ({stop:.2f})"
            objetivo_txt = f"objetivo ({objetivo:.2f})"
    
    
            
            return (
                f"Preço atual em R$ {close:.2f}, operando {((close/mm20)-1)*100:.1f}% acima da MM20 (R$ {mm20:.2f}). "
                f"RSI em {rsi:.1f}, indicando força compradora sustentada. "
                f"MACD em {macd_val:.4f} acima da signal ({macd_sig:.4f}), reforçando momentum positivo. "
                f"Volume financeiro do dia em {vol_fin/1e6:.2f}M, {txt_vol}. "
                f"Cenário favorece posições compradas acima da MM20 com {stop_txt} "
                f"e {objetivo_txt} na região de topo recente."
            )
    
        if operacao.lower() == "venda":
            stop = preco_alvo * 1.02   # +2%
            objetivo = preco_alvo * 0.97  # -3%
            stop_txt = f"stop técnico ({stop:.2f})"
            objetivo_txt = f"objetivo ({objetivo:.2f})"
    
    
    
            return (
                f"Preço atual em R$ {close:.2f}, operando {((close/mm20)-1)*100:.1f}% abaixo da MM20 (R$ {mm20:.2f}). "
                f"RSI em {rsi:.1f}, sugerindo perda de força compradora e pressão vendedora. "
                f"MACD em {macd_val:.4f} abaixo da signal ({macd_sig:.4f}), indicando aceleração negativa. "
                f"Volume financeiro do dia em {vol_fin/1e6:.2f}M, {txt_vol}. "
                f"Estratégia favorece operações defensivas na ponta vendedora com {stop_txt} "
                f"e {objetivo_txt} na região de suporte recente."
            )
    
        return (
            f"Preço próximo à MM20 (R$ {mm20:.2f}). RSI em {rsi:.1f} e volume financeiro {txt_vol}. "
            f"Aguardar definição de direção com confirmação de volume."
        )
    
    
    
    
    # --- Interpretação
    def classificar_e_explicar(df):
        df = df.dropna().copy()
        if len(df) < 60:
            return ("compra","Amostra reduzida; preço e volume em observação no curto prazo.")
    
        c = df["Close"]
        v = df["Volume"]
    
        mm9 = _sma(c,9)
        mm20 = _sma(c,20)
        rsi = _rsi(c)
        macd_l, macd_s, _ = _macd(c)
        vol_rel = v / v.rolling(20).mean()
    
        last = c.iloc[-1]
        s_mm = (last > mm9.iloc[-1]) + (last > mm20.iloc[-1]) + (mm9.iloc[-1] > mm20.iloc[-1])
        s_rsi = (rsi.iloc[-1] > 55) - (rsi.iloc[-1] < 45)
        s_macd = (macd_l.iloc[-1] > macd_s.iloc[-1]) - (macd_l.iloc[-1] < macd_s.iloc[-1])
        s_vol = (vol_rel.iloc[-1] > 1.05) - (vol_rel.iloc[-1] < 0.9)
        score = (1 if s_mm>=2 else -1 if s_mm==0 else 0) + s_rsi + s_macd + s_vol
    
        bullets = []
        bullets.append("Preço acima da MM20 (tendência de alta)" if last>mm20.iloc[-1] else "Preço abaixo da MM20 (tendência de baixa)")
        bullets.append("MM9 > MM20 (viés comprador)" if mm9.iloc[-1]>mm20.iloc[-1] else "MM9 < MM20 (viés vendedor)")
        bullets.append("RSI ≥ 60 (momentum positivo)" if rsi.iloc[-1]>=60 else "RSI ≤ 40 (momentum negativo)" if rsi.iloc[-1]<=40 else "RSI neutro")
        bullets.append("MACD acima da signal" if macd_l.iloc[-1]>macd_s.iloc[-1] else "MACD abaixo da signal")
        bullets.append("Volume acima da média" if vol_rel.iloc[-1]>=1.2 else "Volume fraco" if vol_rel.iloc[-1]<=0.8 else "Volume em linha")
    
        if score >= 1:
            bullets.append("Entrada sugerida via rompimento/pullback; stop abaixo MM20; alvo topo recente")
            return ("compra",". ".join(bullets)+".")
        else:
            bullets.append("Entrada sugerida via pullback de baixa; stop acima MM20; alvo suporte")
            return ("venda",". ".join(bullets)+".")
    
    # --- Candle
    # --- Candle (versão simples que funcionava)
    # --- Candle (versão simples restaurada e corrigida)
    def _candles_png(ticker_b3: str, meses: int = 1) -> str | None:
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
    
            raw = yf.download(f"{ticker_b3}.SA", period="6mo", interval="1d", progress=False)
            if raw is None or raw.empty:
                return None
    
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = [c[0] for c in raw.columns]
    
            df = raw[["Open","High","Low","Close","Volume"]].dropna().copy()
            
            # --- Remover último candle bugado do Yahoo ---
            if len(df) > 2:
                last = df.iloc[-1]
                prev = df.iloc[-2]
            
                cond_volume_zero = last["Volume"] == 0
                cond_queda_irreal = last["Close"] < prev["Close"] * 0.8
                cond_gap_irreal = abs(last["Close"] - prev["Close"]) > prev["Close"] * 0.15
            
                if cond_volume_zero or cond_queda_irreal or cond_gap_irreal:
                    df = df.iloc[:-1]
            
            df["MM8"] = df["Close"].rolling(8).mean()
            df["MM50"] = df["Close"].rolling(50).mean()
            df["VolMM14"] = df["Volume"].rolling(14).mean()
            
            df = df.tail(70)
    
    
            dates = mdates.date2num(df.index.to_pydatetime())
            imgfile = f"_apimec_{ticker_b3}.png"
    
            fig = plt.figure(figsize=(6.4, 3))
            gs = fig.add_gridspec(5, 1, height_ratios=[4, 0.15, 1.8, 0.2, 0.1])
    
            ax_price = fig.add_subplot(gs[0, 0])
            ax_vol = fig.add_subplot(gs[2, 0], sharex=ax_price)
    
            navy = "#001A33"
            watermark = "#BFE4FF"  # azul gelo (muito claro)
    
            fig.patch.set_facecolor(navy)
            ax_price.set_facecolor(navy)
            ax_vol.set_facecolor(navy)
    
            # Marca d'água mais clara
            ax_price.text(
                0.5, 0.5, ticker_b3,
                fontsize=72, weight="bold", color=watermark, alpha=0.10,
                ha="center", va="center", transform=ax_price.transAxes
            )
    
            # Candles
            for i, (o, h, l, c) in enumerate(zip(df["Open"], df["High"], df["Low"], df["Close"])):
                color = "#06D6A0" if c >= o else "#EF476F"
                ax_price.plot([dates[i], dates[i]], [l, h], color=color, linewidth=1.7)
                ax_price.add_patch(
                    plt.Rectangle((dates[i] - 0.35, min(o, c)), 0.7, abs(o - c),
                                  color=color, ec=color)
                )
    
            # MM20 (fina azul)
            ax_price.plot(df.index, df["MM8"], color="#2E86FF", linewidth=1.2)
    
            # MM200 (garante render somente se existir valor)
            mm200 = df["MM50"].dropna()
            if not mm200.empty:
                ax_price.plot(mm200.index, mm200, color="#FFD700", linewidth=1.5, alpha=0.9)
    
            # Volume
            for i, (v, o, c) in enumerate(zip(df["Volume"], df["Open"], df["Close"])):
                color = "#06D6A0" if c >= o else "#EF476F"
                ax_vol.bar(dates[i], v, width=0.6, color=color)
            ax_vol.plot(df.index, df["VolMM14"], color="#C77DFF", linewidth=1.1)
    
            ax_price.axhline(ax_price.get_ylim()[0], color="#4F5D75", linewidth=1.3)
    
            ax_price.grid(which="major", linestyle="--", linewidth=0.35, alpha=0.30, color="#8AA1C1")
            ax_vol.grid(which="major", linestyle="--", linewidth=0.25, alpha=0.25, color="#8AA1C1")
    
            ax_price.yaxis.tick_right()
            ax_price.yaxis.set_major_formatter(lambda x,_: f"{x:.2f}")
            ax_price.tick_params(axis="y", labelsize=7, colors="white")
    
            ax_vol.set_yticks([])
    
            ax_price.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=6))
            ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
            ax_price.tick_params(axis="x", labelsize=6, rotation=0, colors="white")
            plt.setp(ax_vol.get_xticklabels(), fontsize=6, color="white")
    
            fig.subplots_adjust(left=0.04, right=0.97, top=0.97, bottom=0.22, hspace=0.05)
    
            fig.savefig(imgfile, dpi=350, bbox_inches="tight")
            plt.close(fig)
            return imgfile
    
        except Exception as e:
            print(f"[CANDLE ERROR] {ticker_b3} -> {e}")
            return None
    
    
    
    
    
    
    
    
    
    
    
    
    
    # --- Export PDF
    def export_pdf_apimec_vivos(
        robo_key,
        nome_analista,
        certificado_cnpi,
        cpf_analista
    ):
    
        ativos = ler_ativos_vivos(robo_key)
        if not ativos:
            raise RuntimeError("Nenhum ativo vivo encontrado.")
        
        data_hoje = datetime.date.today()
        filename = f"Relatorio_APIMEC_{robo_key}_{data_hoje}.pdf"
    
        buff = io.BytesIO()
        c = canvas.Canvas(buff, pagesize=landscape(A4))
        W, H = landscape(A4)
    
        # ========== LOOP DE PÁGINAS — UM ATIVO POR PÁGINA ==========
        for a in ativos:
            tk = a["ticker"]
            op = a["operacao"].upper()
            alvo = a["preco"]
            nome = nome_empresa_yf(tk)
    
            # --- Cabeçalho ---
            c.setFont("Helvetica-Bold", 14)
            c.drawString(2*cm, H-2*cm, "RELATÓRIO DE ANÁLISE — APIMEC")
    
            c.setFont("Helvetica", 10)
            c.drawString(2*cm, H-2.6*cm, f"Data: {data_hoje:%d/%m/%Y}")
            c.drawString(
                2*cm, H-3.1*cm,
                f"Analista: {nome_analista} — {certificado_cnpi}"
            )
    
            # --- Título ---
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2*cm, H-4*cm, f"{tk} — {nome}")
    
            # --- Tabela ---
            tbl = [
                ["Ticker", "Empresa", "Operação", "Preço alvo"],
                [tk, nome, op, f"R$ {alvo:,.2f}".replace(".", ",")]
            ]
    
            from reportlab.platypus import Table, TableStyle
            from reportlab.lib import colors
    
            col_w = (W - 4*cm) / 4
            t = Table(tbl, colWidths=[col_w]*4)
            t.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("ALIGN", (0,0), (-1,-1), "CENTER")
            ]))
            t.wrapOn(c, W, H)
            t.drawOn(c, 2*cm, H-6.5*cm)
    
            # --- Gráfico Candle ---
            imgfile = _candles_png(tk, meses=1)
            if imgfile and os.path.exists(imgfile):
                try:
                    c.drawImage(
                        ImageReader(imgfile),
                        2*cm, H-13*cm,
                        width=W-4*cm,
                        height=6*cm
                    )
                    c.setFont("Helvetica-Oblique", 7)
                    c.drawString(2*cm, H-13.4*cm,
                        'Fonte: disponível no website "yahoofinance.com"')
                except:
                    c.setFont("Helvetica-Oblique", 10)
                    c.drawString(2*cm, H-7.5*cm, "Erro ao carregar gráfico.")
                finally:
                    try: os.remove(imgfile)
                    except: pass
            else:
                c.setFont("Helvetica-Oblique", 10)
                c.drawString(2*cm, H-7.5*cm, "Gráfico indisponível.")
    
            # --- Interpretação técnica ---
            try:
                hist = yf.download(
                    f"{tk}.SA", period="1y", interval="1d", progress=False
                ).dropna()
    
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
    
                if len(hist) < 60 or "Close" not in hist.columns:
                    texto = "Amostra insuficiente para leitura técnica."
                else:
                    texto = narrativa_cnpi(hist, op.lower(), alvo)
    
            except:
                texto = "Amostra insuficiente para leitura técnica."
    
            # --- Recomendação ---
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2*cm, 6.3*cm, f"Recomendação: {op}")
    
            # --- Texto técnico ---
            c.setFont("Helvetica", 9)
            tx = c.beginText()
            tx.setTextOrigin(2*cm, 5.8*cm)
            tx.setLeading(12)
            for line in texto.split(". "):
                tx.textLine(line.strip() + ".")
            c.drawText(tx)
    
            # --- Rodapé ---
            c.setFont("Helvetica", 9)
            c.drawString(2*cm, 3.2*cm, f"{data_hoje:%d/%m/%Y}")
            c.drawString(
                2*cm, 2.8*cm,
                f"{nome_analista} ({certificado_cnpi})"
            )
            c.drawString(
                2*cm, 2.4*cm,
                f"CPF nº {cpf_analista}"
            )
    
            c.setFont("Helvetica-Oblique", 7)
            c.drawString(
                2*cm, 1.4*cm,
                "As recomendações refletem análise independente e não garantem resultados futuros."
            )
    
            c.showPage()
    
        # ===== Página Final =====
        from reportlab.platypus import Paragraph, Frame
        from reportlab.lib.styles import getSampleStyleSheet
    
        styles = getSampleStyleSheet()
        style_title = styles["Heading2"]
        style_title.fontSize = 12
    
        style_text = styles["Normal"]
        style_text.fontSize = 9
        style_text.leading = 14
    
        titulo = Paragraph("Declarações Importantes do Relatório", style_title)
    
        texto = (
            "Objetivo: compartilhar o melhor entendimento técnico sobre a ação na presente data.<br/><br/>"
            "As recomendações não constituem promessa de resultados futuros e não garantem rentabilidade.<br/><br/>"
            "As recomendações refletem exclusivamente a opinião independente do analista certificado.<br/><br/>"
            "Stop Loss: nível máximo de perda; pode não ser respeitado em gaps.<br/><br/>"
            "Stop Gain: alvo técnico estimado para realização parcial ou total da operação.<br/><br/>"
            f"Analista responsável: <b>{nome_analista}</b> — <b>{certificado_cnpi}</b><br/>"
            f"CPF: <b>{cpf_analista}</b><br/><br/>"
            f"Código interno: <b>{datetime.date.today():%d%m%Y}</b>"
        )
    
        paragrafo = Paragraph(texto, style_text)
    
        frame = Frame(
            2*cm, 2*cm,
            W - 4*cm, H - 4*cm,
            showBoundary=0
        )
        frame.addFromList([titulo, paragrafo], c)
        c.showPage()
    
        # ==== Finaliza ====
        c.save()
    
        with open(filename, "wb") as f:
            f.write(buff.getvalue())
        buff.close()
        return filename
    
    # 🔽 Espaço entre Operações Abertas e Área Restrita APIMEC
    
    st.markdown("---")
    st.caption("© Painel Visual Aurinvest — todos os direitos são reservados")
    st.markdown("------")
    
    # =================================================
    # 🔒 ÁREA RESTRITA — LOGIN APENAS PARA ANALISTAS
    # =================================================
    
    st.markdown("### 🔐 Área restrita — Relatório Técnico APIMEC")
    
    st.markdown("""
    Esta seção é **exclusiva para profissionais certificados**, habilitados a emitir
    relatórios técnicos conforme as normas vigentes da APIMEC e CVM.
    
    Para continuar, insira suas credenciais de acesso.
    """)
    
    # credenciais simples (pode alterar)
    APIMEC_USER = "analista"
    APIMEC_PASS = "1234"
    
    # inicializa o estado
    if "auth_apimec" not in st.session_state:
        st.session_state.auth_apimec = False
    
    # Se não está logado → mostrar login
    if not st.session_state.auth_apimec:
    
        user = st.text_input("Usuário", key="login_apimec_user")
        pwd  = st.text_input("Senha", key="login_apimec_pwd", type="password")
    
        if st.button("Entrar", key="login_apimec_btn"):
            if user == APIMEC_USER and pwd == APIMEC_PASS:
                st.session_state.auth_apimec = True
                st.success("Acesso permitido!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    
        st.stop()  # impede mostrar o expander antes de logar
    
    # =================================================
    # RELATÓRIO APIMEC EM EXPANDER
    # =================================================
    st.markdown("---")
    with st.expander("📑 Relatório APIMEC", expanded=False):
    
        st.markdown("### 📑 Relatório APIMEC")
    
        # ===========================
        # 🧑‍💼 DADOS DO ANALISTA (PARTE 1)
        # ===========================
    # ===========================
    # 🧑‍💼 DADOS DO ANALISTA
    # ===========================
    st.markdown("### 🧑‍💼 Dados do Analista APIMEC")
    
    nome_analista = st.text_input("Nome completo do analista")
    certificado_cnpi = st.text_input("Número do certificado CNPI", placeholder="Ex: CNPI EM-12345")
    cpf_analista = st.text_input("CPF do analista", placeholder="Ex: 123.456.789-00")
    
    dados_ok = nome_analista and certificado_cnpi and cpf_analista
    
    # ===========================
    # RADIO (apenas 1 opção)
    # ===========================
    carteira = st.radio(
        "Selecione a carteira",
        ["Monitoramento dos Trades Pendentes"],
        horizontal=True,
        key="carteira_apimec"
    )
    
    _map = {
        "Monitoramento dos Trades Pendentes": "curto"
    }
    
    # Botão PDF
    if st.button("📄 Gerar Relatório APIMEC (PDF)"):
    
        if not dados_ok:
            st.error("Preencha nome, CNPI e CPF antes de gerar o relatório.")
        else:
            try:
                robo_key = _map[carteira]
    
                pdf = export_pdf_apimec_vivos(
                    robo_key,
                    nome_analista=nome_analista,
                    certificado_cnpi=certificado_cnpi,
                    cpf_analista=cpf_analista                
                )
    
                with open(pdf, "rb") as f:
                    st.download_button(
                        "⬇️ Baixar APIMEC",
                        f,
                        file_name=pdf,
                        mime="application/pdf"
                    )
    
                st.success("✅ Relatório APIMEC gerado com sucesso!")
    
            except Exception as e:
                st.error(f"Erro: {e}")
