"""
Microstructure Snapshot Engine

Stores decision-time state only.
Adds:
- candle_id
- timeframe
- lifecycle metadata support

No future data leakage.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
import uuid


@dataclass
class MicrostructureSnapshot:

    asset: str
    timeframe: str
    candle_id: str

    timestamp: str

    micro_state: str
    impulse_strength: float
    noise_score: float
    momentum_score: float

    pattern_state: str
    liquidity_state: str
    temporal_state: str

    decision_state: str
    evidence_score: float
    execution_score: float

    snapshot_id: str = ""

    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = str(uuid.uuid4())

    def to_dict(self):
        return asdict(self)


def create_snapshot(
    asset,
    timeframe,
    candle_id,
    micro,
    pattern,
    liquidity,
    temporal,
    decision,
):

    return MicrostructureSnapshot(
        asset=asset,
        timeframe=timeframe,
        candle_id=candle_id,
        timestamp=datetime.utcnow().isoformat(),

        micro_state=micro.get("state", ""),
        impulse_strength=micro.get("impulse_strength", 0),
        noise_score=micro.get("noise_score", 0),
        momentum_score=micro.get("momentum_score", 0),

        pattern_state=pattern.get("state", ""),
        liquidity_state=liquidity.get("state", ""),
        temporal_state=temporal.get("state", ""),

        decision_state=decision.get("state", ""),
        evidence_score=decision.get("evidence_score", 0),
        execution_score=decision.get("execution_score", 0),
    )