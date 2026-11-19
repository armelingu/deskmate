"""Schema e tipos compartilhados pelos motores de triagem (API e Claude Code).

O schema e o mesmo nos dois motores: no motor `api` vira o `input_schema` da
tool forcada; no motor `claude_code` vira o `--json-schema` passado ao CLI.
`area` e sempre um enum fechado (`config.AREAS_DISPONIVEIS`) - por isso o
schema e montado por uma funcao, nao um dict fixo: ele reflete o `.env` (e o
que os testes monkeypatcham) a cada chamada, em vez de travar a lista no
import deste modulo.
"""

from __future__ import annotations

from dataclasses import dataclass

from app import config
from app.models import Esforco

NOME_FERRAMENTA = "estruturar_demanda"

# Prompt fixo e enxuto de proposito: nao e inflado so para bater o tamanho
# minimo que algum modelo exige para o prompt caching valer a pena. No motor
# `api` o `cache_control` fica declarado mesmo assim - se o prompt for
# pequeno demais para cachear, o custo extra e desprezivel.
SYSTEM_PROMPT_TRIAGEM = (
    "Voce e o triador de demandas do deskmate. Recebe uma frase solta "
    "descrevendo uma demanda de desenvolvimento e devolve ela estruturada, "
    "sempre no formato pedido, com respostas curtas. A descricao tem no "
    "maximo 2 frases: a primeira diz direto o que fazer; a segunda so "
    "existe quando falta uma informacao essencial para entender o pedido, "
    "e nesse caso e so a pergunta sobre o que falta - nunca liste criterios "
    "de aceite, contexto extra ou topicos. area e sempre exatamente uma das "
    "opcoes dadas, nunca um valor livre. Nao invente contexto que nao esteja "
    "no texto. impacto e esforco sao sempre uma estimativa inicial, que quem "
    "pediu pode ajustar depois."
)


def construir_esquema_triagem() -> dict:
    """Monta o schema com a lista de areas atual (`config.AREAS_DISPONIVEIS`)."""
    return {
        "type": "object",
        "properties": {
            "titulo": {
                "type": "string",
                "description": "Titulo curto e claro da demanda (ate 80 caracteres).",
            },
            "descricao": {
                "type": "string",
                "description": (
                    "No maximo 2 frases: o que fazer e, so se faltar algo essencial, "
                    "a pergunta sobre o que falta. Nunca liste criterios de aceite ou topicos."
                ),
            },
            "area": {
                "type": "string",
                "enum": list(config.AREAS_DISPONIVEIS),
                "description": "Area afetada - escolha exatamente uma das opcoes dadas.",
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


def construir_ferramenta_estruturar_demanda() -> dict:
    return {
        "name": NOME_FERRAMENTA,
        "description": "Estrutura uma demanda de desenvolvimento a partir do texto livre recebido.",
        "input_schema": construir_esquema_triagem(),
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
    """Valida `dados` contra o schema atual e monta o resultado.

    Checagem manual (sem lib de JSON Schema generica) porque o schema e
    pequeno e fixo: confere as 5 chaves obrigatorias, que nao ha chave
    extra, os tipos, a area (precisa ser exatamente uma de
    `config.AREAS_DISPONIVEIS`) e os enums de impacto/esforco. Qualquer
    desvio vira `TriagemFalhou` - e tratado como falha de triagem (fica em
    Entrada, com o "Tentar de novo" na mesa), nunca como dado parcialmente
    aceito.
    """
    esquema = construir_esquema_triagem()

    if not isinstance(dados, dict):
        raise TriagemFalhou(f"Esperava um objeto JSON, recebi {type(dados).__name__}.")

    faltando = [c for c in esquema["required"] if c not in dados]
    if faltando:
        raise TriagemFalhou(f"Campos obrigatorios faltando na triagem: {', '.join(faltando)}.")

    extras = set(dados) - set(esquema["properties"])
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
    if area not in config.AREAS_DISPONIVEIS:
        raise TriagemFalhou(
            f"area {area!r} fora da lista configurada: {', '.join(config.AREAS_DISPONIVEIS)}."
        )

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
