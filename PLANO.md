# Plano de Ação: Teste FastAPI + Streamlit com SAP IW23

Criaremos um backend FastAPI que expõe `POST /consultar_sap` em `localhost:8080` com CORS `*`, recebendo uma nota e consultando o SAP GUI via `pywin32` na transação IW23 para ler o título. O frontend Streamlit terá um campo de nota e botão “Consultar”, disparando um `fetch` (JS) via `st.components.v1.html`. O resultado retornará ao Streamlit atualizando parâmetros da URL (query params), que o app lê para exibir na tela. Decisões: método `POST` com JSON, CORS liberado, retorno ao Streamlit por query params, e placeholder “Código SAP aqui” no wrapper SAP até receber os IDs/labels exatos.

## Etapas
1. Dependências
   - Adicionar `requirements.txt` com FastAPI, `uvicorn[standard]`, Streamlit, `pywin32`, `pydantic`.
   - Instalar no `env` do workspace e validar importação.

2. Servidor FastAPI
   - Criar `server.py` com `FastAPI` e `CORSMiddleware` (`origins=*`, `methods=*`, `headers=*`).
   - Definir modelo `ConsultaRequest` (`nota: str`) e endpoint `POST /consultar_sap`.
   - Em `consultar_sap()`: validar a nota, chamar `sap_client.consultar_nota(nota)` e retornar JSON com `nota`, `titulo`, `status` ou erro.

3. Wrapper SAP GUI
   - Criar `sap_client.py` usando `win32com.client` e `pythoncom`.
   - Implementar `consultar_nota(nota: str) -> str`: inicializar COM, obter `SAPGUI` → `Application` → `Connection` → `Session`, navegar para IW23, preencher a nota e ler o título.
   - Inserir comentário: “Código SAP aqui” onde entram os IDs de scripting.
   - Tratar exceções (sessão/fields ausentes, scripting desativado, etc.) com mensagens claras.

4. Interface Streamlit
   - Criar `frontend.py` com `st.text_input("Número da nota")` e `st.button("Consultar")`.
   - Ao clicar: renderizar `st.components.v1.html` com JS `fetch` para `http://localhost:8080/consultar_sap` (POST JSON `{ nota }`).
   - No `then(...)`: atualizar `window.location.search` com `resultado=<valor-encode>` para recarregar.
   - No Python: ler `resultado` via `st.query_params` (ou `st.experimental_get_query_params()`), decodificar e exibir; incluir ação para limpar parâmetros/estado.

5. Configuração e Resiliência
   - Confirmar CORS `*` no backend.
   - Adicionar logs básicos e mensagens de erro para SAP indisponível/scripting desativado.
   - Documentar pré‑requisitos: SAP GUI instalado, scripting habilitado (cliente e servidor), compatibilidade de arquitetura (x86/x64) com Python/pywin32.

6. Ajustes de Scripting (pós‑setup)
   - Usar o Gravador de Scripting do SAP GUI para capturar `session.findById(...)` dos campos IW23 (nº da notificação e título).
   - Substituir o placeholder “Código SAP aqui” em `sap_client.py` com os IDs fornecidos.

7. Verificação
   - Backend: iniciar em `localhost:8080`, testar `POST` com JSON e observar CORS, logs e respostas.
   - SAP: com SAP GUI aberto e logado, confirmar navegação IW23 e leitura do título.
   - Frontend: acionar consulta, verificar recarregamento com `?resultado=...` e exibição do título; testar limpeza.
   - Erros: validar mensagens para SAP fechado, scripting desativado, ou nota inexistente.

## Tasks
- [ ] Definir e criar `requirements.txt` com as dependências.
- [ ] Implementar `server.py` com `FastAPI`, CORS e `POST /consultar_sap`.
- [ ] Implementar `sap_client.py` com `consultar_nota()` e o placeholder “Código SAP aqui”.
- [ ] Implementar `frontend.py` com campo de nota, botão e `st.components.v1.html` (JS `fetch`).
- [ ] Instalar dependências no `env` e validar importação.
- [ ] Testar backend isolado com `POST` de exemplo.
- [ ] Testar frontend → backend → SAP ponta-a-ponta.
- [ ] Capturar IDs com o Gravador e substituir o placeholder em `sap_client.py`.
- [ ] Revisar mensagens de erro e logs; ajustar UX.
- [ ] Documentar pré‑requisitos e passos de execução no README.