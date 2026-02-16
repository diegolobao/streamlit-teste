import streamlit as st
import os
import sys
import time
import requests
import pandas as pd
from dotenv import load_dotenv
from auth import verificar_sessao, get_usuario, tela_login, tela_cadastro, tela_trocar_senha, logout
from admin import tela_admin

# Importa o componente SmartTable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "components_test"))
from smart_table import smart_table

# Importa módulos de busca e extração
from databricks_client import buscar_notas_batch, salvar_supabase as salvar_notas_raw
from extrair_delineamento import (
    extrair_delineamento, salvar_delineamento_supabase,
    salvar_revisao_supabase, buscar_operacoes_ia,
    MAPA_CENTRO_TRABALHO,
)

# Carrega .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() not in ("false", "0", "no")

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

    # ───────────────────────────────────────────────────────────────────────
    # Buscar dados do Supabase (notas_delineadas)
    # ───────────────────────────────────────────────────────────────────────

    @st.cache_data(ttl=60)
    def carregar_delineamentos() -> list[dict]:
        """Busca notas_delineadas e mescla com notas_revisadas (se existir)."""
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }

        # 1. Buscar todas as notas delineadas (saída da IA)
        url_del = f"{SUPABASE_URL}/rest/v1/notas_delineadas"
        params_del = {"select": "numero_nota,area_responsavel,operacoes,revisao"}
        resp_del = requests.get(url_del, headers=headers, params=params_del, verify=SSL_VERIFY)
        resp_del.raise_for_status()
        delineadas = resp_del.json()

        # 2. Buscar todas as revisões
        url_rev = f"{SUPABASE_URL}/rest/v1/notas_revisadas"
        params_rev = {"select": "numero_nota,operacoes,score"}
        resp_rev = requests.get(url_rev, headers=headers, params=params_rev, verify=SSL_VERIFY)
        revisadas_map = {}
        if resp_rev.ok:
            for r in resp_rev.json():
                revisadas_map[r["numero_nota"]] = r

        # 3. Mesclar: se nota foi revisada, usar operacoes da notas_revisadas
        resultado = []
        for reg in delineadas:
            nota = reg["numero_nota"]
            rev = revisadas_map.get(nota)
            resultado.append({
                "numero_nota": nota,
                "area_responsavel": reg.get("area_responsavel", ""),
                "operacoes": rev["operacoes"] if rev else reg.get("operacoes", []),
                "revisao": reg.get("revisao", False),
                "score": rev.get("score") if rev else None,
            })
        return resultado

    try:
        registros_supabase = carregar_delineamentos()
    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
        registros_supabase = []

    # ───────────────────────────────────────────────────────────────────────
    # Transforma dados em linhas planas (uma por operação)
    # ───────────────────────────────────────────────────────────────────────

    dados = []
    dados_detalhados = {}

    for reg in registros_supabase:
        nota = reg["numero_nota"]
        area = reg.get("area_responsavel", "")
        operacoes = reg.get("operacoes", [])
        dados_detalhados[nota] = reg

        for op in operacoes:
            def _fmt_qtd(v):
                try:
                    f = float(str(v))
                    return str(int(f)) if f == int(f) else str(v)
                except (ValueError, TypeError):
                    return str(v)

            materiais_chips = [
                f"{m['nm']} ({_fmt_qtd(m.get('quantidade', 1))})"
                for m in op.get("materiais", []) if m.get("nm")
            ]
            dados.append({
                "nota": nota,
                "area": area,
                "operacao": op.get("operação", ""),
                "cen_trab": op.get("centro_trabalho_executor", ""),
                "exec": str(op.get("numero_executantes", "")),
                "hh": str(op.get("duracao_hh", "")),
                "txt_breve": op.get("descricao_operacao", ""),
                "materiais": materiais_chips,
                "_op_id": op.get("operação", ""),
            })

    # ───────────────────────────────────────────────────────────────────────
    # Definição de colunas e campos editáveis
    # ───────────────────────────────────────────────────────────────────────

    colunas = [
        {"key": "nota",      "label": "Nota",               "type": "text",  "align": "center"},
        {"key": "area",      "label": "Área",               "type": "text",  "align": "center"},
        {"key": "operacao",  "label": "Operação",           "type": "text",  "align": "center"},
        {"key": "cen_trab",  "label": "Cen Trab Executor",  "type": "text"},
        {"key": "exec",      "label": "Exec",               "type": "text",  "align": "center"},
        {"key": "hh",        "label": "HH",                 "type": "text",  "align": "center"},
        {"key": "txt_breve", "label": "Txt Breve Operação", "type": "text"},
        {"key": "materiais", "label": "Materiais",          "type": "chips"},
    ]

    campos_editaveis = ["cen_trab", "exec", "hh", "txt_breve"]

    FIELD_MAP = {
        "cen_trab": "centro_trabalho_executor",
        "exec": "numero_executantes",
        "hh": "duracao_hh",
        "txt_breve": "descricao_operacao",
    }

    # ───────────────────────────────────────────────────────────────────────
    # Funções CRUD Supabase
    # ───────────────────────────────────────────────────────────────────────

    def _obter_operacoes_atuais(numero_nota: str) -> list | None:
        """Busca operações atuais: de notas_revisadas (se existir) ou notas_delineadas."""
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        # Tenta buscar de notas_revisadas primeiro
        url_rev = f"{SUPABASE_URL}/rest/v1/notas_revisadas"
        params_rev = {"select": "operacoes", "numero_nota": f"eq.{numero_nota}"}
        resp_rev = requests.get(url_rev, headers=headers, params=params_rev, verify=SSL_VERIFY)
        if resp_rev.ok and resp_rev.json():
            return resp_rev.json()[0]["operacoes"]
        # Senão, busca de notas_delineadas (primeira edição)
        url_del = f"{SUPABASE_URL}/rest/v1/notas_delineadas"
        params_del = {"select": "operacoes", "numero_nota": f"eq.{numero_nota}"}
        resp_del = requests.get(url_del, headers=headers, params=params_del, verify=SSL_VERIFY)
        if resp_del.ok and resp_del.json():
            return resp_del.json()[0]["operacoes"]
        return None

    def atualizar_operacao_supabase(numero_nota: str, op_id: str, campo_tabela: str, valor: str):
        campo_jsonb = FIELD_MAP.get(campo_tabela)
        if not campo_jsonb:
            st.warning(f"Campo '{campo_tabela}' não mapeado para JSONB.")
            return False

        operacoes = _obter_operacoes_atuais(numero_nota)
        if operacoes is None:
            st.error(f"Erro ao buscar nota {numero_nota}")
            return False

        encontrou = False
        for op in operacoes:
            if str(op.get("operação", "")) == str(op_id):
                op[campo_jsonb] = valor
                encontrou = True
                break
        if not encontrou:
            st.error(f"Operação {op_id} não encontrada na nota {numero_nota}")
            return False

        # Salva em notas_revisadas (não mais em notas_delineadas)
        usr_chave = usuario.get("chave", "") if usuario else ""
        usr_lotacao = usuario.get("lotacao", "") if usuario else ""
        try:
            salvar_revisao_supabase(numero_nota, operacoes, chave_revisor=usr_chave, lotacao_revisor=usr_lotacao)
            st.toast(f"✅ Salvo: {campo_tabela} → {valor}", icon="✅")
            return True
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
            return False

    def excluir_operacao_supabase(numero_nota: str, op_id: str, is_last: bool = False):
        if is_last:
            # Se é a última operação, remover notas_revisadas e notas_delineadas
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            }
            # Remover revisão (se existir)
            url_rev = f"{SUPABASE_URL}/rest/v1/notas_revisadas?numero_nota=eq.{numero_nota}"
            requests.delete(url_rev, headers=headers, verify=SSL_VERIFY)
            # Remover delineamento original
            url_del = f"{SUPABASE_URL}/rest/v1/notas_delineadas?numero_nota=eq.{numero_nota}"
            resp = requests.delete(url_del, headers=headers, verify=SSL_VERIFY)
            if resp.ok:
                st.toast(f"🗑️ Nota {numero_nota} removida (última operação)", icon="🗑️")
                return True
            else:
                st.error(f"Erro ao excluir nota: {resp.status_code} — {resp.text}")
                return False

        operacoes = _obter_operacoes_atuais(numero_nota)
        if operacoes is None:
            st.error(f"Erro ao buscar nota {numero_nota}")
            return False

        nova_lista = [op for op in operacoes if str(op.get("operação", "")) != str(op_id)]
        if len(nova_lista) == len(operacoes):
            st.warning(f"Operação {op_id} não encontrada na nota {numero_nota}")
            return False

        usr_chave = usuario.get("chave", "") if usuario else ""
        usr_lotacao = usuario.get("lotacao", "") if usuario else ""
        try:
            salvar_revisao_supabase(numero_nota, nova_lista, chave_revisor=usr_chave, lotacao_revisor=usr_lotacao)
            st.toast(f"🗑️ Operação {op_id} removida da nota {numero_nota}", icon="🗑️")
            return True
        except Exception as e:
            st.error(f"Erro ao excluir operação: {e}")
            return False

    def excluir_material_supabase(numero_nota: str, op_id: str, nm: str):
        operacoes = _obter_operacoes_atuais(numero_nota)
        if operacoes is None:
            st.error(f"Erro ao buscar nota {numero_nota}")
            return False

        encontrou_op = False
        for op in operacoes:
            if str(op.get("operação", "")) == str(op_id):
                encontrou_op = True
                materiais = op.get("materiais", [])
                nova_lista = [m for m in materiais if str(m.get("nm", "")) != str(nm)]
                if len(nova_lista) == len(materiais):
                    st.warning(f"Material {nm} não encontrado na operação {op_id}")
                    return False
                op["materiais"] = nova_lista
                break
        if not encontrou_op:
            st.error(f"Operação {op_id} não encontrada na nota {numero_nota}")
            return False

        usr_chave = usuario.get("chave", "") if usuario else ""
        usr_lotacao = usuario.get("lotacao", "") if usuario else ""
        try:
            salvar_revisao_supabase(numero_nota, operacoes, chave_revisor=usr_chave, lotacao_revisor=usr_lotacao)
            st.toast(f"🗑️ Material {nm} removido da operação {op_id}", icon="🗑️")
            return True
        except Exception as e:
            st.error(f"Erro ao excluir material: {e}")
            return False

    # ───────────────────────────────────────────────────────────────────────
    # Abas: Notas Qualificadas | Relatório | Dashboard
    # ───────────────────────────────────────────────────────────────────────

    tab_notas, tab_relatorio, tab_dashboard = st.tabs(
        ["📋 Notas Qualificadas", "📊 Relatório", "📈 Dashboard"]
    )

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 1 — Notas Qualificadas
    # ═══════════════════════════════════════════════════════════════════════
    with tab_notas:
        avisos_placeholder = st.container()

        col_notas, col_resultado = st.columns([1, 7])

        # Coluna esquerda — entrada de notas + botão Buscar
        with col_notas:
            st.text("Notas (uma por linha)")
            notas_texto = st.text_area(
                "Notas (uma por linha)",
                height=280,
                placeholder="10001234\n10005678\n10009012\n...",
                key="input_notas",
                label_visibility="collapsed",
            )
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

            # Botão Buscar + processamento
            btn_buscar = st.button("Buscar", key="btn_buscar", type="primary", use_container_width=True)
            status_placeholder = st.empty()

            if btn_buscar:
                # Parseia notas do text_area
                linhas = [l.strip() for l in notas_texto.strip().splitlines() if l.strip()]
                if not linhas:
                    status_placeholder.warning("⚠️ Insira ao menos um número de nota.")
                else:
                    # ── Etapa 1: Buscar no SAP via Databricks ──
                    status_placeholder.info(f"🔍 Buscando {len(linhas)} nota(s) no SAP...")
                    try:
                        resultados_sap = buscar_notas_batch(linhas)
                    except Exception as e:
                        status_placeholder.error(f"❌ Erro ao buscar no SAP: {e}")
                        resultados_sap = []

                    if resultados_sap:
                        # Notas não encontradas
                        notas_encontradas = {r["numero_nota"] for r in resultados_sap}
                        notas_input = {n.lstrip("0")[-8:] for n in linhas}
                        nao_encontradas = notas_input - notas_encontradas
                        if nao_encontradas:
                            status_placeholder.warning(
                                f"⚠️ {len(nao_encontradas)} nota(s) não encontrada(s): "
                                f"{', '.join(sorted(nao_encontradas))}. Continuando com as demais..."
                            )

                        # ── Filtrar notas que já possuem Ordem de Manutenção ──
                        com_ordem = [
                            r for r in resultados_sap
                            if r.get("ordem_servico") and str(r["ordem_servico"]).strip()
                        ]
                        if com_ordem:
                            detalhes = ", ".join(
                                f"{r['numero_nota']} (OM: {str(r['ordem_servico']).lstrip('0')})"
                                for r in com_ordem
                            )
                            avisos_placeholder.warning(
                                f"🔒 Nota(s) já possuem Ordem de Manutenção: {detalhes}. Serão ignoradas."
                            )
                            notas_com_ordem = {r["numero_nota"] for r in com_ordem}
                            resultados_sap = [
                                r for r in resultados_sap
                                if r["numero_nota"] not in notas_com_ordem
                            ]

                        if not resultados_sap:
                            status_placeholder.info("ℹ️ Todas as notas já possuem Ordem de Manutenção.")
                        else:
                            # ── Verificar notas já delineadas ──
                            notas_ja_delineadas = set()
                            try:
                                notas_restantes = {r["numero_nota"] for r in resultados_sap}
                                url_check = f"{SUPABASE_URL}/rest/v1/notas_delineadas"
                                headers_check = {
                                    "apikey": SUPABASE_KEY,
                                    "Authorization": f"Bearer {SUPABASE_KEY}",
                                }
                                params_check = {
                                    "select": "numero_nota",
                                    "numero_nota": f"in.({','.join(notas_restantes)})",
                                }
                                resp_check = requests.get(
                                    url_check, headers=headers_check,
                                    params=params_check, verify=SSL_VERIFY,
                                )
                                resp_check.raise_for_status()
                                notas_ja_delineadas = {r["numero_nota"] for r in resp_check.json()}
                            except Exception:
                                pass  # Em caso de erro, processa todas

                            if notas_ja_delineadas:
                                avisos_placeholder.warning(
                                    f"📋 Nota(s) já delineada(s): "
                                    f"{', '.join(sorted(notas_ja_delineadas))}. Serão ignoradas."
                                )

                            # Filtra apenas notas não delineadas
                            resultados_sap = [
                                r for r in resultados_sap
                                if r["numero_nota"] not in notas_ja_delineadas
                            ]

                            if not resultados_sap:
                                status_placeholder.info("ℹ️ Todas as notas já foram delineadas.")
                            else:
                                # Dados do usuário logado
                                usr_chave = usuario.get("chave", "") if usuario else ""
                                usr_lotacao = usuario.get("lotacao", "") if usuario else ""

                                # Salvar em notas_raw (Supabase)
                                status_placeholder.info(
                                    f"💾 Salvando {len(resultados_sap)} nota(s) no banco de dados..."
                                )
                                try:
                                    salvar_notas_raw(resultados_sap, chave=usr_chave, lotacao=usr_lotacao)
                                except Exception as e:
                                    status_placeholder.error(f"❌ Erro ao salvar notas_raw: {e}")
                                    st.stop()

                                # ── Etapa 2: Extrair delineamento com IA ──
                                total = len(resultados_sap)
                                erros_ia = []
                                for idx, nota_data in enumerate(resultados_sap, 1):
                                    nota_num = nota_data["numero_nota"]
                                    texto = nota_data.get("texto_nota", "")
                                    if not texto.strip():
                                        erros_ia.append(f"{nota_num} (sem texto)")
                                        continue

                                    status_placeholder.info(
                                        f"🤖 Extraindo delineamento com IA... ({idx}/{total}) — Nota {nota_num}"
                                    )
                                    try:
                                        resultado_ia = extrair_delineamento(texto)

                                        # Pós-processamento
                                        operacoes_final = []
                                        for i, op in enumerate(resultado_ia.operacoes):
                                            abrev = op.centro_trabalho_executor.upper()
                                            operacoes_final.append({
                                                "operação": f"{(i + 1) * 10:04d}",
                                                "centro_trabalho_executor": MAPA_CENTRO_TRABALHO.get(abrev, abrev),
                                                "descricao_operacao": op.descricao_operacao[:40],
                                                "numero_executantes": str(op.numero_executantes),
                                                "duracao_hh": str(op.duracao_hh).replace(".", ","),
                                                "materiais": [{"nm": m.nm, "quantidade": str(m.quantidade)} for m in op.materiais],
                                            })

                                        delineamento_final = {
                                            "numero_nota": nota_data.get("numero_nota", nota_num),
                                            "centro_trabalho_responsavel": nota_data.get("centro_trabalho", ""),
                                            "descricao_geral": nota_data.get("descricao_nota", ""),
                                            "area_responsavel": nota_data.get("notificador", "").split("-")[0],
                                            "operacoes": operacoes_final,
                                        }

                                        salvar_delineamento_supabase(delineamento_final, chave=usr_chave, lotacao=usr_lotacao)
                                    except Exception as e:
                                        erros_ia.append(f"{nota_num} ({e})")

                                # Resultado final
                                if erros_ia:
                                    status_placeholder.warning(
                                        f"✅ Concluído com avisos. Erros em: {', '.join(erros_ia)}"
                                    )
                                else:
                                    status_placeholder.success(
                                        f"✅ {total} nota(s) processada(s) com sucesso!"
                                    )

                                # Atualiza SmartTable
                                carregar_delineamentos.clear()
                                time.sleep(0.5)
                                st.rerun()
                    elif not resultados_sap:
                        status_placeholder.error("❌ Nenhuma nota encontrada no SAP.")

        # Coluna direita — SmartTable
        with col_resultado:
            st.text("Delineamento Prévio Extraído pela IA")
            result = smart_table(
                rows=dados,
                columns=colunas,
                editable_fields=campos_editaveis,
                height=420,
                key="tabela_principal",
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY,
                supabase_table="notas_delineadas",
                primary_key="nota",
                group_key="nota",
                group_merge_keys=["nota", "area"],
                jsonb_column="operacoes",
                jsonb_op_key="operação",
                field_map=FIELD_MAP,
            )

        # ───────────────────────────────────────────────────────────────────────
        # Trata ações do componente
        # ───────────────────────────────────────────────────────────────────────

        if result and isinstance(result, dict):
            action = result.get("action")

            if action == "view":
                st.session_state["selected_nota"] = result.get("id")

            elif action == "edit":
                nota_id = result.get("id")
                op_id = result.get("op_id")
                campo = result.get("field")
                valor = result.get("value", "")
                edit_fingerprint = f"{nota_id}:{op_id}:{campo}:{valor}"
                if nota_id and op_id and campo and st.session_state.get("_last_edit") != edit_fingerprint:
                    st.session_state["_last_edit"] = edit_fingerprint
                    ok = atualizar_operacao_supabase(nota_id, op_id, campo, valor)
                    if ok:
                        carregar_delineamentos.clear()
                        st.rerun()

            elif action == "delete_op":
                nota_id = result.get("id")
                op_id = result.get("op_id")
                is_last = result.get("is_last", False)
                fingerprint = f"delete_op:{nota_id}:{op_id}"
                if nota_id and op_id and st.session_state.get("_last_edit") != fingerprint:
                    st.session_state["_last_edit"] = fingerprint
                    ok = excluir_operacao_supabase(nota_id, op_id, is_last)
                    if ok:
                        carregar_delineamentos.clear()
                        st.rerun()

            elif action == "delete_mat":
                nota_id = result.get("id")
                op_id = result.get("op_id")
                nm = result.get("nm", "")
                fingerprint = f"delete_mat:{nota_id}:{op_id}:{nm}"
                if nota_id and op_id and nm and st.session_state.get("_last_edit") != fingerprint:
                    st.session_state["_last_edit"] = fingerprint
                    ok = excluir_material_supabase(nota_id, op_id, nm)
                    if ok:
                        carregar_delineamentos.clear()
                        st.rerun()

            elif action == "criar_ordens":
                st.markdown("---")
                st.subheader("📋 Pré-visualização — Criar Ordens")

                dt_inicio = result.get("data_inicio", "")
                dt_fim = result.get("data_fim", "")
                selected_rows = result.get("selected_rows", [])

                ci, cf = st.columns(2)
                ci.info(f"📅 Data de Início: **{dt_inicio}**")
                cf.info(f"📅 Data Fim: **{dt_fim}**")

                if selected_rows:
                    df_rows = []
                    for r in selected_rows:
                        mats = r.get("materiais", [])
                        mats_str = ", ".join(mats) if isinstance(mats, list) else str(mats)
                        df_rows.append({
                            "Nota": r.get("nota", ""),
                            "Área": r.get("area", ""),
                            "Operação": r.get("operacao", ""),
                            "Cen Trab Executor": r.get("cen_trab", ""),
                            "Exec": r.get("exec", ""),
                            "HH": r.get("hh", ""),
                            "Txt Breve Operação": r.get("txt_breve", ""),
                            "Materiais": mats_str,
                            "Data Início": dt_inicio,
                            "Data Fim": dt_fim,
                        })
                    df_ordens = pd.DataFrame(df_rows)
                    st.dataframe(df_ordens, use_container_width=True, hide_index=True)
                    st.caption(f"{len(df_rows)} operação(ões) selecionada(s) para criação de ordens.")
                else:
                    st.warning("Nenhuma linha selecionada.")

        # ───────────────────────────────────────────────────────────────────────
        # View de detalhes (olho) — exibe delineamento completo
        # ───────────────────────────────────────────────────────────────────────

        if "selected_nota" in st.session_state:
            nota_id = st.session_state["selected_nota"]
            detalhe = dados_detalhados.get(nota_id)

            if detalhe:
                st.markdown("---")

                # ── Buscar dados brutos da nota (notas_raw) ──
                nota_raw = None
                try:
                    url_raw = f"{SUPABASE_URL}/rest/v1/notas_raw"
                    headers_raw = {
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                    }
                    params_raw = {
                        "select": "numero_nota,centro_trabalho,local_instalacao,descricao_nota,texto_nota,notificador",
                        "numero_nota": f"eq.{nota_id}",
                        "limit": "1",
                    }
                    resp_raw = requests.get(url_raw, headers=headers_raw, params=params_raw, verify=SSL_VERIFY)
                    resp_raw.raise_for_status()
                    raw_list = resp_raw.json()
                    if raw_list:
                        nota_raw = raw_list[0]
                except Exception:
                    pass

                # ── Dados da nota original (notas_raw) ──
                if nota_raw:
                    nota_numero = nota_raw.get("numero_nota", detalhe["numero_nota"])

                    col_titulo, col_close = st.columns([9, 1])
                    with col_titulo:
                        st.markdown(
                            f"<div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;"
                            f"padding:16px;margin-bottom:16px'>"
                            f"<span style='font-size:16px;font-weight:700;color:#1e3a5f;"
                            f"text-transform:uppercase;letter-spacing:0.5px'>📄 Nota Original (SAP) — {nota_numero}</span></div>",
                            unsafe_allow_html=True,
                        )
                    with col_close:
                        if st.button("✕ Fechar", key="btn_close_detail", use_container_width=True):
                            del st.session_state["selected_nota"]
                            st.rerun()

                    centro_trabalho = nota_raw.get("centro_trabalho", "—")
                    local_instalacao = nota_raw.get("local_instalacao", "—")
                    notificador = nota_raw.get("notificador", "—")

                    def _card_metric(label, value, icon):
                        return (
                            f"<div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;"
                            f"padding:12px 16px;height:100%'>"
                            f"<div style='font-size:11px;font-weight:600;color:#94a3b8;"
                            f"text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px'>"
                            f"{icon} {label}</div>"
                            f"<div style='font-size:15px;font-weight:600;color:#1e293b'>{value}</div>"
                            f"</div>"
                        )

                    r1, r2, r3 = st.columns(3)
                    with r1:
                        st.markdown(_card_metric("Centro de Trabalho", centro_trabalho, "🔧"), unsafe_allow_html=True)
                    with r2:
                        st.markdown(_card_metric("Local Instalação", local_instalacao, "📍"), unsafe_allow_html=True)
                    with r3:
                        st.markdown(_card_metric("Notificador", notificador, "👤"), unsafe_allow_html=True)

                    st.markdown(
                        f"<div style='margin-top:4px;margin-bottom:4px'>"
                        f"<span style='font-size:16px;font-weight:600;color:#64748b;"
                        f"letter-spacing:0.5px'>Descrição</span>"
                        f"<div style='background:#fff;border:1px solid #e2e8f0;border-radius:6px;"
                        f"padding:10px 14px;font-size:16px;margin-top:4px'>"
                        f"{nota_raw.get('descricao_nota', '—')}</div></div>",
                        unsafe_allow_html=True,
                    )

                    texto_nota = nota_raw.get("texto_nota", "—")
                    st.markdown(
                        f"<div style='margin-top:4px;margin-bottom:12px'>"
                        f"<span style='font-size:16px;font-weight:600;color:#64748b;"
                        f"letter-spacing:0.5px'>Texto da Nota</span>"
                        f"<div style='background:#fff;border:1px solid #e2e8f0;border-radius:6px;"
                        f"padding:10px 14px;font-size:16px;margin-top:4px;"
                        f"max-height:400px;overflow-y:auto;white-space:pre-wrap'>"
                        f"{texto_nota}</div></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.info("Dados da nota original não encontrados em notas_raw.")
            else:
                st.info(f"Nota {nota_id} não encontrada nos dados carregados.")

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 2 — Relatório
    # ═══════════════════════════════════════════════════════════════════════
    with tab_relatorio:
        st.markdown(
            "<div style='text-align:center;padding:60px 20px'>"
            "<span style='font-size:48px'>📊</span>"
            "<h3 style='color:#64748b;margin-top:16px'>Relatório</h3>"
            "<p style='color:#94a3b8;font-size:14px'>Em breve — relatórios de notas processadas, "
            "ordens criadas e métricas de qualidade.</p></div>",
            unsafe_allow_html=True,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 3 — Dashboard
    # ═══════════════════════════════════════════════════════════════════════
    with tab_dashboard:
        st.markdown(
            "<div style='text-align:center;padding:60px 20px'>"
            "<span style='font-size:48px'>📈</span>"
            "<h3 style='color:#64748b;margin-top:16px'>Dashboard</h3>"
            "<p style='color:#94a3b8;font-size:14px'>Em breve — indicadores visuais de desempenho, "
            "volume de notas e acompanhamento em tempo real.</p></div>",
            unsafe_allow_html=True,
        )
