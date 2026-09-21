"""
Microstructure Tracker Test

Tests:
- validation with matching candle
- candle id protection
- expiration recovery
"""

from intelligence.microstructure_snapshot import create_snapshot
from intelligence.microstructure_memory import MicrostructureMemory
from intelligence.microstructure_replay import MicrostructureReplay
from intelligence.microstructure_tracker import MicrostructureTracker


def run():

    memory = MicrostructureMemory()
    replay = MicrostructureReplay()

    tracker = MicrostructureTracker(
        memory,
        replay
    )


    snapshot = create_snapshot(
        "NZD/CAD",
        "30S",
        "NZDCAD_021230",

        {
            "state": "EXPANSION",
            "impulse_strength": 0.76,
            "noise_score": 0.20,
            "momentum_score": 0.90
        },

        {"state": "BREAK_RETEST"},
        {"state": "ACCEPTED_BREAKOUT"},
        {"state": "FRESH_EXECUTION"},

        {
            "state": "VALID_ENTRY",
            "evidence_score": 0.86,
            "execution_score": 0.86
        }
    )


    print("\n================")
    print("REGISTER")

    state = tracker.register_snapshot(snapshot)
    print(state)


    print("\n================")
    print("VALIDATE")

    print(
        tracker.validate_closed_candle(
            snapshot.snapshot_id,
            {
                "candle_id":"NZDCAD_021230",
                "direction":"CONTINUATION"
            }
        )
    )


    print("\n================")
    print("EXPIRY")

    snapshot2 = create_snapshot(
        "NZD/CAD",
        "30S",
        "NZDCAD_021300",
        {"state":"EXPANSION"},
        {"state":"BREAKOUT"},
        {"state":"ACCEPTED_BREAKOUT"},
        {"state":"FRESH"},
        {"state":"VALID_ENTRY"}
    )

    tracker.register_snapshot(snapshot2)

    print(
        tracker.validate_closed_candle(
            snapshot2.snapshot_id,
            {
                "candle_id":"WRONG_ID"
            }
        )
    )


if __name__ == "__main__":
    run()
