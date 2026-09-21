
from dataclasses import dataclass


@dataclass
class Candle:
    timestamp: str
    open: float
    high: float
    low: float
    close: float


class CandleAdapter:

    def normalize(self, row):

        return Candle(
            timestamp=str(row["timestamp"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"])
        )
