"""
Consensus Decision Gate

Final safety bridge before runtime approval.

Combines:
- Consensus reliability
- Data health
- Microstructure validation
- Risk blockers

Responsibilities:
- Permission evaluation only
- No strategy generation
- No execution logic
"""

from dataclasses import dataclass


@dataclass
class DecisionGateResult:
    allowed: bool
    confidence: float
    reason: str
    blockers: list[str]


class ConsensusDecisionGate:
    """
    Final consensus safety gate.

    Accepts both:

    Real:
        AgentDebateSnapshot
            consensus_confidence: float

    Test / adapter objects:
        status
        confidence

    """

    MIN_CONSENSUS_CONFIDENCE = 0.70


    def evaluate(
        self,
        consensus_confidence,
        data_health,
        microstructure_valid,
        risk_blocked=False,
    ):

        blockers = []


        # ==========================================
        # Extract consensus confidence safely
        # ==========================================

        confidence_value = getattr(
            consensus_confidence,
            "confidence",
            None,
        )


        if confidence_value is None:

            confidence_value = getattr(
                consensus_confidence,
                "consensus_confidence",
                0.0,
            )


        confidence_value = float(
            confidence_value
        )


        # ==========================================
        # Consensus validation
        # ==========================================

        if confidence_value < self.MIN_CONSENSUS_CONFIDENCE:

            blockers.append(
                "WEAK_CONSENSUS"
            )


        # ==========================================
        # Data health validation
        # ==========================================

        if data_health < 0.70:

            blockers.append(
                "BAD_DATA_HEALTH"
            )


        # ==========================================
        # Microstructure validation
        # ==========================================

        if not microstructure_valid:

            blockers.append(
                "MICROSTRUCTURE_INVALID"
            )


        # ==========================================
        # Risk firewall signal
        # ==========================================

        if risk_blocked:

            blockers.append(
                "RISK_MANAGER_BLOCK"
            )


        allowed = (
            len(blockers) == 0
        )


        return DecisionGateResult(

            allowed=allowed,

            confidence=round(
                confidence_value,
                3,
            ),

            reason=(
                "All decision conditions passed"
                if allowed
                else "Decision blocked by gate"
            ),

            blockers=blockers,
        )
    