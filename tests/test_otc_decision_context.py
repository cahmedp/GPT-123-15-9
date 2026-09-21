"""
OTC Decision Context Test

Validates:
- Evidence collection
- Block detection
- No decision generation inside context
"""

from intelligence.otc_decision_context import OTCDecisionContext


def run():

    valid = OTCDecisionContext(
        market_context={
            "5m": "BULLISH"
        },
        setup_context={
            "1m": "BREAK_RETEST"
        },
        micro_context={
            "30s": "EXPANSION"
        },
        pattern_context={
            "pattern": "ENGULFING",
            "score": 0.84
        },
        liquidity_context={
            "state": "ACCEPTED_BREAKOUT",
            "score": 0.88,
            "blocked": False
        },
        temporal_context={
            "state": "FRESH_EXECUTION",
            "score": 0.878
        },
        candle_context={
            "confirmed": True
        },
        conflict_context={
            "blocked": False
        }
    )

    print("\n================")
    print("VALID CONTEXT")
    print(valid.evidence_summary())
    print("BLOCKED:", valid.has_blocker())


    blocked = OTCDecisionContext(
        market_context={"5m": "BULLISH"},
        setup_context={"1m": "BREAK"},
        micro_context={"30s": "EXPANSION"},
        pattern_context={"score": 0.80},
        liquidity_context={
            "state": "LIQUIDITY_SWEEP",
            "blocked": True
        },
        temporal_context={"state": "FRESH"},
        candle_context={"confirmed": True},
        conflict_context={"blocked": False}
    )

    print("\n================")
    print("BLOCKED CONTEXT")
    print(blocked.evidence_summary())
    print("BLOCKED:", blocked.has_blocker())


if __name__ == "__main__":
    run()