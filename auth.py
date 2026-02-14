"""
auth.py — Autenticação e controle de acesso (Supabase + bcrypt)
"""

import os
import ssl
import secrets
import string
import streamlit as st
import bcrypt
import httpx
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega variáveis do .env (se existir — uso local)
load_dotenv()


# ---------------------------------------------------------------------------
# CSS compartilhado para telas de autenticação
# ---------------------------------------------------------------------------

_AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
/* Esconde sidebar e header nas telas de auth */
section[data-testid="stSidebar"] { display: none !important; }
button[data-testid="stSidebarCollapsedControl"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
.login-header { text-align: center; margin-bottom: 24px; }
.login-header h2 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important; font-size: 1.6rem; color: #1e293b; margin-bottom: 4px;
}
.login-header p {
    font-family: 'Inter', sans-serif !important;
    font-weight: 400; font-size: 0.88rem; color: #64748b;
}
html, body, [class*="css"], input, button, label {
    font-family: 'Inter', sans-serif !important;
}
</style>
"""

# JS que sobrescreve o inline style do layout=wide (executado via components.html)
_AUTH_JS = """
<script>
(function() {
    function fix() {
        var doc = window.parent.document;
        var els = doc.querySelectorAll('[data-testid="stMainBlockContainer"], .block-container');
        els.forEach(function(el) {
            el.style.setProperty('max-width', '440px', 'important');
            el.style.setProperty('width', '440px', 'important');
            el.style.setProperty('padding-top', '8vh', 'important');
            el.style.setProperty('margin-left', 'auto', 'important');
            el.style.setProperty('margin-right', 'auto', 'important');
            el.style.setProperty('padding-left', '1rem', 'important');
            el.style.setProperty('padding-right', '1rem', 'important');
        });
    }
    fix();
    setTimeout(fix, 100);
    setTimeout(fix, 500);
})();
</script>
"""


def _aplicar_auth_layout():
    """Aplica CSS + JS para telas de autenticação (container estreito)."""
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    st.components.v1.html(_AUTH_JS, height=0)


# ---------------------------------------------------------------------------
# Conexão Supabase (singleton via st.cache_resource)
# ---------------------------------------------------------------------------

def _get_config(chave: str) -> str:
    """
    Busca configuração primeiro no .env (os.environ),
    depois no st.secrets (Streamlit Cloud).
    """
    valor = os.environ.get(chave)
    if valor:
        return valor
    try:
        return st.secrets[chave]
    except (KeyError, FileNotFoundError):
        st.error(f"⚠️ Configuração '{chave}' não encontrada. Verifique o .env ou os Secrets do Streamlit Cloud.")
        st.stop()


def _ssl_verify() -> bool:
    """Retorna False se SSL_VERIFY=false no .env (redes corporativas)."""
    return _get_config("SSL_VERIFY").lower() not in ("false", "0", "no")


@st.cache_resource
def _get_supabase() -> Client:
    """Retorna cliente Supabase usando .env (local) ou st.secrets (Cloud)."""
    url = _get_config("SUPABASE_URL")
    key = _get_config("SUPABASE_KEY")
    verify = _ssl_verify()

    if not verify:
        # Rede corporativa com proxy SSL — desabilita verificação
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        client = create_client(
            url, key,
            options=None,  # usa defaults
        )
        # Substituir httpx clients internos para desabilitar SSL
        _patch_supabase_ssl(client)
        return client

    return create_client(url, key)


def _patch_supabase_ssl(client: Client):
    """Recria os httpx clients internos do Supabase com verify=False."""
    # O client do postgrest usa httpx por baixo
    if hasattr(client, 'postgrest') and hasattr(client.postgrest, 'session'):
        old_session = client.postgrest.session
        new_session = httpx.Client(
            base_url=str(old_session.base_url),
            headers=dict(old_session.headers),
            verify=False,
        )
        client.postgrest.session = new_session


def supabase() -> Client:
    return _get_supabase()


# ---------------------------------------------------------------------------
# Utilitários de senha
# ---------------------------------------------------------------------------

def hash_senha(senha: str) -> str:
    """Gera hash bcrypt a partir de senha em texto."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Compara senha em texto com hash bcrypt."""
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def gerar_senha_provisoria(tamanho: int = 8) -> tuple[str, str]:
    """
    Gera senha provisória aleatória.
    Retorna (senha_texto, senha_hash_bcrypt).
    """
    caracteres = string.ascii_letters + string.digits
    senha = "".join(secrets.choice(caracteres) for _ in range(tamanho))
    return senha, hash_senha(senha)


