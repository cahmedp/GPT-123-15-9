"""
Full Entry Pipeline Test

5M Context
+
1M Setup
+
30S OTC Microstructure
+
Strategy Competition
+
ADX + ATR7
+
Temporal Timing
+
Candle Close Confirmation
"""

from dataclasses import dataclass


@dataclass
class PipelineResult:
    state: str
    score: float
    reason: str


class FullEntryPipeline:

    def evaluate(
        self,
        strategy_score,
        temporal_score,
        otc_impulse,
        otc_noise,
        adx,
        atr_score,
        candle_closed,
        body_strength,
        close_position,
        wick_rejection,
    ):

        adx_score = (
            1.0 if adx >= 35 else
            0.85 if adx >= 25 else
            0.60 if adx >= 15 else
            0.30
        )

        entry_quality = (
            0.25 * strategy_score
            + 0.30 * temporal_score
            + 0.20 * otc_impulse
            + 0.15 * adx_score
            + 0.10 * atr_score
        )

        entry_quality *= (1 - 0.30 * otc_noise)

        if not candle_closed:
            return PipelineResult(
                "WAIT",
                round(entry_quality, 3),
                "Waiting for candle close"
            )

        if wick_rejection >= 0.70 and close_position < 0.50:
            return PipelineResult(
                "REJECT",
                round(entry_quality, 3),
                "Candle rejection"
            )

        candle_score = (
            0.45 * body_strength
            + 0.35 * close_position
            + 0.20 * (1 - wick_rejection)
        )

        final_score = (
            0.65 * entry_quality
            + 0.35 * candle_score
        )

        if final_score >= 0.80:
            return PipelineResult(
                "VALID_ENTRY",
                round(final_score, 3),
                "Full alignment confirmed"
            )

        if final_score >= 0.60:
            return PipelineResult(
                "WAIT",
                round(final_score, 3),
                "Needs more confirmation"
            )

        return PipelineResult(
            "REJECT",
            round(final_score, 3),
            "Insufficient edge"
        )


if __name__ == "__main__":

    engine = FullEntryPipeline()

    scenarios = [
        (
            "Perfect continuation",
            0.843, 0.878, 0.764, 0.288,
            32, 0.80, True,
            0.85, 0.90, 0.10
        ),
        (
            "Strong but candle open",
            0.843, 0.878, 0.764, 0.288,
            32, 0.80, False,
            0.85, 0.90, 0.10
        ),
        (
            "Late entry",
            0.843, 0.558, 0.764, 0.288,
            32, 0.80, True,
            0.70, 0.65, 0.20
        ),
        (
            "Fake breakout rejection",
            0.843, 0.500, 0.40, 0.70,
            18, 0.40, True,
            0.30, 0.35, 0.85
        ),
    ]

    for case in scenarios:
        print("\n================")
        print(case[0])
        print(engine.evaluate(*case[1:]))