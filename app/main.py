"""Ponto de entrada da aplicacao FastAPI."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config  # noqa: F401  carrega o .env cedo, antes do app.database ler as envs
from app.database import criar_tabelas
from app.routers import demandas, eventos, paginas

DIRETORIO_APP = Path(__file__).resolve().parent


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    criar_tabelas()
    yield


app = FastAPI(title="Agent de Demandas", lifespan=ciclo_de_vida)

# Caminho absoluto (nao relativo ao diretorio de trabalho do processo, que
# muda conforme de onde o `deskmate` e chamado).
app.mount("/static", StaticFiles(directory=DIRETORIO_APP / "static"), name="static")

app.include_router(demandas.router)
app.include_router(eventos.router)
app.include_router(paginas.router)
