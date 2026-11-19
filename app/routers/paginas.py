"""Paginas HTML do painel (Kanban), servidas com Jinja2 + HTMX."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud, schemas
from app.constantes import COLUNAS_LATERAIS, COLUNAS_PRINCIPAIS, ROTULO_STATUS, TODAS_COLUNAS
from app.crud import LIMITE_EM_EXECUCAO
from app.database import obter_sessao
from app.eventos import barramento
from app.models import Demanda, StatusDemanda

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/kanban")


def _agrupar_por_status(db: Session) -> dict[StatusDemanda, list[Demanda]]:
    agrupado: dict[StatusDemanda, list[Demanda]] = {status: [] for status in TODAS_COLUNAS}
    for demanda in crud.listar(db):
        agrupado.setdefault(demanda.status, []).append(demanda)
    return agrupado


@router.get("/kanban", response_class=HTMLResponse)
def pagina_kanban(request: Request, db: Session = Depends(obter_sessao)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "kanban.html",
        {
            "colunas_principais": COLUNAS_PRINCIPAIS,
            "colunas_laterais": COLUNAS_LATERAIS,
            "rotulo_status": ROTULO_STATUS,
            "demandas_por_status": _agrupar_por_status(db),
            "limite_em_execucao": LIMITE_EM_EXECUCAO,
        },
    )


@router.get("/kanban/colunas/{status}", response_class=HTMLResponse)
def pagina_coluna(
    status: StatusDemanda, request: Request, db: Session = Depends(obter_sessao)
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "partials/coluna.html",
        {
            "status": status,
            "rotulo": ROTULO_STATUS[status],
            "demandas": crud.listar(db, status=status),
            "limite_em_execucao": LIMITE_EM_EXECUCAO,
        },
    )


@router.get("/demandas/nova", response_class=HTMLResponse)
def formulario_nova_demanda(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "partials/formulario_demanda.html",
        {"demanda": None, "acao": "/demandas"},
    )


@router.get("/demandas/{demanda_id}/editar", response_class=HTMLResponse)
def formulario_editar_demanda(
    demanda_id: int, request: Request, db: Session = Depends(obter_sessao)
) -> HTMLResponse:
    demanda = crud.obter(db, demanda_id)
    return templates.TemplateResponse(
        request,
        "partials/formulario_demanda.html",
        {"demanda": demanda, "acao": f"/demandas/{demanda_id}"},
    )


def _montar_dados_formulario(
    titulo: str,
    descricao: str,
    solicitante: str,
    area: str,
    impacto: str,
    esforco: str,
    prazo: str,
    delegavel: bool,
    repositorio: str,
) -> dict:
    return {
        "titulo": titulo,
        "descricao": descricao or None,
        "solicitante": solicitante or None,
        "area": area or None,
        "impacto": int(impacto) if impacto else None,
        "esforco": esforco or None,
        "prazo": prazo or None,
        "delegavel": delegavel,
        "repositorio": repositorio or None,
    }


@router.post("/demandas")
async def criar_demanda_form(
    request: Request,
    titulo: str = Form(...),
    descricao: str = Form(""),
    solicitante: str = Form(""),
    area: str = Form(""),
    impacto: str = Form(""),
    esforco: str = Form(""),
    prazo: str = Form(""),
    delegavel: bool = Form(False),
    repositorio: str = Form(""),
    db: Session = Depends(obter_sessao),
):
    dados = schemas.DemandaCriar(
        **_montar_dados_formulario(
            titulo, descricao, solicitante, area, impacto, esforco, prazo, delegavel, repositorio
        )
    )
    demanda = crud.criar(db, dados)
    await barramento.publicar({"colunas": [demanda.status.value]})

    if request.headers.get("hx-request"):
        return HTMLResponse("")
    return RedirectResponse(url="/kanban", status_code=303)


@router.post("/demandas/{demanda_id}")
async def editar_demanda_form(
    demanda_id: int,
    request: Request,
    titulo: str = Form(...),
    descricao: str = Form(""),
    solicitante: str = Form(""),
    area: str = Form(""),
    impacto: str = Form(""),
    esforco: str = Form(""),
    prazo: str = Form(""),
    delegavel: bool = Form(False),
    repositorio: str = Form(""),
    db: Session = Depends(obter_sessao),
):
    demanda = crud.obter(db, demanda_id)
    if demanda is None:
        if request.headers.get("hx-request"):
            return HTMLResponse("Demanda nao encontrada", status_code=404)
        return RedirectResponse(url="/kanban", status_code=303)

    dados = schemas.DemandaAtualizar(
        **_montar_dados_formulario(
            titulo, descricao, solicitante, area, impacto, esforco, prazo, delegavel, repositorio
        )
    )
    demanda = crud.atualizar(db, demanda, dados)
    await barramento.publicar({"colunas": [demanda.status.value]})

    if request.headers.get("hx-request"):
        return HTMLResponse("")
    return RedirectResponse(url="/kanban", status_code=303)
