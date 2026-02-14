# PLANO_NUVEM.md — Plano de Execução do Projeto Real

## Objetivo

Criar uma aplicação modular hospedada no Streamlit Cloud que:
1. Recebe uma lista de notas de manutenção.
2. Consulta dados no SAP Datasphere.
3. Analisa o texto das notas com IA (Azure OpenAI) para extrair delineamento.
4. Apresenta resultado estruturado para revisão manual.
5. Cria ordens de manutenção no SAP GUI via agente local (.exe).

---

## Arquitetura Modular

```
frontend.py  (Orquestrador — Streamlit Cloud)
    │
    ├── auth.py                  → Login e controle de acesso
    │
    ├── consulta_notas.py        → Consulta ao Datasphere
    │
    ├── extrair_delineamento.py  → Análise por IA (Azure OpenAI / LangChain)
    │
    └── JS fetch → localhost:8080
            │
            ▼
        agente.exe  (Máquina do usuário)
            │
            ├── criar_ordens.py  → Script SAP de criação de ordem (COM/pywin32)
            │
            └── (módulos futuros)
```

---

## Módulos

### 1. `auth.py` — Autenticação e Controle de Acesso

**Responsabilidade:** Gerenciar login, sessão e permissões.

**Funcionalidades:**
- Tela de login com campos: **Chave** e **Senha**.
- Validação contra tabela `usuarios` no **Supabase** (PostgreSQL).
- Cadastro: usuário informa Chave + Lotação → fica pendente até admin aprovar.
- Aprovação gera senha provisória (bcrypt) → troca obrigatória no 1o login.
- Controle de sessão via `st.session_state`.
- Painel admin (aba no mesmo Streamlit) para aprovar/revogar/resetar acessos.
- Perfis: **operador** (acesso restrito à sua lotação) e **admin** (gerencia tudo).

**Decisões resolvidas:**
- ✅ Armazenamento de usuários: **Supabase** (tabela `usuarios`).
- ✅ Fluxo de aprovação: **Painel admin no próprio Streamlit**.
- ✅ Senha: provisória gerada pelo sistema, troca obrigatória no 1o login.
- ✅ Hash: **bcrypt**.
- ✅ Admin inicial: seed direto no Supabase.
- ⏳ Expiração de sessão: a definir (por ora, sessão dura enquanto aba aberta).

---

### 2. `consulta_notas.py` — Consulta ao SAP Datasphere

**Responsabilidade:** Receber lista de notas e retornar dados estruturados do Datasphere.

**Interface esperada:**
```python
def consultar_notas(lista_notas: list[str]) -> pd.DataFrame:
    """
    Recebe lista de números de notas.
    Retorna DataFrame com colunas: nota, texto_longo, equipamento, 
    localizacao, tipo_nota, prioridade, data_criacao, ...
    """
```

**Opções de conexão (a definir):**
- API REST com OAuth2
- Conector Python SAP HANA (`hdbcli`)
- ODBC/JDBC

**Decisões pendentes:**
- Credenciais de acesso ao Datasphere (guardadas em Streamlit secrets).
- Quais campos/colunas retornar além do texto longo.
- Há views prontas no Datasphere ou precisa criar?
- Volume: quantas notas por consulta (10? 100? 1000?)?

---

### 3. `extrair_delineamento.py` — Análise por IA

**Responsabilidade:** Analisar o texto longo das notas e extrair delineamento estruturado.

**Interface esperada:**
```python
def extrair_delineamento(texto_nota: str) -> dict:
    """
    Analisa texto longo de uma nota de manutenção.
    Retorna dicionário estruturado com:
    - descricao_atividade: str    → O que deve ser feito
    - especialidades: list[str]   → Ex.: ["Mecânica", "Elétrica"]
    - qtd_pessoas: int            → Quantidade estimada de pessoas
    - hh_estimado: float          → Horas-homem estimadas
    - materiais: list[str]        → Lista de materiais necessários
    - observacoes: str            → Informações adicionais
    """
```

