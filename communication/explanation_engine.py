from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ExplanationPayload:
    title: str
    action: str
    confidence: float
    uncertainty: float
    summary: str
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "action": self.action,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "summary": self.summary,
            "reasons": list(self.reasons),
        }


class ExplanationEngine:
    """
    Converts system decisions into human-readable English explanations.

    No decision making exists here.
    This layer only explains existing decisions.
    """

    def explain(
        self,
        *,
        action: str,
        confidence: float,
        uncertainty: float,
        reasons: Iterable[str] = (),
    ) -> ExplanationPayload:

        clean_reasons = tuple(
            str(reason)
            for reason in reasons
        )

        if action == "BUY":
            title = "Bullish Opportunity Detected"

        elif action == "SELL":
            title = "Bearish Opportunity Detected"

        else:
            title = "Market Observation - Waiting"


        summary = (
            f"The system generated a {action} advisory signal "
            f"with confidence {confidence:.2f}. "
            f"Current uncertainty level is {uncertainty:.2f}."
        )

        return ExplanationPayload(
            title=title,
            action=action,
            confidence=float(confidence),
            uncertainty=float(uncertainty),
            summary=summary,
            reasons=clean_reasons,
        )