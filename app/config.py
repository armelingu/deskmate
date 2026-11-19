"""Configuracao centralizada das variaveis de ambiente usadas na fase 2 (triagem).

Carrega o `.env` uma unica vez aqui. Este modulo e importado bem cedo em
`app.main`, antes de `app.database` ler `DATABASE_URL`, para o `.env` valer
tambem para quem nao exportou as variaveis manualmente no shell.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Qual motor de triagem usar: "claude_code" (padrao - usa a assinatura do
# usuario via `claude` CLI, sem precisar de chave de API) ou "api" (API do
# Claude direto, com tool use - precisa de ANTHROPIC_API_KEY).
TRIAGEM_MOTOR = os.getenv("TRIAGEM_MOTOR", "claude_code")

# --- motor "api" ---
# Menor modelo disponivel por padrao: a triagem so le uma frase e devolve um
# JSON curto, nao precisa de um modelo maior.
CLAUDE_TRIAGEM_MODELO = os.getenv("CLAUDE_TRIAGEM_MODELO", "claude-haiku-5-5")
CLAUDE_TRIAGEM_MAX_TOKENS = int(os.getenv("CLAUDE_TRIAGEM_MAX_TOKENS", "400"))

# Precos em USD por milhao de tokens, para calcular o custo de cada execucao
# de triagem. Configuravel porque o modelo acima tambem e - ajuste no `.env`
# se trocar de modelo e a tabela de precos for diferente desta.
CLAUDE_TRIAGEM_PRECO_ENTRADA_USD_MI = float(
    os.getenv("CLAUDE_TRIAGEM_PRECO_ENTRADA_USD_MI", "1.0")
)
CLAUDE_TRIAGEM_PRECO_SAIDA_USD_MI = float(
    os.getenv("CLAUDE_TRIAGEM_PRECO_SAIDA_USD_MI", "5.0")
)

# --- motor "claude_code" ---
# Caminho do executavel do Claude Code CLI (so o nome usa o PATH do processo).
CLAUDE_CODE_CAMINHO = os.getenv("CLAUDE_CODE_CAMINHO", "claude")
CLAUDE_CODE_MODELO = os.getenv("CLAUDE_CODE_MODELO", "haiku")
CLAUDE_CODE_TIMEOUT_SEGUNDOS = int(os.getenv("CLAUDE_CODE_TIMEOUT_SEGUNDOS", "60"))
