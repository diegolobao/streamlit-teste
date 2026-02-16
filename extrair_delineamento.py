"""
extrair_delineamento.py — Extração de delineamento de notas via Azure OpenAI
Lê texto_nota do Supabase → envia ao LLM → retorna JSON estruturado.
"""

import os
import json
import requests
import httpx
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel, Field
from typing import List, Optional

load_dotenv()

# ── Configuração ──
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() != "false"

AZURE_OPENAI_BASE_URL = os.getenv("AZURE_OPENAI_BASE_URL")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-petrobras")

# Pasta temporária para salvar delineamentos extraídos
DELINEAMENTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "delineamentos")
os.makedirs(DELINEAMENTOS_DIR, exist_ok=True)


# ── Schema Pydantic (saída estruturada — o que a IA extrai) ──

class Material(BaseModel):
    nm: str = Field(..., description="Código SAP do material (NM). Ex: '12.016.888'")
    quantidade: float = Field(default=1.0, description="Quantidade necessária.")


class Operacao(BaseModel):
    centro_trabalho_executor: str = Field(
        ...,
        description="Abreviação da equipe executora em MAIÚSCULAS. "
        "Valores válidos: INS, AUT, ELE, MEC, CALD, PINT, IRATA."
    )
    descricao_operacao: str = Field(
        ..., max_length=40, description="Descrição curta da tarefa (máx 40 caracteres)."
    )
    numero_executantes: int = Field(default=1, description="Quantidade de pessoas.")
    duracao_hh: float = Field(default=8.0, description="Duração estimada em horas.")
    materiais: List[Material] = Field(
        default_factory=list, description="Lista de materiais para esta operação."
    )


class Delineamento(BaseModel):
    operacoes: List[Operacao] = Field(
        ..., description="Lista de operações/tarefas a serem executadas."
    )


# ── Mapeamento de abreviações para nomes completos ──

MAPA_CENTRO_TRABALHO = {
    "INS": "Instrumentação",
    "INST": "Instrumentação",
    "AUT": "Automação",
    "ELE": "Eletricista",
    "MEC": "Mecânico",
    "CALD": "Caldeiraria",
    "PINT": "Pintura",
    "IRATA": "Eletricista Irata",
}


# ── System Prompt ──

SYSTEM_PROMPT = """Você é um planejador de manutenção industrial. Analise o texto de uma nota de manutenção e extraia as seguintes informações em formato estruturado:

1. **O que precisa ser feito?** — Descreva cada tarefa/operação necessária.
2. **Qual especialidade/equipe deve executar?** — Identifique a equipe e retorne APENAS a abreviação padronizada:
   - Instrumentação → INS
   - Automação → AUT
   - Eletricista → ELE
   - Mecânico → MEC
   - Caldeiraria → CALD
   - Pintura → PINT
   - Escalador/Irata/Eletricista irata/ Eletricista escalador → IRATA
3. **Quantas pessoas e horas?** — Extraia número de executantes e duração em horas.
4. **Quais materiais são necessários?** — Extraia código SAP (NM) e quantidade.

REGRAS:
- Extraia APENAS o que está explícito no texto. Não invente dados.
- Se alguma informação não estiver presente, use valores padrão (1 pessoa, 8h, lista vazia de materiais).
- O campo 'descricao_operacao' de cada operação deve ter no MÁXIMO 40 caracteres.
- Retorne APENAS o JSON estruturado conforme o schema fornecido."""


# ── Cliente Azure OpenAI ──

# Caminho do certificado corporativo (se existir)
CERT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "petrobras-ca-root.pem")


def _get_openai_client() -> AzureOpenAI:
    """Cria cliente Azure OpenAI com certificado corporativo."""
    if not all([AZURE_OPENAI_BASE_URL, AZURE_OPENAI_API_KEY]):
        raise ValueError(
            "AZURE_OPENAI_BASE_URL e AZURE_OPENAI_API_KEY são obrigatórias no .env"
        )
    # Usa certificado corporativo se existir, senão usa SSL_VERIFY do .env
    if os.path.exists(CERT_PATH):
        http_client = httpx.Client(verify=CERT_PATH)
    else:
        http_client = httpx.Client(verify=SSL_VERIFY)
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        base_url=AZURE_OPENAI_BASE_URL,
        http_client=http_client,
    )


# ── Buscar nota do Supabase ──

