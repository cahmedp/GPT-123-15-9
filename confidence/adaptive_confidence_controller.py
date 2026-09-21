
"""
Adaptive Confidence Controller

Combines multiple confidence sources:

- Consensus confidence
- Market health modifier
- Knowledge reliability
- Calibration factor

Analysis layer only.
Does not execute decisions.
"""

from dataclasses import dataclass


@dataclass
class AdaptiveConfidenceResult:
    final_confidence: float
    components: dict
    status: str


class AdaptiveConfidenceController:

    def calculate(
        self,
        consensus_confidence,
        market_multiplier,
        knowledge_reliability,
        calibration_factor
    ):

        final = round(
            consensus_confidence
            * market_multiplier
            * knowledge_reliability
            * calibration_factor,
            3
        )

        if final >= 0.75:
            status = "HIGH_CONFIDENCE"

        elif final >= 0.50:
            status = "MEDIUM_CONFIDENCE"

        else:
            status = "LOW_CONFIDENCE"


        return AdaptiveConfidenceResult(
            final_confidence=final,
            components={
                "consensus": consensus_confidence,
                "market": market_multiplier,
                "knowledge": knowledge_reliability,
                "calibration": calibration_factor,
            },
            status=status
        )
