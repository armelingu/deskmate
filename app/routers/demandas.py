"""API REST da fila de demandas (fase 1: CRUD + ciclo de vida, sem IA)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi import status as status_http
from sqlalchemy.orm import Session

from app import crud, schemas, triagem
from app.database import obter_sessao
from app.eventos import barramento
from app.models import Demanda, StatusDemanda

router = APIRouter(prefix="/api/demandas", tags=["demandas"])


def _obter_ou_404(db: Session, demanda_id: int) -> Demanda:
    demanda = crud.obter(db, demanda_id)
    if demanda is None:
        raise HTTPException(status_http.HTTP_404_NOT_FOUND, "Demanda nao encontrada")
    return demanda


@router.get("", response_model=list[schemas.DemandaLeitura])
def listar_demandas(
    status: StatusDemanda | None = None,
    area: str | None = None,
    solicitante: str | None = None,
    db: Session = Depends(obter_sessao),
) -> list[Demanda]:
    return crud.listar(db, status=status, area=area, solicitante=solicitante)


@router.post("", response_model=schemas.DemandaLeitura, status_code=status_http.HTTP_201_CREATED)
async def criar_demanda(
    dados: schemas.DemandaCriar, db: Session = Depends(obter_sessao)
) -> Demanda:
    demanda = crud.criar(db, dados)
    await barramento.publicar({"colunas": [demanda.status.value]})
    return demanda


@router.post(
    "/capturar", response_model=schemas.DemandaLeitura, status_code=status_http.HTTP_201_CREATED
)
async def capturar_demanda(
    dados: schemas.DemandaCapturar,
    tarefas: BackgroundTasks,
    db: Session = Depends(obter_sessao),
) -> Demanda:
    """Captura rapida: cria a demanda em Entrada na hora e dispara a triagem
    em segundo plano (nao bloqueia esta resposta)."""
    demanda = crud.capturar(db, dados.texto)
    await barramento.publicar({"colunas": [demanda.status.value]})
    tarefas.add_task(triagem.executar_triagem_em_background, demanda.id, db)
    return demanda


@router.post("/{demanda_id}/retriar-triagem", response_model=schemas.DemandaLeitura)
async def retriar_triagem(
    demanda_id: int,
    tarefas: BackgroundTasks,
    db: Session = Depends(obter_sessao),
) -> Demanda:
    demanda = _obter_ou_404(db, demanda_id)
    if demanda.status != StatusDemanda.ENTRADA:
        raise HTTPException(status_http.HTTP_400_BAD_REQUEST, "Essa demanda nao esta em Entrada.")
    tarefas.add_task(triagem.executar_triagem_em_background, demanda.id, db)
    return demanda


@router.post("/{demanda_id}/confirmar-triagem", response_model=schemas.DemandaLeitura)
async def confirmar_triagem(
    demanda_id: int, dados: schemas.DemandaConfirmarTriagem, db: Session = Depends(obter_sessao)
) -> Demanda:
    demanda = _obter_ou_404(db, demanda_id)
    status_antigo = demanda.status
    try:
        demanda = crud.confirmar_triagem(db, demanda, dados)
    except crud.EstadoInvalidoParaConfirmar as erro:
        raise HTTPException(status_http.HTTP_400_BAD_REQUEST, str(erro)) from erro
    await barramento.publicar(
        {"colunas": sorted({status_antigo.value, demanda.status.value})}
    )
    return demanda


@router.get("/{demanda_id}", response_model=schemas.DemandaLeitura)
def obter_demanda(demanda_id: int, db: Session = Depends(obter_sessao)) -> Demanda:
    return _obter_ou_404(db, demanda_id)


@router.patch("/{demanda_id}", response_model=schemas.DemandaLeitura)
async def atualizar_demanda(
    demanda_id: int, dados: schemas.DemandaAtualizar, db: Session = Depends(obter_sessao)
) -> Demanda:
    demanda = _obter_ou_404(db, demanda_id)
    demanda = crud.atualizar(db, demanda, dados)
    await barramento.publicar({"colunas": [demanda.status.value]})
    return demanda


@router.post("/{demanda_id}/mover", response_model=schemas.DemandaLeitura)
async def mover_demanda(
    demanda_id: int, dados: schemas.DemandaMover, db: Session = Depends(obter_sessao)
) -> Demanda:
    demanda = _obter_ou_404(db, demanda_id)
    status_antigo = demanda.status
    try:
        demanda = crud.mover(db, demanda, dados.status, dados.posicao)
    except crud.LimiteExecucaoExcedido as erro:
        raise HTTPException(status_http.HTTP_409_CONFLICT, str(erro)) from erro
    await barramento.publicar(
        {"colunas": sorted({status_antigo.value, demanda.status.value})}
    )
    return demanda


@router.post("/{demanda_id}/bloquear", response_model=schemas.DemandaLeitura)
async def bloquear_demanda(demanda_id: int, db: Session = Depends(obter_sessao)) -> Demanda:
    demanda = _obter_ou_404(db, demanda_id)
    status_antigo = demanda.status
    try:
        demanda = crud.bloquear(db, demanda)
    except crud.TransicaoInvalida as erro:
        raise HTTPException(status_http.HTTP_400_BAD_REQUEST, str(erro)) from erro
    await barramento.publicar(
        {"colunas": sorted({status_antigo.value, demanda.status.value})}
    )
    return demanda


@router.post("/{demanda_id}/liberar", response_model=schemas.DemandaLeitura)
async def liberar_demanda(demanda_id: int, db: Session = Depends(obter_sessao)) -> Demanda:
    demanda = _obter_ou_404(db, demanda_id)
    status_antigo = demanda.status
    try:
        demanda = crud.liberar(db, demanda)
    except crud.TransicaoInvalida as erro:
        raise HTTPException(status_http.HTTP_400_BAD_REQUEST, str(erro)) from erro
    except crud.LimiteExecucaoExcedido as erro:
        raise HTTPException(status_http.HTTP_409_CONFLICT, str(erro)) from erro
    await barramento.publicar(
        {"colunas": sorted({status_antigo.value, demanda.status.value})}
    )
    return demanda


@router.post("/{demanda_id}/cancelar", response_model=schemas.DemandaLeitura)
async def cancelar_demanda(demanda_id: int, db: Session = Depends(obter_sessao)) -> Demanda:
    demanda = _obter_ou_404(db, demanda_id)
    status_antigo = demanda.status
    try:
        demanda = crud.cancelar(db, demanda)
    except crud.TransicaoInvalida as erro:
        raise HTTPException(status_http.HTTP_400_BAD_REQUEST, str(erro)) from erro
    await barramento.publicar(
        {"colunas": sorted({status_antigo.value, demanda.status.value})}
    )
    return demanda
