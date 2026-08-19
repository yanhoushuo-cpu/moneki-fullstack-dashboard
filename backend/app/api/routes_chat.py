from __future__ import annotations

from fastapi import APIRouter, Depends

from app.ai.models import ChatRequest, ChatResponse
from app.ai.service import ChatService
from app.api.dependencies import get_chat_service


router = APIRouter(tags=["AI analytics"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return service.answer(request)
