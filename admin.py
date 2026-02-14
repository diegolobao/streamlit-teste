"""
admin.py — Painel administrativo de gestão de usuários
"""

import streamlit as st
from auth import supabase, gerar_senha_provisoria


def tela_admin():
    """Renderiza o painel administrativo (somente para admins)."""
    # Header já vem do frontend.py (page-header)

    tab_pendentes, tab_ativos, tab_revogados = st.tabs([
        "📋 Pendentes",
        "✅ Ativos",
        "🚫 Revogados",
    ])

    with tab_pendentes:
        _secao_pendentes()

    with tab_ativos:
        _secao_ativos()

    with tab_revogados:
        _secao_revogados()


# ---------------------------------------------------------------------------
# Seção: Solicitações Pendentes
# ---------------------------------------------------------------------------

def _secao_pendentes():
    """Lista e gerencia solicitações de cadastro pendentes."""
    resp = (
        supabase()
        .table("usuarios")
        .select("*")
        .eq("status", "pendente")
        .order("criado_em", desc=False)
        .execute()
    )

    if not resp.data:
        st.info("Nenhuma solicitação pendente.")
        return

    st.markdown(f"**{len(resp.data)} solicitação(ões) pendente(s):**")

    for user in resp.data:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 2, 2])
            col1.markdown(f"**Chave:** {user['chave']}")
            col2.markdown(f"**Lotação:** {user['lotacao']}")
            col3.markdown(f"**Solicitado em:** {_formatar_data(user['criado_em'])}")

            col_a, col_r, col_info = st.columns([1, 1, 3])

            if col_a.button("✅ Aprovar", key=f"aprovar_{user['id']}"):
                _aprovar_usuario(user)

            if col_r.button("❌ Rejeitar", key=f"rejeitar_{user['id']}"):
                _rejeitar_usuario(user)


def _aprovar_usuario(user: dict):
    """Aprova solicitação: gera senha provisória e ativa o usuário."""
    senha_texto, senha_hash = gerar_senha_provisoria()

    supabase().table("usuarios").update({
        "status": "ativo",
        "senha_hash": senha_hash,
        "trocar_senha": True,
        "aprovado_em": "now()",
        "aprovado_por": st.session_state.get("chave", "admin"),
    }).eq("id", user["id"]).execute()

    st.success(f"✅ Usuário **{user['chave']}** aprovado!")
    st.warning(
        f"🔑 **Senha provisória gerada — copie e repasse ao usuário:**\n\n"
        f"```\n{senha_texto}\n```\n\n"
        f"O usuário será obrigado a trocar no primeiro login."
    )
    st.info("ℹ️ Atualize a página para ver a lista atualizada.")


def _rejeitar_usuario(user: dict):
    """Rejeita solicitação de cadastro."""
    supabase().table("usuarios").update({
        "status": "rejeitado",
    }).eq("id", user["id"]).execute()

    st.info(f"Solicitação de **{user['chave']}** rejeitada.")
    st.rerun()


# ---------------------------------------------------------------------------
# Seção: Usuários Ativos
# ---------------------------------------------------------------------------

def _secao_ativos():
    """Lista e gerencia usuários ativos."""
    resp = (
        supabase()
        .table("usuarios")
        .select("*")
        .eq("status", "ativo")
        .order("chave", desc=False)
        .execute()
    )

    if not resp.data:
        st.info("Nenhum usuário ativo.")
        return

    st.markdown(f"**{len(resp.data)} usuário(s) ativo(s):**")

    for user in resp.data:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])
            col1.markdown(f"**Chave:** {user['chave']}")
            col2.markdown(f"**Lotação:** {user['lotacao']}")
            col3.markdown(f"**Perfil:** {user['perfil']}")
            col4.markdown(f"**Desde:** {_formatar_data(user.get('aprovado_em'))}")

            # Não permitir ações sobre si mesmo
            if user["chave"] == st.session_state.get("chave"):
                st.caption("(você)")
                continue

            col_a, col_b, col_c = st.columns(3)

            if col_a.button("🚫 Revogar", key=f"revogar_{user['id']}"):
                _revogar_usuario(user)

            if col_b.button("🔄 Resetar Senha", key=f"reset_{user['id']}"):
                _resetar_senha(user)

            # Alternar perfil
            if user["perfil"] == "operador":
                if col_c.button("⬆️ Promover Admin", key=f"promover_{user['id']}"):
                    _alterar_perfil(user, "admin")
            else:
                if col_c.button("⬇️ Rebaixar Operador", key=f"rebaixar_{user['id']}"):
                    _alterar_perfil(user, "operador")


def _revogar_usuario(user: dict):
    """Revoga acesso de um usuário ativo."""
    supabase().table("usuarios").update({
        "status": "revogado",
    }).eq("id", user["id"]).execute()

    st.warning(f"Acesso de **{user['chave']}** revogado.")
    st.rerun()


def _resetar_senha(user: dict):
    """Gera nova senha provisória para o usuário."""
    senha_texto, senha_hash = gerar_senha_provisoria()

    supabase().table("usuarios").update({
        "senha_hash": senha_hash,
        "trocar_senha": True,
    }).eq("id", user["id"]).execute()

    st.success(f"Senha de **{user['chave']}** resetada!")
    st.warning(
        f"🔑 **Nova senha provisória — copie e repasse:**\n\n"
        f"```\n{senha_texto}\n```"
    )


def _alterar_perfil(user: dict, novo_perfil: str):
    """Altera o perfil de um usuário (operador/admin)."""
    supabase().table("usuarios").update({
        "perfil": novo_perfil,
    }).eq("id", user["id"]).execute()

    label = "promovido a Admin" if novo_perfil == "admin" else "rebaixado a Operador"
    st.success(f"**{user['chave']}** {label}.")
    st.rerun()


# ---------------------------------------------------------------------------
# Seção: Usuários Revogados
# ---------------------------------------------------------------------------

def _secao_revogados():
    """Lista usuários com acesso revogado ou rejeitado."""
    resp = (
        supabase()
        .table("usuarios")
        .select("*")
        .in_("status", ["revogado", "rejeitado"])
        .order("chave", desc=False)
        .execute()
    )

    if not resp.data:
        st.info("Nenhum usuário revogado ou rejeitado.")
        return

    st.markdown(f"**{len(resp.data)} usuário(s) revogado(s)/rejeitado(s):**")

    for user in resp.data:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])
            col1.markdown(f"**Chave:** {user['chave']}")
            col2.markdown(f"**Lotação:** {user['lotacao']}")
            col3.markdown(f"**Status:** {user['status']}")
            col4.markdown(f"**Perfil:** {user['perfil']}")

            if st.button("♻️ Reativar", key=f"reativar_{user['id']}"):
                _reativar_usuario(user)


def _reativar_usuario(user: dict):
    """Reativa um usuário revogado com nova senha provisória."""
    senha_texto, senha_hash = gerar_senha_provisoria()

    supabase().table("usuarios").update({
        "status": "ativo",
        "senha_hash": senha_hash,
        "trocar_senha": True,
    }).eq("id", user["id"]).execute()

    st.success(f"**{user['chave']}** reativado!")
    st.warning(
        f"🔑 **Nova senha provisória — copie e repasse:**\n\n"
        f"```\n{senha_texto}\n```"
    )


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _formatar_data(data_str: str | None) -> str:
    """Formata timestamp ISO para exibição simples."""
    if not data_str:
        return "—"
    try:
        return data_str[:10]  # YYYY-MM-DD
    except Exception:
        return str(data_str)
