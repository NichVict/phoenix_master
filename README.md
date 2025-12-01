

---

🦅 PROJETO FÊNIX – DOCUMENTO MESTRE DO SISTEMA

Versão 1.0 — Arquitetura e Fluxo do Fênix Premium


---

1️⃣ Fluxo Completo do Sistema

Login → CRM → Sidebar → Dashboard → Acesso → Upgrades


---

2️⃣ SISTEMA DE LOGIN (PASSO 1)

Objetivo: permitir que o cliente acesse o app com segurança, usando Google ou Magic Link (e-mail).

2.1 — Login com Google

Botão: Entrar com Google

Supabase Auth retorna o e-mail

Sessão salva em:

st.session_state["user"]


2.2 — Login com Magic Link

Cliente digita o e-mail

App executa:

supabase.auth.sign_in_with_otp({"email": email})

Supabase envia link automático

O link cria sessão → usuário autenticado


2.3 — Após login

Redirecionar direto para o Dashboard Geral

Sidebar só aparece depois de logado

Páginas sem login → bloqueadas



---

3️⃣ INTEGRAÇÃO COM O CRM (PASSO 2)

Após login, buscamos as carteiras associadas ao usuário.

3.1 — Exemplo de busca

{
  "email": "cliente@teste.com",
  "carteiras": ["IBOV", "SMALL", "OPCOES"]
}

3.2 — Armazenamento da sessão

st.session_state["carteiras_usuario"] = carteiras


---

4️⃣ SIDEBAR DINÂMICO (PASSO 3)

A Sidebar mostra somente as carteiras que o cliente assinou.

4.1 — Estrutura padrão

📊 Dashboard Geral
------------------------
(Se assinou) Carteira IBOV
(Se assinou) Carteira BDR
(Se assinou) Carteira Small Caps
(Se assinou) Carteira de Opções
------------------------
📚 Assinar outras carteiras

4.2 — Exemplo de lógica

if "IBOV" in carteiras:
    st.sidebar.page_link("pages/ibov.py", label="Carteira IBOV")


---

5️⃣ DASHBOARD GERAL (PASSO 4)

Primeira tela após login.
Exibe 4 cards principais:

IBOV

BDR

Small Caps

Opções


5.1 — Cards Liberados

Se o cliente assinou:

Card colorido

Resumo da carteira

Botão: Abrir Carteira


5.2 — Cards Bloqueados

Se não assinou:

Card cinza

Botão: Assinar Agora


O Dashboard funciona como vitrine premium.


---

6️⃣ PÁGINAS INDIVIDUAIS (PASSO 5)

Cada carteira vira um arquivo em /pages/.

/pages/ibov.py
/pages/bdr.py
/pages/small.py
/pages/opcoes.py

Cada página contém:

filtros

rodadas

tabela

scores

FS

setup

radar


(Toda essa estrutura já existe no app atual; só será modularizada.)


---

7️⃣ PROTEÇÃO DE ACESSO (PASSO 6)

Se o cliente tentar acessar algo que não assinou:

if "IBOV" not in carteiras_usuario:
    st.error("Você não assinou esta carteira.")
    st.stop()

A página fica bloqueada.


---

8️⃣ DEEP LINK INTELIGENTE (PASSO 7)

Permite acesso direto via link externo (WhatsApp, e-mail etc.).

Exemplo:

/app?carteira=IBOV

Fluxo:

Se já está logado → abre IBOV direto

Se não está → faz login → volta automaticamente para IBOV


UX premium.


---

9️⃣ RESUMO ESTRATÉGICO DO SISTEMA

✔ Login → cria sessão
✔ CRM → define carteiras permitidas
✔ Sidebar → dinâmica
✔ Dashboard → vitrine premium
✔ Páginas individuais → modulares
✔ Proteção → sem acesso indevido
✔ Deep link → navegação inteligente


---

🔟 PLANO DE EXECUÇÃO (DIA A DIA)

🚀 Dia 1 — Tela de Login

Google

Magic Link

Sessão Supabase

Redirecionamento automático


🚀 Dia 2 — Integração CRM

Mock local

Rotina real via API


🚀 Dia 3 — Sidebar Dinâmico

Exibe apenas carteiras assinadas


🚀 Dia 4 — Dashboard Geral

4 cards

Cards bloqueados → botão “Assinar”


🚀 Dia 5 — Páginas das Carteiras

IBOV

BDR

Small

Opções


🚀 Dia 6 — Proteção por assinatura

require_login()

require_carteira()


🚀 Dia 7 — Finalização

Deep link

UX Premium

Organização

Performance



---

🧩 Documento Oficial – Versão 1.0

Arquitetura completa do Fênix Premium, pronta para implementação.


---

Se quiser, eu também posso:

✅ Transformar esse documento em PDF
✅ Criar uma versão para README.md padrão GitHub
✅ Criar a estrutura inicial do projeto (pastas + arquivos)
✅ Criar o roadmap detalhado de desenvolvimento

Só dizer: “Quero agora”.



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