# ---------------------------------------------------------------------------
# Controle de sessão (com persistência via token em query_params)
# ---------------------------------------------------------------------------

def verificar_sessao() -> bool:
    """Retorna True se o usuário está logado (session_state ou token persistido)."""
    if st.session_state.get("logado", False):
        return True

    # Tenta restaurar sessão a partir do token na URL
    token = st.query_params.get("token")
    if token:
        resp = (
            supabase()
            .table("usuarios")
            .select("*")
            .eq("session_token", token)
            .eq("status", "ativo")
            .execute()
        )
        if resp.data:
            _iniciar_sessao(resp.data[0], persistir=False)
            return True
        else:
            # Token inválido — limpa da URL
            st.query_params.clear()

    return False


def get_usuario() -> dict | None:
    """Retorna dados do usuário logado ou None."""
    if not verificar_sessao():
        return None
    return {
        "chave": st.session_state.get("chave"),
        "perfil": st.session_state.get("perfil"),
        "lotacao": st.session_state.get("lotacao"),
        "trocar_senha": st.session_state.get("trocar_senha", False),
    }


def _iniciar_sessao(usuario: dict, persistir: bool = True):
    """Armazena dados do usuário no session_state e persiste token na URL."""
    st.session_state["logado"] = True
    st.session_state["chave"] = usuario["chave"]
    st.session_state["perfil"] = usuario["perfil"]
    st.session_state["lotacao"] = usuario["lotacao"]
    st.session_state["trocar_senha"] = usuario["trocar_senha"]

    if persistir:
        # Gera token único e salva no Supabase
        try:
            token = secrets.token_urlsafe(32)
            supabase().table("usuarios").update(
                {"session_token": token}
            ).eq("chave", usuario["chave"]).execute()
            st.query_params["token"] = token
        except Exception:
            pass  # coluna pode não existir ainda
    elif usuario.get("session_token"):
        # Mantém token existente na URL
        st.query_params["token"] = usuario["session_token"]


def logout():
    """Limpa a sessão do usuário e remove token."""
    chave = st.session_state.get("chave")
    if chave:
        try:
            supabase().table("usuarios").update(
                {"session_token": None}
            ).eq("chave", chave).execute()
        except Exception:
            pass
    for key in ["logado", "chave", "perfil", "lotacao", "trocar_senha"]:
        st.session_state.pop(key, None)
    st.query_params.clear()


# ---------------------------------------------------------------------------
# Tela de Login
# ---------------------------------------------------------------------------

def tela_login():
    """Renderiza formulário de login centralizado com visual de card."""
    _aplicar_auth_layout()

    st.markdown('<div class="login-header"><h2>🔐 SmartOM</h2><p>Faça login para acessar o sistema</p></div>', unsafe_allow_html=True)

    with st.form("form_login"):
        chave = st.text_input("Chave", placeholder="Ex.: ABCD")
        senha = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar", use_container_width=True)

    if submit:
        if not chave.strip() or not senha.strip():
            st.error("Preencha todos os campos.")
            return

        # Buscar usuário ativo
        resp = (
            supabase()
            .table("usuarios")
            .select("*")
            .eq("chave", chave.strip().upper())
            .execute()
        )

        if not resp.data:
            st.error("Usuário não encontrado ou cadastro ainda não aprovado.")
            return

        usuario = resp.data[0]

        if usuario["status"] == "pendente":
            st.warning("Seu cadastro ainda está pendente de aprovação. Aguarde o administrador.")
            return

        if usuario["status"] in ("revogado", "rejeitado"):
            st.error("Seu acesso foi revogado. Entre em contato com o administrador.")
            return

        if not usuario.get("senha_hash"):
            st.error("Sua conta ainda não possui senha. Aguarde a aprovação.")
            return

        if not verificar_senha(senha, usuario["senha_hash"]):
            st.error("Senha incorreta.")
            return

        # Login OK
        _iniciar_sessao(usuario)
        st.rerun()

    # Link para cadastro
    st.markdown("---")
    st.caption("Não tem acesso?")
    if st.button("Solicitar Cadastro"):
        st.session_state["tela"] = "cadastro"
        st.rerun()


