"""Testes da pagina 'sua mesa': renderiza as secoes certas, sem kanban/colunas."""


def test_mesa_carrega_vazia(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "Sua mesa" in resposta.text
    assert "Em execução" in resposta.text
    assert "Próxima da fila" in resposta.text
    assert "Triagens aguardando confirmação" in resposta.text
    assert "Nada em execução agora." in resposta.text
    assert "Fila vazia." in resposta.text


def test_mesa_mostra_demanda_em_execucao(cliente):
    criada = cliente.post("/api/demandas", json={"titulo": "Corrigir bug no checkout"}).json()
    cliente.post(f"/api/demandas/{criada['id']}/mover", json={"status": "em_execucao"})

    resposta = cliente.get("/")
    assert "Corrigir bug no checkout" in resposta.text
    assert "1/2" in resposta.text


def test_mesa_mostra_proxima_da_fila(cliente):
    criada = cliente.post("/api/demandas", json={"titulo": "Ajustar layout do relatorio"}).json()
    cliente.post(f"/api/demandas/{criada['id']}/mover", json={"status": "priorizada"})

    resposta = cliente.get("/")
    assert "Ajustar layout do relatorio" in resposta.text
    assert "Fila vazia." not in resposta.text


def test_mesa_mostra_triagem_aguardando_confirmacao(cliente, claude_mock):
    claude_mock()
    cliente.post("/api/demandas/capturar", json={"texto": "Revisar permissao de usuario"})

    resposta = cliente.get("/")
    assert "Ajustar relatorio mensal" in resposta.text  # titulo sugerido pelo mock
    assert "Revisar permissao de usuario" in resposta.text  # texto original, citado no card
    assert "Nenhuma triagem aguardando confirmação." not in resposta.text


def test_mesa_mostra_falha_de_triagem_com_botao_de_retentativa(cliente, claude_mock):
    claude_mock(excecao=RuntimeError("timeout simulado"))
    cliente.post("/api/demandas/capturar", json={"texto": "Demanda que vai falhar"})

    resposta = cliente.get("/")
    assert "Triagem falhou" in resposta.text
    assert "Demanda que vai falhar" in resposta.text
    assert "Tentar de novo" in resposta.text


def test_mesa_conteudo_parcial_para_atualizacao_via_sse(cliente):
    resposta = cliente.get("/mesa/conteudo")
    assert resposta.status_code == 200
    assert "Em execução" in resposta.text
    assert "<html" not in resposta.text.lower()
