# Teste FastAPI + Streamlit com SAP IW23

## Pré-requisitos
- Windows com SAP GUI instalado e Scripting habilitado (cliente e servidor).
- Python no venv do projeto: `env/` (já configurado).

## Instalação
```powershell
# Ativar venv (PowerShell)
& "${PWD}\env\Scripts\Activate.ps1"

# Instalar dependências
pip install -r requirements.txt
```

## Executar backend (FastAPI)
```powershell
# Usando o Python do venv
& "${PWD}\env\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port 8080
```

## Executar frontend (Streamlit)
```powershell
& "${PWD}\env\Scripts\python.exe" -m streamlit run frontend.py
```

## Fluxo de teste
1. Certifique-se de que o SAP GUI está aberto, logado e com Scripting habilitado.
2. No Streamlit, informe a nota e clique em **Consultar**.
3. O frontend dispara um `fetch` para `http://localhost:8080/consultar_sap` (POST JSON `{ nota, token }`) com cabeçalho `X-Trigger: 1`.
4. O resultado é retornado e gravado em `?resultado=...` na URL; o Streamlit lê e exibe.

## Ajuste dos IDs (SAP Scripting)
- Abra o Gravador de Scripting do SAP GUI e capture os IDs dos campos da IW23 (número da notificação e título).
- Substitua o placeholder em `sap_client.py` (comentário "Código SAP aqui") com os IDs reais, por exemplo:
  - `wnd[0]/usr/ctxtVIQMEL-QMNUM` para o número (exemplo; pode variar).
  - `wnd[0]/usr/txtVIQMEL-KURZTEXT` para o título (exemplo; pode variar).

## Observações
- CORS está restrito às origens do Streamlit (`http://localhost:8501`, `http://127.0.0.1:8501`).
- Em caso de erro, o backend retorna `{"status": "erro", "detalhe": "..."}`; o frontend exibe a mensagem.

## Token e segurança
- Backend exige `token` igual a `SAP_TOKEN` (env) e cabeçalho `X-Trigger: 1` para executar a consulta.
- Defina `SAP_TOKEN` antes de iniciar:
```powershell
$env:SAP_TOKEN = "DEV"
```
- Teste via PowerShell:
```powershell
$body = @{ nota = "123456"; token = "DEV" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8080/consultar_sap" -Method Post -Body $body -ContentType "application/json" -Headers @{ "X-Trigger" = "1" }
```
