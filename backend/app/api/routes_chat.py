from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.ai.models import ChatRequest, ChatResponse
from app.ai.service import ChatService
from app.ai.streaming import stream_chat_response
from app.api.dependencies import get_chat_service


router = APIRouter(tags=["AI analytics"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return service.answer(request)


@router.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    response = service.answer(request)
    return StreamingResponse(
        stream_chat_response(response),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
