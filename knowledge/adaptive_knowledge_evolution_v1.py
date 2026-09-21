
from dataclasses import dataclass


@dataclass
class KnowledgeEvolutionResult:
    pattern: str
    old_confidence: float
    new_confidence: float
    old_state: str
    new_state: str
    action: str
    reason: str


class AdaptiveKnowledgeEvolution:

    def evolve(
        self,
        pattern,
        confidence,
        success_rate,
        state="ACTIVE_KNOWLEDGE"
    ):

        new_confidence = confidence
        new_state = state
        action = "NO_CHANGE"

        if success_rate >= 0.75:
            new_confidence = min(
                round(confidence + 0.02, 3),
                0.99
            )
            new_state = "PROVEN_KNOWLEDGE"
            action = "PROMOTED"

            reason = "HIGH_VALIDATED_PERFORMANCE"

        elif success_rate < 0.50:
            new_confidence = max(
                round(confidence - 0.10, 3),
                0.0
            )
            new_state = "DECAY_WARNING"
            action = "DEGRADED"

            reason = "PERFORMANCE_DECREASE"

        else:
            reason = "PERFORMANCE_STABLE"

        return KnowledgeEvolutionResult(
            pattern,
            confidence,
            new_confidence,
            state,
            new_state,
            action,
            reason
        )
