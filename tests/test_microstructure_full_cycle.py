"""
Full Microstructure Cycle Test

Validates complete lifecycle:

Decision
 -> Snapshot
 -> Memory
 -> Waiting Close
 -> Replay Validation

and failure path:

Decision
 -> Snapshot
 -> Wrong Candle
 -> Expired
 -> Recovery
"""

from intelligence.microstructure_snapshot import create_snapshot
from intelligence.microstructure_memory import MicrostructureMemory
from intelligence.microstructure_replay import MicrostructureReplay
from intelligence.microstructure_tracker import MicrostructureTracker
from intelligence.microstructure_recovery import MicrostructureRecovery


def build_snapshot():

    return create_snapshot(
        "NZD/CAD",
        "30S",
        "NZDCAD_021230",

        {
            "state": "EXPANSION",
            "impulse_strength": 0.76,
            "noise_score": 0.20,
            "momentum_score": 0.90
        },

        {
            "state": "BREAK_RETEST"
        },

        {
            "state": "ACCEPTED_BREAKOUT"
        },

        {
            "state": "FRESH_EXECUTION"
        },

        {
            "state": "VALID_ENTRY",
            "evidence_score": 0.86,
            "execution_score": 0.86
        }
    )


def run():

    memory = MicrostructureMemory()
    replay = MicrostructureReplay()

    tracker = MicrostructureTracker(
        memory,
        replay
    )

    recovery = MicrostructureRecovery()


    print("\n================")
    print("SUCCESS PATH")

    snapshot = build_snapshot()

    state = tracker.register_snapshot(snapshot)

    print("REGISTER:")
    print(state)


    validated = tracker.validate_closed_candle(
        snapshot.snapshot_id,
        {
            "candle_id": "NZDCAD_021230",
            "direction": "CONTINUATION"
        }
    )

    print("\nVALIDATED:")
    print(validated)


    print("\n================")
    print("FAILURE PATH")

    bad_snapshot = build_snapshot()

    bad_state = tracker.register_snapshot(bad_snapshot)

    expired = tracker.validate_closed_candle(
        bad_snapshot.snapshot_id,
        {
            "candle_id": "WRONG_CANDLE",
        }
    )

    print("EXPIRED:")
    print(expired)


    print("\nRECOVERY:")

    print(
        recovery.recover(expired)
    )


if __name__ == "__main__":
    run()
