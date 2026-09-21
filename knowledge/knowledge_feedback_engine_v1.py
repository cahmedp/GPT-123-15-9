
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class FeedbackResult:
    pattern: str
    outcome: str
    performance_score: float
    confidence_delta: float
    action: str


class KnowledgeFeedbackEngine:

    def evaluate(
        self,
        knowledge,
        prediction,
        actual,
        reward
    ):

        if prediction == actual:
            outcome = "MATCH"
            delta = 0.05
            action = "REINFORCE"
        else:
            outcome = "MISMATCH"
            delta = -0.05
            action = "PENALIZE"


        knowledge.confidence = round(
            max(
                min(
                    knowledge.confidence + delta,
                    1.0
                ),
                0.0
            ),
            3
        )

        knowledge.evidence["latest_feedback"] = {
            "outcome": outcome,
            "reward": reward,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat()
        }

        return FeedbackResult(
            knowledge.name,
            outcome,
            knowledge.confidence,
            delta,
            action
        )
