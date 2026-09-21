"""
Full OTC Brain Integration Test

Purpose:
Validate the complete evidence flow:

5M Context
    ->
1M Setup
    ->
30S Execution
    ->
Pattern
    ->
Liquidity Memory
    ->
Temporal
    ->
Candle Confirmation
    ->
OTCDecisionContext
    ->
OTCDecisionFusion

No prediction.
No BUY/SELL generation.
Only integration validation.
"""

from intelligence.otc_decision_context import OTCDecisionContext
from intelligence.otc_decision_fusion import OTCDecisionFusionV3


def build_context(
    liquidity_block=False,
    candle_confirmed=True,
    conflict=False,
    timing="FRESH_EXECUTION",
):

    return OTCDecisionContext(
        market_context={
            "state": "BULLISH",
            "score": 0.90,
        },

        setup_context={
            "state": "BREAK_RETEST",
            "score": 0.85,
        },

        micro_context={
            "state": "EXPANSION",
            "score": 0.85,
        },

        pattern_context={
            "state": "ENGULFING",
            "score": 0.84,
        },

        liquidity_context={
            "state": (
                "LIQUIDITY_SWEEP"
                if liquidity_block
                else "ACCEPTED_BREAKOUT"
            ),
            "score": 0.88,
            "blocked": liquidity_block,
        },

        temporal_context={
            "state": timing,
            "score": 0.878,
        },

        candle_context={
            "confirmed": candle_confirmed,
        },

        conflict_context={
            "blocked": conflict,
        },
    )


def run():

    engine = OTCDecisionFusionV3()

    cases = [

        (
            "FULL ALIGNMENT",
            build_context()
        ),

        (
            "LIQUIDITY SWEEP",
            build_context(
                liquidity_block=True
            )
        ),

        (
            "CANDLE NOT CLOSED",
            build_context(
                candle_confirmed=False
            )
        ),

        (
            "HIGHER TIMEFRAME CONFLICT",
            build_context(
                conflict=True
            )
        ),

        (
            "BAD TIMING",
            build_context(
                timing="LATE_EXECUTION"
            )
        ),
    ]


    for name, context in cases:

        print("\n================")
        print(name)

        result = engine.evaluate(context)

        print(result)


if __name__ == "__main__":
    run()
