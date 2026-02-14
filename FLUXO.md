# Fluxo da Aplicação — Consulta SAP IW23

## Visão Geral

A aplicação permite que qualquer pessoa consulte informações de uma Nota no SAP
(transação IW23) direto pelo navegador, sem precisar mexer no SAP manualmente.

Ela funciona em **três partes** que conversam entre si:

```
┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────┐
│  Streamlit Cloud    │       │  Agente Local (.exe) │       │   SAP GUI   │
│  (Página Web)       │──────▶│  (Roda na máquina    │──────▶│  (Aberto e  │
│                     │       │   do usuário)        │       │   logado)   │
│  Onde o usuário     │       │                      │       │             │
│  digita a nota e    │◀──────│  Recebe o pedido,    │◀──────│  Retorna o  │
│  vê o resultado     │       │  executa no SAP e    │       │  título da  │
│                     │       │  devolve o resultado │       │  nota       │
└─────────────────────┘       └─────────────────────┘       └─────────────┘
     INTERNET                   MÁQUINA DO USUÁRIO            MÁQUINA DO USUÁRIO
```

---

## Passo a Passo (o que acontece quando o usuário clica "Consultar")

### 1. O usuário abre a página no navegador

- A página está hospedada no **Streamlit Cloud** (internet).
- Ela é só uma interface visual: um campo de texto e um botão.
- O Streamlit Cloud **não** acessa o SAP. Ele só mostra a tela.

### 2. O usuário digita o número da nota e clica "Consultar"

- O navegador do usuário executa um pequeno código JavaScript (JS).
- Esse JS faz uma **requisição HTTP** (tipo uma "mensagem") para `http://localhost:8080`.
- `localhost` significa "a própria máquina do usuário". Ou seja: **a chamada não vai para a internet, fica local**.

### 3. O Agente Local recebe a requisição

- O `agente.exe` é um pequeno servidor web que roda na máquina do usuário.
- Ele fica "escutando" na porta 8080, esperando alguém mandar um pedido.
- Quando recebe `{"nota": "1234567"}`, ele sabe o que fazer: ir ao SAP.

### 4. O Agente executa a ação no SAP GUI

- O agente usa uma tecnologia chamada **COM (Component Object Model)** do Windows.
- COM permite que um programa controle outro programa — neste caso, o SAP GUI.
- O agente faz exatamente o que um humano faria:
  1. Digita `IW23` na barra de transação do SAP.
  2. Pressiona Enter.
  3. Preenche o campo "Número da Nota" com o valor recebido.
  4. Pressiona Enter novamente.
  5. Lê o campo "Título" (texto curto) da nota.

### 5. O resultado volta para o navegador

- O agente monta uma resposta: `{"status": "ok", "nota": "1234567", "titulo": "Trocar válvula..."}`.
- Essa resposta viaja de volta para o JavaScript no navegador.
- O JS exibe o resultado na tela: **"✅ Nota: 1234567 — Título: Trocar válvula..."**.

---

## Por que funciona assim?

| Pergunta | Resposta |
|----------|---------|
| Por que não acessar o SAP direto da nuvem? | O SAP GUI é um programa Windows que roda na máquina do usuário. Não dá para controlar ele de um servidor na internet. |
| Por que precisa do agente.exe? | Porque o navegador sozinho não consegue controlar o SAP. O agente é a "ponte" entre a página web e o SAP GUI. |
| O agente precisa de internet? | Não. Ele só conversa com o navegador localmente (localhost) e com o SAP GUI na mesma máquina. |
| Os dados passam pela internet? | A página vem da internet, mas a consulta ao SAP (nota e título) **fica 100% na máquina do usuário**. Nenhum dado do SAP sai para a nuvem. |
| Precisa instalar Python? | Não. O `agente.exe` já contém tudo embutido (Python, bibliotecas, servidor web). |

---

## Tecnologias Usadas

| Componente | Tecnologia | O que faz |
|------------|-----------|-----------|
| Página Web | **Streamlit** (Python) | Interface visual: campo de texto, botão, resultado |
| Hospedagem | **Streamlit Cloud** | Serve a página na internet, acessível por qualquer navegador |
| Chamada local | **JavaScript (fetch)** | Código que roda no navegador e manda o pedido para localhost:8080 |
| Agente Local | **FastAPI** (Python) | Servidor web mínimo que recebe o pedido e aciona o SAP |
| Automação SAP | **pywin32 (COM)** | Controla o SAP GUI como se fosse um usuário digitando |
| Empacotamento | **PyInstaller** | Transforma o agente Python em um `.exe` único, sem dependências |

---

## Resumo em uma frase

> A página na nuvem é só a "cara" da aplicação; o trabalho pesado (consultar o SAP)
> acontece na máquina do usuário, através de um pequeno programa (.exe) que é a
> ponte entre o navegador e o SAP GUI.
---
---

# Fluxo do Projeto Real — Criação de Ordem de Manutenção com IA

## Visão Geral

O projeto real estende o teste inicial. O usuário informa uma lista de notas de manutenção,
os dados são buscados no **SAP Datasphere**, analisados por uma **IA (LLM via LangChain)**,
e exibidos para revisão. Após aprovação manual, o agente local cria a ordem no SAP GUI.

