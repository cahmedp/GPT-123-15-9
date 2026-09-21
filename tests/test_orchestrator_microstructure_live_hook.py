"""
Orchestrator Microstructure Live Hook Test

Production-like flow:

RiskManager Final Decision
        |
        v
Microstructure Adapter
        |
        v
Observer
        |
        v
Tracker

Guarantees:
- Decision object is immutable from observer side.
- Observer failure is isolated.
- Snapshot receives candle identity.
"""

from intelligence.orchestrator_microstructure_adapter import (
    OrchestratorMicrostructureAdapter
)


class MockObserver:

    def __init__(self, fail=False):
        self.fail = fail
        self.snapshot = None

    def on_snapshot(self, snapshot):

        if self.fail:
            raise RuntimeError(
                "Snapshot storage unavailable"
            )

        self.snapshot = snapshot

        return True



class LiveDecisionFlow:

    def __init__(
        self,
        adapter,
        observer
    ):
        self.adapter = adapter
        self.observer = observer


    def after_risk_decision(
        self,
        final,
        market,
        regime,
        candle_context
    ):

        snapshot = self.adapter.build_snapshot(
            final=final,
            market=market,
            regime=regime,
            candle_context=candle_context,
        )

        result = {
            "decision": final.advisory_action,
            "confidence": final.calibrated_confidence,
            "snapshot_id": snapshot.snapshot_id,
        }

        try:

            self.observer.on_snapshot(
                snapshot
            )

            result["observer"] = "OK"

        except Exception as error:

            result["observer"] = "FAILED"
            result["observer_error"] = str(error)

        return result



class FinalDecision:

    asset = "NZD/CAD"
    advisory_action = "BUY"
    calibrated_confidence = 0.86



def context():

    return {

        "timeframe":"30S",
        "candle_id":"NZDCAD_021230",

        "micro_state":"EXPANSION",
        "impulse_strength":0.76,
        "noise_score":0.20,
        "momentum_score":0.90,

        "pattern_state":"BREAK_RETEST",
        "liquidity_state":"ACCEPTED_BREAKOUT",
        "temporal_state":"FRESH_EXECUTION",
    }



def run():

    adapter = OrchestratorMicrostructureAdapter()

    print("\n================")
    print("LIVE HOOK SUCCESS")

    flow = LiveDecisionFlow(
        adapter,
        MockObserver(False)
    )

    print(
        flow.after_risk_decision(
            FinalDecision(),
            {},
            {},
            context()
        )
    )


    print("\n================")
    print("LIVE HOOK FAILURE ISOLATION")

    flow = LiveDecisionFlow(
        adapter,
        MockObserver(True)
    )

    print(
        flow.after_risk_decision(
            FinalDecision(),
            {},
            {},
            context()
        )
    )


if __name__ == "__main__":
    run()
