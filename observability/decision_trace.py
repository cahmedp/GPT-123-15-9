
"""
Decision Trace

Complete observability record for every decision path.

Purpose:
- reproduce decisions
- debug failures
- compare replay vs live
- support future learning

Observability only.
Never changes decision outcome.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class DecisionTrace:
    candle_id: str
    asset: str
    data_health: float
    traders: dict
    knowledge_used: list
    consensus_score: float
    consensus_confidence: float
    gate_status: str
    blockers: list
    timestamp: str


class DecisionTraceRecorder:

    def create(
        self,
        candle_id,
        asset,
        data_health,
        traders,
        knowledge_used,
        consensus_score,
        consensus_confidence,
        gate_result
    ):

        return DecisionTrace(
            candle_id=candle_id,
            asset=asset,
            data_health=data_health,
            traders=traders,
            knowledge_used=knowledge_used,
            consensus_score=consensus_score,
            consensus_confidence=consensus_confidence,
            gate_status=(
                "PASSED"
                if gate_result.allowed
                else "BLOCKED"
            ),
            blockers=gate_result.blockers,
            timestamp=datetime.now(
                timezone.utc
            ).isoformat()
        )


    def export(self, trace):
        return asdict(trace)
