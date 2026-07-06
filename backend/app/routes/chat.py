from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.ai_service import get_chat_reply

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Send a fan's message to the multilingual concierge and get a grounded reply."""
    return get_chat_reply(request)
