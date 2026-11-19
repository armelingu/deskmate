# Agent de Demandas

Sistema de gestão de demandas de desenvolvimento com agent de IA e painel de observação.
A fonte de verdade é o `SPEC.md`. Leia-o antes de qualquer tarefa.

## Regras
- Trabalhe APENAS na fase indicada no pedido. Não antecipe fases futuras.
- Se algo não estiver no SPEC.md, pergunte antes de decidir.
- Nunca acesse bases de produção nem faça deploy.
- Commits pequenos, mensagens em português no formato `tipo: descrição` (feat, fix, refactor, docs, test).

## Stack
- Python 3.12, FastAPI, SQLAlchemy, SQLite (Postgres no futuro)
- Testes com pytest
- Front: HTML + HTMX servido pelo FastAPI (sem build de front na fase 1)
- Eventos em tempo real via SSE

## Comandos
- Instalar: `pip install -e ".[dev]"`
- Rodar: `uvicorn app.main:app --reload`
- Testar: `pytest`

## Convenções
- Código e nomes de tabelas/campos em português, sem acentos (ex.: `demanda`, `execucao`, `evento`)
- Type hints em tudo; funções curtas
- Toda rota nova tem pelo menos um teste
