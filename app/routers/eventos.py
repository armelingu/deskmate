"""Endpoint SSE que alimenta o painel com as colunas do Kanban que mudaram."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.eventos import barramento

router = APIRouter()


@router.get("/eventos/stream")
async def transmitir_eventos() -> StreamingResponse:
    return StreamingResponse(barramento.assinar(), media_type="text/event-stream")