**Tecnologias:**
- **Azure OpenAI** — provedor de LLM.
- **LangChain** — orquestração de prompts, output parsing, retry.
- **Pydantic** — validação da saída estruturada.

**Abordagem:**
- Prompt engenharia com exemplos (few-shot) para o modelo entender o padrão dos textos de manutenção.
- Output parser estruturado (JSON) para garantir formato consistente.
- Fallback: se a IA não conseguir extrair, retorna campos vazios com flag "revisão necessária".

**Decisões pendentes:**
- Modelo: GPT-4o, GPT-4o-mini, ou outro disponível no Azure?
- Processar nota a nota ou em lote (batch)?
- Limites de tokens / custo por consulta.
- Campos exatos do delineamento (a detalhar pelo usuário).
- Prompt base (precisa de exemplos reais de textos de notas para calibrar).

---

### 4. `criar_ordens.py` — Script SAP de Criação de Ordem

**Responsabilidade:** Receber dados revisados e criar ordem de manutenção no SAP GUI via COM.

**Interface esperada:**
```python
def criar_ordem(dados: dict) -> dict:
    """
    Recebe dicionário com campos da ordem.
    Executa script SAP (transação a definir).
    Retorna {"status": "ok", "ordem": "400012345"} ou erro.
    """
```

**Integração com o agente:**
- Este módulo será **embutido no agente.exe** (inline ou importado).
- O agente expõe endpoint `POST /criar_ordem` que chama `criar_ordem()`.
- O frontend envia via JS fetch para `localhost:8080/criar_ordem`.

**Decisões pendentes:**
- Transação SAP: IW31? IW21? Outra?
- Campos a preencher (o usuário criará o script).
- Criar uma ordem por vez ou várias em sequência?
- Tratamento de erro no SAP (tela de erro, campos obrigatórios faltando).

---

### 5. `frontend.py` — Orquestrador (Streamlit Cloud)

**Responsabilidade:** Coordenar todo o fluxo e apresentar a interface.

**Fluxo de telas:**

```
[Login]
   │ auth.py
   ▼
[Tela Principal]
   │
   ├── Entrada: lista de notas (text_area ou upload CSV/Excel)
   │
   ├── Botão "Consultar Datasphere"
   │       │ consulta_notas.py
   │       ▼
   │   Exibe dados brutos em tabela
   │
   ├── Botão "Analisar com IA"
   │       │ extrair_delineamento.py
   │       ▼
   │   Exibe delineamento estruturado (tabela editável)
   │
   ├── Revisão manual pelo usuário
   │       │ Edita campos diretamente na tabela
   │       ▼
   │
   ├── Botão "Criar Ordens"
   │       │ JS fetch → localhost:8080/criar_ordem
   │       ▼
   │   Exibe confirmação (nº das ordens criadas)
   │
   └── [Painel Admin] (se usuário for admin)
           │ auth.py
           ▼
       Aprovar/revogar acessos
```

**O `frontend.py` como orquestrador:**
- Importa os módulos (`auth`, `consulta_notas`, `extrair_delineamento`).
- Controla o estado da aplicação via `st.session_state`.
- Gerencia a navegação entre telas (login → consulta → IA → revisão → criação).
- A parte de criação de ordem (JS fetch) é a única que sai do servidor e vai para o navegador/agente local.

---

## Estrutura de Arquivos

```
projeto-real/
├── frontend.py                  # Orquestrador Streamlit
├── auth.py                      # Autenticação e controle de acesso
├── consulta_notas.py            # Consulta ao Datasphere
├── extrair_delineamento.py      # Análise por IA (Azure OpenAI)
├── requirements.txt             # Dependências do Streamlit Cloud
├── .streamlit/
│   ├── config.toml              # Configuração do Streamlit
│   └── secrets.toml             # Chaves (Azure OpenAI, Datasphere, usuários)
├── FLUXO.md                     # Documentação do fluxo
│
├── agente/                      # Código do agente local (separado)
│   ├── agente.py                # Servidor FastAPI local
│   ├── criar_ordens.py          # Script SAP de criação de ordem
│   └── build.py                 # Empacotamento PyInstaller
│
└── dist/
    └── agente.exe               # Executável gerado
```

