## Plano: Autenticação de Usuários com Supabase

O sistema de autenticação será construído como o módulo `auth.py` (Fase 1 do PLANO_NUVEM.md), usando **Supabase** como banco na nuvem. O fluxo é: usuário solicita cadastro (chave + lotação) → admin aprova e recebe senha provisória gerada → usuário loga e é obrigado a trocar a senha no primeiro acesso. Dois perfis: **operador** (acesso só à sua unidade) e **admin** (gerencia usuários). O painel admin será uma aba no mesmo app Streamlit, visível somente para admins. O primeiro admin é inserido via seed direto no Supabase.

### Modelo de dados (Supabase / PostgreSQL)

Tabela `usuarios`:

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | uuid (PK, default) | ID interno |
| `chave` | text (unique, not null) | Identificador do funcionário |
| `lotacao` | text (not null) | Unidade/lotação (texto livre) |
| `senha_hash` | text | Hash bcrypt da senha |
| `perfil` | text (default 'operador') | `'operador'` ou `'admin'` |
| `status` | text (default 'pendente') | `'pendente'`, `'ativo'`, `'revogado'` |
| `trocar_senha` | boolean (default true) | Flag: obriga troca no próximo login |
| `criado_em` | timestamptz (default now()) | Data da solicitação |
| `aprovado_em` | timestamptz | Data da aprovação |
| `aprovado_por` | text | Chave do admin que aprovou |

### Steps