# ---------------------------------------------------------------------------
# Tela de Cadastro
# ---------------------------------------------------------------------------

def tela_cadastro():
    """Renderiza formulário de solicitação de cadastro centralizado."""
    _aplicar_auth_layout()

    st.markdown('<div class="login-header"><h2>📝 Solicitar Cadastro</h2><p>Preencha seus dados para solicitar acesso</p></div>', unsafe_allow_html=True)

    with st.form("form_cadastro"):
        chave = st.text_input("Chave", placeholder="Ex.: ABCD")
        lotacao = st.text_input("Lotação", placeholder="Ex.: EDISE, UO-RJ, ...")
        submit = st.form_submit_button("Enviar Solicitação", use_container_width=True)

    if submit:
        if not chave.strip() or not lotacao.strip():
            st.error("Preencha todos os campos.")
            return

        chave_upper = chave.strip().upper()

        # Verificar se já existe
        existente = (
            supabase()
            .table("usuarios")
            .select("id, status")
            .eq("chave", chave_upper)
            .execute()
        )

        if existente.data:
            status_atual = existente.data[0]["status"]
            if status_atual == "pendente":
                st.warning("Já existe uma solicitação pendente para esta chave.")
            elif status_atual == "ativo":
                st.info("Esta chave já possui acesso ativo. Faça login.")
            elif status_atual in ("revogado", "rejeitado"):
                st.warning("Esta chave teve acesso revogado. Contate o administrador.")
            return

        # Inserir solicitação
        supabase().table("usuarios").insert({
            "chave": chave_upper,
            "lotacao": lotacao.strip(),
        }).execute()

        st.success("✅ Solicitação enviada! Aguarde a aprovação do administrador.")

    st.markdown("---")
    if st.button("← Voltar ao Login"):
        st.session_state.pop("tela", None)
        st.rerun()


# ---------------------------------------------------------------------------
# Tela de Troca de Senha
# ---------------------------------------------------------------------------

def tela_trocar_senha():
    """Renderiza tela de troca de senha obrigatória centralizada."""
    _aplicar_auth_layout()

    st.markdown('<div class="login-header"><h2>🔑 Troca de Senha</h2><p>Defina uma nova senha para continuar (mínimo 6 caracteres)</p></div>', unsafe_allow_html=True)

    with st.form("form_trocar_senha"):
        nova_senha = st.text_input("Nova Senha", type="password")
        confirmar = st.text_input("Confirmar Nova Senha", type="password")
        submit = st.form_submit_button("Salvar Nova Senha")

    if submit:
        if not nova_senha or not confirmar:
            st.error("Preencha todos os campos.")
            return

        if len(nova_senha) < 6:
            st.error("A senha deve ter no mínimo 6 caracteres.")
            return

        if nova_senha != confirmar:
            st.error("As senhas não conferem.")
            return

        # Atualizar senha no Supabase
        novo_hash = hash_senha(nova_senha)
        supabase().table("usuarios").update({
            "senha_hash": novo_hash,
            "trocar_senha": False,
        }).eq("chave", st.session_state["chave"]).execute()

        st.session_state["trocar_senha"] = False
        st.success("✅ Senha alterada com sucesso!")
        st.rerun()
