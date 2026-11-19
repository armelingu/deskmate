"""Testes do motor de triagem via Claude Code CLI (TRIAGEM_MOTOR=claude_code,
o padrao). A chamada ao processo e sempre mockada (fixture `claude_code_mock`)
- nenhum teste executa o CLI de verdade.
"""

import json
import os
import subprocess

from app.models import Evento, Execucao, StatusExecucao, TipoEvento, TipoExecucao
from app.triagem.motor_claude_code import _TRAVA, _montar_comando


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


def test_triagem_via_claude_code_com_sucesso(cliente, claude_code_mock):
    claude_code_mock(resposta={"impacto": 3, "esforco": "G"})
    criada = cliente.post(
        "/api/demandas/capturar", json={"texto": "Revisar fluxo de aprovacao de compras"}
    ).json()

    atual = cliente.get(f"/api/demandas/{criada['id']}").json()
    assert atual["status"] == "triada"
    assert atual["impacto"] == 3
    assert atual["esforco"] == "G"

    execucoes = _execucoes(cliente, criada["id"])
    assert len(execucoes) == 1
    execucao = execucoes[0]
    assert execucao.tipo == TipoExecucao.TRIAGEM
    assert execucao.status == StatusExecucao.CONCLUIDA
    assert execucao.modelo == "haiku"
    assert execucao.tokens_entrada == 300
    assert execucao.tokens_saida == 60
    assert execucao.custo_usd == 0.00012

    eventos = _eventos(cliente, execucao.id)
    assert [e.tipo for e in eventos] == [TipoEvento.MENSAGEM, TipoEvento.TOOL_CALL, TipoEvento.TOOL_RESULT]
    assert eventos[0].payload["motor"] == "claude_code"


def test_comando_do_claude_code_nao_tem_ferramentas_e_roda_restrito():
    comando = _montar_comando("texto qualquer")
    assert comando[0:2] == ["claude", "--print"]
    assert "--restricted" in comando
    assert "--strict-mcp-config" in comando
    assert "--no-session-persistence" in comando

    indice_tools = comando.index("--tools")
    assert comando[indice_tools + 1] == ""  # nenhuma ferramenta liberada

    indice_modelo = comando.index("--model")
    assert comando[indice_modelo + 1] == "haiku"

    indice_schema = comando.index("--json-schema")
    assert '"titulo"' in comando[indice_schema + 1]

    # o texto da demanda vai como ultimo argumento (o prompt)
    assert comando[-1] == "texto qualquer"


def test_triagem_via_claude_code_roda_num_diretorio_temporario_vazio(cliente, monkeypatch):
    # espiona o diretorio NO MOMENTO da chamada (o TemporaryDirectory e
    # apagado assim que `triar()` termina, entao so da pra conferir aqui).
    chamadas = []

    def _espiar(comando, diretorio):
        chamadas.append((os.path.isdir(diretorio), os.listdir(diretorio)))
        padrao = {
            "titulo": "Ajustar relatorio mensal",
            "descricao": "Corrigir o calculo de totais no relatorio mensal.",
            "area": "financeiro",
            "impacto": 2,
            "esforco": "M",
        }
        envelope = {"is_error": False, "result": json.dumps(padrao), "total_cost_usd": 0, "usage": {}}
        return subprocess.CompletedProcess(
            args=comando, returncode=0, stdout=json.dumps(envelope), stderr=""
        )

    monkeypatch.setattr("app.config.TRIAGEM_MOTOR", "claude_code")
    monkeypatch.setattr("app.triagem.motor_claude_code._executar_processo", _espiar)

    cliente.post("/api/demandas/capturar", json={"texto": "Qualquer coisa"})

    assert len(chamadas) == 1
    existia, conteudo = chamadas[0]
    assert existia is True
    assert conteudo == []  # vazio: nada de CLAUDE.md, nenhum repositorio


def test_triagem_via_claude_code_sem_tokens_ou_custo_na_saida_fica_nulo(cliente, claude_code_mock):
    claude_code_mock(envelope_extra={"usage": {}, "total_cost_usd": None})
    criada = cliente.post("/api/demandas/capturar", json={"texto": "Demanda qualquer"}).json()

    execucao = _execucoes(cliente, criada["id"])[0]
    assert execucao.status == StatusExecucao.CONCLUIDA
    assert execucao.tokens_entrada is None
    assert execucao.tokens_saida is None
    assert execucao.custo_usd is None


def test_triagem_via_claude_code_com_is_error_falha(cliente, claude_code_mock):
    claude_code_mock(is_error=True)
    criada = cliente.post("/api/demandas/capturar", json={"texto": "Vai falhar"}).json()

    assert cliente.get(f"/api/demandas/{criada['id']}").json()["status"] == "entrada"
    execucao = _execucoes(cliente, criada["id"])[0]
    assert execucao.status == StatusExecucao.ERRO


def test_triagem_via_claude_code_com_processo_falhando_falha(cliente, claude_code_mock):
    claude_code_mock(returncode=1, stderr="nao foi possivel conectar")
    criada = cliente.post("/api/demandas/capturar", json={"texto": "Vai falhar"}).json()

    assert cliente.get(f"/api/demandas/{criada['id']}").json()["status"] == "entrada"
    execucao = _execucoes(cliente, criada["id"])[0]
    assert execucao.status == StatusExecucao.ERRO
    eventos = _eventos(cliente, execucao.id)
    assert "nao foi possivel conectar" in eventos[-1].payload["mensagem"]


def test_triagem_via_claude_code_com_timeout_falha(cliente, claude_code_mock):
    claude_code_mock(excecao=subprocess.TimeoutExpired(cmd="claude", timeout=60))
    criada = cliente.post("/api/demandas/capturar", json={"texto": "Vai dar timeout"}).json()

    assert cliente.get(f"/api/demandas/{criada['id']}").json()["status"] == "entrada"
    execucao = _execucoes(cliente, criada["id"])[0]
    assert execucao.status == StatusExecucao.ERRO


def test_triagem_via_claude_code_com_json_fora_do_schema_falha(cliente, claude_code_mock):
    # devolve um JSON valido, mas sem os campos que o schema exige
    claude_code_mock(envelope_extra={"result": '{"titulo": "so isso"}'})
    criada = cliente.post("/api/demandas/capturar", json={"texto": "JSON incompleto"}).json()

    assert cliente.get(f"/api/demandas/{criada['id']}").json()["status"] == "entrada"
    execucao = _execucoes(cliente, criada["id"])[0]
    assert execucao.status == StatusExecucao.ERRO
    eventos = _eventos(cliente, execucao.id)
    assert "faltando" in eventos[-1].payload["mensagem"].lower()


def test_triagem_via_claude_code_so_uma_vez_por_vez():
    """A trava e um threading.Lock de verdade, segurado durante `triar()`."""
    assert not _TRAVA.locked()


def test_retriar_apos_falha_do_claude_code_funciona(cliente, claude_code_mock):
    claude_code_mock(is_error=True)
    criada = cliente.post("/api/demandas/capturar", json={"texto": "Demanda instavel"}).json()
    assert cliente.get(f"/api/demandas/{criada['id']}").json()["status"] == "entrada"

    claude_code_mock()  # proxima tentativa funciona
    resposta = cliente.post(f"/api/demandas/{criada['id']}/retriar-triagem")
    assert resposta.status_code == 200
    assert cliente.get(f"/api/demandas/{criada['id']}").json()["status"] == "triada"
