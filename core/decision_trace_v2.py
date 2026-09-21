
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class DecisionTrace:
    decision_id: str
    pattern: str
    confidence: float
    agents: dict
    risk_state: str
    knowledge: str
    stage: str
    blockers: list = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda:
        datetime.now(timezone.utc).isoformat()
    )


class DecisionTraceBuilder:

    def create(
        self,
        decision_id,
        pattern,
        confidence,
        agents,
        risk,
        knowledge,
        stage,
        blockers=None
    ):

        return DecisionTrace(
            decision_id,
            pattern,
            confidence,
            agents,
            risk,
            knowledge,
            stage,
            blockers or []
        )
