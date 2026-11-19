"""Testes da triagem: execucao e eventos gravados, tokens/custo, e o caminho
de erro (demanda continua em Entrada, erro registrado, dá pra tentar de novo).

Em todos os testes o Claude esta mockado (fixture `claude_mock`) - nenhum
teste chama a API de verdade.
"""

from app.models import Evento, Execucao, StatusExecucao, TipoEvento, TipoExecucao


def _execucoes(cliente, demanda_id):
    with cliente.SessaoTeste() as sessao:
        return (
            sessao.query(Execucao)
            .filter(Execucao.demanda_id == demanda_id)
            .order_by(Execucao.id)
            .all()
        )


def _eventos(cliente, execucao_id):
    with cliente.SessaoTeste() as sessao:
        return sessao.query(Evento).filter(Evento.execucao_id == execucao_id).order_by(Evento.id).all()


def test_triagem_com_sucesso_grava_execucao_com_tokens_e_custo(cliente, claude_mock):
    claude_mock(resposta={"impacto": 3, "esforco": "G"})
    criada = cliente.post(
        "/api/demandas/capturar", json={"texto": "Revisar fluxo de aprovacao de compras"}
    ).json()

    execucoes = _execucoes(cliente, criada["id"])
    assert len(execucoes) == 1
    execucao = execucoes[0]
    assert execucao.tipo == TipoExecucao.TRIAGEM
    assert execucao.status == StatusExecucao.CONCLUIDA
    assert execucao.modelo == "claude-haiku-5-5"
    assert execucao.tokens_entrada == 120
    assert execucao.tokens_saida == 40
    assert execucao.custo_usd > 0
    assert execucao.fim is not None

    eventos = _eventos(cliente, execucao.id)
    tipos = [e.tipo for e in eventos]
    assert tipos == [TipoEvento.MENSAGEM, TipoEvento.TOOL_CALL, TipoEvento.TOOL_RESULT]
    assert eventos[0].payload["texto"] == "Revisar fluxo de aprovacao de compras"


def test_triagem_so_recebe_o_texto_da_demanda_nunca_o_historico_da_fila(cliente, claude_mock):
    cliente.post("/api/demandas", json={"titulo": "Outra demanda qualquer na fila"})
    cliente_falso = claude_mock()
    cliente.post("/api/demandas/capturar", json={"texto": "Ajustar email de boas vindas"}).json()

    _, kwargs = cliente_falso.messages.create.call_args
    assert kwargs["messages"] == [{"role": "user", "content": "Ajustar email de boas vindas"}]
    assert "Outra demanda qualquer na fila" not in str(kwargs["messages"])


def test_triagem_usa_max_tokens_baixo_e_cache_control_no_system(cliente, claude_mock):
    cliente_falso = claude_mock()
    cliente.post("/api/demandas/capturar", json={"texto": "Qualquer coisa"})

    _, kwargs = cliente_falso.messages.create.call_args
    assert kwargs["max_tokens"] <= 400
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["tool_choice"] == {"type": "tool", "name": "estruturar_demanda"}


def test_triagem_com_falha_mantem_demanda_em_entrada_e_registra_erro(cliente, claude_mock):
    claude_mock(excecao=RuntimeError("timeout simulado"))
    criada = cliente.post(
        "/api/demandas/capturar", json={"texto": "Demanda que vai falhar na triagem"}
    ).json()

    atual = cliente.get(f"/api/demandas/{criada['id']}").json()
    assert atual["status"] == "entrada"

    execucoes = _execucoes(cliente, criada["id"])
    assert len(execucoes) == 1
    assert execucoes[0].status == StatusExecucao.ERRO

    eventos = _eventos(cliente, execucoes[0].id)
    assert eventos[-1].tipo == TipoEvento.ERRO
    assert "timeout simulado" in eventos[-1].payload["mensagem"]


def test_retriar_triagem_depois_de_falha_tenta_de_novo(cliente, claude_mock):
    claude_mock(excecao=RuntimeError("timeout simulado"))
    criada = cliente.post(
        "/api/demandas/capturar", json={"texto": "Demanda instavel"}
    ).json()
    assert cliente.get(f"/api/demandas/{criada['id']}").json()["status"] == "entrada"

    claude_mock()  # na proxima tentativa, a API responde direito
    resposta = cliente.post(f"/api/demandas/{criada['id']}/retriar-triagem")
    assert resposta.status_code == 200

    atual = cliente.get(f"/api/demandas/{criada['id']}").json()
    assert atual["status"] == "triada"

    execucoes = _execucoes(cliente, criada["id"])
    assert len(execucoes) == 2
    assert [e.status for e in execucoes] == [StatusExecucao.ERRO, StatusExecucao.CONCLUIDA]


def test_retriar_triagem_de_demanda_que_nao_esta_em_entrada_falha(cliente, claude_mock):
    claude_mock()
    criada = cliente.post("/api/demandas", json={"titulo": "Ja triada manualmente"}).json()
    cliente.post(f"/api/demandas/{criada['id']}/mover", json={"status": "triada"})

    resposta = cliente.post(f"/api/demandas/{criada['id']}/retriar-triagem")
    assert resposta.status_code == 400
