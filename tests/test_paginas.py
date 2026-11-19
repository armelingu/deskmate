"""Testes das paginas HTML do painel (Kanban e formularios)."""


def test_raiz_redireciona_para_kanban(cliente):
    resposta = cliente.get("/", follow_redirects=False)
    assert resposta.status_code in (307, 308)
    assert resposta.headers["location"] == "/kanban"


def test_pagina_kanban_lista_demanda_criada(cliente):
    cliente.post("/api/demandas", json={"titulo": "Ver no kanban"})
    resposta = cliente.get("/kanban")
    assert resposta.status_code == 200
    assert "Ver no kanban" in resposta.text


def test_coluna_parcial_retorna_html_da_coluna(cliente):
    cliente.post("/api/demandas", json={"titulo": "Coluna parcial"})
    resposta = cliente.get("/kanban/colunas/entrada")
    assert resposta.status_code == 200
    assert "Coluna parcial" in resposta.text


def test_formulario_nova_demanda_eh_exibido(cliente):
    resposta = cliente.get("/demandas/nova")
    assert resposta.status_code == 200
    assert "Nova demanda" in resposta.text


def test_formulario_cria_demanda_e_fecha_modal_via_htmx(cliente):
    resposta = cliente.post(
        "/demandas",
        data={"titulo": "Via formulario"},
        headers={"HX-Request": "true"},
    )
    assert resposta.status_code == 200
    assert resposta.text == ""

    listagem = cliente.get("/api/demandas").json()
    assert any(d["titulo"] == "Via formulario" for d in listagem)


def test_formulario_edicao_atualiza_demanda(cliente):
    criada = cliente.post("/api/demandas", json={"titulo": "Original"}).json()

    resposta = cliente.post(
        f"/demandas/{criada['id']}",
        data={"titulo": "Atualizada", "impacto": "3"},
        headers={"HX-Request": "true"},
    )
    assert resposta.status_code == 200

    atualizada = cliente.get(f"/api/demandas/{criada['id']}").json()
    assert atualizada["titulo"] == "Atualizada"
    assert atualizada["impacto"] == 3
