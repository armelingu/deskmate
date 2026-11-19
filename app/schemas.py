"""Schemas Pydantic para entrada e saida da API de demandas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Esforco, StatusDemanda


class DemandaCriar(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    descricao: str | None = None
    solicitante: str | None = None
    area: str | None = None
    impacto: int | None = Field(default=None, ge=1, le=3)
    esforco: Esforco | None = None
    prazo: date | None = None
    delegavel: bool = False
    repositorio: str | None = None


class DemandaAtualizar(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descricao: str | None = None
    solicitante: str | None = None
    area: str | None = None
    impacto: int | None = Field(default=None, ge=1, le=3)
    esforco: Esforco | None = None
    prazo: date | None = None
    delegavel: bool | None = None
    repositorio: str | None = None


class DemandaMover(BaseModel):
    status: StatusDemanda
    posicao: int | None = Field(default=None, ge=0)


class DemandaCapturar(BaseModel):
    """Captura rapida: so o texto livre. O resto vem da triagem."""

    texto: str = Field(min_length=1)


class DemandaConfirmarTriagem(BaseModel):
    """Ajustes opcionais ao confirmar a triagem (voce pode so aceitar como veio)."""

    titulo: str = Field(min_length=1, max_length=200)
    descricao: str | None = None
    area: str | None = None
    impacto: int | None = Field(default=None, ge=1, le=3)
    esforco: Esforco | None = None
    delegavel: bool | None = None


class DemandaLeitura(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descricao: str | None
    solicitante: str | None
    area: str | None
    impacto: int | None
    esforco: Esforco | None
    status: StatusDemanda
    status_anterior: StatusDemanda | None
    posicao: int
    prazo: date | None
    delegavel: bool
    repositorio: str | None
    texto_original: str | None
    criado_em: datetime
    atualizado_em: datetime
