"""Modelos do ORM: demanda (fase 1) e execucao/evento (fase 2, triagem)."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StatusDemanda(str, enum.Enum):
    ENTRADA = "entrada"
    TRIADA = "triada"
    PRIORIZADA = "priorizada"
    EM_EXECUCAO = "em_execucao"
    EM_REVISAO = "em_revisao"
    CONCLUIDA = "concluida"
    BLOQUEADA = "bloqueada"
    CANCELADA = "cancelada"


class Esforco(str, enum.Enum):
    P = "P"
    M = "M"
    G = "G"


class TipoExecucao(str, enum.Enum):
    TRIAGEM = "triagem"
    DESENVOLVIMENTO = "desenvolvimento"
    RESUMO = "resumo"


class StatusExecucao(str, enum.Enum):
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    ERRO = "erro"


class TipoEvento(str, enum.Enum):
    MENSAGEM = "mensagem"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERRO = "erro"
    APROVACAO = "aprovacao"


class Demanda(Base):
    """Uma demanda de desenvolvimento na fila."""

    __tablename__ = "demanda"
    __table_args__ = (
        CheckConstraint("impacto IS NULL OR impacto BETWEEN 1 AND 3", name="ck_demanda_impacto"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    solicitante: Mapped[str | None] = mapped_column(String(120), nullable=True)
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    impacto: Mapped[int | None] = mapped_column(Integer, nullable=True)
    esforco: Mapped[Esforco | None] = mapped_column(Enum(Esforco), nullable=True)
    status: Mapped[StatusDemanda] = mapped_column(
        Enum(StatusDemanda), nullable=False, default=StatusDemanda.ENTRADA
    )
    status_anterior: Mapped[StatusDemanda | None] = mapped_column(Enum(StatusDemanda), nullable=True)
    posicao: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prazo: Mapped[date | None] = mapped_column(Date, nullable=True)
    delegavel: Mapped[bool] = mapped_column(default=False)
    repositorio: Mapped[str | None] = mapped_column(String(200), nullable=True)
    texto_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    execucoes: Mapped[list["Execucao"]] = relationship(
        back_populates="demanda", cascade="all, delete-orphan"
    )


class Execucao(Base):
    """Uma execucao do agent sobre uma demanda (triagem, desenvolvimento ou resumo).

    Grava tokens e custo desde o inicio, para a economia ser medida, nao estimada.
    """

    __tablename__ = "execucao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    demanda_id: Mapped[int] = mapped_column(ForeignKey("demanda.id"), nullable=False)
    tipo: Mapped[TipoExecucao] = mapped_column(Enum(TipoExecucao), nullable=False)
    status: Mapped[StatusExecucao] = mapped_column(
        Enum(StatusExecucao), nullable=False, default=StatusExecucao.EM_ANDAMENTO
    )
    modelo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(200), nullable=True)
    resultado: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nulo quando o motor de triagem nao informa (ex.: Claude Code CLI sem
    # esses dados na saida) - nunca estimado/inventado nesse caso.
    tokens_entrada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_saida: Mapped[int | None] = mapped_column(Integer, nullable=True)
    custo_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    inicio: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fim: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    demanda: Mapped["Demanda"] = relationship(back_populates="execucoes")
    eventos: Mapped[list["Evento"]] = relationship(
        back_populates="execucao", cascade="all, delete-orphan", order_by="Evento.ts"
    )


class Evento(Base):
    """Um passo registrado dentro de uma execucao (mensagem, tool call, erro, aprovacao...)."""

    __tablename__ = "evento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execucao_id: Mapped[int] = mapped_column(ForeignKey("execucao.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    tipo: Mapped[TipoEvento] = mapped_column(Enum(TipoEvento), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    execucao: Mapped["Execucao"] = relationship(back_populates="eventos")
