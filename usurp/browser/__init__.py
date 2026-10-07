from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ChallengeType(StrEnum):
    NONE = "none"
    CONSENT_DIALOG = "consent_dialog"
    JS_CHALLENGE = "js_challenge"
    HARD_CAPTCHA = "hard_captcha"


class EscalationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    target_url: HttpUrl
    proxy_uri: HttpUrl | None = None
    user_agent: str = Field(min_length=1, max_length=2048)
    viewport_width: int = Field(gt=0, le=7680)
    viewport_height: int = Field(gt=0, le=7680)
    timeout_seconds: float = Field(default=8.0, gt=0.0, le=60.0)


class EscalationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    rendered_html: str
    final_url: HttpUrl
    execution_duration_ms: float = Field(ge=0.0)
    challenge_type_encountered: ChallengeType
    resolved_successfully: bool


def detect_challenge(raw_html: str) -> ChallengeType:
    body = raw_html.casefold()
    if "recaptcha" in body or "hcaptcha" in body or "captcha" in body:
        return ChallengeType.HARD_CAPTCHA
    if "before you continue to google" in body or "consent.google.com" in body:
        return ChallengeType.CONSENT_DIALOG
    if "/sorry/index" in body or "unusual traffic" in body or "jschl-answer" in body:
        return ChallengeType.JS_CHALLENGE
    return ChallengeType.NONE
