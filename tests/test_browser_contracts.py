import pytest
from pydantic import ValidationError

from usurp.browser import ChallengeType, EscalationRequest, detect_challenge


def test_escalation_request_applies_strict_defaults_and_bounds() -> None:
    request = EscalationRequest(
        target_url="https://www.google.com/search?q=test",
        user_agent="Mozilla/5.0",
        viewport_width=1280,
        viewport_height=900,
    )
    assert request.timeout_seconds == 8.0

    with pytest.raises(ValidationError):
        EscalationRequest(
            target_url="not-a-url",
            user_agent="Mozilla/5.0",
            viewport_width=1280,
            viewport_height=900,
        )


def test_challenge_detector_classifies_known_interstitials() -> None:
    assert detect_challenge("<html>normal result</html>") is ChallengeType.NONE
    assert detect_challenge("Before you continue to Google") is ChallengeType.CONSENT_DIALOG
    assert detect_challenge("/sorry/index?continue=1") is ChallengeType.JS_CHALLENGE
    assert detect_challenge("<div class='g-recaptcha'></div>") is ChallengeType.HARD_CAPTCHA
    assert detect_challenge("/httpservice/retry/enablejs?sei=abc") is ChallengeType.JS_CHALLENGE
