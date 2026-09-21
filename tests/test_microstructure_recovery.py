"""
Microstructure Recovery Test
"""

from intelligence.microstructure_recovery import MicrostructureRecovery
from intelligence.microstructure_tracker import TrackingState


def run():

    recovery = MicrostructureRecovery()


    print("\n================")
    print("EXPIRED RECOVERY")

    expired = TrackingState(
        snapshot_id="old_snapshot_001",
        candle_id="NZDCAD_021230",
        status="EXPIRED",
        created_at="2026-09-19T15:00:00",
        expire_reason="CANDLE_ID_MISMATCH"
    )

    print(
        recovery.recover(expired)
    )


    print("\n================")
    print("ACTIVE SNAPSHOT")

    active = TrackingState(
        snapshot_id="active_snapshot_001",
        candle_id="NZDCAD_021300",
        status="WAITING_CLOSE",
        created_at="2026-09-19T15:00:00"
    )

    print(
        recovery.recover(active)
    )


if __name__ == "__main__":
    run()