---

## Etapas de Execução

### Fase 1 — Estrutura e Autenticação
- [x] Criar estrutura modular de arquivos.
- [x] Implementar `auth.py` (login com Chave/Senha, controle de sessão, Supabase + bcrypt).
- [x] Implementar `admin.py` (painel admin para aprovação/revogação/reset de usuários).
- [x] Definir armazenamento de usuários autorizados → **Supabase**.
- [x] Configurar `frontend.py` como orquestrador com navegação entre telas.
- [ ] Criar projeto Supabase e executar SQL de criação da tabela.
- [ ] Configurar secrets (`SUPABASE_URL`, `SUPABASE_KEY`) no Streamlit Cloud.
- [ ] Fazer seed do primeiro admin no Supabase.
- [ ] Testar fluxo completo (cadastro → aprovação → login → troca de senha).

### Fase 2 — Consulta ao Datasphere
- [ ] Definir método de conexão (API REST / hdbcli / ODBC).
- [ ] Implementar `consulta_notas.py`.
- [ ] Testar consulta com notas reais.
- [ ] Exibir dados retornados em tabela no frontend.

### Fase 3 — Análise por IA
- [ ] Configurar Azure OpenAI (endpoint, API key, modelo).
- [ ] Implementar `extrair_delineamento.py` com LangChain.
- [ ] Criar prompt base com exemplos de textos de manutenção.
- [ ] Definir schema de saída estruturada (Pydantic).
- [ ] Testar com textos reais e ajustar prompt.
- [ ] Exibir resultado em tabela editável no frontend.

### Fase 4 — Criação de Ordem no SAP
- [ ] Criar script SAP de criação de ordem (transação a definir).
- [ ] Implementar `criar_ordens.py`.
- [ ] Integrar ao `agente.py` (novo endpoint `POST /criar_ordem`).
- [ ] Rebuild do `agente.exe` com PyInstaller.
- [ ] Testar criação de ordem via frontend completo.

### Fase 5 — Integração e Testes
- [ ] Teste ponta a ponta: login → consulta → IA → revisão → criação.
- [ ] Teste com outro usuário (colega).
- [ ] Deploy no Streamlit Cloud.
- [ ] Ajustes de UX e tratamento de erros.

---

## Dependências (requirements.txt — Streamlit Cloud)

```
streamlit
langchain
langchain-openai
pandas
pydantic
# Datasphere (a definir):
# hdbcli          → se usar conector Python SAP HANA
# requests        → se usar API REST
```

---

## Secrets (`.streamlit/secrets.toml`)

```toml
# Azure OpenAI
AZURE_OPENAI_ENDPOINT = ""
AZURE_OPENAI_API_KEY = ""
AZURE_OPENAI_DEPLOYMENT = ""
AZURE_OPENAI_API_VERSION = "2024-02-01"

# Datasphere (a definir)
# DATASPHERE_HOST = ""
# DATASPHERE_USER = ""
# DATASPHERE_PASSWORD = ""

# Supabase (autenticação de usuários)
SUPABASE_URL = ""
SUPABASE_KEY = ""  # service_role key
```

---

## Decisões em Aberto

| # | Decisão | Status |
|---|---------|--------|
| 1 | Método de conexão ao Datasphere | A definir |
| 2 | Modelo Azure OpenAI (GPT-4o / GPT-4o-mini) | A definir |
| 3 | Campos exatos do delineamento | A detalhar |
| 4 | Transação SAP de criação de ordem | Usuário criará o script |
| 5 | Armazenamento de usuários autorizados | ✅ **Supabase** (tabela `usuarios`) |
| 6 | Fluxo de aprovação de novos usuários | ✅ Painel admin no Streamlit |
| 7 | Volume de notas por consulta | A definir |
| 8 | Processar IA por nota ou em lote | A definir |
