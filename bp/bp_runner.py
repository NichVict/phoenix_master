import time
from bp.core.data_loader import load_universe, get_ticker_data, validate_data
from bp.core.indicators import apply_all_indicators
from bp.core.criteria_engine import evaluate_all_criteria
from bp.core.scoring import calculate_score
from bp.core.selectors import select_top_assets


# ------------------------------------------------------------
# Função principal do BP-Fênix (um único ciclo)
# ------------------------------------------------------------
def run_cycle():
    """
    Executa um ciclo completo do BP-Fênix:
    - carrega tickers (universo IBOV)
    - baixa dados
    - calcula indicadores
    - avalia critérios
    - calcula scores
    - seleciona top ativos
    """

    results = {}

    # 1 — carregar universo de ativos do IBOV
    tickers = load_universe()
    print(f"\n🟦 INICIANDO CICLO BP-FÊNIX")
    print(f"Carregando {len(tickers)} tickers do universo...\n")

    for ticker in tickers:
        print(f"🔍 Processando {ticker}...")

        # 2 — baixar dados
        df = get_ticker_data(ticker)

        if not validate_data(df):
            print(f"⚠️ Dados inválidos para {ticker}. Pulando...\n")
            continue

        # 3 — aplicar indicadores
        df = apply_all_indicators(df)

        # 4 — avaliar critérios
        criteria = evaluate_all_criteria(df)

        # 5 — calcular score
        score = calculate_score(criteria)

        # armazenar
        results[ticker] = score

        print(f"➡️ Score {ticker}: {score['score']}")
        print("-" * 50)

        time.sleep(0.2)

    # 6 — selecionar top ativos
    top_assets = select_top_assets(results)

    print("\n🟩 ATIVOS SELECIONADOS PELO BP-FÊNIX:")
    for asset in top_assets:
        print(f"  • {asset['ticker']} | Score {asset['score']}")

    print("\nCiclo completo.\n")

    return {
        "raw_results": results,
        "top_assets": top_assets
    }
