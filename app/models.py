"""Modelos do ORM. Fase 1: apenas a entidade `demanda`."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

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
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
