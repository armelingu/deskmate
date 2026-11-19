"""Fixtures compartilhadas dos testes: banco SQLite em memoria por teste, e os
dois motores de triagem sempre mockados (nenhum teste chama a API ou executa
o Claude Code CLI de verdade)."""

from __future__ import annotations

import json
import os
import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ANTHROPIC_API_KEY", "chave-de-teste-nao-usada")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, obter_sessao
from app.main import app


@pytest.fixture()
def cliente():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessaoTeste = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def sobrescrever_sessao():
        db = SessaoTeste()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[obter_sessao] = sobrescrever_sessao
    with TestClient(app) as cliente_teste:
        # exposto para os testes que precisam olhar execucao/evento direto no
        # banco (a API nao tem endpoint de leitura para essas entidades ainda).
        cliente_teste.SessaoTeste = SessaoTeste
        yield cliente_teste
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def bloquear_chamada_real_de_triagem(monkeypatch):
    """Rede de seguranca: qualquer teste que dispare a triagem sem configurar
    `claude_mock` (motor api) ou `claude_code_mock` (motor claude_code)
    primeiro recebe um erro claro (vira uma execucao com status "erro"),
    nunca uma chamada real a API nem a execucao do CLI de verdade."""

    def _proibido_api():
        raise RuntimeError(
            "Teste tentou obter o cliente Claude real - configure a fixture "
            "`claude_mock` antes de disparar a triagem (motor api)."
        )

    def _proibido_cli(*args, **kwargs):
        raise RuntimeError(
            "Teste tentou executar o Claude Code CLI de verdade - configure a "
            "fixture `claude_code_mock` antes de disparar a triagem (motor claude_code)."
        )

    monkeypatch.setattr("app.triagem.motor_api.obter_cliente", _proibido_api)
    monkeypatch.setattr("app.triagem.motor_claude_code._executar_processo", _proibido_cli)


@pytest.fixture()
def claude_mock(monkeypatch):
    """Ativa o motor "api" e configura `obter_cliente` para devolver um
    cliente Anthropic falso.

    Uso:
        claude_mock()                       # sucesso, com valores padrao
        claude_mock(resposta={...})         # sucesso, com valores customizados
        claude_mock(excecao=RuntimeError()) # simula falha na chamada a API
    """

    def _configurar(resposta: dict | None = None, excecao: Exception | None = None):
        monkeypatch.setattr("app.config.TRIAGEM_MOTOR", "api")

        cliente_falso = MagicMock()
        if excecao is not None:
            cliente_falso.messages.create.side_effect = excecao
        else:
            padrao = {
                "titulo": "Ajustar relatorio mensal",
                "descricao": "Corrigir o calculo de totais no relatorio mensal.",
                "area": "financeiro",
                "impacto": 2,
                "esforco": "M",
            }
            padrao.update(resposta or {})
            bloco = SimpleNamespace(type="tool_use", name="estruturar_demanda", input=padrao)
            cliente_falso.messages.create.return_value = SimpleNamespace(
                content=[bloco],
                usage=SimpleNamespace(input_tokens=120, output_tokens=40),
            )
        monkeypatch.setattr("app.triagem.motor_api.obter_cliente", lambda: cliente_falso)
        return cliente_falso

    return _configurar


@pytest.fixture()
def claude_code_mock(monkeypatch):
    """Ativa o motor "claude_code" e configura `_executar_processo` (o unico
    ponto que chamaria o CLI de verdade) para devolver uma saida falsa.

    Uso:
        claude_code_mock()                                  # sucesso
        claude_code_mock(resposta={...})                     # sucesso customizado
        claude_code_mock(envelope_extra={"usage": {}})       # sem tokens/custo informados
        claude_code_mock(is_error=True)                      # CLI devolveu erro
        claude_code_mock(returncode=1, stderr="boom")         # processo falhou
        claude_code_mock(excecao=subprocess.TimeoutExpired(cmd="claude", timeout=60))
    """

    def _configurar(
        resposta: dict | None = None,
        envelope_extra: dict | None = None,
        is_error: bool = False,
        returncode: int = 0,
        stderr: str = "",
        excecao: Exception | None = None,
    ):
        monkeypatch.setattr("app.config.TRIAGEM_MOTOR", "claude_code")

        if excecao is not None:
            mock_executar = MagicMock(side_effect=excecao)
            monkeypatch.setattr("app.triagem.motor_claude_code._executar_processo", mock_executar)
            return mock_executar

        padrao = {
            "titulo": "Ajustar relatorio mensal",
            "descricao": "Corrigir o calculo de totais no relatorio mensal.",
            "area": "financeiro",
            "impacto": 2,
            "esforco": "M",
        }
        padrao.update(resposta or {})

        envelope = {
            "type": "result",
            "subtype": "error" if is_error else "success",
            "is_error": is_error,
            "result": "algo deu errado" if is_error else json.dumps(padrao),
            "total_cost_usd": 0.00012,
            "usage": {"input_tokens": 300, "output_tokens": 60},
        }
        if envelope_extra:
            envelope.update(envelope_extra)

        processo_falso = subprocess.CompletedProcess(
            args=["claude"], returncode=returncode, stdout=json.dumps(envelope), stderr=stderr
        )
        mock_executar = MagicMock(return_value=processo_falso)
        mock_executar.envelope = envelope
        monkeypatch.setattr("app.triagem.motor_claude_code._executar_processo", mock_executar)
        return mock_executar

    return _configurar
