
from dataclasses import dataclass


@dataclass
class ConflictResult:
    dominant_pattern: str
    conflict_score: float
    penalty: float
    status: str
    opposing_patterns: dict


class HybridConflictAnalyzer:

    def analyze(self, reports):

        valid = [
            r for r in reports
            if r.status == "VALID"
        ]

        if not valid:
            return ConflictResult(
                "NO_PATTERN",
                1.0,
                1.0,
                "BLOCKED",
                {}
            )

        patterns = {}

        for r in valid:
            patterns[r.scenario] = patterns.get(
                r.scenario, 0
            ) + 1

        dominant = max(
            patterns,
            key=patterns.get
        )

        dominant_ratio = patterns[dominant] / len(valid)

        conflict_score = round(
            1 - dominant_ratio,
            3
        )

        penalty = round(
            conflict_score * 0.5,
            3
        )

        if conflict_score == 0:
            status = "NO_CONFLICT"
        elif conflict_score < 0.35:
            status = "LOW_CONFLICT"
        elif conflict_score < 0.5:
            status = "MEDIUM_CONFLICT"
        else:
            status = "HIGH_CONFLICT"

        return ConflictResult(
            dominant,
            conflict_score,
            penalty,
            status,
            patterns
        )
