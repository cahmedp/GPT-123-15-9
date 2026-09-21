"""
Historical Replay Cases Test
"""

from dataclasses import dataclass


@dataclass
class ReplayResult:
    case: str
    state: str
    score: float


class HistoricalReplayEngine:

    def evaluate(
        self,
        strategy_score,
        temporal_score,
        otc_quality,
        conflict,
        candle_confirmed,
    ):
        score = (
            0.35 * strategy_score
            + 0.30 * temporal_score
            + 0.35 * otc_quality
        )

        if conflict:
            return "WAIT", round(score, 3)

        if not candle_confirmed:
            return "WAIT", round(score, 3)

        if score >= 0.80:
            return "VALID_ENTRY", round(score, 3)

        if score >= 0.55:
            return "WAIT", round(score, 3)

        return "REJECT", round(score, 3)


def run_replay():

    engine = HistoricalReplayEngine()

    cases = [
        ("Trend continuation", 0.84, 0.88, 0.82, False, True),
        ("Range market", 0.45, 0.50, 0.35, False, True),
        ("Fake breakout", 0.80, 0.60, 0.40, True, True),
        ("Early candle", 0.84, 0.85, 0.80, False, False),
    ]

    for name, strategy, temporal, otc, conflict, closed in cases:
        state, score = engine.evaluate(
            strategy,
            temporal,
            otc,
            conflict,
            closed,
        )

        print("\n================")
        print(
            ReplayResult(
                name,
                state,
                score
            )
        )


if __name__ == "__main__":
    run_replay()
