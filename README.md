# Agent de Demandas

Fila de demandas de desenvolvimento com agent de IA para triagem e execução, e painel para acompanhar o agent trabalhando.

Veja `SPEC.md` para escopo, arquitetura e roadmap.

Status: fase 2 (sua mesa + captura) — captura rápida, triagem automática
(Claude Code CLI ou API do Claude) e a tela da sua mesa implementadas.

## Instalação (uma vez)

Na raiz do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
cp .env.example .env  # ajuste se quiser (motor de triagem, areas, etc.)
pip install -e ".[dev]"
```

Com o `TRIAGEM_MOTOR` padrão (`claude_code`), a triagem usa sua assinatura
do Claude via o CLI `claude` — autentique uma vez com `claude setup-token`
(ou `claude login`) se ainda não tiver feito. Para usar a API direto em vez
do CLI, defina `TRIAGEM_MOTOR=api` e preencha `ANTHROPIC_API_KEY` no `.env`.

### Comando `deskmate` em qualquer terminal (sem ativar o venv)

O passo acima já deixa `deskmate` disponível dentro do venv ativado. Para
rodá-lo de qualquer terminal novo, sem ativar nada, crie um atalho em
`~/.local/bin` (precisa estar no seu `PATH`) apontando para este projeto —
rode a partir da raiz do projeto, com o venv já instalado:

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/deskmate <<EOF
#!/bin/sh
exec "$(pwd)/.venv/bin/deskmate" "\$@"
EOF
chmod +x ~/.local/bin/deskmate
```

O caminho do projeto fica gravado no atalho no momento em que você roda o
bloco acima; se mover a pasta do projeto, repita o passo.

## Uso do dia a dia

```bash
deskmate
```

Sobe o servidor e abre a sua mesa (`http://127.0.0.1:8000/`) automaticamente
no navegador, de qualquer pasta, sem precisar ativar o venv. `Ctrl+C` no
terminal encerra. Porta/host alternativos: `DESKMATE_PORT=8001 deskmate`
(ou `DESKMATE_HOST`). O banco (`demandas.db`) e o `.env` sempre ficam na
raiz do projeto, não na pasta de onde você chamou o comando.

## Desenvolvimento

Para rodar com recarregamento automático a cada mudança no código:

```bash
uvicorn app.main:app --reload
```

A API fica em `http://127.0.0.1:8000/api/demandas` e o stream de eventos em
`http://127.0.0.1:8000/eventos/stream`.

## Testes

```bash
pytest
```
