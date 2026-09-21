
"""
Knowledge Registry

Promotes validated learning into controlled knowledge states.

Lifecycle:

PENDING_KNOWLEDGE
        |
        v
ACTIVE_KNOWLEDGE

or

REJECTED_KNOWLEDGE
        |
        v
RETIRED_KNOWLEDGE

Learning layer only.
Does not directly modify live decisions.
"""

from dataclasses import dataclass


@dataclass
class KnowledgeResult:
    state: str
    confidence: float
    samples: int
    reason: str


class KnowledgeRegistry:

    def __init__(
        self,
        min_samples=50,
        activation_threshold=0.70
    ):
        self.min_samples = min_samples
        self.activation_threshold = activation_threshold
        self.items = {}


    def evaluate(
        self,
        key,
        samples,
        success_rate,
        calibrated=True,
        counterfactual_checked=True
    ):

        if samples < self.min_samples:
            state = "PENDING_KNOWLEDGE"
            reason = "Not enough validated samples"

        elif not calibrated:
            state = "REJECTED_KNOWLEDGE"
            reason = "Confidence is not calibrated"

        elif not counterfactual_checked:
            state = "PENDING_KNOWLEDGE"
            reason = "Counterfactual validation missing"

        elif success_rate >= self.activation_threshold:
            state = "ACTIVE_KNOWLEDGE"
            reason = "Evidence threshold reached"

        else:
            state = "RETIRED_KNOWLEDGE"
            reason = "Performance below threshold"


        result = KnowledgeResult(
            state=state,
            confidence=round(success_rate, 3),
            samples=samples,
            reason=reason
        )

        self.items[key] = result

        return result


    def get(self, key):
        return self.items.get(key)
