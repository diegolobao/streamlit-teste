"""
databricks_client.py — Leitura de notas do Databricks (SAP PM)
Salva JSON local para validação antes de enviar ao Supabase.
"""

import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Configuração Supabase ──
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() != "false"

# ── Configuração Databricks ──
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "dt0046_prd")
DATABRICKS_SCHEMA = os.getenv("DATABRICKS_SCHEMA", "sap_pm_consumo")
DATABRICKS_TABLE = os.getenv("DATABRICKS_TABLE", "notas_texto_longo_zf_zi_zs")

TABLE_FQN = f"{DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}.{DATABRICKS_TABLE}"

# Diretório para salvar JSONs de teste (desabilitado)
# DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
# os.makedirs(DATA_DIR, exist_ok=True)


def _get_connection():
    """Cria conexão com o Databricks SQL Warehouse."""
    from databricks import sql as dbsql
    if not all([DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN]):
        raise ValueError(
            "Variáveis DATABRICKS_HOST, DATABRICKS_HTTP_PATH e DATABRICKS_TOKEN "
            "são obrigatórias no .env"
        )
    return dbsql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
    )


def _limpar_texto_sap(texto: str) -> str:
    """Remove asteriscos do texto longo SAP e limpa espaços."""
    if not texto:
        return ""
    return re.sub(r"\s*\*\s*", "\r", str(texto)).strip()


def buscar_nota(cd_nota: str) -> dict | None:
    """Busca uma nota no Databricks. Retorna None se não encontrada."""
    nota_limpa = "".join(ch for ch in str(cd_nota) if ch.isdigit())
    nota_padrao = nota_limpa.zfill(12)

    with _get_connection() as conn:
        cursor = conn.cursor()
        query = f"""
            SELECT cd_nota, cd_ordem_nt, cd_ctr_trab_nt, ds_texto_longo_notas,
                   ds_nota, cd_local_inst_nt, cd_autor_nt, cd_status_sistema_nt, cd_status_usuario_nt
            FROM {TABLE_FQN}
            WHERE CAST(cd_nota AS STRING) IN ('{nota_limpa}', '{nota_padrao}')
            LIMIT 1
        """
        cursor.execute(query)
        row = cursor.fetchone()

    if not row:
        return None

    return {
        "numero_nota": nota_limpa[-8:],
        "ordem_servico": row[1],
        "centro_trabalho": row[2],
        "texto_nota": _limpar_texto_sap(row[3]),
        "descricao_nota": row[4],
        "local_instalacao": row[5],
        "notificador": row[6],
        "status_sistema": row[7],
        "status_usuario": row[8],
    }


def buscar_notas_batch(lista_notas: list[str]) -> list[dict]:
    """Busca múltiplas notas de uma vez no Databricks."""
    notas_limpas = []
    for n in lista_notas:
        limpa = "".join(ch for ch in str(n) if ch.isdigit())
        notas_limpas.append(limpa)
        notas_limpas.append(limpa.zfill(12))

    notas_unicas = list(set(notas_limpas))
    in_clause = ", ".join(f"'{n}'" for n in notas_unicas)

    with _get_connection() as conn:
        cursor = conn.cursor()
        query = f"""
            SELECT cd_nota, cd_ordem_nt, cd_ctr_trab_nt, ds_texto_longo_notas,
                   ds_nota, cd_local_inst_nt, cd_autor_nt, cd_status_sistema_nt, cd_status_usuario_nt
            FROM {TABLE_FQN}
            WHERE CAST(cd_nota AS STRING) IN ({in_clause})
        """
        cursor.execute(query)
        rows = cursor.fetchall()

    resultados = []
    notas_ja_processadas = set()

    for row in rows:
        nota_num = "".join(ch for ch in str(row[0]) if ch.isdigit())[-8:]
        if nota_num in notas_ja_processadas:
            continue
        notas_ja_processadas.add(nota_num)

        resultados.append({
            "numero_nota": nota_num,
            "ordem_servico": row[1],
            "centro_trabalho": row[2],
            "texto_nota": _limpar_texto_sap(row[3]),
            "descricao_nota": row[4],
            "local_instalacao": row[5],
            "notificador": row[6],
            "status_sistema": row[7],
            "status_usuario": row[8],
        })

    return resultados


def salvar_supabase(dados, chave: str = None, lotacao: str = None) -> dict:
    """Salva nota(s) na tabela notas_raw do Supabase via upsert."""
    if not all([SUPABASE_URL, SUPABASE_KEY]):
        raise ValueError("SUPABASE_URL e SUPABASE_KEY são obrigatórias no .env")

    # Normaliza para lista
    registros = dados if isinstance(dados, list) else [dados]

    # Injeta chave/lotacao do usuário logado em cada registro
    if chave or lotacao:
        for reg in registros:
            if chave:
                reg["chave"] = chave
            if lotacao:
                reg["lotacao"] = lotacao

    url = f"{SUPABASE_URL}/rest/v1/notas_raw"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }

    resp = requests.post(url, headers=headers, json=registros, verify=SSL_VERIFY)
    resp.raise_for_status()
    return resp.json()


# def salvar_json_local(dados, nome_arquivo: str) -> str:
#     """Salva dados em JSON na pasta data/ para validação."""
#     filepath = os.path.join(DATA_DIR, nome_arquivo)
#     with open(filepath, "w", encoding="utf-8") as f:
#         json.dump(dados, f, indent=2, ensure_ascii=False)
#     return filepath


# def carregar_json_local(nome_arquivo: str):
#     """Carrega JSON da pasta data/."""
#     filepath = os.path.join(DATA_DIR, nome_arquivo)
#     if not os.path.exists(filepath):
#         return None
#     with open(filepath, "r", encoding="utf-8") as f:
#         return json.load(f)


# ── CLI para teste rápido ──
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python databricks_client.py <nota1> [nota2] [nota3] ...")
        sys.exit(1)

    notas = sys.argv[1:]

    if len(notas) == 1:
        print(f"Buscando nota {notas[0]}...")
        resultado = buscar_nota(notas[0])
        if resultado:
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
            # Salvar no Supabase
            try:
                salvar_supabase(resultado)
                print(f"✅ Nota {resultado['numero_nota']} salva no Supabase!")
            except Exception as e:
                print(f"❌ Erro ao salvar no Supabase: {e}")
        else:
            print(f"❌ Nota {notas[0]} não encontrada.")
    else:
        print(f"Buscando {len(notas)} notas...")
        resultados = buscar_notas_batch(notas)
        print(f"✅ {len(resultados)} notas encontradas.")
        for r in resultados:
            print(f"  • {r['numero_nota']} — {r['descricao_nota']}")
        # Salvar no Supabase
        if resultados:
            try:
                salvar_supabase(resultados)
                print(f"✅ {len(resultados)} notas salvas no Supabase!")
            except Exception as e:
                print(f"❌ Erro ao salvar no Supabase: {e}")
