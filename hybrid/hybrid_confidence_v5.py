
from dataclasses import dataclass


@dataclass
class HybridConfidenceResult:
    pattern: str
    confidence: float
    agreement_score: float
    quality_score: float
    evidence_strength: float
    coverage_factor: float
    conflict_penalty: float
    status: str
    blockers: list


class HybridConfidenceEngine:

    def __init__(self, minimum_agents=3):
        self.minimum_agents = minimum_agents


    def _coverage_factor(self, count):

        mapping = {
            3: 0.85,
            4: 0.92,
            5: 0.96,
            6: 1.0
        }

        return mapping.get(count, 0.0)


    def calculate(self, reports, conflict_result):

        valid = [
            r for r in reports
            if r.status == "VALID"
        ]

        blockers = []

        if len(valid) < self.minimum_agents:
            blockers.append(
                "INSUFFICIENT_VALID_AGENTS"
            )

        if not valid:
            return HybridConfidenceResult(
                "NO_PATTERN",
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                "BLOCKED",
                blockers
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

        agreement = round(
            patterns[dominant] / len(valid),
            3
        )

        quality = round(
            sum(r.quality_score for r in valid)
            / len(valid),
            3
        )

        evidence_strength = round(
            min(
                len(valid) / self.minimum_agents,
                1.0
            ),
            3
        )

        coverage = self._coverage_factor(
            len(valid)
        )

        conflict_penalty = conflict_result.penalty

        confidence = round(
            agreement
            *
            quality
            *
            evidence_strength
            *
            coverage
            *
            (1 - conflict_penalty),
            3
        )

        if blockers:
            status = "BLOCKED"
        elif conflict_penalty >= 0.25:
            status = "CAUTIOUS_HYBRID"
        elif confidence >= 0.70:
            status = "STRONG_HYBRID"
        else:
            status = "WEAK_HYBRID"

        return HybridConfidenceResult(
            dominant,
            confidence,
            agreement,
            quality,
            evidence_strength,
            coverage,
            conflict_penalty,
            status,
            blockers
        )
