"""
Full Decision Runtime Integration Test

Validates:

Consensus
 ->
Adaptive Confidence
 ->
Threshold
 ->
Gate
 ->
Risk Contract
 ->
Runtime Result

Architecture validation only.
"""


from confidence.adaptive_confidence_controller import (
    AdaptiveConfidenceController
)

from confidence.confidence_threshold_manager import (
    ConfidenceThresholdManager
)

from decision.consensus_decision_gate import (
    ConsensusDecisionGate
)

from pipeline.full_decision_runtime import (
    FullDecisionRuntime
)

from risk.risk_manager import (
    FinalRiskDecision
)



class ConsensusMock:

    status = "RELIABLE_CONSENSUS"

    confidence = 0.86



class CalibratedMock:

    timestamp = 0.0
    asset = "GBPUSD_OTC"
    price = 1.0

    calibrated_confidence = 0.86



class RiskManagerMock:

    def review(
        self,
        *,
        decision,
        market,
        regime,
        debate,
        simulation=None,
    ):

        return FinalRiskDecision(

            timestamp=0.0,

            asset="GBPUSD_OTC",

            price=1.0,

            advisory_action="BUY",

            direction="BULLISH",

            calibrated_confidence=0.86,

            required_confidence=0.70,

            risk_score=0.10,

            uncertainty=0.10,

            data_risk=0.0,

            market_risk=0.05,

            model_risk=0.05,

            behavioral_risk=0.0,

            signal_strength="STRONG",

            blocked=False,

            block_reasons=(),

        )



def run():

    runtime = FullDecisionRuntime(

        adaptive_confidence=
            AdaptiveConfidenceController(),

        threshold_manager=
            ConfidenceThresholdManager(),

        decision_gate=
            ConsensusDecisionGate(),

        risk_manager=
            RiskManagerMock(),

    )


    result = runtime.run(

        consensus_result=ConsensusMock(),

        calibrated_decision=CalibratedMock(),

        market_multiplier=1.0,

        knowledge_reliability=0.90,

        calibration_factor=0.95,

        market_mode="NORMAL",

        data_health=1.0,

        microstructure_valid=True,

        market=None,

        regime=None,

        debate=None,

    )


    print(result)


    assert result.allowed is True

    assert result.stage == "APPROVED"


    print(
        "\nFULL DECISION RUNTIME TEST PASSED"
    )



if __name__ == "__main__":
    run()