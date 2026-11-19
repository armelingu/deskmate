# Agent de Demandas

Fila de demandas de desenvolvimento com agent de IA para triagem e execução, e painel para acompanhar o agent trabalhando.

Veja `SPEC.md` para escopo, arquitetura e roadmap.

Status: fase 2 (sua mesa + captura) — captura rápida, triagem automática via
API do Claude e a tela da sua mesa implementadas.

## Rodando localmente

```bash
cp .env.example .env  # preencha ANTHROPIC_API_KEY
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

A sua mesa fica em `http://127.0.0.1:8000/`, a API em
`http://127.0.0.1:8000/api/demandas` e o stream de eventos em
`http://127.0.0.1:8000/eventos/stream`.

## Testes

```bash
pytest
```
