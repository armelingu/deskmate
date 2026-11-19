"""Orquestra a triagem de uma demanda, despachando para o motor configurado.

`TRIAGEM_MOTOR` no `.env` escolhe o motor: "claude_code" (padrao - usa a
assinatura do usuario via CLI, sem precisar de chave de API) ou "api" (API
do Claude direto, com tool use). Cada motor expoe uma funcao sincrona
`triar(texto) -> ResultadoTriagem`; o resto (persistencia, eventos, SSE,
caminho de erro) e identico para os dois.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import config
from app.eventos import barramento
from app.execucoes import finalizar_execucao, iniciar_execucao, registrar_evento
from app.models import Demanda, StatusDemanda, StatusExecucao, TipoEvento, TipoExecucao
from app.triagem import motor_api, motor_claude_code
from app.triagem.esquema import TriagemFalhou  # noqa: F401  reexportado p/ conveniencia

logger = logging.getLogger(__name__)

_MOTORES = {
    "claude_code": motor_claude_code,
    "api": motor_api,
}


def _motor_e_modelo_atuais() -> tuple[object, str]:
    motor = _MOTORES.get(config.TRIAGEM_MOTOR)
    if motor is None:
        raise TriagemFalhou(
            f"TRIAGEM_MOTOR invalido: {config.TRIAGEM_MOTOR!r} (use 'claude_code' ou 'api')."
        )
    modelo = (
        config.CLAUDE_CODE_MODELO
        if config.TRIAGEM_MOTOR == "claude_code"
        else config.CLAUDE_TRIAGEM_MODELO
    )
    return motor, modelo


async def executar_triagem_em_background(demanda_id: int, db: Session) -> None:
    """Tarefa de segundo plano: tria a demanda e publica o resultado no SSE.

    Reusa a sessao de banco da requisicao que disparou a captura/retentativa
    (uma `Session` do SQLAlchemy pode ser reaberta apos `close()` - ela so
    reconecta ao mesmo engine/pool na proxima consulta). Isso garante que a
    tarefa enxerga o mesmo banco da requisicao original (essencial nos
    testes, que usam um banco em memoria por teste).

    Em caso de erro (API, CLI, timeout ou JSON invalido), a demanda continua
    em `Entrada` e o erro fica registrado na execucao/evento, para voce ver
    na mesa e tentar de novo - nao criei um estado novo so para isso.
    """
    try:
        demanda = db.get(Demanda, demanda_id)
        if demanda is None or demanda.status != StatusDemanda.ENTRADA:
            return

        try:
            motor, modelo = _motor_e_modelo_atuais()
        except TriagemFalhou as erro:
            logger.error("Configuracao de triagem invalida: %s", erro)
            return

        execucao = iniciar_execucao(db, demanda.id, TipoExecucao.TRIAGEM, modelo=modelo)
        texto = demanda.texto_original or demanda.titulo
        registrar_evento(
            db, execucao.id, TipoEvento.MENSAGEM, {"texto": texto, "motor": config.TRIAGEM_MOTOR}
        )

        try:
            resultado = await asyncio.to_thread(motor.triar, texto)
            registrar_evento(db, execucao.id, TipoEvento.TOOL_CALL, {"motor": config.TRIAGEM_MOTOR})
            registrar_evento(
                db,
                execucao.id,
                TipoEvento.TOOL_RESULT,
                {
                    "titulo": resultado.titulo,
                    "descricao": resultado.descricao,
                    "area": resultado.area,
                    "impacto": resultado.impacto,
                    "esforco": resultado.esforco.value,
                },
            )
        except Exception as erro:  # noqa: BLE001 - qualquer falha do motor vira evento de erro
            registrar_evento(db, execucao.id, TipoEvento.ERRO, {"mensagem": str(erro)})
            finalizar_execucao(db, execucao, StatusExecucao.ERRO, fim=datetime.now(timezone.utc))
            logger.warning(
                "Triagem da demanda %s falhou (motor=%s): %s", demanda_id, config.TRIAGEM_MOTOR, erro
            )
            await barramento.publicar({"colunas": [demanda.status.value]})
            return

        demanda.titulo = resultado.titulo
        demanda.descricao = resultado.descricao
        demanda.area = resultado.area
        demanda.impacto = resultado.impacto
        demanda.esforco = resultado.esforco
        demanda.status = StatusDemanda.TRIADA
        db.commit()

        finalizar_execucao(
            db,
            execucao,
            StatusExecucao.CONCLUIDA,
            tokens_entrada=resultado.tokens_entrada,
            tokens_saida=resultado.tokens_saida,
            custo_usd=resultado.custo_usd,
            resultado=resultado.descricao,
            fim=datetime.now(timezone.utc),
        )

        await barramento.publicar({"colunas": ["entrada", "triada"]})
    finally:
        db.close()
