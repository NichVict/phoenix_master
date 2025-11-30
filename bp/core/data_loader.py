import pandas as pd
import yfinance as yf
import requests
import os

CSV_PATH = "data/tickers_ibov.csv"


# ------------------------------------------------------------
# 1. Buscar composição oficial do IBOV (B3)
# ------------------------------------------------------------
def fetch_ibov_from_b3():
    """
    Captura a lista oficial de componentes do IBOV direto da B3.
    Totalmente compatível com Streamlit Cloud.
    """
    url = "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetDetailIndex?language=pt-BR&index=IBOV"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()

        tickers = [item["codNegociacao"].upper() + ".SA" for item in data["results"]]
        tickers = sorted(list(set(tickers)))

        return tickers

    except Exception as e:
        print(f"[ERRO] Falha ao capturar IBOV da B3: {e}")
        return []


# ------------------------------------------------------------
# 2. Atualizar CSV local de tickers
# ------------------------------------------------------------
def update_ticker_file():
    # garantir que a pasta exista (Streamlit apaga no reboot)
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

    tickers = fetch_ibov_from_b3()

    if len(tickers) == 0:
        print("[!] IBOV não carregado — usando CSV atual.")
        return

    df = pd.DataFrame({"ticker": tickers})
    df.to_csv(CSV_PATH, index=False)

    print(f"[OK] Lista do IBOV atualizada com {len(tickers)} ativos.")



# ------------------------------------------------------------
# 3. Carregar lista do IBOV (com fallback)
# ------------------------------------------------------------
def load_universe():
    """
    Carrega a lista de tickers do IBOV com blindagem TOTAL.
    Nunca quebra.
    """

    # 1 — arquivo não existe
    if not os.path.exists(CSV_PATH):
        print("[!] CSV não encontrado — criando a lista do IBOV…")
        update_ticker_file()

    # 2 — arquivo ainda não existe após tentativa
    if not os.path.exists(CSV_PATH):
        print("[ERRO] Falha ao criar CSV. Retornando lista vazia.")
        return []

    # 3 — arquivo existe mas pode estar vazio
    if os.path.getsize(CSV_PATH) == 0:
        print("[!] CSV está vazio — recriando…")
        update_ticker_file()

    try:
        df = pd.read_csv(CSV_PATH)

        if df.empty or "ticker" not in df.columns:
            print("[!] CSV inválido — reconstruindo…")
            update_ticker_file()
            df = pd.read_csv(CSV_PATH)

        tickers = df["ticker"].dropna().unique().tolist()

        if len(tickers) == 0:
            print("[!] CSV sem tickers — reconstruindo…")
            update_ticker_file()
            df = pd.read_csv(CSV_PATH)
            tickers = df["ticker"].dropna().unique().tolist()

        return tickers

    except Exception as e:
        print(f"[ERRO] Falha ao ler CSV ({e}) — reconstruindo…")
        update_ticker_file()
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
            return df["ticker"].dropna().unique().tolist()
        return []




# ============================================================
# 4. Função CRUCIAL — baixar dados de um ticker
# ============================================================
def get_ticker_data(ticker, period="2y", interval="1d"):
    """
    Baixa dados do yfinance com BLINDAGEM TOTAL.
    Funciona para ações do Brasil e BDRs.
    Nunca retorna DataFrame 2D.
    Nunca retorna vazio.
    """

    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        if df is None or df.empty:
            print(f"[!] Dados vazios para {ticker}")
            return None

        # --- Correção Maikinho: remover colunas multi-index (2D) ---
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # --- Garantir OHLCV ---
        required = ["Open", "High", "Low", "Close", "Volume"]
        for col in required:
            if col not in df.columns:
                print(f"[!] {ticker}: coluna ausente → {col}")
                return None

        # --- Coerção para 1D ---
        for col in required:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # --- Remover linhas completamente inválidas mas sem apagar tudo ---
        df = df[df["Close"].notna()]

        # Se tiver poucos dados, rejeitar
        if len(df) < 30:
            print(f"[!] {ticker}: poucos candles ({len(df)}).")
            return None

        # --- Garantir volume válido ---
        if df["Volume"].sum() == 0:
            print(f"[!] {ticker}: volume zerado, ignorado.")
            return None

        return df

    except Exception as e:
        print(f"[ERRO] ao baixar {ticker}: {e}")
        return None


# ============================================================
# 5. Função de validação final (mantida p/ compatibilidade)
# ============================================================
def validate_data(df):
    """
    Validação simples para evitar erros downstream.
    """
    if df is None:
        return False

    if df.empty:
        return False

    required = ["Open", "High", "Low", "Close", "Volume"]
    for col in required:
        if col not in df.columns:
            return False

    return True
