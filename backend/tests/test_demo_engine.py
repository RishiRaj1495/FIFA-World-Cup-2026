from app.models.schemas import ChatRequest, Language, AccessibilityNeed
from app.services.demo_engine import generate_demo_reply, _detect_intent


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


def test_generate_demo_reply_never_requires_api_key():
    """The whole point of this module: no key, no network call, still works."""
    request = ChatRequest(message="Where can I eat?", language=Language.ENGLISH)
    response = generate_demo_reply(request)
    assert response.reply
    assert "food" in response.reply.lower() or "court" in response.reply.lower()


def test_generate_demo_reply_respects_accessibility_need():
    request = ChatRequest(
        message="What accessibility facilities are there?",
        language=Language.ENGLISH,
        accessibility_need=AccessibilityNeed.WHEELCHAIR,
    )
    response = generate_demo_reply(request)
    assert "step-free" in response.reply.lower() or "accessible" in response.reply.lower()


def test_generate_demo_reply_localizes_intro_and_unknown_phrase():
    known = generate_demo_reply(ChatRequest(message="Where is the restroom?", language=Language.SPANISH))
    assert "encontré" in known.reply

    unknown = generate_demo_reply(ChatRequest(message="Who scored the winning goal?", language=Language.SPANISH))
    assert "no tengo información" in unknown.reply.lower()


def test_generate_demo_reply_gate_wait_uses_live_crowd_data():
    response = generate_demo_reply(ChatRequest(message="Which gate is fastest right now?", language=Language.ENGLISH))
    assert "gate" in response.reply.lower()
    assert "view_crowd_status" in response.suggested_actions
