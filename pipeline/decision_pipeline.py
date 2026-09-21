
"""
Decision Pipeline Coordinator

Coordinates decision layers without owning trading logic.

Flow:
Input
 -> Consensus
 -> Adaptive Confidence
 -> Dynamic Threshold
 -> Decision Gate
 -> Risk
 -> Trace

The coordinator only orchestrates.
"""

from dataclasses import dataclass


@dataclass
class PipelineResult:
    allowed: bool
    confidence: float
    stage: str
    details: dict


class DecisionPipelineCoordinator:

    def run(
        self,
        consensus_result,
        confidence_result,
        threshold_result,
        gate_result,
        risk_result,
        trace=None
    ):

        details = {
            "consensus": consensus_result,
            "confidence": confidence_result,
            "threshold": threshold_result,
            "gate": gate_result,
            "risk": risk_result,
            "trace": trace,
        }

        if not threshold_result.decision == "ALLOW":
            return PipelineResult(
                False,
                confidence_result.final_confidence,
                "THRESHOLD_BLOCK",
                details
            )

        if not gate_result.allowed:
            return PipelineResult(
                False,
                confidence_result.final_confidence,
                "GATE_BLOCK",
                details
            )

        if getattr(risk_result, "blocked", False):
            return PipelineResult(
                False,
                confidence_result.final_confidence,
                "RISK_BLOCK",
                details
            )

        return PipelineResult(
            True,
            confidence_result.final_confidence,
            "APPROVED",
            details
        )
