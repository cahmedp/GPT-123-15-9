
"""
Pattern Statistics Engine

Aggregates real replay outcomes:
- MATCH
- FAILURE
- AMBIGUOUS

Used as evidence layer before knowledge promotion.
"""

from dataclasses import dataclass, field


@dataclass
class PatternStatistics:
    pattern: str
    total_samples: int
    matches: int
    failures: int
    ambiguous: int
    success_rate: float
    confidence: float
    regimes: dict = field(default_factory=dict)


class PatternStatisticsEngine:

    def calculate(
        self,
        pattern,
        outcomes,
        regimes=None
    ):

        matches = outcomes.count("MATCH")
        failures = outcomes.count("FAILURE")
        ambiguous = outcomes.count("AMBIGUOUS")

        total = len(outcomes)

        effective = matches + failures

        success_rate = round(
            matches / effective,
            3
        ) if effective else 0


        confidence = round(
            success_rate *
            min(effective / 100, 1.0),
            3
        )


        return PatternStatistics(
            pattern=pattern,
            total_samples=total,
            matches=matches,
            failures=failures,
            ambiguous=ambiguous,
            success_rate=success_rate,
            confidence=confidence,
            regimes=regimes or {}
        )
