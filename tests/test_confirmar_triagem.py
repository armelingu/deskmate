"""Testes da confirmacao da triagem: aceitar como veio ou ajustar, mover
para Priorizada, e gravar o evento de aprovacao (SPEC: toda aprovacao vira
um evento)."""

from app.models import Evento, Execucao, TipoEvento


def _execucao_de_triagem(cliente, demanda_id):
    with cliente.SessaoTeste() as sessao:
        return (
            sessao.query(Execucao)
            .filter(Execucao.demanda_id == demanda_id)
            .order_by(Execucao.id.desc())
            .first()
        )


def _eventos(cliente, execucao_id):
    with cliente.SessaoTeste() as sessao:
        return sessao.query(Evento).filter(Evento.execucao_id == execucao_id).all()


def test_confirmar_triagem_sem_ajustes_move_para_priorizada(cliente, claude_mock):
    claude_mock()
    criada = cliente.post(
        "/api/demandas/capturar", json={"texto": "Ajustar email de boas vindas"}
    ).json()
    assert criada is not None

    triada = cliente.get(f"/api/demandas/{criada['id']}").json()
    assert triada["status"] == "triada"

    resposta = cliente.post(
        f"/api/demandas/{triada['id']}/confirmar-triagem",
        json={
            "titulo": triada["titulo"],
            "descricao": triada["descricao"],
            "area": triada["area"],
            "impacto": triada["impacto"],
            "esforco": triada["esforco"],
        },
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "priorizada"
    assert corpo["titulo"] == triada["titulo"]

    execucao = _execucao_de_triagem(cliente, criada["id"])
    eventos = _eventos(cliente, execucao.id)
    assert any(e.tipo == TipoEvento.APROVACAO for e in eventos)


def test_confirmar_triagem_com_ajustes_sobrescreve_sugestao(cliente, claude_mock):
    claude_mock()
    criada = cliente.post(
        "/api/demandas/capturar", json={"texto": "Ajustar email de boas vindas"}
    ).json()

    resposta = cliente.post(
        f"/api/demandas/{criada['id']}/confirmar-triagem",
        json={
            "titulo": "Titulo ajustado por mim",
            "impacto": 1,
            "esforco": "P",
            "delegavel": True,
        },
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "priorizada"
    assert corpo["titulo"] == "Titulo ajustado por mim"
    assert corpo["impacto"] == 1
    assert corpo["esforco"] == "P"
    assert corpo["delegavel"] is True


def test_confirmar_triagem_de_demanda_nao_triada_falha(cliente):
    criada = cliente.post("/api/demandas", json={"titulo": "Ainda em entrada"}).json()

    resposta = cliente.post(
        f"/api/demandas/{criada['id']}/confirmar-triagem",
        json={"titulo": "Qualquer coisa"},
    )
    assert resposta.status_code == 400