def buscar_nota_supabase(numero_nota: str) -> dict | None:
    """Busca uma nota na tabela notas_raw do Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/notas_raw"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    params = {"numero_nota": f"eq.{numero_nota}", "limit": "1"}

    resp = requests.get(url, headers=headers, params=params, verify=SSL_VERIFY)
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else None


# ── Extração com LLM ──

def extrair_delineamento(texto_nota: str) -> Delineamento:
    """Envia texto_nota ao Azure OpenAI e retorna Delineamento estruturado."""
    client = _get_openai_client()
    try:
        response = client.beta.chat.completions.parse(
            model=AZURE_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": texto_nota},
            ],
            temperature=0.0,
            response_format=Delineamento,
        )
        return response.choices[0].message.parsed
    finally:
        client._client.close()


# ── Salvar delineamento no Supabase ──

def salvar_delineamento_supabase(delineamento: dict, chave: str = None, lotacao: str = None) -> dict:
    """Salva delineamento na tabela notas_delineadas do Supabase via upsert."""
    if not all([SUPABASE_URL, SUPABASE_KEY]):
        raise ValueError("SUPABASE_URL e SUPABASE_KEY são obrigatórias no .env")

    # Injeta chave/lotacao do usuário logado
    if chave:
        delineamento["chave"] = chave
    if lotacao:
        delineamento["lotacao"] = lotacao

    url = f"{SUPABASE_URL}/rest/v1/notas_delineadas"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }

    resp = requests.post(url, headers=headers, json=delineamento, verify=SSL_VERIFY)
    resp.raise_for_status()
    return resp.json()


# ── Buscar operações originais da IA (notas_delineadas) ──

def buscar_operacoes_ia(numero_nota: str) -> list | None:
    """Retorna as operações originais geradas pela IA para uma nota."""
    if not all([SUPABASE_URL, SUPABASE_KEY]):
        return None

    url = f"{SUPABASE_URL}/rest/v1/notas_delineadas"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    params = {"select": "operacoes", "numero_nota": f"eq.{numero_nota}"}
    resp = requests.get(url, headers=headers, params=params, verify=SSL_VERIFY)
    resp.raise_for_status()
    dados = resp.json()
    return dados[0]["operacoes"] if dados else None


# ── Marcar nota como revisada em notas_delineadas ──

def marcar_revisao_supabase(numero_nota: str) -> bool:
    """Seta revisao=true na notas_delineadas (único PATCH permitido)."""
    url = f"{SUPABASE_URL}/rest/v1/notas_delineadas?numero_nota=eq.{numero_nota}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    resp = requests.patch(url, headers=headers, json={"revisao": True}, verify=SSL_VERIFY)
    return resp.ok


# ── Score automático ──

def calcular_score(operacoes_ia: list, operacoes_revisadas: list) -> int:
    """
    Compara operações da IA vs revisadas e retorna score 1-5.
    Critérios detalhados em score.md.
    """
    # Normaliza para comparação
    def _normalizar_op(op: dict) -> dict:
        """Extrai campos comparáveis (ignora materiais)."""
        return {
            "centro_trabalho_executor": str(op.get("centro_trabalho_executor", "")).strip().upper(),
            "descricao_operacao": str(op.get("descricao_operacao", "")).strip(),
            "numero_executantes": str(op.get("numero_executantes", "")).strip(),
            "duracao_hh": str(op.get("duracao_hh", "")).strip(),
        }

    ops_ia = [_normalizar_op(op) for op in operacoes_ia]
    ops_rev = [_normalizar_op(op) for op in operacoes_revisadas]

    # Score 5: idênticos
    if ops_ia == ops_rev:
        return 5

    # Quantidade diferente → Score 2 ou 1
    if len(ops_ia) != len(ops_rev):
        # Mais de 50% removidas → Score 1
        if len(ops_ia) > 0:
            # Contar quantas operações originais ainda existem (por especialidade + descrição)
            centros_ia = [op["centro_trabalho_executor"] for op in ops_ia]
            centros_rev = [op["centro_trabalho_executor"] for op in ops_rev]
            # Calcular sobreposição mínima
            from collections import Counter
            counter_ia = Counter(centros_ia)
            counter_rev = Counter(centros_rev)
            sobreposicao = sum((counter_ia & counter_rev).values())
            if sobreposicao < len(ops_ia) * 0.5:
                return 1
        return 2

    # Mesma quantidade → comparar campo a campo
    mudou_especialidade = False
    mudou_descricao = False
    mudou_numerico = False

    for ia, rev in zip(ops_ia, ops_rev):
        if ia["centro_trabalho_executor"] != rev["centro_trabalho_executor"]:
            mudou_especialidade = True
        if ia["descricao_operacao"] != rev["descricao_operacao"]:
            mudou_descricao = True
        if (ia["numero_executantes"] != rev["numero_executantes"] or
                ia["duracao_hh"] != rev["duracao_hh"]):
            mudou_numerico = True

    # Score 4: só ajustes numéricos
    if not mudou_especialidade and not mudou_descricao and mudou_numerico:
        return 4

    # Score 3: mudou descrição e/ou especialidade mas mesma estrutura
    if mudou_especialidade or mudou_descricao:
        return 3

    # Fallback (não deveria chegar aqui, mas por segurança)
    return 4


# ── Salvar revisão no Supabase ──

def salvar_revisao_supabase(
    numero_nota: str,
    operacoes_revisadas: list,
    chave_revisor: str = None,
    lotacao_revisor: str = None,
) -> dict:
    """
    Salva delineamento revisado na tabela notas_revisadas (upsert).
    Calcula score automático comparando com notas_delineadas.
    Marca revisao=true em notas_delineadas.
    """
    if not all([SUPABASE_URL, SUPABASE_KEY]):
        raise ValueError("SUPABASE_URL e SUPABASE_KEY são obrigatórias no .env")

    # 1. Buscar operações originais da IA
    operacoes_ia = buscar_operacoes_ia(numero_nota)
    score = calcular_score(operacoes_ia, operacoes_revisadas) if operacoes_ia else 3

    # 2. Montar payload
    payload = {
        "numero_nota": numero_nota,
        "operacoes": operacoes_revisadas,
        "score": score,
    }
    if chave_revisor:
        payload["chave_revisor"] = chave_revisor
    if lotacao_revisor:
        payload["lotacao_revisor"] = lotacao_revisor

    # 3. Upsert em notas_revisadas
    url = f"{SUPABASE_URL}/rest/v1/notas_revisadas"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    resp = requests.post(url, headers=headers, json=payload, verify=SSL_VERIFY)
    resp.raise_for_status()

    # 4. Marcar revisao=true em notas_delineadas
    marcar_revisao_supabase(numero_nota)

    return resp.json()


# ── CLI ──

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python extrair_delineamento.py <numero_nota> [numero_nota2] ...")
        print("     python extrair_delineamento.py --texto 'texto livre para testar'")
        sys.exit(1)

    # Modo texto livre (para testes sem Supabase)
    if sys.argv[1] == "--texto":
        texto = " ".join(sys.argv[2:])
        print(f"Extraindo delineamento do texto fornecido...")
        resultado = extrair_delineamento(texto)
        print(json.dumps(resultado.model_dump(), indent=2, ensure_ascii=False))
        sys.exit(0)

    # Modo por número de nota (busca no Supabase)
    for nota in sys.argv[1:]:
        print(f"\n{'='*60}")
        print(f"Nota: {nota}")
        print(f"{'='*60}")

        # 1. Buscar no Supabase
        dados = buscar_nota_supabase(nota)
        if not dados:
            print(f"❌ Nota {nota} não encontrada no Supabase.")
            continue

        texto_nota = dados.get("texto_nota", "")
        if not texto_nota.strip():
            print(f"❌ Nota {nota} não possui texto_nota.")
            continue

        print(f"📋 Descrição: {dados.get('descricao_nota', 'N/A')}")
        print(f"🔧 Centro de trabalho: {dados.get('centro_trabalho', 'N/A')}")
        print(f"\n🤖 Extraindo delineamento com IA...")

        # 2. Extrair com LLM
        try:
            resultado = extrair_delineamento(texto_nota)

            # 3. Pós-processamento: montar JSON final com dados do Supabase + IA
            operacoes_final = []
            for i, op in enumerate(resultado.operacoes):
                abrev = op.centro_trabalho_executor.upper()
                operacoes_final.append({
                    "operação": f"{(i + 1) * 10:04d}",
                    "centro_trabalho_executor": MAPA_CENTRO_TRABALHO.get(abrev, abrev),
                    "descricao_operacao": op.descricao_operacao[:40],
                    "numero_executantes": str(op.numero_executantes),
                    "duracao_hh": str(op.duracao_hh).replace(".", ","),
                    "materiais": [{"nm": m.nm, "quantidade": str(m.quantidade)} for m in op.materiais],
                })

            resultado_final = {
                "numero_nota": dados.get("numero_nota", nota),
                "centro_trabalho_responsavel": dados.get("centro_trabalho", ""),
                "descricao_geral": dados.get("descricao_nota", ""),
                "area_responsavel": dados.get("notificador", "").split("-")[0],
                "operacoes": operacoes_final,
            }

            print(json.dumps(resultado_final, indent=2, ensure_ascii=False))

            # Salvar JSON temporário
            filepath = os.path.join(DELINEAMENTOS_DIR, f"DELINEAMENTO_{nota}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(resultado_final, f, indent=2, ensure_ascii=False)
            print(f"💾 JSON salvo em: {filepath}")

            # Salvar no Supabase
            try:
                salvar_delineamento_supabase(resultado_final)
                print(f"✅ Nota {nota} salva no Supabase (notas_delineadas)!")
            except Exception as e:
                print(f"❌ Erro ao salvar no Supabase: {e}")
        except Exception as e:
            print(f"❌ Erro na extração: {e}")
