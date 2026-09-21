"""
Multi Timeframe Market Cycle Test

Architecture:

5M  = Market Context
1M  = Setup Structure
30S = Execution Microstructure

Tests:
- Valid continuation
- Break without retest
- Fake breakout
- Range trap
"""

from dataclasses import dataclass


@dataclass
class MultiTFResult:
    state: str
    score: float
    reason: str


class MultiTimeframeEngine:

    def evaluate(
        self,
        context_5m,
        setup_1m,
        micro_30s,
        liquidity_quality,
        temporal_quality,
        candle_confirmed,
    ):

        score = (
            0.25 * context_5m
            + 0.25 * setup_1m
            + 0.20 * micro_30s
            + 0.15 * liquidity_quality
            + 0.15 * temporal_quality
        )

        if not candle_confirmed:
            return MultiTFResult(
                "WAIT",
                round(score, 3),
                "Waiting candle confirmation"
            )

        if setup_1m < 0.55:
            return MultiTFResult(
                "WAIT",
                round(score, 3),
                "1M setup incomplete"
            )

        if micro_30s < 0.40:
            return MultiTFResult(
                "WAIT",
                round(score, 3),
                "30S execution weak"
            )

        if score >= 0.80:
            return MultiTFResult(
                "VALID_ENTRY",
                round(score, 3),
                "5M context + 1M setup + 30S execution aligned"
            )

        return MultiTFResult(
            "WAIT",
            round(score, 3),
            "Alignment insufficient"
        )


if __name__ == "__main__":

    engine = MultiTimeframeEngine()

    cases = [
        (
            "Bull trend + Break Retest + 30S Expansion",
            0.90, 0.85, 0.85, 0.80, 0.90, True
        ),
        (
            "Break without Retest",
            0.90, 0.45, 0.85, 0.70, 0.85, True
        ),
        (
            "Fake Breakout",
            0.60, 0.50, 0.80, 0.35, 0.40, True
        ),
        (
            "Good setup but candle open",
            0.90, 0.85, 0.85, 0.80, 0.90, False
        ),
    ]

    for case in cases:
        print("\n================")
        print(case[0])
        print(engine.evaluate(*case[1:]))