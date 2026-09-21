"""
Test OTC Brain Adapter

Validates conversion:
Engine Outputs -> OTCDecisionContext
"""

from intelligence.otc_brain_adapter import OTCBrainAdapter


def run():

    adapter = OTCBrainAdapter()

    context = adapter.build_context(
        market_result={
            "state": "BULLISH",
            "score": 0.90
        },
        setup_result={
            "state": "BREAK_RETEST",
            "score": 0.85
        },
        micro_result={
            "state": "EXPANSION",
            "score": 0.85
        },
        pattern_result={
            "state": "ENGULFING",
            "score": 0.84
        },
        liquidity_result={
            "state": "ACCEPTED_BREAKOUT",
            "score": 0.88,
            "blocked": False
        },
        temporal_result={
            "state": "FRESH_EXECUTION",
            "score": 0.878
        },
        candle_result={
            "confirmed": True
        },
        conflict_result={
            "blocked": False
        }
    )

    print("\n================")
    print("ADAPTER OUTPUT")
    print(context.evidence_summary())

    print("\nBLOCKED:")
    print(context.has_blocker())


if __name__ == "__main__":
    run()
