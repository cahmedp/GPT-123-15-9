
"""
Data Quality Gate

Deterministic safety layer before intelligence pipeline.

Checks:
- timestamp validity
- duplicate candles
- missing candle gaps
- stale feed
- incomplete candles
- latency

No prediction.
No trading decision.
Only data health.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class DataHealthResult:
    healthy: bool
    score: float
    issues: list


class DataQualityGate:

    def __init__(
        self,
        max_latency_seconds=2,
        expected_interval_seconds=30
    ):
        self.max_latency_seconds = max_latency_seconds
        self.expected_interval_seconds = expected_interval_seconds
        self.last_candle_id = None
        self.last_timestamp = None


    def validate(self, candle):

        issues = []

        candle_id = candle.get("candle_id")
        timestamp = candle.get("timestamp")
        closed = candle.get(
            "closed",
            False
        )

        if not closed:
            issues.append(
                "CANDLE_NOT_CLOSED"
            )

        if not candle_id:
            issues.append(
                "MISSING_CANDLE_ID"
            )


        if self.last_candle_id == candle_id:
            issues.append(
                "DUPLICATE_CANDLE"
            )


        if self.last_timestamp is not None:

            gap = timestamp - self.last_timestamp

            if gap > self.expected_interval_seconds * 2:
                issues.append(
                    "CANDLE_GAP"
                )


        now = datetime.utcnow().timestamp()

        latency = now - timestamp

        if latency > self.max_latency_seconds:
            issues.append(
                "STALE_FEED"
            )


        self.last_candle_id = candle_id
        self.last_timestamp = timestamp


        score = max(
            0.0,
            1.0 - (
                len(issues) * 0.25
            )
        )


        return DataHealthResult(
            healthy=len(issues) == 0,
            score=round(score,3),
            issues=issues
        )
