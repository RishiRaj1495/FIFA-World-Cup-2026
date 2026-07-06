from types import SimpleNamespace
from unittest.mock import patch

from app.models.schemas import ChatRequest, Language, AccessibilityNeed
from app.services.ai_service import get_chat_reply, _extract_suggested_actions, _build_system_prompt


def test_extract_suggested_actions_detects_gate_keywords():
    actions = _extract_suggested_actions("Gate B has the shortest queue right now.")
    assert "view_crowd_status" in actions


def test_extract_suggested_actions_detects_accessibility_keywords():
    actions = _extract_suggested_actions("Gate D is wheelchair accessible with a sensory room.")
    assert "view_accessibility_info" in actions


def test_extract_suggested_actions_empty_when_no_keywords():
    assert _extract_suggested_actions("The match kicks off at 7pm.") == []


def test_system_prompt_forces_requested_language():
    request = ChatRequest(message="Where is the restroom?", language=Language.SPANISH)
    prompt = _build_system_prompt(request)
    assert "Spanish" in prompt


def test_system_prompt_includes_accessibility_facilities():
    request = ChatRequest(
        message="Help",
        language=Language.ENGLISH,
        accessibility_need=AccessibilityNeed.WHEELCHAIR,
    )
    prompt = _build_system_prompt(request)
    assert "wheelchair" in prompt.lower()


def test_get_chat_reply_uses_demo_engine_when_no_api_key():
    """
    Core regression test: the assistant MUST fully answer questions with
    zero API key configured. A prior project was disqualified because its
    only reply path required an evaluator-supplied key; this guards
    against that ever happening again.
    """
    with patch("app.services.ai_service.get_settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(
            anthropic_api_key="",
            anthropic_model="claude-sonnet-4-6",
            ai_max_tokens=600,
            ai_request_timeout_seconds=20,
        )
        request = ChatRequest(message="Where is the restroom?", language=Language.ENGLISH)
        response = get_chat_reply(request)
        assert response.reply
        assert response.language == Language.ENGLISH
        # Should contain real venue data, not a generic "service unavailable" message
        assert "restroom" in response.reply.lower() or "accessible" in response.reply.lower()


def test_get_chat_reply_falls_back_to_demo_engine_on_api_failure():
    """If Claude errors out mid-tournament, fans still get a correct answer."""
    with patch("app.services.ai_service.get_settings") as mock_settings, \
         patch("app.services.ai_service.anthropic.Anthropic") as mock_client_cls:
        mock_settings.return_value = SimpleNamespace(
            anthropic_api_key="fake-key",
            anthropic_model="claude-sonnet-4-6",
            ai_max_tokens=600,
            ai_request_timeout_seconds=20,
        )
        mock_client = mock_client_cls.return_value
        mock_client.messages.create.side_effect = RuntimeError("simulated outage")

        request = ChatRequest(message="Where is the restroom?", language=Language.ENGLISH)
        response = get_chat_reply(request)
        assert response.reply
        assert "restroom" in response.reply.lower()


def test_get_chat_reply_uses_anthropic_client_when_key_present():
    fake_text_block = SimpleNamespace(type="text", text="Gate B is quietest right now.")
    fake_response = SimpleNamespace(content=[fake_text_block])

    with patch("app.services.ai_service.get_settings") as mock_settings, \
         patch("app.services.ai_service.anthropic.Anthropic") as mock_client_cls:
        mock_settings.return_value = SimpleNamespace(
            anthropic_api_key="fake-key",
            anthropic_model="claude-sonnet-4-6",
            ai_max_tokens=600,
            ai_request_timeout_seconds=20,
        )
        mock_client = mock_client_cls.return_value
        mock_client.messages.create.return_value = fake_response

        request = ChatRequest(message="Which gate is fastest?", language=Language.ENGLISH)
        response = get_chat_reply(request)

        assert "Gate B" in response.reply
        assert "view_crowd_status" in response.suggested_actions
