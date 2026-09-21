
"""
Knowledge Promotion Gate

Final gate before learned knowledge becomes ACTIVE.

Requirements:
- Lifecycle must be ACTIVE
- Bayesian evidence must be strong
- No decay detected
- Minimum samples reached
"""

from dataclasses import dataclass


@dataclass
class PromotionResult:
    promoted: bool
    state: str
    blockers: list


class KnowledgePromotionGate:

    def evaluate(
        self,
        lifecycle_state,
        bayesian_strength,
        decay_status,
        samples,
        min_samples=50
    ):

        blockers = []

        if lifecycle_state != "ACTIVE":
            blockers.append("LIFECYCLE_NOT_ACTIVE")

        if bayesian_strength != "STRONG_EVIDENCE":
            blockers.append("INSUFFICIENT_BAYESIAN_EVIDENCE")

        if decay_status == "DECAY_DETECTED":
            blockers.append("KNOWLEDGE_DECAY")

        if samples < min_samples:
            blockers.append("NOT_ENOUGH_SAMPLES")

        return PromotionResult(
            promoted=len(blockers) == 0,
            state="ACTIVE_KNOWLEDGE" if len(blockers) == 0 else "REJECTED_PENDING",
            blockers=blockers
        )
