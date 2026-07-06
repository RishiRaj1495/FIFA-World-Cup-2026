"""
Key-free concierge engine.

This module makes the assistant fully functional with ZERO external API
keys. It answers common fan questions by matching intent keywords (in the
fan's selected language) against the same structured venue data the GenAI
path uses, then returns a grounded, deterministic reply.

Why this exists: a prior team submission was disqualified because its core
feature only worked if the evaluator supplied their own API key. To make
sure that can never happen again, this engine is the DEFAULT reply path.
The Anthropic-backed path in `ai_service.py` is strictly an optional
enhancement layered on top of it — if a key is configured, replies become
more natural and can handle open-ended phrasing; if not, every judge,
teammate, or fan still gets a correct, helpful answer with no setup at all.
"""
from app.data.stadium_data import AMENITIES, ACCESSIBILITY_FACILITIES
from app.models.schemas import ChatRequest, ChatResponse, Language
from app.services.crowd_service import get_crowd_status

# Keyword -> intent map. Keys are lowercase substrings matched against the
# fan's message regardless of which language they typed it in, so a fan
# can mix languages or use the local word for something (e.g. "baño").
INTENT_KEYWORDS: dict[str, list[str]] = {
    "restroom": [
        "restroom", "toilet", "bathroom", "washroom",
        "baño", "banheiro", "toilette",
        "शौचालय", "बाथरूम",
        "دورة مياه", "حمام",
        "toiletten",
        "トイレ",
    ],
    "food": [
        "food", "eat", "hungry", "snack", "drink", "concession",
        "comida", "comer", "beber",
        "manger", "boire",
        "खाना", "भोजन",
        "طعام", "أكل",
        "essen", "trinken",
        "食べ物", "食事",
    ],
    "medical": [
        "medical", "first aid", "emergency", "sick", "injury", "hurt",
        "médico", "emergencia", "primeros auxilios",
        "urgence", "premiers secours",
        "चिकित्सा", "आपातकाल",
        "طبي", "طوارئ", "إسعافات",
        "medizinisch", "notfall",
        "医療", "救急",
    ],
    "lost_and_found": [
        "lost", "found", "missing item",
        "perdido", "perdi",
        "perdu", "objet trouvé",
        "खोया", "गुम",
        "مفقود", "ضائع",
        "verloren", "fundbüro",
        "忘れ物", "遺失物",
    ],
    "transport": [
        "transport", "shuttle", "bus", "parking", "taxi", "leave", "way home",
        "transporte", "estacionamiento",
        "transport", "stationnement", "navette",
        "परिवहन", "पार्किंग",
        "نقل", "موقف السيارات", "حافلة",
        "transport", "parkplatz", "shuttlebus",
        "交通", "駐車場", "シャトル",
    ],
    "accessibility": [
        "wheelchair", "accessible", "accessibility", "hearing", "vision",
        "sensory", "disability", "sign language",
        "silla de ruedas", "accesible", "discapacidad",
        "fauteuil roulant", "accessible", "handicap",
        "व्हीलचेयर", "सुगम्यता", "विकलांगता",
        "كرسي متحرك", "إعاقة", "الوصول",
        "rollstuhl", "barrierefrei", "behinderung",
        "車椅子", "アクセシビリティ", "障害",
    ],
    "gate_wait": [
        "gate", "queue", "line", "wait", "entrance", "crowd", "busy", "fastest",
        "puerta", "entrada", "cola", "espera",
        "porte", "entrée", "file", "attente",
        "गेट", "प्रवेश", "कतार", "प्रतीक्षा",
        "بوابة", "دخول", "طابور", "انتظار",
        "tor", "eingang", "warteschlange",
        "ゲート", "入口", "待ち時間",
    ],
}

INTRO_PHRASES: dict[Language, str] = {
    Language.ENGLISH: "Here's what I found:",
    Language.SPANISH: "Esto es lo que encontré:",
    Language.PORTUGUESE: "Aqui está o que encontrei:",
    Language.FRENCH: "Voici ce que j'ai trouvé :",
    Language.HINDI: "मुझे यह जानकारी मिली:",
    Language.ARABIC: "إليك ما وجدته:",
    Language.GERMAN: "Hier ist, was ich gefunden habe:",
    Language.JAPANESE: "見つかった情報はこちらです:",
}

UNKNOWN_PHRASES: dict[Language, str] = {
    Language.ENGLISH: "I don't have information on that. Please ask a steward near any gate, or check the official app.",
    Language.SPANISH: "No tengo información sobre eso. Pregunte a un miembro del personal en cualquier puerta o consulte la app oficial.",
    Language.PORTUGUESE: "Não tenho informações sobre isso. Pergunte a um funcionário em qualquer portão ou consulte o app oficial.",
    Language.FRENCH: "Je n'ai pas cette information. Demandez à un steward près de n'importe quelle porte ou consultez l'app officielle.",
    Language.HINDI: "मेरे पास इसकी जानकारी नहीं है। कृपया किसी भी गेट पर मौजूद स्टाफ से पूछें या आधिकारिक ऐप देखें।",
    Language.ARABIC: "ليس لدي معلومات حول ذلك. يرجى سؤال أحد الموظفين بالقرب من أي بوابة أو مراجعة التطبيق الرسمي.",
    Language.GERMAN: "Dazu habe ich keine Informationen. Fragen Sie einen Mitarbeiter an einem der Tore oder schauen Sie in der offiziellen App nach.",
    Language.JAPANESE: "その情報は持っていません。ゲート付近のスタッフにお尋ねいただくか、公式アプリをご確認ください。",
}


def _detect_intent(message_lower: str) -> str:
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in message_lower for keyword in keywords):
            return intent
    return "unknown"


def _fact_for_intent(intent: str, request: ChatRequest) -> str:
    if intent == "restroom":
        return AMENITIES["restrooms"]
    if intent == "food":
        return AMENITIES["food"]
    if intent == "medical":
        return AMENITIES["medical"]
    if intent == "lost_and_found":
        return AMENITIES["lost_and_found"]
    if intent == "transport":
        return AMENITIES["transport"]
    if intent == "accessibility":
        facilities = ACCESSIBILITY_FACILITIES.get(
            request.accessibility_need.value, ACCESSIBILITY_FACILITIES["none"]
        )
        return " ".join(facilities)
    if intent == "gate_wait":
        status = get_crowd_status()
        return status.recommendation_reason
    return ""


def generate_demo_reply(request: ChatRequest) -> ChatResponse:
    """
    Deterministic, key-free reply. This is the function the app falls
    back to (or uses by default) so the assistant is never non-functional
    just because no AI provider key is configured.
    """
    from app.services.ai_service import _extract_suggested_actions  # local import avoids a circular import

    intent = _detect_intent(request.message.lower())
    intro = INTRO_PHRASES.get(request.language, INTRO_PHRASES[Language.ENGLISH])

    if intent == "unknown":
        reply = UNKNOWN_PHRASES.get(request.language, UNKNOWN_PHRASES[Language.ENGLISH])
        return ChatResponse(reply=reply, language=request.language, suggested_actions=[])

    fact = _fact_for_intent(intent, request)
    reply = f"{intro} {fact}"
    return ChatResponse(
        reply=reply,
        language=request.language,
        suggested_actions=_extract_suggested_actions(reply),
    )
