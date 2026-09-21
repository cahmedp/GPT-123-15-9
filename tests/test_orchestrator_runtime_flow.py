# =========================
# ORCHESTRATOR RUNTIME CHECK
# =========================


from pipeline.full_decision_runtime import (
    FullDecisionRuntime,
)


from confidence.adaptive_confidence_controller import (
    AdaptiveConfidenceController,
)


from confidence.confidence_threshold_manager import (
    ConfidenceThresholdManager,
)


from decision.consensus_decision_gate import (
    ConsensusDecisionGate,
)



class RiskMock:

    blocked = False

    block_reasons = ()



    def review(
        self,
        **kwargs
    ):

        return self



def run():


    runtime = FullDecisionRuntime(

        adaptive_confidence=
            AdaptiveConfidenceController(),

        threshold_manager=
            ConfidenceThresholdManager(),

        decision_gate=
            ConsensusDecisionGate(),

        risk_manager=
            RiskMock(),

    )


    class Consensus:

        status = (
            "RELIABLE_CONSENSUS"
        )

        confidence = 0.85



    class Decision:

        calibrated_confidence = 0.85



    result = runtime.run(

        consensus_result=Consensus(),

        calibrated_decision=Decision(),

        market_multiplier=1.0,

        knowledge_reliability=0.90,

        calibration_factor=1.0,

        market_mode="NORMAL",

        data_health=1.0,

        microstructure_valid=True,

        market=None,

        regime=None,

        debate=None,

    )


    print(result)



if __name__ == "__main__":
    run()