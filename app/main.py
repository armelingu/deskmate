"""Ponto de entrada da aplicacao FastAPI."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import criar_tabelas
from app.routers import demandas, eventos


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    criar_tabelas()
    yield


app = FastAPI(title="Agent de Demandas", lifespan=ciclo_de_vida)

app.include_router(demandas.router)
app.include_router(eventos.router)
