"""
SmartTable — Streamlit Custom Component (tabela interativa)
Usa declare_component com path local — sem CDN externas.
"""

import os
import json
import streamlit as st
import streamlit.components.v1 as components

# Declara o componente apontando para o diretório local do frontend
_component_func = components.declare_component(
    "smart_table",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend"),
)


def smart_table(rows: list, columns: list, editable_fields: list = None,
                height: int = 500, key: str = None,
                supabase_url: str = "", supabase_key: str = "",
                supabase_table: str = "", primary_key: str = "id",
                group_key: str = None, group_merge_keys: list = None,
                jsonb_column: str = None, jsonb_op_key: str = None,
                field_map: dict = None):
    """
    Renderiza uma tabela interativa com checkboxes, edição inline,
    chips de materiais, select, botões de ação e agrupamento visual.

    Parâmetros de agrupamento:
    - group_key: coluna usada para agrupar linhas (ex: "nota")
    - group_merge_keys: colunas unidas via rowspan no grupo

    Parâmetros de edição JSONB:
    - jsonb_column: nome da coluna JSONB no Supabase (ex: "operacoes")
    - jsonb_op_key: chave dentro do JSONB que identifica a operação
      (ex: "operação"). Cada row deve ter "_op_id" com o valor.
    - field_map: mapeamento coluna_tabela → campo_jsonb
      (ex: {"cen_trab": "centro_trabalho_executor", ...})

    Retorna:
    --------
    dict ou None — Ação do usuário (ex: {"action": "view", "id": "10001234"})
    """
    data = {
        "rows": rows,
        "columns": columns,
        "editable_fields": editable_fields or [],
        "supabase_url": supabase_url,
        "supabase_key": supabase_key,
        "supabase_table": supabase_table,
        "primary_key": primary_key,
        "group_key": group_key,
        "group_merge_keys": group_merge_keys or [],
        "jsonb_column": jsonb_column,
        "jsonb_op_key": jsonb_op_key,
        "field_map": field_map or {},
    }

    component_value = _component_func(
        data=data,
        height=height,
        key=key,
        default=None,
    )

    return component_value
