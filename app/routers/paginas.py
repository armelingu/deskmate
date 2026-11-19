"""Paginas HTML da sua mesa.

So GET aqui: toda escrita (capturar, mover, bloquear, confirmar triagem,
tentar de novo) passa pela API REST em `/api/demandas` - a mesa so dispara
essas chamadas via HTMX e se atualiza ao vivo pelo SSE (`/eventos/stream`),
sem precisar de rotas HTML proprias para cada acao.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import config, crud
from app.database import obter_sessao
from app.models import Esforco, StatusDemanda

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _contexto_mesa(db: Session) -> dict:
    fila = crud.listar(db, status=StatusDemanda.PRIORIZADA)
    return {
        "em_execucao": crud.listar(db, status=StatusDemanda.EM_EXECUCAO),
        "proxima": fila[0] if fila else None,
        "triadas": crud.listar(db, status=StatusDemanda.TRIADA),
        "falhas": crud.listar_com_falha_de_triagem(db),
        "esforcos": list(Esforco),
        "areas": config.AREAS_DISPONIVEIS,
    }


@router.get("/", response_class=HTMLResponse)
def mesa(request: Request, db: Session = Depends(obter_sessao)) -> HTMLResponse:
    return templates.TemplateResponse(request, "mesa.html", _contexto_mesa(db))


@router.get("/mesa/conteudo", response_class=HTMLResponse)
def mesa_conteudo(request: Request, db: Session = Depends(obter_sessao)) -> HTMLResponse:
    return templates.TemplateResponse(request, "partials/conteudo_mesa.html", _contexto_mesa(db))
