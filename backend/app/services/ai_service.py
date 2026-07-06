"""
GenAI concierge service.

Responsible for turning (user message + context) into a grounded,
language-appropriate reply from Claude. All stadium facts are injected
into the system prompt as structured context rather than left to the
model's general knowledge, so answers stay accurate to *this* venue and
hallucination risk stays low.
"""
import logging

import anthropic
from anthropic import APIError, APIConnectionError, APITimeoutError

from app.core.config import get_settings
from app.data.stadium_data import GATES, AMENITIES, ACCESSIBILITY_FACILITIES, MATCH_CONTEXT
from app.models.schemas import ChatRequest, ChatResponse, Language

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    Language.ENGLISH: "English",
    Language.SPANISH: "Spanish",
    Language.PORTUGUESE: "Portuguese",
    Language.FRENCH: "French",
    Language.HINDI: "Hindi",
    Language.ARABIC: "Arabic",
    Language.GERMAN: "German",
    Language.JAPANESE: "Japanese",
}

def _build_system_prompt(request: ChatRequest) -> str:
    gate_list = "\n".join(
        f"- {g['gate_id']}: {g['name']} | wheelchair accessible: {g['wheelchair_accessible']} "
        f"| amenities: {', '.join(g['amenities'])}"
        for g in GATES
    )
    amenity_list = "\n".join(f"- {name}: {desc}" for name, desc in AMENITIES.items())
    accessibility_list = "\n".join(
        f"- {item}" for item in ACCESSIBILITY_FACILITIES.get(request.accessibility_need.value, [])
    )
    language_name = LANGUAGE_NAMES.get(request.language, "English")

    return f"""You are "Fan Concierge", a helpful, concise on-site assistant for fans at a
{MATCH_CONTEXT['tournament']} match at {MATCH_CONTEXT['venue']}.

Respond ONLY in {language_name}, regardless of what language the fan writes in.
Keep replies short (2-4 sentences), warm, and practical, like a knowledgeable steward.
Only use the venue facts provided below. If asked something outside this data
(e.g. live scores, player news, ticket refunds), say you don't have that
information and suggest asking a steward or checking the official app.
Never invent gate numbers, amenities, or accessibility features not listed here.

VENUE GATES:
{gate_list}

GENERAL AMENITIES:
{amenity_list}

ACCESSIBILITY FACILITIES RELEVANT TO THIS FAN (need: {request.accessibility_need.value}):
{accessibility_list if accessibility_list else '- No specific accessibility need indicated.'}

FAN CONTEXT:
- Current gate (if known): {request.gate or 'unknown'}
- Kickoff is {MATCH_CONTEXT['gates_open_before_kickoff_minutes']} minutes before gates close.
"""


def _extract_suggested_actions(reply_text: str) -> list[str]:
    """
    Lightweight heuristic to surface quick-action chips in the UI
    (e.g. "Show crowd status", "Accessibility info") based on keywords
    in the model's reply. Kept separate from the AI call so it's a pure,
    easily unit-testable function.
    """
    lowered = reply_text.lower()
    actions = []
    if any(word in lowered for word in ["gate", "entrance", "queue", "wait"]):
        actions.append("view_crowd_status")
    if any(word in lowered for word in ["wheelchair", "accessible", "hearing", "sensory", "vision"]):
        actions.append("view_accessibility_info")
    return actions


def get_chat_reply(request: ChatRequest) -> ChatResponse:
    """
    Reply resolution order:

    1. No ANTHROPIC_API_KEY configured -> use the key-free demo engine.
       This is the DEFAULT path and is fully functional on its own, by
       design: nobody evaluating or running this project should ever be
       required to bring their own API key for the core feature to work.
    2. Key configured -> try Claude for a richer, more open-ended reply.
    3. Claude call fails for any reason (network, rate limit, timeout) ->
       fall back to the same key-free demo engine rather than an error
       message, so a transient AI outage never breaks the assistant.
    """
    from app.services.demo_engine import generate_demo_reply  # local import avoids a circular import

    settings = get_settings()

    if not settings.anthropic_api_key:
        return generate_demo_reply(request)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system_prompt = _build_system_prompt(request)

    try:
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.ai_max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": request.message}],
            timeout=settings.ai_request_timeout_seconds,
        )
        reply_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()

        if not reply_text:
            return generate_demo_reply(request)

        return ChatResponse(
            reply=reply_text,
            language=request.language,
            suggested_actions=_extract_suggested_actions(reply_text),
        )

    except (APIConnectionError, APITimeoutError) as exc:
        logger.error("Anthropic API connection issue: %s", exc)
    except APIError as exc:
        logger.error("Anthropic API error: %s", exc)
    except Exception:
        logger.exception("Unexpected error calling Anthropic API")

    return generate_demo_reply(request)
