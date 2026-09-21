"""
Microstructure Observer Test

Flow:
Decision event
 ->
Snapshot
 ->
Tracker
 ->
Candle close
 ->
Validation
"""

from intelligence.microstructure_memory import MicrostructureMemory
from intelligence.microstructure_replay import MicrostructureReplay
from intelligence.microstructure_tracker import MicrostructureTracker
from intelligence.microstructure_observer import MicrostructureObserver


def run():

    tracker = MicrostructureTracker(
        MicrostructureMemory(),
        MicrostructureReplay()
    )

    observer = MicrostructureObserver(tracker)


    print("\n================")
    print("DECISION EVENT")

    state = observer.on_decision(
        asset="NZD/CAD",
        timeframe="30S",
        candle_id="NZDCAD_021230",

        micro={
            "state":"EXPANSION",
            "impulse_strength":0.76,
            "noise_score":0.20,
            "momentum_score":0.90
        },

        pattern={
            "state":"BREAK_RETEST"
        },

        liquidity={
            "state":"ACCEPTED_BREAKOUT"
        },

        temporal={
            "state":"FRESH_EXECUTION"
        },

        decision={
            "state":"VALID_ENTRY",
            "evidence_score":0.86,
            "execution_score":0.86
        }
    )

    print(state)


    print("\n================")
    print("CANDLE CLOSE")

    result = observer.on_candle_close(
        state.snapshot_id,
        {
            "candle_id":"NZDCAD_021230",
            "direction":"CONTINUATION"
        }
    )

    print(result)


if __name__ == "__main__":
    run()
