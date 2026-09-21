"""
Microstructure Recovery Manager

Handles expired snapshots safely.

Rules:
- Never reuse expired snapshots.
- Never modify live decision.
- Creates recovery state only.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RecoveryResult:

    action: str
    reason: str
    old_snapshot_id: str
    created_at: str


class MicrostructureRecovery:

    def recover(self, tracking_state):

        if tracking_state.status != "EXPIRED":
            return RecoveryResult(
                action="NO_ACTION",
                reason="Snapshot still active",
                old_snapshot_id=tracking_state.snapshot_id,
                created_at=datetime.utcnow().isoformat()
            )

        return RecoveryResult(
            action="NEW_SNAPSHOT_REQUIRED",
            reason=tracking_state.expire_reason or "UNKNOWN_EXPIRY",
            old_snapshot_id=tracking_state.snapshot_id,
            created_at=datetime.utcnow().isoformat()
        )
