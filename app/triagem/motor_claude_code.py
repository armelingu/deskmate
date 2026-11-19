"""Motor de triagem via Claude Code CLI em modo nao interativo, usado quando
TRIAGEM_MOTOR=claude_code (padrao) - usa a assinatura do usuario via `claude`
em vez de uma chave de API.

Seguranca (ver SPEC e CLAUDE.md - nunca acessar repositorio nem rodar
comandos fora do que foi pedido):
  - `--restricted --tools ""`: nenhuma ferramenta disponivel (sem Bash, sem
    Read/Edit/Write, sem WebFetch) e as configuracoes de projeto/usuario sao
    ignoradas.
  - `--strict-mcp-config`: nenhum servidor MCP e carregado.
  - roda num `tempfile.TemporaryDirectory()` novo a cada chamada - vazio,
    fora de qualquer repositorio, sem CLAUDE.md para descobrir.
  - `--system-prompt` substitui o prompt padrao inteiro (que e onde
    CLAUDE.md/memoria de projeto normalmente entrariam), em vez de so
    complementa-lo.
  - `--no-session-persistence`: a chamada nao fica salva no historico de
    sessoes do Claude Code.
  - `--permission-prompts none`: qualquer coisa que pedisse aprovacao e
    negada automaticamente (nao deveria nem ser possivel, ja sem ferramentas).

Uma triagem por vez (trava de processo) para nao abrir varios `claude`
em paralelo; timeout configuravel via `CLAUDE_CODE_TIMEOUT_SEGUNDOS`.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import threading

from app import config
from app.triagem.esquema import (
    SYSTEM_PROMPT_TRIAGEM,
    ResultadoTriagem,
    TriagemFalhou,
    construir_esquema_triagem,
    validar_e_construir,
)

_TRAVA = threading.Lock()


def _montar_comando(texto: str) -> list[str]:
    return [
        config.CLAUDE_CODE_CAMINHO,
        "--print",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(construir_esquema_triagem()),
        "--model",
        config.CLAUDE_CODE_MODELO,
        "--restricted",
        "--tools",
        "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--permission-prompts",
        "none",
        "--system-prompt",
        SYSTEM_PROMPT_TRIAGEM,
        texto,
    ]


def _executar_processo(comando: list[str], diretorio: str) -> subprocess.CompletedProcess:
    """Isolado numa funcao propria - o unico ponto que os testes mockam
    (nenhum teste executa o CLI de verdade)."""
    return subprocess.run(
        comando,
        cwd=diretorio,
        capture_output=True,
        text=True,
        timeout=config.CLAUDE_CODE_TIMEOUT_SEGUNDOS,
    )


def triar(texto: str) -> ResultadoTriagem:
    """Chamada sincrona e bloqueante - o orquestrador (`app.triagem`) a roda
    numa thread (`asyncio.to_thread`) para nao travar o event loop."""
    comando = _montar_comando(texto)

    with _TRAVA, tempfile.TemporaryDirectory(prefix="deskmate-triagem-") as diretorio_vazio:
        try:
            processo = _executar_processo(comando, diretorio_vazio)
        except subprocess.TimeoutExpired as erro:
            raise TriagemFalhou(
                f"Claude Code nao respondeu em {config.CLAUDE_CODE_TIMEOUT_SEGUNDOS}s."
            ) from erro
        except FileNotFoundError as erro:
            raise TriagemFalhou(
                f"Nao encontrei o executavel '{config.CLAUDE_CODE_CAMINHO}' do Claude Code "
                "- confira CLAUDE_CODE_CAMINHO no .env."
            ) from erro

    if processo.returncode != 0:
        detalhe = (processo.stderr or processo.stdout or "").strip()[:500]
        raise TriagemFalhou(f"Claude Code terminou com codigo {processo.returncode}: {detalhe}")

    try:
        envelope = json.loads(processo.stdout)
    except json.JSONDecodeError as erro:
        raise TriagemFalhou(f"Saida do Claude Code nao e um JSON valido: {erro}") from erro

    if not isinstance(envelope, dict):
        raise TriagemFalhou("Saida do Claude Code nao e um objeto JSON.")

    if envelope.get("is_error"):
        raise TriagemFalhou(f"Claude Code devolveu erro: {envelope.get('result')!r}")

    resultado_bruto = envelope.get("result")
    try:
        dados = json.loads(resultado_bruto) if isinstance(resultado_bruto, str) else resultado_bruto
    except json.JSONDecodeError as erro:
        raise TriagemFalhou(f"O texto final do Claude Code nao e um JSON valido: {erro}") from erro

    uso = envelope.get("usage") or {}
    tokens_entrada = uso.get("input_tokens")
    tokens_saida = uso.get("output_tokens")
    custo_usd = envelope.get("total_cost_usd")

    return validar_e_construir(dados, tokens_entrada, tokens_saida, custo_usd)
