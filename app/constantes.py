"""Constantes compartilhadas entre rotas e templates do painel."""

from app.models import StatusDemanda

COLUNAS_PRINCIPAIS: list[StatusDemanda] = [
    StatusDemanda.ENTRADA,
    StatusDemanda.TRIADA,
    StatusDemanda.PRIORIZADA,
    StatusDemanda.EM_EXECUCAO,
    StatusDemanda.EM_REVISAO,
    StatusDemanda.CONCLUIDA,
]

COLUNAS_LATERAIS: list[StatusDemanda] = [
    StatusDemanda.BLOQUEADA,
    StatusDemanda.CANCELADA,
]

TODAS_COLUNAS: list[StatusDemanda] = COLUNAS_PRINCIPAIS + COLUNAS_LATERAIS

ROTULO_STATUS: dict[StatusDemanda, str] = {
    StatusDemanda.ENTRADA: "Entrada",
    StatusDemanda.TRIADA: "Triada",
    StatusDemanda.PRIORIZADA: "Priorizada",
    StatusDemanda.EM_EXECUCAO: "Em execução",
    StatusDemanda.EM_REVISAO: "Em revisão",
    StatusDemanda.CONCLUIDA: "Concluída",
    StatusDemanda.BLOQUEADA: "Bloqueada",
    StatusDemanda.CANCELADA: "Cancelada",
}
