"""Barramento de eventos em memoria para alimentar o painel via SSE.

Fase 1 nao tem a entidade `evento` (essa chega com execucao/triagem).
Aqui so avisamos os assinantes de quais status de demanda mudaram, para
a futura interface do painel atualizar via Server-Sent Events sem
precisar de polling.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator


class BarramentoEventos:
    """Pub/sub simples em memoria (um unico processo) para o painel."""

    def __init__(self) -> None:
        self._assinantes: set[asyncio.Queue[str]] = set()

    async def publicar(self, evento: dict) -> None:
        dados = json.dumps(evento, ensure_ascii=False)
        for fila in list(self._assinantes):
            await fila.put(dados)

    async def assinar(self) -> AsyncIterator[str]:
        fila: asyncio.Queue[str] = asyncio.Queue()
        self._assinantes.add(fila)
        try:
            while True:
                dados = await fila.get()
                yield f"data: {dados}\n\n"
        finally:
            self._assinantes.discard(fila)


barramento = BarramentoEventos()
