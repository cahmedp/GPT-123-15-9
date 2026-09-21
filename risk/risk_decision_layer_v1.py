
from dataclasses import dataclass


@dataclass
class RiskDecision:
    allowed: bool
    state: str
    confidence: float
    blockers: list


class RiskDecisionEngine:

    def evaluate(
        self,
        data_health,
        hybrid_confidence,
        conflict_status,
        market_mode="NORMAL"
    ):

        blockers = []

        if not data_health.valid:
            blockers.append("BAD_DATA_HEALTH")

        if hybrid_confidence.confidence < 0.70:
            blockers.append("LOW_CONFIDENCE")

        if conflict_status == "HIGH_CONFLICT":
            blockers.append("HIGH_CONFLICT")

        if market_mode == "DEFENSIVE":
            blockers.append("DEFENSIVE_MARKET")


        return RiskDecision(
            allowed=len(blockers) == 0,
            state=(
                "APPROVED"
                if not blockers
                else "BLOCKED"
            ),
            confidence=hybrid_confidence.confidence,
            blockers=blockers
        )
