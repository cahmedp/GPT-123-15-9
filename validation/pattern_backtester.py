
"""
Pattern Backtester

Evaluates discovered patterns on replay windows.
"""

from dataclasses import dataclass


@dataclass
class BacktestResult:
    pattern: str
    samples: int
    matches: int
    success_rate: float
    status: str


class PatternBacktester:

    def evaluate(
        self,
        pattern,
        replay_results
    ):

        samples = len(replay_results)

        matches = len(
            [
                x for x in replay_results
                if x == pattern
            ]
        )

        rate = round(
            matches / samples,
            3
        ) if samples else 0


        status = (
            "SUPPORTED_PATTERN"
            if samples >= 30 and rate >= 0.6
            else "WEAK_PATTERN"
        )

        return BacktestResult(
            pattern,
            samples,
            matches,
            rate,
            status
        )
