"""Ponto de entrada da aplicacao FastAPI."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config  # noqa: F401  carrega o .env cedo, antes do app.database ler as envs
from app.database import criar_tabelas
from app.routers import demandas, eventos, paginas


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    criar_tabelas()
    yield


app = FastAPI(title="Agent de Demandas", lifespan=ciclo_de_vida)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(demandas.router)
app.include_router(eventos.router)
app.include_router(paginas.router)
