
"""
Dynamic Confidence Threshold Manager

Adjusts required confidence based on market state.

Purpose:
- Avoid fixed thresholds
- Increase caution in weak markets
- Keep flexibility in normal conditions

Analysis layer only.
"""

from dataclasses import dataclass


@dataclass
class ThresholdResult:
    market_mode: str
    required_confidence: float
    decision: str
    reason: str


class ConfidenceThresholdManager:

    def get_threshold(
        self,
        market_mode
    ):

        thresholds = {
            "NORMAL": 0.70,
            "CAUTIOUS": 0.80,
            "DEFENSIVE": 0.90,
        }

        return thresholds.get(
            market_mode,
            0.85
        )


    def evaluate(
        self,
        confidence,
        market_mode
    ):

        required = self.get_threshold(
            market_mode
        )

        if confidence >= required:
            return ThresholdResult(
                market_mode,
                required,
                "ALLOW",
                "Confidence above dynamic threshold"
            )

        return ThresholdResult(
            market_mode,
            required,
            "BLOCK",
            "Confidence below dynamic threshold"
        )
