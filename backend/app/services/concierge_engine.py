"""
Concierge reply engine.

Turns a fan's message into a grounded, localized reply using only the
structured venue data in `app/data/stadium_data.py`. Intent is detected by
matching keywords from the fan's message (in whichever supported language
they wrote it in) against a lookup table, then the matching venue facts are
composed into a natural-language sentence in the fan's selected language.

This runs entirely in-process: no network calls, no third-party services,
no configuration. It is the only reply path the chat endpoint uses, which
keeps the whole assistant runnable and testable with nothing more than
`pip install -r requirements.txt`.
"""

from app.data.stadium_data import ACCESSIBILITY_FACILITIES, AMENITIES
from app.models.schemas import ChatRequest, ChatResponse, Language
from app.services.crowd_service import get_crowd_status

# Keyword -> intent map. Keys are lowercase substrings matched against the
# fan's message regardless of which language they typed it in, so a fan
# can mix languages or use the local word for something (e.g. "baño").
INTENT_KEYWORDS: dict[str, list[str]] = {
    "restroom": [
        "restroom",
        "toilet",
        "bathroom",
        "washroom",
        "baño",
        "banheiro",
        "toilette",
        "शौचालय",
        "बाथरूम",
        "دورة مياه",
        "حمام",
        "toiletten",
        "トイレ",
    ],
    "food": [
        "food",
        "eat",
        "hungry",
        "snack",
        "drink",
        "concession",
        "comida",
        "comer",
        "beber",
        "manger",
        "boire",
        "खाना",
        "भोजन",
        "طعام",
        "أكل",
        "essen",
        "trinken",
        "食べ物",
        "食事",
    ],
    "medical": [
        "medical",
        "first aid",
        "emergency",
        "sick",
        "injury",
        "hurt",
        "médico",
        "emergencia",
        "primeros auxilios",
        "urgence",
        "premiers secours",
        "चिकित्सा",
        "आपातकाल",
        "طبي",
        "طوارئ",
        "إسعافات",
        "medizinisch",
        "notfall",
        "医療",
        "救急",
    ],
    "lost_and_found": [
        "lost",
        "found",
        "missing item",
        "perdido",
        "perdi",
        "perdu",
        "objet trouvé",
        "खोया",
        "गुम",
        "مفقود",
        "ضائع",
        "verloren",
        "fundbüro",
        "忘れ物",
        "遺失物",
    ],
    "transport": [
        "transport",
        "shuttle",
        "bus",
        "parking",
        "taxi",
        "leave",
        "way home",
        "transporte",
        "estacionamiento",
        "transport",
        "stationnement",
        "navette",
        "परिवहन",
        "पार्किंग",
        "نقل",
        "موقف السيارات",
        "حافلة",
        "transport",
        "parkplatz",
        "shuttlebus",
        "交通",
        "駐車場",
        "シャトル",
    ],
    "accessibility": [
        "wheelchair",
        "accessible",
        "accessibility",
        "hearing",
        "vision",
        "sensory",
        "disability",
        "sign language",
        "silla de ruedas",
        "accesible",
        "discapacidad",
        "fauteuil roulant",
        "accessible",
        "handicap",
        "व्हीलचेयर",
        "सुगम्यता",
        "विकलांगता",
        "كرسي متحرك",
        "إعاقة",
        "الوصول",
        "rollstuhl",
        "barrierefrei",
        "behinderung",
        "車椅子",
        "アクセシビリティ",
        "障害",
    ],
    "gate_wait": [
        "gate",
        "queue",
        "line",
        "wait",
        "entrance",
        "crowd",
        "busy",
        "fastest",
        "puerta",
        "entrada",
        "cola",
        "espera",
        "porte",
        "entrée",
        "file",
        "attente",
        "गेट",
        "प्रवेश",
        "कतार",
        "प्रतीक्षा",
        "بوابة",
        "دخول",
        "طابور",
        "انتظار",
        "tor",
        "eingang",
        "warteschlange",
        "ゲート",
        "入口",
        "待ち時間",
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


def _restroom_fact(_: ChatRequest) -> str:
    return AMENITIES["restrooms"]


def _food_fact(_: ChatRequest) -> str:
    return AMENITIES["food"]


def _medical_fact(_: ChatRequest) -> str:
    return AMENITIES["medical"]


def _lost_and_found_fact(_: ChatRequest) -> str:
    return AMENITIES["lost_and_found"]


def _transport_fact(_: ChatRequest) -> str:
    return AMENITIES["transport"]


def _accessibility_fact(request: ChatRequest) -> str:
    facilities = ACCESSIBILITY_FACILITIES.get(
        request.accessibility_need.value, ACCESSIBILITY_FACILITIES["none"]
    )
    return " ".join(facilities)


def _gate_wait_fact(_: ChatRequest) -> str:
    return get_crowd_status().recommendation_reason


# Dispatch table mapping each intent to the function that resolves its
# venue facts. Adding a new intent is then a two-step, additive change:
# add keywords to INTENT_KEYWORDS, add an entry here — no branching logic
# to modify.
INTENT_FACT_RESOLVERS = {
    "restroom": _restroom_fact,
    "food": _food_fact,
    "medical": _medical_fact,
    "lost_and_found": _lost_and_found_fact,
    "transport": _transport_fact,
    "accessibility": _accessibility_fact,
    "gate_wait": _gate_wait_fact,
}


def _fact_for_intent(intent: str, request: ChatRequest) -> str:
    resolver = INTENT_FACT_RESOLVERS.get(intent)
    return resolver(request) if resolver else ""


def _extract_suggested_actions(reply_text: str) -> list[str]:
    """
    Lightweight heuristic to surface quick-action chips in the UI
    (e.g. "Show crowd status", "Accessibility info") based on keywords
    in the composed reply. Kept as a pure function so it's easily
    unit-testable on its own.
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
    Compose a grounded, localized reply for the fan's message.

    This is the only reply path in the application: it runs fully offline,
    requires no configuration, and is deterministic — the same question
    always resolves to the same intent and the same underlying venue facts
    (crowd data updates on its own natural refresh cycle, independent of
    this function).
    """
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
