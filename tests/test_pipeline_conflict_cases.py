"""
Pipeline Conflict Cases Test

Purpose:
Validate that the system rejects conflicting environments.

Cases:
1) 5M trend conflict with 1M/30S
2) High OTC noise
3) Expired temporal signal
4) Strategy disagreement
"""


from dataclasses import dataclass


@dataclass
class ConflictResult:
    state: str
    score: float
    reason: str


class PipelineConflictEngine:

    def evaluate(
        self,
        context_5m: str,
        setup_1m: str,
        strategy_score: float,
        temporal_score: float,
        otc_noise: float,
        otc_impulse: float,
        candle_confirmed: bool,
        direction_conflict: bool,
    ) -> ConflictResult:

        score = (
            0.30 * strategy_score
            + 0.30 * temporal_score
            + 0.20 * otc_impulse
            + 0.20 * (1 - otc_noise)
        )

        if direction_conflict:
            return ConflictResult(
                "WAIT",
                round(score, 3),
                "Higher timeframe conflict detected",
            )

        if otc_noise >= 0.80:
            return ConflictResult(
                "WAIT",
                round(score, 3),
                "OTC environment too noisy",
            )

        if temporal_score < 0.40:
            return ConflictResult(
                "NO_EDGE",
                round(score, 3),
                "Timing expired",
            )

        if not candle_confirmed:
            return ConflictResult(
                "WAIT",
                round(score, 3),
                "Waiting candle confirmation",
            )

        if score >= 0.80:
            return ConflictResult(
                "VALID_ENTRY",
                round(score, 3),
                "No conflict detected",
            )

        return ConflictResult(
            "WAIT",
            round(score, 3),
            "Alignment incomplete",
        )


if __name__ == "__main__":

    engine = PipelineConflictEngine()

    tests = [
        (
            "5M conflict",
            "BULLISH", "PULLBACK",
            0.84, 0.85, 0.30, 0.75,
            True, True
        ),
        (
            "High OTC noise",
            "BULLISH", "PULLBACK",
            0.84, 0.85, 0.90, 0.75,
            True, False
        ),
        (
            "Expired timing",
            "BULLISH", "PULLBACK",
            0.84, 0.20, 0.30, 0.75,
            True, False
        ),
        (
            "Clean setup",
            "BULLISH", "PULLBACK",
            0.84, 0.87, 0.28, 0.76,
            True, False
        ),
    ]

    for case in tests:
        print("\n================")
        print(case[0])
        print(engine.evaluate(*case[1:]))
