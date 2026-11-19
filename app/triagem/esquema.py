"""Schema e tipos compartilhados pelos motores de triagem (API e Claude Code).

O schema e o mesmo nos dois motores: no motor `api` vira o `input_schema` da
tool forcada; no motor `claude_code` vira o `--json-schema` passado ao CLI.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Esforco

NOME_FERRAMENTA = "estruturar_demanda"

# Prompt fixo e enxuto de proposito: nao e inflado so para bater o tamanho
# minimo que algum modelo exige para o prompt caching valer a pena. No motor
# `api` o `cache_control` fica declarado mesmo assim - se o prompt for
# pequeno demais para cachear, o custo extra e desprezivel.
SYSTEM_PROMPT_TRIAGEM = (
    "Voce e o triador de demandas do deskmate. Recebe uma frase solta "
    "descrevendo uma demanda de desenvolvimento e devolve ela estruturada, "
    "sempre no formato pedido. Nao invente contexto que nao esteja no "
    "texto: se faltar informacao, deixe a area generica e va direto ao "
    "ponto na descricao. impacto e esforco sao sempre uma estimativa "
    "inicial, que quem pediu pode ajustar depois."
)

ESQUEMA_TRIAGEM = {
    "type": "object",
    "properties": {
        "titulo": {
            "type": "string",
            "description": "Titulo curto e claro da demanda (ate 80 caracteres).",
        },
        "descricao": {
            "type": "string",
            "description": (
                "Descricao estruturada, com contexto e criterio de aceite quando possivel."
            ),
        },
        "area": {
            "type": "string",
            "description": "Area ou sistema afetado (ex.: financeiro, comercial, ti).",
        },
        "impacto": {
            "type": "integer",
            "enum": [1, 2, 3],
            "description": "Impacto estimado: 1 baixo, 2 medio, 3 alto.",
        },
        "esforco": {
            "type": "string",
            "enum": ["P", "M", "G"],
            "description": "Esforco estimado: P pequeno, M medio, G grande.",
        },
    },
    "required": ["titulo", "descricao", "area", "impacto", "esforco"],
    "additionalProperties": False,
}

FERRAMENTA_ESTRUTURAR_DEMANDA = {
    "name": NOME_FERRAMENTA,
    "description": "Estrutura uma demanda de desenvolvimento a partir do texto livre recebido.",
    "input_schema": ESQUEMA_TRIAGEM,
}


@dataclass
class ResultadoTriagem:
    titulo: str
    descricao: str
    area: str
    impacto: int
    esforco: Esforco
    tokens_entrada: int | None
    tokens_saida: int | None
    custo_usd: float | None


class TriagemFalhou(Exception):
    """Levantada quando a triagem (por qualquer motor) falha ou devolve dado invalido."""


def validar_e_construir(
    dados: object,
    tokens_entrada: int | None,
    tokens_saida: int | None,
    custo_usd: float | None,
) -> ResultadoTriagem:
    """Valida `dados` contra `ESQUEMA_TRIAGEM` e monta o resultado.

    Checagem manual (sem lib de JSON Schema generica) porque o schema e
    pequeno e fixo: confere as 5 chaves obrigatorias, que nao ha chave
    extra, os tipos e os enums de impacto/esforco. Qualquer desvio vira
    `TriagemFalhou` - e tratado como falha de triagem (fica em Entrada,
    com o "Tentar de novo" na mesa), nunca como dado parcialmente aceito.
    """
    if not isinstance(dados, dict):
        raise TriagemFalhou(f"Esperava um objeto JSON, recebi {type(dados).__name__}.")

    faltando = [c for c in ESQUEMA_TRIAGEM["required"] if c not in dados]
    if faltando:
        raise TriagemFalhou(f"Campos obrigatorios faltando na triagem: {', '.join(faltando)}.")

    extras = set(dados) - set(ESQUEMA_TRIAGEM["properties"])
    if extras:
        raise TriagemFalhou(f"Campos inesperados na triagem: {', '.join(sorted(extras))}.")

    try:
        titulo = str(dados["titulo"]).strip()
        descricao = str(dados["descricao"]).strip()
        area = str(dados["area"]).strip()
        impacto = int(dados["impacto"])
        esforco = Esforco(dados["esforco"])
    except (TypeError, ValueError) as erro:
        raise TriagemFalhou(f"Resposta da triagem invalida: {erro}") from erro

    if not titulo or not descricao or not area:
        raise TriagemFalhou("titulo, descricao e area nao podem ser vazios.")
    if impacto not in (1, 2, 3):
        raise TriagemFalhou(f"impacto fora do permitido (1-3): {impacto!r}")

    return ResultadoTriagem(
        titulo=titulo,
        descricao=descricao,
        area=area,
        impacto=impacto,
        esforco=esforco,
        tokens_entrada=tokens_entrada,
        tokens_saida=tokens_saida,
        custo_usd=custo_usd,
    )
