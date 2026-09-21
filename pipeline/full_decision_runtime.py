# ============================================================
# Full Decision Runtime v1
#
# Purpose:
# Production decision orchestration layer.
#
# Flow:
#
# Consensus
#      |
# Confidence Calibration
#      |
# Adaptive Confidence
#      |
# Dynamic Threshold
#      |
# Decision Gate
#      |
# Risk Manager
#      |
# Final Runtime Result
#
# Rules:
# - No strategy generation
# - No BUY/SELL logic
# - No execution
# - Only coordinates existing intelligence
#
# ============================================================


from dataclasses import dataclass, field
from typing import Any


# ============================================================
# Runtime Result Contract
# ============================================================


@dataclass
class RuntimeDecisionResult:
    """
    Final result returned by the decision runtime.

    This object is designed to be consumed by:
    - orchestrator
    - decision trace
    - event system
    - learning layer
    """

    allowed: bool

    stage: str

    confidence: float

    blockers: list[str] = field(
        default_factory=list
    )

    evidence: dict[str, Any] = field(
        default_factory=dict
    )



# ============================================================
# Full Decision Runtime
# ============================================================


class FullDecisionRuntime:
    """
    Central coordinator for the complete decision path.

    Existing engines remain independent.

    This class only connects them.
    """


    def __init__(
        self,
        adaptive_confidence,
        threshold_manager,
        decision_gate,
        risk_manager,
    ):

        self.adaptive_confidence = (
            adaptive_confidence
        )

        self.threshold_manager = (
            threshold_manager
        )

        self.decision_gate = (
            decision_gate
        )

        self.risk_manager = (
            risk_manager
        )



    # ========================================================
    # Main Runtime Entry
    # ========================================================


    def run(
        self,
        *,
        consensus_result,
        calibrated_decision,

        market_multiplier,
        knowledge_reliability,
        calibration_factor,

        market_mode,

        data_health,
        microstructure_valid,

        market,
        regime,
        debate,

        simulation=None,
    ):


        trace = {

            "consensus": consensus_result,

            "adaptive_confidence": None,

            "threshold": None,

            "gate": None,

            "risk": None,

        }



        # ====================================================
        # 1) Adaptive Confidence
        # ====================================================


        confidence_result = (
            self.adaptive_confidence.calculate(
                consensus_confidence=(
                    calibrated_decision
                    .calibrated_confidence
                ),

                market_multiplier=(
                    market_multiplier
                ),

                knowledge_reliability=(
                    knowledge_reliability
                ),

                calibration_factor=(
                    calibration_factor
                ),
            )
        )


        trace[
            "adaptive_confidence"
        ] = confidence_result




        # ====================================================
        # 2) Dynamic Threshold
        # ====================================================


        threshold_result = (
            self.threshold_manager.evaluate(
                confidence_result.final_confidence,
                market_mode,
            )
        )


        trace[
            "threshold"
        ] = threshold_result




        if threshold_result.decision != "ALLOW":

            return RuntimeDecisionResult(

                allowed=False,

                stage=(
                    "THRESHOLD_BLOCK"
                ),

                confidence=(
                    confidence_result
                    .final_confidence
                ),

                blockers=[
                    threshold_result.reason
                ],

                evidence=trace,

            )




        # ====================================================
        # 3) Decision Gate
        # ====================================================


        gate_result = (
            self.decision_gate.evaluate(
                consensus_confidence=(
                    consensus_result
                ),

                data_health=(
                    data_health
                ),

                microstructure_valid=(
                    microstructure_valid
                ),

                risk_blocked=False,
            )
        )


        trace[
            "gate"
        ] = gate_result




        if not gate_result.allowed:


            return RuntimeDecisionResult(

                allowed=False,

                stage="GATE_BLOCK",

                confidence=(
                    confidence_result
                    .final_confidence
                ),

                blockers=(
                    gate_result.blockers
                ),

                evidence=trace,

            )




        # ====================================================
        # 4) Final Risk Firewall
        # ====================================================


        risk_result = (
            self.risk_manager.review(

                decision=(
                    calibrated_decision
                ),

                market=market,

                regime=regime,

                debate=debate,

                simulation=simulation,

            )
        )


        trace[
            "risk"
        ] = risk_result




        if risk_result.blocked:


            return RuntimeDecisionResult(

                allowed=False,

                stage="RISK_BLOCK",

                confidence=(
                    confidence_result
                    .final_confidence
                ),

                blockers=list(
                    risk_result
                    .block_reasons
                ),

                evidence=trace,

            )




        # ====================================================
        # 5) Final Approval
        # ====================================================


        return RuntimeDecisionResult(

            allowed=True,

            stage="APPROVED",

            confidence=(
                confidence_result
                .final_confidence
            ),

            blockers=[],

            evidence=trace,

        )