**1. Configurar projeto Supabase**
- Criar projeto gratuito no [supabase.com](https://supabase.com).
- Criar a tabela `usuarios` com o schema acima (via SQL Editor do Supabase).
- Desabilitar RLS (Row Level Security) inicialmente ou configurar service_role key para acesso irrestrito do backend (o Streamlit Cloud é o único cliente).
- Fazer seed do primeiro admin: `INSERT INTO usuarios (chave, lotacao, senha_hash, perfil, status, trocar_senha) VALUES ('CHAVE_ADMIN', 'LOTACAO', '<hash_bcrypt>', 'admin', 'ativo', false);`

**2. Configurar secrets no Streamlit**
- Adicionar no `.streamlit/secrets.toml` (local) e nos Secrets do Streamlit Cloud:
  - `SUPABASE_URL` — URL do projeto Supabase
  - `SUPABASE_KEY` — `service_role` key (não a anon key, pois vamos manipular dados sem RLS)
- Adicionar `supabase` e `bcrypt` ao requirements.txt (versão cloud).

**3. Criar `auth.py` — módulo de autenticação**

Funções principais:

- `tela_login()` — Renderiza formulário com campos Chave e Senha. Valida contra Supabase (`status='ativo'`). Se `trocar_senha=true`, redireciona para tela de troca. Armazena sessão em `st.session_state` (`usuario`, `perfil`, `lotacao`, `logado`).

- `tela_cadastro()` — Formulário com campos Chave e Lotação. Insere registro na tabela `usuarios` com `status='pendente'`, `senha_hash=null`. Exibe mensagem "Cadastro enviado, aguarde aprovação do administrador".

- `tela_trocar_senha()` — Formulário com campo Nova Senha + Confirmação. Atualiza `senha_hash` e seta `trocar_senha=false`.

- `verificar_sessao()` — Checa `st.session_state` para saber se usuário está logado. Chamada no início do `frontend.py`.

- `logout()` — Limpa `st.session_state`.

- `gerar_senha_provisoria()` — Gera string aleatória de 8 caracteres (letras + números) usando `secrets` stdlib. Retorna (senha_texto, senha_hash_bcrypt).

- `hash_senha(senha)` / `verificar_senha(senha, hash)` — Wrappers de `bcrypt`.

**4. Criar painel admin (dentro de `auth.py` ou `admin.py`)**

Função `tela_admin()`, renderizada como aba/menu no `frontend.py` apenas quando `st.session_state.perfil == 'admin'`:

- **Lista de solicitações pendentes**: Query `SELECT * FROM usuarios WHERE status='pendente'`. Tabela com colunas Chave, Lotação, Data Solicitação. Botão "Aprovar" por linha → gera senha provisória, atualiza `status='ativo'`, grava `senha_hash`, `aprovado_em`, `aprovado_por`. Exibe a senha provisória gerada na tela para o admin copiar e repassar ao usuário. Botão "Rejeitar" → deleta o registro ou seta `status='rejeitado'`.

- **Lista de usuários ativos**: Query `SELECT * FROM usuarios WHERE status='ativo'`. Tabela com Chave, Lotação, Perfil, Data Aprovação. Ações: "Revogar acesso" (`status='revogado'`), "Resetar senha" (gera nova provisória + `trocar_senha=true`), "Promover a admin" / "Rebaixar a operador".

- **Lista de usuários revogados**: Visualização + opção de reativar.

**5. Integrar ao `frontend.py` (orquestrador)**

Modificar frontend.py para:
- Importar `auth`.
- No início: chamar `verificar_sessao()`. Se não logado → exibir `tela_login()` com link para `tela_cadastro()`.
- Se logado e `trocar_senha=true` → exibir `tela_trocar_senha()`.
- Se logado normalmente → exibir tela principal (funcionalidade atual).
- Se `perfil == 'admin'` → exibir opção de menu/aba "Administração" que renderiza `tela_admin()`.
- Usar `st.sidebar` para navegação (Login/Cadastrar, e depois Consulta/Admin/Logout).

**6. Controle de acesso por lotação**

- Armazenar `lotacao` na `st.session_state` após login.
- Nas futuras consultas ao Datasphere (Fase 2), filtrar resultados pela lotação do usuário logado.
- Admins poderão ver dados de todas as unidades (sem filtro de lotação).

**7. Atualizar dependências e docs**

- Adicionar ao requirements-cloud.txt: `supabase`, `bcrypt`.
- Atualizar PLANO_NUVEM.md: resolver decisões #5 (Supabase) e #6 (fluxo de aprovação via painel admin no Streamlit).
- Criar SQL de criação da tabela para documentação.

### Fluxo completo do usuário

```
Novo usuário                          Admin
    │                                   │
    ├─ Acessa o app                     │
    ├─ Clica "Cadastrar"               │
    ├─ Digita Chave + Lotação          │
    ├─ Recebe "Aguarde aprovação"      │
    │                                   │
    │                    ┌──────────────┤
    │                    │ Acessa aba Admin
    │                    │ Vê solicitação pendente
    │                    │ Clica "Aprovar"
    │                    │ Sistema gera senha provisória
    │                    │ Admin copia e repassa ao usuário
    │                    └──────────────┤
    │                                   │
    ├─ Recebe senha provisória (fora do sistema)
    ├─ Faz login com Chave + Senha provisória
    ├─ É redirecionado para trocar senha
    ├─ Define nova senha
    ├─ Acessa o sistema normalmente
    │  (vê somente dados de sua lotação)
```

### Verificação

- **Teste de cadastro**: Solicitar cadastro → verificar registro `pendente` no Supabase.
- **Teste de aprovação**: Admin aprova → verificar `status='ativo'`, senha provisória exibida.
- **Teste de login**: Logar com provisória → tela de troca aparece. Após troca, acesso normal.
- **Teste de permissão**: Operador não vê aba Admin. Admin vê.
- **Teste de revogação**: Revogar usuário → login retorna erro.
- **Teste de lotação**: Operador vê só dados da sua unidade (validar nas fases futuras do Datasphere).

### Decisões tomadas

| Decisão | Escolha |
|---|---|
| Armazenamento de usuários | **Supabase** (PostgreSQL gerenciado) |
| Fluxo de aprovação | Painel admin no mesmo app Streamlit |
| Perfis | Operador (acesso por unidade) e Admin (gerencia tudo) |
| Senha | Provisória gerada pelo sistema na aprovação; troca obrigatória no 1o login |
| Lotação | Campo texto livre digitado pelo usuário |
| Admin inicial | Seed direto no Supabase |
| Hash de senha | bcrypt |
