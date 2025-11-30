import schedule
import time
from datetime import datetime
from bp.bp_runner import run_cycle


# ------------------------------------------------------------
# Verificar se estamos no horário do pregão
# ------------------------------------------------------------
def market_is_open():
    """
    Retorna True se estiver dentro do horário do pregão.
    Horário aproximado: 10h às 17h (Brasília).
    """
    now = datetime.now()
    hour = now.hour
    minute = now.minute

    # Ajustável se quiser maior precisão
    return (hour > 9 and hour < 17) or (hour == 17 and minute <= 0)


# ------------------------------------------------------------
# Função executada pelo agendador
# ------------------------------------------------------------
def scheduled_task():
    """
    Executa o ciclo do BP-Fênix somente se o mercado estiver aberto.
    """
    print("\n⏱️  Verificando horário do mercado...")

    if market_is_open():
        print("🟢 Mercado aberto — executando ciclo BP-Fênix.")
        run_cycle()
    else:
        print("🔴 Mercado fechado — aguardando próximo horário.")


# ------------------------------------------------------------
# Agendamento a cada 15 minutos
# ------------------------------------------------------------
def start_scheduler():
    """
    Inicia o scheduler para rodar o BP a cada 15 minutos.
    """
    print("⏳ Iniciando scheduler do BP-Fênix...")
    schedule.every(15).minutes.do(scheduled_task)

    print("🟦 Scheduler ativo. Aguardando ciclo...")

    while True:
        schedule.run_pending()
        time.sleep(1)

