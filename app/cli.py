"""Comando `deskmate`: sobe o servidor local e abre a sua mesa no navegador.

Uso do dia a dia (depois de `pip install -e ".[dev]"`, que registra o
comando):

    deskmate

Ctrl+C encerra o servidor normalmente.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
import time
import urllib.request
import webbrowser

import uvicorn

from app import config  # noqa: F401  carrega o .env cedo, antes do uvicorn subir


def _aguardar_pronto(url: str, tentativas: int = 50, intervalo: float = 0.2) -> bool:
    """Espera o servidor responder antes de abrir o navegador (sem travar
    caso ele demore: desiste apos `tentativas * intervalo` segundos)."""
    for _ in range(tentativas):
        with contextlib.suppress(Exception):
            if urllib.request.urlopen(url, timeout=1).status == 200:
                return True
        time.sleep(intervalo)
    return False


def _abrir_navegador_quando_pronto(url: str) -> None:
    if _aguardar_pronto(url):
        webbrowser.open(url)
    else:
        print(f"O servidor demorou para responder - abra manualmente: {url}")


def subir() -> None:
    if len(sys.argv) > 1:
        print(__doc__)
        return

    host = os.getenv("DESKMATE_HOST", "127.0.0.1")
    port = int(os.getenv("DESKMATE_PORT", "8000"))
    url = f"http://{host}:{port}/"

    threading.Thread(target=_abrir_navegador_quando_pronto, args=(url,), daemon=True).start()

    print(f"Subindo o deskmate em {url} (Ctrl+C para encerrar)...")
    uvicorn.run("app.main:app", host=host, port=port)


if __name__ == "__main__":
    subir()
