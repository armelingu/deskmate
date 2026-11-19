"""Motor de triagem via API do Claude (tool use), usado quando TRIAGEM_MOTOR=api.

Recebe so o texto da demanda (nunca o historico da fila), devolve JSON
estruturado atraves de uma tool forcada (`tool_choice`), com `max_tokens`
baixo e um system prompt fixo marcado para prompt caching.
"""

from __future__ import annotations

from functools import lru_cache

import anthropic

from app import config
from app.triagem.esquema import (
    FERRAMENTA_ESTRUTURAR_DEMANDA,
    NOME_FERRAMENTA,
    SYSTEM_PROMPT_TRIAGEM,
    ResultadoTriagem,
    TriagemFalhou,
    validar_e_construir,
)


@lru_cache(maxsize=1)
def obter_cliente() -> anthropic.Anthropic:
    """Cliente Anthropic (lazy, uma instancia por processo).

    Isolado numa funcao propria (em vez de um cliente global no import) para
    os testes poderem substitui-la por um cliente falso sem nunca tocar na
    API de verdade.
    """
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def chamar_claude(cliente: anthropic.Anthropic, texto: str):
    """Chamada isolada a API - o unico ponto que os testes precisam mockar."""
    return cliente.messages.create(
        model=config.CLAUDE_TRIAGEM_MODELO,
        max_tokens=config.CLAUDE_TRIAGEM_MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT_TRIAGEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[FERRAMENTA_ESTRUTURAR_DEMANDA],
        tool_choice={"type": "tool", "name": NOME_FERRAMENTA},
        messages=[{"role": "user", "content": texto}],
    )


def _custo_usd(tokens_entrada: int, tokens_saida: int) -> float:
    entrada = tokens_entrada / 1_000_000 * config.CLAUDE_TRIAGEM_PRECO_ENTRADA_USD_MI
    saida = tokens_saida / 1_000_000 * config.CLAUDE_TRIAGEM_PRECO_SAIDA_USD_MI
    return round(entrada + saida, 6)


def triar(texto: str) -> ResultadoTriagem:
    """Chamada sincrona e bloqueante - o orquestrador (`app.triagem`) a
    roda numa thread (`asyncio.to_thread`) para nao travar o event loop."""
    cliente = obter_cliente()
    mensagem = chamar_claude(cliente, texto)

    bloco = next((b for b in mensagem.content if getattr(b, "type", None) == "tool_use"), None)
    if bloco is None:
        raise TriagemFalhou("A resposta do Claude nao trouxe a ferramenta esperada.")

    tokens_entrada = mensagem.usage.input_tokens
    tokens_saida = mensagem.usage.output_tokens
    return validar_e_construir(
        bloco.input, tokens_entrada, tokens_saida, _custo_usd(tokens_entrada, tokens_saida)
    )
