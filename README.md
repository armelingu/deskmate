# Agent de Demandas

Fila de demandas de desenvolvimento com agent de IA para triagem e execução, e painel para acompanhar o agent trabalhando.

Veja `SPEC.md` para escopo, arquitetura e roadmap.

Status: fase 1 (fila manual) — API implementada. Ainda sem interface gráfica
(a interface do painel será o escritório virtual, ver fase 5 do roadmap).

## Rodando localmente

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

A API fica em `http://127.0.0.1:8000/api/demandas` e o stream de eventos em
`http://127.0.0.1:8000/eventos/stream`.

## Testes

```bash
pytest
```
