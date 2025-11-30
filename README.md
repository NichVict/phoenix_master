# 🦅 Projeto Fênix – Módulo BP (Busca Primordial)

Este repositório contém o módulo *BP – Busca Primordial*, parte integrante do Projeto Fênix.

O BP é responsável por:

- varrer automaticamente ações e ETFs do Índice Bovespa  
- calcular indicadores técnicos e de volume  
- avaliar 5 critérios fundamentais  
- pontuar cada ativo (score 0–5)  
- selecionar os 5 melhores ativos do ciclo  
- exibir logs e visualização avançada via Streamlit  
- futuramente enviar recomendações ao robô principal do Fênix  

## 📌 Estado atual
Este é o esqueleto inicial do sistema.  
Os módulos serão preenchidos gradualmente conforme o desenvolvimento.

## 📁 Estrutura
- `bp/core/` → Lógica interna (indicadores, critérios, score, loader)
- `bp/ui/` → Visualização no Streamlit
- `bp/tests/` → Testes básicos
- `data/` → Arquivos auxiliares

## 🚀 Próximos passos
1. Implementar `data_loader.py`  
2. Implementar `indicators.py`  
3. Implementar `criteria_engine.py`  
4. Implementar `scoring.py`  
5. Criar primeira versão em Streamlit  
