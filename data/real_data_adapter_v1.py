
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Candle:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class DataHealth:
    valid: bool
    status: str
    issues: list


class CandleNormalizer:

    def normalize(self, raw):

        return Candle(
            timestamp=raw["timestamp"],
            open=float(raw["open"]),
            high=float(raw["high"]),
            low=float(raw["low"]),
            close=float(raw["close"]),
            volume=float(raw.get("volume", 0))
        )


class CandleStreamManager:

    def __init__(self):
        self.last_timestamp = None


    def validate(self, candles):

        issues = []

        if not candles:
            issues.append("EMPTY_STREAM")

        timestamps = [
            c.timestamp for c in candles
        ]

        if len(timestamps) != len(set(timestamps)):
            issues.append("DUPLICATE_CANDLE")

        if self.last_timestamp:
            if timestamps[-1] <= self.last_timestamp:
                issues.append("OLD_CANDLE")

        if candles:
            self.last_timestamp = timestamps[-1]


        return DataHealth(
            valid=len(issues) == 0,
            status="HEALTHY" if not issues else "DEGRADED",
            issues=issues
        )
