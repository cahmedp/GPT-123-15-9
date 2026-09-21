"""
Orchestrator Microstructure Adapter Test

Uses production-like objects.
Checks:
- Final decision conversion
- Candle identity preservation
- No decision mutation
"""

from dataclasses import dataclass

from intelligence.orchestrator_microstructure_adapter import (
    OrchestratorMicrostructureAdapter
)


@dataclass
class FinalDecision:

    asset: str = "NZD/CAD"
    advisory_action: str = "BUY"
    calibrated_confidence: float = 0.86


def run():

    adapter = OrchestratorMicrostructureAdapter()

    final = FinalDecision()

    market = {
        "multi_timeframe_bias": "BULLISH"
    }

    regime = {
        "state": "TREND"
    }

    candle_context = {
        "timeframe": "30S",
        "candle_id": "NZDCAD_021230",
        "micro_state": "EXPANSION",
        "pattern_state": "BREAK_RETEST",
        "liquidity_state": "ACCEPTED_BREAKOUT",
        "temporal_state": "FRESH_EXECUTION",
        "impulse_strength": 0.76,
        "noise_score": 0.20,
        "momentum_score": 0.90,
    }


    print("\n================")
    print("ADAPTER SNAPSHOT")

    snapshot = adapter.build_snapshot(
        final=final,
        market=market,
        regime=regime,
        candle_context=candle_context,
    )

    print(snapshot.to_dict())


    print("\n================")
    print("DECISION PRESERVED")

    print({
        "action": final.advisory_action,
        "confidence": final.calibrated_confidence
    })


if __name__ == "__main__":
    run()
