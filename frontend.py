import streamlit as st
from auth import verificar_sessao, get_usuario, tela_login, tela_cadastro, tela_trocar_senha, logout
from admin import tela_admin

st.set_page_config(page_title="SmartOM", layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------------------
# CSS Global — Fonte Inter + Sidebar com menu estilizado + Header
# ---------------------------------------------------------------------------

st.markdown("""
<style>
/* ── Google Font Inter ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Aplica Inter em todo o app */
html, body, [class*="css"], .stMarkdown, .stTextInput label,
.stButton button, .stRadio label, .stSelectbox label,
.stTabs button, input, textarea, select {
    font-family: 'Inter', sans-serif !important;
    font-weight: 400;
}

/* ── Sidebar — fundo cinza claro ── */
section[data-testid="stSidebar"] {
    background-color: #f4f5f7;
    padding-top: 1rem;
}

section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span {
    color: #475569;
    font-size: 0.82rem;
}

/* ── Botões de menu na sidebar ── */
div[data-testid="stSidebar"] .stButton > button {
    background-color: transparent;
    border: none;
    color: #475569;
    padding: 10px 16px;
    margin: 2px 0;
    border-radius: 8px;
    width: 100%;
    text-align: left;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500;
    font-size: 0.92rem;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    gap: 8px;
}

div[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #e2e8f0;
    color: #1e293b;
    border: none;
}

div[data-testid="stSidebar"] .stButton > button:focus {
    box-shadow: none;
    border: none;
}

/* ── Botão ativo (menu selecionado) — usa type=primary ── */
div[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background-color: #2563eb !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border: none !important;
}

div[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background-color: #1d4ed8 !important;
    color: #ffffff !important;
    border: none !important;
}

/* Ícone Material do botão ativo = branco */
div[data-testid="stSidebar"] .stButton > button[kind="primary"] span[data-testid="stIconMaterial"] {
    color: #ffffff !important;
}

/* ── Botão Sair ── */
div[data-testid="stSidebar"] .menu-logout > div > .stButton > button {
    color: #dc2626 !important;
}

div[data-testid="stSidebar"] .menu-logout > div > .stButton > button:hover {
    background-color: #fee2e2 !important;
    color: #b91c1c !important;
}

/* ── User info box ── */
.user-info {
    padding: 0 16px 12px 16px;
    border-bottom: 1px solid #d1d5db;
    margin-bottom: 12px;
}

.user-info p {
    margin: 2px 0;
    font-size: 0.8rem;
    color: #6b7280;
}

.user-info .user-name {
    color: #1e293b !important;
    font-weight: 600;
    font-size: 0.9rem;
}

/* ── Separador sidebar ── */
div[data-testid="stSidebar"] hr {
    border-color: #d1d5db;
    margin: 8px 16px;
}

/* ── Header da Visualização ── */
.page-header {
    padding: 20px 0 16px 0;
    border-bottom: 2px solid #e2e8f0;
    margin-bottom: 100px;
}

.page-header h1 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.75rem !important;
    color: #1e293b;
    margin: 0 0 4px 0;
    line-height: 1.2;
}

.page-header .subtitle {
    font-family: 'Inter', sans-serif !important;
    font-weight: 400;
    font-size: 0.9rem;
    color: #64748b;
    margin: 0;
}

/* ── Conteúdo principal ── */
.main .block-container {
    padding-top: 1rem;
    max-width: 1100px;
}

/* ── Títulos gerais ── */
h1, h2, h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
}

h4, h5, h6 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
}

/* ── Aproxima coluna de ações (olho) do dataframe ── */


</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Roteamento de autenticação
# ---------------------------------------------------------------------------

if st.session_state.get("tela") == "cadastro":
    tela_cadastro()
    st.stop()

if not verificar_sessao():
    tela_login()
    st.stop()

usuario = get_usuario()
if usuario and usuario["trocar_senha"]:
    tela_trocar_senha()
    st.stop()

# ---------------------------------------------------------------------------
# Restaura layout wide (desfaz inline styles da tela de auth)
# ---------------------------------------------------------------------------
st.components.v1.html("""
<script>
(function() {
    function fix() {
        var doc = window.parent.document;
        var els = doc.querySelectorAll('[data-testid="stMainBlockContainer"], .block-container');
        els.forEach(function(el) {
            el.style.removeProperty('max-width');
            el.style.removeProperty('width');
            el.style.removeProperty('padding-top');
            el.style.removeProperty('margin-left');
            el.style.removeProperty('margin-right');
            el.style.removeProperty('padding-left');
            el.style.removeProperty('padding-right');
        });
    }
    fix();
    setTimeout(fix, 100);
})();
</script>
""", height=0)


# ---------------------------------------------------------------------------
# Definição de páginas (ícone, label, subtítulo)
# ---------------------------------------------------------------------------

PAGINAS = [
    {"key": "consulta", "icon": ":material/search:", "label": "Extrair Notas", "subtitle": "Consulta de notas de manutenção via IW23"},
]

if usuario["perfil"] == "admin":
    PAGINAS.append(
        {"key": "admin", "icon": ":material/settings:", "label": "Administração", "subtitle": "Gestão de usuários e acessos do sistema"}
    )

if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "consulta"


# ---------------------------------------------------------------------------
# Sidebar — Menu com ícones e active state
# ---------------------------------------------------------------------------

with st.sidebar:
    # Info do usuário
    st.markdown(f"""
    <div class="user-info">
        <p class="user-name">👤 {usuario['chave']}</p>
        <p>{usuario['lotacao']}</p>
        <p style="text-transform: capitalize;">{usuario['perfil']}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # Botões de menu com ícones Material Symbols (nativo Streamlit)
    for pag in PAGINAS:
        is_active = st.session_state["pagina_atual"] == pag["key"]
        btn_type = "primary" if is_active else "secondary"

        if st.button(pag["label"], key=f"menu_{pag['key']}", icon=pag["icon"], type=btn_type, use_container_width=True):
            st.session_state["pagina_atual"] = pag["key"]
            st.rerun()

    st.markdown("---")

    # Botão Sair
    if st.button("Sair", key="btn_logout", icon=":material/logout:", use_container_width=True):
        logout()
        st.rerun()


# ---------------------------------------------------------------------------
# Área de Visualização — Header + Conteúdo
# ---------------------------------------------------------------------------

pagina_atual = st.session_state["pagina_atual"]
pag_info = next((p for p in PAGINAS if p["key"] == pagina_atual), PAGINAS[0])

# Header da página
st.markdown(f"""
<div class="page-header">
    <h1>{pag_info['label']}</h1>
    <p class="subtitle">{pag_info['subtitle']}</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Conteúdo das páginas
# ---------------------------------------------------------------------------

if pagina_atual == "admin" and usuario["perfil"] == "admin":
    tela_admin()

elif pagina_atual == "consulta":
    col_notas, col_resultado = st.columns([1, 7])

    # Coluna esquerda — entrada de notas
    with col_notas:
        st.text("Notas (uma por linha)")
        notas_texto = st.text_area(
            "Notas (uma por linha)",
            height=280,
            placeholder="10001234\n10005678\n10009012\n...",
            key="input_notas",
            label_visibility="collapsed",
        )

        # CSS para scrollbar auto-hide na text_area
        st.markdown("""
        <style>
        div[data-testid="stTextArea"] textarea {
            scrollbar-width: thin;
            scrollbar-color: transparent transparent;
            transition: scrollbar-color 0.3s;
        }
        div[data-testid="stTextArea"] textarea:hover {
            scrollbar-color: #94a3b8 transparent;
        }
        </style>
        """, unsafe_allow_html=True)

    # Coluna direita — dataframe de resultados
    with col_resultado:
        import pandas as pd

        # Dataframe de exemplo (placeholder)
        df_exemplo = pd.DataFrame({
            "Sel": [False, False, False, False, False, False, False],
            "Nota": ["10001234", "10005678", "10009012", "10003456", "10007890", "10002345", "10006789"],
            "Operação": ["0010", "0020", "0010", "0030", "0010", "0020", "0010"],
            "Exec": ["01", "02", "01", "03", "02", "01", "03"],
            "HH": ["2.50", "1.00", "4.00", "0.50", "3.00", "1.50", "2.00"],
            "Txt Breve Operação": ["Vazamento na bomba", "Troca de rolamento", "Inspeção válvula", "Reparo elétrico", "Alinhamento turbina", "Calibração transm.", "Substituição gaxeta"],
            "Materiais": [
                ["Parafuso M10", "Junta 3/4"],
                ["Rolamento 6205", "Graxa EP"],
                [],
                ["Cabo 2.5mm", "Disjuntor 20A", "Borne"],
                ["Calço 0.5mm"],
                ["Kit calibração"],
                ["Gaxeta 1/2", "Prensa gaxeta"],
            ],
        })

        # Sub-colunas: dataframe + coluna de ações (ícone olho)
        col_df, col_acoes = st.columns([20, 1])

        with col_df:
            st.text("Dados extraídos")
            st.data_editor(
                df_exemplo,
                use_container_width=True,
                hide_index=True,
                disabled=["Nota", "Operação", "Materiais"],
                column_config={
                    "Sel": st.column_config.CheckboxColumn(
                        label="",
                        width=45,
                        default=False,
                    ),
                    "Nota": st.column_config.TextColumn(
                        label="Nota",
                        width=90,
                    ),
                    "Operação": st.column_config.TextColumn(
                        label="Operação",
                        width=70,
                    ),
                    "Exec": st.column_config.TextColumn(
                        label="Exec",
                        width=70,
                    ),
                    "HH": st.column_config.TextColumn(
                        label="HH",
                        width=60,
                    ),
                    "Txt Breve Operação": st.column_config.TextColumn(
                        label="Txt Breve Operação",
                        width=400,
                        max_chars=40,
                    ),
                    "Materiais": st.column_config.ListColumn(
                        label="Materiais",
                        width=300,
                    ),
                },
                key="df_resultados",
            )

        with col_acoes:
            st.text("\u00a0")
            # Gerar ícones de olho alinhados com cada linha do dataframe
            header_h = 65  # altura do header do Glide Data Grid
            row_h = 35     # altura de cada row
            icons_html = f'<div style="margin-top: {header_h}px;">'
            for i in range(len(df_exemplo)):
                icons_html += f'''
                <div style="height: {row_h}px; display:flex; align-items:center;
                     justify-content:center; cursor:pointer; opacity:0.5;
                     transition: opacity 0.15s;"
                     onmouseover="this.style.opacity='1'"
                     onmouseout="this.style.opacity='0.5'">
                    <span style="font-size:18px;">👁</span>
                </div>'''
            icons_html += '</div>'
            st.markdown(icons_html, unsafe_allow_html=True)
