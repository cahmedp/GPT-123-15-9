"""
OTC Decision Fusion V3 Test
"""

from intelligence.otc_decision_context import OTCDecisionContext
from intelligence.otc_decision_fusion import OTCDecisionFusionV3


def context(liquidity=False, candle=True, conflict=False):

    return OTCDecisionContext(
        market_context={"score":0.90},
        setup_context={"score":0.85},
        micro_context={"score":0.85},
        pattern_context={"score":0.84},
        liquidity_context={
            "score":0.88,
            "state":"LIQUIDITY_SWEEP" if liquidity else "ACCEPTED_BREAKOUT",
            "blocked":liquidity
        },
        temporal_context={
            "score":0.878,
            "state":"FRESH_EXECUTION"
        },
        candle_context={
            "confirmed":candle
        },
        conflict_context={
            "blocked":conflict
        }
    )


if __name__ == "__main__":

    engine = OTCDecisionFusionV3()

    cases = [
        ("Clean", context()),
        ("Liquidity Sweep", context(liquidity=True)),
        ("Candle Open", context(candle=False)),
        ("HTF Conflict", context(conflict=True)),
    ]

    for name, ctx in cases:
        print("\n================")
        print(name)
        print(engine.evaluate(ctx))