```
┌─────────────────────────────────────────────────────────────┐
│                      STREAMLIT CLOUD                        │
│                                                             │
│  1. Usuário informa lista de notas                          │
│              │                                              │
│              ▼                                              │
│  2. Backend Python consulta Datasphere (API REST / SQL)     │
│              │                                              │
│              ▼                                              │
│  3. LangChain + LLM analisa os dados retornados             │
│              │                                              │
│              ▼                                              │
│  4. Exibe resultado para revisão manual do usuário          │
│              │                                              │
│              ▼                                              │
│  5. Usuário revisa, ajusta e clica "Criar Ordem"            │
│              │                                              │
└──────────────┼──────────────────────────────────────────────┘
               │  JS fetch → localhost:8080
               ▼
┌─────────────────────────────────────────────────────────────┐
│                    MÁQUINA DO USUÁRIO                        │
│                                                             │
│  6. Agente Local (.exe) recebe dados da ordem               │
│              │                                              │
│              ▼                                              │
│  7. Executa script SAP (COM) → Cria Ordem no SAP GUI        │
│              │                                              │
│              ▼                                              │
│  8. Retorna confirmação (nº da ordem criada)                │
└─────────────────────────────────────────────────────────────┘
```

---

## Passo a Passo Detalhado

### 1. Entrada de dados (Streamlit Cloud)

- O usuário abre a página no navegador (hospedada no Streamlit Cloud).
- Informa uma **lista de notas de manutenção** (campo de texto, upload de planilha, etc.).
- Clica em **"Consultar"**.

### 2. Consulta ao Datasphere (Streamlit Cloud → Datasphere)

- O servidor Python (Streamlit) se conecta ao **SAP Datasphere** via API REST ou SQL.
- Busca os dados das notas informadas: descrição, equipamento, localização, histórico, etc.
- Toda essa comunicação acontece **na nuvem** — não depende da máquina do usuário.

### 3. Análise por IA (Streamlit Cloud → LLM)

- Os dados retornados do Datasphere são enviados para uma **LLM (Large Language Model)** via LangChain.
- A IA analisa os dados e retorna, por exemplo:
  - Classificação/priorização das notas.
  - Sugestão de tipo de ordem, centro de trabalho, materiais.
  - Resumo técnico para o planejador.
- A LLM roda na nuvem (OpenAI, Azure OpenAI, Google Gemini, etc.) — **não se comunica com o agente local nem com o SAP GUI**.

### 4. Revisão manual (Streamlit Cloud)

- O frontend exibe os resultados da IA em uma tabela editável.
- O usuário pode **revisar, ajustar ou corrigir** os dados sugeridos pela IA.
- Nenhuma ação é executada no SAP até o usuário confirmar.

### 5. Criação da Ordem (Navegador → Agente Local → SAP GUI)

- O usuário clica **"Criar Ordem"**.
- O navegador faz um `fetch` para `http://localhost:8080` (agente local na máquina dele).
- O agente local recebe os dados revisados (tipo de ordem, nota, equipamento, descrição, etc.).

### 6. Execução no SAP GUI (Agente Local → SAP)

- O agente executa um **script SAP via COM (pywin32)**:
  - Abre a transação de criação de ordem (ex.: IW31).
  - Preenche os campos com os dados recebidos.
  - Confirma a criação.
  - Lê o número da ordem criada.
- Retorna a confirmação ao navegador: `{"status": "ok", "ordem": "400012345"}`.

### 7. Confirmação (Navegador)

- O frontend exibe: **"✅ Ordem 400012345 criada com sucesso"**.
- O log é salvo para auditoria.

---

## Onde cada coisa roda

| Etapa | Onde roda | Tecnologia | Precisa do agente? |
|-------|-----------|------------|--------------------|
| Entrada de notas | Nuvem (Streamlit Cloud) | Streamlit | Não |
| Consulta Datasphere | Nuvem (Streamlit Cloud) | API REST / hdbcli / SQL | Não |
| Análise com IA | Nuvem (Streamlit Cloud) | LangChain + LLM | Não |
| Revisão manual | Nuvem (Streamlit Cloud) | Streamlit (tabela editável) | Não |
| Criação de Ordem no SAP | Local (máquina do usuário) | agente.exe + pywin32 COM | **Sim** |

---

## Pontos-chave

| Pergunta | Resposta |
|----------|---------|
| A IA acessa o SAP? | **Não.** A IA só processa dados que vieram do Datasphere. Ela não se comunica com o agente local nem com o SAP GUI. |
| Os dados do SAP passam pela internet? | Na consulta ao Datasphere, sim (conexão segura via API). Na criação da ordem, **não** — os dados vão do navegador direto para localhost. |
| O agente local precisa de internet? | **Não.** Ele só recebe dados do navegador (localhost) e executa no SAP GUI local. |
| Posso usar sem a IA? | Sim. A etapa de IA é opcional — o Datasphere retorna os dados e o usuário pode revisar direto, sem análise automática. |

---

## Tecnologias do Projeto Real

| Componente | Tecnologia | Onde roda |
|------------|-----------|-----------|
| Frontend | **Streamlit** | Streamlit Cloud |
| Banco de dados | **SAP Datasphere** | Nuvem SAP |
| Inteligência Artificial | **LangChain + LLM** (OpenAI/Azure/Gemini) | Nuvem (API) |
| Agente Local | **FastAPI + pywin32** empacotado com PyInstaller | Máquina do usuário |
| Automação SAP | **pywin32 (COM)** — script Python controlando SAP GUI | Máquina do usuário |

---

## Resumo em uma frase

> O Streamlit Cloud cuida de toda a inteligência (dados + IA + revisão); o agente local
> só entra no final, quando o usuário confirma a criação da ordem — aí o .exe executa
> o script no SAP GUI da máquina dele.