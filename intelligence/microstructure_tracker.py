"""
Microstructure Tracker

Lifecycle:

CREATED
   |
WAITING_CLOSE
   |
VALIDATED

or

WAITING_CLOSE
   |
EXPIRED
   |
RECOVERY

Observer only.
Does not modify live decisions.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class TrackingState:

    snapshot_id: str
    candle_id: str
    status: str
    created_at: str

    validated_at: str = None
    replay_result: dict = None
    expire_reason: str = None


class MicrostructureTracker:

    def __init__(
        self,
        memory,
        replay_engine,
        timeout_seconds=35
    ):
        self.memory = memory
        self.replay_engine = replay_engine
        self.timeout_seconds = timeout_seconds
        self.active = {}


    def register_snapshot(self, snapshot):

        self.memory.store(snapshot)

        state = TrackingState(
            snapshot_id=snapshot.snapshot_id,
            candle_id=snapshot.candle_id,
            status="WAITING_CLOSE",
            created_at=datetime.utcnow().isoformat()
        )

        self.active[snapshot.snapshot_id] = state

        return state


    def validate_closed_candle(
        self,
        snapshot_id,
        candle_result
    ):

        state = self.active.get(snapshot_id)

        if not state:
            return None

        if candle_result.get("candle_id") != state.candle_id:
            return self.expire(
                snapshot_id,
                "CANDLE_ID_MISMATCH"
            )

        snapshot_data = self.memory.get(snapshot_id)

        snapshot = self._restore_snapshot(snapshot_data)

        result = self.replay_engine.validate(
            snapshot,
            candle_result
        )

        self.memory.update_result(
            snapshot_id,
            result.__dict__
        )

        state.status = "VALIDATED"
        state.validated_at = datetime.utcnow().isoformat()
        state.replay_result = result.__dict__

        return state


    def expire(
        self,
        snapshot_id,
        reason="CANDLE_TIMEOUT"
    ):

        state = self.active.get(snapshot_id)

        if not state:
            return None

        state.status = "EXPIRED"
        state.expire_reason = reason

        return state


    def recovery_required(self, snapshot_id):

        state = self.active.get(snapshot_id)

        return (
            state is not None
            and state.status == "EXPIRED"
        )


    def _restore_snapshot(self, data):

        from intelligence.microstructure_snapshot import MicrostructureSnapshot

        return MicrostructureSnapshot(**data)
