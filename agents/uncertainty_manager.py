
"""
Uncertainty Manager

Adds abstention capability to trader opinions.

States:
- ALIGN
- BLOCK
- ABSTAIN

Purpose:
Avoid forcing weak evidence into a binary decision.
Learning/analysis layer only.
"""

from dataclasses import dataclass


@dataclass
class UncertaintyResult:
    trader: str
    state: str
    confidence: float
    reason: str


class UncertaintyManager:

    def __init__(
        self,
        minimum_confidence=0.60
    ):
        self.minimum_confidence = minimum_confidence


    def evaluate(
        self,
        trader,
        opinion_state,
        confidence,
        data_health=1.0
    ):

        if data_health < 0.70:
            return UncertaintyResult(
                trader,
                "ABSTAIN",
                confidence,
                "Poor data health"
            )

        if confidence < self.minimum_confidence:
            return UncertaintyResult(
                trader,
                "ABSTAIN",
                confidence,
                "Low confidence"
            )

        return UncertaintyResult(
            trader,
            opinion_state,
            confidence,
            "Evidence sufficient"
        )
