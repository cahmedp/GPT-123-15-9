"""
Temporal Analysis Test Layer

Purpose:
Evaluate time-based behavior for OTC 30s execution.

Hierarchy:
5M = Context time
1M = Setup timing
30S = Execution timing

Measures:
- impulse age
- momentum persistence
- timing quality
- entry freshness
"""


from dataclasses import dataclass


@dataclass
class TemporalResult:
    state: str
    score: float
    reason: str


class TemporalAnalysisEngine:

    def analyze(
        self,
        ticks_in_move: int,
        ticks_since_impulse: int,
        direction_changes: int,
        execution_window: int,
    ) -> TemporalResult:

        freshness = max(
            0,
            1 - (ticks_since_impulse / execution_window)
        )

        stability = max(
            0,
            1 - (direction_changes / max(ticks_in_move, 1))
        )

        score = (
            0.55 * freshness +
            0.45 * stability
        )

        if score >= 0.75:
            return TemporalResult(
                "FRESH_EXECUTION",
                round(score, 3),
                "Impulse is fresh and stable"
            )

        if score >= 0.45:
            return TemporalResult(
                "LATE_EXECUTION",
                round(score, 3),
                "Move exists but timing is weaker"
            )

        return TemporalResult(
            "EXPIRED_OR_NOISY",
            round(score, 3),
            "Timing quality is poor"
        )


if __name__ == "__main__":

    engine = TemporalAnalysisEngine()

    tests = [
        (
            "Fresh 30s Entry",
            20, 2, 3, 20
        ),
        (
            "Late Entry",
            20, 12, 5, 20
        ),
        (
            "Noisy Move",
            20, 18, 14, 20
        ),
    ]

    for name, *args in tests:
        print("\n====", name, "====")
        print(engine.analyze(*args))