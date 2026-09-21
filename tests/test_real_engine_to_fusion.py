"""
Real Engine To Fusion Integration Test

Purpose:
Validate real engine-style outputs flowing through:

Engines
   ->
OTC Brain Adapter
   ->
OTC Decision Context
   ->
OTC Decision Fusion

No BUY/SELL generation.
No prediction.
Only integration validation.
"""

from intelligence.otc_brain_adapter import OTCBrainAdapter
from intelligence.otc_decision_fusion import OTCDecisionFusionV3


# lightweight engine-like objects
class EngineResult:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def build_realistic_engine_outputs():

    market = EngineResult(
        state="BULLISH",
        score=0.90
    )

    setup = EngineResult(
        state="BREAK_RETEST",
        score=0.85
    )

    micro = EngineResult(
        state="EXPANSION",
        score=0.85
    )

    pattern = EngineResult(
        state="ENGULFING",
        score=0.84
    )

    liquidity = EngineResult(
        state="ACCEPTED_BREAKOUT",
        score=0.88,
        blocked=False
    )

    temporal = EngineResult(
        state="FRESH_EXECUTION",
        score=0.878
    )

    candle = EngineResult(
        confirmed=True
    )

    conflict = EngineResult(
        blocked=False
    )

    return (
        market,
        setup,
        micro,
        pattern,
        liquidity,
        temporal,
        candle,
        conflict,
    )


def run():

    adapter = OTCBrainAdapter()
    fusion = OTCDecisionFusionV3()

    print("\n================")
    print("REAL ENGINE OUTPUT -> FUSION")

    outputs = build_realistic_engine_outputs()

    context = adapter.build_context(*outputs)

    print("\nCONTEXT CREATED:")
    print(context.evidence_summary())

    print("\nFUSION RESULT:")
    print(
        fusion.evaluate(context)
    )


if __name__ == "__main__":
    run()
