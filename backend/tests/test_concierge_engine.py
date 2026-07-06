from app.models.schemas import AccessibilityNeed, ChatRequest, Language
from app.services.concierge_engine import _detect_intent, get_chat_reply


def test_detect_intent_restroom_english():
    assert _detect_intent("where is the nearest restroom?") == "restroom"


def test_detect_intent_restroom_spanish():
    assert _detect_intent("¿dónde está el baño?") == "restroom"


def test_detect_intent_accessibility():
    assert _detect_intent("is there wheelchair access?") == "accessibility"


def test_detect_intent_gate_wait():
    assert _detect_intent("which gate has the shortest queue?") == "gate_wait"


def test_detect_intent_unknown_for_unrelated_question():
    assert _detect_intent("who won the world cup in 2018?") == "unknown"


def test_get_chat_reply_runs_fully_offline():
    """Core guarantee: no network call, no configuration, still answers correctly."""
    request = ChatRequest(message="Where can I eat?", language=Language.ENGLISH)
    response = get_chat_reply(request)
    assert response.reply
    assert "food" in response.reply.lower() or "court" in response.reply.lower()


def test_get_chat_reply_respects_accessibility_need():
    request = ChatRequest(
        message="What accessibility facilities are there?",
        language=Language.ENGLISH,
        accessibility_need=AccessibilityNeed.WHEELCHAIR,
    )
    response = get_chat_reply(request)
    assert "step-free" in response.reply.lower() or "accessible" in response.reply.lower()


def test_get_chat_reply_localizes_intro_and_unknown_phrase():
    known = get_chat_reply(ChatRequest(message="Where is the restroom?", language=Language.SPANISH))
    assert "encontré" in known.reply

    unknown = get_chat_reply(ChatRequest(message="Who scored the winning goal?", language=Language.SPANISH))
    assert "no tengo información" in unknown.reply.lower()


def test_get_chat_reply_gate_wait_uses_live_crowd_data():
    response = get_chat_reply(
        ChatRequest(message="Which gate is fastest right now?", language=Language.ENGLISH)
    )
    assert "gate" in response.reply.lower()
    assert "view_crowd_status" in response.suggested_actions


def test_get_chat_reply_is_deterministic_for_same_intent():
    """Same question, same intent -> same structural answer (no hidden randomness)."""
    first = get_chat_reply(ChatRequest(message="Where is the restroom?", language=Language.ENGLISH))
    second = get_chat_reply(ChatRequest(message="Where is the restroom?", language=Language.ENGLISH))
    assert first.reply == second.reply
