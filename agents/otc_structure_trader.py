"""
OTC Structure Trader

Analyzes OTC structure only.
No execution.
No order generation.
"""

from dataclasses import dataclass


@dataclass
class TraderOpinion:
    trader: str
    view: str
    confidence: float
    reasons: list


class OTCStructureTrader:

    def analyze(self, snapshot: dict) -> TraderOpinion:
        reasons = []

        if snapshot.get("micro_state") == "EXPANSION":
            reasons.append("Expansion detected")

        if snapshot.get("pattern_state") == "BREAK_RETEST":
            reasons.append("Break retest structure")

        confidence = min(
            0.95,
            0.5 + len(reasons) * 0.15
        )

        view = "FOLLOW_STRUCTURE" if reasons else "WAIT"

        return TraderOpinion(
            trader="STRUCTURE_TRADER",
            view=view,
            confidence=round(confidence, 3),
            reasons=reasons,
        )
