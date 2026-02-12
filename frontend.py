import streamlit as st

st.set_page_config(page_title="Consulta SAP IW23", layout="centered")

st.title("Consulta de Nota (IW23)")

# --- Download do Agente Local ---
# Configure o link em .streamlit/secrets.toml ou como variável de ambiente
# Exemplo: AGENTE_URL = "https://drive.google.com/uc?export=download&id=SEU_ID"
AGENTE_URL = st.secrets.get("AGENTE_URL", "") if hasattr(st, "secrets") else ""
if AGENTE_URL:
    st.link_button("⬇ Baixar Agente Local (.exe)", AGENTE_URL)
else:
    st.info("Link do agente local não configurado. Defina AGENTE_URL em secrets.")

st.divider()

# --- Consulta ---
nota = st.text_input("Número da nota", value="", placeholder="Ex.: 1234567")
consultar = st.button("Consultar")

if consultar and nota.strip():
    # JS fetch roda no NAVEGADOR do usuário → chama localhost:8080 (agente local dele)
    html = f"""
    <div id="resultado" style="font-family:sans-serif; font-size:14px; padding:8px;"></div>
    <script>
    (function() {{
        var el = document.getElementById('resultado');
        el.textContent = '⏳ Consultando SAP...';
        fetch('http://localhost:8080/consultar_sap', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{nota: '{nota.strip()}'}})
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
            if (data.status === 'ok') {{
                el.innerHTML = '<b style="color:green">✅ Nota: ' + data.nota + '<br>Título: ' + data.titulo + '</b>';
            }} else {{
                el.innerHTML = '<b style="color:red">❌ Erro: ' + (data.detalhe || 'desconhecido') + '</b>';
            }}
        }})
        .catch(function(err) {{
            el.innerHTML = '<b style="color:red">❌ Agente local indisponível.<br>Verifique se o agente.exe está rodando.</b>';
        }});
    }})();
    </script>
    """
    st.components.v1.html(html, height=80)

# Botão para limpar
if st.button("Limpar"):
    st.rerun()
