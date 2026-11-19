# Agent de Demandas

Fila de demandas de desenvolvimento com agent de IA para triagem e execução, e painel para acompanhar o agent trabalhando.

Veja `SPEC.md` para escopo, arquitetura e roadmap.

Status: fase 1 (fila manual) — implementada.

## Rodando localmente

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Acesse `http://127.0.0.1:8000/kanban`.

## Testes

```bash
pytest
```
