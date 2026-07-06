"""
Pydantic models shared across routes and services.

Keeping these in one module (rather than scattering them inline in routes)
is what lets services and routes evolve independently in a Clean
Architecture layout: routes depend on schemas, services depend on schemas,
neither depends on the other's internals.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Language(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"
    PORTUGUESE = "pt"
    FRENCH = "fr"
    HINDI = "hi"
    ARABIC = "ar"
    GERMAN = "de"
    JAPANESE = "ja"


class AccessibilityNeed(str, Enum):
    NONE = "none"
    WHEELCHAIR = "wheelchair"
    LOW_VISION = "low_vision"
    HEARING_IMPAIRED = "hearing_impaired"
    COGNITIVE_SUPPORT = "cognitive_support"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    language: Language = Language.ENGLISH
    accessibility_need: AccessibilityNeed = AccessibilityNeed.NONE
    gate: str | None = Field(default=None, max_length=20)
    session_id: str | None = Field(default=None, max_length=64)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message cannot be blank")
        return cleaned


class ChatResponse(BaseModel):
    reply: str
    language: Language
    suggested_actions: list[str] = Field(default_factory=list)


class CrowdLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class GateStatus(BaseModel):
    gate_id: str
    name: str
    crowd_level: CrowdLevel
    occupancy_percent: int = Field(ge=0, le=100)
    estimated_wait_minutes: int = Field(ge=0)
    wheelchair_accessible: bool


class CrowdStatusResponse(BaseModel):
    updated_at: str
    gates: list[GateStatus]
    recommended_gate: str
    recommendation_reason: str


class AccessibilityInfoResponse(BaseModel):
    accessibility_need: AccessibilityNeed
    facilities: list[str]
    nearest_gate: str
    notes: str
