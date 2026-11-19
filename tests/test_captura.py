"""Testes da captura rapida: texto livre -> demanda em Entrada na hora,
com a triagem (Claude sempre mockada) rodando em seguida."""


def test_capturar_cria_demanda_em_entrada_com_texto_original(cliente, claude_mock):
    claude_mock()
    resposta = cliente.post(
        "/api/demandas/capturar", json={"texto": "Corrigir calculo errado no relatorio mensal"}
    )
    assert resposta.status_code == 201
    corpo = resposta.json()
    # a resposta reflete o estado logo apos a captura, antes da triagem
    # (que roda em segundo plano) atualizar a demanda.
    assert corpo["status"] == "entrada"
    assert corpo["texto_original"] == "Corrigir calculo errado no relatorio mensal"
    assert corpo["titulo"] == "Corrigir calculo errado no relatorio mensal"


def test_capturar_sem_texto_falha(cliente):
    resposta = cliente.post("/api/demandas/capturar", json={"texto": ""})
    assert resposta.status_code == 422


def test_titulo_provisorio_trunca_texto_longo(cliente, claude_mock):
    claude_mock()
    texto = "x" * 150
    resposta = cliente.post("/api/demandas/capturar", json={"texto": texto})
    corpo = resposta.json()
    assert len(corpo["titulo"]) <= 80
    assert corpo["titulo"].endswith("…")
    assert corpo["texto_original"] == texto


def test_capturar_dispara_triagem_que_estrutura_a_demanda(cliente, claude_mock):
    claude_mock()
    criada = cliente.post(
        "/api/demandas/capturar", json={"texto": "Corrigir calculo errado no relatorio mensal"}
    ).json()

    atual = cliente.get(f"/api/demandas/{criada['id']}").json()
    assert atual["status"] == "triada"
    assert atual["titulo"] == "Ajustar relatorio mensal"
    assert atual["area"] == "Financeiro"
    assert atual["impacto"] == 2
    assert atual["esforco"] == "M"
    # o texto original nunca e sobrescrito pela triagem.
    assert atual["texto_original"] == "Corrigir calculo errado no relatorio mensal"
