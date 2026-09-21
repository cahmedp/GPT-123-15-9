
from dataclasses import dataclass


@dataclass
class HybridValidationResult:
    pattern: str
    state: str
    confidence: float
    blockers: list
    evidence: dict


class HybridPatternValidationGateway:
    """
    Final gate before Hybrid Pattern enters Knowledge.

    Pipeline:
    Hybrid Confidence
    Replay
    Statistics
    Walk Forward
    """

    def validate(
        self,
        pattern,
        hybrid_confidence,
        replay_result,
        statistics,
        walk_forward
    ):

        blockers = []

        if hybrid_confidence.status == "BLOCKED":
            blockers.append("HYBRID_BLOCKED")

        if hybrid_confidence.confidence < 0.70:
            blockers.append("LOW_HYBRID_CONFIDENCE")

        if replay_result != "SUPPORTED":
            blockers.append("REPLAY_NOT_SUPPORTED")

        if statistics.get("success_rate", 0) < 0.60:
            blockers.append("WEAK_STATISTICS")

        if walk_forward != "FORWARD_VALIDATED":
            blockers.append("FAILED_WALK_FORWARD")


        if blockers:
            state = "PENDING_HYBRID"

        else:
            state = "VALIDATED_HYBRID"


        return HybridValidationResult(
            pattern=pattern,
            state=state,
            confidence=hybrid_confidence.confidence,
            blockers=blockers,
            evidence={
                "replay": replay_result,
                "statistics": statistics,
                "walk_forward": walk_forward
            }
        )
