
"""
Consensus Confidence Analyzer

Adds confidence around consensus quality.

Measures:
- consensus score
- active trader coverage
- abstain ratio
- final confidence

Analysis layer only.
"""

from dataclasses import dataclass


@dataclass
class ConsensusConfidenceResult:
    score: float
    coverage: float
    abstain_ratio: float
    confidence: float
    status: str


class ConsensusConfidenceAnalyzer:

    def evaluate(
        self,
        score,
        active_votes,
        abstained,
        total_traders
    ):

        total_traders = max(
            total_traders,
            1
        )

        active_count = len(active_votes)
        abstain_count = len(abstained)

        coverage = round(
            active_count / total_traders,
            3
        )

        abstain_ratio = round(
            abstain_count / total_traders,
            3
        )

        # Confidence requires both agreement quality
        # and enough participating traders.
        confidence = round(
            score * coverage,
            3
        )

        if confidence >= 0.65:
            status = "RELIABLE_CONSENSUS"

        elif confidence >= 0.45:
            status = "WEAK_CONSENSUS"

        else:
            status = "UNRELIABLE_CONSENSUS"


        return ConsensusConfidenceResult(
            score=score,
            coverage=coverage,
            abstain_ratio=abstain_ratio,
            confidence=confidence,
            status=status
        )
