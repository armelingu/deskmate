"""Testes da API REST de demandas (CRUD e ciclo de vida)."""


def test_criar_e_listar_demanda(cliente):
    resposta = cliente.post("/api/demandas", json={"titulo": "Ajustar relatorio"})
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "entrada"
    assert corpo["posicao"] == 0

    resposta = cliente.get("/api/demandas")
    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


def test_criar_demanda_sem_titulo_falha(cliente):
    resposta = cliente.post("/api/demandas", json={"titulo": ""})
    assert resposta.status_code == 422


def test_atualizar_demanda(cliente):
    criada = cliente.post("/api/demandas", json={"titulo": "Demanda X"}).json()
    resposta = cliente.patch(f"/api/demandas/{criada['id']}", json={"impacto": 2, "esforco": "M"})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["impacto"] == 2
    assert corpo["esforco"] == "M"


def test_mover_demanda_para_triada(cliente):
    criada = cliente.post("/api/demandas", json={"titulo": "Demanda Y"}).json()
    resposta = cliente.post(f"/api/demandas/{criada['id']}/mover", json={"status": "triada"})
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "triada"


def test_mover_demanda_inexistente_retorna_404(cliente):
    resposta = cliente.post("/api/demandas/999/mover", json={"status": "triada"})
    assert resposta.status_code == 404


def test_limite_de_duas_demandas_em_execucao(cliente):
    ids = []
    for titulo in ("A", "B", "C"):
        criada = cliente.post("/api/demandas", json={"titulo": titulo}).json()
        ids.append(criada["id"])

    for id_ in ids[:2]:
        resposta = cliente.post(f"/api/demandas/{id_}/mover", json={"status": "em_execucao"})
        assert resposta.status_code == 200

    resposta = cliente.post(f"/api/demandas/{ids[2]}/mover", json={"status": "em_execucao"})
    assert resposta.status_code == 409
    assert "limite" in resposta.json()["detail"].lower()

    # a demanda recusada continua no status anterior (entrada)
    assert cliente.get(f"/api/demandas/{ids[2]}").json()["status"] == "entrada"


def test_liberar_demanda_em_execucao_tambem_respeita_limite(cliente):
    # D estava em execucao e foi bloqueada: status_anterior = em_execucao.
    d = cliente.post("/api/demandas", json={"titulo": "D"}).json()
    cliente.post(f"/api/demandas/{d['id']}/mover", json={"status": "em_execucao"})
    cliente.post(f"/api/demandas/{d['id']}/bloquear")

    # A e B ocupam as duas vagas de execucao enquanto D esta bloqueada.
    for titulo in ("A", "B"):
        criada = cliente.post("/api/demandas", json={"titulo": titulo}).json()
        resposta = cliente.post(f"/api/demandas/{criada['id']}/mover", json={"status": "em_execucao"})
        assert resposta.status_code == 200

    # Liberar D tentaria voltar para em_execucao, estourando o limite.
    resposta = cliente.post(f"/api/demandas/{d['id']}/liberar")
    assert resposta.status_code == 409

    # D continua bloqueada, sem perder o estado anterior.
    atual = cliente.get(f"/api/demandas/{d['id']}").json()
    assert atual["status"] == "bloqueada"
    assert atual["status_anterior"] == "em_execucao"


def test_bloquear_e_liberar_restaura_status_anterior(cliente):
    criada = cliente.post("/api/demandas", json={"titulo": "Demanda Z"}).json()
    cliente.post(f"/api/demandas/{criada['id']}/mover", json={"status": "priorizada"})

    resposta = cliente.post(f"/api/demandas/{criada['id']}/bloquear")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "bloqueada"

    resposta = cliente.post(f"/api/demandas/{criada['id']}/liberar")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "priorizada"


def test_liberar_demanda_nao_bloqueada_falha(cliente):
    criada = cliente.post("/api/demandas", json={"titulo": "Demanda W"}).json()
    resposta = cliente.post(f"/api/demandas/{criada['id']}/liberar")
    assert resposta.status_code == 400


def test_cancelar_demanda(cliente):
    criada = cliente.post("/api/demandas", json={"titulo": "Demanda Cancelada"}).json()
    resposta = cliente.post(f"/api/demandas/{criada['id']}/cancelar")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "cancelada"

    resposta = cliente.post(f"/api/demandas/{criada['id']}/cancelar")
    assert resposta.status_code == 400


def test_reordenar_dentro_da_mesma_coluna(cliente):
    ids = []
    for titulo in ("1", "2", "3"):
        criada = cliente.post("/api/demandas", json={"titulo": titulo}).json()
        ids.append(criada["id"])

    resposta = cliente.post(f"/api/demandas/{ids[2]}/mover", json={"status": "entrada", "posicao": 0})
    assert resposta.status_code == 200

    posicoes = {d["id"]: d["posicao"] for d in cliente.get("/api/demandas").json()}
    assert posicoes[ids[2]] == 0
    assert posicoes[ids[0]] == 1
    assert posicoes[ids[1]] == 2
