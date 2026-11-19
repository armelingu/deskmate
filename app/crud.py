"""Acesso a dados e regras do ciclo de vida da demanda.

Mantem a coluna de cada status com `posicao` contigua (0..n-1), para suportar
reordenacao das demandas dentro de um mesmo status.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Demanda, StatusDemanda
from app.schemas import DemandaAtualizar, DemandaCriar

LIMITE_EM_EXECUCAO = 2


class LimiteExecucaoExcedido(Exception):
    """Levantada quando mover a demanda estouraria o limite de execucoes simultaneas."""


class TransicaoInvalida(Exception):
    """Levantada quando a mudanca de status pedida nao faz sentido no estado atual."""


def _contar_em_execucao(db: Session, excluir_id: int | None = None) -> int:
    consulta = select(func.count()).select_from(Demanda).where(
        Demanda.status == StatusDemanda.EM_EXECUCAO
    )
    if excluir_id is not None:
        consulta = consulta.where(Demanda.id != excluir_id)
    return db.scalar(consulta) or 0


def _proxima_posicao(db: Session, status: StatusDemanda) -> int:
    maior = db.scalar(select(func.max(Demanda.posicao)).where(Demanda.status == status))
    return 0 if maior is None else maior + 1


def _reindexar_coluna(db: Session, status: StatusDemanda, excluir_id: int | None = None) -> None:
    """Recompacta as posicoes de uma coluna para 0..n-1, na ordem atual."""
    consulta = select(Demanda).where(Demanda.status == status)
    if excluir_id is not None:
        consulta = consulta.where(Demanda.id != excluir_id)
    itens = db.scalars(consulta.order_by(Demanda.posicao, Demanda.id)).all()
    for indice, item in enumerate(itens):
        if item.posicao != indice:
            item.posicao = indice


def listar(
    db: Session,
    status: StatusDemanda | None = None,
    area: str | None = None,
    solicitante: str | None = None,
) -> list[Demanda]:
    consulta = select(Demanda)
    if status is not None:
        consulta = consulta.where(Demanda.status == status)
    if area is not None:
        consulta = consulta.where(Demanda.area == area)
    if solicitante is not None:
        consulta = consulta.where(Demanda.solicitante == solicitante)
    consulta = consulta.order_by(Demanda.status, Demanda.posicao, Demanda.id)
    return list(db.scalars(consulta).all())


def obter(db: Session, demanda_id: int) -> Demanda | None:
    return db.get(Demanda, demanda_id)


def criar(db: Session, dados: DemandaCriar) -> Demanda:
    posicao = _proxima_posicao(db, StatusDemanda.ENTRADA)
    demanda = Demanda(**dados.model_dump(), status=StatusDemanda.ENTRADA, posicao=posicao)
    db.add(demanda)
    db.commit()
    db.refresh(demanda)
    return demanda


def atualizar(db: Session, demanda: Demanda, dados: DemandaAtualizar) -> Demanda:
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(demanda, campo, valor)
    db.commit()
    db.refresh(demanda)
    return demanda


def mover(
    db: Session,
    demanda: Demanda,
    novo_status: StatusDemanda,
    nova_posicao: int | None = None,
) -> Demanda:
    """Move a demanda para `novo_status`, na posicao pedida (ou no fim da coluna).

    Aplica o limite de `LIMITE_EM_EXECUCAO` demandas simultaneas em
    'em_execucao' (regra do SPEC) e mantem `status_anterior` para o
    ciclo Bloqueada -> volta ao estado anterior.
    """
    status_antigo = demanda.status

    if novo_status == StatusDemanda.EM_EXECUCAO and status_antigo != StatusDemanda.EM_EXECUCAO:
        if _contar_em_execucao(db, excluir_id=demanda.id) >= LIMITE_EM_EXECUCAO:
            raise LimiteExecucaoExcedido(
                f"Limite de {LIMITE_EM_EXECUCAO} demandas em execucao atingido. "
                "Finalize ou mova uma demanda em execucao antes de iniciar outra."
            )

    # recompacta a coluna de origem (sem a demanda, que esta de passagem)
    _reindexar_coluna(db, status_antigo, excluir_id=demanda.id)

    tamanho_destino = db.scalar(
        select(func.count())
        .select_from(Demanda)
        .where(Demanda.status == novo_status, Demanda.id != demanda.id)
    ) or 0
    alvo = tamanho_destino if nova_posicao is None else max(0, min(nova_posicao, tamanho_destino))

    for item in db.scalars(
        select(Demanda).where(
            Demanda.status == novo_status,
            Demanda.id != demanda.id,
            Demanda.posicao >= alvo,
        )
    ):
        item.posicao += 1

    if novo_status == StatusDemanda.BLOQUEADA and status_antigo != StatusDemanda.BLOQUEADA:
        demanda.status_anterior = status_antigo
    elif status_antigo == StatusDemanda.BLOQUEADA and novo_status != StatusDemanda.BLOQUEADA:
        demanda.status_anterior = None

    demanda.status = novo_status
    demanda.posicao = alvo

    db.commit()
    db.refresh(demanda)
    return demanda


def bloquear(db: Session, demanda: Demanda) -> Demanda:
    if demanda.status in (StatusDemanda.BLOQUEADA, StatusDemanda.CANCELADA, StatusDemanda.CONCLUIDA):
        raise TransicaoInvalida("Essa demanda nao pode ser bloqueada no estado atual.")
    return mover(db, demanda, StatusDemanda.BLOQUEADA)


def liberar(db: Session, demanda: Demanda) -> Demanda:
    if demanda.status != StatusDemanda.BLOQUEADA or demanda.status_anterior is None:
        raise TransicaoInvalida("Essa demanda nao esta bloqueada.")
    return mover(db, demanda, demanda.status_anterior)


def cancelar(db: Session, demanda: Demanda) -> Demanda:
    if demanda.status == StatusDemanda.CANCELADA:
        raise TransicaoInvalida("Essa demanda ja esta cancelada.")
    return mover(db, demanda, StatusDemanda.CANCELADA)
