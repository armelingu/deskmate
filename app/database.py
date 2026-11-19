"""Configuracao do banco de dados (SQLite na fase 1, Postgres no futuro)."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Raiz do projeto (pai de app/) - nao o diretorio de trabalho do processo, que
# muda conforme de onde o `deskmate` e chamado (ex.: pelo wrapper global).
RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{RAIZ_DO_PROJETO / 'demandas.db'}")

_argumentos_conexao = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_argumentos_conexao)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Classe base declarativa para os modelos do ORM."""


def obter_sessao() -> Generator[Session, None, None]:
    """Dependencia do FastAPI: abre uma sessao e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas() -> None:
    """Cria as tabelas que ainda nao existem (sem migracoes na fase 1)."""
    from app import models  # noqa: F401  garante que os modelos sejam registrados

    Base.metadata.create_all(bind=engine)
