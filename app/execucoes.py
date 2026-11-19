"""Acesso a dados das entidades `execucao` e `evento`.

Cada execucao do agent (triagem, desenvolvimento, resumo) grava tokens e
custo desde o inicio; cada passo dela vira um evento (mensagem, tool_call,
tool_result, erro ou aprovacao).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Evento, Execucao, StatusExecucao, TipoEvento, TipoExecucao


def iniciar_execucao(
    db: Session, demanda_id: int, tipo: TipoExecucao, modelo: str | None = None
) -> Execucao:
    execucao = Execucao(
        demanda_id=demanda_id, tipo=tipo, modelo=modelo, status=StatusExecucao.EM_ANDAMENTO
    )
    db.add(execucao)
    db.commit()
    db.refresh(execucao)
    return execucao


def registrar_evento(
    db: Session, execucao_id: int, tipo: TipoEvento, payload: dict | None = None
) -> Evento:
    evento = Evento(execucao_id=execucao_id, tipo=tipo, payload=payload)
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


def finalizar_execucao(
    db: Session,
    execucao: Execucao,
    status: StatusExecucao,
    tokens_entrada: int | None = None,
    tokens_saida: int | None = None,
    custo_usd: float | None = None,
    resultado: str | None = None,
    fim: datetime | None = None,
) -> Execucao:
    execucao.status = status
    execucao.tokens_entrada = tokens_entrada
    execucao.tokens_saida = tokens_saida
    execucao.custo_usd = custo_usd
    execucao.resultado = resultado
    execucao.fim = fim or datetime.now(timezone.utc)
    db.commit()
    db.refresh(execucao)
    return execucao


def execucao_mais_recente(db: Session, demanda_id: int, tipo: TipoExecucao) -> Execucao | None:
    """Ultima execucao de um tipo para a demanda (usada para anexar o evento de
    aprovacao da confirmacao da triagem e para detectar falha de triagem)."""
    consulta = (
        select(Execucao)
        .where(Execucao.demanda_id == demanda_id, Execucao.tipo == tipo)
        .order_by(Execucao.inicio.desc(), Execucao.id.desc())
        .limit(1)
    )
    return db.scalars(consulta).first()
